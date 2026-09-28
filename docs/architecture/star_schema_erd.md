# AutoCare Intelligence — Star Schema & Database ERD Specification

**Document Version:** 1.0.0  
**Phase:** 6 — Productionization & Capstone Delivery  
**Classification:** Database Architecture & Dimensional Model Specification  

---

## 1. Dimensional Model Overview

The AutoCare Intelligence analytical core is architected as an enterprise dimensional Star Schema hosted in PostgreSQL (`autocare_dw` schema), complemented by the operational machine learning inference store (`ml_inference` schema).

The design strictly isolates dimensional entities from transactional fact tables to guarantee high-performance analytical slicing, deterministic grain consistency, and clean dbt model aggregation.

- **Warehouse Schema (`autocare_dw`):** Exactly 6 Dimensions and 4 Facts (10 base tables total).
- **Inference Schema (`ml_inference`):** 4 ML Prediction Tables and 1 Action Audit Log Table (5 base tables total).

---

## 2. Visual Entity-Relationship Diagram (ERD)

```mermaid
erDiagram
    %% DIMENSIONS
    DIM_VEHICLE {
        int vehicle_key PK
        varchar vehicle_id UK
        int model_key FK
        int customer_key FK
        date purchase_date
        int warranty_duration_months
        varchar vehicle_class
    }

    DIM_MODEL {
        int model_key PK
        varchar model_name
        varchar manufacturer
        int year
        varchar body_type
        varchar fuel_type
    }

    DIM_DEALER {
        int dealer_key PK
        varchar dealer_id UK
        varchar dealer_name
        varchar region
        varchar city
        varchar state
    }

    DIM_CUSTOMER {
        int customer_key PK
        varchar customer_id UK
        varchar customer_name
        varchar customer_type
        varchar contact_phone
        varchar contact_email
    }

    DIM_DATE {
        int date_key PK
        date full_date UK
        int year
        int quarter
        int month
        int day
        varchar day_name
        boolean is_weekend
    }

    DIM_COMPONENT {
        int component_key PK
        varchar component_id UK
        varchar component_name
        varchar component_category
        decimal unit_cost
        int expected_lifespan_miles
    }

    %% FACTS
    FACT_TELEMETRY {
        bigint telemetry_key PK
        int vehicle_key FK
        int date_key FK
        timestamp recorded_at
        decimal rpm
        decimal engine_temperature
        decimal battery_voltage
        decimal vibration
        decimal speed_mph
    }

    FACT_SERVICE {
        bigint service_key PK
        int vehicle_key FK
        int dealer_key FK
        int date_key FK
        varchar service_id UK
        varchar issue_description
        decimal labor_hours
        decimal labor_cost
        decimal parts_cost
        decimal total_cost
        boolean is_breakdown
    }

    FACT_WARRANTY {
        bigint warranty_key PK
        int service_key FK
        int vehicle_key FK
        int dealer_key FK
        int date_key FK
        varchar claim_id UK
        decimal claim_amount
        varchar claim_status
        date filing_date
        date resolution_date
    }

    FACT_PARTS {
        bigint parts_usage_key PK
        int service_key FK
        int component_key FK
        int quantity
        decimal unit_price
        decimal total_parts_cost
    }

    %% ML INFERENCE
    VEHICLE_FAILURE_PREDICTIONS {
        varchar vehicle_id PK
        date cutoff_date PK
        decimal risk_score
        varchar risk_tier
        jsonb top_features
        timestamp scored_at
    }

    SENSOR_ANOMALY_PREDICTIONS {
        bigint prediction_id PK
        varchar vehicle_id
        timestamp window_timestamp
        decimal anomaly_score
        boolean is_anomaly
        decimal decision_threshold
        jsonb anomalous_features
        decimal algorithmic_latency_ms
        varchar model_version
    }

    DEALER_DEMAND_FORECASTS {
        varchar dealer_id PK
        date forecast_date PK
        int horizon_days
        decimal predicted_visits
        decimal lower_bound_80
        decimal upper_bound_80
        varchar model_version
    }

    WARRANTY_OUTLIER_PREDICTIONS {
        varchar claim_id PK
        varchar dealer_id
        decimal claim_amount
        decimal outlier_score
        decimal percentile_rank
        boolean audit_recommended
        varchar ranking_scope
    }

    ACTION_LOGS {
        varchar action_id PK
        varchar rule_id
        varchar entity_type
        varchar entity_id
        timestamp trigger_timestamp
        decimal trigger_value
        decimal threshold_applied
        text action_taken
        varchar channel_dispatched
        varchar delivery_status
        jsonb payload
    }

    %% RELATIONSHIPS
    DIM_MODEL ||--o{ DIM_VEHICLE : "classifies"
    DIM_CUSTOMER ||--o{ DIM_VEHICLE : "owns"

    DIM_VEHICLE ||--o{ FACT_TELEMETRY : "generates"
    DIM_DATE ||--o{ FACT_TELEMETRY : "timestamps"

    DIM_VEHICLE ||--o{ FACT_SERVICE : "receives"
    DIM_DEALER ||--o{ FACT_SERVICE : "performs"
    DIM_DATE ||--o{ FACT_SERVICE : "recorded_on"

    FACT_SERVICE ||--o| FACT_WARRANTY : "claims"
    DIM_VEHICLE ||--o{ FACT_WARRANTY : "subject_of"
    DIM_DEALER ||--o{ FACT_WARRANTY : "submitted_by"
    DIM_DATE ||--o{ FACT_WARRANTY : "filed_on"

    FACT_SERVICE ||--o{ FACT_PARTS : "requires"
    DIM_COMPONENT ||--o{ FACT_PARTS : "supplies"

    DIM_VEHICLE ||--o{ VEHICLE_FAILURE_PREDICTIONS : "scored_for"
    DIM_VEHICLE ||--o{ SENSOR_ANOMALY_PREDICTIONS : "monitored_by"
    DIM_DEALER ||--o{ DEALER_DEMAND_FORECASTS : "forecast_for"
    FACT_WARRANTY ||--o| WARRANTY_OUTLIER_PREDICTIONS : "audited_as"

    VEHICLE_FAILURE_PREDICTIONS ||--o{ ACTION_LOGS : "triggers"
    SENSOR_ANOMALY_PREDICTIONS ||--o{ ACTION_LOGS : "triggers"
    DEALER_DEMAND_FORECASTS ||--o{ ACTION_LOGS : "triggers"
    WARRANTY_OUTLIER_PREDICTIONS ||--o{ ACTION_LOGS : "triggers"
```

---

## 3. Dimension Specifications

### 3.1 `dim_vehicle`
- **Grain:** One row per unique vehicle in the fleet.
- **Surrogate Key:** `vehicle_key` (SERIAL / INT).
- **Natural / Business Key:** `vehicle_id` (e.g., `VH-00101`).
- **Foreign Keys:** `model_key -> dim_model(model_key)`, `customer_key -> dim_customer(customer_key)`.
- **Attributes:** `purchase_date`, `warranty_duration_months`, `vehicle_class` (`PASSENGER`, `COMMERCIAL_LIGHT`, `HEAVY_DUTY`).

### 3.2 `dim_model`
- **Grain:** One row per manufacturer make, model, and year specification.
- **Surrogate Key:** `model_key` (SERIAL / INT).
- **Attributes:** `model_name`, `manufacturer`, `year`, `body_type` (`SEDAN`, `SUV`, `TRUCK`), `fuel_type` (`GASOLINE`, `HYBRID`, `ELECTRIC`).

### 3.3 `dim_dealer`
- **Grain:** One row per authorized dealership service center.
- **Surrogate Key:** `dealer_key` (SERIAL / INT).
- **Natural / Business Key:** `dealer_id` (e.g., `DLR-001`).
- **Attributes:** `dealer_name`, `region`, `city`, `state`.

### 3.4 `dim_customer`
- **Grain:** One row per registered vehicle owner or corporate fleet entity.
- **Surrogate Key:** `customer_key` (SERIAL / INT).
- **Natural / Business Key:** `customer_id` (e.g., `CUST-0042`).
- **Attributes:** `customer_name`, `customer_type` (`INDIVIDUAL`, `COMMERCIAL_FLEET`), contact metadata.

### 3.5 `dim_date`
- **Grain:** One row per calendar day.
- **Surrogate Key:** `date_key` (INT in format `YYYYMMDD`).
- **Natural Key:** `full_date` (DATE).
- **Attributes:** `year`, `quarter`, `month`, `day`, `day_name`, `is_weekend`, `is_holiday`.

### 3.6 `dim_component`
- **Grain:** One row per serviceable vehicle part/component.
- **Surrogate Key:** `component_key` (SERIAL / INT).
- **Natural / Business Key:** `component_id` (e.g., `CMP-007`).
- **Attributes:** `component_name`, `component_category` (`BRAKE`, `POWERTRAIN`, `ELECTRICAL`, `COOLING`), `unit_cost`, `expected_lifespan_miles`.

---

## 4. Fact Specifications

### 4.1 `fact_telemetry`
- **Grain:** One row per aggregated 1-minute vehicle sensor ping window.
- **Primary Key:** `telemetry_key` (BIGSERIAL).
- **Foreign Keys:** `vehicle_key`, `date_key`.
- **Approved Sensor Attributes:**
  - `rpm` (Revolutions Per Minute)
  - `engine_temperature` (Celsius)
  - `battery_voltage` (Volts)
  - `vibration` (mm/s RMS)
  - `speed_mph` (Speed in miles per hour)
- **Note:** Excludes ambient temperature and vehicle class per ratified ML feature set contracts.

### 4.2 `fact_service`
- **Grain:** One row per completed dealership service order.
- **Primary Key:** `service_key` (BIGSERIAL).
- **Natural Key:** `service_id` (e.g., `SRV-008912`).
- **Foreign Keys:** `vehicle_key`, `dealer_key`, `date_key`.
- **Metrics & Indicators:** `labor_hours`, `labor_cost`, `parts_cost`, `total_cost`, `is_breakdown` (deterministic boolean derived from `is_breakdown_issue()`).

### 4.3 `fact_warranty`
- **Grain:** One row per warranty reimbursement claim filed.
- **Primary Key:** `warranty_key` (BIGSERIAL).
- **Natural Key:** `claim_id` (e.g., `CLM-00912`).
- **Foreign Keys:** `service_key`, `vehicle_key`, `dealer_key`, `date_key`.
- **Attributes & Financials:** `claim_amount`, `claim_status` (`APPROVED`, `UNDER_REVIEW`, `REJECTED`), `filing_date`, `resolution_date`.

### 4.4 `fact_parts`
- **Grain:** One row per line-item part consumed on a service order.
- **Primary Key:** `parts_usage_key` (BIGSERIAL).
- **Foreign Keys:** `service_key`, `component_key`.
- **Financials:** `quantity`, `unit_price`, `total_parts_cost`.

---

## 5. Machine Learning Schema (`ml_inference`)

The `ml_inference` schema houses predictions and audit trails generated by production ML models and the rule engine:

| Table Name | Primary Key | Key Attributes | Purpose |
|---|---|---|---|
| `vehicle_failure_predictions` | `(vehicle_id, cutoff_date)` | `risk_score`, `risk_tier`, `top_features`, `scored_at` | 14-day vehicle failure risk probability and tiering |
| `sensor_anomaly_predictions` | `prediction_id` (BIGSERIAL) | `anomaly_score`, `is_anomaly`, `decision_threshold`, `algorithmic_latency_ms` | Real-time sensor anomaly scoring history |
| `dealer_demand_forecasts` | `(dealer_id, forecast_date)` | `predicted_visits`, `lower_bound_80`, `upper_bound_80`, `horizon_days` | 14-day service bay capacity demand projections |
| `warranty_outlier_predictions` | `claim_id` | `claim_amount`, `outlier_score`, `percentile_rank`, `audit_recommended` | Forensic warranty claim outlier audit prioritization |
| `action_logs` | `action_id` (UUID) | `rule_id`, `entity_type`, `entity_id`, `trigger_value`, `threshold_applied`, `delivery_status`, `payload` | Immutable audit trail of automated actions dispatched |

---

## 6. Schema Governance & Role Invariants

1. **Schema Partitioning:** Analytical tables reside in `autocare_dw`. Machine learning artifacts and audit logs reside in `ml_inference`. Staging raw tables reside in `staging`.
2. **Role Immutability:**
   - `autocare_backend`: Holds `SELECT` on all 10 `autocare_dw` tables and 5 `ml_inference` tables. Holds zero DDL or write permissions.
   - `autocare_worker`: Holds `SELECT` on `ml_inference` predictions and `INSERT` exclusively on `ml_inference.action_logs`. Holds zero delete/update permissions.
   - Superuser `postgres`: Exclusively holds DDL and table management privileges.
