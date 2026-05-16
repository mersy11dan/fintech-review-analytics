"""Tests for visualization helpers."""

import pandas as pd

from src.visuals import (
    VisualizationConfig,
    can_plot_sentiment_over_time,
    generate_review_plots,
    normalize_visual_columns,
)


def sample_visual_data() -> pd.DataFrame:
    """Small synthetic dataset with enough dates for trend plotting."""
    return pd.DataFrame(
        {
            "bank": ["CBE", "CBE", "Dashen", "Dashen", "BoA", "BoA"],
            "rating": [5, 2, 4, 1, 3, 5],
            "review_text": [
                "fast transfer",
                "login issue",
                "good design",
                "slow support",
                "okay app",
                "great feature",
            ],
            "sentiment_label": ["positive", "negative", "positive", "negative", "neutral", "positive"],
            "identified_theme": [
                "transfer_speed",
                "login_issues",
                "ui_design",
                "customer_support",
                "general_feedback",
                "feature_requests",
            ],
            "review_date": [
                "2024-01-01",
                "2024-01-15",
                "2024-02-01",
                "2024-02-20",
                "2024-03-01",
                "2024-03-15",
            ],
        }
    )


def test_normalize_visual_columns_accepts_aliases():
    frame = sample_visual_data().rename(columns={"bank": "app_name", "review_text": "review"})

    normalized = normalize_visual_columns(frame)

    assert "bank" in normalized.columns
    assert "review_text" in normalized.columns
    assert pd.api.types.is_datetime64_any_dtype(normalized["review_date"])


def test_can_plot_sentiment_over_time_requires_multiple_dates():
    assert can_plot_sentiment_over_time(sample_visual_data())
    assert not can_plot_sentiment_over_time(sample_visual_data().assign(review_date="2024-01-01"))


def test_generate_review_plots_saves_expected_figures(tmp_path):
    input_path = tmp_path / "reviews_with_sentiment.csv"
    output_dir = tmp_path / "figures"
    sample_visual_data().to_csv(input_path, index=False)

    outputs = generate_review_plots(VisualizationConfig(input_path=input_path, output_dir=output_dir))

    assert outputs["sentiment_distribution_by_bank"].exists()
    assert outputs["rating_distribution_by_bank"].exists()
    assert outputs["top_themes_by_bank"].exists()
    assert outputs["average_rating_by_bank"].exists()
    assert outputs["sentiment_over_time"].exists()
