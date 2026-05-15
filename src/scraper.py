"""Utilities for scraping fintech app reviews."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReviewScrapeConfig:
    """Configuration for one Google Play review scrape."""

    app_id: str
    country: str = "us"
    language: str = "en"
    count: int = 500


def scrape_google_play_reviews(config: ReviewScrapeConfig):
    """Scrape Google Play reviews and return them as a DataFrame."""
    import pandas as pd
    from google_play_scraper import Sort, reviews

    rows, _ = reviews(
        config.app_id,
        lang=config.language,
        country=config.country,
        sort=Sort.NEWEST,
        count=config.count,
    )
    return pd.DataFrame(rows)
