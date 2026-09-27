-- AutoCare Intelligence Phase 6: Decision Automation Action Logs Schema
-- Audit log of automated decisions, triggers, and notification deliveries.

CREATE TABLE IF NOT EXISTS ml_inference.action_logs (
    action_id UUID PRIMARY KEY,
    rule_id VARCHAR(64) NOT NULL,
    entity_type VARCHAR(32) NOT NULL,
    entity_id VARCHAR(64) NOT NULL,
    trigger_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    trigger_value DOUBLE PRECISION NOT NULL,
    threshold_applied DOUBLE PRECISION NOT NULL,
    action_taken TEXT NOT NULL,
    channel_dispatched VARCHAR(32) NOT NULL,
    delivery_status VARCHAR(32) NOT NULL,
    idempotency_key VARCHAR(128) UNIQUE NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_action_logs_rule 
    ON ml_inference.action_logs (rule_id);

CREATE INDEX IF NOT EXISTS idx_action_logs_entity 
    ON ml_inference.action_logs (entity_type, entity_id);

CREATE INDEX IF NOT EXISTS idx_action_logs_timestamp 
    ON ml_inference.action_logs (trigger_timestamp);

CREATE INDEX IF NOT EXISTS idx_action_logs_idempotency 
    ON ml_inference.action_logs (idempotency_key);
