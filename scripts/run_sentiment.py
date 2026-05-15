"""Command-line entry point for bank review sentiment analysis."""

from __future__ import annotations

import argparse
import logging

from src.sentiment import SentimentConfig, run_sentiment_pipeline


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for sentiment scoring."""
    parser = argparse.ArgumentParser(description="Score cleaned bank reviews for sentiment.")
    parser.add_argument("--input", default="data/processed/reviews_cleaned.csv")
    parser.add_argument("--output", default="data/processed/reviews_with_sentiment.csv")
    parser.add_argument(
        "--no-transformer",
        action="store_true",
        help="Skip DistilBERT and use the fallback sentiment backend.",
    )
    return parser.parse_args()


def main() -> None:
    """Run the sentiment analysis pipeline."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = parse_args()
    config = SentimentConfig(
        input_path=args.input,
        output_path=args.output,
        prefer_transformer=not args.no_transformer,
    )
    run_sentiment_pipeline(config)


if __name__ == "__main__":
    main()

