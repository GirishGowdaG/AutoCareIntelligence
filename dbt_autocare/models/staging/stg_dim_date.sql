SELECT
    date_key,
    calendar_date,
    day_of_week,
    day_name,
    day_of_month,
    day_of_year,
    week_of_year,
    month_number,
    month_name,
    quarter,
    year,
    is_weekend
FROM {{ source('autocare_dw', 'dim_date') }}
