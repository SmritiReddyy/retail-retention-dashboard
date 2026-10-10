"""Clean the raw Online Retail II file into a compact Parquet extract.

Usage:
    python scripts/build_features.py

Auto-detects data/*.csv or data/*.xlsx, runs sql/01_clean.sql, writes
data/clean_transactions.parquet (small enough to commit for Streamlit Cloud)
and prints a cleaning funnel showing how many rows each rule removed.
"""
import glob
import os
import pathlib

import duckdb

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = DATA / "clean_transactions.parquet"
# The UCI workbook splits the history across two sheets.
SHEETS = ("Year 2009-2010", "Year 2010-2011")


def load_raw(con):
    """Load every source row into `raw`, all columns as VARCHAR.

    Reading as text avoids type sniffing, which fails on the workbook because
    'Invoice' looks numeric until the first cancelled 'C489449'.
    """
    csv = glob.glob(str(DATA / "*.csv"))
    xlsx = glob.glob(str(DATA / "*.xlsx"))
    if csv:
        con.execute(f"CREATE TABLE raw AS SELECT * FROM read_csv('{csv[0]}', header=true, all_varchar=true)")
    elif xlsx:
        con.execute("INSTALL excel; LOAD excel;")
        parts = " UNION ALL ".join(
            f"SELECT * FROM read_xlsx('{xlsx[0]}', sheet='{s}', all_varchar=true)" for s in SHEETS
        )
        con.execute(f"CREATE TABLE raw AS {parts}")
    else:
        raise SystemExit("No data/*.csv or data/*.xlsx found. See scripts/DOWNLOAD.md")


FUNNEL = [
    ("raw rows", "SELECT COUNT(*) FROM raw"),
    ("after removing exact duplicates", "SELECT COUNT(*) FROM typed"),
    ("  with a customer ID", "SELECT COUNT(*) FROM typed WHERE customer_id IS NOT NULL"),
    ("  and not a cancellation", "SELECT COUNT(*) FROM typed WHERE customer_id IS NOT NULL AND invoice NOT LIKE 'C%'"),
    ("  and positive quantity and price", "SELECT COUNT(*) FROM typed WHERE customer_id IS NOT NULL "
     "AND invoice NOT LIKE 'C%' AND quantity > 0 AND price > 0"),
    ("clean (also excluding service codes)", "SELECT COUNT(*) FROM clean_transactions"),
]


def main():
    os.chdir(ROOT)
    con = duckdb.connect()
    load_raw(con)
    con.execute((ROOT / "sql" / "01_clean.sql").read_text())
    con.execute(f"COPY clean_transactions TO '{OUT}' (FORMAT PARQUET, COMPRESSION ZSTD)")

    print("Cleaning funnel")
    for label, q in FUNNEL:
        print(f"  {label:40s} {con.execute(q).fetchone()[0]:>10,}")
    span = con.execute(
        "SELECT MIN(invoice_date), MAX(invoice_date), COUNT(DISTINCT customer_id), "
        "COUNT(DISTINCT invoice), COUNT(DISTINCT country), ROUND(SUM(revenue)) FROM clean_transactions"
    ).fetchone()
    con.close()
    print(f"\nWrote {OUT.name} ({OUT.stat().st_size / 2**20:.1f} MiB)")
    print(f"  date range : {span[0]} -> {span[1]}")
    print(f"  customers  : {span[2]:,}")
    print(f"  orders     : {span[3]:,}")
    print(f"  countries  : {span[4]}")
    print(f"  revenue    : £{span[5]:,.0f}")
    print("\nNext: streamlit run app/streamlit_app.py")


if __name__ == "__main__":
    main()
