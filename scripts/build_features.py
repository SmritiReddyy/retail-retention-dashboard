"""Clean the raw Online Retail II file into a compact Parquet extract.

Usage:
    python scripts/build_features.py

Auto-detects data/*.csv or data/*.xlsx, runs sql/01_clean.sql, writes
data/clean_transactions.parquet (small enough to commit for Streamlit Cloud).
"""
import glob
import os
import pathlib

import duckdb

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = DATA / "clean_transactions.parquet"


def find_source():
    csv = glob.glob(str(DATA / "*.csv"))
    xlsx = [f for f in glob.glob(str(DATA / "*.xlsx"))]
    if csv:
        return f"read_csv_auto('{csv[0]}', header=true, sample_size=-1)"
    if xlsx:
        # openpyxl-backed reader; reads the first sheet
        return f"read_xlsx('{xlsx[0]}', all_varchar=false)"
    raise SystemExit("No data/*.csv or data/*.xlsx found. See scripts/DOWNLOAD.md")


def main():
    os.chdir(ROOT)
    src = find_source()
    con = duckdb.connect()
    con.execute("INSTALL excel; LOAD excel;")  # for read_xlsx (no-op if csv)
    sql = (ROOT / "sql" / "01_clean.sql").read_text().replace("{SRC}", src)
    con.execute(sql)
    n = con.execute("SELECT COUNT(*) FROM clean_transactions").fetchone()[0]
    con.execute(f"COPY clean_transactions TO '{OUT}' (FORMAT PARQUET)")
    span = con.execute(
        "SELECT MIN(invoice_date), MAX(invoice_date), "
        "COUNT(DISTINCT customer_id), ROUND(SUM(revenue)) FROM clean_transactions"
    ).fetchone()
    con.close()
    print(f"Wrote {OUT.name}: {n:,} clean rows")
    print(f"  date range : {span[0]} -> {span[1]}")
    print(f"  customers  : {span[2]:,}")
    print(f"  revenue    : {span[3]:,.0f}")
    print("\nNext: streamlit run app/streamlit_app.py")


if __name__ == "__main__":
    main()
