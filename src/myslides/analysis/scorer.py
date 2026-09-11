"""
Composite slide quality scorer (0 to 100) with dimensional breakdown.
"""
from __future__ import annotations

from typing import Any
from myslides.analysis.metrics.formatting import calculate_formatting_metrics
from myslides.analysis.metrics.layout import calculate_layout_metrics
from myslides.analysis.metrics.visuals import calculate_visual_metrics


def score_slide(features: dict[str, Any]) -> dict[str, Any]:
    """Calculate overall quality score (0 - 100) and detailed dimensional breakdowns."""
    vis = calculate_visual_metrics(features)
    lay = calculate_layout_metrics(features)
    fmt = calculate_formatting_metrics(features)

    vis_score = vis["composite_visual_score"] * 100
    lay_score = lay["composite_layout_score"] * 100
    fmt_score = fmt["composite_formatting_score"] * 100

    # Overall weight: 35% Layout & Structure, 35% Design & Formatting, 30% Visuals
    total_score = round(0.35 * lay_score + 0.35 * fmt_score + 0.30 * vis_score, 1)

    return {
        "total_score": total_score,
        "visuals_score": round(vis_score, 1),
        "layout_score": round(lay_score, 1),
        "formatting_score": round(fmt_score, 1),
        "breakdown": {
            "visuals": vis,
            "layout": lay,
            "formatting": fmt,
        },
    }
