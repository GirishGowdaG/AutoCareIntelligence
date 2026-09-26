-- Test: Asserts that daily operating hours per vehicle are within [0.0, 24.0]
SELECT
    vehicle_health_pk,
    vehicle_id,
    calendar_date,
    daily_operating_hours
FROM {{ ref('mart_vehicle_health_daily') }}
WHERE daily_operating_hours < 0.0 OR daily_operating_hours > 24.0
