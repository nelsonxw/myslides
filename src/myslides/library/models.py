"""
SQLAlchemy ORM models for the template library.
"""
from __future__ import annotations

import datetime
from typing import Any
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Source(Base):
    """A template/slide source (online site, GitHub, local folder, URL)."""
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    kind = Column(String(50), nullable=False)  # local_folder | slidescarnival | ms_create | github | generic_url
    url_or_path = Column(Text, nullable=False)
    license = Column(String(100), default="Unknown")
    attribution = Column(Text, default="")
    enabled = Column(Boolean, default=True)
    last_scraped_at = Column(DateTime, nullable=True)
    last_status = Column(String(50), default="idle")  # idle | running | success | error
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    assets = relationship("TemplateAsset", back_populates="source", cascade="all, delete-orphan")


class TemplateAsset(Base):
    """An ingested .pptx file."""
    __tablename__ = "template_assets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=True)
    sha256 = Column(String(64), unique=True, nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(Text, nullable=False)
    file_size = Column(Integer, default=0)
    slide_count = Column(Integer, default=0)
    title = Column(String(255), default="")
    author_or_source = Column(String(255), default="")
    license = Column(String(100), default="Unknown")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    source = relationship("Source", back_populates="assets")
    slides = relationship("SlideRecord", back_populates="asset", cascade="all, delete-orphan")


class SlideRecord(Base):
    """A single slide extracted from an asset."""
    __tablename__ = "slide_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(Integer, ForeignKey("template_assets.id"), nullable=False)
    slide_index = Column(Integer, nullable=False)  # 0-based
    structural_hash = Column(String(64), index=True)
    layout_name = Column(String(100), default="")
    preview_png_path = Column(Text, nullable=True)
    title_text = Column(Text, default="")
    subtitle_text = Column(Text, default="")
    all_text = Column(Text, default="")
    
    # LLM Critic qualitative assessment
    archetype = Column(String(100), default="general")  # kpi_summary, timeline, comparison, process, agenda, architecture, data_chart, cover
    tags = Column(JSON, default=list)  # list of strings
    strengths = Column(JSON, default=list)
    weaknesses = Column(JSON, default=list)
    critic_notes = Column(Text, default="")

    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    asset = relationship("TemplateAsset", back_populates="slides")
    features = relationship("SlideFeaturesRecord", uselist=False, back_populates="slide", cascade="all, delete-orphan")
    score = relationship("SlideScoreRecord", uselist=False, back_populates="slide", cascade="all, delete-orphan")


class SlideFeaturesRecord(Base):
    """Extracted raw design metrics/features."""
    __tablename__ = "slide_features"

    id = Column(Integer, primary_key=True, autoincrement=True)
    slide_id = Column(Integer, ForeignKey("slide_records.id"), nullable=False, unique=True)
    
    # Raw features dictionary (shapes, positions, fonts, colors, charts)
    features_json = Column(JSON, nullable=False)
    
    # Pre-indexed summary metrics for quick querying
    shape_count = Column(Integer, default=0)
    has_chart = Column(Boolean, default=False)
    has_table = Column(Boolean, default=False)
    has_images = Column(Boolean, default=False)
    icon_count = Column(Integer, default=0)
    font_count = Column(Integer, default=0)
    whitespace_ratio = Column(Float, default=0.0)
    alignment_score = Column(Float, default=0.0)
    contrast_min = Column(Float, default=0.0)

    slide = relationship("SlideRecord", back_populates="features")


class SlideScoreRecord(Base):
    """Computed quality score & dimensional breakdown."""
    __tablename__ = "slide_scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    slide_id = Column(Integer, ForeignKey("slide_records.id"), nullable=False, unique=True)
    
    total_score = Column(Float, nullable=False, index=True)  # 0 - 100
    visuals_score = Column(Float, default=0.0)               # charts, icons, images, diagrams
    layout_score = Column(Float, default=0.0)                # alignment, whitespace, spacing, hierarchy
    formatting_score = Column(Float, default=0.0)            # fonts, colors, contrast, consistency
    breakdown = Column(JSON, default=dict)                   # detailed metric breakdown

    slide = relationship("SlideRecord", back_populates="score")


class DesignRuleRecord(Base):
    """Learned design principles derived from top-quartile slides."""
    __tablename__ = "design_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String(50), nullable=False)  # visuals | layout | formatting | archetype
    name = Column(String(100), nullable=False)
    target_value = Column(JSON, nullable=False)  # e.g. {"min": 0.35, "max": 0.55} or ["#0672CB", ...]
    importance_weight = Column(Float, default=1.0)
    description = Column(Text, default="")
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)
