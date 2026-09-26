SELECT
    telemetry_fact_id,
    vehicle_key,
    date_key,
    timestamp,
    rpm,
    temperature,
    battery,
    vibration,
    _silver_batch_id,
    _loaded_at
FROM {{ source('autocare_dw', 'fact_telemetry') }}
