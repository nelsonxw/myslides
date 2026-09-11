"""
Slide visual quality metrics: charts, icons, images, diagrams, infographics.
"""
from __future__ import annotations

from typing import Any


def calculate_visual_metrics(features: dict[str, Any]) -> dict[str, float]:
    """Calculate scores (0.0 to 1.0) for visual richness and balance."""
    shapes = features.get("shapes", [])
    has_chart = features.get("has_chart", False)
    has_table = features.get("has_table", False)
    has_images = features.get("has_images", False)
    icon_count = features.get("icon_count", 0)
    
    # 1. Visual Diversity score: combinations of visual aids (charts, icons, diagrams)
    visual_types = 0
    if has_chart:
        visual_types += 1
    if has_table:
        visual_types += 1
    if has_images or icon_count > 0:
        visual_types += 1
    
    diversity_score = min(1.0, visual_types * 0.4)
    
    # 2. Icon usage score: sweet spot is 2-6 icons for visual anchors
    if icon_count == 0:
        icon_score = 0.5  # Neutral (text or chart slides may not need icons)
    elif 1 <= icon_count <= 6:
        icon_score = 1.0  # Optimal
    else:
        icon_score = 0.7  # Overcrowded with icons
        
    # 3. Chart/Infographic impact score
    chart_score = 1.0 if has_chart else (0.8 if has_table else 0.5)

    # Composite visual score
    composite = round(0.4 * diversity_score + 0.3 * icon_score + 0.3 * chart_score, 3)

    return {
        "visual_diversity": diversity_score,
        "icon_usage": icon_score,
        "chart_impact": chart_score,
        "composite_visual_score": composite,
    }
