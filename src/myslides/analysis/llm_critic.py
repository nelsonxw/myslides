"""
LLM Critic: analyzes a slide to assign archetype tags, strengths, weaknesses, and key design takeaways.
"""
from __future__ import annotations

from typing import Any
from myslides.llm.provider import LLMProvider


CRITIC_PROMPT = """You are an executive PowerPoint design expert.
Analyze the following extracted slide structure and provide a concise design evaluation in JSON format:

Slide Title: {title}
Subtitle: {subtitle}
Shapes Count: {shape_count}
Has Chart: {has_chart}
Has Table: {has_table}
Icon Count: {icon_count}
Whitespace Ratio: {whitespace_ratio}
Slide Text Sample:
{text_sample}

Respond ONLY with a JSON object in this exact schema:
{{
  "archetype": "kpi_summary" | "timeline" | "comparison" | "process" | "agenda" | "architecture" | "data_chart" | "general",
  "tags": ["list", "of", "relevant", "keywords"],
  "strengths": ["1-3 bullet points on what works well in layout/visuals"],
  "weaknesses": ["1-2 suggestions for improvement"],
  "critic_notes": "One sentence summary of why this slide is effective or how it should be used."
}}
"""


def critique_slide(features: dict[str, Any], llm: LLMProvider) -> dict[str, Any]:
    """Use LLM to generate qualitative tags, archetype classification, and critique."""
    text_sample = features.get("all_text", "")[:500]
    prompt = CRITIC_PROMPT.format(
        title=features.get("title_text", "Untitled"),
        subtitle=features.get("subtitle_text", ""),
        shape_count=features.get("shape_count", 0),
        has_chart=features.get("has_chart", False),
        has_table=features.get("has_table", False),
        icon_count=features.get("icon_count", 0),
        whitespace_ratio=features.get("whitespace_ratio", 0.5),
        text_sample=text_sample,
    )

    try:
        data = llm.complete_json([{"role": "user", "content": prompt}])
        return {
            "archetype": data.get("archetype", "general"),
            "tags": data.get("tags", ["slide"]),
            "strengths": data.get("strengths", ["Clean layout"]),
            "weaknesses": data.get("weaknesses", []),
            "critic_notes": data.get("critic_notes", "Standard presentation slide."),
        }
    except Exception:
        # Fallback heuristic
        archetype = "general"
        if features.get("has_chart"):
            archetype = "data_chart"
        elif features.get("icon_count", 0) >= 3:
            archetype = "kpi_summary"
        return {
            "archetype": archetype,
            "tags": ["auto-tagged"],
            "strengths": ["Parsed from template"],
            "weaknesses": [],
            "critic_notes": "Slide analyzed via heuristic rules.",
        }
