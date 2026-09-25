# AutoCare Intelligence — Enterprise Data Dictionary

**Authoritative Reference:** `AutoCare_Intelligence.pdf` (Section 4 & Section 7)  
**Version:** 1.0.0  
**Last Updated:** September 2026

---

## 1. Overview & Governance

This document establishes the official data dictionary and schema contract for the AutoCare Intelligence platform. Every incoming event, batch table, and analytical mart must adhere to the data types, integrity rules, and physical bounds defined herein.

---

## 2. Source Datasets (Raw / Ingestion Layer)

### 2.1. Vehicles (`raw_vehicles`)
*Grain: 1 row per physical vehicle registered in the connected fleet.*

| Column Name | Data Type | Nullable | Primary Key | Foreign Key | Description & Business Rules | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `vehicle_id` | `VARCHAR(32)` | No | PK | - | Unique fleet vehicle identifier (e.g. `VH-10001`). | `VH-10024` |
| `model` | `VARCHAR(64)` | No | - | `dim_model.model_name` | Commercial vehicle model name (e.g., Apex, Titan, Pulse). | `Apex` |
| `variant` | `VARCHAR(32)` | No | - | - | Vehicle trim/powertrain variant (e.g., EV, Turbo, Hybrid, Base). | `Turbo-GT` |
| `manufacture_date` | `DATE` | No | - | - | Factory manufacturing date. Must be $\le \text{CURRENT\_DATE}$. | `2023-04-15` |
| `dealer_id` | `VARCHAR(32)` | No | - | `dim_dealer.dealer_id` | Selling / primary servicing dealership identifier. | `DLR-004` |
| `_ingested_at` | `TIMESTAMP` | No | - | - | Audit timestamp when record entered the Bronze layer. | `2026-09-25 10:00:00` |

---

### 2.2. Telemetry (`raw_telemetry`)
*Grain: 1 row per vehicle per periodic IoT sensor transmission instant.*

| Column Name | Data Type | Nullable | Primary Key | Foreign Key | Description & Business Rules | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `vehicle_id` | `VARCHAR(32)` | No | Composite PK | `raw_vehicles.vehicle_id` | Identifier of vehicle transmitting CAN bus signals. | `VH-10024` |
| `timestamp` | `TIMESTAMP` | No | Composite PK | - | UTC timestamp when sensor reading was captured at the edge. | `2026-09-25 14:32:05` |
| `rpm` | `INTEGER` | No | - | - | Engine revolutions per minute. Valid Range: `[0, 9000]`. | `2450` |
| `temperature` | `NUMERIC(5,2)` | No | - | - | Engine coolant / battery pack temperature (°C). Range: `[-40.0, 160.0]`. | `91.40` |
| `battery` | `NUMERIC(4,2)` | No | - | - | Low-voltage auxiliary / 12V battery terminal voltage (V). Range: `[9.0, 16.0]`. | `12.60` |
| `vibration` | `NUMERIC(6,3)` | No | - | - | 3-axis accelerometer RMS vibration index (mm/s). Range: `[0.0, 15.0]`. | `1.420` |
| `_ingested_at` | `TIMESTAMP` | No | - | - | Audit timestamp when message was committed to Kafka / Bronze. | `2026-09-25 14:32:06` |

---

### 2.3. Diagnostics (`raw_diagnostics`)
*Grain: 1 row per Diagnostic Trouble Code (DTC) event logged by an onboard Electronic Control Unit (ECU).*

| Column Name | Data Type | Nullable | Primary Key | Foreign Key | Description & Business Rules | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `vehicle_id` | `VARCHAR(32)` | No | Composite PK | `raw_vehicles.vehicle_id` | Vehicle logging the diagnostic fault. | `VH-10024` |
| `timestamp` | `TIMESTAMP` | No | Composite PK | - | UTC timestamp when trouble code was triggered. | `2026-09-25 14:30:00` |
| `code` | `VARCHAR(16)` | No | Composite PK | - | Standard OBD-II / UDS diagnostic trouble code. Must match regex `^[PCBU][0-9]{4}$`. | `P0217` |
| `component` | `VARCHAR(64)` | No | - | `dim_component.component_id` | Affected vehicular subsystem or component. | `Cooling System` |
| `severity` | `VARCHAR(16)` | No | - | - | Severity tier. Allowed values: `['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']`. | `CRITICAL` |
| `_ingested_at` | `TIMESTAMP` | No | - | - | Audit ingestion timestamp. | `2026-09-25 14:30:02` |

---

### 2.4. Service (`raw_service`)
*Grain: 1 row per completed dealership workshop service repair invoice.*

| Column Name | Data Type | Nullable | Primary Key | Foreign Key | Description & Business Rules | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `service_id` | `VARCHAR(32)` | No | PK | - | Unique workshop service order identifier (e.g. `SRV-50012`). | `SRV-50012` |
| `vehicle_id` | `VARCHAR(32)` | No | - | `raw_vehicles.vehicle_id` | Serviced vehicle identifier. | `VH-10024` |
| `dealer_id` | `VARCHAR(32)` | No | - | `dim_dealer.dealer_id` | Dealership facility that performed the maintenance. | `DLR-004` |
| `visit_date` | `DATE` | No | - | - | Date repair was completed. Must be $\ge \text{manufacture\_date}$. | `2026-05-12` |
| `issue` | `TEXT` | No | - | - | Diagnostic complaint, maintenance description, or repair description. | `Replaced water pump and coolant flush` |
| `cost` | `NUMERIC(10,2)` | No | - | - | Total invoice amount charged (parts + labor). Must be $\ge 0.00$. | `485.50` |
| `_ingested_at` | `TIMESTAMP` | No | - | - | Audit ingestion timestamp. | `2026-09-25 01:00:00` |

---

### 2.5. Warranty (`raw_warranty`)
*Grain: 1 row per warranty reimbursement claim submitted by a dealership to the OEM.*

| Column Name | Data Type | Nullable | Primary Key | Foreign Key | Description & Business Rules | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `claim_id` | `VARCHAR(32)` | No | PK | - | Unique OEM warranty claim identifier (e.g. `CLM-90041`). | `CLM-90041` |
| `vehicle_id` | `VARCHAR(32)` | No | - | `raw_vehicles.vehicle_id` | Vehicle under warranty for which claim was filed. | `VH-10024` |
| `component` | `VARCHAR(64)` | No | - | `dim_component.component_id` | Defective part or component covered by manufacturer warranty. | `Water Pump` |
| `claim_date` | `DATE` | No | - | - | Date warranty claim was filed. Must be $\le \text{CURRENT\_DATE}$. | `2026-05-14` |
| `amount` | `NUMERIC(10,2)` | No | - | - | Reimbursed financial amount. Must be $> 0.00$. | `380.00` |
| `_ingested_at` | `TIMESTAMP` | No | - | - | Audit ingestion timestamp. | `2026-09-25 01:00:00` |

---

### 2.6. Parts (`raw_parts`)
*Grain: 1 row per component SKU per dealership inventory snapshot.*

| Column Name | Data Type | Nullable | Primary Key | Foreign Key | Description & Business Rules | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `part_id` | `VARCHAR(32)` | No | Composite PK | `dim_component.component_id` | Spare-part stock keeping unit (SKU) identifier. | `PRT-WP-01` |
| `dealer_id` | `VARCHAR(32)` | No | Composite PK | `dim_dealer.dealer_id` | Dealership stocking the part. | `DLR-004` |
| `stock` | `INTEGER` | No | - | - | On-hand physical inventory quantity. Must be $\ge 0$. | `4` |
| `lead_time` | `INTEGER` | No | - | - | Supplier replenishment lead time (calendar days). Must be $\ge 1$. | `7` |
| `snapshot_date`| `DATE` | No | Composite PK | - | Date inventory level was recorded. | `2026-09-25` |
| `_ingested_at` | `TIMESTAMP` | No | - | - | Audit ingestion timestamp. | `2026-09-25 01:00:00` |

---

## 3. Dimensional Model (Warehouse Marts)

### Dimensions
1. **`dim_vehicle`:** Surrogate `vehicle_key (INT, PK)`, `vehicle_id`, `model_key`, `customer_key`, `dealer_key`, `manufacture_date`, `status`.
2. **`dim_customer`:** Surrogate `customer_key (INT, PK)`, `customer_id`, `customer_name (Masked)`, `segment`, `region`.
3. **`dim_dealer`:** Surrogate `dealer_key (INT, PK)`, `dealer_id`, `dealer_name`, `region`, `city`, `bay_count`.
4. **`dim_model`:** Surrogate `model_key (INT, PK)`, `model_name`, `variant`, `engine_type`, `model_year`.
5. **`dim_component`:** Surrogate `component_key (INT, PK)`, `component_id`, `component_name`, `category`, `expected_lifespan_km`.
6. **`dim_date`:** Surrogate `date_key (INT, PK, e.g. 20260925)`, `full_date`, `year`, `quarter`, `month`, `month_name`, `day_of_month`, `day_of_week`.

### Fact Tables
1. **`fact_telemetry`:** `telemetry_id (BIGINT, PK)`, `vehicle_key (FK)`, `date_key (FK)`, `event_timestamp`, `rpm`, `temperature`, `battery_voltage`, `vibration`, `anomaly_flag`.
2. **`fact_service`:** `service_key (INT, PK)`, `service_id (UK)`, `vehicle_key (FK)`, `dealer_key (FK)`, `date_key (FK)`, `visit_date`, `issue_code`, `labor_cost`, `parts_cost`, `total_cost`.
3. **`fact_warranty`:** `warranty_key (INT, PK)`, `claim_id (UK)`, `vehicle_key (FK)`, `component_key (FK)`, `date_key (FK)`, `claim_date`, `claim_amount`, `status`.
4. **`fact_parts`:** `parts_inventory_key (INT, PK)`, `dealer_key (FK)`, `component_key (FK)`, `date_key (FK)`, `stock_level`, `lead_time_days`, `reorder_point`, `is_stockout_risk`.
