{{ config(materialized='table') }}

WITH ordered_telemetry AS (
    SELECT
        telemetry_fact_id,
        vehicle_key,
        date_key,
        timestamp,
        rpm,
        temperature,
        battery,
        vibration,
        LAG(timestamp) OVER (
            PARTITION BY vehicle_key, date_key
            ORDER BY timestamp
        ) AS prev_timestamp
    FROM {{ ref('stg_fact_telemetry') }}
),

deltas AS (
    SELECT
        telemetry_fact_id,
        vehicle_key,
        date_key,
        timestamp,
        rpm,
        temperature,
        battery,
        vibration,
        CASE
            WHEN prev_timestamp IS NULL THEN 0.0
            ELSE EXTRACT(EPOCH FROM (timestamp - prev_timestamp))
        END AS delta_seconds
    FROM ordered_telemetry
),

flagged_deltas AS (
    SELECT
        telemetry_fact_id,
        vehicle_key,
        date_key,
        timestamp,
        rpm,
        temperature,
        battery,
        vibration,
        delta_seconds,
        -- Accumulate operating time only when delta <= 300s inactivity limit and engine rpm > 0
        CASE
            WHEN delta_seconds > 0 AND delta_seconds <= {{ var('telemetry_session_gap_seconds', 300) }} AND rpm > 0
            THEN delta_seconds
            ELSE 0.0
        END AS active_operating_seconds,
        -- Vibration anomaly flag (PROPOSED INITIAL HEURISTIC THRESHOLD)
        CASE
            WHEN vibration >= {{ var('vibration_anomaly_threshold', 2.5) }} THEN 1
            ELSE 0
        END AS is_vibration_alert,
        CASE
            WHEN temperature >= 105.0 THEN 1
            ELSE 0
        END AS is_temperature_alert,
        CASE
            WHEN battery < 11.8 OR battery > 15.0 THEN 1
            ELSE 0
        END AS is_battery_alert
    FROM deltas
)

SELECT
    vehicle_key,
    date_key,
    COUNT(*) AS total_telemetry_pings,
    ROUND(CAST(SUM(active_operating_seconds) / 3600.0 AS NUMERIC), 4) AS daily_operating_hours,
    ROUND(AVG(rpm), 2) AS avg_rpm,
    MAX(rpm) AS max_rpm,
    ROUND(AVG(temperature), 2) AS avg_temperature,
    MAX(temperature) AS max_temperature,
    ROUND(AVG(battery), 2) AS avg_battery_voltage,
    MIN(battery) AS min_battery_voltage,
    ROUND(AVG(vibration), 3) AS avg_vibration,
    MAX(vibration) AS max_vibration,
    SUM(is_vibration_alert) AS vibration_alert_count,
    SUM(is_temperature_alert) AS temperature_alert_count,
    SUM(is_battery_alert) AS battery_alert_count
FROM flagged_deltas
GROUP BY vehicle_key, date_key
