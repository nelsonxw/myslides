"""
Seed the template library from local Dell templates and ../ppt output decks.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Set UTF-8 encoding for stdout
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Ensure src is in python path
src_dir = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(src_dir))

from myslides.analysis.knowledge import build_knowledge_rules
from myslides.config import settings
from myslides.library.ingest import ingest_pptx_file
from myslides.library.models import Source, TemplateAsset
from myslides.library.repository import get_standalone_session, init_db
from myslides.llm.factory import get_llm_provider
from myslides.scrapers.local_folder import LocalFolderScraper


def main():
    print("=" * 60)
    print("Seeding MySlides Library from ../ppt...")
    print("=" * 60)

    init_db()
    session = get_standalone_session()
    # Pass llm=None during batch seeding for super-fast offline ingestion (critic runs on-demand or background)
    llm = None

    # Create / update Default Local Sources
    ppt_root = Path(__file__).resolve().parents[2] / "ppt"
    templates_dir = ppt_root / "templates"
    output_dir = ppt_root / "output"

    sources_to_seed = [
        ("Dell Official Templates", str(templates_dir), "Dell Internal", "Dell Technologies Brand"),
        ("Dell AI Slide Decks", str(output_dir), "Dell Internal", "Generated corporate slides"),
    ]

    for name, path_str, lic, attr in sources_to_seed:
        p = Path(path_str)
        if not p.exists():
            print(f"Skipping missing path: {p}")
            continue

        source = session.query(Source).filter_by(name=name).first()
        if not source:
            source = Source(
                name=name,
                kind="local_folder",
                url_or_path=str(p.resolve()),
                license=lic,
                attribution=attr,
                enabled=True,
            )
            session.add(source)
            session.commit()
            print(f"Added Source: {name}")

        scraper = LocalFolderScraper(source.id, p, lic, attr)
        items = list(scraper.discover(limit=50))
        print(f"Found {len(items)} .pptx files in {name}")

        for item in items:
            if item.local_path:
                asset = ingest_pptx_file(
                    item.local_path,
                    session,
                    source_id=source.id,
                    license_str=lic,
                    attribution=attr,
                    author=item.author,
                    llm=llm,
                )
                if asset:
                    print(f"  -> Ingested {asset.filename} ({asset.slide_count} slides)")

    # Synthesize knowledge rules from ingested slides
    print("\nSynthesizing design knowledge rules...")
    rules = build_knowledge_rules(session)
    print(f"Learned design rules updated. Current categories: {list(rules.keys())}")
    
    total_assets = session.query(TemplateAsset).count()
    print(f"\nSeeding complete! Total assets in library: {total_assets}")


if __name__ == "__main__":
    main()
