SELECT
    warranty_fact_id,
    claim_id,
    vehicle_key,
    component_key,
    date_key,
    claim_date,
    amount,
    _silver_batch_id,
    _loaded_at
FROM {{ source('autocare_dw', 'fact_warranty') }}
