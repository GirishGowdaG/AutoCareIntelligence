# AutoCare Intelligence — Architecture & Technology Decisions

**Authoritative Reference:** `AutoCare_Intelligence.pdf` (Section 5)  
**Document Status:** Governed Technology Decision Record (TDR)  
**Last Updated:** September 2026

---

## 1. Executive Strategy & Architectural Directives

Section 5 of the AutoCare Intelligence assignment PDF defines the end-to-end pipeline:
$$\text{Source systems} \rightarrow \text{ingestion} \rightarrow \text{Kafka/event bus} \rightarrow \text{Bronze data lake} \rightarrow \text{Silver cleansing} \rightarrow \text{PySpark/SQL transformations} \rightarrow \text{cloud warehouse} \rightarrow \text{dbt analytical marts} \rightarrow \text{analytics/ML} \rightarrow \text{automation} \rightarrow \text{FastAPI} \rightarrow \text{React/Next.js} \rightarrow \text{cloud deployment.}$$

The PDF explicitly notes:  
*"Recommended technologies: Python, SQL, Kafka, PySpark, GCS/S3, BigQuery/Snowflake, dbt, Airflow, FastAPI, React/Next.js, Docker and GitHub Actions. Equivalent technologies are allowed."*

To eliminate ambiguity, prevent conflicting implementations, and ensure zero-cost student execution alongside enterprise-grade cloud deployment, this document records the **exact, authoritative technology selection** for each layer of the platform.

---

## 2. Technology Decision Matrix

| Architectural Layer | PDF Recommendation | Selected Implementation Decision | Mandatory vs. Proposed | Local Development Choice | Cloud Deployment Choice | Technical Rationale |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Programming Languages** | Python, SQL | **Python 3.10+ & ANSI SQL** | Mandatory | Python 3.10.11 (installed), native SQL | Python 3.10+ Linux runtime containers | Industry standard for data engineering, ML, FastAPI, and dbt. |
| **Event Bus / Streaming** | Kafka | **Apache Kafka** | Mandatory | Native Kafka broker / Docker / Confluent Cloud dev tier | Confluent Cloud / Managed Kafka broker | Distributed log, partition keys by `vehicle_id`, idempotent producer semantics. |
| **Data Lake Storage** | GCS / S3 | **S3-Compatible Object Store (Local MinIO & AWS S3 / GCS)** | Mandatory | Local structured directory / MinIO lake (`data/bronze/`, `data/silver/`) | AWS S3 or Google Cloud Storage | Cost-effective, immutable, scalable Parquet storage partitioned by date. |
| **Lakehouse Processing** | PySpark / SQL | **PySpark & DuckDB** | Mandatory | DuckDB / Local PySpark | PySpark / Serverless Dataproc or AWS EMR | PySpark satisfies the distributed ETL requirement; DuckDB provides blazing fast local relational verification. |
| **Data Warehouse** | BigQuery / Snowflake | **PROPOSED IMPLEMENTATION DECISION: PostgreSQL (Analytical) + BigQuery / Snowflake schema compatibility** | Proposed Implementation Decision | PostgreSQL 16 (or local analytical DuckDB/Postgres) | PostgreSQL on Managed Cloud (Render / Supabase / AWS RDS) or Google BigQuery | Full ANSI SQL compliance, zero local running costs, native dbt adapter support (`dbt-postgres`/`dbt-bigquery`), easily demonstrator-friendly. |
| **Analytical Modeling** | dbt | **dbt-core 1.7+** | Mandatory | `dbt-core` CLI | `dbt-core` in GitHub Actions CI & Airflow | Version-controlled SQL DAGs, automated data testing, documentation generation, column-level lineage. |
| **Orchestration** | Airflow | **Apache Airflow 2.8+** | Mandatory | Local Airflow (Standalone / Dockerized) | Managed Airflow (MWAA / Cloud Composer / Astronomer CLI) | Scheduled DAGs with automatic retries, failure callbacks, SLA alerts, and run logging. |
| **Machine Learning** | Analytics/ML | **scikit-learn, Isolation Forest, Prophet** | Mandatory | Python scikit-learn & Prophet packages | Containerized ML inference service | Robust, auditable algorithms for classification, anomaly detection, and time-series forecasting. |
| **Decision Engine** | Automation | **Python Rule Engine + Slack / Email Webhooks** | Mandatory | Local event evaluator + Incoming Webhook | Cloud event evaluator + Live Slack/Teams Incoming Webhook | Codifies the 4 domain rules; delivers live, verifiable notifications to Slack/Email. |
| **Backend API** | FastAPI | **FastAPI + Pydantic v2 + SQLAlchemy (Async)** | Mandatory | Uvicorn (`http://localhost:8000`) | Cloud Run / Render / AWS App Runner | Async I/O, auto-generated interactive OpenAPI/Swagger docs (`/docs`), native Server-Sent Events (SSE). |
| **Frontend Framework** | React / Next.js | **Next.js 14+ (App Router) + Tailwind CSS + Recharts** | Mandatory | Next.js dev server (`http://localhost:3000`) | Vercel / Cloud Run | Modern React server/client components, responsive KPI cards, interactive charts, and live SSE event indicator. |
| **Containerization** | Docker | **Multi-stage Dockerfiles & Docker Compose** | Mandatory | Multi-container `docker-compose.yml` | Container registry (GHCR/ECR/GCR) | Guarantees identical execution across all developer and evaluation environments. |
| **CI/CD** | GitHub Actions | **GitHub Actions CI/CD Pipeline** | Mandatory | `pre-commit` hooks & local pytest | `.github/workflows/ci.yml` running on pull requests | Automated linting, test execution, dbt test verification, and container build checks. |

---

## 3. Explicit Declarations & Clarifications

1. **Warehouse Strategy Declaration:**
   - **PROPOSED IMPLEMENTATION DECISION:** The primary development warehouse will use **PostgreSQL** (with analytical indexing and partitioned tables) and **DuckDB** for local development. In production, models can be seamlessly ported to **Google BigQuery** or **Snowflake** by swapping the dbt connection profile without modifying business logic SQL models.
2. **Notification Channel Declaration:**
   - The PDF mandates: *"At least two automated actions must send a notification through email, Slack or Teams."*
   - AutoCare Intelligence selects **Slack Webhooks** as the primary real-time integration and **Email (SMTP/SendGrid)** as the secondary channel. Mock-only or Discord-only notifications will **not** be considered compliant final evidence.
3. **Deliverables Count Declaration:**
   - As established by Section 17 of `AutoCare_Intelligence.pdf`, there are exactly **18 Mandatory Deliverables** and **1 Recommended Deliverable** (`Demo video`).
