"""
Composer: combines intent, design rules, and library exemplars to produce a validated SlideBlueprint.
"""
from __future__ import annotations

import json
from typing import Any
from myslides.analysis.knowledge import get_cached_design_rules
from myslides.generation.spec import ShapeBlueprint, SlideBlueprint, SlideIntentSpec
from myslides.llm.provider import LLMProvider


COMPOSER_PROMPT = """You are an elite presentation designer. Create a pixel-perfect, executive-grade one-page PowerPoint slide blueprint based on the following specifications:

SLIDE SPECIFICATION:
Headline: {headline}
Subtitle: {subhead}
Archetype: {archetype}
Key Points: {key_points}
Data Points: {data_points}

DESIGN PRINCIPLES & CONSTRAINTS:
- Slide Dimensions: 13.33 inches wide x 7.5 inches high (16:9 widescreen)
- Available Vertical Space: Y = 1.4 inches to Y = 6.8 inches (Header is in Y=0.4 to 1.3)
- Left/Right Margins: X >= 0.8 inches and X + Width <= 12.5 inches
- Brand Colors:
  - Primary Accent: #0672CB (Dell Blue)
  - Card/Container Fill: #F0F0F0 (Quartz light grey) or #FFFFFF (White)
  - Dark Container: #1D2C3B (Cosmos dark blue/grey)
  - Dark Text: #1D2C3B
  - White Text: #FFFFFF
- Visual Hierarchy: Clear cards/containers, large KPI numbers (32-44pt), concise labels (11-14pt).
- Archetype layout patterns:
  - kpi_summary: 3 or 4 horizontal metric cards (width ~2.6-3.5in, height ~4.5in, top ~1.6in)
  - timeline/process: 3 to 4 sequential milestone cards side-by-side with step numbers/badges
  - comparison: 2 wide side-by-side columns (left ~0.8in and ~6.8in, width ~5.7in)
  - data_chart: 1 chart container on left/top + takeaway callout cards on right/bottom

Respond ONLY with a JSON object in this exact schema:
{{
  "title": "{headline}",
  "subtitle": "{subhead}",
  "archetype": "{archetype}",
  "layout_index": 29,
  "change_summary": "Generated optimal {archetype} executive layout",
  "shapes": [
    {{
      "id": "card_1",
      "type": "card",
      "left_in": 0.8,
      "top_in": 1.6,
      "width_in": 3.6,
      "height_in": 4.8,
      "bg_color": "#F0F0F0",
      "title": "Card Title",
      "stat_number": "85%",
      "stat_label": "Key Metric Subtitle",
      "icon_name": "target",
      "items": ["First key takeaway point", "Second supporting evidence point"]
    }}
  ]
}}
"""


def compose_slide_blueprint(
    intent: SlideIntentSpec,
    exemplars: list[dict[str, Any]],
    llm: LLMProvider,
) -> SlideBlueprint:
    """Produce a validated SlideBlueprint using LLM + rule validation."""
    prompt = COMPOSER_PROMPT.format(
        headline=intent.headline,
        subhead=intent.subhead,
        archetype=intent.archetype,
        key_points=json.dumps(intent.key_points),
        data_points=json.dumps(intent.data_points),
    )

    try:
        raw_json = llm.complete_json([{"role": "user", "content": prompt}])
        blueprint = SlideBlueprint(**raw_json)
    except Exception as e:
        print(f"LLM composer fallback: {e}")
        blueprint = _build_fallback_blueprint(intent)

    # Apply deterministic rule validation & bounds clamping
    validated = validate_and_autofix_blueprint(blueprint)
    return validated


def validate_and_autofix_blueprint(blueprint: SlideBlueprint) -> SlideBlueprint:
    """Ensure coordinates do not overflow the 13.33 x 7.5 canvas and maintain clean margins."""
    canvas_w = 13.33
    canvas_h = 7.5
    min_x = 0.6
    max_x = 12.73
    min_y = 1.4
    max_y = 6.9

    fixed_shapes = []
    for s in blueprint.shapes:
        # Clamp bounds
        left = max(min_x, min(s.left_in, max_x - 1.0))
        top = max(min_y, min(s.top_in, max_y - 1.0))
        width = min(s.width_in, canvas_w - left - 0.6)
        height = min(s.height_in, canvas_h - top - 0.5)

        # Default fallback styling
        bg_col = s.bg_color or "#F0F0F0"

        fixed_s = s.model_copy(
            update={
                "left_in": round(left, 2),
                "top_in": round(top, 2),
                "width_in": round(width, 2),
                "height_in": round(height, 2),
                "bg_color": bg_col,
            }
        )
        fixed_shapes.append(fixed_s)

    return blueprint.model_copy(update={"shapes": fixed_shapes})


def _build_fallback_blueprint(intent: SlideIntentSpec) -> SlideBlueprint:
    """Deterministic, high-quality fallback layout when LLM is unavailable."""
    shapes = []
    points = intent.key_points or ["Core business milestone achieved", "Operational efficiency increased", "Strategic growth roadmap"]
    num_cards = min(len(points), 4) or 3
    card_w = round((11.8 - (num_cards - 1) * 0.4) / num_cards, 2)

    for i in range(num_cards):
        left = round(0.8 + i * (card_w + 0.4), 2)
        stat_val = f"#{i+1}" if not intent.data_points else intent.data_points[i % len(intent.data_points)].get("value", f"0{i+1}")
        stat_lbl = "Milestone" if not intent.data_points else intent.data_points[i % len(intent.data_points)].get("label", "Key Objective")
        
        shapes.append(
            ShapeBlueprint(
                id=f"card_{i+1}",
                type="card",
                left_in=left,
                top_in=1.6,
                width_in=card_w,
                height_in=4.8,
                bg_color="#F0F0F0" if i % 2 == 0 else "#FFFFFF",
                title=f"Focus Area {i+1}",
                stat_number=str(stat_val),
                stat_label=str(stat_lbl),
                icon_name="target",
                items=[points[i % len(points)], "Aligned with organizational strategic priorities"],
            )
        )

    return SlideBlueprint(
        title=intent.headline,
        subtitle=intent.subhead or "Executive strategy & progress overview",
        archetype=intent.archetype,
        layout_index=29,
        change_summary="Built structured multi-column executive card layout",
        shapes=shapes,
    )
