"""
Generic URL scraper: fetches a direct .pptx URL or parses an HTML page for downloadable .pptx anchors.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin
import httpx
from bs4 import BeautifulSoup

from myslides.scrapers.base import ScrapedItem


class GenericUrlScraper:
    def __init__(self, source_id: int, target_url: str, license_str: str = "Web Resource", attribution: str = ""):
        self.source_id = source_id
        self.target_url = target_url
        self.license_str = license_str
        self.attribution = attribution or target_url
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        }

    def discover(self, limit: int = 20) -> Iterable[ScrapedItem]:
        items = []
        # Case 1: direct .pptx link
        if self.target_url.lower().endswith(".pptx"):
            name = self.target_url.split("/")[-1].replace(".pptx", "").replace("_", " ").title()
            return [
                ScrapedItem(
                    source_id=self.source_id,
                    title=name,
                    url_or_path=self.target_url,
                    license=self.license_str,
                    attribution=self.attribution,
                    author="Web",
                )
            ]

        # Case 2: Web page with .pptx links
        try:
            with httpx.Client(headers=self.headers, timeout=15.0, follow_redirects=True, verify=False) as client:
                resp = client.get(self.target_url)
                if resp.status_code != 200:
                    return items
                
                soup = BeautifulSoup(resp.text, "html.parser")
                links = soup.find_all("a", href=re.compile(r"\.pptx(?:\?.*)?$", re.IGNORECASE))
                seen = set()
                for a in links:
                    href = a.get("href")
                    full_url = urljoin(self.target_url, href)
                    if full_url in seen:
                        continue
                    seen.add(full_url)
                    title = a.get_text(strip=True) or full_url.split("/")[-1].split("?")[0].replace(".pptx", "")
                    items.append(
                        ScrapedItem(
                            source_id=self.source_id,
                            title=title,
                            url_or_path=full_url,
                            license=self.license_str,
                            attribution=self.attribution,
                            author="Web",
                        )
                    )
                    if len(items) >= limit:
                        break
        except Exception as e:
            print(f"Generic URL scraper error: {e}")
        return items

    def fetch(self, item: ScrapedItem, dest_dir: Path) -> Path | None:
        try:
            with httpx.Client(headers=self.headers, timeout=30.0, follow_redirects=True, verify=False) as client:
                resp = client.get(item.url_or_path)
                if resp.status_code == 200 and len(resp.content) > 1000:
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    clean_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', item.title) + ".pptx"
                    dest_file = dest_dir / clean_name
                    dest_file.write_bytes(resp.content)
                    return dest_file
        except Exception as e:
            print(f"Failed fetching {item.url_or_path}: {e}")
        return None
