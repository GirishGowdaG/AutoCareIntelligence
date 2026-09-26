-- Test: Asserts that warranty reimbursement claim amounts are strictly positive
SELECT
    warranty_cost_pk,
    component_key,
    month_key,
    total_claim_amount
FROM {{ ref('mart_warranty_cost_analysis') }}
WHERE total_claim_amount <= 0.00
