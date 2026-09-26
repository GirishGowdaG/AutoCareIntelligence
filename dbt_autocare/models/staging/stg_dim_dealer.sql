SELECT
    dealer_key,
    dealer_id,
    dealer_name,
    city,
    state,
    region,
    tier
FROM {{ source('autocare_dw', 'dim_dealer') }}
