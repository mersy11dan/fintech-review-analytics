"""Preprocessing helpers for scraped bank review data."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from src.utils import ensure_directory, resolve_project_path


WHITESPACE_RE = re.compile(r"\s+")
NON_TEXT_RE = re.compile(r"[^a-zA-Z0-9\s.,!?'-]")

COLUMN_ALIASES = {
    "review_text": "review",
    "content": "review",
    "text": "review",
    "score": "rating",
    "at": "date",
    "app_name": "bank",
    "bank_name": "bank",
}

CLEAN_COLUMNS = ["review", "rating", "date", "bank", "source"]


def clean_review_text(text: object) -> str:
    """Normalize one review body into a clean text string."""
    if pd.isna(text):
        return ""

    cleaned = str(text).strip().lower()
    cleaned = NON_TEXT_RE.sub(" ", cleaned)
    cleaned = WHITESPACE_RE.sub(" ", cleaned)
    return cleaned.strip()


def standardize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Rename known raw scraper columns to the canonical clean schema."""
    renamed = frame.rename(columns=COLUMN_ALIASES).copy()
    missing = [column for column in CLEAN_COLUMNS if column not in renamed.columns]
    if missing:
        raise ValueError(f"Missing required columns after standardization: {missing}")

    return renamed[CLEAN_COLUMNS]


def normalize_dates(frame: pd.DataFrame, date_column: str = "date") -> pd.DataFrame:
    """Normalize date values to YYYY-MM-DD strings."""
    normalized = frame.copy()

    # Invalid dates become missing values instead of crashing the whole pipeline.
    dates = normalized[date_column].map(lambda value: pd.to_datetime(value, errors="coerce"))
    normalized[date_column] = dates.dt.strftime("%Y-%m-%d")
    return normalized


def missing_value_counts(frame: pd.DataFrame) -> dict[str, int]:
    """Return missing value counts, treating blank review text as missing."""
    counts = frame.isna().sum().to_dict()
    if "review" in frame.columns:
        review_values = frame["review"]
        blank_reviews = (review_values.notna() & review_values.astype(str).str.strip().eq("")).sum()
        counts["review"] = int(counts.get("review", 0) + blank_reviews)
    return {column: int(count) for column, count in counts.items()}


def print_quality_report(before: pd.DataFrame, after: pd.DataFrame) -> None:
    """Print before-and-after row counts and missing value counts."""
    print(f"Rows before cleaning: {len(before)}")
    print(f"Missing values before cleaning: {missing_value_counts(before)}")
    print(f"Rows after cleaning: {len(after)}")
    print(f"Missing values after cleaning: {missing_value_counts(after)}")


def preprocess_reviews(frame: pd.DataFrame) -> pd.DataFrame:
    """Clean scraped reviews into review, rating, date, bank, and source columns."""
    standardized = standardize_columns(frame)

    processed = standardized.copy()
    processed["review"] = processed["review"].map(clean_review_text)
    processed["rating"] = pd.to_numeric(processed["rating"], errors="coerce")
    processed = normalize_dates(processed)

    # Review text and rating are required for downstream sentiment analysis.
    processed = processed.dropna(subset=["rating"])
    processed = processed[processed["review"].ne("")]

    # Remove duplicates across the business key so repeated scrapes do not skew analysis.
    processed = processed.drop_duplicates(
        subset=["review", "rating", "date", "bank", "source"],
        keep="first",
    )
    return processed.reset_index(drop=True)


def save_cleaned_reviews(
    frame: pd.DataFrame,
    output_path: str | Path = "data/processed/reviews_cleaned.csv",
) -> Path:
    """Save cleaned review data under data/processed and return the file path."""
    path = Path(output_path)
    resolved_path = path if path.is_absolute() else resolve_project_path(str(path))
    ensure_directory(resolved_path.parent)
    frame.to_csv(resolved_path, index=False)
    return resolved_path


def preprocess_file(
    input_path: str | Path,
    output_path: str | Path = "data/processed/reviews_cleaned.csv",
) -> pd.DataFrame:
    """Load raw reviews, clean them, print a quality report, and save the result."""
    path = Path(input_path)
    raw_path = path if path.is_absolute() else resolve_project_path(str(path))
    raw = pd.read_csv(raw_path)
    cleaned = preprocess_reviews(raw)

    print_quality_report(standardize_columns(raw), cleaned)
    save_cleaned_reviews(cleaned, output_path=output_path)
    return cleaned
