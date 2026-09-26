{{ config(materialized='table') }}

WITH rollup AS (
    SELECT * FROM {{ ref('int_dealer_service_parts_rollup') }}
),

dealers AS (
    SELECT * FROM {{ ref('stg_dim_dealer') }}
)

SELECT
    MD5(CONCAT(CAST(r.dealer_key AS TEXT), '|', CAST(r.month_key AS TEXT))) AS dealer_operational_pk,
    r.dealer_key,
    r.month_key,
    d.dealer_id,
    d.dealer_name,
    d.city,
    d.state,
    d.region,
    d.tier AS dealer_tier,
    r.total_service_invoices,
    r.total_service_revenue,
    r.avg_service_invoice_cost,
    r.unique_vehicles_serviced,
    r.total_parts_stock,
    r.avg_parts_lead_time_days,
    r.low_stock_sku_count,
    r.out_of_stock_sku_count
FROM rollup r
JOIN dealers d ON r.dealer_key = d.dealer_key
