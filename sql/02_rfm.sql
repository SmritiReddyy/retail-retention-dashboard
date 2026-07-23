-- 02_rfm.sql
-- RFM segmentation. Reads from a view/table named `tx` (the app registers the
-- filtered Parquet as `tx`). Snapshot = day after the last transaction in scope.

WITH snap AS (
    SELECT CAST(MAX(invoice_date) AS DATE) + INTERVAL 1 DAY AS snapshot_date FROM tx
),
per_customer AS (
    SELECT
        customer_id,
        date_diff('day', CAST(MAX(invoice_date) AS DATE),
                  (SELECT snapshot_date FROM snap))  AS recency_days,
        COUNT(DISTINCT invoice)                       AS frequency,
        SUM(revenue)                                  AS monetary
    FROM tx
    GROUP BY customer_id
),
scored AS (
    SELECT *,
        -- lower recency (more recent) should score higher -> ORDER BY recency DESC
        NTILE(5) OVER (ORDER BY recency_days DESC)  AS r_score,
        NTILE(5) OVER (ORDER BY frequency ASC)      AS f_score,
        NTILE(5) OVER (ORDER BY monetary ASC)       AS m_score
    FROM per_customer
)
SELECT
    customer_id, recency_days, frequency, monetary,
    r_score, f_score, m_score,
    (r_score + f_score + m_score) AS rfm_total,
    CASE
        WHEN r_score >= 4 AND f_score >= 4               THEN 'Champions'
        WHEN f_score >= 4                                THEN 'Loyal'
        WHEN r_score >= 4 AND f_score <= 2               THEN 'New'
        WHEN r_score >= 3 AND f_score >= 3               THEN 'Potential Loyalist'
        WHEN r_score <= 2 AND f_score >= 3               THEN 'At Risk'
        WHEN r_score <= 2 AND f_score <= 2               THEN 'Hibernating'
        ELSE 'Needs Attention'
    END AS segment
FROM scored;
