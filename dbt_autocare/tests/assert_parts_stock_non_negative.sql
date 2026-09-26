-- Test: Asserts that spare parts inventory counts in the warehouse are non-negative
SELECT
    dealer_operational_pk,
    dealer_id,
    month_key,
    total_parts_stock
FROM {{ ref('mart_dealer_operational_summary') }}
WHERE total_parts_stock < 0
