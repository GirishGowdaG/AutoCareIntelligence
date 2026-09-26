SELECT
    parts_fact_id,
    part_id,
    dealer_key,
    component_key,
    date_key,
    snapshot_date,
    stock,
    lead_time,
    _silver_batch_id,
    _loaded_at
FROM {{ source('autocare_dw', 'fact_parts') }}
