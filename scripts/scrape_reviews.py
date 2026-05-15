"""Command-line entry point for scraping Google Play reviews."""

from __future__ import annotations

import argparse

from src.scraper import ReviewScrapeConfig, scrape_google_play_reviews
from src.utils import ensure_directory, resolve_project_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape Google Play app reviews.")
    parser.add_argument("app_id", help="Google Play package name, for example com.example.app")
    parser.add_argument("--country", default="us", help="Two-letter country code")
    parser.add_argument("--language", default="en", help="Two-letter language code")
    parser.add_argument("--count", default=500, type=int, help="Number of reviews to fetch")
    parser.add_argument("--output", default="data/raw/reviews.csv", help="Output CSV path")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = ReviewScrapeConfig(
        app_id=args.app_id,
        country=args.country,
        language=args.language,
        count=args.count,
    )
    output_path = resolve_project_path(args.output)
    ensure_directory(output_path.parent)
    scrape_google_play_reviews(config).to_csv(output_path, index=False)


if __name__ == "__main__":
    main()
