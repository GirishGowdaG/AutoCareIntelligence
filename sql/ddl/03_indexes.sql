-- AutoCare Intelligence — Enterprise Data Warehouse DDL
-- File: 03_indexes.sql
-- Target Database: PostgreSQL 16+
-- Indexes: Performance B-Tree indexes on dimension natural keys, foreign keys, and temporal filters

-- ============================================================================
-- 1. Dimension Natural Key Lookup Indexes
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_dim_model_name ON autocare_dw.dim_model(model_name);
CREATE INDEX IF NOT EXISTS idx_dim_dealer_id ON autocare_dw.dim_dealer(dealer_id);
CREATE INDEX IF NOT EXISTS idx_dim_customer_id ON autocare_dw.dim_customer(customer_id);
CREATE INDEX IF NOT EXISTS idx_dim_component_name ON autocare_dw.dim_component(component_name);
CREATE INDEX IF NOT EXISTS idx_dim_vehicle_id ON autocare_dw.dim_vehicle(vehicle_id);

-- ============================================================================
-- 2. Dimension Hierarchy Foreign Key Indexes
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_dim_vehicle_model ON autocare_dw.dim_vehicle(model_key);
CREATE INDEX IF NOT EXISTS idx_dim_vehicle_customer ON autocare_dw.dim_vehicle(customer_key);
CREATE INDEX IF NOT EXISTS idx_dim_vehicle_dealer ON autocare_dw.dim_vehicle(selling_dealer_key);

-- ============================================================================
-- 3. fact_telemetry Foreign Key & Time-Series Indexes
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_fact_telemetry_vehicle_ts ON autocare_dw.fact_telemetry(vehicle_key, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_fact_telemetry_date ON autocare_dw.fact_telemetry(date_key);

-- ============================================================================
-- 4. fact_service Foreign Key & Temporal Indexes
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_fact_service_vehicle ON autocare_dw.fact_service(vehicle_key);
CREATE INDEX IF NOT EXISTS idx_fact_service_dealer ON autocare_dw.fact_service(dealer_key);
CREATE INDEX IF NOT EXISTS idx_fact_service_date ON autocare_dw.fact_service(date_key);

-- ============================================================================
-- 5. fact_warranty Foreign Key & Temporal Indexes
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_fact_warranty_vehicle ON autocare_dw.fact_warranty(vehicle_key);
CREATE INDEX IF NOT EXISTS idx_fact_warranty_component ON autocare_dw.fact_warranty(component_key);
CREATE INDEX IF NOT EXISTS idx_fact_warranty_date ON autocare_dw.fact_warranty(date_key);

-- ============================================================================
-- 6. fact_parts Foreign Key & Atomic Part Lookup Indexes
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_fact_parts_dealer ON autocare_dw.fact_parts(dealer_key);
CREATE INDEX IF NOT EXISTS idx_fact_parts_component ON autocare_dw.fact_parts(component_key);
CREATE INDEX IF NOT EXISTS idx_fact_parts_date ON autocare_dw.fact_parts(date_key);
CREATE INDEX IF NOT EXISTS idx_fact_parts_part_id ON autocare_dw.fact_parts(part_id);
