# AutoCare Intelligence — Architecture & Technology Decisions

**Authoritative Reference:** `AutoCare_Intelligence.pdf` (Section 5)  
**Document Status:** Governed Technology Decision Record (TDR)  
**Version:** 1.2.0  
**Last Updated:** September 2026

---

## 1. Executive Strategy & Architectural Directives

Section 5 of the AutoCare Intelligence assignment PDF defines the end-to-end pipeline:
$$\text{Source systems} \rightarrow \text{ingestion} \rightarrow \text{Kafka/event bus} \rightarrow \text{Bronze data lake} \rightarrow \text{Silver cleansing} \rightarrow \text{PySpark/SQL transformations} \rightarrow \text{cloud warehouse} \rightarrow \text{dbt analytical marts} \rightarrow \text{analytics/ML} \rightarrow \text{automation} \rightarrow \text{FastAPI} \rightarrow \text{React/Next.js} \rightarrow \text{cloud deployment.}$$

The PDF explicitly notes:  
*"Recommended technologies: Python, SQL, Kafka, PySpark, GCS/S3, BigQuery/Snowflake, dbt, Airflow, FastAPI, React/Next.js, Docker and GitHub Actions. Equivalent technologies are allowed."*

To eliminate confusion between local development and cloud targets, this document explicitly separates the **Local Development Stack** from the **Eventual Cloud Deployment Stack**.

---

## 2. Local Development Stack (Authoritative Selection)

The local stack is engineered for immediate, zero-cost, reproducible developer workflows on local developer workstations:

| Architectural Layer | PDF Baseline | Local Development Selection | Classification | Technical Rationale |
| :--- | :--- | :--- | :--- | :--- |
| **Programming Language** | Python, SQL | **Python 3.10+ & Modern ANSI SQL** | **MANDATORY PDF REQUIREMENT** | Standard across data engineering, ML, backend API, and dbt. |
| **Streaming / Message Bus** | Kafka | **Apache Kafka (Local / In-Process Mock Test Harness)** | **MANDATORY PDF REQUIREMENT** | Full Kafka API compatibility; supports partition keys by `vehicle_id` and idempotent delivery. |
| **Data Lake Storage** | GCS / S3 | **Local Parquet Lakehouse (`data/bronze/`, `data/silver/`)** | **MANDATORY PDF REQUIREMENT** | Immutable Bronze raw files and partitioned Silver Parquet files on local disk. |
| **Lakehouse Processing** | PySpark / SQL | **DuckDB & PySpark** | **MANDATORY PDF REQUIREMENT** | DuckDB for ultra-fast local analytical SQL and schema verification; PySpark for distributed transformations. |
| **Data Warehouse** | BigQuery / Snowflake | **PostgreSQL (Analytical Star Schema)** | **PROPOSED IMPLEMENTATION DECISION** | Full ANSI SQL star schema, zero cloud billing risk during development, native dbt support (`dbt-postgres`). |
| **Data Modeling** | dbt | **dbt-core 1.7+** | **MANDATORY PDF REQUIREMENT** | Governed staging, intermediate, and marts models; automated dbt tests; documentation generation. |
| **Workflow Orchestration** | Airflow | **Apache Airflow 2.8+ (Standalone / Local)** | **MANDATORY PDF REQUIREMENT** | Scheduled DAG execution, automatic retries, task dependencies, and run logs. |
| **Machine Learning** | Analytics / ML | **scikit-learn, IsolationForest, Prophet** | **MANDATORY PDF REQUIREMENT** | Auditable implementations for Failure Risk, Sensor Anomaly, Demand Forecast, and Warranty Outliers. |
| **Decision Engine** | Automation | **Python Rule Engine + Slack Incoming Webhook & SMTP** | **MANDATORY PDF REQUIREMENT** | Codifies the 4 domain rules; delivers live, verifiable notifications to Slack and Email. |
| **Backend API** | FastAPI | **FastAPI + Pydantic v2 + Uvicorn** | **MANDATORY PDF REQUIREMENT** | Async endpoints (`http://localhost:8000`), auto-generated OpenAPI documentation, native SSE live stream. |
| **Frontend Framework** | React / Next.js | **Next.js 14+ (App Router) + Tailwind CSS + Recharts** | **MANDATORY PDF REQUIREMENT** | Modern server/client components (`http://localhost:3000`), responsive KPI cards, and live telemetry feed. |
| **Testing & CI** | Test cases | **pytest + pytest-cov + dbt test** | **MANDATORY PDF REQUIREMENT** | Automated test suite enforcing schema contracts, ranges, keys, and reproducibility. |

---

## 3. Eventual Cloud Deployment Stack (Separate Cloud Equivalents)

The cloud architecture maps the local components 1-to-1 to production cloud services:

| Local Component | Eventual Cloud Equivalent | Classification | Cloud Hosting Rationale |
| :--- | :--- | :--- | :--- |
| **Local Kafka** | Confluent Cloud / AWS MSK / Managed Kafka | **MANDATORY PDF REQUIREMENT** | Fully managed distributed log with TLS encryption and auto-scaling. |
| **Local Parquet Lake** | AWS S3 or Google Cloud Storage (GCS) | **MANDATORY PDF REQUIREMENT** | Scalable, durable object storage partitioned by `year=YYYY/month=MM/day=DD`. |
| **DuckDB / Local PySpark** | Google Cloud Dataproc / AWS EMR Serverless | **MANDATORY PDF REQUIREMENT** | Cloud-native distributed processing for large batch ingestion and cleansing. |
| **PostgreSQL Warehouse** | Google BigQuery / Snowflake / Managed Cloud PostgreSQL | **PROPOSED IMPLEMENTATION DECISION** | ANSI SQL analytical warehouse. dbt profiles switch seamlessly between Postgres and BigQuery. |
| **Local Airflow** | Managed Airflow (MWAA / Cloud Composer / Astronomer) | **MANDATORY PDF REQUIREMENT** | High-availability cloud DAG scheduler with automated worker scaling. |
| **FastAPI Backend** | Google Cloud Run / AWS ECS / Render Web Service | **MANDATORY PDF REQUIREMENT** | Serverless container deployment with automated HTTPS and scale-to-zero capability. |
| **Next.js Frontend** | Vercel / Google Cloud Run | **MANDATORY PDF REQUIREMENT** | Global edge CDN rendering with instant Next.js App Router optimization. |
| **Local Docker** | GitHub Actions CI/CD + Cloud Container Registry (GHCR/ECR) | **MANDATORY PDF REQUIREMENT** | Automated build, test, and container publishing on pull request. |

---

## 4. Explicit Governance Declarations

1. **No Competing Technologies:** We do not treat PostgreSQL, BigQuery, Snowflake, and DuckDB as simultaneously required. **PostgreSQL** is the selected development warehouse, and **DuckDB** is the local execution engine. BigQuery/Snowflake are production cloud equivalents.
2. **Warehouse Decision Classification:** The choice of PostgreSQL as the development warehouse is explicitly classified as a **PROPOSED IMPLEMENTATION DECISION**.
3. **Notification Channels:** In strict accordance with PDF Section 10 (*"At least two automated actions must send a notification through email, Slack or Teams"*), **Slack Webhooks** and **Email (SMTP)** are the selected notification targets.
4. **Deliverables Count:** Exactly **18 Mandatory Deliverables** and **1 Recommended Deliverable** (`Demo video`) as mandated by Section 17 of `AutoCare_Intelligence.pdf`.
