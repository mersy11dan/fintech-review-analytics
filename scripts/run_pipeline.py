"""Command-line entry point for running the review analytics pipeline."""

from __future__ import annotations

import argparse

import pandas as pd

from src.preprocess import preprocess_reviews
from src.sentiment import add_sentiment_scores
from src.themes import add_theme_labels
from src.utils import ensure_directory, resolve_project_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preprocess, score, and theme review data.")
    parser.add_argument("--input", default="data/raw/reviews.csv", help="Input raw reviews CSV")
    parser.add_argument("--output", default="data/processed/reviews_processed.csv", help="Output CSV")
    parser.add_argument("--text-column", default="content", help="Column containing review text")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = resolve_project_path(args.input)
    output_path = resolve_project_path(args.output)

    reviews = pd.read_csv(input_path)
    processed = preprocess_reviews(reviews, text_column=args.text_column)
    processed = add_sentiment_scores(processed)
    processed = add_theme_labels(processed)

    ensure_directory(output_path.parent)
    processed.to_csv(output_path, index=False)


if __name__ == "__main__":
    main()
