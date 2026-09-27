-- AutoCare Intelligence Phase 5: Machine Learning Operational Schema
-- Isolated operational and inference store outside autocare_dw base star schema.

CREATE SCHEMA IF NOT EXISTS ml_inference;

-- 1. Vehicle Failure-Risk Predictions
CREATE TABLE IF NOT EXISTS ml_inference.vehicle_failure_predictions (
    prediction_id UUID PRIMARY KEY,
    vehicle_id VARCHAR(64) NOT NULL,
    cutoff_date DATE NOT NULL,
    risk_score DOUBLE PRECISION NOT NULL,
    risk_tier VARCHAR(16) NOT NULL,
    top_features JSONB,
    model_version VARCHAR(32) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ml_failure_vehicle_date 
    ON ml_inference.vehicle_failure_predictions (vehicle_id, cutoff_date);

-- 2. Sensor Anomalies (Telemetry)
CREATE TABLE IF NOT EXISTS ml_inference.sensor_anomalies (
    anomaly_id UUID PRIMARY KEY,
    vehicle_id VARCHAR(64) NOT NULL,
    window_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    anomaly_score DOUBLE PRECISION NOT NULL,
    is_anomaly BOOLEAN NOT NULL,
    anomalous_features JSONB,
    model_version VARCHAR(32) NOT NULL,
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ml_sensor_vehicle_ts 
    ON ml_inference.sensor_anomalies (vehicle_id, window_timestamp);

-- 3. Service-Demand Forecasts
CREATE TABLE IF NOT EXISTS ml_inference.service_demand_forecasts (
    forecast_id UUID PRIMARY KEY,
    dealer_id VARCHAR(64) NOT NULL,
    forecast_date DATE NOT NULL,
    predicted_volume DOUBLE PRECISION NOT NULL,
    lower_bound_80 DOUBLE PRECISION NOT NULL,
    upper_bound_80 DOUBLE PRECISION NOT NULL,
    model_version VARCHAR(32) NOT NULL,
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ml_demand_dealer_date 
    ON ml_inference.service_demand_forecasts (dealer_id, forecast_date);

-- 4. Warranty Claim Anomalies
CREATE TABLE IF NOT EXISTS ml_inference.warranty_anomalies (
    anomaly_id UUID PRIMARY KEY,
    claim_id VARCHAR(64) NOT NULL,
    dealer_id VARCHAR(64),
    component_id VARCHAR(64),
    claim_amount NUMERIC(12, 2) NOT NULL,
    anomaly_score DOUBLE PRECISION NOT NULL,
    outlier_reasons JSONB,
    model_version VARCHAR(32) NOT NULL,
    flagged_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ml_warranty_claim 
    ON ml_inference.warranty_anomalies (claim_id);

-- 5. Model Metadata & Governance Registry
CREATE TABLE IF NOT EXISTS ml_inference.model_metadata (
    model_id VARCHAR(64) NOT NULL,
    model_version VARCHAR(32) NOT NULL,
    trained_at TIMESTAMP WITH TIME ZONE NOT NULL,
    training_git_commit VARCHAR(64) NOT NULL,
    training_data_sha256 VARCHAR(64) NOT NULL,
    feature_names JSONB NOT NULL,
    hyperparameters JSONB NOT NULL,
    metrics JSONB NOT NULL,
    artifact_path VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (model_id, model_version)
);
