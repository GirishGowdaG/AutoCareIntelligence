-- Test: Asserts that total dealer service revenue reconciles with total fact_service invoice amounts
WITH mart_total AS (
    SELECT COALESCE(SUM(total_service_revenue), 0.00) AS total_revenue
    FROM {{ ref('mart_dealer_operational_summary') }}
),

fact_total AS (
    SELECT COALESCE(SUM(cost), 0.00) AS total_cost
    FROM {{ ref('stg_fact_service') }}
)

SELECT
    m.total_revenue AS mart_revenue,
    f.total_cost AS fact_cost,
    ABS(m.total_revenue - f.total_cost) AS variance
FROM mart_total m
CROSS JOIN fact_total f
WHERE ABS(m.total_revenue - f.total_cost) > 0.01
