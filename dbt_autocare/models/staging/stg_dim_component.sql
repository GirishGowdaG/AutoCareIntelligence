SELECT
    component_key,
    component_name,
    category,
    expected_lifespan_km,
    warranty_period_months
FROM {{ source('autocare_dw', 'dim_component') }}
