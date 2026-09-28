# AutoCare Intelligence

> **Connected-Vehicle & After-Sales Analytics Platform**  
> *MastersCampus Academy — Enterprise Analytics Engineering Capstone*

---

## 1. Executive Summary & Objective

**AutoCare Intelligence** is an enterprise-grade connected-vehicle and after-sales analytics platform. The application combines real-time vehicular IoT telemetry, onboard diagnostic trouble codes (DTCs), dealership service records, manufacturer warranty claims, and parts inventory supply chain data to transition automotive OEMs and dealership networks from reactive scheduled maintenance to proactive, condition-based predictive intelligence.

---

## 2. Platform Architecture

```
Source Systems (CAN Bus Simulator, ECU DTCs, DMS, Warranty Claims, Parts ERP)
       │
       ▼
Apache Kafka Event Bus (Topics: telemetry.raw, diagnostics.raw, alerts.actions)
       │
       ▼
Medallion Data Lakehouse
  ├── Bronze (Raw Immutable JSON/Parquet)
  └── Silver (Cleaned, Typed, Deduplicated Parquet)
       │
       ▼
Data Warehouse (PostgreSQL / DuckDB / BigQuery Star Schema)
  ├── Dimensions: dim_vehicle, dim_customer, dim_dealer, dim_model, dim_component, dim_date
  └── Facts: fact_telemetry, fact_service, fact_warranty, fact_parts
       │
       ▼
dbt Transformation Layer (Staging ➔ Intermediate ➔ Analytical Marts)
       │
       ├── ML & Intelligence Engine (Failure Risk, Sensor Anomaly, Demand Forecast, Warranty Outlier)
       └── Automation & Decision Engine (Domain Rules ➔ Slack/Email Webhooks & Alert Audit Log)
       │
       ▼
FastAPI Serving Layer (Async REST APIs + Server-Sent Events Live Telemetry)
       │
       ▼
Next.js 14+ Frontend Application (Vehicle 360, Fleet Health, Dealer Dashboard, Warranty, Parts, Alerts)
```

---

## 3. Repository Structure

```
AutoCareIntelligence/
├── AutoCare_Intelligence.pdf     # Authoritative Assignment Specification
├── README.md                     # Platform Overview and Developer Guide
├── requirements.txt              # Pinned Python Dependencies
├── data/
│   ├── raw/                      # Baseline Generated Datasets (CSV/Parquet)
│   ├── bronze/                   # Raw Ingested Lake Storage
│   └── silver/                   # Cleaned, Governed Lake Storage
├── data_generator/               # Synthetic Automotive Data Generation Suite
│   ├── config.py                 # Simulation Parameters and Master Lists
│   ├── vehicle_physics.py        # Correlated CAN Bus Sensor Simulation
│   └── generate_all.py           # Dataset Generator CLI
├── streaming/                    # Kafka Streaming Producers and Consumers
├── lakehouse/                    # PySpark / Lakehouse Cleansing Pipelines
├── dbt_autocare/                 # dbt-core Project (Staging, Marts, Tests)
├── backend/                      # FastAPI Application
│   └── app/
│       ├── main.py               # API Application Entrypoint
│       ├── routers/              # 12 Modular API Endpoints
│       └── schemas/              # Pydantic v2 Request/Response Models
├── frontend/                     # Next.js 14 Web Application
├── ml/                           # Predictive Maintenance & Anomaly Models
├── automation/                   # Decision Engine & Webhook Dispatchers
├── sql/                          # DDL Scripts & Dimensional Seeds
├── tests/                        # Comprehensive Pytest & Data Quality Suite
└── docs/                         # Architecture Diagrams & Data Dictionary
    ├── data_dictionary.md        # Full Column-level Data Dictionary
    └── architecture/             # System and Dimensional Diagrams
```

---

## 4. Source Data Contract (Assignment Section 4)

| Source Domain | Required Fields (PDF) | Storage Format | Ingestion Pattern |
| :--- | :--- | :--- | :--- |
| **Vehicles** | `vehicle_id`, `model`, `variant`, `manufacture_date`, `dealer_id` | Parquet / SQL | Batch Snapshot |
| **Telemetry** | `vehicle_id`, `timestamp`, `rpm`, `temperature`, `battery`, `vibration` | Kafka JSON / Parquet | Real-Time Streaming |
| **Diagnostics** | `vehicle_id`, `timestamp`, `code`, `component`, `severity` | Kafka JSON / Parquet | Real-Time / Event-Driven |
| **Service** | `service_id`, `vehicle_id`, `dealer_id`, `visit_date`, `issue`, `cost` | Parquet / SQL | Batch Daily |
| **Warranty** | `claim_id`, `vehicle_id`, `component`, `claim_date`, `amount` | Parquet / SQL | Batch Daily |
| **Parts** | `part_id`, `dealer_id`, `stock`, `lead_time` | Parquet / SQL | Periodic Snapshot |

---

## 5. Development Setup

### Prerequisites
- Python 3.10+
- Node.js v18+ and npm
- Git

### Quickstart
1. Clone the repository and navigate to the project directory:
   ```bash
   git clone <repo-url> AutoCareIntelligence
   cd AutoCareIntelligence
   ```
2. Set up and activate a Python virtual environment:
   ```bash
   python -m venv venv
   # Windows PowerShell:
   .\venv\Scripts\Activate.ps1
   # Linux/macOS:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Generate baseline synthetic data:
   ```bash
   python -m data_generator.generate_all --vehicles 100 --days 90
   ```
5. Run the test suite:
   ```bash
   pytest tests/
   ```

---

## 6. Traceability to Assignment Requirements

All requirements from `AutoCare_Intelligence.pdf` are mapped and tracked across 6 engineering phases:
- **Phase 1 (Week 1):** Requirements, Governance, Data Generation & Data Dictionary *(Current)*
- **Phase 2 (Week 2):** Lakehouse Ingestion & Warehouse Star Schema
- **Phase 3 (Week 3):** Kafka Streaming, dbt Transformations & Data Quality Tests
- **Phase 4 (Week 4):** Analytics Marts, ML Models & Decision Engine
- **Phase 5 (Week 5):** FastAPI Backend & Next.js Frontend
- **Phase 6 (Week 6):** Containerization, CI/CD, Cloud Deployment & Capstone Demo

### Official Deliverables Inventory (PDF Section 17)
The project tracks exactly **18 Mandatory Deliverables** and **1 Recommended Deliverable**:
1. GitHub repository (Mandatory)
2. Architecture diagram (Mandatory)
3. ERD / star schema (Mandatory)
4. Data dictionary (`docs/data_dictionary.md`) (Mandatory)
5. SQL scripts (Mandatory)
6. dbt project (Mandatory)
7. Airflow workflows (Mandatory)
8. Kafka streaming implementation (Mandatory)
9. Data-quality tests (Mandatory)
10. ML/forecasting/risk module (Mandatory)
11. Automation/notification module (Mandatory)
12. FastAPI backend (Mandatory)
13. React/Next.js frontend (Mandatory)
14. Docker configuration (Mandatory)
15. CI/CD workflow (Mandatory)
16. Cloud deployment (Mandatory)
17. Test cases (Mandatory)
18. Final presentation (Mandatory)
19. Demo video (Recommended)

### Architectural & Governance References
- [Enterprise Data Dictionary](docs/data_dictionary.md)
- [Architecture & Technology Decisions](docs/architecture/technology_decisions.md)
- [System Architecture & Visual C4 Specifications](docs/architecture/system_architecture.md)
- [Star Schema & Dimensional ERD Specification](docs/architecture/star_schema_erd.md)
- [Cloud Deployment Architecture & TCO Cost Model](docs/deployment/cloud_architecture_and_cost.md)
- [Capstone Presentation Deck Outline](docs/presentation/capstone_presentation.md)
- [Capstone 5-Minute Demo Walkthrough Script](docs/demo/capstone_demo_walkthrough.md)
