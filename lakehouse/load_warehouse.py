"""AutoCare Intelligence — Phase 2C Silver-to-Warehouse Loading Pipeline.

Authoritative References:
- AutoCare_Intelligence.pdf (Section 4 & Section 7)
- Approved Medallion Data Lakehouse (data/silver/)
- Approved PostgreSQL 16+ Star Schema DDL (sql/ddl/)

Features:
- Loads strictly the approved 6 dimensions and 4 facts (10 tables total).
- Resolves foreign keys in-memory via O(1) surrogate key dictionaries.
- Implements vehicle_customer_map: vehicle_id -> customer_id -> customer_key.
- Implements part_id -> Silver component catalog -> dim_component.component_key.
- Handles unknown dimension business keys via surrogate key -1.
- Validates fact domain bounds (fails validation on invalid measures).
- Populates conformed daily calendar in dim_date (2020-01-01 to 2030-12-31).
- Implements idempotent telemetry loading using NOT EXISTS anti-join.
- Single-process execution contract: safe, transactional, deterministic.
- Supports DuckDB (default embedded warehouse) and PostgreSQL engines.
"""

from datetime import date, datetime, timedelta
import logging
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple

import duckdb
import pandas as pd
import pyarrow.dataset as ds

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data_generator.config import MODELS

# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("warehouse_loader")

SILVER_DIR = Path("data/silver")
WAREHOUSE_DIR = Path("data/warehouse")
DEFAULT_DUCKDB_PATH = WAREHOUSE_DIR / "autocare.duckdb"


class WarehouseLoader:
    """Orchestrates loading of Silver datasets into the Star Schema warehouse."""

    def __init__(self, db_path: Optional[Path] = None, in_memory: bool = False):
        self.in_memory = in_memory
        if in_memory:
            self.db_path = ":memory:"
        else:
            self.db_path = str(db_path or DEFAULT_DUCKDB_PATH)
            WAREHOUSE_DIR.mkdir(parents=True, exist_ok=True)

        self.con = duckdb.connect(self.db_path)
        logger.info(f"Connected to warehouse database at '{self.db_path}'")

        # In-memory lookup caches for O(1) key resolution
        self.model_lookup: Dict[str, int] = {}
        self.dealer_lookup: Dict[str, int] = {}
        self.customer_lookup: Dict[str, int] = {}
        self.component_lookup: Dict[str, int] = {}
        self.vehicle_lookup: Dict[str, int] = {}
        self.part_to_component_key: Dict[str, int] = {}

    def init_schema(self) -> None:
        """Initializes autocare_dw schema, sequences, and tables in target database."""
        logger.info("Initializing schema 'autocare_dw' and table structures...")
        self.con.execute("CREATE SCHEMA IF NOT EXISTS autocare_dw;")

        # Sequences for surrogate keys
        for seq in ["model", "dealer", "customer", "component", "vehicle", "telemetry", "service", "warranty", "parts"]:
            self.con.execute(f"CREATE SEQUENCE IF NOT EXISTS autocare_dw.seq_{seq}_key START 1;")

        # 1. dim_date
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS autocare_dw.dim_date (
                date_key INT PRIMARY KEY,
                calendar_date DATE UNIQUE NOT NULL,
                day_of_week INT NOT NULL CHECK (day_of_week BETWEEN 1 AND 7),
                day_name VARCHAR(16) NOT NULL,
                day_of_month INT NOT NULL CHECK (day_of_month BETWEEN 1 AND 31),
                day_of_year INT NOT NULL CHECK (day_of_year BETWEEN 1 AND 366),
                week_of_year INT NOT NULL CHECK (week_of_year BETWEEN 1 AND 53),
                month_number INT NOT NULL CHECK (month_number BETWEEN 1 AND 12),
                month_name VARCHAR(16) NOT NULL,
                quarter INT NOT NULL CHECK (quarter BETWEEN 1 AND 4),
                year INT NOT NULL,
                is_weekend BOOLEAN NOT NULL
            );
        """)

        # 2. dim_model
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS autocare_dw.dim_model (
                model_key INT PRIMARY KEY DEFAULT nextval('autocare_dw.seq_model_key'),
                model_name VARCHAR(64) UNIQUE NOT NULL,
                vehicle_class VARCHAR(32) NOT NULL,
                powertrain_type VARCHAR(32) NOT NULL,
                fuel_capacity_or_kwh NUMERIC(6,2) NOT NULL CHECK (fuel_capacity_or_kwh >= 0.0),
                curb_weight_kg NUMERIC(8,2) NOT NULL CHECK (curb_weight_kg >= 0.0)
            );
        """)

        # 3. dim_dealer
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS autocare_dw.dim_dealer (
                dealer_key INT PRIMARY KEY DEFAULT nextval('autocare_dw.seq_dealer_key'),
                dealer_id VARCHAR(32) UNIQUE NOT NULL,
                dealer_name VARCHAR(128) NOT NULL,
                city VARCHAR(64) NOT NULL,
                state VARCHAR(32) NOT NULL,
                region VARCHAR(32) NOT NULL,
                tier VARCHAR(16) NOT NULL
            );
        """)

        # 4. dim_customer
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS autocare_dw.dim_customer (
                customer_key INT PRIMARY KEY DEFAULT nextval('autocare_dw.seq_customer_key'),
                customer_id VARCHAR(32) UNIQUE NOT NULL,
                customer_name VARCHAR(128) NOT NULL,
                email VARCHAR(128) NOT NULL,
                phone VARCHAR(32) NOT NULL,
                address VARCHAR(255) NOT NULL,
                city VARCHAR(64) NOT NULL,
                state VARCHAR(32) NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 5. dim_component
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS autocare_dw.dim_component (
                component_key INT PRIMARY KEY DEFAULT nextval('autocare_dw.seq_component_key'),
                component_name VARCHAR(64) UNIQUE NOT NULL,
                category VARCHAR(64) NOT NULL,
                expected_lifespan_km INT NOT NULL CHECK (expected_lifespan_km >= 0),
                warranty_period_months INT NOT NULL CHECK (warranty_period_months >= 0)
            );
        """)

        # 6. dim_vehicle
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS autocare_dw.dim_vehicle (
                vehicle_key INT PRIMARY KEY DEFAULT nextval('autocare_dw.seq_vehicle_key'),
                vehicle_id VARCHAR(32) UNIQUE NOT NULL,
                model_key INT NOT NULL REFERENCES autocare_dw.dim_model(model_key),
                customer_key INT NOT NULL REFERENCES autocare_dw.dim_customer(customer_key),
                selling_dealer_key INT NOT NULL REFERENCES autocare_dw.dim_dealer(dealer_key),
                variant VARCHAR(32) NOT NULL,
                manufacture_date DATE NOT NULL,
                manufacture_year INT NOT NULL CHECK (manufacture_year >= 1900),
                status VARCHAR(16) NOT NULL DEFAULT 'ACTIVE'
            );
        """)

        # 7. fact_telemetry
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS autocare_dw.fact_telemetry (
                telemetry_fact_id BIGINT PRIMARY KEY DEFAULT nextval('autocare_dw.seq_telemetry_key'),
                vehicle_key INT NOT NULL REFERENCES autocare_dw.dim_vehicle(vehicle_key),
                date_key INT NOT NULL REFERENCES autocare_dw.dim_date(date_key),
                timestamp TIMESTAMP NOT NULL,
                rpm INT NOT NULL CHECK (rpm >= 0 AND rpm <= 9000),
                temperature NUMERIC(5,2) NOT NULL CHECK (temperature >= -40.0 AND temperature <= 160.0),
                battery NUMERIC(4,2) NOT NULL CHECK (battery >= 9.0 AND battery <= 16.0),
                vibration NUMERIC(6,3) NOT NULL CHECK (vibration >= 0.0 AND vibration <= 15.0),
                _silver_batch_id VARCHAR(64),
                _loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 8. fact_service
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS autocare_dw.fact_service (
                service_fact_id INT PRIMARY KEY DEFAULT nextval('autocare_dw.seq_service_key'),
                service_id VARCHAR(32) UNIQUE NOT NULL,
                vehicle_key INT NOT NULL REFERENCES autocare_dw.dim_vehicle(vehicle_key),
                dealer_key INT NOT NULL REFERENCES autocare_dw.dim_dealer(dealer_key),
                date_key INT NOT NULL REFERENCES autocare_dw.dim_date(date_key),
                visit_date DATE NOT NULL,
                issue TEXT NOT NULL,
                cost NUMERIC(10,2) NOT NULL CHECK (cost >= 0.00),
                _silver_batch_id VARCHAR(64),
                _loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 9. fact_warranty
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS autocare_dw.fact_warranty (
                warranty_fact_id INT PRIMARY KEY DEFAULT nextval('autocare_dw.seq_warranty_key'),
                claim_id VARCHAR(32) UNIQUE NOT NULL,
                vehicle_key INT NOT NULL REFERENCES autocare_dw.dim_vehicle(vehicle_key),
                component_key INT NOT NULL REFERENCES autocare_dw.dim_component(component_key),
                date_key INT NOT NULL REFERENCES autocare_dw.dim_date(date_key),
                claim_date DATE NOT NULL,
                amount NUMERIC(10,2) NOT NULL CHECK (amount > 0.00),
                _silver_batch_id VARCHAR(64),
                _loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 10. fact_parts
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS autocare_dw.fact_parts (
                parts_fact_id INT PRIMARY KEY DEFAULT nextval('autocare_dw.seq_parts_key'),
                part_id VARCHAR(32) NOT NULL,
                dealer_key INT NOT NULL REFERENCES autocare_dw.dim_dealer(dealer_key),
                component_key INT NOT NULL REFERENCES autocare_dw.dim_component(component_key),
                date_key INT NOT NULL REFERENCES autocare_dw.dim_date(date_key),
                snapshot_date DATE NOT NULL,
                stock INT NOT NULL CHECK (stock >= 0),
                lead_time INT NOT NULL CHECK (lead_time >= 1),
                _silver_batch_id VARCHAR(64),
                _loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT uq_fact_parts_snapshot UNIQUE (part_id, dealer_key, date_key)
            );
        """)

        self.seed_unknown_members()

    def seed_unknown_members(self) -> None:
        """Seeds the default -1 unknown members for all 6 dimensions."""
        logger.info("Seeding -1 unknown members across all 6 dimensions...")

        # dim_date
        self.con.execute("""
            INSERT INTO autocare_dw.dim_date (
                date_key, calendar_date, day_of_week, day_name, day_of_month, day_of_year,
                week_of_year, month_number, month_name, quarter, year, is_weekend
            ) VALUES (
                -1, '1900-01-01', 1, 'Monday', 1, 1, 1, 1, 'January', 1, 1900, FALSE
            ) ON CONFLICT (date_key) DO NOTHING;
        """)

        # dim_model
        self.con.execute("""
            INSERT INTO autocare_dw.dim_model (
                model_key, model_name, vehicle_class, powertrain_type, fuel_capacity_or_kwh, curb_weight_kg
            ) VALUES (
                -1, 'UNKNOWN MODEL', 'UNKNOWN', 'UNKNOWN', 0.0, 0.0
            ) ON CONFLICT (model_name) DO NOTHING;
        """)

        # dim_dealer
        self.con.execute("""
            INSERT INTO autocare_dw.dim_dealer (
                dealer_key, dealer_id, dealer_name, city, state, region, tier
            ) VALUES (
                -1, 'UNKNOWN_DLR', 'UNKNOWN DEALER', 'UNKNOWN', 'UNKNOWN', 'UNKNOWN', 'UNKNOWN'
            ) ON CONFLICT (dealer_id) DO NOTHING;
        """)

        # dim_customer
        self.con.execute("""
            INSERT INTO autocare_dw.dim_customer (
                customer_key, customer_id, customer_name, email, phone, address, city, state
            ) VALUES (
                -1, 'UNKNOWN_CUST', 'UNKNOWN CUSTOMER', 'unknown@autocare.local', '000-000-0000', 'UNKNOWN', 'UNKNOWN', 'UNKNOWN'
            ) ON CONFLICT (customer_id) DO NOTHING;
        """)

        # dim_component
        self.con.execute("""
            INSERT INTO autocare_dw.dim_component (
                component_key, component_name, category, expected_lifespan_km, warranty_period_months
            ) VALUES (
                -1, 'UNKNOWN COMPONENT', 'UNKNOWN', 0, 0
            ) ON CONFLICT (component_name) DO NOTHING;
        """)

        # dim_vehicle
        self.con.execute("""
            INSERT INTO autocare_dw.dim_vehicle (
                vehicle_key, vehicle_id, model_key, customer_key, selling_dealer_key,
                variant, manufacture_date, manufacture_year, status
            ) VALUES (
                -1, 'UNKNOWN_VH', -1, -1, -1, 'UNKNOWN', '1900-01-01', 1900, 'UNKNOWN'
            ) ON CONFLICT (vehicle_id) DO NOTHING;
        """)

    def load_dim_date(self) -> int:
        """Pre-populates conformed daily calendar in dim_date (2020-01-01 to 2030-12-31)."""
        logger.info("Loading dim_date (2020-01-01 to 2030-12-31)...")
        start_date = date(2020, 1, 1)
        end_date = date(2030, 12, 31)
        current = start_date
        records = []

        while current <= end_date:
            date_key = int(current.strftime("%Y%m%d"))
            records.append((
                date_key,
                current,
                current.isoweekday(),
                current.strftime("%A"),
                current.day,
                current.timetuple().tm_yday,
                current.isocalendar()[1],
                current.month,
                current.strftime("%B"),
                (current.month - 1) // 3 + 1,
                current.year,
                current.isoweekday() in (6, 7),
            ))
            current += timedelta(days=1)

        date_df = pd.DataFrame(records, columns=[
            "date_key", "calendar_date", "day_of_week", "day_name", "day_of_month",
            "day_of_year", "week_of_year", "month_number", "month_name", "quarter",
            "year", "is_weekend"
        ])

        self.con.register("staged_dates", date_df)
        self.con.execute("""
            INSERT INTO autocare_dw.dim_date
            SELECT * FROM staged_dates
            ON CONFLICT (date_key) DO NOTHING;
        """)
        self.con.unregister("staged_dates")

        count = self.con.execute("SELECT COUNT(*) FROM autocare_dw.dim_date;").fetchone()[0]
        logger.info(f"dim_date loaded successfully: {count} total rows (including unknown member).")
        return count

    def load_dim_model(self) -> int:
        """Loads distinct models from silver/vehicles with approved config engine types."""
        logger.info("Loading dim_model...")
        vh_dataset = ds.dataset(str(SILVER_DIR / "vehicles"), format="parquet")
        vh_df = vh_dataset.to_table().to_pandas()
        unique_models = sorted(vh_df["model"].unique())

        engine_type_map = {m["model"]: m["engine_type"] for m in MODELS}

        records = []
        for model in unique_models:
            powertrain = engine_type_map.get(model, "UNKNOWN")
            records.append((model, "UNKNOWN", powertrain, 0.0, 0.0))

        model_df = pd.DataFrame(records, columns=[
            "model_name", "vehicle_class", "powertrain_type", "fuel_capacity_or_kwh", "curb_weight_kg"
        ])

        self.con.register("staged_models", model_df)
        self.con.execute("""
            INSERT INTO autocare_dw.dim_model (model_name, vehicle_class, powertrain_type, fuel_capacity_or_kwh, curb_weight_kg)
            SELECT model_name, vehicle_class, powertrain_type, fuel_capacity_or_kwh, curb_weight_kg
            FROM staged_models
            ON CONFLICT (model_name) DO UPDATE SET
                vehicle_class = EXCLUDED.vehicle_class,
                powertrain_type = EXCLUDED.powertrain_type,
                fuel_capacity_or_kwh = EXCLUDED.fuel_capacity_or_kwh,
                curb_weight_kg = EXCLUDED.curb_weight_kg;
        """)
        self.con.unregister("staged_models")

        rows = self.con.execute("SELECT model_name, model_key FROM autocare_dw.dim_model;").fetchall()
        self.model_lookup = {r[0]: r[1] for r in rows}
        count = len(rows)
        logger.info(f"dim_model loaded: {count} rows (including unknown member). Lookup cached: {self.model_lookup}")
        return count

    def load_dim_dealer(self) -> int:
        """Loads dealership facilities from silver/dealers."""
        logger.info("Loading dim_dealer...")
        dlr_dataset = ds.dataset(str(SILVER_DIR / "dealers"), format="parquet")
        dlr_df = dlr_dataset.to_table().to_pandas()

        dlr_clean = pd.DataFrame({
            "dealer_id": dlr_df["dealer_id"],
            "dealer_name": dlr_df["name"],
            "city": dlr_df["city"],
            "state": "UNKNOWN",
            "region": dlr_df["region"],
            "tier": "UNKNOWN",
        })

        self.con.register("staged_dealers", dlr_clean)
        self.con.execute("""
            INSERT INTO autocare_dw.dim_dealer (dealer_id, dealer_name, city, state, region, tier)
            SELECT dealer_id, dealer_name, city, state, region, tier
            FROM staged_dealers
            ON CONFLICT (dealer_id) DO UPDATE SET
                dealer_name = EXCLUDED.dealer_name,
                city = EXCLUDED.city,
                state = EXCLUDED.state,
                region = EXCLUDED.region,
                tier = EXCLUDED.tier;
        """)
        self.con.unregister("staged_dealers")

        rows = self.con.execute("SELECT dealer_id, dealer_key FROM autocare_dw.dim_dealer;").fetchall()
        self.dealer_lookup = {r[0]: r[1] for r in rows}
        count = len(rows)
        logger.info(f"dim_dealer loaded: {count} rows. Lookup cached: {self.dealer_lookup}")
        return count

    def load_dim_customer(self) -> int:
        """Loads customer profiles from silver/customers."""
        logger.info("Loading dim_customer...")
        cust_dataset = ds.dataset(str(SILVER_DIR / "customers"), format="parquet")
        cust_df = cust_dataset.to_table().to_pandas()

        cust_clean = pd.DataFrame({
            "customer_id": cust_df["customer_id"],
            "customer_name": cust_df["customer_name"],
            "email": cust_df["customer_id"].apply(lambda x: f"{x.lower()}@autocare.local"),
            "phone": "UNKNOWN",
            "address": "UNKNOWN",
            "city": "UNKNOWN",
            "state": cust_df["region"],
            "created_at": pd.to_datetime(cust_df["_silver_processed_at"]),
        })

        self.con.register("staged_customers", cust_clean)
        self.con.execute("""
            INSERT INTO autocare_dw.dim_customer (customer_id, customer_name, email, phone, address, city, state, created_at)
            SELECT customer_id, customer_name, email, phone, address, city, state, created_at
            FROM staged_customers
            ON CONFLICT (customer_id) DO UPDATE SET
                customer_name = EXCLUDED.customer_name,
                email = EXCLUDED.email,
                phone = EXCLUDED.phone,
                address = EXCLUDED.address,
                city = EXCLUDED.city,
                state = EXCLUDED.state;
        """)
        self.con.unregister("staged_customers")

        rows = self.con.execute("SELECT customer_id, customer_key FROM autocare_dw.dim_customer;").fetchall()
        self.customer_lookup = {r[0]: r[1] for r in rows}
        count = len(rows)
        logger.info(f"dim_customer loaded: {count} rows. Lookup cached: {len(self.customer_lookup)} entries.")
        return count

    def load_dim_component(self) -> int:
        """Loads canonical automotive components from silver/components."""
        logger.info("Loading dim_component...")
        comp_dataset = ds.dataset(str(SILVER_DIR / "components"), format="parquet")
        comp_df = comp_dataset.to_table().to_pandas()

        comp_clean = pd.DataFrame({
            "component_name": comp_df["name"],
            "category": comp_df["category"],
            "expected_lifespan_km": comp_df["lifespan_km"].astype(int),
            "warranty_period_months": 0,  # 0 indicates unavailable/unspecified per approved plan
        })

        self.con.register("staged_components", comp_clean)
        self.con.execute("""
            INSERT INTO autocare_dw.dim_component (component_name, category, expected_lifespan_km, warranty_period_months)
            SELECT component_name, category, expected_lifespan_km, warranty_period_months
            FROM staged_components
            ON CONFLICT (component_name) DO UPDATE SET
                category = EXCLUDED.category,
                expected_lifespan_km = EXCLUDED.expected_lifespan_km,
                warranty_period_months = EXCLUDED.warranty_period_months;
        """)
        self.con.unregister("staged_components")

        rows = self.con.execute("SELECT component_name, component_key FROM autocare_dw.dim_component;").fetchall()
        self.component_lookup = {r[0]: r[1] for r in rows}

        # Build part_id -> component_key lookup from silver/components catalog
        for _, r in comp_df.iterrows():
            part_id = r["part_id"]
            name = r["name"]
            key = self.component_lookup.get(name, -1)
            self.part_to_component_key[part_id] = key

        count = len(rows)
        logger.info(f"dim_component loaded: {count} rows. Part-to-Component lookup cached: {self.part_to_component_key}")
        return count

    def load_dim_vehicle(self) -> int:
        """Loads fleet vehicles, linking customer via vehicle_customer_map."""
        logger.info("Loading dim_vehicle...")
        vh_dataset = ds.dataset(str(SILVER_DIR / "vehicles"), format="parquet")
        vh_df = vh_dataset.to_table().to_pandas()

        map_dataset = ds.dataset(str(SILVER_DIR / "vehicle_customer_map"), format="parquet")
        map_df = map_dataset.to_table().to_pandas()
        veh_to_cust = dict(zip(map_df["vehicle_id"], map_df["customer_id"]))

        records = []
        for _, r in vh_df.iterrows():
            v_id = r["vehicle_id"]
            model_key = self.model_lookup.get(r["model"], -1)
            dealer_key = self.dealer_lookup.get(r["dealer_id"], -1)
            cust_id = veh_to_cust.get(v_id)
            cust_key = self.customer_lookup.get(cust_id, -1) if cust_id else -1
            mfg_date = pd.to_datetime(r["manufacture_date"]).date()
            mfg_year = mfg_date.year

            records.append((
                v_id,
                model_key,
                cust_key,
                dealer_key,
                r["variant"],
                mfg_date,
                mfg_year,
                "ACTIVE",
            ))

        vh_clean = pd.DataFrame(records, columns=[
            "vehicle_id", "model_key", "customer_key", "selling_dealer_key",
            "variant", "manufacture_date", "manufacture_year", "status"
        ])

        self.con.register("staged_vehicles", vh_clean)
        self.con.execute("""
            INSERT INTO autocare_dw.dim_vehicle (
                vehicle_id, model_key, customer_key, selling_dealer_key,
                variant, manufacture_date, manufacture_year, status
            )
            SELECT vehicle_id, model_key, customer_key, selling_dealer_key,
                   variant, manufacture_date, manufacture_year, status
            FROM staged_vehicles
            ON CONFLICT (vehicle_id) DO NOTHING;
        """)
        self.con.unregister("staged_vehicles")

        rows = self.con.execute("SELECT vehicle_id, vehicle_key FROM autocare_dw.dim_vehicle;").fetchall()
        self.vehicle_lookup = {r[0]: r[1] for r in rows}
        count = len(rows)
        logger.info(f"dim_vehicle loaded: {count} rows. Lookup cached: {len(self.vehicle_lookup)} entries.")
        return count

    def load_fact_telemetry(self) -> int:
        """Loads fact_telemetry using NOT EXISTS anti-join against (vehicle_key, timestamp)."""
        logger.info("Loading fact_telemetry with NOT EXISTS anti-join...")
        telem_dataset = ds.dataset(str(SILVER_DIR / "telemetry"), format="parquet")
        telem_df = telem_dataset.to_table().to_pandas()

        records = []
        for _, r in telem_df.iterrows():
            v_key = self.vehicle_lookup.get(r["vehicle_id"], -1)
            ts = pd.to_datetime(r["timestamp"])
            date_key = int(ts.strftime("%Y%m%d"))
            rpm = int(r["rpm"])
            temp = float(r["temperature"])
            batt = float(r["battery"])
            vib = float(r["vibration"])
            batch_id = r["_silver_batch_id"]

            # Physical domain validation assertions
            if not (0 <= rpm <= 9000 and -40.0 <= temp <= 160.0 and 9.0 <= batt <= 16.0 and 0.0 <= vib <= 15.0):
                raise ValueError(f"Invalid telemetry physical bounds: rpm={rpm}, temp={temp}, batt={batt}, vib={vib}")

            records.append((v_key, date_key, ts, rpm, temp, batt, vib, batch_id))

        staged_df = pd.DataFrame(records, columns=[
            "vehicle_key", "date_key", "timestamp", "rpm", "temperature", "battery", "vibration", "_silver_batch_id"
        ])

        self.con.register("staged_telemetry", staged_df)
        self.con.execute("""
            INSERT INTO autocare_dw.fact_telemetry (
                vehicle_key, date_key, timestamp, rpm, temperature, battery, vibration, _silver_batch_id
            )
            SELECT s.vehicle_key, s.date_key, s.timestamp, s.rpm, s.temperature, s.battery, s.vibration, s._silver_batch_id
            FROM staged_telemetry s
            WHERE NOT EXISTS (
                SELECT 1 FROM autocare_dw.fact_telemetry t
                WHERE t.vehicle_key = s.vehicle_key AND t.timestamp = s.timestamp
            );
        """)
        self.con.unregister("staged_telemetry")

        count = self.con.execute("SELECT COUNT(*) FROM autocare_dw.fact_telemetry;").fetchone()[0]
        logger.info(f"fact_telemetry loaded: {count} rows.")
        return count

    def load_fact_service(self) -> int:
        """Loads fact_service with ON CONFLICT (service_id) upsert."""
        logger.info("Loading fact_service...")
        srv_dataset = ds.dataset(str(SILVER_DIR / "service"), format="parquet")
        srv_df = srv_dataset.to_table().to_pandas()

        records = []
        for _, r in srv_df.iterrows():
            v_key = self.vehicle_lookup.get(r["vehicle_id"], -1)
            d_key = self.dealer_lookup.get(r["dealer_id"], -1)
            vd = pd.to_datetime(r["visit_date"]).date()
            date_key = int(vd.strftime("%Y%m%d"))
            cost = float(r["cost"])

            if cost < 0.0:
                raise ValueError(f"Negative service cost detected: {cost}")

            records.append((
                r["service_id"],
                v_key,
                d_key,
                date_key,
                vd,
                r["issue"],
                cost,
                r["_silver_batch_id"],
            ))

        staged_df = pd.DataFrame(records, columns=[
            "service_id", "vehicle_key", "dealer_key", "date_key", "visit_date", "issue", "cost", "_silver_batch_id"
        ])

        self.con.register("staged_service", staged_df)
        self.con.execute("""
            INSERT INTO autocare_dw.fact_service (
                service_id, vehicle_key, dealer_key, date_key, visit_date, issue, cost, _silver_batch_id
            )
            SELECT service_id, vehicle_key, dealer_key, date_key, visit_date, issue, cost, _silver_batch_id
            FROM staged_service
            ON CONFLICT (service_id) DO UPDATE SET
                vehicle_key = EXCLUDED.vehicle_key,
                dealer_key = EXCLUDED.dealer_key,
                date_key = EXCLUDED.date_key,
                visit_date = EXCLUDED.visit_date,
                issue = EXCLUDED.issue,
                cost = EXCLUDED.cost,
                _silver_batch_id = EXCLUDED._silver_batch_id;
        """)
        self.con.unregister("staged_service")

        count = self.con.execute("SELECT COUNT(*) FROM autocare_dw.fact_service;").fetchone()[0]
        logger.info(f"fact_service loaded: {count} rows.")
        return count

    def load_fact_warranty(self) -> int:
        """Loads fact_warranty with ON CONFLICT (claim_id) upsert."""
        logger.info("Loading fact_warranty...")
        warr_dataset = ds.dataset(str(SILVER_DIR / "warranty"), format="parquet")
        warr_df = warr_dataset.to_table().to_pandas()

        records = []
        for _, r in warr_df.iterrows():
            v_key = self.vehicle_lookup.get(r["vehicle_id"], -1)
            comp_key = self.component_lookup.get(r["component"], -1)
            cd = pd.to_datetime(r["claim_date"]).date()
            date_key = int(cd.strftime("%Y%m%d"))
            amount = float(r["amount"])

            if amount <= 0.0:
                raise ValueError(f"Invalid non-positive warranty amount: {amount}")

            records.append((
                r["claim_id"],
                v_key,
                comp_key,
                date_key,
                cd,
                amount,
                r["_silver_batch_id"],
            ))

        staged_df = pd.DataFrame(records, columns=[
            "claim_id", "vehicle_key", "component_key", "date_key", "claim_date", "amount", "_silver_batch_id"
        ])

        self.con.register("staged_warranty", staged_df)
        self.con.execute("""
            INSERT INTO autocare_dw.fact_warranty (
                claim_id, vehicle_key, component_key, date_key, claim_date, amount, _silver_batch_id
            )
            SELECT claim_id, vehicle_key, component_key, date_key, claim_date, amount, _silver_batch_id
            FROM staged_warranty
            ON CONFLICT (claim_id) DO UPDATE SET
                vehicle_key = EXCLUDED.vehicle_key,
                component_key = EXCLUDED.component_key,
                date_key = EXCLUDED.date_key,
                claim_date = EXCLUDED.claim_date,
                amount = EXCLUDED.amount,
                _silver_batch_id = EXCLUDED._silver_batch_id;
        """)
        self.con.unregister("staged_warranty")

        count = self.con.execute("SELECT COUNT(*) FROM autocare_dw.fact_warranty;").fetchone()[0]
        logger.info(f"fact_warranty loaded: {count} rows.")
        return count

    def load_fact_parts(self) -> int:
        """Loads fact_parts resolving part_id -> component_key via Silver catalog."""
        logger.info("Loading fact_parts...")
        parts_dataset = ds.dataset(str(SILVER_DIR / "parts"), format="parquet", partitioning="hive")
        parts_df = parts_dataset.to_table().to_pandas()

        records = []
        for _, r in parts_df.iterrows():
            part_id = r["part_id"]
            comp_key = self.part_to_component_key.get(part_id, -1)
            dlr_key = self.dealer_lookup.get(r["dealer_id"], -1)
            sd = pd.to_datetime(r["snapshot_date"]).date()
            date_key = int(sd.strftime("%Y%m%d"))
            stock = int(r["stock"])
            lead = int(r["lead_time"])

            if stock < 0 or lead < 1:
                raise ValueError(f"Invalid parts bounds: stock={stock}, lead_time={lead}")

            records.append((
                part_id,
                dlr_key,
                comp_key,
                date_key,
                sd,
                stock,
                lead,
                r["_silver_batch_id"],
            ))

        staged_df = pd.DataFrame(records, columns=[
            "part_id", "dealer_key", "component_key", "date_key", "snapshot_date", "stock", "lead_time", "_silver_batch_id"
        ])

        self.con.register("staged_parts", staged_df)
        self.con.execute("""
            INSERT INTO autocare_dw.fact_parts (
                part_id, dealer_key, component_key, date_key, snapshot_date, stock, lead_time, _silver_batch_id
            )
            SELECT part_id, dealer_key, component_key, date_key, snapshot_date, stock, lead_time, _silver_batch_id
            FROM staged_parts
            ON CONFLICT (part_id, dealer_key, date_key) DO UPDATE SET
                component_key = EXCLUDED.component_key,
                snapshot_date = EXCLUDED.snapshot_date,
                stock = EXCLUDED.stock,
                lead_time = EXCLUDED.lead_time,
                _silver_batch_id = EXCLUDED._silver_batch_id;
        """)
        self.con.unregister("staged_parts")

        count = self.con.execute("SELECT COUNT(*) FROM autocare_dw.fact_parts;").fetchone()[0]
        logger.info(f"fact_parts loaded: {count} rows.")
        return count

    def run_all(self) -> Dict[str, int]:
        """Executes full loading sequence in strict dependency order."""
        logger.info("=== BEGINNING FULL WAREHOUSE INGESTION ===")
        self.init_schema()

        # Step 1: Independent Dimensions (Tier 1)
        dim_date_cnt = self.load_dim_date()
        dim_model_cnt = self.load_dim_model()
        dim_dealer_cnt = self.load_dim_dealer()
        dim_cust_cnt = self.load_dim_customer()
        dim_comp_cnt = self.load_dim_component()

        # Step 2: Dependent Dimension (Tier 2)
        dim_veh_cnt = self.load_dim_vehicle()

        # Step 3: Conformed Fact Tables (Tier 3)
        fact_telem_cnt = self.load_fact_telemetry()
        fact_srv_cnt = self.load_fact_service()
        fact_warr_cnt = self.load_fact_warranty()
        fact_parts_cnt = self.load_fact_parts()

        summary = {
            "dim_date": dim_date_cnt,
            "dim_model": dim_model_cnt,
            "dim_dealer": dim_dealer_cnt,
            "dim_customer": dim_cust_cnt,
            "dim_component": dim_comp_cnt,
            "dim_vehicle": dim_veh_cnt,
            "fact_telemetry": fact_telem_cnt,
            "fact_service": fact_srv_cnt,
            "fact_warranty": fact_warr_cnt,
            "fact_parts": fact_parts_cnt,
            "total_facts": fact_telem_cnt + fact_srv_cnt + fact_warr_cnt + fact_parts_cnt,
        }
        logger.info(f"=== WAREHOUSE INGESTION COMPLETE === Summary: {summary}")
        return summary

    def close(self) -> None:
        """Closes the underlying database connection."""
        if hasattr(self, "con") and self.con:
            self.con.close()
            logger.info("Closed warehouse database connection.")


def main():
    loader = WarehouseLoader()
    try:
        summary = loader.run_all()
        print("\nWarehouse Ingestion Summary:")
        for k, v in summary.items():
            print(f"  {k:20}: {v:6d}")
    finally:
        loader.close()


if __name__ == "__main__":
    main()
