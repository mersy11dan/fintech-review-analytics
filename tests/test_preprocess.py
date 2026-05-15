"""Tests for preprocessing helpers."""

import pandas as pd

from src.preprocess import (
    CLEAN_COLUMNS,
    missing_value_counts,
    preprocess_reviews,
    save_cleaned_reviews,
)


def test_preprocess_reviews_standardizes_and_cleans_rows():
    raw = pd.DataFrame(
        [
            {
                "review_text": " Fast transfer!!! ",
                "rating": 5,
                "date": "2024-02-01 13:45:00",
                "app_name": "Dashen Bank",
                "source": "google_play",
            },
            {
                "review_text": " Fast transfer!!! ",
                "rating": 5,
                "date": "2024-02-01 13:45:00",
                "app_name": "Dashen Bank",
                "source": "google_play",
            },
            {
                "review_text": "",
                "rating": 4,
                "date": "2024-02-02",
                "app_name": "Dashen Bank",
                "source": "google_play",
            },
            {
                "review_text": "Missing rating",
                "rating": None,
                "date": "2024-02-03",
                "app_name": "Dashen Bank",
                "source": "google_play",
            },
        ]
    )

    cleaned = preprocess_reviews(raw)

    assert list(cleaned.columns) == CLEAN_COLUMNS
    assert len(cleaned) == 1
    assert cleaned.loc[0, "review"] == "fast transfer!!!"
    assert cleaned.loc[0, "rating"] == 5
    assert cleaned.loc[0, "date"] == "2024-02-01"
    assert cleaned.loc[0, "bank"] == "Dashen Bank"


def test_missing_value_counts_treats_blank_reviews_as_missing():
    frame = pd.DataFrame(
        {
            "review": ["", None, "good app"],
            "rating": [5, None, 4],
            "date": ["2024-01-01", "2024-01-02", None],
        }
    )

    assert missing_value_counts(frame)["review"] == 2
    assert missing_value_counts(frame)["rating"] == 1
    assert missing_value_counts(frame)["date"] == 1


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
