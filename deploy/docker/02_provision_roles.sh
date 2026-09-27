#!/bin/sh
set -e

# ==============================================================================
# AutoCare Intelligence — Phase 6 Stage 4: PostgreSQL Application Role Provisioning
# Executed automatically by postgres entrypoint during initial cluster bootstrap.
# Provisions autocare_backend and autocare_worker with strictly scoped least-privilege access.
# ==============================================================================

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- 1. Idempotently create or configure autocare_backend and autocare_worker roles
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'autocare_backend') THEN
            CREATE ROLE autocare_backend WITH
                LOGIN
                PASSWORD '$AUTOCARE_BACKEND_DB_PASSWORD'
                NOSUPERUSER
                NOCREATEDB
                NOCREATEROLE
                NOINHERIT
                NOREPLICATION
                CONNECTION LIMIT 20;
        ELSE
            ALTER ROLE autocare_backend WITH
                LOGIN
                PASSWORD '$AUTOCARE_BACKEND_DB_PASSWORD'
                NOSUPERUSER
                NOCREATEDB
                NOCREATEROLE
                NOINHERIT
                NOREPLICATION
                CONNECTION LIMIT 20;
        END IF;

        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'autocare_worker') THEN
            CREATE ROLE autocare_worker WITH
                LOGIN
                PASSWORD '$AUTOCARE_WORKER_DB_PASSWORD'
                NOSUPERUSER
                NOCREATEDB
                NOCREATEROLE
                NOINHERIT
                NOREPLICATION
                CONNECTION LIMIT 10;
        ELSE
            ALTER ROLE autocare_worker WITH
                LOGIN
                PASSWORD '$AUTOCARE_WORKER_DB_PASSWORD'
                NOSUPERUSER
                NOCREATEDB
                NOCREATEROLE
                NOINHERIT
                NOREPLICATION
                CONNECTION LIMIT 10;
        END IF;
    END
    \$\$;

    -- 2. Revoke any prior broad grants (idempotency enforcement)
    REVOKE ALL ON ALL TABLES IN SCHEMA autocare_dw FROM autocare_backend, autocare_worker;
    REVOKE ALL ON ALL TABLES IN SCHEMA staging FROM autocare_backend, autocare_worker;
    REVOKE ALL ON ALL TABLES IN SCHEMA ml_inference FROM autocare_backend, autocare_worker;
    REVOKE USAGE ON SCHEMA autocare_dw, staging, ml_inference FROM autocare_backend, autocare_worker;

    -- 3. Database Connection Grants
    GRANT CONNECT ON DATABASE autocare_dw TO autocare_backend;
    GRANT CONNECT ON DATABASE autocare_dw TO autocare_worker;

    -- 4. Schema USAGE Grants
    GRANT USAGE ON SCHEMA autocare_dw TO autocare_backend;
    GRANT USAGE ON SCHEMA staging TO autocare_backend;
    GRANT USAGE ON SCHEMA ml_inference TO autocare_backend;

    GRANT USAGE ON SCHEMA ml_inference TO autocare_worker;

    -- 5. Table Privileges for autocare_backend (SELECT ONLY on EXACTLY 9 approved tables)
    GRANT SELECT ON TABLE autocare_dw.dim_vehicle TO autocare_backend;
    GRANT SELECT ON TABLE autocare_dw.dim_model TO autocare_backend;
    GRANT SELECT ON TABLE autocare_dw.dim_dealer TO autocare_backend;
    GRANT SELECT ON TABLE staging.silver_diagnostics TO autocare_backend;
    GRANT SELECT ON TABLE ml_inference.vehicle_failure_predictions TO autocare_backend;
    GRANT SELECT ON TABLE ml_inference.sensor_anomalies TO autocare_backend;
    GRANT SELECT ON TABLE ml_inference.service_demand_forecasts TO autocare_backend;
    GRANT SELECT ON TABLE ml_inference.warranty_anomalies TO autocare_backend;
    GRANT SELECT ON TABLE ml_inference.action_logs TO autocare_backend;

    -- 6. Table Privileges for autocare_worker (SELECT on 4 tables, INSERT ONLY on ml_inference.action_logs)
    GRANT SELECT ON TABLE ml_inference.vehicle_failure_predictions TO autocare_worker;
    GRANT SELECT ON TABLE ml_inference.service_demand_forecasts TO autocare_worker;
    GRANT SELECT ON TABLE ml_inference.warranty_anomalies TO autocare_worker;
    GRANT SELECT ON TABLE ml_inference.action_logs TO autocare_worker;

    GRANT INSERT ON TABLE ml_inference.action_logs TO autocare_worker;
EOSQL
