"""Utilities for scraping fintech app reviews from Google Play."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import logging
from pathlib import Path

from src.utils import ensure_directory, resolve_project_path


LOGGER = logging.getLogger(__name__)


BANK_APPS = {
    "Commercial Bank of Ethiopia": "com.combanketh.mobilebanking",
    "Bank of Abyssinia": "com.boa.boaMobileBanking",
    "Dashen Bank": "com.dashen.dashensuperapp",
}


@dataclass(frozen=True)
class ReviewScrapeConfig:
    """Configuration for one Google Play review scrape."""

    app_id: str
    app_name: str
    country: str = "us"
    language: str = "en"
    limit: int = 500
    start_date: date | None = None
    end_date: date | None = None
    batch_size: int = 200


def parse_review_date(value: str | date | datetime | None) -> date | None:
    """Convert user-provided date input into a date object."""
    if value is None or isinstance(value, date):
        return value
    return datetime.strptime(value, "%Y-%m-%d").date()


def build_default_configs(
    limit: int = 500,
    start_date: str | date | None = None,
    end_date: str | date | None = None,
    country: str = "us",
    language: str = "en",
) -> list[ReviewScrapeConfig]:
    """Create scrape configs for the three target bank apps."""
    parsed_start = parse_review_date(start_date)
    parsed_end = parse_review_date(end_date)

    return [
        ReviewScrapeConfig(
            app_name=app_name,
            app_id=app_id,
            country=country,
            language=language,
            limit=limit,
            start_date=parsed_start,
            end_date=parsed_end,
        )
        for app_name, app_id in BANK_APPS.items()
    ]


def _is_review_in_date_range(
    review_date: datetime | None,
    start_date: date | None,
    end_date: date | None,
) -> bool:
    """Return whether a review date is inside the configured date window."""
    if review_date is None:
        return False

    review_day = review_date.date()
    if start_date and review_day < start_date:
        return False
    if end_date and review_day > end_date:
        return False
    return True


def _should_stop_for_date(review_date: datetime | None, start_date: date | None) -> bool:
    """Stop paginating once newest-first reviews are older than the start date."""
    return bool(start_date and review_date and review_date.date() < start_date)


def _normalise_review(row: dict, config: ReviewScrapeConfig) -> dict:
    """Select only the raw fields needed by the analytics pipeline."""
    return {
        "review_text": row.get("content", ""),
        "rating": row.get("score"),
        "date": row.get("at"),
        "app_name": config.app_name,
        "source": "google_play",
        "app_id": config.app_id,
    }


def scrape_google_play_reviews(config: ReviewScrapeConfig):
    """Scrape one Google Play app and return matching reviews as a DataFrame."""
    import pandas as pd
    from google_play_scraper import Sort, reviews

    collected: list[dict] = []
    continuation_token = None

    LOGGER.info("Starting scrape for %s (%s)", config.app_name, config.app_id)

    try:
        while len(collected) < config.limit:
            # Fetch reviews in batches because Google Play responses are paginated.
            batch_count = min(config.batch_size, config.limit - len(collected))
            rows, continuation_token = reviews(
                config.app_id,
                lang=config.language,
                country=config.country,
                sort=Sort.NEWEST,
                count=batch_count,
                continuation_token=continuation_token,
            )

            if not rows:
                LOGGER.info("No more reviews returned for %s", config.app_name)
                break

            for row in rows:
                review_date = row.get("at")

                # Date filtering happens locally because the scraper API does not
                # expose server-side date range filters.
                if _is_review_in_date_range(review_date, config.start_date, config.end_date):
                    collected.append(_normalise_review(row, config))

                if _should_stop_for_date(review_date, config.start_date):
                    LOGGER.info("Reached start date boundary for %s", config.app_name)
                    return pd.DataFrame(collected)

            if continuation_token is None:
                break

    except Exception as exc:
        LOGGER.exception("Failed to scrape reviews for %s: %s", config.app_name, exc)

    LOGGER.info("Collected %s reviews for %s", len(collected), config.app_name)
    return pd.DataFrame(collected)


def scrape_bank_reviews(configs: list[ReviewScrapeConfig]):
    """Scrape all configured bank apps and combine reviews into one DataFrame."""
    import pandas as pd

    frames = [scrape_google_play_reviews(config) for config in configs]
    frames = [frame for frame in frames if not frame.empty]

    columns = ["review_text", "rating", "date", "app_name", "source", "app_id"]
    if not frames:
        return pd.DataFrame(columns=columns)

    return pd.concat(frames, ignore_index=True)[columns]


def save_raw_reviews(frame, output_dir: str | Path = "data/raw") -> Path:
    """Save raw scraped reviews to data/raw and return the output path."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = resolve_project_path(str(output_dir), f"google_play_reviews_{timestamp}.csv")

    ensure_directory(output_path.parent)
    frame.to_csv(output_path, index=False)
    LOGGER.info("Saved %s raw reviews to %s", len(frame), output_path)
    return output_path


def scrape_and_save_bank_reviews(
    limit: int = 500,
    start_date: str | date | None = None,
    end_date: str | date | None = None,
    country: str = "us",
    language: str = "en",
    output_dir: str | Path = "data/raw",
):
    """Scrape the three target bank apps and save the raw output CSV."""
    configs = build_default_configs(
        limit=limit,
        start_date=start_date,
        end_date=end_date,
        country=country,
        language=language,
    )
    frame = scrape_bank_reviews(configs)
    save_raw_reviews(frame, output_dir=output_dir)
    return frame
