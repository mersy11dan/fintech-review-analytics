"""Sentiment analysis pipeline for cleaned bank review data."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
from typing import Protocol

import pandas as pd


LOGGER = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_NAME = "distilbert-base-uncased-finetuned-sst-2-english"


THEME_KEYWORDS = {
    "account_access": {"login", "password", "otp", "account", "verification"},
    "transactions": {"transfer", "payment", "send", "receive", "transaction"},
    "performance": {"slow", "crash", "bug", "error", "freeze", "failed"},
    "customer_support": {"support", "service", "help", "agent", "response"},
    "usability": {"easy", "simple", "interface", "design", "navigation"},
    "fees": {"fee", "charge", "cost", "expensive", "rate"},
}


@dataclass(frozen=True)
class SentimentConfig:
    """Runtime settings for the sentiment analysis pipeline."""

    input_path: str | Path = "data/processed/reviews_cleaned.csv"
    output_path: str | Path = "data/processed/reviews_with_sentiment.csv"
    model_name: str = DEFAULT_MODEL_NAME
    prefer_transformer: bool = True


class SentimentClassifier(Protocol):
    """Small interface that makes sentiment backends easy to test."""

    def predict(self, text: str) -> tuple[str, float]:
        """Return a normalized sentiment label and confidence-like score."""


def resolve_project_path(path: str | Path) -> Path:
    """Resolve project-relative paths while preserving absolute paths."""
    candidate = Path(path)
    return candidate if candidate.is_absolute() else PROJECT_ROOT / candidate


def identify_theme(review_text: str) -> str:
    """Assign a coarse theme using transparent keyword matching."""
    tokens = set(str(review_text).lower().split())
    for theme, keywords in THEME_KEYWORDS.items():
        if tokens.intersection(keywords):
            return theme
    return "general"


class TransformerSentimentClassifier:
    """Sentiment backend using the requested Hugging Face DistilBERT model."""

    def __init__(self, model_name: str = DEFAULT_MODEL_NAME) -> None:
        from transformers import pipeline

        self._classifier = pipeline("sentiment-analysis", model=model_name)

    def predict(self, text: str) -> tuple[str, float]:
        """Classify one review with DistilBERT SST-2."""
        result = self._classifier(text[:512])[0]
        label = result["label"].lower()
        return label, float(result["score"])


class VaderSentimentClassifier:
    """Fallback sentiment backend using VADER."""

    def __init__(self) -> None:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

        self._analyzer = SentimentIntensityAnalyzer()

    def predict(self, text: str) -> tuple[str, float]:
        """Classify one review with VADER compound score."""
        compound = float(self._analyzer.polarity_scores(text)["compound"])
        if compound >= 0.05:
            return "positive", compound
        if compound <= -0.05:
            return "negative", abs(compound)
        return "neutral", 1.0 - abs(compound)


class TextBlobSentimentClassifier:
    """Secondary fallback sentiment backend using TextBlob polarity."""

    def predict(self, text: str) -> tuple[str, float]:
        """Classify one review with TextBlob polarity."""
        from textblob import TextBlob

        polarity = float(TextBlob(text).sentiment.polarity)
        if polarity > 0:
            return "positive", polarity
        if polarity < 0:
            return "negative", abs(polarity)
        return "neutral", 1.0


def build_sentiment_classifier(config: SentimentConfig) -> SentimentClassifier:
    """Create the best available classifier, falling back when needed."""
    if config.prefer_transformer:
        try:
            LOGGER.info("Loading transformer sentiment model: %s", config.model_name)
            return TransformerSentimentClassifier(config.model_name)
        except Exception as exc:
            LOGGER.warning("Transformer sentiment model unavailable: %s", exc)

    try:
        LOGGER.info("Using VADER sentiment fallback")
        return VaderSentimentClassifier()
    except Exception as exc:
        LOGGER.warning("VADER sentiment fallback unavailable: %s", exc)
        LOGGER.info("Using TextBlob sentiment fallback")
        return TextBlobSentimentClassifier()


def classify_compound_score(score: float) -> str:
    """Convert a VADER compound score into a sentiment label."""
    if score >= 0.05:
        return "positive"
    if score <= -0.05:
        return "negative"
    return "neutral"


def score_sentiment(text: str) -> dict[str, float | str]:
    """Score one review with VADER for lightweight pipeline compatibility."""
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

    analyzer = SentimentIntensityAnalyzer()
    scores = analyzer.polarity_scores(text or "")
    return {**scores, "sentiment": classify_compound_score(scores["compound"])}


def add_sentiment_scores(frame: pd.DataFrame, text_column: str = "review") -> pd.DataFrame:
    """Append VADER scores and labels to a DataFrame."""
    if text_column not in frame.columns:
        raise ValueError(f"Missing required text column: {text_column}")

    scored = frame.copy()
    sentiment_frame = pd.DataFrame(scored[text_column].map(score_sentiment).to_list())
    return scored.join(sentiment_frame)


def get_review_column(frame: pd.DataFrame) -> str:
    """Find the review text column from cleaned or raw-like data."""
    for column in ("review", "review_text", "content"):
        if column in frame.columns:
            return column
    raise ValueError("Input data must contain one of: review, review_text, content")


def add_sentiment_columns(
    frame: pd.DataFrame,
    classifier: SentimentClassifier,
    review_column: str | None = None,
) -> pd.DataFrame:
    """Add review_id, sentiment columns, and identified theme to reviews."""
    text_column = review_column or get_review_column(frame)
    output = frame.copy().reset_index(drop=True)
    review_text = output[text_column].fillna("").astype(str)

    output["review_id"] = range(1, len(output) + 1)
    output["review_text"] = review_text

    predictions = review_text.map(classifier.predict)
    output["sentiment_label"] = predictions.map(lambda item: item[0])
    output["sentiment_score"] = predictions.map(lambda item: item[1])
    output["identified_theme"] = review_text.map(identify_theme)

    return output[
        ["review_id", "review_text", "sentiment_label", "sentiment_score", "identified_theme"]
    ]


def run_sentiment_pipeline(
    config: SentimentConfig = SentimentConfig(),
    classifier: SentimentClassifier | None = None,
) -> pd.DataFrame:
    """Read cleaned reviews, score sentiment, identify themes, and save CSV output."""
    input_path = resolve_project_path(config.input_path)
    output_path = resolve_project_path(config.output_path)

    LOGGER.info("Reading cleaned reviews from %s", input_path)
    reviews = pd.read_csv(input_path)
    active_classifier = classifier or build_sentiment_classifier(config)
    scored = add_sentiment_columns(reviews, active_classifier)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    scored.to_csv(output_path, index=False)
    LOGGER.info("Saved sentiment output to %s", output_path)
    return scored
