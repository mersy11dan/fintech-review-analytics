# Fintech App Review Analytics: Final Report Draft

## Executive Summary

This project analyzed Google Play reviews for major Ethiopian banking apps to understand customer satisfaction, recurring pain points, and product improvement opportunities. The current analysis includes **Commercial Bank of Ethiopia** and **Bank of Abyssinia**. Dashen Bank was included in the scraping target list, but the current collection returned no usable reviews for Dashen, so this report does not make product claims for Dashen.

Commercial Bank of Ethiopia shows stronger customer satisfaction, with **616 analyzed reviews**, an **average rating of 4.20**, and **401 positive reviews** compared with **55 negative reviews**. Bank of Abyssinia shows more urgent product risk, with **621 analyzed reviews**, an **average rating of 2.73**, and a much higher negative review volume of **184 negative reviews**.

The most important product takeaway is clear: **CBE should protect and refine its already strong usability and transaction experience, while Bank of Abyssinia should prioritize app reliability, performance, and core workflow stability before expanding features.**

## Data Collection Methodology

Reviews were collected from Google Play using `google-play-scraper`. The target apps were:

- Commercial Bank of Ethiopia: `com.combanketh.mobilebanking`
- Bank of Abyssinia: `com.boa.boaMobileBanking`
- Dashen Bank: `com.dashen.dashensuperapp`

The scraper collected review text, rating, date, bank name, source, and app package information. Reviews were fetched newest-first in batches and filtered locally by date because Google Play review scraping does not provide a server-side date range filter.

The current run collected **1,323 raw reviews**:

- Commercial Bank of Ethiopia: **660 raw reviews collected**
- Bank of Abyssinia: **663 raw reviews collected**
- Dashen Bank: **0 raw reviews collected**

After preprocessing and filtering, the analyzed dataset included **1,237 reviews**:

- Commercial Bank of Ethiopia: **616 analyzed reviews**
- Bank of Abyssinia: **621 analyzed reviews**

## Data Quality Assessment

The preprocessing pipeline standardized columns to `review`, `rating`, `date`, `bank`, and `source`. It removed records missing review text or rating, normalized dates to `YYYY-MM-DD`, and removed duplicate reviews using review text, rating, date, bank, and source.

The biggest data quality limitation is the missing Dashen Bank coverage. Since the scraper returned no Dashen reviews in this run, Dashen should be treated as **out of scope for current findings**, not as a bank with neutral or poor performance. Another limitation is that many reviews were mapped to a broad `general` theme, which means some customer feedback requires deeper NLP or manual review to produce more precise product categories.

## Sentiment Analysis Methodology and Tool Choice

The project supports transformer-based sentiment classification using `distilbert-base-uncased-finetuned-sst-2-english`. For this run, the fallback path was used with VADER sentiment scoring because it is lightweight, fast, and suitable for short app-store reviews.

The sentiment output includes:

- `sentiment_label`: positive, neutral, or negative
- `sentiment_score`: model confidence or sentiment strength
- `identified_theme`: a keyword-based theme label for downstream reporting

VADER is a practical choice for rapid analysis, but a transformer model should be preferred in future runs when compute resources and dependencies are stable, especially for better handling of context, sarcasm, and mixed-language reviews.

## Theme Extraction Findings

Themes were extracted using keyword logic and TF-IDF/ngram-based analysis. The most common themes were broad `general` feedback, transactions, usability, performance, customer support, and account access.

For **Commercial Bank of Ethiopia**, top themes were:

- General feedback: 518 reviews
- Transactions: 37 reviews
- Usability: 30 reviews
- Customer support: 13 reviews
- Account access: 12 reviews

For **Bank of Abyssinia**, top themes were:

- General feedback: 524 reviews
- Performance: 32 reviews
- Transactions: 27 reviews
- Customer support: 16 reviews
- Account access: 14 reviews

The theme distribution suggests that CBE’s product conversation is more centered on refinement of core banking journeys, while Bank of Abyssinia’s feedback shows stronger signs of reliability and performance friction.

## Database Design Overview

The PostgreSQL schema is normalized into two main tables:

- `banks`: stores bank-level metadata such as `bank_id`, `bank_name`, and `app_name`
- `reviews`: stores review-level facts including review text, rating, review date, sentiment label, sentiment score, identified theme, and source

The `reviews.bank_id` field references `banks.bank_id`, which keeps bank metadata separate from review records and avoids repeating bank details across every review row. The schema also includes primary keys, a foreign key constraint, rating and sentiment checks, useful indexes, and a uniqueness constraint to prevent duplicate review records.

## Insights and Visualizations

The analysis generated report-ready outputs in `reports/`, including:

- `analysis_summary.md`
- `bank_recommendation_inputs.md`
- `bank_recommendation_inputs.csv`
- `sentiment_distribution_by_bank.csv`
- `sentiment_by_rating.csv`
- `top_themes_per_bank.csv`

Generated figures are stored in `reports/figures/`, including:

- `sentiment_distribution_by_bank.png`
- `sentiment_by_rating.png`
- `top_themes_by_bank.png`

Key insight: **rating and sentiment are strongly aligned**. Five-star reviews are overwhelmingly positive, while one-star reviews contain most of the negative sentiment. This confirms that the sentiment pipeline is directionally consistent with explicit customer ratings.

## Bank-Specific Recommendations

### Commercial Bank of Ethiopia

CBE is the stronger performer in the dataset. It has a **4.20 average rating**, **401 positive reviews**, and only **55 negative reviews**. Its main satisfaction drivers are broad positive experience and usability, while its leading product risks are transaction-related complaints and update/application issues.

Recommended actions:

1. **Protect the usability advantage.** Keep common flows such as login, balance checks, transfers, and payments simple and fast.
2. **Improve transaction reliability and transparency.** Negative comments mention transaction and transfer issues, so users need clearer success/failure states, better confirmations, and easier support paths for failed transactions.
3. **Strengthen release quality.** Complaint keywords include update and application, suggesting that app updates may introduce friction. Regression testing around core banking flows should be prioritized before releases.

### Bank of Abyssinia

Bank of Abyssinia has the highest product risk in the current dataset. It has a **2.73 average rating**, **184 negative reviews**, and a negative sentiment share of roughly **29.6%**. Its positive reviews indicate that customers value transaction capability when it works, but its pain points are broader and more severe.

Recommended actions:

1. **Prioritize stability and performance.** Performance is a top pain point, and complaint keywords include app, worst, work, and banking. The product team should focus on crashes, failed actions, slow loading, and reliability before adding new features.
2. **Fix core transaction journeys.** Transactions appear in both satisfaction drivers and top themes, meaning this is a high-impact workflow. Improving transfer success rates and status visibility should improve both ratings and trust.
3. **Improve access and support workflows.** Account access and customer support appear in the top themes. The bank should review login, OTP, password recovery, and support escalation journeys.

### Dashen Bank

Dashen Bank was included in the scrape configuration, but the current run returned no usable review records. No satisfaction drivers, pain points, or product recommendations should be inferred until review coverage is available.

Recommended action:

1. **Rerun collection for Dashen using verified package IDs and country/language settings.** Dashen may require a different app package, locale, or scraping configuration to retrieve review data reliably.

## Limitations and Next Steps

This analysis is useful for directional product decisions, but it has several limitations:

- Dashen Bank had no usable review data in the current scrape.
- The `general` theme is too broad and should be refined in future theme extraction.
- App-store reviews may overrepresent users with strong positive or negative experiences.
- VADER is fast and interpretable, but transformer-based sentiment analysis may produce better results for nuanced review language.
- The current report does not yet include manual validation of sampled reviews.

Recommended next steps:

1. Rerun scraping for Dashen Bank with verified app identifiers and locale settings.
2. Improve theme extraction by adding more banking-specific keyword dictionaries and reviewing samples manually.
3. Run transformer-based sentiment scoring once the environment is stable.
4. Load the final dataset into PostgreSQL and run database integrity checks before submission.
5. Export this Markdown report to PDF and include the generated figures from `reports/figures/`.
