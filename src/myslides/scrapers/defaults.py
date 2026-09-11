"""
Seed initial default template sources in the database.
"""
from __future__ import annotations

from pathlib import Path
from sqlalchemy.orm import Session
from myslides.library.models import Source


def seed_default_sources(db: Session) -> None:
    """Ensure standard local and online sources exist in the database."""
    workspace_root = Path(__file__).resolve().parents[3]
    ppt_templates = workspace_root / "ppt" / "templates"
    ppt_output = workspace_root / "ppt" / "output"

    defaults = [
        {
            "name": "Dell Official Templates",
            "kind": "local_folder",
            "url_or_path": str(ppt_templates.resolve()) if ppt_templates.exists() else "",
            "license": "Dell Internal",
            "attribution": "Dell Technologies Official Brand",
        },
        {
            "name": "Dell Executive Generated Decks",
            "kind": "local_folder",
            "url_or_path": str(ppt_output.resolve()) if ppt_output.exists() else "",
            "license": "Dell Internal",
            "attribution": "Dell Technologies Generated AI Decks",
        },
    ]

    for d in defaults:
        if not d["url_or_path"]:
            continue
        exists = db.query(Source).filter_by(name=d["name"]).first()
        if not exists:
            src = Source(
                name=d["name"],
                kind=d["kind"],
                url_or_path=d["url_or_path"],
                license=d["license"],
                attribution=d["attribution"],
                enabled=True,
            )
            db.add(src)
    db.commit()
