# 🛒 Customer Retention & Revenue Dashboard

An interactive analytics product on 1.07M real e-commerce transactions (UK online retailer,
Dec 2009 – Dec 2011) that answers the questions a growth/CRM team lives by:
**who are our best customers, who's about to churn, and how well does each monthly cohort
stick around?**

**Stack:** DuckDB (SQL) → Parquet extract → Streamlit + Plotly.

---

## Headline numbers

From `scripts/build_features.py` and `app/data.py` over the full dataset:

| | |
|---|---|
| Raw rows (both sheets of the UCI workbook) | **1,067,371** |
| Clean transaction lines | **776,579** |
| Customers / orders / countries | 5,852 / 36,594 / 41 |
| Revenue | £17.07M |
| Average order value | £466 |
| Top 20% of customers' share of revenue | **77.2%** |
| Champions: share of customers → share of revenue | **25% → 69%** |
| At Risk (frequent buyers gone quiet ~1 year) | 831 customers, 9.4% of revenue |
| Customers with no order in 90+ days | 50.7% |
| Month-1 retention, averaged over 25 monthly cohorts | 21% |

**Cleaning funnel:**

| Step | Rows left |
|---|---|
| Raw | 1,067,371 |
| Exact duplicates removed | 1,033,036 |
| With a customer ID | 797,885 |
| Cancellations removed | 779,495 |
| Non-positive quantity or price removed | 779,425 |
| Service and accounting codes removed (postage, bank charges, …) | **776,579** |

## What it does
- **RFM segmentation in SQL.** Every customer is scored 1–5 on Recency, Frequency and
  Monetary value using `NTILE(5)` quintiles. A recency × frequency grid then assigns each
  customer to exactly one of six segments (`sql/02_rfm.sql`).
- **Churn flag.** A configurable recency threshold (30–365 days); the churn rate moves as
  you slide it.
- **Cohort retention heatmap.** Monthly acquisition cohorts × months since first order,
  the classic retention triangle (`sql/03_cohort.sql`).
- **Revenue, AOV and LTV.** Monthly revenue and average-order-value trends, plus historical
  LTV (revenue per customer to date) by segment.
- **Interactive filters.** Country and date range (end date inclusive), applied across
  every view.

## Segments

| Segment | Rule (R, F scores) | Customers | Share of revenue | Action |
|---|---|---|---|---|
| Champions | R ≥ 4, F ≥ 4 | 1,463 | 68.9% | reward, ask for referrals |
| Loyal | R ≥ 3, F ≥ 3 | 1,216 | 14.4% | upsell, loyalty perks |
| At Risk | R ≤ 2, F ≥ 3 | 831 | 9.4% | win-back campaign |
| New | R ≥ 4, F ≤ 2 | 446 | 2.4% | onboard, nurture |
| Potential Loyalist | R = 3, F ≤ 2 | 385 | 1.2% | second-order incentive |
| Hibernating | R ≤ 2, F ≤ 2 | 1,511 | 3.6% | low-cost reactivation |

Recency gates every "good" segment, so a frequent buyer who has gone quiet is **At Risk**,
not Loyal. Score ties (about a third of customers have exactly one order) are broken by
`customer_id`, so the same data always produces the same segments.

## Data
UCI "Online Retail II" (https://archive.ics.uci.edu/dataset/502/online+retail+ii), or the
Kaggle CSV `mashlyn/online-retail-ii-uci`.

The workbook splits the history across two sheets, `Year 2009-2010` and `Year 2010-2011`;
both are loaded. Columns are read as text and cast in SQL. Type sniffing fails on
`Invoice` (numeric until the first cancelled `C…` invoice), and dates are stored as Excel
serial numbers.

The raw file is gitignored. The cleaned `data/clean_transactions.parquet` (8.7 MiB, ZSTD)
is committed so the deployed app has data.

## How to run
```bash
python -m venv .venv && ./.venv/bin/pip install -r requirements.txt
# Optional: rebuild the Parquet from the raw file (see scripts/DOWNLOAD.md)
./.venv/bin/python scripts/build_features.py     # raw -> clean_transactions.parquet + funnel
./.venv/bin/streamlit run app/streamlit_app.py   # launch the dashboard
./.venv/bin/pytest -q                            # 9 tests on the query layer
```

## Deploy
Go to https://share.streamlit.io, choose **New app**, and point it at this repo's
`app/streamlit_app.py`.

## Project structure
```
scripts/  build_features.py  (raw -> Parquet, cleaning funnel), DOWNLOAD.md
sql/      01_clean.sql, 02_rfm.sql, 03_cohort.sql
app/      data.py (query layer), streamlit_app.py (UI)
tests/    test_data.py (hand-checked fixture: KPIs, filters, RFM, churn, cohorts, AOV)
data/     clean_transactions.parquet
```
