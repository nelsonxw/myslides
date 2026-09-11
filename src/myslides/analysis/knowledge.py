"""
Knowledge synthesis: learns what makes top slides effective and updates design rules.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from sqlalchemy.orm import Session

from myslides.config import settings
from myslides.library.models import DesignRuleRecord, SlideRecord


DEFAULT_DESIGN_RULES = {
    "visuals": {
        "preferred_chart_types": ["bar", "column", "line", "donut"],
        "icon_count_range": {"min": 2, "max": 6},
        "use_visual_anchors": True,
    },
    "layout": {
        "whitespace_ratio_range": {"min": 0.35, "max": 0.55},
        "min_margin_in": 0.5,
        "max_columns": 4,
        "grid_alignment_tolerance_in": 0.1,
    },
    "formatting": {
        "max_font_families": 2,
        "font_hierarchy": {
            "title_pt_range": {"min": 26, "max": 36},
            "subtitle_pt_range": {"min": 14, "max": 18},
            "section_header_pt_range": {"min": 14, "max": 18},
            "body_pt_range": {"min": 11, "max": 14},
            "caption_pt_range": {"min": 9, "max": 11},
        },
        "color_palette_limit": {"min": 2, "max": 4},
        "brand_colors": [
            "#0672CB",  # Dell Blue
            "#1D2C3B",  # Cosmos
            "#00468B",  # Ocean
            "#0B7C84",  # Forest
            "#F0F0F0",  # Quartz
            "#FFFFFF",  # White
        ],
    },
    "archetypes": {
        "kpi_summary": {"columns": 3, "has_stat_callouts": True, "has_icons": True},
        "timeline": {"steps_range": {"min": 3, "max": 5}, "orientation": "horizontal"},
        "comparison": {"columns": 2, "has_headers": True},
        "process": {"steps_range": {"min": 3, "max": 4}, "has_connectors": True},
    },
}


def build_knowledge_rules(db_session: Session) -> dict[str, Any]:
    """Analyze high-scoring slides in the library to distill effective design patterns."""
    # Query top-quartile slides (score >= 75)
    top_slides = (
        db_session.query(SlideRecord)
        .join(SlideRecord.score)
        .filter(SlideRecord.score.has())
        .order_by(SlideRecord.score.property.mapper.class_.total_score.desc())  # type: ignore
        .limit(50)
        .all()
    )

    rules = dict(DEFAULT_DESIGN_RULES)

    if top_slides:
        # Extract whitespace, font counts, color counts from top slides
        whitespaces = []
        font_counts = []
        for s in top_slides:
            if s.features:
                f_json = s.features.features_json
                whitespaces.append(f_json.get("whitespace_ratio", 0.45))
                font_counts.append(len(f_json.get("fonts", [])))

        if whitespaces:
            avg_ws = sum(whitespaces) / len(whitespaces)
            rules["layout"]["whitespace_ratio_range"] = {
                "min": round(max(0.25, avg_ws - 0.15), 2),
                "max": round(min(0.65, avg_ws + 0.15), 2),
            }

    # Persist rules to disk
    settings.ensure_directories()
    rules_file = settings.data_dir / "knowledge" / "design_rules.json"
    with open(rules_file, "w", encoding="utf-8") as f:
        json.dump(rules, f, indent=2)

    # Persist to database DesignRuleRecord
    for category, items in rules.items():
        existing = db_session.query(DesignRuleRecord).filter_by(category=category, name="rules_bundle").first()
        if not existing:
            rec = DesignRuleRecord(
                category=category,
                name="rules_bundle",
                target_value=items,
                description=f"Synthesized design principles for {category}",
            )
            db_session.add(rec)
        else:
            existing.target_value = items
    db_session.commit()

    return rules


def get_cached_design_rules() -> dict[str, Any]:
    """Read design rules from disk or return default."""
    rules_file = settings.data_dir / "knowledge" / "design_rules.json"
    if rules_file.exists():
        try:
            with open(rules_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_DESIGN_RULES
