-- 01_clean.sql
-- Turn the raw Online Retail II rows into a clean transaction fact.
-- Reads `raw`: every source column as VARCHAR, loaded by build_features.py from
-- both sheets of the UCI workbook (or the single Kaggle CSV).

CREATE OR REPLACE TABLE typed AS
SELECT DISTINCT                          -- the source has exact duplicate lines
    "Invoice"                                         AS invoice,
    "StockCode"                                       AS stock_code,
    "Description"                                     AS description,
    TRY_CAST("Quantity" AS INTEGER)                   AS quantity,
    CASE
        -- the workbook stores dates as Excel serial days since 1899-12-30
        WHEN regexp_full_match("InvoiceDate", '[0-9]+(\.[0-9]+)?')
        THEN TIMESTAMP '1899-12-30'
             + to_seconds(CAST(round(CAST("InvoiceDate" AS DOUBLE) * 86400) AS BIGINT))
        ELSE TRY_CAST("InvoiceDate" AS TIMESTAMP)
    END                                               AS invoice_date,
    TRY_CAST("Price" AS DOUBLE)                       AS price,
    TRY_CAST(TRY_CAST("Customer ID" AS DOUBLE) AS BIGINT) AS customer_id,
    "Country"                                         AS country
FROM raw;

CREATE OR REPLACE TABLE clean_transactions AS
SELECT *, quantity * price AS revenue
FROM typed
WHERE customer_id IS NOT NULL            -- can't attribute anonymous sales to a customer
  AND invoice NOT LIKE 'C%'              -- 'C' prefix = cancelled invoice
  AND quantity > 0                       -- drop returns / adjustments (negative qty)
  AND price > 0                          -- drop zero/negative price rows
  -- service and accounting lines, not products a customer bought
  AND upper(stock_code) NOT IN ('POST', 'DOT', 'M', 'D', 'C2', 'S', 'B', 'PADS', 'CRUK',
                                'BANK CHARGES', 'AMAZONFEE', 'ADJUST', 'ADJUST2')
  AND upper(stock_code) NOT LIKE 'TEST%';
