"""Tests for database helpers."""

import pandas as pd
import pytest

from src.db import normalize_review_frame, validate_review_frame


def test_db_module_imports():
    import src.db

    assert src.db is not None


def test_normalize_review_frame_maps_pipeline_columns():
    frame = pd.DataFrame(
        {
            "bank": ["Commercial Bank of Ethiopia"],
            "app_name": ["CBE Mobile"],
            "review": ["Great transfer experience"],
            "rating": ["5"],
            "date": ["2024-01-31"],
            "sentiment_label": ["Positive"],
            "sentiment_score": ["0.98"],
            "identified_theme": ["transfer_speed"],
            "source": ["google_play"],
        }
    )

    normalized = normalize_review_frame(frame)

    assert normalized.loc[0, "bank_name"] == "Commercial Bank of Ethiopia"
    assert normalized.loc[0, "app_name"] == "CBE Mobile"
    assert normalized.loc[0, "review_text"] == "Great transfer experience"
    assert normalized.loc[0, "rating"] == 5
    assert normalized.loc[0, "sentiment_label"] == "positive"


def test_validate_review_frame_rejects_invalid_rating():
    frame = pd.DataFrame(
        {
            "bank_name": ["Dashen Bank"],
            "app_name": ["Dashen Super App"],
            "review_text": ["Bad app"],
            "rating": [6],
            "review_date": [pd.to_datetime("2024-01-01").date()],
            "sentiment_label": ["negative"],
            "sentiment_score": [0.91],
            "identified_theme": ["login_issues"],
            "source": ["google_play"],
        }
    )

    with pytest.raises(ValueError, match="Ratings must be between 1 and 5"):
        validate_review_frame(frame)


def test_validate_review_frame_accepts_valid_rows():
    frame = pd.DataFrame(
        {
            "bank_name": ["Bank of Abyssinia"],
            "app_name": ["BoA Mobile"],
            "review_text": ["Easy login"],
            "rating": [4],
            "review_date": [pd.to_datetime("2024-01-01").date()],
            "sentiment_label": ["positive"],
            "sentiment_score": [0.88],
            "identified_theme": ["login_issues"],
            "source": ["google_play"],
        }
    )

    validate_review_frame(frame)
