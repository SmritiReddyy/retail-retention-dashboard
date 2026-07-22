-- 01_clean.sql
-- Turn the raw Online Retail II rows into a clean transaction fact.
-- Parameterized by {SRC} (a read_csv/read_xlsx call injected by build_features.py).

CREATE OR REPLACE TABLE clean_transactions AS
SELECT
    "Invoice"                              AS invoice,
    "StockCode"                            AS stock_code,
    "Description"                          AS description,
    CAST("Quantity" AS INTEGER)            AS quantity,
    CAST("InvoiceDate" AS TIMESTAMP)       AS invoice_date,
    CAST("Price" AS DOUBLE)                AS price,
    CAST("Customer ID" AS BIGINT)          AS customer_id,
    "Country"                              AS country,
    CAST("Quantity" AS INTEGER) * CAST("Price" AS DOUBLE) AS revenue
FROM {SRC}
WHERE "Customer ID" IS NOT NULL          -- can't attribute anonymous sales to a customer
  AND "Quantity" > 0                     -- drop returns / adjustments (negative qty)
  AND "Price" > 0                        -- drop zero/negative price rows
  AND CAST("Invoice" AS VARCHAR) NOT LIKE 'C%';  -- 'C' prefix = cancelled invoice
