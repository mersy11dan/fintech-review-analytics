"""Tests for sentiment analysis helpers."""

import pandas as pd

from src.sentiment import (
    SentimentConfig,
    add_sentiment_columns,
    identify_theme,
    run_sentiment_pipeline,
)


class FakeClassifier:
    """Predictable classifier for fast unit tests."""

    def predict(self, text: str) -> tuple[str, float]:
        if "bad" in text:
            return "negative", 0.91
        return "positive", 0.87


def test_sentiment_module_imports():
    import src.sentiment

    assert src.sentiment is not None


def test_identify_theme_matches_known_keywords():
    assert identify_theme("login otp problem") == "account_access"
    assert identify_theme("transfer failed again") == "transactions"
    assert identify_theme("nothing specific here") == "general"


def test_add_sentiment_columns_outputs_required_schema():
    frame = pd.DataFrame({"review": ["easy transfer", "bad login"], "bank": ["CBE", "Dashen"]})

    scored = add_sentiment_columns(frame, FakeClassifier())

    assert scored.columns.to_list()[:5] == [
        "review_id",
        "review_text",
        "sentiment_label",
        "sentiment_score",
        "identified_theme",
    ]
    assert "bank" in scored.columns
    assert scored["review_id"].to_list() == [1, 2]
    assert scored["sentiment_label"].to_list() == ["positive", "negative"]


def test_run_sentiment_pipeline_reads_and_writes_csv(tmp_path):
    input_path = tmp_path / "reviews_cleaned.csv"
    output_path = tmp_path / "reviews_with_sentiment.csv"
    pd.DataFrame({"review": ["easy app"]}).to_csv(input_path, index=False)

    scored = run_sentiment_pipeline(
        SentimentConfig(input_path=input_path, output_path=output_path),
        classifier=FakeClassifier(),
    )

    assert output_path.exists()
    assert scored.loc[0, "review_text"] == "easy app"
    assert scored.loc[0, "sentiment_label"] == "positive"
