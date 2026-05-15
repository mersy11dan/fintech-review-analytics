"""Database helpers for storing processed review data."""

from __future__ import annotations

import os


def get_database_url(env_var: str = "DATABASE_URL") -> str:
    """Read the PostgreSQL connection URL from the environment."""
    from dotenv import load_dotenv

    load_dotenv()
    database_url = os.getenv(env_var)
    if not database_url:
        raise RuntimeError(f"Missing required environment variable: {env_var}")
    return database_url


def create_engine_from_env(env_var: str = "DATABASE_URL"):
    """Create a SQLAlchemy engine from a PostgreSQL connection URL."""
    from sqlalchemy import create_engine

    return create_engine(get_database_url(env_var))


def write_reviews_to_db(frame, table_name: str = "reviews", if_exists: str = "replace") -> None:
    """Persist a processed review DataFrame to PostgreSQL."""
    engine = create_engine_from_env()
    with engine.begin() as connection:
        frame.to_sql(table_name, connection, if_exists=if_exists, index=False)
