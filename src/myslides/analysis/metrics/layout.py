"""
Slide layout metrics: alignment, whitespace, consistent spacing, visual hierarchy, reading flow.
"""
from __future__ import annotations

import statistics
from typing import Any


def calculate_layout_metrics(features: dict[str, Any]) -> dict[str, float]:
    """Calculate scores (0.0 to 1.0) for structure, hierarchy, alignment, and whitespace."""
    shapes = [s for s in features.get("shapes", []) if s.get("type") != "group"]
    if not shapes:
        return {
            "alignment": 0.5,
            "whitespace": 0.5,
            "consistent_spacing": 0.5,
            "visual_hierarchy": 0.5,
            "reading_flow": 0.5,
            "composite_layout_score": 0.5,
        }

    # 1. Whitespace score: sweet spot is 30% to 60% whitespace
    ws = features.get("whitespace_ratio", 0.5)
    if 0.30 <= ws <= 0.65:
        whitespace_score = 1.0
    elif 0.20 <= ws < 0.30 or 0.65 < ws <= 0.80:
        whitespace_score = 0.75
    else:
        whitespace_score = 0.40  # either totally cluttered or empty

    # 2. Alignment score: check how many left / top edges share coordinates (within 0.1 inch tolerance)
    lefts = [round(s["left_in"], 1) for s in shapes]
    tops = [round(s["top_in"], 1) for s in shapes]
    
    unique_lefts = len(set(lefts))
    unique_tops = len(set(tops))
    total_shapes = len(shapes)
    
    # Fewer distinct x/y grid lines per shape means higher alignment
    left_align_ratio = 1.0 - (unique_lefts / max(total_shapes, 1))
    top_align_ratio = 1.0 - (unique_tops / max(total_shapes, 1))
    alignment_score = max(0.2, min(1.0, round((left_align_ratio + top_align_ratio) / 1.5 + 0.3, 3)))

    # 3. Spacing consistency: calculate standard deviation of horizontal / vertical gaps
    sorted_by_x = sorted(shapes, key=lambda s: s["left_in"])
    x_gaps = []
    for i in range(len(sorted_by_x) - 1):
        gap = sorted_by_x[i+1]["left_in"] - (sorted_by_x[i]["left_in"] + sorted_by_x[i]["width_in"])
        if gap >= 0.05:  # meaningful positive gap
            x_gaps.append(gap)
            
    spacing_score = 0.8
    if len(x_gaps) >= 2:
        std_gap = statistics.stdev(x_gaps)
        spacing_score = max(0.3, min(1.0, round(1.0 - (std_gap / 2.0), 3)))

    # 4. Visual Hierarchy: font size tiers
    font_sizes = features.get("font_sizes", [])
    if len(font_sizes) >= 2:
        distinct_tiers = len(set(round(sz) for sz in font_sizes))
        # 2 to 4 distinct font size tiers is optimal (Title, Section/Header, Body, Caption)
        if 2 <= distinct_tiers <= 4:
            hierarchy_score = 1.0
        elif distinct_tiers == 1:
            hierarchy_score = 0.4  # monotone text
        else:
            hierarchy_score = 0.6  # too chaotic font sizes
    else:
        hierarchy_score = 0.7

    # 5. Logical Reading Flow: check if title is at top, key content flows top-to-bottom, left-to-right
    title_at_top = any(s.get("is_title") and s.get("top_in", 99) < 2.0 for s in shapes) or bool(features.get("title_text"))
    reading_flow_score = 1.0 if title_at_top else 0.6

    composite = round(
        0.25 * alignment_score +
        0.25 * whitespace_score +
        0.20 * spacing_score +
        0.15 * hierarchy_score +
        0.15 * reading_flow_score,
        3
    )

    return {
        "alignment": alignment_score,
        "whitespace": whitespace_score,
        "consistent_spacing": spacing_score,
        "visual_hierarchy": hierarchy_score,
        "reading_flow": reading_flow_score,
        "composite_layout_score": composite,
    }
