"""Command-line entry point for running the review analytics pipeline."""

from __future__ import annotations

import argparse

from src.preprocess import preprocess_file
from src.sentiment import add_sentiment_scores
from src.themes import add_theme_labels
from src.utils import ensure_directory, resolve_project_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preprocess, score, and theme review data.")
    parser.add_argument("--input", default="data/raw/reviews.csv", help="Input raw reviews CSV")
    parser.add_argument("--output", default="data/processed/reviews_processed.csv", help="Output CSV")
    parser.add_argument("--clean-only", action="store_true", help="Only run preprocessing")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = resolve_project_path(args.input)
    output_path = resolve_project_path(args.output)

    processed = preprocess_file(input_path, output_path=output_path)
    if args.clean_only:
        return

    processed = add_sentiment_scores(processed, text_column="review")
    processed = add_theme_labels(processed, text_column="review")

    ensure_directory(output_path.parent)
    processed.to_csv(output_path, index=False)


if __name__ == "__main__":
    main()
