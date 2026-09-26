{{ config(materialized='table') }}

WITH trip_sessions AS (
    SELECT * FROM {{ ref('int_telemetry_trip_sessions') }}
),

vehicles AS (
    SELECT * FROM {{ ref('stg_dim_vehicle') }}
),

models AS (
    SELECT * FROM {{ ref('stg_dim_model') }}
),

customers AS (
    SELECT * FROM {{ ref('stg_dim_customer') }}
),

dealers AS (
    SELECT * FROM {{ ref('stg_dim_dealer') }}
),

dates AS (
    SELECT * FROM {{ ref('stg_dim_date') }}
)

SELECT
    MD5(CONCAT(CAST(t.vehicle_key AS TEXT), '|', CAST(t.date_key AS TEXT))) AS vehicle_health_pk,
    t.vehicle_key,
    t.date_key,
    d.calendar_date,
    d.year,
    d.month_number,
    d.month_name,
    d.is_weekend,
    v.vehicle_id,
    v.variant,
    v.manufacture_year,
    v.status AS vehicle_status,
    m.model_name,
    m.vehicle_class,
    m.powertrain_type,
    c.customer_id,
    c.customer_name,
    c.city AS customer_city,
    c.state AS customer_state,
    dlr.dealer_name AS selling_dealer_name,
    dlr.region AS selling_dealer_region,
    t.total_telemetry_pings,
    t.daily_operating_hours,
    t.avg_rpm,
    t.max_rpm,
    t.avg_temperature,
    t.max_temperature,
    t.avg_battery_voltage,
    t.min_battery_voltage,
    t.avg_vibration,
    t.max_vibration,
    t.vibration_alert_count,
    t.temperature_alert_count,
    t.battery_alert_count,
    CASE
        WHEN t.temperature_alert_count > 0 OR t.vibration_alert_count > 3 OR t.battery_alert_count > 3 THEN 'CRITICAL'
        WHEN t.vibration_alert_count > 0 OR t.battery_alert_count > 0 THEN 'WARNING'
        ELSE 'HEALTHY'
    END AS health_status
FROM trip_sessions t
JOIN dates d ON t.date_key = d.date_key
JOIN vehicles v ON t.vehicle_key = v.vehicle_key
JOIN models m ON v.model_key = m.model_key
JOIN customers c ON v.customer_key = c.customer_key
JOIN dealers dlr ON v.selling_dealer_key = dlr.dealer_key
