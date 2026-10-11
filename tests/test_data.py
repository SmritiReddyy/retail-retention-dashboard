"""Query-layer tests against a tiny hand-built Parquet with known answers."""
import pathlib
import sys

import duckdb
import pandas as pd
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "app"))
import data  # noqa: E402

ROWS = [
    # invoice, customer, country, date, qty, price
    ("1001", 1, "United Kingdom", "2011-01-05 10:00", 2, 10.0),
    ("1002", 1, "United Kingdom", "2011-02-10 10:00", 1, 30.0),
    ("1003", 1, "United Kingdom", "2011-03-15 10:00", 1, 20.0),
    ("1004", 2, "France",         "2011-01-20 12:00", 4, 5.0),
    ("1005", 2, "France",         "2011-03-01 12:00", 1, 5.0),
    ("1006", 3, "Germany",        "2011-02-01 09:00", 10, 1.0),
    ("1007", 4, "United Kingdom", "2011-03-31 23:30", 1, 100.0),
]


@pytest.fixture()
def parquet(tmp_path):
    df = pd.DataFrame(ROWS, columns=["invoice", "customer_id", "country", "invoice_date", "quantity", "price"])
    df["invoice_date"] = pd.to_datetime(df["invoice_date"])
    df["revenue"] = df["quantity"] * df["price"]
    path = tmp_path / "tx.parquet"
    duckdb.from_df(df).write_parquet(str(path))
    return path


def test_kpis(parquet):
    k = data.kpis(parquet_path=parquet)
    assert k == {"customers": 4, "orders": 7, "revenue": 205.0, "avg_order_value": 29.29}


def test_country_filter(parquet):
    k = data.kpis(parquet_path=parquet, countries=["France"])
    assert (k["customers"], k["revenue"]) == (1, 25.0)


def test_date_range_end_is_inclusive(parquet):
    # 1007 lands at 23:30 on the last day and must be kept.
    k = data.kpis(parquet_path=parquet, date_range=("2011-03-01", "2011-03-31"))
    assert k["orders"] == 3
    assert k["revenue"] == 125.0


def test_rfm_recency_and_frequency(parquet):
    df = data.rfm(parquet_path=parquet).set_index("customer_id")
    # Snapshot is the day after the last order (2011-04-01).
    assert df.loc[4, "recency_days"] == 1
    assert df.loc[3, "recency_days"] == 59
    assert df.loc[1, "frequency"] == 3
    assert df.loc[1, "monetary"] == 70.0
    assert df[["r_score", "f_score", "m_score"]].isin(range(1, 6)).all().all()


def test_segment_summary_shares_sum_to_one(parquet):
    seg = data.segment_summary(parquet_path=parquet)
    assert seg["customers"].sum() == 4
    assert seg["share_of_customers"].sum() == pytest.approx(1.0)
    assert seg["share_of_revenue"].sum() == pytest.approx(1.0)
    assert seg["total_monetary"].sum() == 205.0


def test_churn_rate_threshold(parquet):
    # Recency: customer 4 = 1 day, 1 = 17, 2 = 31, 3 = 59.
    assert data.churn_rate(30, parquet_path=parquet) == 50.0
    assert data.churn_rate(60, parquet_path=parquet) == 0.0


def test_cohort_month_zero_is_full_retention(parquet):
    piv = data.cohort_pivot(parquet_path=parquet)
    assert (piv[0] == 100.0).all()
    # January cohort (customers 1 and 2): both active again in March.
    assert piv.loc["2011-01", 2] == 100.0
    assert piv.loc["2011-01", 1] == 50.0


def test_monthly_revenue_and_aov(parquet):
    mr = data.monthly_revenue(parquet_path=parquet).set_index("month")
    assert mr["revenue"].tolist() == [40.0, 40.0, 125.0]
    assert mr["orders"].tolist() == [2, 2, 3]
    assert mr["avg_order_value"].tolist() == [20.0, 20.0, 41.67]


def test_segments_cover_the_rf_grid_and_respect_recency():
    """Every (r, f) score pair maps to one segment; no lapsed customer is 'good'."""
    con = duckdb.connect()
    case = data._read_sql("02_rfm.sql").split("CASE", 1)[1].split("END AS segment", 1)[0]
    grid = con.execute(
        f"SELECT r_score, f_score, CASE {case} END AS segment "
        "FROM range(1, 6) r(r_score), range(1, 6) f(f_score)"
    ).df()
    con.close()
    assert len(grid) == 25 and grid["segment"].notna().all()
    good = grid[grid["segment"].isin(["Champions", "Loyal", "New"])]
    assert (good["r_score"] >= 3).all()
    assert set(grid["segment"]) == {"Champions", "Loyal", "New", "Potential Loyalist", "At Risk", "Hibernating"}
