# 🛒 Customer Retention & Revenue Dashboard

An interactive analytics product on ~1M real e-commerce transactions (UK online retailer,
2009–2011) that answers the questions a growth/CRM team lives by:
**who are our best customers, who's about to churn, and how well does each monthly cohort
stick around?**

**Stack:** DuckDB (SQL) → Parquet extract → Streamlit + Plotly (deployed live).

👉 **[Live app](#)** _(link after deploying to Streamlit Community Cloud)_

---

## What it does
- **RFM segmentation** — scores every customer on Recency, Frequency, Monetary value
  (SQL `NTILE` quintiles) and buckets them into actionable segments (Champions, Loyal,
  At Risk, Hibernating, …).
- **Churn flag** — configurable recency threshold; see churn rate move as you slide it.
- **Cohort retention heatmap** — monthly acquisition cohorts × months-since-first-order,
  the classic retention triangle.
- **Revenue & LTV** — monthly revenue trend, average order value, historical LTV by segment.
- **Interactive filters** — country + date range, applied across every view.

## Business value of the segments
| Segment | Meaning | Action |
|---|---|---|
| Champions | recent, frequent, high spend | reward, ask for referrals |
| Loyal | frequent buyers | upsell, loyalty perks |
| At Risk | were valuable, going quiet | win-back campaign |
| Hibernating | low recency & frequency | low-cost reactivation |
| New | just acquired | onboard, nurture |

## Data
UCI "Online Retail II" (via Kaggle `mashlyn/online-retail-ii-uci` or UCI ML Repo).
- ~1,067,000 rows: `Invoice, StockCode, Description, Quantity, InvoiceDate, Price, Customer ID, Country`
- Cleaning handles: cancelled invoices (Invoice starts with `C`), missing Customer ID,
  non-positive quantity/price, returns — see `sql/01_clean.sql`.

## How to run
```bash
python -m venv .venv && ./.venv/bin/pip install -r requirements.txt
# 1. Download the dataset into ./data/ (see scripts/DOWNLOAD.md)
./.venv/bin/python scripts/build_features.py     # raw -> clean_transactions.parquet
./.venv/bin/streamlit run app/streamlit_app.py   # launch the dashboard
```

## Deploy (for the resume link)
Push to GitHub, then https://share.streamlit.io → point it at `app/streamlit_app.py`.
Commit `data/clean_transactions.parquet` (small) so the deployed app has data.

## Project structure
```
scripts/  build_features.py  (raw -> Parquet), DOWNLOAD.md
sql/      01_clean.sql, 02_rfm.sql, 03_cohort.sql
app/      data.py (testable query layer), streamlit_app.py (UI)
```
