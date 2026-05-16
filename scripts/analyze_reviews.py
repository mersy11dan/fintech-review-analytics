"""Command-line script for report-ready bank review analysis."""

from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import argparse
import logging
import sys

from src.analysis import AnalysisConfig, run_review_analysis


LOGGER = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse analysis script arguments."""
    parser = argparse.ArgumentParser(description="Generate final-report review analysis outputs.")
    parser.add_argument("--input", default="data/processed/reviews_with_sentiment.csv")
    parser.add_argument("--output-dir", default="reports")
    parser.add_argument("--top-n", type=int, default=5)
    parser.add_argument(
        "--env-var",
        default="DATABASE_URL",
        help="Environment variable containing the PostgreSQL connection URL",
    )
    return parser.parse_args()


def main() -> None:
    """Run the review analysis workflow."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = parse_args()
    try:
        outputs = run_review_analysis(
            AnalysisConfig(
                input_path=args.input,
                output_dir=args.output_dir,
                top_n=args.top_n,
                env_var=args.env_var,
            )
        )
    except Exception as exc:
        LOGGER.error("Analysis failed: %s", exc)
        print(f"Analysis failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    LOGGER.info("Analysis outputs written to %s", args.output_dir)
    print("Analysis outputs written:")
    for name, path in outputs.items():
        print(f"- {name}: {path}")


if __name__ == "__main__":
    main()
