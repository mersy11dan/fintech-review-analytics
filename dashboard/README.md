# Fintech Review Analytics Dashboard

This Streamlit dashboard presents the fintech review analytics outputs for bank executives and product managers. It loads generated analysis files from `reports/` and review-level data from `data/processed/`.

## Run Locally

From the project root:

```powershell
pip install -r requirements.txt
pip install -r dashboard/requirements.txt
streamlit run dashboard/app.py
```

## Deploy on Render

This repository includes `render.yaml` for a free-tier Render web service. The Render start command is:

```bash
streamlit run dashboard/app.py --server.port=$PORT --server.address=0.0.0.0 --server.headless=true
```

Render uses `dashboard/requirements.txt` during deployment so the dashboard installs only lightweight runtime dependencies: Streamlit, Plotly, and pandas. This keeps free-tier builds faster and avoids installing training or NLP packages that are not required to serve the dashboard.

The app resolves files relative to the repository root, which works both locally and in Render. Review-level data defaults to `data/processed/reviews_with_sentiment.csv`. For cloud deployments where `data/processed/` is not committed, set the optional `REVIEW_DATA_PATH` environment variable to another CSV path if you provide review-level data separately.

The dashboard expects these files when available:

- `reports/bank_recommendation_inputs.csv`
- `reports/top_themes_per_bank.csv`
- `data/processed/reviews_with_sentiment.csv`

If review-level processed data is missing, the executive and recommendation sections still use the report summaries, but the complaint explorer will ask you to run the pipeline first.
