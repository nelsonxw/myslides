"""
Slide generation specifications and blueprint schemas.
"""
from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


class SlideIntentSpec(BaseModel):
    """Structured intent parsed from a user prompt."""
    purpose: str = Field(..., description="Main business purpose of the slide")
    audience: str = Field("Executives", description="Target audience")
    archetype: Literal[
        "kpi_summary",
        "timeline",
        "comparison",
        "process",
        "agenda",
        "architecture",
        "data_chart",
        "general",
    ] = Field("general", description="Chosen visual layout archetype")
    headline: str = Field(..., description="Action title (max 10 words)")
    subhead: str = Field("", description="Supporting context or key takeaway")
    key_points: list[str] = Field(default_factory=list, description="Core messages or steps")
    data_points: list[dict[str, Any]] = Field(default_factory=list, description="KPI metrics or chart data")
    tone: str = Field("executive", description="Visual tone")
    brand_style: str = Field("Dell Brand", description="Target brand template style")


class ShapeBlueprint(BaseModel):
    """A shape or visual element on the generated slide."""
    id: str
    type: Literal[
        "card",
        "text_box",
        "kpi_stat",
        "icon",
        "chart",
        "table",
        "arrow",
        "badge",
        "divider",
    ]
    left_in: float
    top_in: float
    width_in: float
    height_in: float
    bg_color: str | None = None  # Hex color (e.g. #0672CB, #F0F0F0)
    border_color: str | None = None
    title: str = ""
    text: str = ""
    stat_number: str = ""
    stat_label: str = ""
    icon_name: str = ""  # Conceptual icon name (e.g. chart, cloud, rocket, shield)
    chart_type: Literal["column", "bar", "line", "pie", "donut"] | None = None
    chart_categories: list[str] = Field(default_factory=list)
    chart_series: list[dict[str, Any]] = Field(default_factory=list)  # [{"name": "2026", "values": [10, 20]}]
    font_size_pt: float | None = None
    font_color: str | None = None
    font_bold: bool = False
    items: list[str] = Field(default_factory=list)  # bullet points for card/text


class SlideBlueprint(BaseModel):
    """Complete executable blueprint for rendering a 16:9 PowerPoint slide."""
    title: str
    subtitle: str
    archetype: str
    layout_index: int = 29  # Default to layout 29 (Title & Subtitle only)
    shapes: list[ShapeBlueprint] = Field(default_factory=list)
    palette: list[str] = Field(
        default_factory=lambda: ["#0672CB", "#1D2C3B", "#00468B", "#F0F0F0", "#FFFFFF"]
    )
    change_summary: str = "Initial generation"
