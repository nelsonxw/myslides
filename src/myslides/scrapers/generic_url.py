"""
Generic URL scraper & site crawler: crawls site pages and sub-pages to discover and download all available .pptx presentations.
"""
from __future__ import annotations

import collections
import re
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin, urlparse
import httpx
from bs4 import BeautifulSoup

from myslides.scrapers.base import ScrapedItem


class GenericUrlScraper:
    def __init__(
        self,
        source_id: int,
        target_url: str,
        license_str: str = "Web Resource",
        attribution: str = "",
        max_crawl_pages: int = 50,
        max_depth: int = 3,
    ):
        self.source_id = source_id
        self.target_url = target_url
        self.license_str = license_str
        self.attribution = attribution or target_url
        self.max_crawl_pages = max_crawl_pages
        self.max_depth = max_depth
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

    def discover(self, limit: int = 50) -> Iterable[ScrapedItem]:
        items: list[ScrapedItem] = []
        parsed_root = urlparse(self.target_url)
        root_domain = parsed_root.netloc.lower()

        # Case 1: Direct link to a .pptx file
        if self.target_url.lower().split("?")[0].endswith(".pptx"):
            name = self.target_url.split("/")[-1].split("?")[0].replace(".pptx", "").replace("_", " ").title()
            return [
                ScrapedItem(
                    source_id=self.source_id,
                    title=name or "Presentation",
                    url_or_path=self.target_url,
                    license=self.license_str,
                    attribution=self.attribution,
                    author="Web",
                )
            ]

        # Case 2: Deep Crawler — BFS queue across internal links to find all downloadable .pptx files
        queue: collections.deque[tuple[str, int]] = collections.deque([(self.target_url, 0)])
        visited_pages: set[str] = set()
        seen_pptx_urls: set[str] = set()

        with httpx.Client(headers=self.headers, timeout=15.0, follow_redirects=True, verify=False) as client:
            while queue and len(visited_pages) < self.max_crawl_pages and len(items) < limit:
                current_url, depth = queue.popleft()
                clean_url = current_url.split("#")[0].rstrip("/")
                if clean_url in visited_pages:
                    continue
                visited_pages.add(clean_url)

                try:
                    resp = client.get(current_url)
                    if resp.status_code != 200:
                        continue

                    # If response is actually a PPTX binary attachment
                    content_type = resp.headers.get("content-type", "").lower()
                    if "presentation" in content_type or "powerpoint" in content_type:
                        if current_url not in seen_pptx_urls:
                            seen_pptx_urls.add(current_url)
                            name = current_url.split("/")[-1].split("?")[0].replace(".pptx", "") or f"Presentation_{len(items)+1}"
                            items.append(
                                ScrapedItem(
                                    source_id=self.source_id,
                                    title=name.replace("_", " ").title(),
                                    url_or_path=current_url,
                                    license=self.license_str,
                                    attribution=self.attribution,
                                    author="Web",
                                )
                            )
                        continue

                    # If HTML page, parse links
                    if "html" not in content_type and not current_url.endswith((".html", ".htm", "/")):
                        continue

                    soup = BeautifulSoup(resp.text, "html.parser")

                    for a in soup.find_all("a", href=True):
                        href = a.get("href", "").strip()
                        if not href or href.startswith(("javascript:", "mailto:", "tel:", "#")):
                            continue

                        full_url = urljoin(current_url, href)
                        parsed_href = urlparse(full_url)

                        # Check if link is a PPTX download link
                        is_pptx_link = bool(
                            re.search(r"\.pptx(?:\?.*)?$", full_url, re.IGNORECASE)
                            or "download" in full_url.lower() and "ppt" in full_url.lower()
                            or "powerpoint" in a.get("title", "").lower()
                            or "download" in a.get_text(strip=True).lower() and ("ppt" in href.lower() or "slide" in href.lower())
                        )

                        if is_pptx_link:
                            if full_url not in seen_pptx_urls:
                                seen_pptx_urls.add(full_url)
                                link_title = a.get_text(strip=True) or full_url.split("/")[-1].split("?")[0].replace(".pptx", "")
                                link_title = link_title.replace("Download", "").replace("PPTX", "").strip() or f"Template_{len(items)+1}"
                                items.append(
                                    ScrapedItem(
                                        source_id=self.source_id,
                                        title=link_title.replace("_", " ").title(),
                                        url_or_path=full_url,
                                        license=self.license_str,
                                        attribution=self.attribution,
                                        author="Web",
                                    )
                                )
                                if len(items) >= limit:
                                    break
                        elif depth < self.max_depth:
                            # Only crawl subpages belonging to the same host domain
                            if parsed_href.netloc.lower() == root_domain:
                                # Skip non-content/media assets
                                if not parsed_href.path.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".svg", ".pdf", ".zip", ".css", ".js")):
                                    queue.append((full_url, depth + 1))

                except Exception as e:
                    print(f"Crawl error on {current_url}: {e}")

        return items

    def fetch(self, item: ScrapedItem, dest_dir: Path) -> Path | None:
        try:
            with httpx.Client(headers=self.headers, timeout=30.0, follow_redirects=True, verify=False) as client:
                resp = client.get(item.url_or_path)
                # Verify HTTP 200, non-empty, and valid ZIP/PPTX magic header (b"PK\x03\x04")
                if resp.status_code == 200 and len(resp.content) > 2048:
                    # PPTX files are OOXML zip archives starting with standard PK magic bytes
                    if resp.content.startswith(b"PK\x03\x04"):
                        dest_dir.mkdir(parents=True, exist_ok=True)
                        clean_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', item.title).strip('_') or "presentation"
                        dest_file = dest_dir / f"{clean_name}.pptx"
                        dest_file.write_bytes(resp.content)
                        return dest_file
                    else:
                        # If the link returned an HTML page (e.g. download landing page), parse for the actual direct download link
                        if b"<html" in resp.content[:500].lower():
                            sub_soup = BeautifulSoup(resp.text, "html.parser")
                            direct_link = sub_soup.find("a", href=re.compile(r"\.pptx(?:\?.*)?$", re.IGNORECASE))
                            if direct_link and direct_link.get("href"):
                                direct_url = urljoin(item.url_or_path, direct_link["href"])
                                dl_resp = client.get(direct_url)
                                if dl_resp.status_code == 200 and dl_resp.content.startswith(b"PK\x03\x04"):
                                    dest_dir.mkdir(parents=True, exist_ok=True)
                                    clean_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', item.title).strip('_') or "presentation"
                                    dest_file = dest_dir / f"{clean_name}.pptx"
                                    dest_file.write_bytes(dl_resp.content)
                                    return dest_file
        except Exception as e:
            print(f"Failed fetching {item.url_or_path}: {e}")
        return None
