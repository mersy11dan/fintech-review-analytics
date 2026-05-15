"""Visualization helpers for fintech review analytics."""

from __future__ import annotations


def plot_sentiment_distribution(frame, sentiment_column: str = "sentiment"):
    """Create a sentiment distribution bar chart."""
    import matplotlib.pyplot as plt
    import seaborn as sns

    if sentiment_column not in frame.columns:
        raise ValueError(f"Missing required sentiment column: {sentiment_column}")

    figure, axis = plt.subplots(figsize=(8, 5))
    order = ["positive", "neutral", "negative"]
    sns.countplot(data=frame, x=sentiment_column, order=order, ax=axis)
    axis.set_title("Review Sentiment Distribution")
    axis.set_xlabel("Sentiment")
    axis.set_ylabel("Review Count")
    figure.tight_layout()
    return figure
