SELECT
    model_key,
    model_name,
    vehicle_class,
    powertrain_type,
    fuel_capacity_or_kwh,
    curb_weight_kg
FROM {{ source('autocare_dw', 'dim_model') }}
