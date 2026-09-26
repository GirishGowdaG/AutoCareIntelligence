{{ config(materialized='table') }}

WITH warranty_claims AS (
    SELECT
        w.component_key,
        CAST(TO_CHAR(w.claim_date, 'YYYYMM') AS INT) AS month_key,
        COUNT(w.warranty_fact_id) AS total_claims,
        COUNT(DISTINCT w.vehicle_key) AS unique_vehicles_claimed,
        SUM(w.amount) AS total_claim_amount,
        ROUND(AVG(w.amount), 2) AS avg_claim_amount,
        MIN(w.amount) AS min_claim_amount,
        MAX(w.amount) AS max_claim_amount
    FROM {{ ref('stg_fact_warranty') }} w
    GROUP BY w.component_key, CAST(TO_CHAR(w.claim_date, 'YYYYMM') AS INT)
),

components AS (
    SELECT * FROM {{ ref('stg_dim_component') }}
)

SELECT
    MD5(CONCAT(CAST(w.component_key AS TEXT), '|', CAST(w.month_key AS TEXT))) AS warranty_cost_pk,
    w.component_key,
    w.month_key,
    c.component_name,
    c.category AS component_category,
    c.expected_lifespan_km,
    c.warranty_period_months,
    w.total_claims,
    w.unique_vehicles_claimed,
    w.total_claim_amount,
    w.avg_claim_amount,
    w.min_claim_amount,
    w.max_claim_amount
FROM warranty_claims w
JOIN components c ON w.component_key = c.component_key
