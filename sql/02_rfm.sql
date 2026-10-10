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
        -- lower recency (more recent) should score higher -> ORDER BY recency DESC.
        -- customer_id breaks ties so the same data always gets the same scores.
        NTILE(5) OVER (ORDER BY recency_days DESC, customer_id) AS r_score,
        NTILE(5) OVER (ORDER BY frequency ASC, customer_id)     AS f_score,
        NTILE(5) OVER (ORDER BY monetary ASC, customer_id)      AS m_score
    FROM per_customer
)
SELECT
    customer_id, recency_days, frequency, monetary,
    r_score, f_score, m_score,
    (r_score + f_score + m_score) AS rfm_total,
    -- A recency x frequency grid: every (r, f) pair lands in exactly one segment.
    -- Recency gates every "good" segment, so a frequent buyer who has gone quiet
    -- is At Risk, not Loyal.
    CASE
        WHEN r_score >= 4 AND f_score >= 4 THEN 'Champions'
        WHEN r_score >= 3 AND f_score >= 3 THEN 'Loyal'
        WHEN r_score >= 4                  THEN 'New'                 -- recent, 1-2 orders
        WHEN r_score =  3                  THEN 'Potential Loyalist'  -- fairly recent, few orders
        WHEN f_score >= 3                  THEN 'At Risk'             -- was frequent, now lapsed
        ELSE 'Hibernating'                                            -- lapsed and infrequent
    END AS segment
FROM scored;
