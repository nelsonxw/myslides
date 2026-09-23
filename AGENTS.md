# MySlides - Engineering Guidance

## Architecture Overview

MySlides is an AI-powered slide builder that ingests PowerPoint presentations, catalogs slide templates, and generates new slides from natural language prompts. The system consists of:

1. **Ingestion Pipeline** (`src/myslides/ingestion`): PPTX parsing, slide classification, template extraction, and embedding generation
2. **Storage Layer** (`src/myslides/storage`): Firebase Storage integration for PPTX files and thumbnails
3. **Database Layer** (`src/myslides/database`): SQLite database for collections, templates, and generation requests
4. **Embedding System** (`src/myslides/ingestion/embedding_generator.py`): ChromaDB for semantic and visual embeddings
5. **Generation Engine** (To be implemented): Template-based slide generation using python-pptx
6. **LLM Integration** (To be implemented): Prompt parsing and intent extraction
7. **Web API & Frontend** (To be implemented): FastAPI backend + React frontend

## Verification Commands

- Python Tests: `python run_tests.py` or `python -m pytest tests/ -v`
- Install Dependencies: `pip install -r requirements.txt`
- Run Backend API: `$env:PYTHONPATH="src"; python -m uvicorn myslides.api.main:app --host 0.0.0.0 --port 8000`
- Run Frontend UI: `cd frontend; npm.cmd run dev`
- Build Frontend: `cd frontend; npm.cmd run build`

## Clean Code & Project Rules

- Follow Robert C. Martin Clean Code principles: single responsibility, intention-revealing names, explicit error boundaries
- On Windows PowerShell, always use `npm.cmd` instead of `npm` (when frontend is added)
- Never commit `.env` or sensitive credentials
- Use type hints for all function signatures
- Write comprehensive tests for all modules before proceeding to next module
- Follow the MVP scope defined in requirements.md for initial implementation

## Development Priorities & Completion Status

1. **Module 1 (COMPLETED)**: Ingestion Pipeline
   - PPTX parsing with python-pptx ✅
   - Slide classification (heuristic-based) ✅
   - Template extraction and storage ✅
   - Visual/semantic embedding generation ✅
   - Comprehensive tests ✅

2. **Module 4 (COMPLETED)**: Generation Engine
   - Template-based slide assembly ✅
   - Chart generation (bar, pie, line) ✅
   - Diagram generation (process, timeline) ✅
   - Style inheritance ✅
   - PPTX export ✅

3. **Module 2 (COMPLETED)**: Prompt Interpretation Engine (LLM Integration)
   - Natural language prompt parsing with Dell Dev GenAI & OpenAI ✅
   - Multi-slide deck planning ✅
   - Contextual follow-up conversation manager ✅

4. **Module 3 (COMPLETED)**: Template Matching & Suggestion
   - ChromaDB vector search ✅
   - Template ranking strategies & filters ✅
   - Adaptive element count matching ✅

5. **Module 5 (COMPLETED - MVP)**: User Interface
   - FastAPI REST API backend (`myslides.api.main`) ✅
   - Upload interface component (FR-5.1) ✅
   - Prompt interface component (FR-5.2) ✅
   - Suggestion & preview panel (FR-5.3) ✅
   - React + Vite web client ✅

## Module 1 Implementation Details

### PPTX Parser
- Extracts comprehensive slide information: shapes, charts, tables, images, text, styling
- Supports layout type detection and complexity scoring
- Handles positioning data in EMUs (English Metric Units)

### Slide Classifier
- Heuristic-based classification into 15+ categories
- Tag generation for template matching
- Pattern recognition for common slide types

### Template Extractor
- Creates structured template records with element manifests
- Extracts placeholder maps for variable fields
- Generates natural language descriptions
- Calculates structural hashes for similarity matching

### Embedding Generator
- ChromaDB integration for vector storage
- Semantic embeddings based on slide content and structure
- Visual embeddings based on thumbnail images (MVP uses simplified features)
- Similarity search for template matching

### Database Manager
- SQLAlchemy models for collections, templates, generation requests
- CRUD operations with transaction support
- Statistics and query capabilities

### Firebase Storage Service
- Admin SDK integration with service account authentication
- Upload/download for PPTX files and thumbnails
- Collection management and file operations
- SSL configuration for network environments

## Testing Strategy

- Unit tests for each component with mocked dependencies
- Integration tests for pipeline workflows
- Test coverage for all major code paths
- Error handling and edge case testing
