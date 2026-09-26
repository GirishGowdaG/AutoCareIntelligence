"""Tests for Phase 2C Data Warehouse DDL and Dimensional Star Schema.

Authoritative Reference: AutoCare_Intelligence.pdf (Section 4 & Section 7).
Verifies:
- Exact table inventory: exactly 6 dimensions and exactly 4 facts (10 tables total).
- Absolute absence of unapproved tables (dim_part, fact_diagnostics_events).
- Primary keys, foreign keys, unique constraints, and check constraints.
- fact_parts grain, SKU integrity, and business uniqueness constraint.
- Unknown dimension member (-1) seed statements.
- Index definitions on foreign keys and natural lookup keys.
"""

from pathlib import Path
import re
import pytest
import sqlglot
from sqlglot import exp

DDL_DIR = Path("sql/ddl")

REQUIRED_DIMENSIONS = {
    "dim_date",
    "dim_model",
    "dim_dealer",
    "dim_customer",
    "dim_component",
    "dim_vehicle",
}

REQUIRED_FACTS = {
    "fact_telemetry",
    "fact_service",
    "fact_warranty",
    "fact_parts",
}

FORBIDDEN_TABLES = {
    "dim_part",
    "fact_diagnostics_events",
    "fact_diagnostics",
    "dim_parts",
}


def read_ddl_file(filename: str) -> str:
    path = DDL_DIR / filename
    assert path.exists(), f"DDL file {filename} does not exist at {path}"
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def get_all_create_tables():
    """Parses all DDL files and extracts all CREATE TABLE expressions."""
    tables = {}
    for filename in ["01_dimensions.sql", "02_facts.sql"]:
        sql = read_ddl_file(filename)
        statements = sqlglot.parse(sql, read="postgres")
        for stmt in statements:
            if isinstance(stmt, exp.Create) and stmt.args.get("kind") == "TABLE":
                table_name = stmt.this.this.name
                tables[table_name] = stmt
    return tables


def test_ddl_files_exist():
    """Verify all 4 required DDL files exist in sql/ddl/."""
    expected_files = [
        "00_schema.sql",
        "01_dimensions.sql",
        "02_facts.sql",
        "03_indexes.sql",
    ]
    for fname in expected_files:
        p = DDL_DIR / fname
        assert p.is_file(), f"Missing required DDL file: {fname}"


def test_schema_definition():
    """Verify 00_schema.sql defines autocare_dw schema."""
    sql = read_ddl_file("00_schema.sql")
    statements = sqlglot.parse(sql, read="postgres")
    assert len(statements) >= 1
    create_schema_found = any(
        isinstance(s, exp.Create) and s.args.get("kind") == "SCHEMA"
        for s in statements
    )
    assert create_schema_found, "00_schema.sql must contain CREATE SCHEMA IF NOT EXISTS autocare_dw"


def test_table_inventory_and_counts():
    """Verify exactly 6 dimensions and exactly 4 facts (10 tables total)."""
    tables = get_all_create_tables()
    table_names = set(tables.keys())

    assert len(table_names) == 10, f"Expected exactly 10 tables, found {len(table_names)}: {table_names}"

    dimensions = table_names.intersection(REQUIRED_DIMENSIONS)
    facts = table_names.intersection(REQUIRED_FACTS)

    assert dimensions == REQUIRED_DIMENSIONS, f"Missing or unexpected dimensions. Found: {dimensions}"
    assert facts == REQUIRED_FACTS, f"Missing or unexpected facts. Found: {facts}"
    assert len(dimensions) == 6, f"Expected exactly 6 dimensions, got {len(dimensions)}"
    assert len(facts) == 4, f"Expected exactly 4 facts, got {len(facts)}"


def test_forbidden_tables_absent():
    """Verify dim_part and fact_diagnostics_events are strictly NOT defined."""
    tables = get_all_create_tables()
    for forbidden in FORBIDDEN_TABLES:
        assert forbidden not in tables, f"Forbidden table '{forbidden}' must NOT be created in DDL"


def test_primary_keys_defined():
    """Verify every table has a defined primary key."""
    dim_sql = read_ddl_file("01_dimensions.sql")
    fact_sql = read_ddl_file("02_facts.sql")
    combined = dim_sql + "\n" + fact_sql

    expected_pks = {
        "dim_date": "date_key",
        "dim_model": "model_key",
        "dim_dealer": "dealer_key",
        "dim_customer": "customer_key",
        "dim_component": "component_key",
        "dim_vehicle": "vehicle_key",
        "fact_telemetry": "telemetry_fact_id",
        "fact_service": "service_fact_id",
        "fact_warranty": "warranty_fact_id",
        "fact_parts": "parts_fact_id",
    }

    for table, pk in expected_pks.items():
        pattern = rf"{pk}\s+[\w\(\)]+.*PRIMARY KEY"
        assert re.search(pattern, combined, re.IGNORECASE), f"Table {table} must define PRIMARY KEY on {pk}"


def test_natural_key_uniqueness():
    """Verify natural keys have UNIQUE constraints."""
    dim_sql = read_ddl_file("01_dimensions.sql")
    fact_sql = read_ddl_file("02_facts.sql")
    combined = dim_sql + "\n" + fact_sql

    expected_uniques = [
        ("dim_date", "calendar_date"),
        ("dim_model", "model_name"),
        ("dim_dealer", "dealer_id"),
        ("dim_customer", "customer_id"),
        ("dim_component", "component_name"),
        ("dim_vehicle", "vehicle_id"),
        ("fact_service", "service_id"),
        ("fact_warranty", "claim_id"),
    ]

    for table, col in expected_uniques:
        pattern = rf"{col}\s+[\w\(\)]+.*UNIQUE"
        assert re.search(pattern, combined, re.IGNORECASE), f"Column {col} in {table} must be UNIQUE"


def test_foreign_key_constraints():
    """Verify approved foreign key relationships are strictly declared."""
    dim_sql = read_ddl_file("01_dimensions.sql")
    fact_sql = read_ddl_file("02_facts.sql")

    # dim_vehicle FKs
    assert "REFERENCES autocare_dw.dim_model(model_key)" in dim_sql
    assert "REFERENCES autocare_dw.dim_customer(customer_key)" in dim_sql
    assert "REFERENCES autocare_dw.dim_dealer(dealer_key)" in dim_sql

    # fact_telemetry FKs
    assert "REFERENCES autocare_dw.dim_vehicle(vehicle_key)" in fact_sql
    assert "REFERENCES autocare_dw.dim_date(date_key)" in fact_sql

    # fact_service FKs
    assert "REFERENCES autocare_dw.dim_dealer(dealer_key)" in fact_sql

    # fact_warranty FKs
    assert "REFERENCES autocare_dw.dim_component(component_key)" in fact_sql

    # fact_parts FKs
    assert "dealer_key INT NOT NULL REFERENCES autocare_dw.dim_dealer(dealer_key)" in fact_sql
    assert "component_key INT NOT NULL REFERENCES autocare_dw.dim_component(component_key)" in fact_sql
    assert "date_key INT NOT NULL REFERENCES autocare_dw.dim_date(date_key)" in fact_sql

    # ON DELETE RESTRICT enforcement and NO ON UPDATE CASCADE
    assert "ON UPDATE CASCADE" not in dim_sql, "ON UPDATE CASCADE is prohibited per governance"
    assert "ON UPDATE CASCADE" not in fact_sql, "ON UPDATE CASCADE is prohibited per governance"
    assert "ON DELETE RESTRICT" in dim_sql
    assert "ON DELETE RESTRICT" in fact_sql


def test_fact_parts_design():
    """Verify fact_parts satisfies all approved targeted design specifications."""
    fact_sql = read_ddl_file("02_facts.sql")

    # 1. Atomic SKU part_id retained
    assert "part_id VARCHAR(32) NOT NULL" in fact_sql

    # 2. Foreign keys to dim_dealer, dim_component, dim_date
    assert "dealer_key INT NOT NULL REFERENCES autocare_dw.dim_dealer(dealer_key)" in fact_sql
    assert "component_key INT NOT NULL REFERENCES autocare_dw.dim_component(component_key)" in fact_sql
    assert "date_key INT NOT NULL REFERENCES autocare_dw.dim_date(date_key)" in fact_sql

    # 3. Snapshot date degenerate column
    assert "snapshot_date DATE NOT NULL" in fact_sql

    # 4. Measures stock and lead_time with CHECK bounds
    assert "stock INT NOT NULL CHECK (stock >= 0)" in fact_sql
    assert "lead_time INT NOT NULL CHECK (lead_time >= 1)" in fact_sql

    # 5. Composite business uniqueness constraint
    assert "CONSTRAINT uq_fact_parts_snapshot UNIQUE (part_id, dealer_key, date_key)" in fact_sql

    # 6. Does NOT reference any dim_part table
    assert "dim_part" not in fact_sql


def test_check_constraints():
    """Verify physical and business domain check constraints in facts and dimensions."""
    dim_sql = read_ddl_file("01_dimensions.sql")
    fact_sql = read_ddl_file("02_facts.sql")

    # Dimensions
    assert "CHECK (day_of_week BETWEEN 1 AND 7)" in dim_sql
    assert "CHECK (month_number BETWEEN 1 AND 12)" in dim_sql
    assert "CHECK (quarter BETWEEN 1 AND 4)" in dim_sql
    assert "CHECK (fuel_capacity_or_kwh >= 0.0)" in dim_sql
    assert "CHECK (expected_lifespan_km >= 0)" in dim_sql
    assert "CHECK (manufacture_year >= 1900)" in dim_sql

    # Facts
    assert "CHECK (rpm >= 0 AND rpm <= 9000)" in fact_sql
    assert "CHECK (temperature >= -40.0 AND temperature <= 160.0)" in fact_sql
    assert "CHECK (battery >= 9.0 AND battery <= 16.0)" in fact_sql
    assert "CHECK (vibration >= 0.0 AND vibration <= 15.0)" in fact_sql
    assert "CHECK (cost >= 0.00)" in fact_sql
    assert "CHECK (amount > 0.00)" in fact_sql


def test_unknown_dimension_members_seeded():
    """Verify all 6 dimensions have seed statements for unknown member -1."""
    dim_sql = read_ddl_file("01_dimensions.sql")

    for dim in REQUIRED_DIMENSIONS:
        assert f"INSERT INTO autocare_dw.{dim}" in dim_sql, f"Missing unknown member insert for {dim}"
        assert "VALUES (\n    -1," in dim_sql or "VALUES (-1," in dim_sql or "(-1," in dim_sql, (
            f"Expected key -1 in seed insert for {dim}"
        )


def test_indexes_defined():
    """Verify 03_indexes.sql defines required foreign key and lookup indexes."""
    idx_sql = read_ddl_file("03_indexes.sql")

    expected_indexes = [
        "idx_dim_model_name",
        "idx_dim_dealer_id",
        "idx_dim_customer_id",
        "idx_dim_component_name",
        "idx_dim_vehicle_id",
        "idx_dim_vehicle_model",
        "idx_dim_vehicle_customer",
        "idx_dim_vehicle_dealer",
        "idx_fact_telemetry_vehicle_ts",
        "idx_fact_telemetry_date",
        "idx_fact_service_vehicle",
        "idx_fact_service_dealer",
        "idx_fact_service_date",
        "idx_fact_warranty_vehicle",
        "idx_fact_warranty_component",
        "idx_fact_warranty_date",
        "idx_fact_parts_dealer",
        "idx_fact_parts_component",
        "idx_fact_parts_date",
        "idx_fact_parts_part_id",
    ]

    for idx in expected_indexes:
        assert idx in idx_sql, f"Index {idx} must be defined in 03_indexes.sql"
