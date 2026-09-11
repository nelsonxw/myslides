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
CANCEL_FLAGS: set[int] = set()


def cancel_source_scrape(source_id: int) -> None:
    """Request cancellation for a running scraper task."""
    CANCEL_FLAGS.add(source_id)


def is_scrape_cancelled(source_id: int) -> bool:
    return source_id in CANCEL_FLAGS


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
    CANCEL_FLAGS.discard(source_id)

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
                if is_scrape_cancelled(source_id):
                    raise InterruptedError("Scrape cancelled by user.")

                deck_num = i + 1
                SCRAPER_PROGRESS[source_id]["current_file"] = f"Ingesting: {item.title}"

                def _on_slide(current_slide: int, total_slides: int):
                    # Compute granular sub-deck percentage: completed decks + fraction of current deck slides
                    sub_progress = (deck_num - 1) + (current_slide / max(total_slides, 1))
                    SCRAPER_PROGRESS[source_id]["current"] = round(sub_progress, 2)
                    SCRAPER_PROGRESS[source_id]["current_file"] = f"Ingesting: {item.title} (slide {current_slide}/{total_slides})"

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
                            on_slide_progress=_on_slide,
                            check_cancelled=lambda: is_scrape_cancelled(source_id),
                        )
                        if asset:
                            ingested_count += 1
                    SCRAPER_PROGRESS[source_id]["current"] = deck_num
                    # Polite rate limit delay between web downloads
                    time.sleep(0.3)
                except InterruptedError:
                    raise
                except Exception as ex:
                    errors.append(f"Failed {item.title}: {ex}")

        # Update source status
        source.last_scraped_at = datetime.datetime.utcnow()
        if ingested_count == 0:
            source.last_status = "no_slides_found"
            if not source.last_error:
                source.last_error = f"Discovered {total_items} item(s) but no valid new slides were ingested." if total_items > 0 else "No .pptx presentations or templates found on this source."
        elif errors:
            source.last_status = "partial"
            source.last_error = "\n".join(errors[:5])
        else:
            source.last_status = "success"
            source.last_error = None
        db_session.commit()

        # Update knowledge rules after new ingestion
        if ingested_count > 0:
            build_knowledge_rules(db_session)

        SCRAPER_PROGRESS[source_id] = {
            "status": "completed",
            "current": total_items,
            "total": total_items,
            "current_file": f"Ingested {ingested_count} slides." if ingested_count > 0 else "No slides ingested.",
            "last_result": f"Ingested {ingested_count} templates ({len(errors)} errors)",
        }
        CANCEL_FLAGS.discard(source_id)

        return {
            "status": source.last_status,
            "discovered": len(discovered),
            "ingested": ingested_count,
            "errors": errors,
        }

    except Exception as e:
        db_session.rollback()
        source = db_session.query(Source).filter_by(id=source_id).first()
        is_cancelled = is_scrape_cancelled(source_id) or isinstance(e, InterruptedError)
        if source:
            source.last_status = "idle" if is_cancelled else "error"
            source.last_error = None if is_cancelled else str(e)
            db_session.commit()
        SCRAPER_PROGRESS[source_id] = {
            "status": "idle" if is_cancelled else "error",
            "current": 0,
            "total": 0,
            "current_file": "Cancelled by user" if is_cancelled else f"Error: {str(e)}",
            "last_result": "Stopped" if is_cancelled else f"Failed: {str(e)}",
        }
        CANCEL_FLAGS.discard(source_id)
        return {"status": "cancelled" if is_cancelled else "error", "message": str(e), "ingested": ingested_count}
