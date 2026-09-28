# AutoCare Intelligence — End-to-End System Architecture

**Document Version:** 1.0.0  
**Phase:** 6 — Productionization & Capstone Delivery  
**Classification:** Technical System Specification & Architectural Reference  

---

## 1. Executive Summary

AutoCare Intelligence is an enterprise-grade predictive maintenance, warranty analytics, and automated decisioning platform for connected vehicle fleets. The platform continuously ingests high-frequency IoT sensor telemetry, diagnostic trouble codes (DTCs), service records, and warranty claims; processes them through a multi-tier Medallion Lakehouse architecture; models failure dynamics via production machine learning; and enforces real-time closed-loop automated interventions with immutable audit logging.

This document describes the high-level architecture, container topology, data flow, dual-path streaming inference, security controls, and networking contracts across the five core platform tiers.

---

## 2. High-Level C4 Context Diagram

The following C4 Context diagram illustrates how external vehicle fleets, dealership networks, and platform operators interact with the AutoCare Intelligence platform boundary.

```mermaid
C4Context
    title System Context Diagram — AutoCare Intelligence Platform

    Person(driver, "Connected Vehicle", "Edge telematics unit streaming high-frequency sensor readings and DTCs.")
    Person(service_mgr, "Dealer Service Manager", "Reviews service demand forecasts and schedules maintenance.")
    Person(analyst, "Fleet Analyst", "Audits warranty outliers and evaluates component failure trends.")
    Person(admin, "Platform Admin", "Monitors platform health, automated action dispatch, and security logs.")

    Enterprise_Boundary(autocare_boundary, "AutoCare Intelligence Platform") {
        System(autocare_sys, "AutoCare Intelligence Core", "End-to-end data lakehouse, ML inference engine, automated rule dispatch, and REST/SSE API.")
    }

    System_Ext(slack_ext, "Enterprise Slack / Webhook", "Real-time critical anomaly and breakdown notifications.")
    System_Ext(email_ext, "SMTP / Dealership Email", "Daily high-risk triage manifests and demand schedule alerts.")

    Rel(driver, autocare_sys, "Publishes telemetry & DTC events", "Kafka KRaft / TLS (Port 9092)")
    Rel(service_mgr, autocare_sys, "Views demand forecasts & fleet status", "HTTPS / REST (Port 5173 / 8000)")
    Rel(analyst, autocare_sys, "Analyzes warranty anomalies & fleet risk", "HTTPS / REST (Port 5173 / 8000)")
    Rel(admin, autocare_sys, "Inspects action audit logs & system health", "HTTPS / REST & SSE (Port 5173 / 8000)")

    Rel(autocare_sys, slack_ext, "Dispatches critical alerts", "HTTPS / Webhook")
    Rel(autocare_sys, email_ext, "Sends triage reports", "SMTP / REST")
```

---

## 3. Container Topology & Network Architecture

The platform runs as a 5-tier orchestrated container topology governed by Docker Compose. Each container is configured with strict health checks, non-root execution, resource boundaries, and environment-provided fail-fast secrets.

```mermaid
graph TD
    subgraph Host Network ["Host Interface (0.0.0.0)"]
        P_FE["Port 3000 (Docker) / 5173 (Dev)"]
        P_BE["Port 8000 (Backend API & SSE)"]
        P_PG["Port 5432 (PostgreSQL Data Warehouse)"]
        P_KF["Port 9092 (Kafka KRaft Broker)"]
    end

    subgraph Docker Network ["autocare-net (172.28.0.0/16 Bridge)"]
        FE["autocare-frontend<br/>React 18 + Vite Production Server<br/>Port 3000 (Internal)"]
        BE["autocare-backend<br/>FastAPI + Uvicorn<br/>Port 8000 (Internal)"]
        WORKER["autocare-automation-worker<br/>Python 3.10 Daemon<br/>Continuous Supervisor Loop"]
        PG[("autocare-postgres<br/>PostgreSQL 16 Alpine<br/>Port 5432 (Internal)")]
        KF["autocare-kafka<br/>Apache Kafka 3.7 (KRaft Mode)<br/>Port 9092 (Internal)"]
    end

    P_FE --> FE
    P_BE --> BE
    P_PG --> PG
    P_KF --> KF

    FE -->|HTTP / SSE REST| BE
    BE -->|SQL queries (SELECT only)| PG
    BE -.->|Live Telemetry Fallback| KF
    WORKER -->|Consume vehicle-telemetry| KF
    WORKER -->|Batch Read / Append Logs| PG
```

### Container Specifications

| Container Name | Base Image | Role | Bound Ports | Healthcheck Mechanism |
|---|---|---|---|---|
| `autocare-postgres` | `postgres:16-alpine` | Warehouse, lakehouse staging, and ML inference store | `5432:5432` | `pg_isready -U postgres -d autocare_dw` |
| `autocare-kafka` | `apache/kafka:3.7.0` | Event bus for real-time telemetry streaming (KRaft mode) | `9092:9092` | `/opt/kafka/bin/kafka-broker-api-versions.sh` |
| `autocare-backend` | `python:3.10-slim` | FastAPI REST & SSE server with 3-tier RBAC | `8000:8000` | `curl -f http://localhost:8000/api/v1/health` |
| `autocare-frontend` | `node:20-alpine` | React 18 SPA with TailwindCSS & Recharts | `3000:3000` | `wget --spider http://127.0.0.1:3000/` |
| `autocare-automation-worker` | `python:3.10-slim` | Kafka consumer, streaming scorer, and rule evaluator | None | `pgrep -f '[a]utomation.worker'` |

---

## 4. End-to-End Multi-Tier Data Flow

The platform implements a Medallion Architecture (Bronze -> Silver -> Gold) coupled with near-real-time streaming inference:

```mermaid
flowchart LR
    subgraph Ingestion ["1. Telematics & Event Ingestion"]
        VEH["Connected Fleet<br/>50–5,000 Vehicles"]
        K_IN["Kafka KRaft Topic<br/>vehicle-telemetry"]
    end

    subgraph Lakehouse ["2. Lakehouse Storage"]
        BRONZE[("Bronze Storage<br/>Raw JSON Lines")]
        SILVER[("Silver Parquet<br/>Validated & Typed")]
    end

    subgraph Warehouse ["3. Relational Warehouse (autocare_dw)"]
        STAGING[("Staging Schema<br/>silver_*")]
        DW[("Gold Star Schema<br/>6 Dims + 4 Facts")]
        DBT["dbt Analytical Models<br/>Aggregations & Metrics"]
    end

    subgraph ML_Layer ["4. Machine Learning & Inference"]
        M1["Model 1: Failure Risk<br/>RandomForest (ROC-AUC 0.72)"]
        M2["Model 2: Sensor Anomaly<br/>IsolationForest (Calib. 98.8%)"]
        M3["Model 3: Demand Forecast<br/>GBR Quantile (14-day Horizon)"]
        M4["Model 4: Warranty Outlier<br/>Audit Prioritization Ranking"]
        INF_DB[("ml_inference Schema<br/>Predictions & Action Logs")]
    end

    subgraph Automation ["5. Automated Action Engine"]
        RULES["Rule Engine<br/>Rules 1, 2, 3, 4"]
        ACT_LOG["Action Logger<br/>Immutable INSERT"]
        NOTIF["Notification Channels<br/>Slack / Email Mock"]
    end

    subgraph Presentation ["6. API & Presentation"]
        FASTAPI["FastAPI REST & SSE<br/>Enterprise RBAC Guard"]
        REACT["React 18 Dashboard<br/>Live Visualizations"]
    end

    VEH -->|Streaming pings| K_IN
    VEH -->|Micro-batch dump| BRONZE
    BRONZE -->|Validation & cleaning| SILVER
    SILVER -->|COPY ingestion| STAGING
    STAGING -->|Star schema loading| DW
    DW -->|Transformations| DBT
    
    K_IN -->|Real-time consumption| M2
    DW -->|Batch feature extraction| M1
    DW -->|Historical demand| M3
    DW -->|Claim features| M4

    M1 & M2 & M3 & M4 --> INF_DB
    M2 -->|Real-time alerts| RULES
    INF_DB -->|Batch evaluation| RULES
    RULES --> ACT_LOG
    ACT_LOG --> INF_DB
    RULES --> NOTIF

    DW & INF_DB -->|SELECT only| FASTAPI
    FASTAPI -->|REST & SSE| REACT
```

---

## 5. Dual-Path Streaming & Batch Architecture

To balance low-latency alerting with high-throughput historical training and compaction, AutoCare Intelligence implements a dual-path pipeline:

```mermaid
flowchart TD
    KAFKA["Kafka Topic: vehicle-telemetry"]

    subgraph FastPath ["Real-Time Streaming Path (< 10 ms)"]
        C_FAST["AutomationWorker Consumer<br/>autocare-automation-group"]
        SCORER["StreamingSensorScorer<br/>Algorithmic Latency < 5 ms"]
        RULE2["Rule 2 Evaluator<br/>Consecutive Anomaly Filter"]
        SLACK_DISPATCH["Slack Notification Webhook"]
        LOG_INSERT["Action Logger<br/>INSERT into ml_inference.action_logs"]
    end

    subgraph BatchPath ["Analytical Batch & Compaction Path (Airflow / dbt)"]
        DAG_HOURLY["Hourly Bronze Ingestion DAG"]
        BRONZE_SINK["Bronze Raw Storage (JSONL)"]
        CLEANER["Silver Cleaning & Parquet Compaction"]
        SILVER_SINK["Silver Parquet Archive"]
        DW_LOAD["Gold Warehouse Ingestion (PostgreSQL)"]
        DBT_RUN["dbt Transformations & Marts"]
        BATCH_ML["Daily ML Retraining & Cutoff Scoring"]
    end

    KAFKA -->|Continuous event stream| C_FAST
    C_FAST --> SCORER
    SCORER --> RULE2
    RULE2 -->|Threshold exceeded (3x)| SLACK_DISPATCH
    RULE2 -->|Audit record| LOG_INSERT

    KAFKA -->|Micro-batch consume| DAG_HOURLY
    DAG_HOURLY --> BRONZE_SINK
    BRONZE_SINK --> CLEANER
    CLEANER --> SILVER_SINK
    SILVER_SINK --> DW_LOAD
    DW_LOAD --> DBT_RUN
    DBT_RUN --> BATCH_ML
```

---

## 6. Enterprise Security & Database RBAC Model

The platform strictly isolates privileges across operating roles and database identities:

```mermaid
graph LR
    subgraph Roles ["Application Personas"]
        R_ADM["Admin<br/>Platform Superuser"]
        R_DLR["DealerServiceManager<br/>Dealership Operations"]
        R_ANA["FleetAnalyst<br/>Fleet & Warranty Auditor"]
    end

    subgraph API_Guard ["FastAPI Security Middleware"]
        SEC["Header: X-API-Key<br/>Fallback: ?api_key= (SSE only)"]
    end

    subgraph Endpoints ["REST Endpoints"]
        EP_HLT["/api/v1/health (Public)"]
        EP_VEH["/api/v1/vehicles (All Roles)"]
        EP_SVC["/api/v1/demand/forecasts (All Roles)"]
        EP_WAR["/api/v1/anomalies/warranty (Admin, FleetAnalyst)"]
        EP_AUD["/api/v1/audit/actions (Admin Only)"]
        EP_SSE["/api/v1/stream/events (All Authenticated)"]
    end

    subgraph DB_Identities ["PostgreSQL Runtime Roles"]
        DB_BE["autocare_backend<br/>SELECT ONLY (9 tables)"]
        DB_WK["autocare_worker<br/>SELECT (4 tables)<br/>INSERT ONLY (action_logs)"]
    end

    R_ADM --> SEC
    R_DLR --> SEC
    R_ANA --> SEC

    SEC --> EP_HLT
    SEC --> EP_VEH
    SEC --> EP_SVC
    SEC --> EP_WAR
    SEC --> EP_AUD
    SEC --> EP_SSE

    EP_VEH & EP_SVC & EP_WAR & EP_AUD --> DB_BE
    WORKER --> DB_WK
```

### Immutable Security Invariants
1. **Zero Write Privileges on Backend:** `autocare_backend` cannot execute `INSERT`, `UPDATE`, `DELETE`, `TRUNCATE`, or `ALTER` anywhere in the database.
2. **Immutable Action Logs:** `autocare_worker` holds `INSERT` privilege on `ml_inference.action_logs` and zero update/delete permissions. Historical actions can never be overwritten or erased.
3. **Fail-Fast Secret Enforcement:** If `AUTOCARE_ADMIN_KEY`, `AUTOCARE_DEALER_KEY`, or `AUTOCARE_ANALYST_KEY` are unset or empty, the API server terminates immediately at startup. No default fallback keys exist.
