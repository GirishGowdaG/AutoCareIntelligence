SELECT
    service_fact_id,
    service_id,
    vehicle_key,
    dealer_key,
    date_key,
    visit_date,
    issue,
    cost,
    _silver_batch_id,
    _loaded_at
FROM {{ source('autocare_dw', 'fact_service') }}
