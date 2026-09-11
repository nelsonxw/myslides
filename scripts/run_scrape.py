"""
CLI tool to run scraping for all or specific sources.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure src is in python path
src_dir = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(src_dir))

from myslides.library.models import Source
from myslides.library.repository import get_standalone_session, init_db
from myslides.scrapers.runner import run_source_scrape


def main():
    parser = argparse.ArgumentParser(description="MySlides Scraper Runner")
    parser.add_argument("--source", type=str, default="all", help="Source ID or 'all'")
    parser.add_argument("--limit", type=int, default=5, help="Max templates per source")
    args = parser.parse_args()

    init_db()
    session = get_standalone_session()

    if args.source == "all":
        sources = session.query(Source).filter_by(enabled=True).all()
    else:
        sources = session.query(Source).filter_by(id=int(args.source)).all()

    print(f"Running scraper for {len(sources)} source(s)...")
    for s in sources:
        print(f"\nScraping '{s.name}' ({s.kind})...")
        res = run_source_scrape(s.id, session, limit=args.limit)
        print(f"Result: {res}")


if __name__ == "__main__":
    main()
