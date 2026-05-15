"""Tests for report-ready review analysis helpers."""

import pandas as pd

from src.analysis import (
    AnalysisConfig,
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
    assert (outputs["figures"] / "sentiment_distribution_by_bank.png").exists()


def test_load_processed_reviews_accepts_review_column_alias(tmp_path):
    input_path = tmp_path / "reviews.csv"
    sample_reviews().rename(columns={"review_text": "review"}).to_csv(input_path, index=False)

    loaded = load_processed_reviews(input_path)

    assert "review_text" in loaded.columns
