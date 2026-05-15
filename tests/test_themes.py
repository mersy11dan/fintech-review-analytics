"""Tests for thematic analysis helpers."""

import pandas as pd

from src.themes import (
    THEME_GROUPING_EXPLANATION,
    ThemeAnalysisConfig,
    add_theme_columns,
    build_bank_theme_map,
    extract_tfidf_keywords,
    group_keywords_into_themes,
    run_theme_analysis,
)


def test_extract_tfidf_keywords_uses_ngrams():
    reviews = pd.Series(
        [
            "login problem and transfer delay",
            "login issue with otp problem",
            "transfer delay is slow",
        ]
    )

    keywords = extract_tfidf_keywords(reviews, max_features=10, ngram_range=(1, 2))

    assert "login" in keywords
    assert any("transfer" in keyword for keyword in keywords)


def test_group_keywords_into_business_themes():
    keywords = ["login", "otp problem", "transfer delay", "simple design", "support"]

    grouped = group_keywords_into_themes(keywords)

    assert "login_issues" in grouped
    assert "transfer_speed" in grouped
    assert "ui_design" in grouped


def test_add_theme_columns_maps_reviews_to_themes():
    frame = pd.DataFrame(
        {
            "review": ["login otp issue", "transfer is very slow"],
            "bank": ["Dashen Bank", "Dashen Bank"],
        }
    )
    theme_map = {
        "Dashen Bank": {
            "login_issues": ["login", "otp"],
            "transfer_speed": ["transfer", "slow"],
            "ui_design": [],
        }
    }

    themed = add_theme_columns(frame, theme_map)

    assert themed["identified_theme"].to_list() == ["login_issues", "transfer_speed"]
    assert themed.columns.to_list() == [
        "review_id",
        "bank",
        "review_text",
        "identified_theme",
        "theme_keywords",
    ]


def test_run_theme_analysis_saves_csv_and_explanation(tmp_path):
    input_path = tmp_path / "reviews_cleaned.csv"
    output_path = tmp_path / "reviews_with_themes.csv"
    explanation_path = tmp_path / "theme_grouping_logic.md"
    pd.DataFrame(
        {
            "review": [
                "login problem with otp",
                "transfer delay is slow",
                "simple ui design",
                "support response is slow",
            ],
            "bank": ["Bank A", "Bank A", "Bank A", "Bank A"],
        }
    ).to_csv(input_path, index=False)

    themed = run_theme_analysis(
        ThemeAnalysisConfig(
            input_path=input_path,
            output_path=output_path,
            explanation_path=explanation_path,
            max_features=20,
        )
    )

    assert output_path.exists()
    assert explanation_path.read_text(encoding="utf-8") == THEME_GROUPING_EXPLANATION
    assert len(themed) == 4


def test_build_bank_theme_map_limits_themes_per_bank():
    frame = pd.DataFrame(
        {
            "review": [
                "login otp issue",
                "transfer delay slow",
                "simple ui design",
                "support response poor",
                "need balance feature",
            ],
            "bank": ["Bank A"] * 5,
        }
    )

    theme_map = build_bank_theme_map(frame, ThemeAnalysisConfig(max_features=30))

    assert 3 <= len(theme_map["Bank A"]) <= 5
