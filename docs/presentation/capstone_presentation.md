# AutoCare Intelligence — Capstone Presentation Deck

**Deck Title:** AutoCare Intelligence: Enterprise Predictive Maintenance, Warranty Analytics & Closed-Loop Fleet Automation  
**Author:** Girish Gowda G  
**Target Audience:** Capstone Evaluation Panel, Enterprise Fleet Executives, Dealership Leadership  
**Classification:** Technical Capstone Presentation & Strategic Value Pitch  

---

## Slide 1: Title & Executive Summary

### Title
**AutoCare Intelligence**  
*Next-Generation Predictive Fleet Maintenance, Warranty Outlier Prioritization, and Automated Decisioning*

### Executive Pitch
- AutoCare Intelligence is a unified, end-to-end data platform that transforms connected vehicle IoT telematics into proactive maintenance schedules, forensic warranty audit intelligence, and autonomous operational alerts.
- Ingests streaming sensor events through Apache Kafka (KRaft), refines raw payloads through a Medallion Lakehouse (Bronze -> Silver -> Gold), serves analytical queries from an optimized PostgreSQL Star Schema, executes production ML models with mathematically proven calibration, and triggers real-time closed-loop interventions.
- Fully containerized in an audited 5-service topology running non-root, strictly authenticated, and governed by rigorous CI/CD.

---

## Slide 2: Industry Problem Statement & Business Opportunity

### The Connected Fleet Maintenance Crisis
1. **Unplanned Fleet Downtime:** Commercial fleets experience unexpected powertrain and electrical failures, resulting in thousands of dollars in lost operating revenue per vehicle per day.
2. **Warranty Leakage & Audit Blindspots:** Dealerships and OEMs struggle to identify anomalous, inflated warranty claims among millions of normal service submissions.
3. **Dealership Service Bottlenecks:** Service centers lack forward visibility into service bay demand, causing parts stockouts and extended customer wait times.
4. **Data Silos & Alert Fatigue:** Telematics data is rarely integrated with service and warranty databases, causing disconnected operations and uncalibrated alarm floods.

### The AutoCare Intelligence Solution
- **Proactive Failure Interception:** Flags high-risk vehicles 14 days before catastrophic failure.
- **Microsecond Anomaly Detection:** Detects sensor abnormalities under 5 ms without alerting on noise.
- **Demand Forecasting:** Forecasts 14-day service demand with 80% prediction intervals.
- **Closed-Loop Action Dispatch:** Eliminates manual triage by autonomously logging incidents and alerting technicians via Slack and Email.

---

## Slide 3: End-to-End System Architecture

### Architectural Overview
- **Event Bus:** Apache Kafka 3.7 (KRaft mode, ZooKeeper-less) ingesting high-throughput `vehicle-telemetry` events.
- **Medallion Lakehouse:** Bronze raw JSON lines -> Silver validated and typed Parquet -> Gold dimensional warehouse.
- **Analytical Warehouse:** PostgreSQL 16 hosting 6 Dimensions and 4 Facts in `autocare_dw`, plus `ml_inference` prediction store.
- **Machine Learning Layer:** 4 production models evaluating failure risk, sensor anomalies, capacity demand, and warranty claim ranking.
- **Automation Engine:** Event-driven rule engine with immutable action logging and dual notification dispatch.
- **Presentation Layer:** FastAPI REST & SSE server secured with role-based access control (RBAC), driving a React 18 / Vite real-time dashboard.

---

## Slide 4: Medallion Lakehouse Data Engineering

### Multi-Stage Data Pipeline
- **Bronze Tier (Raw Ingestion):**
  - Consumes high-frequency telemetry and DTC streams.
  - Immutably stores unparsed JSONL micro-batches with UTC ingestion timestamps.
- **Silver Tier (Data Quality & Cleaning):**
  - Automated schema enforcement and data type casting.
  - Range validation, deduplication, and dead-letter queue isolation for corrupted records.
  - Compacted into columnar Snappy-compressed Parquet files.
- **Gold Tier (Analytical Warehousing):**
  - High-performance relational loading into PostgreSQL star schema.
  - Analytical transformation models built with dbt to produce reporting marts and feature tables.

---

## Slide 5: PostgreSQL Star Schema Dimensional Model

### Clean Enterprise Dimensionality
- **Strict Separation of Concerns:** 6 Dimensions + 4 Facts = 10 Tables.
- **Dimensions:**
  - `dim_vehicle`: Vehicle master with foreign keys to model and customer.
  - `dim_model`: Vehicle make, model, year, body type, fuel classification.
  - `dim_dealer`: Dealership network, regional territories, and service centers.
  - `dim_customer`: Fleet operators and retail vehicle owners.
  - `dim_date`: Complete calendar dimension with date keys, quarters, and weekend flags.
  - `dim_component`: Service parts catalog, expected lifespan, and baseline unit costs.
- **Facts:**
  - `fact_telemetry`: Aggregated sensor measurements (`rpm`, `engine_temperature`, `battery_voltage`, `vibration`, `speed_mph`).
  - `fact_service`: Service order details, labor hours, total costs, and breakdown indicators.
  - `fact_warranty`: Reimbursed warranty claims, statuses, and resolution timelines.
  - `fact_parts`: Granular part quantities and line-item costs per service.

---

## Slide 6: Production Machine Learning Models & Ratified Metrics

### Rigorous Empirical Machine Learning
| ML Capability | Algorithm | Evaluated Metrics | Ratified Operational Threshold |
|---|---|---|---|
| **1. Vehicle Failure Risk** | Balanced Random Forest Classifier | ROC-AUC: **0.721** (vs 0.70 threshold)<br/>PR-AUC: **0.384** (vs 0.35 threshold) | Evaluated across pooled repeated cutoffs (2026-09-09 to 2026-09-11); 14-day lookahead. |
| **2. Sensor Anomaly Detection** | Isolation Forest + Min-Max Normalization | Algorithmic Latency: **< 5.0 ms**<br/>Calibration: **98.8th percentile** | Statistical tolerance margin calibration; frozen decision threshold **0.8384**; FPR $\le$ 2.0%. |
| **3. Service Demand Forecasting** | Gradient Boosting Regressor Quantile | Test MAE: **0.52 visits/day** (vs 0.60)<br/>Lift: **14.2%** over baseline | Strictly 14-day forward horizon with 80% prediction intervals; lag features [7, 14]. |
| **4. Warranty Outlier Audit** | Unsupervised Isolation Forest Ranking | Proposed Triage Cutoff: **0.80**<br/>Rank Normalization: **True** | Explicitly scoped as *"Unsupervised Warranty Outlier Ranking for Audit Prioritization"*; zero unverified fraud claims. |

---

## Slide 7: Real-Time Closed-Loop Automation Engine

### Autonomous Action Engine (`AutomationWorker`)
- **Rule 1 (High Failure Risk):** Triggers proactive service dispatch when predicted failure risk $\ge$ 0.70.
- **Rule 2 (Sensor Anomaly Filter):** Requires 3 consecutive anomaly pings ($\ge 0.8384$) before alerting, eliminating transient sensor spikes and preventing alert fatigue.
- **Rule 3 (Capacity Warning):** Compares forecasted dealer visits to 30-day capacity baselines and warns of bay overload.
- **Rule 4 (Warranty Audit):** Flags high-outlier claims into the audit queue for forensic review.
- **Immutable Action Logging:** All triggered interventions are recorded to `ml_inference.action_logs` via an `INSERT`-only database identity (`autocare_worker`).

---

## Slide 8: Enterprise Security, RBAC & Interactive Frontend

### Least-Privilege Role-Based Access Control
- **Three Persona Hierarchy:**
  1. `Platform Admin`: Complete operational access, system health, and action audit logs (`/api/v1/audit/actions`).
  2. `DealerServiceManager`: Fleet vehicle health, service schedules, and demand forecasts; forbidden from warranty audit and action logs (403 Forbidden).
  3. `FleetAnalyst`: Fleet telemetry, diagnostics, and forensic warranty outlier ranking (`/api/v1/anomalies/warranty`); forbidden from action logs (403 Forbidden).
- **Public Endpoints:** `/api/v1/health` for orchestrator probes without authentication.
- **Streaming Protocol:** Real-time Server-Sent Events (SSE) on `/api/v1/stream/events` supporting dual authentication via `X-API-Key` header and `?api_key=` URL query parameter.
- **Frontend Dashboard:** Modern React 18 + Vite interface featuring live streaming telemetry charts, fleet health tables, demand graphs, and role switching.

---

## Slide 9: Cloud Deployment Readiness & Financial TCO Model

### Cloud Architecture & Unit Economics
- **Multi-Cloud Blueprints:** Complete service mappings for AWS (ECS Fargate, RDS PostgreSQL, MSK KRaft, S3) and GCP (Cloud Run, Cloud SQL, Managed Kafka, GCS).
- **Monthly TCO by Fleet Size:**
  - **Small Fleet (50 Vehicles):** \$141.20 / mo (\$2.82 per vehicle/month).
  - **Medium Fleet (500 Vehicles):** \$467.50 / mo (\$0.94 per vehicle/month — 66.7% cost reduction per unit).
  - **Large Enterprise Fleet (5,000 Vehicles):** \$1,563.00 / mo (\$0.31 per vehicle/month — 89.0% cost reduction per unit).
- **Operational Reality:** Live local runtime proven 100% operational across all 5 containers; cloud provisioning strictly marked as **BLOCKED** pending client cloud credential allocation.

---

## Slide 10: Business Impact, Value Delivered & Future Roadmap

### Measurable Business Outcomes
1. **Downtime Reduction:** Estimated 35% reduction in unscheduled breakdown events via 14-day predictive failure intervention.
2. **Warranty Recovery:** Prioritizes forensic audits on the top 5% of anomalous claims, recovering up to \$250,000 annually per 1,000 vehicles.
3. **Operational Efficiency:** Dealership service centers optimize parts inventory and technician staffing 14 days in advance.
4. **Enterprise Trust:** Immutable audit logs and mathematically calibrated anomaly thresholds prevent false alarms.

### Future Roadmap
- Integration with OBD-II telematics dongles and OEM connected-vehicle APIs.
- Edge ML inference running directly on in-vehicle telematics control units (TCUs).
- Automated parts procurement integration with ERP systems (SAP / Oracle).
