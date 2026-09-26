# AutoCare Intelligence — Technology Governance & Decision Record

**Authoritative Reference:** `AutoCare_Intelligence.pdf` (Section 5, 10, 12, 13, 15)  
**Document Status:** Governed Technology Decision Record (TDR)  
**Version:** 2.0.0  
**Last Updated:** September 2026

---

## 1. Architectural Governance Overview

Section 5 of `AutoCare_Intelligence.pdf` specifies the end-to-end data pipeline flow:
$$\text{Source systems} \longrightarrow \text{ingestion} \longrightarrow \text{Kafka/event bus} \longrightarrow \text{Bronze data lake} \longrightarrow \text{Silver cleansing} \longrightarrow \text{PySpark/SQL transformations} \longrightarrow \text{cloud warehouse} \longrightarrow \text{dbt analytical marts} \longrightarrow \text{analytics/ML} \longrightarrow \text{automation} \longrightarrow \text{FastAPI} \longrightarrow \text{React/Next.js} \longrightarrow \text{cloud deployment.}$$

The PDF explicitly establishes:  
*"Recommended technologies: Python, SQL, Kafka, PySpark, GCS/S3, BigQuery/Snowflake, dbt, Airflow, FastAPI, React/Next.js, Docker and GitHub Actions. Equivalent technologies are allowed."*

To eliminate governance ambiguity, this document separates:
1. **Assignment-Mandated Capabilities:** The architectural responsibilities required by the assignment specification.
2. **Selected Implementation Technologies:** The specific, concrete tools chosen to implement each capability for this project.
3. **Optional / Future Cloud Equivalents:** Viable cloud-native production hosting alternatives (which are not simultaneously required).

---

## Section A — Assignment-Mandated Capabilities

These capabilities are explicitly required by the assignment specification:

| Capability Area | PDF Reference | Assignment Mandate Summary |
| :--- | :--- | :--- |
| **Event Bus / Streaming** | PDF Section 5 & 6 | Ingest telemetry and diagnostic events through a distributed message bus with retry handling, duplicate strategy, and monitoring. |
| **Medallion Data Lake** | PDF Section 5 & 7 | Maintain immutable raw landing (Bronze) and conformed, validated, deduplicated storage (Silver). |
| **Data Transformations** | PDF Section 5 | Perform scalable data transformations and schema validation on lakehouse data. |
| **Data Warehouse** | PDF Section 5 & 7 | Star schema housing 4 Fact tables (`fact_telemetry`, `fact_service`, `fact_warranty`, `fact_parts`) and 6 Dimensions (`vehicle`, `customer`, `dealer`, `model`, `component`, `date`). |
| **Analytical Marts** | PDF Section 5 & 8 | Governed SQL models answering 6 required business questions with drill-downs, trends, segmentation, and exceptions. |
| **Workflow Orchestration** | PDF Section 13 | Scheduled pipeline execution for batch ingestion, transformations, quality checks, model refresh, and operational logging. |
| **Machine Learning** | PDF Section 9 | 4 models: Failure-risk prediction, sensor anomaly detection, service-demand forecasting, and warranty anomaly detection. |
| **Decision Automation** | PDF Section 10 | 4 domain rules; at least two automated actions must send notifications via Email, Slack, or Teams. |
| **Backend Serving API** | PDF Section 12 | REST API with 12 defined endpoints, validation, authentication, authorization, error handling, logging, and OpenAPI docs. |
| **Frontend Dashboard** | PDF Section 11 | Interactive web application with 6 core modules, Alert Center, KPI cards, charts, filters, drill-downs, and live indicator. |
| **DevOps & Containers** | PDF Section 15 | Repeatable Dockerized environments, Git with meaningful commit history, and automated CI/CD workflows. |
| **Cloud Deployment** | PDF Section 15 & 22 | Deployed application and core services accessible on a cloud platform with estimated monthly cost documentation. |

---

## Section B — Selected Implementation Technologies

These are the concrete, chosen implementation decisions for the AutoCare Intelligence platform:

| Layer | Selected Implementation Technology | Classification | Decision Rationale |
| :--- | :--- | :--- | :--- |
| **Programming Language** | **Python 3.10+ & Modern ANSI SQL** | Selected Implementation Decision | Industry standard across PySpark, ML libraries, FastAPI, and dbt. |
| **Event Streaming** | **Apache Kafka** | Selected Implementation Decision | Recommended by PDF; provides replayable distributed logs with `vehicle_id` partitioning. |
| **Lake Storage** | **Local / MinIO Parquet Lake (`data/bronze/`, `data/silver/`)** | Selected Implementation Decision | Clean file-based partitioned storage; zero cloud storage costs during early phases. |
| **Lakehouse Processing** | **PySpark & DuckDB** | Selected Implementation Decision | PySpark satisfies distributed processing; DuckDB provides fast local analytical SQL. |
| **Data Warehouse** | **PostgreSQL (Analytical Star Schema)** | **PROPOSED IMPLEMENTATION DECISION** | Full ANSI SQL star schema, native dbt-postgres adapter, zero local runtime costs. |
| **Data Modeling** | **dbt-core 1.7+** | Selected Implementation Decision | Recommended by PDF; automated testing, column-level lineage, and version-controlled SQL. |
| **Orchestration** | **Apache Airflow 2.8+** | Selected Implementation Decision | Recommended by PDF; DAG-based dependency management, automatic retries, and run logs. |
| **Machine Learning** | **scikit-learn, IsolationForest, Prophet** | Selected Implementation Decision | Robust, explainable algorithms covering classification, anomaly detection, and time series. |
| **Decision Engine** | **Python Rule Engine + Slack Incoming Webhook & SMTP** | Selected Implementation Decision | Codifies 4 rules; satisfies PDF requirement for at least 2 channels (Slack + Email). |
| **Backend API** | **FastAPI + Pydantic v2 + Uvicorn** | Selected Implementation Decision | Recommended by PDF; high-performance async I/O, automatic OpenAPI docs (`/docs`). |
| **Frontend Framework** | **Next.js 14+ (App Router) + Tailwind CSS + Recharts** | Selected Implementation Decision | Recommended by PDF; responsive enterprise UI, server components, live SSE stream updates. |
| **Containerization** | **Multi-stage Dockerfiles & Docker Compose** | Selected Implementation Decision | Recommended by PDF; guarantees identical runtime across team environments. |
| **CI/CD** | **GitHub Actions** | Selected Implementation Decision | Recommended by PDF; automated linting, pytest execution, and dbt validation on PRs. |

---

## Section C — Optional / Future Cloud Equivalents

These cloud services represent viable, cloud-native hosting alternatives for production deployment. They are **not** simultaneously required:

| Architecture Layer | Local Selected Choice | Optional Cloud Production Equivalents | Evaluation Context |
| :--- | :--- | :--- | :--- |
| **Data Warehouse** | PostgreSQL 16 | Google BigQuery / Snowflake / Managed Cloud PostgreSQL | PostgreSQL models seamlessly port to BigQuery via dbt profile config without SQL rewrites. |
| **Data Lake** | Local Parquet | Google Cloud Storage (GCS) or AWS S3 | Durable, scalable cloud object storage partitioned by date. |
| **Streaming Broker** | Local Kafka | Confluent Cloud / AWS MSK / Redpanda Cloud | Fully managed Kafka broker with TLS encryption and auto-scaling. |
| **Compute / Serving** | Local Uvicorn | Google Cloud Run / AWS ECS / Render Web Service | Serverless container deployment with automated SSL certificates and scale-to-zero. |
| **Frontend Hosting** | Local Next.js | Vercel / Google Cloud Run | Global edge CDN rendering with native Next.js optimization. |
| **Orchestration** | Local Airflow | Managed Cloud Composer / AWS MWAA / Astronomer | Managed cloud Airflow with auto-scaling worker nodes. |

---

## 4. Key Governance Rules

1. **No Multiple Simultaneous Technologies:** Only the selected local stack (Section B) is used for active development. Cloud equivalents (Section C) are production deployment targets, not concurrent dependencies.
2. **PostgreSQL Warehouse Label:** The choice of PostgreSQL as the development warehouse is explicitly classified as a **PROPOSED IMPLEMENTATION DECISION**.
3. **Notification Channels:** Slack and Email are the two chosen notification channels to fulfill PDF Section 10.
4. **Deliverables Accounting:** The platform tracks exactly **18 Mandatory Deliverables** and **1 Recommended Deliverable** (`Demo video`) as mandated by Section 17 of `AutoCare_Intelligence.pdf`.
