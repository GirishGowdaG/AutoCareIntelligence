SELECT
    diagnostic_id,
    vehicle_id,
    timestamp,
    code AS dtc_code,
    component,
    severity,
    _source_file,
    _bronze_batch_id,
    _silver_batch_id,
    _staging_loaded_at
FROM {{ source('staging', 'silver_diagnostics') }}
