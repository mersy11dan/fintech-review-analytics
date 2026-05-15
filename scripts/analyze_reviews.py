"""Command-line script for report-ready bank review analysis."""

from __future__ import annotations

import argparse

from src.analysis import AnalysisConfig, run_review_analysis


def parse_args() -> argparse.Namespace:
    """Parse analysis script arguments."""
    parser = argparse.ArgumentParser(description="Generate analysis tables and plots.")
    parser.add_argument("--input", default="data/processed/reviews_with_sentiment.csv")
    parser.add_argument("--output-dir", default="reports")
    parser.add_argument("--top-n", type=int, default=5)
    return parser.parse_args()


def main() -> None:
    """Run the review analysis workflow."""
    args = parse_args()
    outputs = run_review_analysis(
        AnalysisConfig(input_path=args.input, output_dir=args.output_dir, top_n=args.top_n)
    )
    print("Analysis outputs written:")
    for name, path in outputs.items():
        print(f"- {name}: {path}")


if __name__ == "__main__":
    main()
