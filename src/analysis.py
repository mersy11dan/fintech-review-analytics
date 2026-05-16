"""Report-ready analysis helpers for processed bank review data."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import os
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sqlalchemy import create_engine, text


LOGGER = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SENTIMENT_ORDER = ["positive", "neutral", "negative"]
DEFAULT_PROCESSED_PATH = Path("data/processed/reviews_with_sentiment.csv")


@dataclass(frozen=True)
class AnalysisConfig:
    """Runtime settings for generating analysis outputs."""

    input_path: str | Path = DEFAULT_PROCESSED_PATH
    output_dir: str | Path = "reports"
    top_n: int = 5
    env_var: str = "DATABASE_URL"


def resolve_project_path(path: str | Path) -> Path:
    """Resolve project-relative paths while preserving absolute paths."""
    candidate = Path(path)
    return candidate if candidate.is_absolute() else PROJECT_ROOT / candidate


def normalize_analysis_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize likely pipeline columns into a consistent analysis schema."""
    renamed = frame.copy()
    if "bank" not in renamed.columns:
        renamed = renamed.rename(columns={"app_name": "bank", "bank_name": "bank"})
    if "review_text" not in renamed.columns:
        renamed = renamed.rename(columns={"review": "review_text"})
    if "review_date" not in renamed.columns:
        renamed = renamed.rename(columns={"date": "review_date"})
    required = {"bank", "rating", "sentiment_label"}
    missing = required.difference(renamed.columns)
    if missing:
        raise ValueError(f"Processed data is missing required columns: {sorted(missing)}")

    if "identified_theme" not in renamed.columns:
        renamed["identified_theme"] = "unassigned"
    if "review_text" not in renamed.columns:
        renamed["review_text"] = ""

    renamed["sentiment_label"] = renamed["sentiment_label"].astype(str).str.lower()
    renamed["rating"] = pd.to_numeric(renamed["rating"], errors="coerce")
    if "sentiment_score" not in renamed.columns:
        renamed["sentiment_score"] = pd.NA
    renamed["sentiment_score"] = pd.to_numeric(renamed["sentiment_score"], errors="coerce")
    if "review_date" in renamed.columns:
        renamed["review_date"] = pd.to_datetime(renamed["review_date"], errors="coerce")
    return renamed


def load_processed_reviews(input_path: str | Path) -> pd.DataFrame:
    """Load processed reviews from CSV and standardize column names."""
    frame = pd.read_csv(resolve_project_path(input_path))
    return normalize_analysis_columns(frame)


def load_reviews_from_postgres(env_var: str = "DATABASE_URL") -> pd.DataFrame:
    """Load analyzed review rows from PostgreSQL using DATABASE_URL."""
    from dotenv import load_dotenv

    load_dotenv()
    database_url = os.getenv(env_var)
    if not database_url:
        raise RuntimeError(
            f"{env_var} is not set and {DEFAULT_PROCESSED_PATH} was not found. "
            "Create the processed CSV or set DATABASE_URL to load from PostgreSQL."
        )

    query = text(
        """
        SELECT
            b.bank_name AS bank,
            b.app_name,
            r.review_id,
            r.review_text,
            r.rating,
            r.review_date,
            r.sentiment_label,
            r.sentiment_score,
            r.identified_theme,
            r.source
        FROM reviews AS r
        JOIN banks AS b
            ON r.bank_id = b.bank_id
        """
    )
    engine = create_engine(database_url)
    with engine.begin() as connection:
        frame = pd.read_sql(query, connection)
    return normalize_analysis_columns(frame)


def load_analysis_dataset(
    input_path: str | Path = DEFAULT_PROCESSED_PATH,
    env_var: str = "DATABASE_URL",
) -> pd.DataFrame:
    """Load analysis data from CSV first, then PostgreSQL when the CSV is missing."""
    resolved_input = resolve_project_path(input_path)
    if resolved_input.exists():
        LOGGER.info("Loading analysis data from CSV: %s", resolved_input)
        return load_processed_reviews(resolved_input)

    LOGGER.info("Processed CSV not found at %s; attempting PostgreSQL fallback", resolved_input)
    return load_reviews_from_postgres(env_var=env_var)


def sentiment_distribution_by_bank(frame: pd.DataFrame) -> pd.DataFrame:
    """Count sentiment labels for each bank."""
    table = pd.crosstab(frame["bank"], frame["sentiment_label"])
    return table.reindex(columns=SENTIMENT_ORDER, fill_value=0)


def sentiment_by_rating(frame: pd.DataFrame) -> pd.DataFrame:
    """Count sentiment labels by numeric app rating."""
    table = pd.crosstab(frame["rating"], frame["sentiment_label"])
    table = table.reindex(columns=SENTIMENT_ORDER, fill_value=0)
    return table.sort_index()


def top_themes_per_bank(frame: pd.DataFrame, top_n: int = 5) -> pd.DataFrame:
    """Return the most common themes for each bank."""
    counts = (
        frame.groupby(["bank", "identified_theme"])
        .size()
        .reset_index(name="review_count")
        .sort_values(["bank", "review_count"], ascending=[True, False])
    )
    return counts.groupby("bank", as_index=False).head(top_n).reset_index(drop=True)


def extract_top_keywords(texts: pd.Series, top_n: int = 5) -> list[str]:
    """Extract frequent complaint keywords or phrases from a group of reviews."""
    clean_texts = texts.fillna("").astype(str).str.strip()
    clean_texts = clean_texts[clean_texts.ne("")]
    if clean_texts.empty:
        return []

    vectorizer = CountVectorizer(stop_words="english", ngram_range=(1, 2), max_features=50)
    try:
        matrix = vectorizer.fit_transform(clean_texts)
    except ValueError:
        return []
    scores = matrix.sum(axis=0).A1
    terms = vectorizer.get_feature_names_out()
    ranked = sorted(zip(terms, scores), key=lambda item: item[1], reverse=True)
    return [term for term, _score in ranked[:top_n]]


def _top_values(values: pd.Series, top_n: int) -> list[str]:
    """Return top non-empty values from a Series."""
    clean = values.dropna().astype(str)
    clean = clean[clean.str.strip().ne("")]
    return clean.value_counts().head(top_n).index.tolist()


def build_bank_recommendation_summary(frame: pd.DataFrame, top_n: int = 5) -> pd.DataFrame:
    """Build bank-specific metrics, drivers, pain points, and complaint keywords."""
    data = normalize_analysis_columns(frame)
    rows: list[dict[str, object]] = []

    for bank, bank_reviews in data.groupby("bank"):
        sentiment_counts = bank_reviews["sentiment_label"].value_counts()
        positive_reviews = bank_reviews[bank_reviews["sentiment_label"].eq("positive")]
        negative_reviews = bank_reviews[bank_reviews["sentiment_label"].eq("negative")]

        satisfaction_drivers = _top_values(positive_reviews["identified_theme"], top_n=2)
        pain_points = _top_values(negative_reviews["identified_theme"], top_n=2)
        complaint_keywords = extract_top_keywords(negative_reviews["review_text"], top_n=top_n)
        top_themes = _top_values(bank_reviews["identified_theme"], top_n=top_n)

        rows.append(
            {
                "bank": bank,
                "review_count": int(len(bank_reviews)),
                "average_rating": round(float(bank_reviews["rating"].mean()), 2),
                "positive_count": int(sentiment_counts.get("positive", 0)),
                "neutral_count": int(sentiment_counts.get("neutral", 0)),
                "negative_count": int(sentiment_counts.get("negative", 0)),
                "positive_share": round(float(sentiment_counts.get("positive", 0) / len(bank_reviews)), 3),
                "negative_share": round(float(sentiment_counts.get("negative", 0) / len(bank_reviews)), 3),
                "average_sentiment_score": round(float(bank_reviews["sentiment_score"].mean()), 3)
                if bank_reviews["sentiment_score"].notna().any()
                else pd.NA,
                "top_themes": "; ".join(top_themes),
                "top_complaint_keywords": "; ".join(complaint_keywords),
                "satisfaction_drivers": "; ".join(satisfaction_drivers),
                "pain_points": "; ".join(pain_points),
            }
        )

    return pd.DataFrame(rows).sort_values(["review_count", "bank"], ascending=[False, True])


def validate_analysis_data(frame: pd.DataFrame) -> None:
    """Fail early with useful messages instead of inventing findings."""
    if frame.empty:
        raise ValueError("No review rows were found. Generate/load data before running analysis.")

    required = {"bank", "rating", "review_text", "sentiment_label", "identified_theme"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Analysis data is missing required columns: {sorted(missing)}")

    if frame["bank"].dropna().empty:
        raise ValueError("Analysis data has no bank names.")
    if frame["sentiment_label"].dropna().empty:
        raise ValueError("Analysis data has no sentiment labels.")


def summarize_patterns(frame: pd.DataFrame, top_n: int = 3) -> list[str]:
    """Build concise report bullets for positive and negative review patterns."""
    bullets: list[str] = []

    for bank, bank_reviews in frame.groupby("bank"):
        positive = bank_reviews[bank_reviews["sentiment_label"].eq("positive")]
        negative = bank_reviews[bank_reviews["sentiment_label"].eq("negative")]

        positive_themes = positive["identified_theme"].value_counts().head(top_n)
        negative_themes = negative["identified_theme"].value_counts().head(top_n)

        positive_text = ", ".join(positive_themes.index) if not positive_themes.empty else "none recorded"
        negative_text = ", ".join(negative_themes.index) if not negative_themes.empty else "none recorded"

        bullets.append(
            f"- {bank}: positive reviews most often mention {positive_text}; "
            f"negative reviews most often mention {negative_text}."
        )

    return bullets


def dataframe_to_markdown(frame: pd.DataFrame) -> str:
    """Render a small DataFrame as a markdown table without extra dependencies."""
    if frame.empty:
        return "_No rows available._"

    string_frame = frame.reset_index().astype(str) if frame.index.name else frame.astype(str)
    headers = list(string_frame.columns)
    separator = ["---"] * len(headers)
    rows = [headers, separator] + string_frame.values.tolist()
    return "\n".join("| " + " | ".join(row) + " |" for row in rows)


def save_sentiment_distribution_plot(table: pd.DataFrame, output_path: Path) -> None:
    """Save a stacked bar chart of sentiment distribution by bank."""
    axis = table.plot(kind="bar", stacked=True, figsize=(10, 6))
    axis.set_title("Sentiment Distribution by Bank")
    axis.set_xlabel("Bank")
    axis.set_ylabel("Review Count")
    axis.legend(title="Sentiment")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def save_sentiment_by_rating_plot(table: pd.DataFrame, output_path: Path) -> None:
    """Save a stacked bar chart of sentiment by app rating."""
    axis = table.plot(kind="bar", stacked=True, figsize=(10, 6))
    axis.set_title("Sentiment by Rating")
    axis.set_xlabel("Rating")
    axis.set_ylabel("Review Count")
    axis.legend(title="Sentiment")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def save_top_themes_plot(table: pd.DataFrame, output_path: Path) -> None:
    """Save a horizontal bar chart of top themes by bank."""
    plot_frame = table.copy()
    plot_frame["label"] = plot_frame["bank"] + " - " + plot_frame["identified_theme"]
    plot_frame = plot_frame.sort_values("review_count", ascending=True)

    axis = plot_frame.plot.barh(x="label", y="review_count", legend=False, figsize=(10, 7))
    axis.set_title("Top Themes by Bank")
    axis.set_xlabel("Review Count")
    axis.set_ylabel("Bank and Theme")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def write_markdown_report(
    output_path: Path,
    sentiment_bank: pd.DataFrame,
    sentiment_rating: pd.DataFrame,
    top_themes: pd.DataFrame,
    pattern_bullets: list[str],
) -> None:
    """Write report-ready markdown summaries and tables."""
    content = [
        "# Bank Review Analysis Summary",
        "",
        "## Main Positive and Negative Patterns",
        "",
        *pattern_bullets,
        "",
        "## Sentiment Distribution by Bank",
        "",
        dataframe_to_markdown(sentiment_bank),
        "",
        "## Sentiment by Rating",
        "",
        dataframe_to_markdown(sentiment_rating),
        "",
        "## Top Themes per Bank",
        "",
        dataframe_to_markdown(top_themes),
        "",
        "## Generated Plots",
        "",
        "- `figures/sentiment_distribution_by_bank.png`",
        "- `figures/sentiment_by_rating.png`",
        "- `figures/top_themes_by_bank.png`",
    ]
    output_path.write_text("\n".join(content), encoding="utf-8")


def write_recommendation_markdown(output_path: Path, summary: pd.DataFrame) -> None:
    """Write executive-ready bank recommendations from observed data."""
    content = [
        "# Bank Review Recommendation Inputs",
        "",
        "This summary is generated only from available processed reviews or PostgreSQL data.",
        "",
    ]

    for row in summary.to_dict(orient="records"):
        content.extend(
            [
                f"## {row['bank']}",
                "",
                f"- Review count: {row['review_count']}",
                f"- Average rating: {row['average_rating']}",
                (
                    "- Sentiment mix: "
                    f"{row['positive_count']} positive, {row['neutral_count']} neutral, "
                    f"{row['negative_count']} negative"
                ),
                f"- Average sentiment score: {row['average_sentiment_score']}",
                f"- Top themes: {row['top_themes'] or 'Not enough theme data'}",
                f"- Top complaint keywords: {row['top_complaint_keywords'] or 'Not enough negative review text'}",
                f"- Likely satisfaction drivers: {row['satisfaction_drivers'] or 'Not enough positive review themes'}",
                f"- Likely pain points: {row['pain_points'] or 'Not enough negative review themes'}",
                "",
            ]
        )

    output_path.write_text("\n".join(content), encoding="utf-8")


def run_review_analysis(config: AnalysisConfig = AnalysisConfig()) -> dict[str, Path]:
    """Generate report tables, markdown, and plots from processed reviews."""
    reviews = load_analysis_dataset(config.input_path, env_var=config.env_var)
    validate_analysis_data(reviews)
    output_dir = resolve_project_path(config.output_dir)
    figures_dir = output_dir / "figures"
    output_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    sentiment_bank = sentiment_distribution_by_bank(reviews)
    sentiment_rating = sentiment_by_rating(reviews)
    top_themes = top_themes_per_bank(reviews, top_n=config.top_n)
    pattern_bullets = summarize_patterns(reviews)
    recommendation_summary = build_bank_recommendation_summary(reviews, top_n=config.top_n)

    sentiment_bank_path = output_dir / "sentiment_distribution_by_bank.csv"
    sentiment_rating_path = output_dir / "sentiment_by_rating.csv"
    top_themes_path = output_dir / "top_themes_per_bank.csv"
    recommendation_summary_path = output_dir / "bank_recommendation_inputs.csv"
    report_path = output_dir / "analysis_summary.md"
    recommendation_markdown_path = output_dir / "bank_recommendation_inputs.md"

    sentiment_bank.to_csv(sentiment_bank_path)
    sentiment_rating.to_csv(sentiment_rating_path)
    top_themes.to_csv(top_themes_path, index=False)
    recommendation_summary.to_csv(recommendation_summary_path, index=False)

    save_sentiment_distribution_plot(
        sentiment_bank,
        figures_dir / "sentiment_distribution_by_bank.png",
    )
    save_sentiment_by_rating_plot(sentiment_rating, figures_dir / "sentiment_by_rating.png")
    save_top_themes_plot(top_themes, figures_dir / "top_themes_by_bank.png")
    write_markdown_report(report_path, sentiment_bank, sentiment_rating, top_themes, pattern_bullets)
    write_recommendation_markdown(recommendation_markdown_path, recommendation_summary)

    return {
        "report": report_path,
        "recommendation_report": recommendation_markdown_path,
        "recommendation_summary": recommendation_summary_path,
        "sentiment_by_bank": sentiment_bank_path,
        "sentiment_by_rating": sentiment_rating_path,
        "top_themes": top_themes_path,
        "figures": figures_dir,
    }
