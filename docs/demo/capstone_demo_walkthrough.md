# AutoCare Intelligence — 5-Minute Capstone Demo Walkthrough Script

**Document Version:** 1.0.0  
**Phase:** 6 — Productionization & Capstone Delivery  
**Target Duration:** Exactly 5 Minutes (300 Seconds)  
**Presenter:** Project Lead / Engineer  
**Audience:** Capstone Evaluation Panel & Stakeholders  

---

## Demo Timing & Sequence Overview

| Act | Timestamp | Demonstration Focus | Key Verification Proof Points |
|---|---|---|---|
| **Act 1** | 0:00 – 1:00 | Environment & Container Health Verification | `docker compose ps`, `/api/v1/health` 200 OK |
| **Act 2** | 1:00 – 2:00 | Fleet Overview & Real-Time SSE Telemetry | Live vehicle telemetry charts, streaming updates |
| **Act 3** | 2:00 – 3:00 | Predictive ML: Failure Risk & Demand Forecasting | 14-day failure risk tiers, 14-day capacity intervals |
| **Act 4** | 3:00 – 4:00 | Warranty Outlier Audit & Real-Time Anomaly Alerting | Forensic claim ranking, 3-ping consecutive trigger |
| **Act 5** | 4:00 – 5:00 | Enterprise RBAC Guard & Immutable Action Logs | 401/403 security enforcement, `action_logs` audit trail |

---

## Detailed Act-by-Act Script & Command Log

### Act 1: Environment & Container Health Verification (0:00 – 1:00)

**Speaker Talking Points:**
> "Welcome to the AutoCare Intelligence live capstone demonstration. AutoCare Intelligence is an enterprise-grade predictive maintenance, warranty analytics, and automated decisioning platform.
> We begin by verifying our containerized topology. The entire platform runs across five isolated, non-root Docker containers governed by Docker Compose with strict health checks and environment-provided fail-fast secrets."

**Actions & Commands:**
1. Open terminal and run:
   ```bash
   docker compose ps
   ```
   *Expected Output:* All 5 containers show `Up (healthy)`:
   - `autocare-postgres` (PostgreSQL 16 on 5432)
   - `autocare-kafka` (Apache Kafka 3.7 KRaft on 9092)
   - `autocare-backend` (FastAPI REST & SSE on 8000)
   - `autocare-frontend` (React 18 / Nginx on 5173)
   - `autocare-automation-worker` (Supervised Python daemon)

2. Demonstrate public healthcheck:
   ```bash
   curl -i http://localhost:8000/api/v1/health
   ```
   *Expected Output:* `HTTP/1.1 200 OK`, JSON response showing:
   ```json
   {
     "status": "healthy",
     "database": "connected",
     "models": "loaded",
     "kafka_broker": "mock_fallback"
   }
   ```

---

### Act 2: Fleet Overview & Real-Time SSE Telemetry Stream (1:00 – 2:00)

**Speaker Talking Points:**
> "Next, we transition to our live user interface running on port 3000 in Docker (or port 5173 in Vite dev server). We authenticate as an authorized operator.
> Under the Fleet Telemetry view, the platform maintains a persistent Server-Sent Events (SSE) connection streaming real-time IoT vehicle sensor readings—RPM, engine temperature, battery voltage, and vibration."

**Actions & UI Demonstration:**
1. Open browser to `http://localhost:3000` (or `http://localhost:5173` in local dev).
2. Select **Admin** persona from the role switcher in the top navigation bar.
3. Navigate to **Fleet Overview**:
   - Show the fleet summary cards: Active Vehicles, High-Risk Vehicles, Pending Service Bookings.
   - Point out the joined vehicle model specifications: Make, Model, Fuel Type, and Customer ownership details.
4. Navigate to **Live Telemetry Stream**:
   - Highlight the live streaming chart updating in real time via `/api/v1/stream/events`.
   - Point out the dual authentication support: works seamlessly with standard `X-API-Key` headers or browser EventSource `?api_key=` parameter.

---

### Act 3: Predictive ML: Failure Risk & Demand Forecasting (2:00 – 3:00)

**Speaker Talking Points:**
> "Moving to our predictive machine learning capabilities. AutoCare Intelligence replaces reactive maintenance with mathematically proven, calibrated ML models.
> Our Vehicle Failure Risk model predicts component breakdown 14 days in advance with a verified ROC-AUC of 0.72. Meanwhile, our Service Demand Forecasting model provides dealerships with 14-day capacity projections featuring 80% prediction intervals."

**Actions & UI Demonstration:**
1. Navigate to **Failure Risk Analysis**:
   - Inspect the high-risk vehicle rankings: Show risk scores, assigned risk tiers (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`), and SHAP-derived top features (e.g., maximum engine temperature, DTC frequency).
   - Explain how Rule 1 automatically schedules high-risk vehicles before breakdown occurs.
2. Navigate to **Dealership Demand Forecasting**:
   - Select a dealership service center (e.g., `DLR-001`).
   - Highlight the 14-day daily visit forecasts with upper and lower 80% confidence bands.
   - Show how Rule 3 monitors bay overload conditions when forecasted demand exceeds capacity baselines.

---

### Act 4: Warranty Outlier Audit & Real-Time Anomaly Alerting (3:00 – 4:00)

**Speaker Talking Points:**
> "In Act 4, we examine warranty audit intelligence and real-time streaming anomaly detection.
> For warranty claims, rather than making unverified fraud claims, our model is explicitly scoped as 'Unsupervised Warranty Outlier Ranking for Audit Prioritization'. It ranks claims by component median ratios and IQR distance, highlighting the top outliers for forensic audit.
> Simultaneously, our streaming sensor engine detects sensor anomalies under 5 milliseconds. To eliminate alert fatigue, our automation engine enforces Rule 2: requiring three consecutive anomalous pings before dispatching a critical alert."

**Actions & Terminal Demonstration:**
1. Navigate to **Warranty Outlier Audit**:
   - Show the claim outlier distribution table and percentile rankings.
   - Filter claims exceeding the 0.80 triage threshold recommended for audit review.
2. Demonstrate real-time sensor anomaly dispatch:
   - In terminal, show the worker processing consecutive anomalous telemetry pings.
   - Confirm that single transient spikes do not trigger notifications, whereas three consecutive anomalies trigger an immediate incident and dispatch to Slack.

---

### Act 5: Enterprise RBAC Guard & Immutable Action Logs (4:00 – 5:00)

**Speaker Talking Points:**
> "Finally, we demonstrate enterprise security, role-based access control, and our immutable audit log.
> The platform enforces a strict 3-tier RBAC hierarchy across Admin, DealerServiceManager, and FleetAnalyst personas. Furthermore, our database operates with strict privilege immutability: the API backend holds SELECT-only permissions, while the automation worker holds INSERT-only privileges on action logs. No deletion or modification is ever permitted."

**Actions & Demonstration:**
1. In the UI, switch to the **DealerServiceManager** persona:
   - Attempt to access the **Action Audit Logs** or **Warranty Outlier** screens.
   - Demonstrate the secure `403 Forbidden` response: "Operation not permitted for role DealerServiceManager".
2. Switch back to the **Admin** persona:
   - Navigate to **Action Audit Logs** (`/api/v1/audit/actions`).
   - Show the immutable chronological log of dispatched actions: `rule_id`, `entity_type`, `trigger_value`, `threshold_applied`, `delivery_status` (`DELIVERED` or `MOCK_LOGGED`), and JSON payload.
3. Run terminal verification:
   ```bash
   curl -s -H "X-API-Key: invalid-key" http://localhost:8000/api/v1/vehicles
   ```
   *Expected Output:* `{"detail":"Invalid or missing API Key"}` (`401 Unauthorized`).
4. Conclude the demonstration:
   > "In summary, AutoCare Intelligence delivers a complete, verified, secure, and production-ready intelligent fleet maintenance platform. Thank you."
