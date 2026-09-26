{{ config(materialized='table') }}

WITH service_monthly AS (
    SELECT
        dealer_key,
        CAST(TO_CHAR(visit_date, 'YYYYMM') AS INT) AS month_key,
        COUNT(service_fact_id) AS total_service_invoices,
        SUM(cost) AS total_service_revenue,
        ROUND(AVG(cost), 2) AS avg_service_invoice_cost,
        COUNT(DISTINCT vehicle_key) AS unique_vehicles_serviced
    FROM {{ ref('stg_fact_service') }}
    GROUP BY dealer_key, CAST(TO_CHAR(visit_date, 'YYYYMM') AS INT)
),

parts_monthly AS (
    SELECT
        dealer_key,
        CAST(TO_CHAR(snapshot_date, 'YYYYMM') AS INT) AS month_key,
        SUM(stock) AS total_parts_stock,
        ROUND(AVG(lead_time), 2) AS avg_parts_lead_time_days,
        COUNT(CASE WHEN stock < 10 THEN 1 END) AS low_stock_sku_count,
        COUNT(CASE WHEN stock = 0 THEN 1 END) AS out_of_stock_sku_count
    FROM {{ ref('stg_fact_parts') }}
    GROUP BY dealer_key, CAST(TO_CHAR(snapshot_date, 'YYYYMM') AS INT)
),

dealer_months AS (
    SELECT dealer_key, month_key FROM service_monthly
    UNION
    SELECT dealer_key, month_key FROM parts_monthly
)

SELECT
    dm.dealer_key,
    dm.month_key,
    COALESCE(s.total_service_invoices, 0) AS total_service_invoices,
    COALESCE(s.total_service_revenue, 0.00) AS total_service_revenue,
    COALESCE(s.avg_service_invoice_cost, 0.00) AS avg_service_invoice_cost,
    COALESCE(s.unique_vehicles_serviced, 0) AS unique_vehicles_serviced,
    COALESCE(p.total_parts_stock, 0) AS total_parts_stock,
    COALESCE(p.avg_parts_lead_time_days, 0.00) AS avg_parts_lead_time_days,
    COALESCE(p.low_stock_sku_count, 0) AS low_stock_sku_count,
    COALESCE(p.out_of_stock_sku_count, 0) AS out_of_stock_sku_count
FROM dealer_months dm
LEFT JOIN service_monthly s
    ON dm.dealer_key = s.dealer_key AND dm.month_key = s.month_key
LEFT JOIN parts_monthly p
    ON dm.dealer_key = p.dealer_key AND dm.month_key = p.month_key
