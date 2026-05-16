"""Command-line entry point for loading processed reviews to PostgreSQL."""

from __future__ import annotations

import argparse

from src.db import load_reviews_to_postgres, read_review_data
from src.utils import resolve_project_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load processed reviews into PostgreSQL.")
    parser.add_argument(
        "--input",
        default="data/processed/reviews_with_sentiment.csv",
        help="Cleaned/analyzed review CSV",
    )
    parser.add_argument(
        "--env-var",
        default="DATABASE_URL",
        help="Environment variable containing the PostgreSQL connection URL",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    frame = read_review_data(resolve_project_path(args.input))
    counts = load_reviews_to_postgres(frame, env_var=args.env_var)

    print(f"Banks processed: {counts['banks_seen']}")
    print(f"Reviews processed: {counts['reviews_seen']}")
    print(f"Reviews inserted: {counts['reviews_inserted']}")
    print(f"Duplicate reviews skipped: {counts['reviews_skipped']}")


if __name__ == "__main__":
    main()
