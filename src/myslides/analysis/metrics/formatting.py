"""
Slide design & formatting metrics: font count, size hierarchy, color palette harmony, contrast, consistency.
"""
from __future__ import annotations

import re
from typing import Any


def calculate_formatting_metrics(features: dict[str, Any]) -> dict[str, float]:
    """Calculate formatting quality scores (0.0 to 1.0)."""
    fonts = features.get("fonts", [])
    font_count = len(fonts)
    
    # 1. Font Choice & Count Score: 1-2 font families is professional, 3+ is messy
    if font_count in (1, 2):
        font_choice_score = 1.0
    elif font_count == 3:
        font_choice_score = 0.7
    elif font_count > 3:
        font_choice_score = 0.3
    else:
        font_choice_score = 0.8  # Default template inherited

    # 2. Color Palette Score: 2 to 5 distinct colors (primary, secondary, neutral, background, accent)
    colors = features.get("colors", [])
    color_count = len(colors)
    if 2 <= color_count <= 5:
        palette_score = 1.0
    elif color_count in (1, 6):
        palette_score = 0.8
    elif color_count > 6:
        palette_score = 0.4  # Rainbow / uncoordinated
    else:
        palette_score = 0.7

    # 3. Contrast Score: heuristic check on hex color brightness
    contrast_score = 0.85
    # If dark text on light slide or light text on dark slide
    if colors:
        brightness_vals = [_hex_luminance(c) for c in colors if re.match(r"^#[0-9A-Fa-f]{6}$", c)]
        if brightness_vals:
            max_b = max(brightness_vals)
            min_b = min(brightness_vals)
            if (max_b - min_b) > 0.4:
                contrast_score = 1.0
            else:
                contrast_score = 0.5  # low contrast

    # 4. Consistent Styling: standard margins and shape consistency
    shapes = features.get("shapes", [])
    has_consistent_margins = all(s.get("left_in", 0) >= 0.3 for s in shapes if not s.get("is_placeholder"))
    styling_score = 0.95 if has_consistent_margins else 0.7

    composite = round(
        0.30 * font_choice_score +
        0.25 * palette_score +
        0.25 * contrast_score +
        0.20 * styling_score,
        3
    )

    return {
        "font_choice": font_choice_score,
        "color_palette": palette_score,
        "contrast": contrast_score,
        "consistent_styling": styling_score,
        "composite_formatting_score": composite,
    }


def _hex_luminance(hex_str: str) -> float:
    """Compute relative perceived luminance of a hex color (0.0 to 1.0)."""
    hex_clean = hex_str.lstrip("#")
    if len(hex_clean) != 6:
        return 0.5
    try:
        r = int(hex_clean[0:2], 16) / 255.0
        g = int(hex_clean[2:4], 16) / 255.0
        b = int(hex_clean[4:6], 16) / 255.0
        return 0.299 * r + 0.587 * g + 0.114 * b
    except ValueError:
        return 0.5
