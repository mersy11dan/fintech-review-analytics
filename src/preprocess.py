"""Text preprocessing helpers for review data."""

from __future__ import annotations

import re


WHITESPACE_RE = re.compile(r"\s+")
NON_TEXT_RE = re.compile(r"[^a-zA-Z0-9\s.,!?'-]")


def clean_review_text(text: object) -> str:
    """Normalize one review body into a clean text string."""
    if text is None:
        return ""

    cleaned = str(text).strip().lower()
    cleaned = NON_TEXT_RE.sub(" ", cleaned)
    cleaned = WHITESPACE_RE.sub(" ", cleaned)
    return cleaned.strip()


def preprocess_reviews(frame, text_column: str = "content"):
    """Clean review text and remove duplicate reviews from a DataFrame."""
    if text_column not in frame.columns:
        raise ValueError(f"Missing required text column: {text_column}")

    processed = frame.copy()
    processed["clean_text"] = processed[text_column].map(clean_review_text)
    processed = processed[processed["clean_text"].ne("")]
    return processed.drop_duplicates(subset=["clean_text"]).reset_index(drop=True)
