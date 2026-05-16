"""Publication-ready visualization helpers for bank review analytics."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SENTIMENT_ORDER = ["positive", "neutral", "negative"]


@dataclass(frozen=True)
class VisualizationConfig:
    """Runtime settings for generating review analysis plots."""

    input_path: str | Path = "data/processed/reviews_with_sentiment.csv"
    output_dir: str | Path = "reports/figures"
    top_n: int = 5


def resolve_project_path(path: str | Path) -> Path:
    """Resolve project-relative paths while preserving absolute paths."""
    candidate = Path(path)
    return candidate if candidate.is_absolute() else PROJECT_ROOT / candidate


def normalize_visual_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize common pipeline column names for plotting."""
    normalized = frame.rename(
        columns={
            "review": "review_text",
            "app_name": "bank",
            "date": "review_date",
        }
    ).copy()

    required = {"bank", "rating", "sentiment_label"}
    missing = required.difference(normalized.columns)
    if missing:
        raise ValueError(f"Missing required visualization columns: {sorted(missing)}")

    if "identified_theme" not in normalized.columns:
        normalized["identified_theme"] = "unassigned"
    if "review_date" in normalized.columns:
        normalized["review_date"] = pd.to_datetime(normalized["review_date"], errors="coerce")

    normalized["rating"] = pd.to_numeric(normalized["rating"], errors="coerce")
    normalized["sentiment_label"] = normalized["sentiment_label"].astype(str).str.lower()
    return normalized


def load_visualization_data(input_path: str | Path) -> pd.DataFrame:
    """Load processed review data and normalize it for visualization."""
    return normalize_visual_columns(pd.read_csv(resolve_project_path(input_path)))


def set_publication_style() -> None:
    """Apply a clean visual style suitable for stakeholder reports."""
    sns.set_theme(style="whitegrid", context="talk")
    plt.rcParams.update(
        {
            "figure.dpi": 120,
            "savefig.dpi": 180,
            "axes.titleweight": "bold",
            "axes.labelsize": 12,
            "axes.titlesize": 15,
            "legend.frameon": True,
        }
    )


def save_figure(figure: plt.Figure, output_path: Path) -> Path:
    """Save a figure with tight layout and close it to free memory."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.tight_layout()
    figure.savefig(output_path, bbox_inches="tight")
    plt.close(figure)
    return output_path


def plot_sentiment_distribution_by_bank(frame: pd.DataFrame, output_path: str | Path) -> Path:
    """Save a grouped bar chart of sentiment distribution by bank."""
    data = normalize_visual_columns(frame)
    figure, axis = plt.subplots(figsize=(11, 6))
    sns.countplot(
        data=data,
        x="bank",
        hue="sentiment_label",
        hue_order=SENTIMENT_ORDER,
        ax=axis,
        palette="Set2",
    )
    axis.set_title("Sentiment Distribution by Bank")
    axis.set_xlabel("Bank")
    axis.set_ylabel("Number of Reviews")
    axis.tick_params(axis="x", rotation=20)
    axis.legend(title="Sentiment")
    return save_figure(figure, resolve_project_path(output_path))


def plot_rating_distribution_by_bank(frame: pd.DataFrame, output_path: str | Path) -> Path:
    """Save a grouped bar chart of rating distribution by bank."""
    data = normalize_visual_columns(frame).dropna(subset=["rating"])
    data["rating"] = data["rating"].astype(int)

    figure, axis = plt.subplots(figsize=(11, 6))
    sns.countplot(data=data, x="bank", hue="rating", hue_order=[1, 2, 3, 4, 5], ax=axis)
    axis.set_title("Rating Distribution by Bank")
    axis.set_xlabel("Bank")
    axis.set_ylabel("Number of Reviews")
    axis.tick_params(axis="x", rotation=20)
    axis.legend(title="Rating")
    return save_figure(figure, resolve_project_path(output_path))


def plot_top_themes_by_bank(frame: pd.DataFrame, output_path: str | Path, top_n: int = 5) -> Path:
    """Save a horizontal bar chart of top theme frequency by bank."""
    data = normalize_visual_columns(frame)
    theme_counts = (
        data.groupby(["bank", "identified_theme"])
        .size()
        .reset_index(name="review_count")
        .sort_values(["bank", "review_count"], ascending=[True, False])
    )
    top_themes = theme_counts.groupby("bank", as_index=False).head(top_n)
    top_themes["label"] = top_themes["bank"] + " - " + top_themes["identified_theme"]
    top_themes = top_themes.sort_values("review_count", ascending=True)

    figure, axis = plt.subplots(figsize=(12, 7))
    sns.barplot(
        data=top_themes,
        x="review_count",
        y="label",
        hue="label",
        ax=axis,
        palette="Blues_r",
        legend=False,
    )
    axis.set_title(f"Top {top_n} Themes by Bank")
    axis.set_xlabel("Number of Reviews")
    axis.set_ylabel("Bank and Theme")
    return save_figure(figure, resolve_project_path(output_path))


def can_plot_sentiment_over_time(frame: pd.DataFrame) -> bool:
    """Return whether the dataset has enough dated rows for a time trend."""
    data = normalize_visual_columns(frame)
    return "review_date" in data.columns and data["review_date"].dropna().nunique() >= 2


def plot_sentiment_over_time(frame: pd.DataFrame, output_path: str | Path) -> Path | None:
    """Save a monthly sentiment trend plot when enough date coverage exists."""
    data = normalize_visual_columns(frame)
    if not can_plot_sentiment_over_time(data):
        return None

    dated = data.dropna(subset=["review_date"]).copy()
    dated["month"] = dated["review_date"].dt.to_period("M").dt.to_timestamp()
    trend = dated.groupby(["month", "sentiment_label"]).size().reset_index(name="review_count")

    figure, axis = plt.subplots(figsize=(12, 6))
    sns.lineplot(
        data=trend,
        x="month",
        y="review_count",
        hue="sentiment_label",
        hue_order=SENTIMENT_ORDER,
        marker="o",
        ax=axis,
    )
    axis.set_title("Sentiment Trend Over Time")
    axis.set_xlabel("Month")
    axis.set_ylabel("Number of Reviews")
    axis.legend(title="Sentiment")
    return save_figure(figure, resolve_project_path(output_path))


def plot_average_rating_by_bank(frame: pd.DataFrame, output_path: str | Path) -> Path:
    """Save a bar chart of average rating by bank."""
    data = normalize_visual_columns(frame).dropna(subset=["rating"])
    averages = data.groupby("bank", as_index=False)["rating"].mean().sort_values("rating")

    figure, axis = plt.subplots(figsize=(10, 6))
    sns.barplot(
        data=averages,
        x="rating",
        y="bank",
        hue="bank",
        ax=axis,
        palette="Greens_r",
        legend=False,
    )
    axis.set_title("Average Rating by Bank")
    axis.set_xlabel("Average Rating")
    axis.set_ylabel("Bank")
    axis.set_xlim(0, 5)
    return save_figure(figure, resolve_project_path(output_path))


def generate_review_plots(config: VisualizationConfig = VisualizationConfig()) -> dict[str, Path]:
    """Generate all stakeholder-friendly review analysis plots."""
    set_publication_style()
    data = load_visualization_data(config.input_path)
    output_dir = resolve_project_path(config.output_dir)

    outputs: dict[str, Path] = {
        "sentiment_distribution_by_bank": plot_sentiment_distribution_by_bank(
            data,
            output_dir / "sentiment_distribution_by_bank.png",
        ),
        "rating_distribution_by_bank": plot_rating_distribution_by_bank(
            data,
            output_dir / "rating_distribution_by_bank.png",
        ),
        "top_themes_by_bank": plot_top_themes_by_bank(
            data,
            output_dir / "top_themes_by_bank.png",
            top_n=config.top_n,
        ),
        "average_rating_by_bank": plot_average_rating_by_bank(
            data,
            output_dir / "average_rating_by_bank.png",
        ),
    }

    sentiment_over_time = plot_sentiment_over_time(data, output_dir / "sentiment_over_time.png")
    if sentiment_over_time is not None:
        outputs["sentiment_over_time"] = sentiment_over_time

    return outputs
