"""
Pydantic models for API requests and responses.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


# Collection Models
class CollectionCreate(BaseModel):
    """Request model for creating a collection."""
    file_name: str
    storage_path: str
    total_slides: int
    metadata: Optional[Dict[str, Any]] = None


class CollectionResponse(BaseModel):
    """Response model for a collection."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_name: str
    storage_path: str
    total_slides: int
    upload_date: datetime
    metadata: Optional[Dict[str, Any]] = None


class CollectionsListResponse(BaseModel):
    """Response model for listing collections."""
    collections: List[CollectionResponse]
    total: int


# Template Models
class TemplateResponse(BaseModel):
    """Response model for a template."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    collection_id: int
    slide_index: int
    classification: str
    tags: List[str]
    thumbnail_path: Optional[str]
    element_manifest: Dict[str, Any]
    placeholder_map: List[Dict[str, Any]]
    color_palette: List[str]
    complexity_score: int
    description: str
    template_hash: str


class TemplateUpdate(BaseModel):
    """Request model for updating a template."""
    classification: Optional[str] = None
    tags: Optional[List[str]] = None


class TemplatesListResponse(BaseModel):
    """Response model for listing templates."""
    templates: List[TemplateResponse]
    total: int


# Generation Models
class PromptParseRequest(BaseModel):
    """Request model for parsing a prompt."""
    prompt_text: str
    conversation_id: Optional[str] = None


class PromptParseResponse(BaseModel):
    """Response model for parsed prompt."""
    slide_type: str
    content: Dict[str, Any]
    tone: Optional[str] = None
    element_preferences: Optional[List[str]] = None
    color_preference: Optional[str] = None


class TemplateSuggestionRequest(BaseModel):
    """Request model for getting template suggestions."""
    slide_type: str
    content: Dict[str, Any]
    tone: Optional[str] = None
    n_results: int = 5
    use_adaptive_element_count: bool = True


class TemplateSuggestionResponse(BaseModel):
    """Response model for template suggestions."""
    template_id: str
    template_data: Dict[str, Any]
    similarity_score: float
    rank: int
    match_reason: str


class SlideGenerationRequest(BaseModel):
    """Request model for generating a slide."""
    slide_type: str
    content: Dict[str, Any]
    tone: Optional[str] = None
    template_id: Optional[str] = None
    element_preferences: Optional[List[str]] = None
    color_preference: Optional[str] = None


class SlideGenerationResponse(BaseModel):
    """Response model for generated slide."""
    request_id: int
    status: str
    file_path: Optional[str] = None
    preview_path: Optional[str] = None
    error: Optional[str] = None


class DeckGenerationRequest(BaseModel):
    """Request model for generating a deck."""
    prompts: List[str]
    title: Optional[str] = "Generated Deck"


class DeckGenerationResponse(BaseModel):
    """Response model for generated deck."""
    deck_id: int
    status: str
    file_path: Optional[str] = None
    slide_count: int
    error: Optional[str] = None


# Palette Models
class PaletteResponse(BaseModel):
    """Response model for a color palette."""
    colors: List[str]
    source_template_id: Optional[int] = None
    source_collection_id: Optional[int] = None


class PalettesListResponse(BaseModel):
    """Response model for listing color palettes."""
    palettes: List[PaletteResponse]
    total: int


# Upload Models
class UploadProgress(BaseModel):
    """Model for upload progress."""
    file_name: str
    status: str  # pending, uploading, processing, complete, error
    progress: float  # 0.0 to 1.0
    templates_created: int = 0
    error: Optional[str] = None


class UploadResponse(BaseModel):
    """Response model for file upload."""
    collection_id: int
    file_name: str
    status: str
    templates_created: int
