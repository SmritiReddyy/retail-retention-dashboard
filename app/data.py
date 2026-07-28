"""Query layer: all analytics run as DuckDB SQL against the Parquet extract.

Kept separate from the Streamlit UI so it can be unit-tested headlessly.
Each function returns a pandas DataFrame.
"""
import pathlib

import duckdb
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
PARQUET = ROOT / "data" / "clean_transactions.parquet"
SQL = ROOT / "sql"


def _con(parquet_path=None, countries=None, date_range=None):
    """Open a DuckDB connection with a `tx` view over the (filtered) Parquet."""
    path = str(parquet_path or PARQUET)
    con = duckdb.connect()
    where = ["1=1"]
    if countries:
        lst = ",".join("'" + c.replace("'", "''") + "'" for c in countries)
        where.append(f"country IN ({lst})")
    if date_range:
        where.append(f"invoice_date >= '{date_range[0]}'")
        where.append(f"invoice_date < '{date_range[1]}'")
    con.execute(
        f"CREATE VIEW tx AS SELECT * FROM read_parquet('{path}') WHERE {' AND '.join(where)}"
    )
    return con


def _read_sql(name):
    return (SQL / name).read_text()


def kpis(**f) -> dict:
    con = _con(**f)
    row = con.execute(
        """SELECT COUNT(DISTINCT customer_id) AS customers,
                  COUNT(DISTINCT invoice)     AS orders,
                  ROUND(SUM(revenue))         AS revenue,
                  ROUND(SUM(revenue) / NULLIF(COUNT(DISTINCT invoice), 0), 2) AS avg_order_value
           FROM tx"""
    ).fetchone()
    con.close()
    return {"customers": row[0], "orders": row[1], "revenue": row[2], "avg_order_value": row[3]}


def rfm(**f) -> pd.DataFrame:
    con = _con(**f)
    df = con.execute(_read_sql("02_rfm.sql")).df()
    con.close()
    return df


def segment_summary(**f) -> pd.DataFrame:
    df = rfm(**f)
    if df.empty:
        return df
    return (
        df.groupby("segment")
        .agg(customers=("customer_id", "count"),
             avg_monetary=("monetary", "mean"),
             total_monetary=("monetary", "sum"))
        .reset_index()
        .sort_values("total_monetary", ascending=False)
    )


def churn_rate(threshold_days: int, **f) -> float:
    """Share of customers whose recency exceeds the threshold."""
    df = rfm(**f)
    if df.empty:
        return 0.0
    return round(100.0 * (df["recency_days"] > threshold_days).mean(), 1)


def cohort(**f) -> pd.DataFrame:
    con = _con(**f)
    df = con.execute(_read_sql("03_cohort.sql")).df()
    con.close()
    return df


def cohort_pivot(**f) -> pd.DataFrame:
    df = cohort(**f)
    if df.empty:
        return df
    df["cohort_month"] = pd.to_datetime(df["cohort_month"]).dt.strftime("%Y-%m")
    return df.pivot(index="cohort_month", columns="month_index", values="retention_pct")


def monthly_revenue(**f) -> pd.DataFrame:
    con = _con(**f)
    df = con.execute(
        """SELECT date_trunc('month', invoice_date) AS month,
                  ROUND(SUM(revenue)) AS revenue,
                  COUNT(DISTINCT customer_id) AS active_customers
           FROM tx GROUP BY month ORDER BY month"""
    ).df()
    con.close()
    return df


def country_list() -> list:
    con = duckdb.connect()
    df = con.execute(
        f"SELECT country, COUNT(*) n FROM read_parquet('{PARQUET}') "
        f"GROUP BY country ORDER BY n DESC"
    ).df()
    con.close()
    return df["country"].tolist()


def date_bounds():
    con = duckdb.connect()
    row = con.execute(
        f"SELECT MIN(invoice_date), MAX(invoice_date) FROM read_parquet('{PARQUET}')"
    ).fetchone()
    con.close()
    return row[0], row[1]
