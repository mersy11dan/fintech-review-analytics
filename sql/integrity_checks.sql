-- Database integrity checks for the bank review analytics project.
-- Run these queries in pgAdmin Query Tool after loading review data.

-- 1. Count reviews per bank.
SELECT
    b.bank_name,
    COUNT(r.review_id) AS review_count
FROM banks AS b
LEFT JOIN reviews AS r
    ON b.bank_id = r.bank_id
GROUP BY b.bank_id, b.bank_name
ORDER BY review_count DESC, b.bank_name;

-- 2. Compute average rating per bank.
SELECT
    b.bank_name,
    ROUND(AVG(r.rating)::numeric, 2) AS average_rating,
    COUNT(r.review_id) AS review_count
FROM banks AS b
LEFT JOIN reviews AS r
    ON b.bank_id = r.bank_id
GROUP BY b.bank_id, b.bank_name
ORDER BY average_rating DESC NULLS LAST, b.bank_name;

-- 3. Check for nulls in important columns.
SELECT
    SUM(CASE WHEN r.review_id IS NULL THEN 1 ELSE 0 END) AS null_review_id,
    SUM(CASE WHEN r.bank_id IS NULL THEN 1 ELSE 0 END) AS null_bank_id,
    SUM(CASE WHEN r.review_text IS NULL OR BTRIM(r.review_text) = '' THEN 1 ELSE 0 END) AS null_or_blank_review_text,
    SUM(CASE WHEN r.rating IS NULL THEN 1 ELSE 0 END) AS null_rating,
    SUM(CASE WHEN r.review_date IS NULL THEN 1 ELSE 0 END) AS null_review_date,
    SUM(CASE WHEN r.source IS NULL OR BTRIM(r.source) = '' THEN 1 ELSE 0 END) AS null_or_blank_source
FROM reviews AS r;

-- 4. Confirm foreign key relationships are valid.
-- This should return zero rows because every review.bank_id should exist in banks.
SELECT
    r.review_id,
    r.bank_id
FROM reviews AS r
LEFT JOIN banks AS b
    ON r.bank_id = b.bank_id
WHERE b.bank_id IS NULL;

-- 5. Check for duplicate review business keys.
-- This should return zero rows because reviews_unique_review should prevent duplicates.
SELECT
    bank_id,
    review_text,
    rating,
    review_date,
    source,
    COUNT(*) AS duplicate_count
FROM reviews
GROUP BY bank_id, review_text, rating, review_date, source
HAVING COUNT(*) > 1;
