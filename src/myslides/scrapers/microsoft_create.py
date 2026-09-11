"""
Microsoft Create PowerPoint templates scraper.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable
import httpx
from bs4 import BeautifulSoup

from myslides.scrapers.base import ScrapedItem


class MicrosoftCreateScraper:
    def __init__(self, source_id: int, url: str = "https://create.microsoft.com/en-us/templates/powerpoint"):
        self.source_id = source_id
        self.url = url
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

    def discover(self, limit: int = 10) -> Iterable[ScrapedItem]:
        items = []
        try:
            with httpx.Client(headers=self.headers, timeout=15.0, follow_redirects=True) as client:
                resp = client.get(self.url)
                if resp.status_code != 200:
                    return items
                
                soup = BeautifulSoup(resp.text, "html.parser")
                # Look for template cards
                cards = soup.find_all("a", href=re.compile(r"/template/"))
                seen = set()
                
                for c in cards:
                    href = c.get("href")
                    if not href or href in seen:
                        continue
                    seen.add(href)
                    full_url = href if href.startswith("http") else f"https://create.microsoft.com{href}"
                    title = c.get_text(strip=True) or full_url.split("/")[-1].replace("-", " ").title()
                    
                    items.append(
                        ScrapedItem(
                            source_id=self.source_id,
                            title=title,
                            url_or_path=full_url,
                            license="Microsoft Free Template Terms",
                            attribution="Microsoft Create",
                            author="Microsoft",
                        )
                    )
                    if len(items) >= limit:
                        break
        except Exception as e:
            print(f"Microsoft Create discovery: {e}")
        return items

    def fetch(self, item: ScrapedItem, dest_dir: Path) -> Path | None:
        # Microsoft Create uses dynamic React hydration / direct download endpoints
        # In case direct download requires browser automation, we support graceful fallback
        return None
