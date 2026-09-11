"""
Slide ingestion pipeline: .pptx -> TemplateAsset + SlideRecords + features + scores + previews.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any
from sqlalchemy.orm import Session

from myslides.analysis.extractor import extract_presentation_features
from myslides.analysis.llm_critic import critique_slide
from myslides.analysis.scorer import score_slide
from myslides.config import settings
from myslides.library.dedupe import compute_slide_structural_hash, file_sha256
from myslides.library.models import (
    SlideFeaturesRecord,
    SlideRecord,
    SlideScoreRecord,
    TemplateAsset,
)
from myslides.llm.provider import LLMProvider


def ingest_pptx_file(
    file_path: Path | str,
    db_session: Session,
    source_id: int | None = None,
    license_str: str = "Unknown",
    attribution: str = "",
    author: str = "",
    llm: LLMProvider | None = None,
    renderer_func: Any = None,
) -> TemplateAsset | None:
    """
    Ingest a .pptx file into the database:
    - Calculates SHA-256 (dedupes asset)
    - Extracts all slide features
    - Computes quality scores
    - Generates slide preview thumbnails
    - Runs LLM critic for semantic tags/archetypes
    """
    path = Path(file_path).resolve()
    if not path.exists() or not path.name.endswith(".pptx"):
        return None

    sha = file_sha256(path)
    # Check if asset already ingested
    existing_asset = db_session.query(TemplateAsset).filter_by(sha256=sha).first()
    if existing_asset:
        return existing_asset

    settings.ensure_directories()
    # Store copy of asset in data/assets/<sha>/
    asset_dir = settings.data_dir / "assets" / sha
    asset_dir.mkdir(parents=True, exist_ok=True)
    target_pptx = asset_dir / path.name
    shutil.copy2(path, target_pptx)

    # Extract all slide features
    try:
        slides_features = extract_presentation_features(target_pptx)
    except Exception as e:
        print(f"Failed to parse {path.name}: {e}")
        return None

    asset = TemplateAsset(
        source_id=source_id,
        sha256=sha,
        filename=path.name,
        file_path=str(target_pptx),
        file_size=path.stat().st_size,
        slide_count=len(slides_features),
        title=path.stem.replace("_", " ").title(),
        author_or_source=author,
        license=license_str,
    )
    db_session.add(asset)
    db_session.flush()

    # Process each slide
    for f in slides_features:
        idx = f["slide_index"]
        s_hash = compute_slide_structural_hash(f)
        
        # Calculate quality scores
        score_data = score_slide(f)
        
        # Run LLM critic if available
        critic_data = critique_slide(f, llm) if llm else {
            "archetype": "general", "tags": [], "strengths": [], "weaknesses": [], "critic_notes": ""
        }

        # Render preview thumbnail if renderer supplied
        preview_path = None
        if renderer_func:
            try:
                preview_path = renderer_func(target_pptx, idx)
            except Exception as e:
                print(f"Thumbnail render failed for slide {idx}: {e}")

        slide_rec = SlideRecord(
            asset_id=asset.id,
            slide_index=idx,
            structural_hash=s_hash,
            layout_name=f.get("layout_name", ""),
            preview_png_path=str(preview_path) if preview_path else None,
            title_text=f.get("title_text", ""),
            subtitle_text=f.get("subtitle_text", ""),
            all_text=f.get("all_text", ""),
            archetype=critic_data.get("archetype", "general"),
            tags=critic_data.get("tags", []),
            strengths=critic_data.get("strengths", []),
            weaknesses=critic_data.get("weaknesses", []),
            critic_notes=critic_data.get("critic_notes", ""),
        )
        db_session.add(slide_rec)
        db_session.flush()

        # Features record
        feat_rec = SlideFeaturesRecord(
            slide_id=slide_rec.id,
            features_json=f,
            shape_count=f.get("shape_count", 0),
            has_chart=f.get("has_chart", False),
            has_table=f.get("has_table", False),
            has_images=f.get("has_images", False),
            icon_count=f.get("icon_count", 0),
            font_count=f.get("font_count", 0),
            whitespace_ratio=f.get("whitespace_ratio", 0.0),
            alignment_score=score_data["breakdown"]["layout"]["alignment"],
            contrast_min=score_data["breakdown"]["formatting"]["contrast"],
        )
        db_session.add(feat_rec)

        # Score record
        score_rec = SlideScoreRecord(
            slide_id=slide_rec.id,
            total_score=score_data["total_score"],
            visuals_score=score_data["visuals_score"],
            layout_score=score_data["layout_score"],
            formatting_score=score_data["formatting_score"],
            breakdown=score_data["breakdown"],
        )
        db_session.add(score_rec)

    db_session.commit()
    return asset
