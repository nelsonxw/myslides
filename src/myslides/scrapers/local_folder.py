"""
Local folder scraper: ingests .pptx files from a local path.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Iterable

from myslides.scrapers.base import ScrapedItem


class LocalFolderScraper:
    def __init__(self, source_id: int, folder_path: Path | str, license_str: str = "Internal", attribution: str = ""):
        self.source_id = source_id
        self.folder_path = Path(folder_path).resolve()
        self.license_str = license_str
        self.attribution = attribution

    def discover(self, limit: int = 100) -> Iterable[ScrapedItem]:
        if not self.folder_path.exists():
            return []
        
        items = []
        # Case 1: Target path is a direct .pptx file
        if self.folder_path.is_file() and self.folder_path.suffix.lower() == ".pptx":
            if not self.folder_path.name.startswith("~$"):
                items.append(
                    ScrapedItem(
                        source_id=self.source_id,
                        title=self.folder_path.stem,
                        url_or_path=str(self.folder_path),
                        local_path=self.folder_path,
                        license=self.license_str,
                        attribution=self.attribution or f"Local file: {self.folder_path.name}",
                        author="Local",
                    )
                )
            return items

        # Case 2: Target path is a directory containing .pptx files
        count = 0
        for p in self.folder_path.rglob("*.pptx"):
            if p.name.startswith("~$"):  # skip PowerPoint temp lock files
                continue
            items.append(
                ScrapedItem(
                    source_id=self.source_id,
                    title=p.stem,
                    url_or_path=str(p),
                    local_path=p,
                    license=self.license_str,
                    attribution=self.attribution or f"Local file from {self.folder_path.name}",
                    author="Local",
                )
            )
            count += 1
            if count >= limit:
                break
        return items

    def fetch(self, item: ScrapedItem, dest_dir: Path) -> Path | None:
        if not item.local_path or not item.local_path.exists():
            return None
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_file = dest_dir / item.local_path.name
        shutil.copy2(item.local_path, dest_file)
        return dest_file
