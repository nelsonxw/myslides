"""
Scraper execution runner: orchestrates discovery, download, ingestion, scoring, and knowledge synthesis.
"""
from __future__ import annotations

import datetime
import tempfile
import time
from pathlib import Path
from typing import Any
from sqlalchemy.orm import Session

from myslides.analysis.knowledge import build_knowledge_rules
from myslides.config import settings
from myslides.library.ingest import ingest_pptx_file
from myslides.library.models import Source
from myslides.llm.provider import LLMProvider
from myslides.scrapers.registry import get_scraper_for_source

# In-memory progress tracking: {source_id: {"status": str, "current": int, "total": int, "current_file": str, "last_result": str}}
SCRAPER_PROGRESS: dict[int, dict[str, Any]] = {}


def get_source_progress(source_id: int) -> dict[str, Any]:
    return SCRAPER_PROGRESS.get(source_id, {
        "status": "idle",
        "current": 0,
        "total": 0,
        "current_file": "",
        "last_result": "",
    })


def run_source_scrape(
    source_id: int,
    db_session: Session,
    limit: int = 10,
    llm: LLMProvider | None = None,
    renderer_func: Any = None,
) -> dict[str, Any]:
    """Run discovery and ingestion pipeline for a single source."""
    source = db_session.query(Source).filter_by(id=source_id).first()
    if not source:
        return {"status": "error", "message": f"Source {source_id} not found", "ingested": 0}

    source.last_status = "running"
    source.last_error = None
    db_session.commit()

    SCRAPER_PROGRESS[source_id] = {
        "status": "discovering",
        "current": 0,
        "total": 0,
        "current_file": "Discovering templates...",
        "last_result": "",
    }

    ingested_count = 0
    errors = []

    try:
        scraper = get_scraper_for_source(source)
        discovered = list(scraper.discover(limit=limit))
        total_items = len(discovered)
        
        SCRAPER_PROGRESS[source_id]["total"] = total_items
        SCRAPER_PROGRESS[source_id]["status"] = "ingesting"

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            for i, item in enumerate(discovered):
                SCRAPER_PROGRESS[source_id]["current"] = i + 1
                SCRAPER_PROGRESS[source_id]["current_file"] = f"Ingesting: {item.title}"
                try:
                    local_pptx = scraper.fetch(item, temp_path)
                    if local_pptx and local_pptx.exists():
                        asset = ingest_pptx_file(
                            local_pptx,
                            db_session,
                            source_id=source.id,
                            license_str=item.license,
                            attribution=item.attribution,
                            author=item.author,
                            llm=llm,
                            renderer_func=renderer_func,
                        )
                        if asset:
                            ingested_count += 1
                    # Polite rate limit delay between web downloads
                    time.sleep(0.5)
                except Exception as ex:
                    errors.append(f"Failed {item.title}: {ex}")

        # Update source status
        source.last_scraped_at = datetime.datetime.utcnow()
        source.last_status = "success" if not errors else "partial"
        source.last_error = "\n".join(errors[:5]) if errors else None
        db_session.commit()

        # Update knowledge rules after new ingestion
        if ingested_count > 0:
            build_knowledge_rules(db_session)

        SCRAPER_PROGRESS[source_id] = {
            "status": "completed",
            "current": total_items,
            "total": total_items,
            "current_file": f"Completed! Ingested {ingested_count} new slides.",
            "last_result": f"Ingested {ingested_count} templates ({len(errors)} errors)",
        }

        return {
            "status": source.last_status,
            "discovered": len(discovered),
            "ingested": ingested_count,
            "errors": errors,
        }

    except Exception as e:
        db_session.rollback()
        source = db_session.query(Source).filter_by(id=source_id).first()
        if source:
            source.last_status = "error"
            source.last_error = str(e)
            db_session.commit()
        SCRAPER_PROGRESS[source_id] = {
            "status": "error",
            "current": 0,
            "total": 0,
            "current_file": f"Error: {str(e)}",
            "last_result": f"Failed: {str(e)}",
        }
        return {"status": "error", "message": str(e), "ingested": ingested_count}
