-- 03_cohort.sql
-- Monthly cohort retention. Each customer belongs to the cohort of their first
-- purchase month; we count how many are still active N months later.
-- Reads from `tx`.

WITH first_purchase AS (
    SELECT customer_id,
           date_trunc('month', MIN(invoice_date)) AS cohort_month
    FROM tx GROUP BY customer_id
),
activity AS (
    SELECT DISTINCT customer_id,
           date_trunc('month', invoice_date) AS active_month
    FROM tx
),
cohort_size AS (
    SELECT cohort_month, COUNT(*) AS n_customers
    FROM first_purchase GROUP BY cohort_month
)
SELECT
    f.cohort_month,
    date_diff('month', f.cohort_month, a.active_month) AS month_index,
    cs.n_customers                                     AS cohort_size,
    COUNT(DISTINCT a.customer_id)                      AS active_customers,
    ROUND(100.0 * COUNT(DISTINCT a.customer_id) / cs.n_customers, 1) AS retention_pct
FROM activity a
JOIN first_purchase f USING (customer_id)
JOIN cohort_size cs   ON cs.cohort_month = f.cohort_month
GROUP BY f.cohort_month, month_index, cs.n_customers
ORDER BY f.cohort_month, month_index;
