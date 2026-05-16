"""Command-line entry point for scraping the target bank Google Play reviews."""

from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import argparse
import logging

from src.scraper import scrape_and_save_bank_reviews


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape Google Play reviews for target bank apps.")
    parser.add_argument("--country", default="us", help="Two-letter country code")
    parser.add_argument("--language", default="en", help="Two-letter language code")
    parser.add_argument("--limit", default=500, type=int, help="Maximum reviews per bank app")
    parser.add_argument("--start-date", help="Inclusive start date in YYYY-MM-DD format")
    parser.add_argument("--end-date", help="Inclusive end date in YYYY-MM-DD format")
    parser.add_argument("--output-dir", default="data/raw", help="Directory for raw CSV output")
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = parse_args()

    # The module knows the three required bank package IDs, so the CLI only
    # controls scrape size, locale, date range, and output location.
    scrape_and_save_bank_reviews(
        limit=args.limit,
        start_date=args.start_date,
        end_date=args.end_date,
        country=args.country,
        language=args.language,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
