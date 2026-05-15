"""Command-line entry point for loading processed reviews to PostgreSQL."""

from __future__ import annotations

import argparse

import pandas as pd

from src.db import write_reviews_to_db
from src.utils import resolve_project_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load processed reviews into PostgreSQL.")
    parser.add_argument("--input", default="data/processed/reviews_processed.csv", help="Processed CSV")
    parser.add_argument("--table", default="reviews", help="Destination table name")
    parser.add_argument("--if-exists", default="replace", choices=["fail", "replace", "append"])
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    frame = pd.read_csv(resolve_project_path(args.input))
    write_reviews_to_db(frame, table_name=args.table, if_exists=args.if_exists)


if __name__ == "__main__":
    main()
