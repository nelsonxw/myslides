"""
Library router: explore templates, slide scores, quality metrics, and learned design rules.
"""
from __future__ import annotations

from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from myslides.analysis.knowledge import get_cached_design_rules
from myslides.library.models import SlideRecord, SlideScoreRecord, TemplateAsset
from myslides.library.repository import get_session
from myslides.web.schemas import SlideLibraryItem, SlideLibraryResponse

router = APIRouter(prefix="/api/library", tags=["library"])


@router.get("/slides", response_model=SlideLibraryResponse)
def list_slides(
    archetype: str | None = None,
    min_score: float = 0.0,
    search: str | None = None,
    limit: int = 500,
    db: Session = Depends(get_session),
):
    total_in_db = db.query(SlideRecord).count()
    query = db.query(SlideRecord).join(SlideRecord.score)
    if archetype and archetype != "all":
        query = query.filter(SlideRecord.archetype == archetype)
    if min_score > 0:
        query = query.filter(SlideRecord.score.has(SlideScoreRecord.total_score >= min_score))
    if search:
        query = query.filter(
            (SlideRecord.title_text.ilike(f"%{search}%"))
            | (SlideRecord.all_text.ilike(f"%{search}%"))
        )

    filtered_count = query.count()
    slides = query.limit(limit).all()
    results = []
    for s in slides:
        feat = s.features.features_json if s.features else {}
        results.append(
            SlideLibraryItem(
                id=s.id,
                asset_id=s.asset_id,
                asset_title=s.asset.title if s.asset else "",
                slide_index=s.slide_index,
                title=s.title_text or f"Slide {s.slide_index + 1}",
                subtitle=s.subtitle_text or "",
                archetype=s.archetype or "general",
                score=s.score.total_score if s.score else 0.0,
                visuals_score=s.score.visuals_score if s.score else 0.0,
                layout_score=s.score.layout_score if s.score else 0.0,
                formatting_score=s.score.formatting_score if s.score else 0.0,
                tags=s.tags or [],
                has_chart=bool(feat.get("has_chart", False)),
                has_table=bool(feat.get("has_table", False)),
                icon_count=feat.get("icon_count", 0),
                license=s.asset.license if s.asset else "Unknown",
                attribution=s.asset.source.attribution if (s.asset and s.asset.source) else (s.asset.author_or_source if s.asset else ""),
            )
        )
    return SlideLibraryResponse(
        total_count=total_in_db,
        filtered_count=filtered_count,
        slides=results,
    )


@router.get("/slides/{slide_id}/preview.png")
def get_slide_thumbnail(slide_id: int, db: Session = Depends(get_session)):
    slide = db.query(SlideRecord).filter_by(id=slide_id).first()
    if not slide or not slide.preview_png_path or not Path(slide.preview_png_path).exists():
        raise HTTPException(status_code=404, detail="Preview not found")
    return FileResponse(slide.preview_png_path, media_type="image/png")


@router.delete("/slides/{slide_id}")
def delete_single_slide(slide_id: int, db: Session = Depends(get_session)):
    """Delete a single slide record from the library."""
    slide = db.query(SlideRecord).filter_by(id=slide_id).first()
    if not slide:
        raise HTTPException(status_code=404, detail="Slide not found")
    db.delete(slide)
    db.commit()
    return {"status": "deleted", "slide_id": slide_id}


@router.delete("/slides")
def delete_all_slides(db: Session = Depends(get_session)):
    """Clear all slides and template assets from the library."""
    deleted_slides = db.query(SlideRecord).delete()
    deleted_assets = db.query(TemplateAsset).delete()
    db.commit()
    return {"status": "cleared", "slides_deleted": deleted_slides, "assets_deleted": deleted_assets}


@router.get("/rules")
def get_design_rules():
    """Return the synthesized corporate design rules & target metrics."""
    return get_cached_design_rules()
