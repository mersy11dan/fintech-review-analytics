-- PostgreSQL schema for the bank review analytics project.
-- The design keeps bank metadata separate from individual reviews and links
-- each review to its bank through a foreign key.

CREATE TABLE IF NOT EXISTS banks (
    bank_id BIGSERIAL PRIMARY KEY,
    bank_name VARCHAR(150) NOT NULL UNIQUE,
    app_name VARCHAR(150) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS reviews (
    review_id BIGSERIAL PRIMARY KEY,
    bank_id BIGINT NOT NULL REFERENCES banks (bank_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    review_text TEXT NOT NULL,
    rating SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    review_date DATE NOT NULL,
    sentiment_label VARCHAR(20) CHECK (
        sentiment_label IN ('positive', 'neutral', 'negative')
    ),
    sentiment_score NUMERIC(6, 5) CHECK (
        sentiment_score IS NULL OR (sentiment_score >= 0 AND sentiment_score <= 1)
    ),
    identified_theme VARCHAR(100),
    source VARCHAR(50) NOT NULL DEFAULT 'google_play',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT reviews_unique_review UNIQUE (
        bank_id,
        review_text,
        rating,
        review_date,
        source
    )
);

CREATE INDEX IF NOT EXISTS idx_reviews_bank_id ON reviews (bank_id);
CREATE INDEX IF NOT EXISTS idx_reviews_review_date ON reviews (review_date);
CREATE INDEX IF NOT EXISTS idx_reviews_sentiment_label ON reviews (sentiment_label);
CREATE INDEX IF NOT EXISTS idx_reviews_identified_theme ON reviews (identified_theme);
