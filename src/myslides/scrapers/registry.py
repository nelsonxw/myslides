"""
Scraper Registry: mapping source kind to corresponding scraper instance.
"""
from __future__ import annotations

from pathlib import Path
from myslides.library.models import Source
from myslides.scrapers.base import SourceScraper
from myslides.scrapers.generic_url import GenericUrlScraper
from myslides.scrapers.github_pptx import GitHubPptxScraper
from myslides.scrapers.local_folder import LocalFolderScraper
from myslides.scrapers.microsoft_create import MicrosoftCreateScraper
from myslides.scrapers.slidescarnival import SlidesCarnivalScraper


def get_scraper_for_source(source: Source) -> SourceScraper:
    """Instantiate appropriate scraper implementation based on source kind."""
    kind = source.kind
    if kind == "local_folder":
        return LocalFolderScraper(
            source_id=source.id,
            folder_path=source.url_or_path,
            license_str=source.license,
            attribution=source.attribution,
        )
    elif kind == "slidescarnival":
        return SlidesCarnivalScraper(
            source_id=source.id,
            base_url=source.url_or_path or "https://www.slidescarnival.com/category/free-templates",
        )
    elif kind == "ms_create":
        return MicrosoftCreateScraper(
            source_id=source.id,
            url=source.url_or_path or "https://create.microsoft.com/en-us/templates/powerpoint",
        )
    elif kind == "github":
        return GitHubPptxScraper(
            source_id=source.id,
            query=source.url_or_path or "powerpoint template",
        )
    elif kind == "generic_url":
        return GenericUrlScraper(
            source_id=source.id,
            target_url=source.url_or_path,
            license_str=source.license,
            attribution=source.attribution,
        )
    else:
        # Default to generic URL handler
        return GenericUrlScraper(
            source_id=source.id,
            target_url=source.url_or_path,
            license_str=source.license,
            attribution=source.attribution,
        )
