"""Tests for report-ready review analysis helpers."""

import pandas as pd
import pytest

from src.analysis import (
    AnalysisConfig,
    build_bank_recommendation_summary,
    load_analysis_dataset,
    load_processed_reviews,
    run_review_analysis,
    sentiment_by_rating,
    sentiment_distribution_by_bank,
    summarize_patterns,
    top_themes_per_bank,
)


def sample_reviews() -> pd.DataFrame:
    """Small synthetic dataset that mirrors processed pipeline output."""
    return pd.DataFrame(
        {
            "bank": ["CBE", "CBE", "Dashen", "Dashen"],
            "rating": [5, 1, 4, 2],
            "review_text": [
                "easy transfer",
                "login failure",
                "simple ui",
                "slow support",
            ],
            "sentiment_label": ["positive", "negative", "positive", "negative"],
            "sentiment_score": [0.95, 0.9, 0.88, 0.84],
            "identified_theme": [
                "transfer_speed",
                "login_issues",
                "ui_design",
                "customer_support",
            ],
        }
    )


def test_sentiment_distribution_by_bank_counts_labels():
    table = sentiment_distribution_by_bank(sample_reviews())

    assert table.loc["CBE", "positive"] == 1
    assert table.loc["CBE", "negative"] == 1
    assert table.loc["Dashen", "positive"] == 1


def test_sentiment_by_rating_counts_labels():
    table = sentiment_by_rating(sample_reviews())

    assert table.loc[5, "positive"] == 1
    assert table.loc[1, "negative"] == 1


def test_top_themes_per_bank_returns_ranked_themes():
    table = top_themes_per_bank(sample_reviews(), top_n=1)

    assert set(table["bank"]) == {"CBE", "Dashen"}
    assert table["review_count"].eq(1).all()


def test_summarize_patterns_returns_report_bullets():
    bullets = summarize_patterns(sample_reviews())

    assert any("CBE" in bullet for bullet in bullets)
    assert any("positive reviews" in bullet for bullet in bullets)


def test_run_review_analysis_writes_report_tables_and_plots(tmp_path):
    input_path = tmp_path / "reviews_with_sentiment.csv"
    output_dir = tmp_path / "reports"
    sample_reviews().to_csv(input_path, index=False)

    outputs = run_review_analysis(AnalysisConfig(input_path=input_path, output_dir=output_dir))

    assert outputs["report"].exists()
    assert outputs["sentiment_by_bank"].exists()
    assert outputs["sentiment_by_rating"].exists()
    assert outputs["top_themes"].exists()
    assert outputs["recommendation_summary"].exists()
    assert outputs["recommendation_report"].exists()
    assert (outputs["figures"] / "sentiment_distribution_by_bank.png").exists()


def test_load_processed_reviews_accepts_review_column_alias(tmp_path):
    input_path = tmp_path / "reviews.csv"
    sample_reviews().rename(columns={"review_text": "review"}).to_csv(input_path, index=False)

    loaded = load_processed_reviews(input_path)

    assert "review_text" in loaded.columns


def test_load_processed_reviews_handles_existing_review_text_and_review_alias(tmp_path):
    input_path = tmp_path / "reviews.csv"
    frame = sample_reviews()
    frame["review"] = frame["review_text"]
    frame.to_csv(input_path, index=False)

    loaded = load_processed_reviews(input_path)

    assert loaded["review_text"].to_list() == frame["review_text"].to_list()


def test_build_bank_recommendation_summary_uses_observed_themes_and_sentiment():
    summary = build_bank_recommendation_summary(sample_reviews(), top_n=3)

    cbe = summary[summary["bank"].eq("CBE")].iloc[0]

    assert cbe["review_count"] == 2
    assert cbe["average_rating"] == 3.0
    assert cbe["positive_count"] == 1
    assert cbe["negative_count"] == 1
    assert "transfer_speed" in cbe["satisfaction_drivers"]
    assert "login_issues" in cbe["pain_points"]
    assert "login" in cbe["top_complaint_keywords"]


def test_load_analysis_dataset_fails_helpfully_without_csv_or_database_url(tmp_path, monkeypatch):
    missing_input = tmp_path / "missing.csv"
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="DATABASE_URL is not set"):
        load_analysis_dataset(missing_input)
