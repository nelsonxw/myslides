"""
Sources management router: CRUD for template sources and trigger scraping.
"""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from myslides.library.models import Source
from myslides.library.repository import get_session, get_standalone_session
from myslides.llm.factory import get_llm_provider
from myslides.rendering.powerpoint_com import get_default_renderer
from myslides.scrapers.runner import get_source_progress, run_source_scrape
from myslides.web.schemas import CreateSourceRequest, SourceResponse

router = APIRouter(prefix="/api/sources", tags=["sources"])


@router.get("", response_model=list[SourceResponse])
def list_sources(db: Session = Depends(get_session)):
    sources = db.query(Source).all()
    return [
        SourceResponse(
            id=s.id,
            name=s.name,
            kind=s.kind,
            url_or_path=s.url_or_path,
            license=s.license or "Unknown",
            attribution=s.attribution or "",
            enabled=s.enabled,
            last_scraped_at=s.last_scraped_at.isoformat() if s.last_scraped_at else None,
            last_status=s.last_status,
            last_error=s.last_error,
        )
        for s in sources
    ]


@router.post("", response_model=SourceResponse)
def add_source(payload: CreateSourceRequest, db: Session = Depends(get_session)):
    source = Source(
        name=payload.name,
        kind=payload.kind,
        url_or_path=payload.url_or_path,
        license=payload.license,
        attribution=payload.attribution,
        enabled=True,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return SourceResponse(
        id=source.id,
        name=source.name,
        kind=source.kind,
        url_or_path=source.url_or_path,
        license=source.license or "Unknown",
        attribution=source.attribution or "",
        enabled=source.enabled,
        last_status=source.last_status,
    )


@router.delete("/{source_id}")
def delete_source(source_id: int, db: Session = Depends(get_session)):
    source = db.query(Source).filter_by(id=source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    db.delete(source)
    db.commit()
    return {"status": "deleted", "id": source_id}


@router.post("/{source_id}/run")
def trigger_scrape(source_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_session)):
    source = db.query(Source).filter_by(id=source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    def _task():
        db_s = get_standalone_session()
        try:
            llm = get_llm_provider()
            renderer = get_default_renderer()
            run_source_scrape(source_id, db_s, limit=10, llm=llm, renderer_func=renderer.render_slide)
        finally:
            db_s.close()

    background_tasks.add_task(_task)
    return {"status": "started", "source_id": source_id}


@router.get("/{source_id}/progress")
def get_scrape_progress(source_id: int):
    """Poll the real-time progress of an active scraper."""
    return get_source_progress(source_id)
