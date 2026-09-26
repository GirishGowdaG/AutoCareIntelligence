SELECT
    vehicle_key,
    vehicle_id,
    model_key,
    customer_key,
    selling_dealer_key,
    variant,
    manufacture_date,
    manufacture_year,
    status
FROM {{ source('autocare_dw', 'dim_vehicle') }}
