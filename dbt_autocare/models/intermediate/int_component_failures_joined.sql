{{ config(materialized='table') }}

WITH diagnostics_resolved AS (
    SELECT
        d.diagnostic_id,
        d.vehicle_id,
        COALESCE(v.vehicle_key, -1) AS vehicle_key,
        COALESCE(v.model_key, -1) AS model_key,
        COALESCE(c.component_key, -1) AS component_key,
        CAST(TO_CHAR(d.timestamp, 'YYYYMMDD') AS INT) AS date_key,
        CAST(TO_CHAR(d.timestamp, 'YYYYMM') AS INT) AS month_key,
        d.timestamp,
        d.dtc_code,
        d.component AS component_name,
        d.severity,
        CASE WHEN d.severity = 'CRITICAL' THEN 1 ELSE 0 END AS is_critical_dtc,
        CASE WHEN d.severity = 'HIGH' THEN 1 ELSE 0 END AS is_high_dtc
    FROM {{ ref('stg_diagnostics') }} d
    LEFT JOIN {{ ref('stg_dim_vehicle') }} v
        ON d.vehicle_id = v.vehicle_id
    LEFT JOIN {{ ref('stg_dim_component') }} c
        ON LOWER(TRIM(d.component)) = LOWER(TRIM(c.component_name))
),

diagnostics_monthly AS (
    SELECT
        component_key,
        model_key,
        month_key,
        COUNT(diagnostic_id) AS total_dtc_count,
        SUM(is_critical_dtc) AS critical_dtc_count,
        SUM(is_high_dtc) AS high_dtc_count,
        COUNT(DISTINCT vehicle_key) AS unique_vehicles_with_dtc
    FROM diagnostics_resolved
    GROUP BY component_key, model_key, month_key
),

warranty_monthly AS (
    SELECT
        w.component_key,
        v.model_key,
        CAST(TO_CHAR(w.claim_date, 'YYYYMM') AS INT) AS month_key,
        COUNT(w.warranty_fact_id) AS warranty_claim_count,
        SUM(w.amount) AS total_warranty_amount,
        ROUND(AVG(w.amount), 2) AS avg_warranty_claim_amount
    FROM {{ ref('stg_fact_warranty') }} w
    JOIN {{ ref('stg_dim_vehicle') }} v
        ON w.vehicle_key = v.vehicle_key
    GROUP BY w.component_key, v.model_key, CAST(TO_CHAR(w.claim_date, 'YYYYMM') AS INT)
),

combined_keys AS (
    SELECT component_key, model_key, month_key FROM diagnostics_monthly
    UNION
    SELECT component_key, model_key, month_key FROM warranty_monthly
)

SELECT
    k.component_key,
    k.model_key,
    k.month_key,
    COALESCE(dm.total_dtc_count, 0) AS total_dtc_count,
    COALESCE(dm.critical_dtc_count, 0) AS critical_dtc_count,
    COALESCE(dm.high_dtc_count, 0) AS high_dtc_count,
    COALESCE(dm.unique_vehicles_with_dtc, 0) AS unique_vehicles_with_dtc,
    COALESCE(wm.warranty_claim_count, 0) AS warranty_claim_count,
    COALESCE(wm.total_warranty_amount, 0.00) AS total_warranty_amount,
    COALESCE(wm.avg_warranty_claim_amount, 0.00) AS avg_warranty_claim_amount
FROM combined_keys k
LEFT JOIN diagnostics_monthly dm
    ON k.component_key = dm.component_key
   AND k.model_key = dm.model_key
   AND k.month_key = dm.month_key
LEFT JOIN warranty_monthly wm
    ON k.component_key = wm.component_key
   AND k.model_key = wm.model_key
   AND k.month_key = wm.month_key
