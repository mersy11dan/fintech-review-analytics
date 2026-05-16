"""Run PostgreSQL integrity checks for loaded review data."""

from __future__ import annotations

import argparse

from src.db import run_integrity_checks


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Run database integrity checks.")
    parser.add_argument(
        "--env-var",
        default="DATABASE_URL",
        help="Environment variable containing the PostgreSQL connection URL",
    )
    return parser.parse_args()


def main() -> None:
    """Run checks and print each result table."""
    args = parse_args()
    results = run_integrity_checks(env_var=args.env_var)

    for name, table in results.items():
        print(f"\n{name}")
        print("-" * len(name))
        print(table.to_string(index=False))


if __name__ == "__main__":
    main()
