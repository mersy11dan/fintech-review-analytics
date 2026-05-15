"""Tests for Google Play scraper helpers."""

from datetime import date

from src.scraper import BANK_APPS, build_default_configs, parse_review_date


def test_parse_review_date_accepts_iso_string():
    assert parse_review_date("2024-01-31") == date(2024, 1, 31)


def test_build_default_configs_creates_target_bank_configs():
    configs = build_default_configs(limit=25, start_date="2024-01-01", end_date="2024-12-31")

    assert len(configs) == len(BANK_APPS)
    assert {config.app_name for config in configs} == set(BANK_APPS)
    assert all(config.limit == 25 for config in configs)
