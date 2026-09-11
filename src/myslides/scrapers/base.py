"""
Scraper protocol and base classes.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Protocol


@dataclass
class ScrapedItem:
    """A discovered PowerPoint asset."""
    source_id: int
    title: str
    url_or_path: str
    local_path: Path | None = None
    license: str = "Unknown"
    attribution: str = ""
    author: str = ""


class SourceScraper(Protocol):
    """Protocol for all scrapers."""

    def discover(self, limit: int = 50) -> Iterable[ScrapedItem]:
        """Discover .pptx files from the source."""
        ...

    def fetch(self, item: ScrapedItem, dest_dir: Path) -> Path | None:
        """Download or copy the asset to dest_dir. Returns local Path."""
        ...
