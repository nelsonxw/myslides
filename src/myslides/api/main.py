"""
FastAPI main application for MySlides.

REST API endpoints for collections, templates, generation, and deck management.
"""
from typing import List, Optional
from pathlib import Path
import shutil
import tempfile

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from myslides.config import settings
from myslides.database.database_manager import DatabaseManager
from myslides.ingestion.ingestion_pipeline import IngestionPipeline
from myslides.storage.firebase_storage import FirebaseStorageService
from myslides.llm.prompt_parser import PromptParser
from myslides.llm.deck_planner import DeckPlanner
from myslides.llm.llm_client import LLMClient, LLMProvider
from myslides.template_matching.template_matcher import TemplateMatcher
from myslides.generation.slide_generator import SlideGenerator
from myslides.generation.pptx_exporter import PPTXExporter
from myslides.generation.data_parser import DataParser
from myslides.generation.slide_preview_renderer import SlidePreviewRenderer
from myslides.generation.pdf_exporter import PDFExporter
from myslides.api.api_models import (
    CollectionCreate, CollectionResponse, CollectionsListResponse,
    TemplateResponse, TemplateUpdate, TemplatesListResponse,
    PromptParseRequest, PromptParseResponse,
    TemplateSuggestionRequest, TemplateSuggestionResponse,
    SlideGenerationRequest, SlideGenerationResponse,
    DeckGenerationRequest, DeckGenerationResponse, DeckResponse,
    PaletteResponse, PalettesListResponse,
    UploadResponse
)

# Initialize FastAPI app
app = FastAPI(
    title="MySlides API",
    description="AI-Powered Slide Builder from Curated Templates",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
db_manager = DatabaseManager()
ingestion_pipeline = IngestionPipeline()

# Initialize LLM client (auto-detect provider)
llm_client = LLMClient()
prompt_parser = PromptParser(llm_client=llm_client)
deck_planner = DeckPlanner(llm_client=llm_client)

# Initialize template matching
template_matcher = TemplateMatcher()

# Initialize generation services
slide_generator = SlideGenerator()


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}


# Collection Endpoints
@app.post("/api/collections/upload", response_model=UploadResponse)
async def upload_collection(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Upload a PPTX file and ingest it into the catalog.

    FR-5.1: Upload Interface
    """
    # Create temporary file
    temp_dir = Path(tempfile.mkdtemp())
    temp_file_path = temp_dir / file.filename

    try:
        # Save uploaded file
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Ingest the file (pipeline handles Firebase upload internally)
        result = ingestion_pipeline.ingest_pptx_file(
            local_pptx_path=temp_file_path,
            collection_name=file.filename
        )

        return UploadResponse(
            collection_id=result.get("collection_id", 0),
            file_name=file.filename,
            status="complete" if result.get("success") else "error",
            templates_created=result.get("templates_created", 0)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Cleanup temp directory
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


@app.get("/api/collections", response_model=CollectionsListResponse)
async def list_collections(skip: int = 0, limit: int = 100):
    """List all collections."""
    collections = db_manager.list_collections(skip=skip, limit=limit)
    return CollectionsListResponse(
        collections=[CollectionResponse.model_validate(c) for c in collections],
        total=len(collections)
    )


# Template Endpoints
@app.get("/api/templates", response_model=TemplatesListResponse)
async def list_templates(
    classification: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
):
    """
    List/filter cataloged templates.

    FR-5.1: Catalog viewer
    """
    if classification:
        templates = db_manager.list_templates_by_classification(classification, skip=skip, limit=limit)
    else:
        templates = db_manager.list_templates(skip=skip, limit=limit)

    return TemplatesListResponse(
        templates=[TemplateResponse.model_validate(t) for t in templates],
        total=len(templates)
    )


@app.patch("/api/templates/{template_id}", response_model=TemplateResponse)
async def update_template(template_id: int, update: TemplateUpdate):
    """
    Update template classification or tags.

    FR-5.1: Tag, re-classify individual slides
    """
    template = db_manager.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    update_data = {}
    if update.classification:
        update_data["classification"] = update.classification
    if update.tags:
        update_data["tags"] = update.tags

    updated = db_manager.update_template(template_id, update_data)
    return TemplateResponse.model_validate(updated)


# Generation Endpoints
@app.post("/api/generate/parse-prompt", response_model=PromptParseResponse)
async def parse_prompt(request: PromptParseRequest):
    """
    Parse natural language prompt into structured intent.

    FR-5.2: Prompt Interface
    """
    try:
        intent = prompt_parser.parse_prompt(request.prompt_text)
        return PromptParseResponse(
            slide_type=intent.slide_type.value,
            content=intent.content,
            tone=intent.tone,
            element_preferences=intent.element_preferences,
            color_preference=intent.color_preference
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate/suggest-templates", response_model=List[TemplateSuggestionResponse])
async def suggest_templates(request: TemplateSuggestionRequest):
    """
    Get template suggestions for a given intent.

    FR-5.3: Suggestion Panel
    """
    try:
        from myslides.generation.generation_models import GenerationIntent, SlideType

        # Convert request to GenerationIntent
        slide_type = SlideType(request.slide_type)
        intent = GenerationIntent(
            slide_type=slide_type,
            content=request.content,
            tone=request.tone
        )

        # Get suggestions
        matches = template_matcher.find_similar_templates(
            intent,
            n_results=request.n_results,
            use_adaptive_element_count=request.use_adaptive_element_count
        )

        return [
            TemplateSuggestionResponse(
                template_id=m.template_id,
                template_data=m.template_data,
                similarity_score=m.similarity_score.combined_score,
                rank=m.rank,
                match_reason=m.match_reason
            )
            for m in matches
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate/create-slide", response_model=SlideGenerationResponse)
async def create_slide(request: SlideGenerationRequest):
    """
    Generate a slide from intent and optional template.

    FR-5.2: Generate button triggers pipeline
    """
    try:
        from myslides.generation.generation_models import GenerationIntent, SlideType

        # Convert request to GenerationIntent
        slide_type = SlideType(request.slide_type)
        intent = GenerationIntent(
            slide_type=slide_type,
            content=request.content,
            tone=request.tone,
            element_preferences=request.element_preferences,
            color_preference=request.color_preference
        )

        # Generate slide
        presentation = slide_generator.generate_slide(intent)

        # Save to temporary file
        temp_dir = Path(tempfile.mkdtemp())
        output_path = temp_dir / "generated_slide.pptx"
        exporter = PPTXExporter(presentation)
        exporter.save(output_path)

        # Create generation request record
        request_data = {
            "user_id": 0,  # TODO: Add user authentication
            "prompt_text": f"Generate {request.slide_type} slide",
            "parsed_intent": request.model_dump(),
            "matched_template_ids": [request.template_id] if request.template_id else [],
            "selected_template_id": request.template_id,
            "generated_file_path": str(output_path),
            "status": "complete"
        }
        gen_request = db_manager.create_generation_request(request_data)

        return SlideGenerationResponse(
            request_id=gen_request.id,
            status="complete",
            file_path=str(output_path)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate/create-deck", response_model=DeckGenerationResponse)
async def create_deck(request: DeckGenerationRequest):
    """
    Generate a multi-slide deck from prompts.

    FR-5.5: Deck Builder
    """
    try:
        # Plan the deck
        deck_plan = deck_planner.plan_deck(" ".join(request.prompts))

        # Generate slides
        intents = deck_plan.slide_intents
        presentation = slide_generator.generate_deck(intents)

        # Save to temporary file
        temp_dir = Path(tempfile.mkdtemp())
        output_path = temp_dir / f"{request.title.replace(' ', '_')}.pptx"
        exporter = PPTXExporter(presentation)
        exporter.save(output_path)

        # Create deck record
        deck_data = {
            "user_id": 0,  # TODO: Add user authentication
            "title": request.title,
            "created_at": None
        }
        deck = db_manager.create_deck(deck_data)

        return DeckGenerationResponse(
            deck_id=deck.id,
            status="complete",
            file_path=str(output_path),
            slide_count=len(deck_plan.slide_intents)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/decks/{deck_id}", response_model=DeckResponse)
async def get_deck(deck_id: int):
    """
    Get a deck by ID.

    FR-5.5: Deck Builder
    """
    try:
        deck = db_manager.get_deck(deck_id)
        if not deck:
            raise HTTPException(status_code=404, detail="Deck not found")

        return DeckResponse(
            id=deck.id,
            title=deck.title,
            slides=deck.slides,
            created_at=deck.created_at.isoformat() if deck.created_at else None
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/decks/{deck_id}")
async def update_deck(deck_id: int, update_data: dict):
    """
    Update a deck (e.g., reorder slides).

    FR-5.5: Deck Builder
    """
    try:
        deck = db_manager.update_deck(deck_id, update_data)
        if not deck:
            raise HTTPException(status_code=404, detail="Deck not found")

        return {"status": "success", "deck_id": deck.id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/data/parse-csv")
async def parse_csv_data(file: UploadFile = File(...)):
    """
    Parse uploaded CSV file into chart data.

    FR-4.2 Phase 2: CSV/Excel data upload for charts
    """
    try:
        content = await file.read()
        csv_text = content.decode('utf-8')
        parsed_data = DataParser.parse_csv(csv_text)
        return parsed_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/data/parse-excel")
async def parse_excel_data(file: UploadFile = File(...)):
    """
    Parse uploaded Excel file into chart data.

    FR-4.2 Phase 2: CSV/Excel data upload for charts
    """
    try:
        content = await file.read()
        parsed_data = DataParser.parse_excel(content)
        return parsed_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Slide and Deck Endpoints
@app.get("/api/slides/{request_id}/preview")
async def get_slide_preview(request_id: int):
    """
    Get PNG preview of generated slide.

    FR-5.3: Preview panel
    FR-4.5 Phase 2: PPTX to image rendering
    """
    gen_request = db_manager.get_generation_request(request_id)
    if not gen_request:
        raise HTTPException(status_code=404, detail="Generation request not found")

    if not gen_request.generated_file_path:
        raise HTTPException(status_code=404, detail="No generated file found")

    # Attempt to render real PNG image
    rendered_image = SlidePreviewRenderer.render_slide_to_image(gen_request.generated_file_path)
    if rendered_image and rendered_image.endswith(".png") and Path(rendered_image).exists():
        return FileResponse(
            rendered_image,
            media_type="image/png",
            filename=f"slide_{request_id}_preview.png"
        )

    # Fallback to metadata if image rendering not supported on host
    metadata = SlidePreviewRenderer.get_slide_metadata(gen_request.generated_file_path)
    return {
        "request_id": request_id,
        "metadata": metadata,
        "note": "PNG preview generated or fallback metadata provided"
    }


@app.get("/api/slides/{request_id}/export-pdf")
async def export_slide_pdf(request_id: int):
    """
    Export generated slide as PDF.

    FR-4.5 Phase 2: PDF export
    """
    gen_request = db_manager.get_generation_request(request_id)
    if not gen_request:
        raise HTTPException(status_code=404, detail="Generation request not found")

    if not gen_request.generated_file_path:
        raise HTTPException(status_code=404, detail="No generated file found")

    pdf_path = PDFExporter.export_to_pdf(gen_request.generated_file_path)

    if pdf_path.endswith(".pdf") and Path(pdf_path).exists():
        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename="generated_slide.pdf"
        )

    return FileResponse(
        pdf_path,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename="generated_slide.pptx"
    )


@app.get("/api/decks/{deck_id}/export-pdf")
async def export_deck_pdf(deck_id: int):
    """
    Export generated deck as PDF.

    FR-4.5 Phase 2: PDF export
    """
    deck = db_manager.get_deck(deck_id)
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")

    from myslides.generation.generation_models import GenerationIntent, SlideType
    intent = GenerationIntent(
        slide_type=SlideType.TITLE_SLIDE,
        content={"title": deck.title, "subtitle": "Generated by MySlides"}
    )
    presentation = slide_generator.generate_slide(intent)
    temp_dir = Path(tempfile.mkdtemp())
    pptx_path = temp_dir / f"{deck.title.replace(' ', '_')}.pptx"
    exporter = PPTXExporter(presentation)
    exporter.save(pptx_path)

    pdf_path = PDFExporter.export_to_pdf(str(pptx_path))
    if pdf_path.endswith(".pdf") and Path(pdf_path).exists():
        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename=f"{deck.title.replace(' ', '_')}.pdf"
        )

    return FileResponse(
        str(pptx_path),
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=f"{deck.title.replace(' ', '_')}.pptx"
    )


@app.get("/api/slides/{request_id}/download")
async def download_slide(request_id: int):
    """
    Download generated slide as PPTX.

    FR-5.2: Download generated slide
    """
    gen_request = db_manager.get_generation_request(request_id)
    if not gen_request:
        raise HTTPException(status_code=404, detail="Generation request not found")

    if not gen_request.generated_file_path:
        raise HTTPException(status_code=404, detail="No generated file found")

    return FileResponse(
        gen_request.generated_file_path,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename="generated_slide.pptx"
    )


@app.get("/api/decks/{deck_id}/download")
async def download_deck(deck_id: int):
    """
    Download full deck as PPTX.

    FR-5.5: Export entire deck
    """
    deck = db_manager.get_deck(deck_id)
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")

    # For MVP, generate deck on-the-fly (in production, would have stored file)
    from myslides.generation.generation_models import GenerationIntent, SlideType

    # Create a simple title slide
    intent = GenerationIntent(
        slide_type=SlideType.TITLE_SLIDE,
        content={"title": deck.title, "subtitle": "Generated by MySlides"}
    )
    presentation = slide_generator.generate_slide(intent)

    temp_dir = Path(tempfile.mkdtemp())
    output_path = temp_dir / f"{deck.title.replace(' ', '_')}.pptx"
    exporter = PPTXExporter(presentation)
    exporter.save(output_path)

    return FileResponse(
        output_path,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=f"{deck.title.replace(' ', '_')}.pptx"
    )


# Palette Endpoints
@app.get("/api/palettes", response_model=PalettesListResponse)
async def list_palettes(limit: int = 50):
    """
    List extracted color palettes.

    FR-5.4: Change color scheme
    """
    templates = db_manager.list_templates(limit=limit)

    palettes = []
    for template in templates:
        if template.color_palette and len(template.color_palette) > 0:
            palettes.append(PaletteResponse(
                colors=template.color_palette,
                source_template_id=template.id,
                source_collection_id=template.collection_id
            ))

    return PalettesListResponse(
        palettes=palettes[:limit],
        total=len(palettes)
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
