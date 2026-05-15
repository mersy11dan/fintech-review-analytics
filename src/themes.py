"""Thematic analysis for bank app reviews using TF-IDF n-grams."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer


PROJECT_ROOT = Path(__file__).resolve().parents[1]

THEME_GROUPING_EXPLANATION = """
## Theme Grouping Logic

The thematic analysis first extracts recurring one-word and two-word phrases per
bank using TF-IDF. Extracted phrases are then matched to business-relevant theme
categories with transparent keyword rules. Each review is mapped to the theme
whose seed words and extracted keywords appear most often in the review text. If
no category matches, the review is assigned to `general_feedback`.
""".strip()

THEME_SEEDS = {
    "login_issues": {
        "login",
        "log in",
        "password",
        "otp",
        "pin",
        "verification",
        "authentication",
        "account",
    },
    "transfer_speed": {
        "transfer",
        "transaction",
        "payment",
        "send",
        "receive",
        "slow",
        "fast",
        "delay",
    },
    "ui_design": {
        "ui",
        "interface",
        "design",
        "screen",
        "navigation",
        "easy",
        "simple",
        "user friendly",
    },
    "customer_support": {
        "support",
        "service",
        "help",
        "agent",
        "response",
        "call center",
        "customer",
    },
    "feature_requests": {
        "feature",
        "add",
        "need",
        "request",
        "update",
        "option",
        "balance",
        "statement",
    },
}

DEFAULT_THEME_KEYWORDS = {
    "onboarding": {"register", "login", "signup", "verification", "kyc"},
    "transactions": {"transfer", "payment", "send", "receive", "transaction"},
    "reliability": {"crash", "bug", "slow", "error", "failed", "freeze"},
    "support": {"support", "help", "service", "agent", "response"},
    "pricing": {"fee", "charge", "cost", "rate", "expensive"},
    "usability": {"easy", "interface", "design", "navigation", "simple"},
}


@dataclass(frozen=True)
class ThemeAnalysisConfig:
    """Runtime settings for thematic analysis."""

    input_path: str | Path = "data/processed/reviews_cleaned.csv"
    output_path: str | Path = "data/processed/reviews_with_themes.csv"
    explanation_path: str | Path = "data/processed/theme_grouping_logic.md"
    max_features: int = 40
    ngram_min: int = 1
    ngram_max: int = 2
    min_themes_per_bank: int = 3
    max_themes_per_bank: int = 5


def resolve_project_path(path: str | Path) -> Path:
    """Resolve project-relative paths while preserving absolute paths."""
    candidate = Path(path)
    return candidate if candidate.is_absolute() else PROJECT_ROOT / candidate


def get_review_column(frame: pd.DataFrame) -> str:
    """Find the review text column in cleaned or sentiment-enriched data."""
    for column in ("review", "review_text", "content"):
        if column in frame.columns:
            return column
    raise ValueError("Input data must contain one of: review, review_text, content")


def get_bank_column(frame: pd.DataFrame) -> str:
    """Find the bank/app name column."""
    for column in ("bank", "app_name"):
        if column in frame.columns:
            return column
    raise ValueError("Input data must contain one of: bank, app_name")


def normalize_text(text: object) -> str:
    """Normalize review text for keyword matching."""
    return re.sub(r"\s+", " ", str(text).lower()).strip()


def extract_themes(text: str, theme_keywords: dict[str, set[str]] | None = None) -> list[str]:
    """Return matching lightweight business themes for one cleaned review."""
    keywords = theme_keywords or DEFAULT_THEME_KEYWORDS
    tokens = set((text or "").lower().split())
    return [theme for theme, words in keywords.items() if tokens.intersection(words)]


def add_theme_labels(frame: pd.DataFrame, text_column: str = "review") -> pd.DataFrame:
    """Append lightweight keyword theme labels to a DataFrame."""
    if text_column not in frame.columns:
        raise ValueError(f"Missing required text column: {text_column}")

    themed = frame.copy()
    themed["themes"] = themed[text_column].map(extract_themes)
    return themed


def extract_tfidf_keywords(
    reviews: pd.Series,
    max_features: int = 40,
    ngram_range: tuple[int, int] = (1, 2),
) -> list[str]:
    """Extract recurring keywords and phrases from reviews with TF-IDF."""
    clean_reviews = reviews.fillna("").astype(str).map(normalize_text)
    clean_reviews = clean_reviews[clean_reviews.ne("")]

    if clean_reviews.empty:
        return []

    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=ngram_range,
        max_features=max_features,
    )
    matrix = vectorizer.fit_transform(clean_reviews)
    scores = matrix.mean(axis=0).A1
    terms = vectorizer.get_feature_names_out()
    ranked = sorted(zip(terms, scores), key=lambda item: item[1], reverse=True)
    return [term for term, score in ranked if score > 0]


def group_keywords_into_themes(
    keywords: list[str],
    min_themes: int = 3,
    max_themes: int = 5,
) -> dict[str, list[str]]:
    """Group extracted keywords into business-relevant theme categories."""
    grouped: dict[str, list[str]] = {theme: [] for theme in THEME_SEEDS}

    for keyword in keywords:
        for theme, seeds in THEME_SEEDS.items():
            if any(seed in keyword for seed in seeds):
                grouped[theme].append(keyword)
                break

    grouped = {theme: terms for theme, terms in grouped.items() if terms}
    ranked_themes = sorted(grouped.items(), key=lambda item: len(item[1]), reverse=True)
    selected = dict(ranked_themes[:max_themes])

    for theme in THEME_SEEDS:
        if len(selected) >= min_themes:
            break
        selected.setdefault(theme, [])

    return selected


def build_bank_theme_map(
    frame: pd.DataFrame,
    config: ThemeAnalysisConfig,
) -> dict[str, dict[str, list[str]]]:
    """Build theme keyword groups for each bank."""
    review_column = get_review_column(frame)
    bank_column = get_bank_column(frame)
    theme_map: dict[str, dict[str, list[str]]] = {}

    for bank, bank_reviews in frame.groupby(bank_column):
        keywords = extract_tfidf_keywords(
            bank_reviews[review_column],
            max_features=config.max_features,
            ngram_range=(config.ngram_min, config.ngram_max),
        )
        theme_map[str(bank)] = group_keywords_into_themes(
            keywords,
            min_themes=config.min_themes_per_bank,
            max_themes=config.max_themes_per_bank,
        )

    return theme_map


def map_review_to_theme(
    review_text: str,
    bank: str,
    theme_map: dict[str, dict[str, list[str]]],
) -> str:
    """Map one review to the highest-scoring theme for its bank."""
    text = normalize_text(review_text)
    bank_themes = theme_map.get(str(bank), {})
    theme_scores: dict[str, int] = {}

    for theme, keywords in bank_themes.items():
        seeds = THEME_SEEDS.get(theme, set())
        terms = set(keywords).union(seeds)
        theme_scores[theme] = sum(1 for term in terms if term and term in text)

    if not theme_scores or max(theme_scores.values()) == 0:
        return "general_feedback"

    return max(theme_scores.items(), key=lambda item: item[1])[0]


def add_theme_columns(
    frame: pd.DataFrame,
    theme_map: dict[str, dict[str, list[str]]],
) -> pd.DataFrame:
    """Add review IDs, normalized review text, and mapped themes."""
    review_column = get_review_column(frame)
    bank_column = get_bank_column(frame)
    output = frame.copy().reset_index(drop=True)

    if "review_id" not in output.columns:
        output["review_id"] = range(1, len(output) + 1)

    output["review_text"] = output[review_column].fillna("").astype(str)
    output["bank"] = output[bank_column].astype(str)
    output["identified_theme"] = output.apply(
        lambda row: map_review_to_theme(row["review_text"], row["bank"], theme_map),
        axis=1,
    )
    output["theme_keywords"] = output.apply(
        lambda row: ", ".join(theme_map.get(row["bank"], {}).get(row["identified_theme"], [])),
        axis=1,
    )
    return output[["review_id", "bank", "review_text", "identified_theme", "theme_keywords"]]


def save_theme_outputs(
    themed_reviews: pd.DataFrame,
    explanation: str,
    output_path: str | Path,
    explanation_path: str | Path,
) -> None:
    """Save theme assignments and markdown grouping notes."""
    resolved_output = resolve_project_path(output_path)
    resolved_explanation = resolve_project_path(explanation_path)
    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    resolved_explanation.parent.mkdir(parents=True, exist_ok=True)

    themed_reviews.to_csv(resolved_output, index=False)
    resolved_explanation.write_text(explanation, encoding="utf-8")


def run_theme_analysis(config: ThemeAnalysisConfig = ThemeAnalysisConfig()) -> pd.DataFrame:
    """Read processed reviews, map themes, and save results to CSV."""
    input_path = resolve_project_path(config.input_path)
    reviews = pd.read_csv(input_path)
    theme_map = build_bank_theme_map(reviews, config)
    themed_reviews = add_theme_columns(reviews, theme_map)
    save_theme_outputs(
        themed_reviews,
        THEME_GROUPING_EXPLANATION,
        output_path=config.output_path,
        explanation_path=config.explanation_path,
    )
    return themed_reviews
