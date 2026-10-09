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
    slide_type: Optional[str] = None
    content: Optional[Dict[str, Any]] = None
    tone: Optional[str] = None
    template_id: Optional[str] = None
    element_preferences: Optional[List[str]] = None
    color_preference: Optional[str] = None
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


class DeckResponse(BaseModel):
    """Response model for a deck."""
    id: int
    title: str
    slides: List[int]
    created_at: Optional[str] = None


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


# Curated Training Slides Models
class CuratedSlideItemResponse(BaseModel):
    """Model for a curated training slide from Firebase Storage."""
    name: str
    storage_path: str
    size: int
    updated: Optional[str] = None
    download_url: str
    public_url: str
    template_id: Optional[int] = None
    classification: Optional[str] = None
    tags: Optional[List[str]] = None
    is_indexed: bool = False


class CuratedSlidesListResponse(BaseModel):
    """Response model for listing curated training slides."""
    slides: List[CuratedSlideItemResponse]
    total: int
    indexed_count: int


class CuratedSlidesStatusResponse(BaseModel):
    """Response model for curated training slides status."""
    firebase_connected: bool
    storage_bucket: str
    curated_slides_folder: str
    total_curated_in_storage: int
    total_curated_indexed: int
    total_templates_in_db: int
    total_collections_in_db: int


class CuratedSlidesSyncResponse(BaseModel):
    """Response model for curated slides sync operation."""
    total_found: int
    total_pending: int
    synced_count: int
    failed_count: int
    errors: List[Dict[str, str]]


class CuratedSlidesReindexStatusResponse(BaseModel):
    """Response model for curated slides manual re-indexing and vectorization."""
    status: str  # idle, running, completed, error
    total: int = 0
    processed: int = 0
    current: str = ""
    progress_percent: float = 0.0
    time_taken_seconds: Optional[float] = None
    categories_summary: Optional[Dict[str, int]] = None
    error: Optional[str] = None


class CuratedSlidesSyncAndReindexStatusResponse(BaseModel):
    """Response model for combined sync and re-index operation."""
    status: str  # idle, running, completed, error
    sync_total_found: int = 0
    sync_synced_count: int = 0
    sync_failed_count: int = 0
    reindex_total: int = 0
    reindex_processed: int = 0
    reindex_progress_percent: float = 0.0
    current: str = ""
    time_taken_seconds: Optional[float] = None
    categories_summary: Optional[Dict[str, int]] = None
    error: Optional[str] = None



# Slide Improvement / Redesign Models
class SlideImprovementResponse(BaseModel):
    """Response model for analyzing an existing slide and suggesting improved layouts."""
    original_classification: str
    extracted_title: str
    extracted_subtitle: Optional[str] = None
    extracted_items: List[str]
    suggested_prompt: str
    recommended_slide_types: List[str]
    parsed_intent: Dict[str, Any]
    suggested_templates: List[Dict[str, Any]]


# Slide AI Refinement Models (for Edit Tab)
class SlideRefineRequest(BaseModel):
    """Request model for modifying a generated slide using natural language prompt."""
    refinement_prompt: str
    current_slide_type: str
    current_content: Dict[str, Any]
    current_template_id: Optional[str] = None
    current_color_preference: Optional[str] = None
    conversation_id: Optional[str] = None


class SlideRefineResponse(BaseModel):
    """Response model after AI refinement."""
    request_id: int
    status: str
    file_path: Optional[str] = None
    slide_type: str
    content: Dict[str, Any]
    template_id: Optional[str] = None
    color_preference: Optional[str] = None
    matched_template_name: Optional[str] = None
    matched_template_palette: Optional[List[str]] = None
    message: str



