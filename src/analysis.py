"""Report-ready analysis helpers for processed bank review data."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SENTIMENT_ORDER = ["positive", "neutral", "negative"]


@dataclass(frozen=True)
class AnalysisConfig:
    """Runtime settings for generating analysis outputs."""

    input_path: str | Path = "data/processed/reviews_with_sentiment.csv"
    output_dir: str | Path = "reports"
    top_n: int = 5


def resolve_project_path(path: str | Path) -> Path:
    """Resolve project-relative paths while preserving absolute paths."""
    candidate = Path(path)
    return candidate if candidate.is_absolute() else PROJECT_ROOT / candidate


def normalize_analysis_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize likely pipeline columns into a consistent analysis schema."""
    renamed = frame.rename(columns={"app_name": "bank", "review": "review_text"}).copy()
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
    return renamed


def load_processed_reviews(input_path: str | Path) -> pd.DataFrame:
    """Load processed reviews from CSV and standardize column names."""
    frame = pd.read_csv(resolve_project_path(input_path))
    return normalize_analysis_columns(frame)


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


def run_review_analysis(config: AnalysisConfig = AnalysisConfig()) -> dict[str, Path]:
    """Generate report tables, markdown, and plots from processed reviews."""
    reviews = load_processed_reviews(config.input_path)
    output_dir = resolve_project_path(config.output_dir)
    figures_dir = output_dir / "figures"
    output_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    sentiment_bank = sentiment_distribution_by_bank(reviews)
    sentiment_rating = sentiment_by_rating(reviews)
    top_themes = top_themes_per_bank(reviews, top_n=config.top_n)
    pattern_bullets = summarize_patterns(reviews)

    sentiment_bank_path = output_dir / "sentiment_distribution_by_bank.csv"
    sentiment_rating_path = output_dir / "sentiment_by_rating.csv"
    top_themes_path = output_dir / "top_themes_per_bank.csv"
    report_path = output_dir / "analysis_summary.md"

    sentiment_bank.to_csv(sentiment_bank_path)
    sentiment_rating.to_csv(sentiment_rating_path)
    top_themes.to_csv(top_themes_path, index=False)

    save_sentiment_distribution_plot(
        sentiment_bank,
        figures_dir / "sentiment_distribution_by_bank.png",
    )
    save_sentiment_by_rating_plot(sentiment_rating, figures_dir / "sentiment_by_rating.png")
    save_top_themes_plot(top_themes, figures_dir / "top_themes_by_bank.png")
    write_markdown_report(report_path, sentiment_bank, sentiment_rating, top_themes, pattern_bullets)

    return {
        "report": report_path,
        "sentiment_by_bank": sentiment_bank_path,
        "sentiment_by_rating": sentiment_rating_path,
        "top_themes": top_themes_path,
        "figures": figures_dir,
    }
