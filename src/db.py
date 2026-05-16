"""Database helpers for storing processed review data."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from sqlalchemy import text


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


def read_review_data(input_path: str | Path) -> pd.DataFrame:
    """Read cleaned/analyzed review data from a CSV file."""
    return pd.read_csv(input_path)


def _first_existing_column(frame: pd.DataFrame, candidates: tuple[str, ...]) -> str | None:
    """Return the first column found from a list of candidate names."""
    return next((column for column in candidates if column in frame.columns), None)


def normalize_review_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize supported pipeline outputs to the database schema columns."""
    review_column = _first_existing_column(frame, ("review_text", "review", "content"))
    bank_column = _first_existing_column(frame, ("bank", "bank_name", "app_name"))
    date_column = _first_existing_column(frame, ("review_date", "date", "at"))

    missing = []
    if review_column is None:
        missing.append("review_text/review/content")
    if bank_column is None:
        missing.append("bank/bank_name/app_name")
    if date_column is None:
        missing.append("review_date/date/at")
    for required in ("rating", "sentiment_label", "sentiment_score", "identified_theme", "source"):
        if required not in frame.columns:
            missing.append(required)
    if missing:
        raise ValueError(f"Missing required review data columns: {missing}")

    normalized = pd.DataFrame(
        {
            "bank_name": frame[bank_column],
            "app_name": frame["app_name"] if "app_name" in frame.columns else frame[bank_column],
            "review_text": frame[review_column],
            "rating": pd.to_numeric(frame["rating"], errors="coerce"),
            "review_date": pd.to_datetime(frame[date_column], errors="coerce").dt.date,
            "sentiment_label": frame["sentiment_label"].astype(str).str.lower(),
            "sentiment_score": pd.to_numeric(frame["sentiment_score"], errors="coerce"),
            "identified_theme": frame["identified_theme"],
            "source": frame["source"],
        }
    )
    return normalized


def validate_review_frame(frame: pd.DataFrame) -> None:
    """Validate normalized review rows before inserting them into PostgreSQL."""
    required_columns = {
        "bank_name",
        "app_name",
        "review_text",
        "rating",
        "review_date",
        "sentiment_label",
        "sentiment_score",
        "identified_theme",
        "source",
    }
    missing_columns = required_columns.difference(frame.columns)
    if missing_columns:
        raise ValueError(f"Missing normalized columns: {sorted(missing_columns)}")

    required_non_null = ["bank_name", "app_name", "review_text", "rating", "review_date", "source"]
    null_counts = frame[required_non_null].isna().sum()
    invalid_nulls = null_counts[null_counts.gt(0)]
    if not invalid_nulls.empty:
        raise ValueError(f"Null values found in required columns: {invalid_nulls.to_dict()}")

    blank_reviews = frame["review_text"].astype(str).str.strip().eq("")
    if blank_reviews.any():
        raise ValueError(f"Blank review_text rows found: {int(blank_reviews.sum())}")

    invalid_ratings = ~frame["rating"].between(1, 5)
    if invalid_ratings.any():
        raise ValueError(f"Ratings must be between 1 and 5: {int(invalid_ratings.sum())} invalid rows")

    valid_sentiments = {"positive", "neutral", "negative"}
    invalid_sentiments = frame["sentiment_label"].dropna().map(lambda value: value not in valid_sentiments)
    if invalid_sentiments.any():
        raise ValueError("sentiment_label must be one of positive, neutral, or negative")

    invalid_scores = frame["sentiment_score"].dropna().map(lambda value: value < 0 or value > 1)
    if invalid_scores.any():
        raise ValueError("sentiment_score must be between 0 and 1 when present")


def upsert_banks(connection, frame: pd.DataFrame) -> dict[str, int]:
    """Insert/update bank metadata and return a bank-name to bank-id mapping."""
    bank_rows = (
        frame[["bank_name", "app_name"]]
        .drop_duplicates(subset=["bank_name"])
        .sort_values("bank_name")
        .to_dict(orient="records")
    )
    bank_ids: dict[str, int] = {}

    statement = text(
        """
        INSERT INTO banks (bank_name, app_name)
        VALUES (:bank_name, :app_name)
        ON CONFLICT (bank_name)
        DO UPDATE SET
            app_name = EXCLUDED.app_name,
            updated_at = NOW()
        RETURNING bank_id, bank_name
        """
    )

    for row in bank_rows:
        result = connection.execute(statement, row).mappings().one()
        bank_ids[result["bank_name"]] = result["bank_id"]

    return bank_ids


def insert_reviews(connection, frame: pd.DataFrame, bank_ids: dict[str, int]) -> int:
    """Insert review rows, skipping duplicates using the schema unique constraint."""
    statement = text(
        """
        INSERT INTO reviews (
            bank_id,
            review_text,
            rating,
            review_date,
            sentiment_label,
            sentiment_score,
            identified_theme,
            source
        )
        VALUES (
            :bank_id,
            :review_text,
            :rating,
            :review_date,
            :sentiment_label,
            :sentiment_score,
            :identified_theme,
            :source
        )
        ON CONFLICT ON CONSTRAINT reviews_unique_review
        DO NOTHING
        RETURNING review_id
        """
    )

    inserted_count = 0
    for row in frame.to_dict(orient="records"):
        payload = {
            "bank_id": bank_ids[row["bank_name"]],
            "review_text": row["review_text"],
            "rating": int(row["rating"]),
            "review_date": row["review_date"],
            "sentiment_label": row["sentiment_label"],
            "sentiment_score": None if pd.isna(row["sentiment_score"]) else float(row["sentiment_score"]),
            "identified_theme": row["identified_theme"],
            "source": row["source"],
        }
        result = connection.execute(statement, payload).first()
        inserted_count += int(result is not None)

    return inserted_count


def load_reviews_to_postgres(frame: pd.DataFrame, env_var: str = "DATABASE_URL") -> dict[str, int]:
    """Validate and insert bank metadata plus review rows into PostgreSQL."""
    normalized = normalize_review_frame(frame)
    validate_review_frame(normalized)

    engine = create_engine_from_env(env_var)
    with engine.begin() as connection:
        bank_ids = upsert_banks(connection, normalized)
        inserted_reviews = insert_reviews(connection, normalized, bank_ids)

    return {
        "banks_seen": len(bank_ids),
        "reviews_seen": len(normalized),
        "reviews_inserted": inserted_reviews,
        "reviews_skipped": len(normalized) - inserted_reviews,
    }


def count_reviews_per_bank(connection) -> pd.DataFrame:
    """Return review counts grouped by bank."""
    return pd.read_sql(
        text(
            """
            SELECT
                b.bank_name,
                COUNT(r.review_id) AS review_count
            FROM banks AS b
            LEFT JOIN reviews AS r
                ON b.bank_id = r.bank_id
            GROUP BY b.bank_id, b.bank_name
            ORDER BY review_count DESC, b.bank_name
            """
        ),
        connection,
    )


def average_rating_per_bank(connection) -> pd.DataFrame:
    """Return average rating and review count grouped by bank."""
    return pd.read_sql(
        text(
            """
            SELECT
                b.bank_name,
                ROUND(AVG(r.rating)::numeric, 2) AS average_rating,
                COUNT(r.review_id) AS review_count
            FROM banks AS b
            LEFT JOIN reviews AS r
                ON b.bank_id = r.bank_id
            GROUP BY b.bank_id, b.bank_name
            ORDER BY average_rating DESC NULLS LAST, b.bank_name
            """
        ),
        connection,
    )


def important_null_counts(connection) -> pd.DataFrame:
    """Return null/blank counts for important review columns."""
    return pd.read_sql(
        text(
            """
            SELECT
                SUM(CASE WHEN r.review_id IS NULL THEN 1 ELSE 0 END) AS null_review_id,
                SUM(CASE WHEN r.bank_id IS NULL THEN 1 ELSE 0 END) AS null_bank_id,
                SUM(
                    CASE
                        WHEN r.review_text IS NULL OR BTRIM(r.review_text) = '' THEN 1
                        ELSE 0
                    END
                ) AS null_or_blank_review_text,
                SUM(CASE WHEN r.rating IS NULL THEN 1 ELSE 0 END) AS null_rating,
                SUM(CASE WHEN r.review_date IS NULL THEN 1 ELSE 0 END) AS null_review_date,
                SUM(
                    CASE
                        WHEN r.source IS NULL OR BTRIM(r.source) = '' THEN 1
                        ELSE 0
                    END
                ) AS null_or_blank_source
            FROM reviews AS r
            """
        ),
        connection,
    )


def orphan_review_rows(connection) -> pd.DataFrame:
    """Return reviews whose bank_id does not exist in banks."""
    return pd.read_sql(
        text(
            """
            SELECT
                r.review_id,
                r.bank_id
            FROM reviews AS r
            LEFT JOIN banks AS b
                ON r.bank_id = b.bank_id
            WHERE b.bank_id IS NULL
            """
        ),
        connection,
    )


def duplicate_review_keys(connection) -> pd.DataFrame:
    """Return duplicate review business keys, which should be prevented by the schema."""
    return pd.read_sql(
        text(
            """
            SELECT
                bank_id,
                review_text,
                rating,
                review_date,
                source,
                COUNT(*) AS duplicate_count
            FROM reviews
            GROUP BY bank_id, review_text, rating, review_date, source
            HAVING COUNT(*) > 1
            """
        ),
        connection,
    )


def run_integrity_checks(env_var: str = "DATABASE_URL") -> dict[str, pd.DataFrame]:
    """Run all database integrity checks and return named result tables."""
    engine = create_engine_from_env(env_var)
    with engine.begin() as connection:
        return {
            "reviews_per_bank": count_reviews_per_bank(connection),
            "average_rating_per_bank": average_rating_per_bank(connection),
            "null_counts": important_null_counts(connection),
            "orphan_reviews": orphan_review_rows(connection),
            "duplicate_review_keys": duplicate_review_keys(connection),
        }
