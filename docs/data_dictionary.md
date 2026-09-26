# AutoCare Intelligence — Enterprise Data Dictionary

**Authoritative Reference:** `AutoCare_Intelligence.pdf` (Section 4 & Section 7)  
**Document Status:** Governed Data Contract & Mapping Specification  
**Version:** 1.1.0  
**Last Updated:** September 2026

---

## 1. Overview & Governance

This document establishes the official data dictionary and schema contract for the AutoCare Intelligence platform. Every incoming event, batch table, and analytical mart must adhere to the data types, integrity rules, and physical bounds defined herein.

To preserve strict compliance with the authoritative assignment PDF:
- **PDF REQUIRED FIELDS:** Fields explicitly mandated by Section 4 of `AutoCare_Intelligence.pdf`.
- **PROPOSED AUDIT / SYSTEM FIELDS:** Technical metadata fields (such as `_ingested_at`) added for enterprise medallion data governance.
- **PROPOSED SUPPORTING MAPPINGS:** Entities (such as `dim_customer` and `dim_part` mapping) introduced to satisfy Section 7's dimensional requirements without corrupting raw source contracts.

---

## 2. Source Datasets (Raw / Ingestion Layer)

### 2.1. Vehicles (`raw_vehicles`)
*Grain: 1 row per physical vehicle registered in the connected fleet.*

| Column Name | Status | Data Type | Nullable | Primary Key | Foreign Key | Description & Business Rules | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `vehicle_id` | **PDF REQUIRED** | `VARCHAR(32)` | No | PK | - | Unique fleet vehicle identifier (e.g. `VH-10001`). | `VH-10024` |
| `model` | **PDF REQUIRED** | `VARCHAR(64)` | No | - | `dim_model.model_name` | Commercial vehicle model name (e.g., Apex, Titan, Pulse). | `Apex` |
| `variant` | **PDF REQUIRED** | `VARCHAR(32)` | No | - | - | Vehicle trim/powertrain variant (e.g., EV, Turbo, Hybrid, Base). | `Turbo-GT` |
| `manufacture_date` | **PDF REQUIRED** | `DATE` | No | - | - | Factory manufacturing date. Must be $\le \text{CURRENT\_DATE}$. | `2023-04-15` |
| `dealer_id` | **PDF REQUIRED** | `VARCHAR(32)` | No | - | `dim_dealer.dealer_id` | Selling / primary servicing dealership identifier. | `DLR-004` |
| `_ingested_at` | PROPOSED AUDIT | `TIMESTAMP` | No | - | - | Ingestion timestamp when record entered the Bronze layer. | `2026-09-25 10:00:00` |

*Note on Customer Relationship:* PDF Section 4 does **not** include `customer_id` in the Vehicles source. To satisfy the PDF Section 7 requirement for a `customer` dimension, customer association is maintained via a proposed supporting registration mapping (`vehicle_customer_map` or `dim_vehicle.customer_key`).

---

### 2.2. Telemetry (`raw_telemetry`)
*Grain: 1 row per vehicle per periodic IoT sensor transmission instant.*

| Column Name | Status | Data Type | Nullable | Primary Key | Foreign Key | Description & Business Rules | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `vehicle_id` | **PDF REQUIRED** | `VARCHAR(32)` | No | Composite PK | `raw_vehicles.vehicle_id` | Identifier of vehicle transmitting CAN bus signals. | `VH-10024` |
| `timestamp` | **PDF REQUIRED** | `TIMESTAMP` | No | Composite PK | - | UTC timestamp when sensor reading was captured at the edge. | `2026-09-25 14:32:05` |
| `rpm` | **PDF REQUIRED** | `INTEGER` | No | - | - | Engine revolutions per minute. Physical Range: `[0, 9000]`. | `2450` |
| `temperature` | **PDF REQUIRED** | `NUMERIC(5,2)` | No | - | - | Engine coolant / battery pack temperature (°C). Range: `[-40.0, 160.0]`. | `91.40` |
| `battery` | **PDF REQUIRED** | `NUMERIC(4,2)` | No | - | - | Low-voltage auxiliary / 12V battery terminal voltage (V). Range: `[9.0, 16.0]`. | `12.60` |
| `vibration` | **PDF REQUIRED** | `NUMERIC(6,3)` | No | - | - | 3-axis accelerometer RMS vibration index (mm/s). Range: `[0.0, 15.0]`. | `1.420` |
| `_ingested_at` | PROPOSED AUDIT | `TIMESTAMP` | No | - | - | Audit timestamp when message was committed to Kafka / Bronze. | `2026-09-25 14:32:06` |

---

### 2.3. Diagnostics (`raw_diagnostics`)
*Grain: 1 row per Diagnostic Trouble Code (DTC) event logged by an onboard Electronic Control Unit (ECU).*

| Column Name | Status | Data Type | Nullable | Primary Key | Foreign Key | Description & Business Rules | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `vehicle_id` | **PDF REQUIRED** | `VARCHAR(32)` | No | Composite PK | `raw_vehicles.vehicle_id` | Vehicle logging the diagnostic fault. | `VH-10024` |
| `timestamp` | **PDF REQUIRED** | `TIMESTAMP` | No | Composite PK | - | UTC timestamp when trouble code was triggered. | `2026-09-25 14:30:00` |
| `code` | **PDF REQUIRED** | `VARCHAR(16)` | No | Composite PK | - | Standard OBD-II / UDS diagnostic trouble code. Regex `^[PCBU][0-9]{4}$`. | `P0217` |
| `component` | **PDF REQUIRED** | `VARCHAR(64)` | No | - | `dim_component.component_name` | Affected vehicular subsystem or component name. | `Cooling System` |
| `severity` | **PDF REQUIRED** | `VARCHAR(16)` | No | - | - | Severity tier. Allowed values: `['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']`. | `CRITICAL` |
| `_ingested_at` | PROPOSED AUDIT | `TIMESTAMP` | No | - | - | Audit ingestion timestamp. | `2026-09-25 14:30:02` |

---

### 2.4. Service (`raw_service`)
*Grain: 1 row per completed dealership workshop service repair invoice.*

| Column Name | Status | Data Type | Nullable | Primary Key | Foreign Key | Description & Business Rules | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `service_id` | **PDF REQUIRED** | `VARCHAR(32)` | No | PK | - | Unique workshop service order identifier (e.g. `SRV-50012`). | `SRV-50012` |
| `vehicle_id` | **PDF REQUIRED** | `VARCHAR(32)` | No | - | `raw_vehicles.vehicle_id` | Serviced vehicle identifier. | `VH-10024` |
| `dealer_id` | **PDF REQUIRED** | `VARCHAR(32)` | No | - | `dim_dealer.dealer_id` | Dealership facility that performed the maintenance. | `DLR-004` |
| `visit_date` | **PDF REQUIRED** | `DATE` | No | - | - | Date repair was completed. Must be $\ge \text{manufacture\_date}$. | `2026-05-12` |
| `issue` | **PDF REQUIRED** | `TEXT` | No | - | - | Diagnostic complaint, maintenance description, or repair description. | `Replaced water pump and coolant flush` |
| `cost` | **PDF REQUIRED** | `NUMERIC(10,2)` | No | - | - | Total invoice amount charged (parts + labor). Must be $\ge 0.00$. | `485.50` |
| `_ingested_at` | PROPOSED AUDIT | `TIMESTAMP` | No | - | - | Audit ingestion timestamp. | `2026-09-25 01:00:00` |

---

### 2.5. Warranty (`raw_warranty`)
*Grain: 1 row per warranty reimbursement claim submitted by a dealership to the OEM.*

| Column Name | Status | Data Type | Nullable | Primary Key | Foreign Key | Description & Business Rules | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `claim_id` | **PDF REQUIRED** | `VARCHAR(32)` | No | PK | - | Unique OEM warranty claim identifier (e.g. `CLM-90041`). | `CLM-90041` |
| `vehicle_id` | **PDF REQUIRED** | `VARCHAR(32)` | No | - | `raw_vehicles.vehicle_id` | Vehicle under warranty for which claim was filed. | `VH-10024` |
| `component` | **PDF REQUIRED** | `VARCHAR(64)` | No | - | `dim_component.component_name` | Defective part or component covered by manufacturer warranty. | `Water Pump & Thermostat` |
| `claim_date` | **PDF REQUIRED** | `DATE` | No | - | - | Date warranty claim was filed. Must be $\le \text{CURRENT\_DATE}$. | `2026-05-14` |
| `amount` | **PDF REQUIRED** | `NUMERIC(10,2)` | No | - | - | Reimbursed financial amount. Must be $> 0.00$. | `380.00` |
| `_ingested_at` | PROPOSED AUDIT | `TIMESTAMP` | No | - | - | Audit ingestion timestamp. | `2026-09-25 01:00:00` |

---

### 2.6. Parts (`raw_parts`)
*Grain: 1 row per spare-part SKU per dealership inventory snapshot.*

| Column Name | Status | Data Type | Nullable | Primary Key | Foreign Key | Description & Business Rules | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `part_id` | **PDF REQUIRED** | `VARCHAR(32)` | No | Composite PK | `dim_part.part_id` | Spare-part stock keeping unit (SKU) identifier. | `PRT-CLG-02` |
| `dealer_id` | **PDF REQUIRED** | `VARCHAR(32)` | No | Composite PK | `dim_dealer.dealer_id` | Dealership stocking the part. | `DLR-004` |
| `stock` | **PDF REQUIRED** | `INTEGER` | No | - | - | On-hand physical inventory quantity. Must be $\ge 0$. | `4` |
| `lead_time` | **PDF REQUIRED** | `INTEGER` | No | - | - | Supplier replenishment lead time (calendar days). Must be $\ge 1$. | `5` |
| `_ingested_at` | PROPOSED AUDIT | `TIMESTAMP` | No | - | - | Audit ingestion timestamp. | `2026-09-25 01:00:00` |

---

## 3. Entity Relationships & Mapping Strategy

### 3.1. `part_id` vs. `component_id` Mapping Strategy
- **Identified Gap in Raw Sources:** The PDF specifies `part_id` in Parts, but `component` (string name/subsystem) in Warranty and Diagnostics, while Section 7 mandates a `component` dimension.
- **Architectural Resolution:**
  - `raw_parts` retains `part_id` exactly as required by the PDF.
  - A proposed supporting entity `dim_part` (Part Catalog) maps each `part_id` to its corresponding `component_key` in `dim_component`.
  - In the warehouse star schema:
    $$\text{raw\_parts.part\_id} \longrightarrow \text{dim\_part.part\_id} \longrightarrow \text{dim\_component.component\_key} \longleftarrow \text{fact\_warranty.component\_key}$$
  - This avoids conflating `part_id` with `component_id` while maintaining 100% fidelity to both Section 4 and Section 7.

### 3.2. Customer Relationship Strategy
- **Identified Gap in Raw Sources:** The PDF Vehicles source contains `vehicle_id, model, variant, manufacture_date, dealer_id`. It does **not** contain `customer_id`. However, Section 7 mandates `customer` dimension.
- **Architectural Resolution:**
  - `customers.csv` and `dim_customer` are documented as **PROPOSED SUPPORTING MAPPINGS**.
  - A registration mapping (`vehicle_customer_map` or surrogate `customer_key` populated during dimensional staging) links `vehicle_key` to `customer_key`, reflecting automotive OEM warranty title registration.

---

## 4. Proposed Initial Thresholds (For Review & Calibration)

The following operational thresholds are **PROPOSED INITIAL THRESHOLDS** for prototype calibration and are **not** hard requirements of the assignment PDF:

| Domain / Engine | Metric / Indicator | Proposed Initial Threshold | Business Rationale |
| :--- | :--- | :--- | :--- |
| **Decision Engine (Rule 1)** | Predictive Failure Risk Score | $\ge 0.70$ (PROPOSED INITIAL THRESHOLD) | Calibrated to prioritize high-confidence proactive maintenance without overwhelming dealer service bays. |
| **Decision Engine (Rule 2)** | Warranty Spike Outlier | $> 2.5\sigma$ over baseline (PROPOSED INITIAL THRESHOLD) | Statistical fence to flag manufacturing lot defect clusters. |
| **Decision Engine (Rule 3)** | Parts Shortage | $\text{Stock} \le \text{Lead Time} \times \text{Daily Rate}$ (PROPOSED INITIAL THRESHOLD) | Standard inventory reorder point formula. |
| **Sensor Anomaly Detection** | Multivariate Anomaly Percentile | $98.5\text{th}$ percentile (PROPOSED INITIAL THRESHOLD) | Unsupervised Isolation Forest boundary for severe CAN bus outliers. |
| **Model Evaluation** | Failure Risk Classifier Target AUC | $\text{AUC} \ge 0.80$ (PROPOSED INITIAL THRESHOLD) | Benchmark for baseline predictive quality. |
| **Demand Forecasting** | Service Forecasting Target Error | $\text{MAPE} \le 12\%$ (PROPOSED INITIAL THRESHOLD) | Benchmark for workshop capacity planning. |

---

## 5. Traceability to Mandatory Deliverables

In accordance with Section 17 of `AutoCare_Intelligence.pdf`, the project deliverables are:
- **18 Mandatory Deliverables:**
  1. GitHub repository
  2. Architecture diagram
  3. ERD / star schema
  4. Data dictionary (this document)
  5. SQL scripts
  6. dbt project
  7. Airflow workflows
  8. Kafka streaming implementation
  9. Data-quality tests
  10. ML/forecasting/risk module
  11. Automation/notification module
  12. FastAPI backend
  13. React/Next.js frontend
  14. Docker configuration
  15. CI/CD workflow
  16. Cloud deployment
  17. Test cases
  18. Final presentation
- **1 Recommended Deliverable:**
  19. Demo video
