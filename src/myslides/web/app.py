"""
FastAPI application factory and static frontend mounting.
"""
from __future__ import annotations

import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from myslides.config import settings
from myslides.library.repository import get_standalone_session, init_db
from myslides.scrapers.defaults import seed_default_sources
from myslides.web.routers import generate, library, sources


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings.ensure_directories()
    init_db()

    # Pre-populate default verified sources
    db_s = get_standalone_session()
    try:
        seed_default_sources(db_s)
    finally:
        db_s.close()

    app = FastAPI(
        title="MySlides AI",
        description="PowerPoint template library, design learner, and one-page slide generator",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API Routers
    app.include_router(sources.router)
    app.include_router(library.router)
    app.include_router(generate.router)

    # Mount compiled React frontend if exists
    frontend_dist = Path(__file__).resolve().parents[3] / "frontend" / "dist"
    if frontend_dist.exists():
        app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")

    return app


def run():
    import uvicorn
    uvicorn.run("myslides.web.app:create_app", host="0.0.0.0", port=8000, reload=True, factory=True)


if __name__ == "__main__":
    run()
