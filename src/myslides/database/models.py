"""
Database models for MySlides.
SQLAlchemy models for storing collections, templates, and generation requests.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, JSON, Text, Float, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class SlideCollection(Base):
    """Model for storing slide collection information."""
    __tablename__ = "slide_collections"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)  # For future multi-user support
    file_name = Column(String, nullable=False)
    upload_date = Column(DateTime, default=datetime.utcnow)
    total_slides = Column(Integer, default=0)
    storage_path = Column(String)  # Firebase Storage path
    metadata = Column(JSON)  # Additional metadata
    
    # Relationship to templates
    templates = relationship("SlideTemplate", back_populates="collection", cascade="all, delete-orphan")
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "file_name": self.file_name,
            "upload_date": self.upload_date.isoformat() if self.upload_date else None,
            "total_slides": self.total_slides,
            "storage_path": self.storage_path,
            "metadata": self.metadata
        }


class SlideTemplate(Base):
    """Model for storing slide template information."""
    __tablename__ = "slide_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    collection_id = Column(Integer, ForeignKey("slide_collections.id"), nullable=False)
    slide_index = Column(Integer, nullable=False)
    
    # Classification and tags
    classification = Column(String, index=True)
    tags = Column(JSON)  # List of tags
    
    # File references
    thumbnail_path = Column(String)
    original_pptx_reference = Column(String)  # Reference to original file
    
    # Template data
    element_manifest = Column(JSON)  # Structured JSON of shapes, positions, styles
    placeholder_map = Column(JSON)  # Which fields are variable vs decorative
    color_palette = Column(JSON)  # Extracted color palette
    complexity_score = Column(Integer)
    
    # Embeddings (stored as JSON arrays for MVP)
    visual_embedding = Column(JSON)  # Visual embedding vector
    semantic_embedding = Column(JSON)  # Semantic embedding vector
    
    # Description and metadata
    description = Column(Text)
    template_hash = Column(String, index=True)  # For identifying similar layouts
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship to collection
    collection = relationship("SlideCollection", back_populates="templates")
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "collection_id": self.collection_id,
            "slide_index": self.slide_index,
            "classification": self.classification,
            "tags": self.tags,
            "thumbnail_path": self.thumbnail_path,
            "original_pptx_reference": self.original_pptx_reference,
            "element_manifest": self.element_manifest,
            "placeholder_map": self.placeholder_map,
            "color_palette": self.color_palette,
            "complexity_score": self.complexity_score,
            "visual_embedding": self.visual_embedding,
            "semantic_embedding": self.semantic_embedding,
            "description": self.description,
            "template_hash": self.template_hash,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class GenerationRequest(Base):
    """Model for storing slide generation requests."""
    __tablename__ = "generation_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)  # For future multi-user support
    prompt_text = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Parsed intent
    parsed_intent = Column(JSON)  # Structured intent from LLM
    
    # Template matching
    matched_template_ids = Column(JSON)  # List of matched template IDs
    selected_template_id = Column(Integer, ForeignKey("slide_templates.id"))
    
    # Generation results
    generated_file_path = Column(String)
    status = Column(String, default="pending")  # pending, generating, complete, failed
    error_message = Column(Text)
    
    # Performance metrics
    processing_time_seconds = Column(Float)
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "prompt_text": self.prompt_text,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "parsed_intent": self.parsed_intent,
            "matched_template_ids": self.matched_template_ids,
            "selected_template_id": self.selected_template_id,
            "generated_file_path": self.generated_file_path,
            "status": self.status,
            "error_message": self.error_message,
            "processing_time_seconds": self.processing_time_seconds
        }


class GeneratedDeck(Base):
    """Model for storing generated slide decks."""
    __tablename__ = "generated_decks"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)  # For future multi-user support
    title = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Slide references (ordered list of generation request IDs)
    slides = Column(JSON)  # Ordered array of GenerationRequest IDs
    
    # Export information
    export_file_path = Column(String)
    export_format = Column(String, default="pptx")  # pptx, pdf
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "slides": self.slides,
            "export_file_path": self.export_file_path,
            "export_format": self.export_format
        }
