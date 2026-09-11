"""
SlidesCarnival scraper: crawls free Creative Commons PowerPoint templates.
"""
from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Iterable
import httpx
from bs4 import BeautifulSoup

from myslides.scrapers.base import ScrapedItem


class SlidesCarnivalScraper:
    def __init__(self, source_id: int, base_url: str = "https://www.slidescarnival.com/category/free-templates"):
        self.source_id = source_id
        self.base_url = base_url
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

    def discover(self, limit: int = 10) -> Iterable[ScrapedItem]:
        items = []
        try:
            with httpx.Client(headers=self.headers, timeout=15.0, follow_redirects=True, verify=False) as client:
                resp = client.get(self.base_url)
                if resp.status_code != 200:
                    print(f"SlidesCarnival HTTP {resp.status_code}")
                    return items
                
                # Detect corporate proxy blocking
                if "To keep Dell's data secure" in resp.text or "Access Blocked" in resp.text:
                    raise RuntimeError("Site is blocked by corporate network policy (Category: shareware/freeware). Use GitHub Open Source, direct URLs, or local template folders instead.")

                soup = BeautifulSoup(resp.text, "html.parser")
                # Find template article links
                links = soup.find_all("a", href=re.compile(r"slidescarnival\.com/[a-z0-9\-]+(?:-free-presentation-template|-presentation-template)?/?$"))
                seen = set()
                
                for a in links:
                    url = a.get("href")
                    if not url or url in seen or "category" in url or "tag" in url or "about" in url:
                        continue
                    seen.add(url)
                    title = a.get_text(strip=True) or url.rstrip("/").split("/")[-1].replace("-free-presentation-template", "").replace("-", " ").title()
                    if not title or len(title) < 3:
                        continue

                    items.append(
                        ScrapedItem(
                            source_id=self.source_id,
                            title=title,
                            url_or_path=url,
                            license="CC BY 4.0",
                            attribution="SlidesCarnival (Free Presentation Templates)",
                            author="SlidesCarnival",
                        )
                    )
                    if len(items) >= limit:
                        break
        except Exception as e:
            print(f"SlidesCarnival discovery error: {e}")
        return items

    def fetch(self, item: ScrapedItem, dest_dir: Path) -> Path | None:
        """Download PPTX link from the template page."""
        try:
            with httpx.Client(headers=self.headers, timeout=25.0, follow_redirects=True, verify=False) as client:
                page_resp = client.get(item.url_or_path)
                if page_resp.status_code != 200:
                    return None
                
                soup = BeautifulSoup(page_resp.text, "html.parser")
                # Find download button/link for PowerPoint (.pptx)
                dl_link = soup.find("a", href=re.compile(r"\.pptx(?:\?.*)?$|\/download\/|\/pptx", re.IGNORECASE))
                if not dl_link:
                    dl_link = soup.find("a", class_=re.compile(r"download|btn-download|powerpoint", re.IGNORECASE))
                
                if not dl_link or not dl_link.get("href"):
                    return None
                
                pptx_url = dl_link.get("href")
                dl_resp = client.get(pptx_url)
                if dl_resp.status_code == 200 and len(dl_resp.content) > 1000:
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', item.title) + ".pptx"
                    dest_file = dest_dir / safe_name
                    dest_file.write_bytes(dl_resp.content)
                    return dest_file
        except Exception as e:
            print(f"Failed to fetch {item.title}: {e}")
        return None
