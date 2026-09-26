SELECT
    customer_key,
    customer_id,
    customer_name,
    email,
    phone,
    address,
    city,
    state,
    created_at
FROM {{ source('autocare_dw', 'dim_customer') }}
