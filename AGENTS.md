# MySlides - Engineering Guidance

## Architecture Overview

MySlides is an AI-assisted one-page PowerPoint slide studio consisting of:
1. **Template & Slide Library (`src/myslides/library`)**: SQLite storage of `.pptx` assets and individual slide records, indexed with structural hashes, visual metrics, quality scores, and archetype tags.
2. **Scraper System (`src/myslides/scrapers`)**: Pluggable scrapers (Microsoft Create, SlidesCarnival, GitHub, local folders, generic URLs) with rate limiting and attribution tracking.
3. **Design Learner (`src/myslides/analysis`)**: Analyzes slide components (visuals, layout, typography, contrast, alignment) to score effectiveness and synthesize corporate `design_rules.json`.
4. **Generation & Revision Pipeline (`src/myslides/generation`)**: Prompt -> Intent Spec -> Exemplar Retrieval -> Composer -> Blueprint Validation -> python-pptx Builder -> Iterative Revision loop.
5. **Preview Rendering (`src/myslides/rendering`)**: High-fidelity Windows PowerPoint COM automation via `pywin32` with cross-platform mock fallback.
6. **Web API & Frontend (`src/myslides/web` & `frontend/`)**: FastAPI backend + React/Vite/TS frontend.

## Verification Commands

- Python Tests: `python -m pytest tests`
- Frontend Build: `npm.cmd --prefix frontend run build`
- Frontend Tests: `npm.cmd --prefix frontend test`
- Seed Library: `python scripts/seed_library.py`
- Run App: `run_app.bat` or `python -m uvicorn myslides.web.app:create_app --port 8000 --factory`

## Clean Code & Project Rules
- Follow Robert C. Martin Clean Code principles: single responsibility, intention-revealing names, explicit error boundaries.
- On Windows PowerShell, always use `npm.cmd` instead of `npm`.
- Never commit `.env` or sensitive corporate credentials.
