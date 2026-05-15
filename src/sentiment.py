"""Sentiment analysis utilities for customer reviews."""

from __future__ import annotations


def classify_compound_score(score: float) -> str:
    """Convert a VADER compound score into a sentiment label."""
    if score >= 0.05:
        return "positive"
    if score <= -0.05:
        return "negative"
    return "neutral"


def score_sentiment(text: str) -> dict[str, float | str]:
    """Score one review with VADER sentiment analysis."""
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

    analyzer = SentimentIntensityAnalyzer()
    scores = analyzer.polarity_scores(text or "")
    return {
        **scores,
        "sentiment": classify_compound_score(scores["compound"]),
    }


def add_sentiment_scores(frame, text_column: str = "clean_text"):
    """Append sentiment scores and labels to a DataFrame."""
    import pandas as pd

    if text_column not in frame.columns:
        raise ValueError(f"Missing required text column: {text_column}")

    scored = frame.copy()
    sentiment_frame = pd.DataFrame(scored[text_column].map(score_sentiment).to_list())
    return scored.join(sentiment_frame)
