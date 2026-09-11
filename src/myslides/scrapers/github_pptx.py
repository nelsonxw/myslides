"""
GitHub open-source PPTX scraper: searches repositories and git trees for .pptx templates.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Iterable
import httpx

from myslides.config import settings
from myslides.scrapers.base import ScrapedItem


class GitHubPptxScraper:
    def __init__(self, source_id: int, query: str = "powerpoint template"):
        self.source_id = source_id
        self.query = query
        self.token = settings.github_token or os.getenv("GITHUB_TOKEN", "")

    def discover(self, limit: int = 10) -> Iterable[ScrapedItem]:
        items = []
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MySlides/1.0",
        }
        if self.token:
            headers["Authorization"] = f"token {self.token}"

        # 1. Search public repositories with pptx templates
        search_url = f"https://api.github.com/search/repositories?q={self.query}&per_page={min(limit, 10)}"
        try:
            with httpx.Client(headers=headers, timeout=15.0, verify=False) as client:
                resp = client.get(search_url)
                if resp.status_code != 200:
                    return items
                
                repos = resp.json().get("items", [])
                for r in repos:
                    full_name = r.get("full_name", "")
                    default_branch = r.get("default_branch", "main")
                    
                    # Fetch git tree
                    tree_url = f"https://api.github.com/repos/{full_name}/git/trees/{default_branch}?recursive=1"
                    tree_resp = client.get(tree_url)
                    if tree_resp.status_code != 200:
                        # Fallback to master branch
                        tree_url = f"https://api.github.com/repos/{full_name}/git/trees/master?recursive=1"
                        tree_resp = client.get(tree_url)
                        if tree_resp.status_code == 200:
                            default_branch = "master"
                        else:
                            continue
                    
                    tree = tree_resp.json().get("tree", [])
                    for node in tree:
                        path = node.get("path", "")
                        if path.lower().endswith(".pptx") and not path.startswith("~$"):
                            raw_url = f"https://raw.githubusercontent.com/{full_name}/{default_branch}/{path}"
                            title = Path(path).stem.replace("_", " ").replace("-", " ").title()
                            items.append(
                                ScrapedItem(
                                    source_id=self.source_id,
                                    title=f"{r.get('name', '')} - {title}",
                                    url_or_path=raw_url,
                                    license=r.get("license", {}).get("name") if r.get("license") else "Open Source",
                                    attribution=f"GitHub: {full_name}",
                                    author=full_name.split("/")[0],
                                )
                            )
                            if len(items) >= limit:
                                return items
        except Exception as e:
            print(f"GitHub scraper error: {e}")
        return items

    def fetch(self, item: ScrapedItem, dest_dir: Path) -> Path | None:
        try:
            headers = {"User-Agent": "MySlides-Agent"}
            if self.token:
                headers["Authorization"] = f"token {self.token}"
            with httpx.Client(headers=headers, timeout=30.0, follow_redirects=True, verify=False) as client:
                resp = client.get(item.url_or_path)
                if resp.status_code == 200 and len(resp.content) > 1000:
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', item.title) + ".pptx"
                    dest_file = dest_dir / safe_name
                    dest_file.write_bytes(resp.content)
                    return dest_file
        except Exception as e:
            print(f"Failed downloading GitHub file {item.title}: {e}")
        return None
