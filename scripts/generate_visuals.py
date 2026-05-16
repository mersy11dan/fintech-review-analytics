"""Generate stakeholder-ready plots for bank review analysis."""

from __future__ import annotations

import argparse

from src.visuals import VisualizationConfig, generate_review_plots


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Generate bank review analysis figures.")
    parser.add_argument("--input", default="data/processed/reviews_with_sentiment.csv")
    parser.add_argument("--output-dir", default="reports/figures")
    parser.add_argument("--top-n", type=int, default=5)
    return parser.parse_args()


def main() -> None:
    """Generate and print saved figure paths."""
    args = parse_args()
    outputs = generate_review_plots(
        VisualizationConfig(input_path=args.input, output_dir=args.output_dir, top_n=args.top_n)
    )

    print("Generated figures:")
    for name, path in outputs.items():
        print(f"- {name}: {path}")


if __name__ == "__main__":
    main()
