"""Initialize the PostgreSQL schema without requiring the psql CLI."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from sqlalchemy import create_engine, text


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def resolve_project_path(path: str | Path) -> Path:
    """Resolve a project-relative path while preserving absolute paths."""
    candidate = Path(path)
    return candidate if candidate.is_absolute() else PROJECT_ROOT / candidate


def load_database_url() -> str:
    """Load DATABASE_URL from the environment or a local .env file."""
    try:
        from dotenv import load_dotenv

        load_dotenv(PROJECT_ROOT / ".env")
    except Exception:
        pass

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is not set. Add it to your terminal or .env before initializing the DB."
        )
    return database_url


def apply_schema(schema_path: str | Path = "sql/schema.sql") -> None:
    """Apply the SQL schema file through SQLAlchemy."""
    resolved_schema_path = resolve_project_path(schema_path)
    if not resolved_schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {resolved_schema_path}")

    schema_sql = resolved_schema_path.read_text(encoding="utf-8")
    database_url = load_database_url()
    engine = create_engine(database_url)

    with engine.begin() as connection:
        connection.execute(text(schema_sql))


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Apply the PostgreSQL schema with Python.")
    parser.add_argument("--schema", default="sql/schema.sql", help="Path to the schema SQL file")
    return parser.parse_args()


def main() -> None:
    """Run schema initialization from the command line."""
    args = parse_args()
    apply_schema(args.schema)
    print("Database schema initialized successfully.")


if __name__ == "__main__":
    main()
