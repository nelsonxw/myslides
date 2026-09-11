"""
Intent analysis: converts unstructured user prompts into structured SlideIntentSpec.
"""
from __future__ import annotations

import json
from myslides.generation.spec import SlideIntentSpec
from myslides.llm.provider import LLMProvider


INTENT_PROMPT = """You are an executive PowerPoint presentation director.
Given the user's slide prompt, extract structured intent into a clear slide specification.

User Prompt:
"{prompt}"

Respond ONLY with a JSON object conforming to this schema:
{{
  "purpose": "Primary objective of the slide",
  "audience": "Executives / Technical Team / Clients",
  "archetype": "kpi_summary" | "timeline" | "comparison" | "process" | "agenda" | "architecture" | "data_chart" | "general",
  "headline": "Action-oriented slide title (max 8-10 words)",
  "subhead": "Single sentence takeaway or context",
  "key_points": ["3 to 4 distinct key messages or sequential milestones"],
  "data_points": [
    {{"label": "Metric Name", "value": "Number/Pct", "delta": "+15%"}}
  ],
  "tone": "executive",
  "brand_style": "Dell Brand"
}}
"""


def parse_user_intent(prompt: str, llm: LLMProvider) -> SlideIntentSpec:
    """Parse user prompt into a structured SlideIntentSpec."""
    formatted = INTENT_PROMPT.format(prompt=prompt)
    try:
        data = llm.complete_json([{"role": "user", "content": formatted}])
        return SlideIntentSpec(**data)
    except Exception as e:
        print(f"Intent parsing fallback: {e}")
        # Robust heuristic fallback
        return SlideIntentSpec(
            purpose="Executive briefing",
            audience="Leadership",
            archetype="kpi_summary" if any(w in prompt.lower() for w in ["kpi", "metric", "revenue", "stat"]) else "general",
            headline=prompt.split("\n")[0][:60].title() or "Executive Summary",
            subhead="Key updates and strategic highlights",
            key_points=["High priority milestones delivered", "Quarterly objectives on track", "Upcoming strategic focus areas"],
        )
