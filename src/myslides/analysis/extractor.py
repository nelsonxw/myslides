"""
Extract structured features, shapes, layouts, and typography from a PowerPoint slide.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE


def extract_presentation_features(pptx_path: Path | str) -> list[dict[str, Any]]:
    """Extract all slides with their visual, layout, and textual features."""
    prs = Presentation(str(pptx_path))
    slide_width = prs.slide_width
    slide_height = prs.slide_height

    slides_data = []
    for idx, slide in enumerate(prs.slides):
        slide_info = extract_single_slide_features(slide, idx, slide_width, slide_height)
        slides_data.append(slide_info)

    return slides_data


def extract_single_slide_features(slide, slide_index: int, slide_width: int, slide_height: int) -> dict[str, Any]:
    """Extract features for a single slide."""
    layout_name = getattr(slide.slide_layout, "name", f"Layout {slide_index}")
    
    shapes_data = []
    title_text = ""
    subtitle_text = ""
    all_texts = []
    
    fonts_used = set()
    font_sizes = []
    colors_used = set()
    
    has_chart = False
    has_table = False
    has_images = False
    icon_count = 0

    for shape in slide.shapes:
        s_data = _extract_shape_data(shape, slide_width, slide_height)
        shapes_data.append(s_data)

        # Update flags & counts
        if s_data["type"] == "chart":
            has_chart = True
        elif s_data["type"] == "table":
            has_table = True
        elif s_data["type"] == "picture":
            has_images = True
            # Icon heuristic: roughly square and small (< 1.5 inches)
            if 0.8 <= (s_data["width_ratio"] / (s_data["height_ratio"] + 1e-6)) <= 1.2:
                if s_data["width_in"] <= 1.5:
                    icon_count += 1
        
        # Check text
        if s_data.get("text"):
            all_texts.append(s_data["text"])
            if s_data.get("is_title"):
                title_text = s_data["text"]
            elif s_data.get("is_subtitle"):
                subtitle_text = s_data["text"]
        
        for f in s_data.get("fonts", []):
            if f:
                fonts_used.add(f)
        for sz in s_data.get("font_sizes", []):
            if sz:
                font_sizes.append(sz)
        for col in s_data.get("colors", []):
            if col:
                colors_used.add(col)

    # Compute bounding boxes and whitespace
    occupied_area = sum(s["width_ratio"] * s["height_ratio"] for s in shapes_data if s["type"] not in ["group"])
    # Clamp occupied area ratio between 0 and 1
    occupied_ratio = min(max(occupied_area, 0.0), 0.95)
    whitespace_ratio = round(1.0 - occupied_ratio, 3)

    return {
        "slide_index": slide_index,
        "layout_name": layout_name,
        "title_text": title_text,
        "subtitle_text": subtitle_text,
        "all_text": "\n".join(all_texts),
        "shapes": shapes_data,
        "shape_count": len(shapes_data),
        "has_chart": has_chart,
        "has_table": has_table,
        "has_images": has_images,
        "icon_count": icon_count,
        "fonts": sorted(list(fonts_used)),
        "font_count": len(fonts_used),
        "font_sizes": font_sizes,
        "colors": sorted(list(colors_used)),
        "whitespace_ratio": whitespace_ratio,
        "dimensions": {
            "width_emu": slide_width,
            "height_emu": slide_height,
            "width_in": round(slide_width / 914400, 2),
            "height_in": round(slide_height / 914400, 2),
        },
    }


def _extract_shape_data(shape, slide_width: int, slide_height: int) -> dict[str, Any]:
    left = getattr(shape, "left", 0) or 0
    top = getattr(shape, "top", 0) or 0
    width = getattr(shape, "width", 0) or 0
    height = getattr(shape, "height", 0) or 0

    shape_type_name = "unknown"
    if shape.has_text_frame:
        shape_type_name = "text_box"
    if shape.has_chart:
        shape_type_name = "chart"
    elif shape.has_table:
        shape_type_name = "table"
    elif getattr(shape, "shape_type", None) == MSO_SHAPE_TYPE.PICTURE:
        shape_type_name = "picture"
    elif getattr(shape, "shape_type", None) == MSO_SHAPE_TYPE.AUTO_SHAPE:
        shape_type_name = "auto_shape"
    elif getattr(shape, "shape_type", None) == MSO_SHAPE_TYPE.GROUP:
        shape_type_name = "group"

    # Placeholder detection
    is_title = False
    is_subtitle = False
    if shape.is_placeholder:
        ph_type = shape.placeholder_format.type
        # 1=Title, 3=Center Title
        if ph_type in (1, 3):
            is_title = True
        elif ph_type == 2:
            is_subtitle = True

    # Extract text and typography
    text = ""
    fonts = set()
    font_sizes = []
    colors = set()

    if shape.has_text_frame:
        text = shape.text_frame.text
        for p in shape.text_frame.paragraphs:
            for r in p.runs:
                if r.font.name:
                    fonts.add(r.font.name)
                if r.font.size:
                    font_sizes.append(round(r.font.size.pt, 1))
                try:
                    if r.font.color and getattr(r.font.color, "type", None) is not None:
                        # python-pptx raises AttributeError on .rgb when color is inherited/theme/None
                        rgb = getattr(r.font.color, "rgb", None)
                        if rgb:
                            colors.add(f"#{rgb}")
                except Exception:
                    pass

    return {
        "name": shape.name,
        "type": shape_type_name,
        "is_placeholder": shape.is_placeholder,
        "is_title": is_title,
        "is_subtitle": is_subtitle,
        "left_in": round(left / 914400, 3),
        "top_in": round(top / 914400, 3),
        "width_in": round(width / 914400, 3),
        "height_in": round(height / 914400, 3),
        "left_ratio": round(left / (slide_width or 1), 3),
        "top_ratio": round(top / (slide_height or 1), 3),
        "width_ratio": round(width / (slide_width or 1), 3),
        "height_ratio": round(height / (slide_height or 1), 3),
        "text": text,
        "fonts": list(fonts),
        "font_sizes": font_sizes,
        "colors": list(colors),
    }
