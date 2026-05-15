"""Tests for preprocessing helpers."""

import pandas as pd
import pytest

from src.preprocess import (
    CLEAN_COLUMNS,
    missing_value_counts,
    normalize_dates,
    preprocess_reviews,
    save_cleaned_reviews,
    standardize_columns,
)


@pytest.fixture
def raw_reviews() -> pd.DataFrame:
    """Small representative fixture using scraper-style column names."""
    return pd.DataFrame(
        [
            {
                "review_text": " Fast transfer!!! ",
                "rating": 5,
                "date": "2024-02-01 13:45:00",
                "app_name": "Dashen Bank",
                "source": "google_play",
            },
            {
                "review_text": " Slow login ",
                "rating": 2,
                "date": "2024/02/02",
                "app_name": "Bank of Abyssinia",
                "source": "google_play",
            },
        ]
    )


def test_standardize_columns_maps_scraper_fields(raw_reviews):
    standardized = standardize_columns(raw_reviews)

    assert list(standardized.columns) == CLEAN_COLUMNS
    assert standardized.loc[0, "review"] == " Fast transfer!!! "
    assert standardized.loc[0, "bank"] == "Dashen Bank"


def test_standardize_columns_requires_clean_schema_fields():
    incomplete = pd.DataFrame({"review_text": ["good app"], "rating": [5]})

    with pytest.raises(ValueError, match="Missing required columns"):
        standardize_columns(incomplete)


def test_preprocess_reviews_removes_duplicate_reviews():
    duplicated = pd.DataFrame(
        [
            {
                "review_text": "Reliable app",
                "rating": 4,
                "date": "2024-01-01",
                "app_name": "Commercial Bank of Ethiopia",
                "source": "google_play",
            },
            {
                "review_text": "Reliable app",
                "rating": 4,
                "date": "2024-01-01",
                "app_name": "Commercial Bank of Ethiopia",
                "source": "google_play",
            },
        ]
    )

    cleaned = preprocess_reviews(duplicated)

    assert len(cleaned) == 1
    assert cleaned.loc[0, "review"] == "reliable app"


def test_preprocess_reviews_drops_missing_review_or_rating():
    raw = pd.DataFrame(
        [
            {
                "review_text": "Good app",
                "rating": 5,
                "date": "2024-01-01",
                "app_name": "Dashen Bank",
                "source": "google_play",
            },
            {
                "review_text": "",
                "rating": 4,
                "date": "2024-01-02",
                "app_name": "Dashen Bank",
                "source": "google_play",
            },
            {
                "review_text": "Missing rating",
                "rating": None,
                "date": "2024-01-03",
                "app_name": "Dashen Bank",
                "source": "google_play",
            },
        ]
    )

    cleaned = preprocess_reviews(raw)

    assert len(cleaned) == 1
    assert cleaned.loc[0, "review"] == "good app"
    assert cleaned["rating"].notna().all()


def test_normalize_dates_outputs_yyyy_mm_dd(raw_reviews):
    standardized = standardize_columns(raw_reviews)

    normalized = normalize_dates(standardized)

    assert normalized["date"].to_list() == ["2024-02-01", "2024-02-02"]


def test_missing_value_counts_treats_blank_reviews_as_missing():
    frame = pd.DataFrame(
        {
            "review": ["", None, "good app"],
            "rating": [5, None, 4],
            "date": ["2024-01-01", "2024-01-02", None],
        }
    )

    counts = missing_value_counts(frame)

    assert counts["review"] == 2
    assert counts["rating"] == 1
    assert counts["date"] == 1


def test_save_cleaned_reviews_writes_csv(tmp_path):
    frame = pd.DataFrame(
        {
            "review": ["good app"],
            "rating": [5],
            "date": ["2024-01-01"],
            "bank": ["Commercial Bank of Ethiopia"],
            "source": ["google_play"],
        }
    )

    output_path = save_cleaned_reviews(frame, tmp_path / "cleaned.csv")

    assert output_path.exists()
