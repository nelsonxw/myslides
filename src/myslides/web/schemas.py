"""
Pydantic API schemas for FastAPI endpoints.
"""
from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class CreateSourceRequest(BaseModel):
    name: str
    kind: str = "generic_url"  # local_folder | slidescarnival | ms_create | github | generic_url
    url_or_path: str
    license: str = "Unknown"
    attribution: str = ""


class SourceResponse(BaseModel):
    id: int
    name: str
    kind: str
    url_or_path: str
    license: str
    attribution: str
    enabled: bool
    last_scraped_at: str | None = None
    last_status: str
    last_error: str | None = None


class SlideLibraryItem(BaseModel):
    id: int
    asset_id: int
    asset_title: str
    slide_index: int
    title: str
    subtitle: str
    archetype: str
    score: float
    visuals_score: float
    layout_score: float
    formatting_score: float
    tags: list[str]
    has_chart: bool
    has_table: bool
    icon_count: int
    license: str
    attribution: str


class SlideLibraryResponse(BaseModel):
    total_count: int
    filtered_count: int
    slides: list[SlideLibraryItem]


class CreateSessionRequest(BaseModel):
    prompt: str = Field(..., min_length=3, description="User description of the slide to generate")


class IterateSessionRequest(BaseModel):
    feedback: str = Field(..., min_length=2, description="Feedback or adjustments requested by user")
