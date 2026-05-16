"""Command-line entry point for thematic analysis."""

from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import argparse

from src.themes import ThemeAnalysisConfig, run_theme_analysis


def parse_args() -> argparse.Namespace:
    """Parse command-line options for theme extraction."""
    parser = argparse.ArgumentParser(description="Extract bank review themes with TF-IDF.")
    parser.add_argument("--input", default="data/processed/reviews_cleaned.csv")
    parser.add_argument("--output", default="data/processed/reviews_with_themes.csv")
    parser.add_argument("--explanation", default="data/processed/theme_grouping_logic.md")
    parser.add_argument("--max-features", type=int, default=40)
    return parser.parse_args()


def main() -> None:
    """Run thematic analysis and save CSV/markdown outputs."""
    args = parse_args()
    config = ThemeAnalysisConfig(
        input_path=args.input,
        output_path=args.output,
        explanation_path=args.explanation,
        max_features=args.max_features,
    )
    run_theme_analysis(config)


if __name__ == "__main__":
    main()
