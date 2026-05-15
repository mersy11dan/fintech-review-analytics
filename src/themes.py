"""Theme extraction utilities for review analysis."""

from __future__ import annotations


DEFAULT_THEME_KEYWORDS = {
    "onboarding": {"register", "login", "signup", "verification", "kyc"},
    "transactions": {"transfer", "payment", "send", "receive", "transaction"},
    "reliability": {"crash", "bug", "slow", "error", "failed", "freeze"},
    "support": {"support", "help", "service", "agent", "response"},
    "pricing": {"fee", "charge", "cost", "rate", "expensive"},
    "usability": {"easy", "interface", "design", "navigation", "simple"},
}


def extract_themes(text: str, theme_keywords: dict[str, set[str]] | None = None) -> list[str]:
    """Return matching business themes for one cleaned review."""
    keywords = theme_keywords or DEFAULT_THEME_KEYWORDS
    tokens = set((text or "").lower().split())
    return [theme for theme, words in keywords.items() if tokens.intersection(words)]


def add_theme_labels(frame, text_column: str = "clean_text"):
    """Append a list of matched themes to each review row."""
    if text_column not in frame.columns:
        raise ValueError(f"Missing required text column: {text_column}")

    themed = frame.copy()
    themed["themes"] = themed[text_column].map(extract_themes)
    return themed
