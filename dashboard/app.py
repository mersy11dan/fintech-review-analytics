"""Executive Streamlit dashboard for fintech review analytics."""

from __future__ import annotations

import os
import re
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = PROJECT_ROOT / "reports"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
REVIEW_DATA_PATH = Path(os.getenv("REVIEW_DATA_PATH", PROCESSED_DIR / "reviews_with_sentiment.csv"))

BANK_ORDER = [
    "Commercial Bank of Ethiopia",
    "Bank of Abyssinia",
    "Dashen Bank",
]
SENTIMENT_ORDER = ["positive", "neutral", "negative"]
STOPWORDS = {
    "a",
    "an",
    "and",
    "app",
    "are",
    "bank",
    "banking",
    "be",
    "for",
    "from",
    "good",
    "i",
    "in",
    "is",
    "it",
    "my",
    "of",
    "on",
    "or",
    "the",
    "this",
    "to",
    "very",
    "with",
    "you",
}


st.set_page_config(
    page_title="Fintech Review Analytics",
    layout="wide",
)


@st.cache_data(show_spinner=False)
def load_csv(path: Path) -> pd.DataFrame:
    """Load a CSV file if it exists, otherwise return an empty frame."""
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def _numeric_value(text: str) -> float:
    """Extract the first numeric value from report text."""
    match = re.search(r"[-+]?\d*\.?\d+", text.replace(",", ""))
    return float(match.group()) if match else 0.0


def normalize_recommendations(recommendations: pd.DataFrame) -> pd.DataFrame:
    """Normalize bank summary numeric fields and add Dashen when missing."""
    if recommendations.empty:
        return recommendations

    recommendations = recommendations.copy()
    numeric_columns = [
        "review_count",
        "average_rating",
        "positive_count",
        "neutral_count",
        "negative_count",
        "positive_share",
        "negative_share",
        "average_sentiment_score",
    ]
    for column in numeric_columns:
        if column in recommendations.columns:
            recommendations[column] = pd.to_numeric(recommendations[column], errors="coerce").fillna(0)

    return add_missing_banks(recommendations)


def load_recommendations_from_markdown() -> pd.DataFrame:
    """Load bank KPI outputs from the committed Markdown summary for deployment."""
    path = REPORTS_DIR / "bank_recommendation_inputs.md"
    if not path.exists():
        return pd.DataFrame()

    rows: list[dict[str, object]] = []
    current: dict[str, object] | None = None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            if current:
                rows.append(current)
            current = {"bank": line.removeprefix("## ").strip()}
            continue
        if not current or not line.startswith("- "):
            continue

        label, _, value = line[2:].partition(":")
        key = label.strip().lower()
        value = value.strip()

        if key == "review count":
            current["review_count"] = int(_numeric_value(value))
        elif key == "average rating":
            current["average_rating"] = _numeric_value(value)
        elif key == "sentiment mix":
            sentiment_match = re.search(
                r"(\d+)\s+positive,\s+(\d+)\s+neutral,\s+(\d+)\s+negative",
                value,
                flags=re.IGNORECASE,
            )
            if sentiment_match:
                current["positive_count"] = int(sentiment_match.group(1))
                current["neutral_count"] = int(sentiment_match.group(2))
                current["negative_count"] = int(sentiment_match.group(3))
        elif key == "average sentiment score":
            current["average_sentiment_score"] = _numeric_value(value)
        elif key == "top themes":
            current["top_themes"] = value
        elif key == "top complaint keywords":
            current["top_complaint_keywords"] = value
        elif key == "likely satisfaction drivers":
            current["satisfaction_drivers"] = value
        elif key == "likely pain points":
            current["pain_points"] = value

    if current:
        rows.append(current)

    recommendations = pd.DataFrame(rows)
    if recommendations.empty:
        return recommendations

    total_sentiment = (
        recommendations.get("positive_count", 0)
        + recommendations.get("neutral_count", 0)
        + recommendations.get("negative_count", 0)
    )
    recommendations["positive_share"] = recommendations.get("positive_count", 0).div(
        total_sentiment.replace(0, pd.NA)
    )
    recommendations["negative_share"] = recommendations.get("negative_count", 0).div(
        total_sentiment.replace(0, pd.NA)
    )

    return normalize_recommendations(recommendations)


def load_themes_from_markdown() -> pd.DataFrame:
    """Load top theme counts from the committed Markdown analysis summary."""
    path = REPORTS_DIR / "analysis_summary.md"
    if not path.exists():
        return pd.DataFrame()

    rows: list[dict[str, object]] = []
    in_theme_table = False
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line == "## Top Themes per Bank":
            in_theme_table = True
            continue
        if in_theme_table and line.startswith("## "):
            break
        if not in_theme_table or not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != 3:
            continue
        if cells[0].lower() == "bank" or cells[0].startswith("---"):
            continue
        rows.append(
            {
                "bank": cells[0],
                "identified_theme": cells[1],
                "review_count": int(_numeric_value(cells[2])),
            }
        )

    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False)
def load_reviews() -> pd.DataFrame:
    """Load review-level processed data used for interactive exploration."""
    reviews = load_csv(REVIEW_DATA_PATH)
    if reviews.empty:
        reviews = load_csv(PROCESSED_DIR / "reviews_cleaned.csv")

    if reviews.empty:
        return reviews

    reviews = reviews.copy()
    if "review_text" not in reviews.columns and "review" in reviews.columns:
        reviews["review_text"] = reviews["review"]
    if "identified_theme" not in reviews.columns:
        reviews["identified_theme"] = "unclassified"
    if "sentiment_label" not in reviews.columns:
        reviews["sentiment_label"] = "unknown"
    if "sentiment_score" not in reviews.columns:
        reviews["sentiment_score"] = pd.NA

    if "rating" not in reviews.columns:
        reviews["rating"] = pd.NA
    if "date" not in reviews.columns:
        reviews["date"] = pd.NaT
    if "bank" not in reviews.columns:
        reviews["bank"] = "Unknown"

    reviews["rating"] = pd.to_numeric(reviews["rating"], errors="coerce")
    reviews["date"] = pd.to_datetime(reviews["date"], errors="coerce")
    reviews["review_text"] = reviews["review_text"].fillna("").astype(str)
    reviews["bank"] = reviews["bank"].fillna("Unknown")
    reviews["sentiment_label"] = reviews["sentiment_label"].fillna("unknown").str.lower()
    reviews["identified_theme"] = reviews["identified_theme"].fillna("unclassified")
    return reviews


@st.cache_data(show_spinner=False)
def load_recommendations() -> pd.DataFrame:
    """Load bank-level recommendation and KPI summary outputs."""
    recommendations = load_csv(REPORTS_DIR / "bank_recommendation_inputs.csv")
    if recommendations.empty:
        recommendations = load_recommendations_from_markdown()

    return normalize_recommendations(recommendations)


@st.cache_data(show_spinner=False)
def load_theme_summary() -> pd.DataFrame:
    """Load theme counts generated by the analysis pipeline."""
    themes = load_csv(REPORTS_DIR / "top_themes_per_bank.csv")
    if themes.empty:
        themes = load_themes_from_markdown()
    if themes.empty:
        return pd.DataFrame(columns=["bank", "identified_theme", "review_count"])
    themes = themes.copy()
    themes["review_count"] = pd.to_numeric(themes["review_count"], errors="coerce").fillna(0)
    return themes


def add_missing_banks(summary: pd.DataFrame) -> pd.DataFrame:
    """Keep CBE, BOA, and Dashen visible even when a bank has no usable reviews."""
    existing = set(summary.get("bank", pd.Series(dtype=str)).dropna())
    missing_rows = []
    for bank in BANK_ORDER:
        if bank not in existing:
            missing_rows.append(
                {
                    "bank": bank,
                    "review_count": 0,
                    "average_rating": 0,
                    "positive_count": 0,
                    "neutral_count": 0,
                    "negative_count": 0,
                    "positive_share": 0,
                    "negative_share": 0,
                    "average_sentiment_score": 0,
                    "top_themes": "No usable reviews",
                    "top_complaint_keywords": "No usable reviews",
                    "satisfaction_drivers": "No usable reviews",
                    "pain_points": "No usable reviews",
                }
            )
    if missing_rows:
        summary = pd.concat([summary, pd.DataFrame(missing_rows)], ignore_index=True)
    return summary


def token_frequency(texts: pd.Series, top_n: int = 20) -> pd.DataFrame:
    """Build simple keyword frequencies for complaint and feature request views."""
    counts: dict[str, int] = {}
    for text in texts.dropna().astype(str):
        for token in re.findall(r"[a-zA-Z]{3,}", text.lower()):
            if token not in STOPWORDS:
                counts[token] = counts.get(token, 0) + 1

    return (
        pd.DataFrame(counts.items(), columns=["keyword", "count"])
        .sort_values("count", ascending=False)
        .head(top_n)
    )


def sentiment_long(summary: pd.DataFrame) -> pd.DataFrame:
    """Convert bank-level sentiment counts to long format for Plotly."""
    columns = {
        "positive_count": "positive",
        "neutral_count": "neutral",
        "negative_count": "negative",
    }
    available = [column for column in columns if column in summary.columns]
    if not available:
        return pd.DataFrame(columns=["bank", "sentiment", "count"])
    long = summary.melt(
        id_vars="bank",
        value_vars=available,
        var_name="sentiment",
        value_name="count",
    )
    long["sentiment"] = long["sentiment"].map(columns)
    return long


def show_header() -> None:
    st.title("Fintech Review Analytics Dashboard")
    st.caption(
        "Executive dashboard for Google Play customer experience analysis across Ethiopian banking apps."
    )


def render_kpi_cards(summary: pd.DataFrame, reviews: pd.DataFrame) -> None:
    total_reviews = int(summary["review_count"].sum()) if "review_count" in summary else len(reviews)
    active_banks = int((summary.get("review_count", pd.Series(dtype=int)) > 0).sum())
    avg_rating = summary.loc[summary["review_count"] > 0, "average_rating"].mean()
    negative_reviews = int(summary.get("negative_count", pd.Series(dtype=int)).sum())

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Analyzed Reviews", f"{total_reviews:,}")
    col2.metric("Banks With Usable Data", f"{active_banks}/3")
    col3.metric("Average Rating", f"{avg_rating:.2f}" if pd.notna(avg_rating) else "N/A")
    col4.metric("Negative Reviews", f"{negative_reviews:,}")


def executive_overview(summary: pd.DataFrame, themes: pd.DataFrame, reviews: pd.DataFrame) -> None:
    st.header("Executive Overview")
    render_kpi_cards(summary, reviews)

    left, right = st.columns(2)
    with left:
        st.subheader("Average Rating per Bank")
        rating_chart = px.bar(
            summary,
            x="bank",
            y="average_rating",
            color="bank",
            text_auto=".2f",
            title="Average App Rating by Bank",
            labels={"bank": "Bank", "average_rating": "Average rating"},
        )
        rating_chart.update_layout(showlegend=False, yaxis_range=[0, 5])
        st.plotly_chart(rating_chart, use_container_width=True)

    with right:
        st.subheader("Sentiment Distribution")
        sentiment_chart = px.bar(
            sentiment_long(summary),
            x="bank",
            y="count",
            color="sentiment",
            barmode="stack",
            category_orders={"sentiment": SENTIMENT_ORDER},
            title="Sentiment Mix by Bank",
            labels={"bank": "Bank", "count": "Review count", "sentiment": "Sentiment"},
        )
        st.plotly_chart(sentiment_chart, use_container_width=True)

    st.subheader("Dominant Themes")
    if themes.empty:
        st.info("Theme summary is not available yet. Run the analysis pipeline to generate it.")
    else:
        theme_chart = px.bar(
            themes,
            x="review_count",
            y="identified_theme",
            color="bank",
            orientation="h",
            title="Top Themes by Bank",
            labels={"review_count": "Review count", "identified_theme": "Theme", "bank": "Bank"},
        )
        st.plotly_chart(theme_chart, use_container_width=True)


def bank_comparison(summary: pd.DataFrame, themes: pd.DataFrame, reviews: pd.DataFrame) -> None:
    st.header("Bank Comparison")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Review Counts")
        chart = px.bar(
            summary,
            x="bank",
            y="review_count",
            color="bank",
            text_auto=True,
            title="Review Coverage by Bank",
            labels={"bank": "Bank", "review_count": "Review count"},
        )
        chart.update_layout(showlegend=False)
        st.plotly_chart(chart, use_container_width=True)

    with col2:
        st.subheader("Sentiment Comparison")
        chart = px.bar(
            sentiment_long(summary),
            x="bank",
            y="count",
            color="sentiment",
            barmode="group",
            category_orders={"sentiment": SENTIMENT_ORDER},
            title="Positive, Neutral, and Negative Reviews",
            labels={"bank": "Bank", "count": "Review count"},
        )
        st.plotly_chart(chart, use_container_width=True)

    if not reviews.empty and "rating" in reviews.columns:
        st.subheader("Rating Distribution")
        rating_counts = (
            reviews.dropna(subset=["rating"])
            .groupby(["bank", "rating"])
            .size()
            .reset_index(name="review_count")
        )
        chart = px.bar(
            rating_counts,
            x="rating",
            y="review_count",
            color="bank",
            barmode="group",
            title="Rating Distribution by Bank",
            labels={"rating": "Rating", "review_count": "Review count"},
        )
        st.plotly_chart(chart, use_container_width=True)

    if not themes.empty:
        st.subheader("Theme Frequency Comparison")
        chart = px.bar(
            themes,
            x="bank",
            y="review_count",
            color="identified_theme",
            title="Theme Frequency by Bank",
            labels={"bank": "Bank", "review_count": "Review count", "identified_theme": "Theme"},
        )
        st.plotly_chart(chart, use_container_width=True)


def complaint_explorer(reviews: pd.DataFrame) -> None:
    st.header("Complaint Explorer")
    if reviews.empty:
        st.warning("Review-level data is unavailable. Generate `data/processed/reviews_with_sentiment.csv` to use this explorer.")
        return

    col1, col2, col3, col4 = st.columns(4)
    bank_options = ["All"] + sorted(reviews["bank"].dropna().unique().tolist())
    sentiment_options = ["All"] + sorted(reviews["sentiment_label"].dropna().unique().tolist())
    theme_options = ["All"] + sorted(reviews["identified_theme"].dropna().unique().tolist())
    rating_options = ["All"] + sorted(int(value) for value in reviews["rating"].dropna().unique())

    bank_filter = col1.selectbox("Bank", bank_options)
    sentiment_filter = col2.selectbox("Sentiment", sentiment_options, index=sentiment_options.index("negative") if "negative" in sentiment_options else 0)
    rating_filter = col3.selectbox("Rating", rating_options)
    theme_filter = col4.selectbox("Theme", theme_options)
    search_text = st.text_input("Search review text", placeholder="Example: login, transfer, update, slow")

    filtered = reviews.copy()
    if bank_filter != "All":
        filtered = filtered[filtered["bank"] == bank_filter]
    if sentiment_filter != "All":
        filtered = filtered[filtered["sentiment_label"] == sentiment_filter]
    if rating_filter != "All":
        filtered = filtered[filtered["rating"] == rating_filter]
    if theme_filter != "All":
        filtered = filtered[filtered["identified_theme"] == theme_filter]
    if search_text:
        filtered = filtered[filtered["review_text"].str.contains(search_text, case=False, na=False)]

    st.metric("Matching Reviews", f"{len(filtered):,}")
    display_columns = [
        column
        for column in ["date", "bank", "rating", "sentiment_label", "sentiment_score", "identified_theme", "review_text"]
        if column in filtered.columns
    ]
    st.dataframe(filtered[display_columns], use_container_width=True, hide_index=True)


def theme_keyword_analysis(summary: pd.DataFrame, themes: pd.DataFrame, reviews: pd.DataFrame) -> None:
    st.header("Theme & Keyword Analysis")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Top Complaint Keywords")
        keywords = summary[["bank", "top_complaint_keywords"]].copy()
        st.dataframe(keywords, use_container_width=True, hide_index=True)

    with col2:
        st.subheader("Feature Request Keywords")
        if reviews.empty:
            st.info("Review text is unavailable for feature keyword extraction.")
        else:
            request_reviews = reviews[
                reviews["review_text"].str.contains(
                    r"\b(feature|request|add|need|want|please|support|should)\b",
                    case=False,
                    na=False,
                    regex=True,
                )
            ]
            feature_terms = token_frequency(request_reviews["review_text"], top_n=12)
            if feature_terms.empty:
                st.info("No feature request keywords were found in the current review text.")
            else:
                chart = px.bar(
                    feature_terms,
                    x="count",
                    y="keyword",
                    orientation="h",
                    title="Most Frequent Feature Request Terms",
                    labels={"count": "Frequency", "keyword": "Keyword"},
                )
                st.plotly_chart(chart, use_container_width=True)

    if not reviews.empty:
        st.subheader("Negative Review Keyword Frequency")
        negative_terms = token_frequency(
            reviews.loc[reviews["sentiment_label"] == "negative", "review_text"],
            top_n=20,
        )
        if not negative_terms.empty:
            chart = px.bar(
                negative_terms,
                x="count",
                y="keyword",
                orientation="h",
                title="Common Terms in Negative Reviews",
                labels={"count": "Frequency", "keyword": "Keyword"},
            )
            st.plotly_chart(chart, use_container_width=True)

    if not themes.empty:
        st.subheader("Theme Breakdown per Bank")
        chart = px.treemap(
            themes,
            path=["bank", "identified_theme"],
            values="review_count",
            title="Theme Composition by Bank",
        )
        st.plotly_chart(chart, use_container_width=True)


def recommendations(summary: pd.DataFrame) -> None:
    st.header("Recommendations")
    for _, row in summary.iterrows():
        bank = row["bank"]
        review_count = int(row.get("review_count", 0) or 0)
        with st.expander(bank, expanded=review_count > 0):
            if review_count == 0:
                st.info("No usable review data is available yet. Re-run scraping with verified app metadata before making product recommendations.")
                continue

            st.write(f"**Satisfaction drivers:** {row.get('satisfaction_drivers', 'Not available')}")
            st.write(f"**Pain points:** {row.get('pain_points', 'Not available')}")
            st.write(f"**Top complaint keywords:** {row.get('top_complaint_keywords', 'Not available')}")

            if bank == "Commercial Bank of Ethiopia":
                st.success(
                    "Recommendation: protect the current usability advantage and improve transaction status transparency, especially around transfers, updates, and application reliability."
                )
            elif bank == "Bank of Abyssinia":
                st.warning(
                    "Recommendation: prioritize app stability, performance, account access, and transaction completion before expanding feature scope."
                )
            else:
                st.info("Recommendation: collect usable review data before prioritizing product changes.")


def main() -> None:
    reviews = load_reviews()
    summary = load_recommendations()
    themes = load_theme_summary()

    if summary.empty:
        st.error("Bank-level report outputs were not found. Run `python scripts/analyze_reviews.py` before launching the dashboard.")
        return

    show_header()
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Dashboard section",
        [
            "Executive Overview",
            "Bank Comparison",
            "Complaint Explorer",
            "Theme & Keyword Analysis",
            "Recommendations",
        ],
    )
    st.sidebar.markdown("---")
    st.sidebar.caption("Data sources: `reports/` and `data/processed/`")

    if page == "Executive Overview":
        executive_overview(summary, themes, reviews)
    elif page == "Bank Comparison":
        bank_comparison(summary, themes, reviews)
    elif page == "Complaint Explorer":
        complaint_explorer(reviews)
    elif page == "Theme & Keyword Analysis":
        theme_keyword_analysis(summary, themes, reviews)
    else:
        recommendations(summary)


if __name__ == "__main__":
    main()
