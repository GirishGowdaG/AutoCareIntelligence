{{ config(materialized='table') }}

WITH failures AS (
    SELECT * FROM {{ ref('int_component_failures_joined') }}
),

components AS (
    SELECT * FROM {{ ref('stg_dim_component') }}
),

models AS (
    SELECT * FROM {{ ref('stg_dim_model') }}
)

SELECT
    MD5(CONCAT(CAST(f.component_key AS TEXT), '|', CAST(f.model_key AS TEXT), '|', CAST(f.month_key AS TEXT))) AS component_risk_pk,
    f.component_key,
    f.model_key,
    f.month_key,
    c.component_name,
    c.category AS component_category,
    c.expected_lifespan_km,
    c.warranty_period_months,
    m.model_name,
    m.vehicle_class,
    m.powertrain_type,
    f.total_dtc_count,
    f.critical_dtc_count,
    f.high_dtc_count,
    f.unique_vehicles_with_dtc,
    f.warranty_claim_count,
    f.total_warranty_amount,
    f.avg_warranty_claim_amount,
    ROUND(
        CAST(
            (f.critical_dtc_count * 3.0 + f.high_dtc_count * 1.5 + (f.total_dtc_count - f.critical_dtc_count - f.high_dtc_count) * 0.5)
            AS NUMERIC
        ), 2
    ) AS failure_severity_score,
    CASE
        WHEN f.critical_dtc_count > 5 OR f.total_warranty_amount > 10000.00 THEN 'HIGH_RISK'
        WHEN f.critical_dtc_count > 0 OR f.warranty_claim_count > 2 THEN 'MEDIUM_RISK'
        ELSE 'LOW_RISK'
    END AS risk_tier
FROM failures f
JOIN components c ON f.component_key = c.component_key
JOIN models m ON f.model_key = m.model_key
