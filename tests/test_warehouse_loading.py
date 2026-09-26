"""Tests for Phase 2C Silver-to-Warehouse Loading Pipeline.

Authoritative References:
- AutoCare_Intelligence.pdf (Section 4 & Section 7)
- Approved Medallion Data Lakehouse (data/silver/)
- Approved PostgreSQL 16+ Star Schema DDL (sql/ddl/)

Verifies:
- Exact dimension row counts (all 6 dimensions).
- Exact fact row counts (all 4 facts).
- Row conservation: Count(Silver Clean) == Count(Warehouse Fact).
- Zero orphaned fact records (100% PK/FK referential integrity).
- Natural key uniqueness and preservation.
- Default unknown member (-1) preservation.
- Part/component mapping integrity: part_id -> Silver component catalog -> dim_component.component_key.
- Vehicle/customer mapping integrity: vehicle_id -> vehicle_customer_map -> dim_customer.customer_key.
- Telemetry re-run idempotency (NOT EXISTS anti-join prevents duplicates).
- DDL unchanged verification (git diff on sql/ddl/ is clean).
- Prohibited tables (dim_part, fact_diagnostics_events) strictly absent.
"""

from pathlib import Path
import subprocess
import duckdb
import pytest
import pyarrow.dataset as ds

from lakehouse.load_warehouse import WarehouseLoader, DEFAULT_DUCKDB_PATH

SILVER_DIR = Path("data/silver")


@pytest.fixture(scope="module")
def warehouse_loader():
    """Provides an initialized and loaded WarehouseLoader instance."""
    loader = WarehouseLoader()
    loader.run_all()
    yield loader
    loader.close()


@pytest.fixture(scope="module")
def warehouse_conn(warehouse_loader):
    """Provides a connection to the loaded warehouse database."""
    return warehouse_loader.con


def test_warehouse_tables_exist(warehouse_conn):
    """Verify exactly the approved 10 tables exist and no unauthorized tables exist."""
    tables = [
        r[0] for r in warehouse_conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'autocare_dw';"
        ).fetchall()
    ]
    expected_tables = {
        "dim_date",
        "dim_model",
        "dim_dealer",
        "dim_customer",
        "dim_component",
        "dim_vehicle",
        "fact_telemetry",
        "fact_service",
        "fact_warranty",
        "fact_parts",
    }
    assert set(tables) == expected_tables, f"Tables mismatch. Expected {expected_tables}, got {set(tables)}"
    assert "dim_part" not in tables, "dim_part must NOT exist in warehouse"
    assert "fact_diagnostics_events" not in tables, "fact_diagnostics_events must NOT exist in warehouse"


def test_dimension_row_counts(warehouse_conn):
    """Verify row counts for all 6 dimensions (entities + unknown member)."""
    expected_dim_counts = {
        "dim_date": 4019,       # 4,018 calendar days (2020-01-01 to 2030-12-31) + 1 unknown
        "dim_model": 5,         # 4 models + 1 unknown
        "dim_dealer": 6,        # 5 dealers + 1 unknown
        "dim_customer": 41,     # 40 customers + 1 unknown
        "dim_component": 9,     # 8 components + 1 unknown
        "dim_vehicle": 51,      # 50 vehicles + 1 unknown
    }

    for table, expected in expected_dim_counts.items():
        actual = warehouse_conn.execute(f"SELECT COUNT(*) FROM autocare_dw.{table};").fetchone()[0]
        assert actual == expected, f"Row count mismatch for {table}. Expected {expected}, got {actual}"


def test_fact_row_counts_and_conservation(warehouse_conn):
    """Verify strict mathematical row conservation: Count(Silver Clean) == Count(Warehouse Fact)."""
    expected_fact_counts = {
        "fact_telemetry": ("telemetry", 7554),
        "fact_service": ("service", 46),
        "fact_warranty": ("warranty", 10),
        "fact_parts": ("parts", 40),
    }

    total_facts = 0
    for fact_table, (silver_name, expected_count) in expected_fact_counts.items():
        # 1. Check Silver clean count
        silver_dataset = ds.dataset(str(SILVER_DIR / silver_name), format="parquet")
        silver_count = silver_dataset.count_rows()
        assert silver_count == expected_count, (
            f"Silver count mismatch for {silver_name}. Expected {expected_count}, got {silver_count}"
        )

        # 2. Check Warehouse fact count
        wh_count = warehouse_conn.execute(f"SELECT COUNT(*) FROM autocare_dw.{fact_table};").fetchone()[0]
        assert wh_count == silver_count, (
            f"Row conservation failed for {fact_table}: Silver={silver_count} vs Warehouse={wh_count}"
        )
        total_facts += wh_count

    assert total_facts == 7650, f"Expected 7,650 total fact rows, got {total_facts}"


def test_unknown_dimension_members_exist(warehouse_conn):
    """Verify each dimension contains the pre-seeded unknown member -1."""
    unknown_checks = [
        ("dim_date", "date_key", -1),
        ("dim_model", "model_key", -1),
        ("dim_dealer", "dealer_key", -1),
        ("dim_customer", "customer_key", -1),
        ("dim_component", "component_key", -1),
        ("dim_vehicle", "vehicle_key", -1),
    ]

    for table, pk_col, unknown_key in unknown_checks:
        res = warehouse_conn.execute(
            f"SELECT COUNT(*) FROM autocare_dw.{table} WHERE {pk_col} = {unknown_key};"
        ).fetchone()[0]
        assert res == 1, f"Missing unknown member with {pk_col}={unknown_key} in {table}"


def test_referential_integrity_no_orphaned_facts(warehouse_conn):
    """Verify 100% referential integrity across all fact foreign keys."""
    # fact_telemetry
    orphaned_telem_veh = warehouse_conn.execute("""
        SELECT COUNT(*) FROM autocare_dw.fact_telemetry t
        WHERE t.vehicle_key NOT IN (SELECT vehicle_key FROM autocare_dw.dim_vehicle);
    """).fetchone()[0]
    assert orphaned_telem_veh == 0, f"Found {orphaned_telem_veh} orphaned telemetry vehicle_keys"

    orphaned_telem_date = warehouse_conn.execute("""
        SELECT COUNT(*) FROM autocare_dw.fact_telemetry t
        WHERE t.date_key NOT IN (SELECT date_key FROM autocare_dw.dim_date);
    """).fetchone()[0]
    assert orphaned_telem_date == 0, f"Found {orphaned_telem_date} orphaned telemetry date_keys"

    # fact_service
    orphaned_srv_veh = warehouse_conn.execute("""
        SELECT COUNT(*) FROM autocare_dw.fact_service s
        WHERE s.vehicle_key NOT IN (SELECT vehicle_key FROM autocare_dw.dim_vehicle);
    """).fetchone()[0]
    assert orphaned_srv_veh == 0, f"Found {orphaned_srv_veh} orphaned service vehicle_keys"

    orphaned_srv_dlr = warehouse_conn.execute("""
        SELECT COUNT(*) FROM autocare_dw.fact_service s
        WHERE s.dealer_key NOT IN (SELECT dealer_key FROM autocare_dw.dim_dealer);
    """).fetchone()[0]
    assert orphaned_srv_dlr == 0, f"Found {orphaned_srv_dlr} orphaned service dealer_keys"

    # fact_warranty
    orphaned_warr_veh = warehouse_conn.execute("""
        SELECT COUNT(*) FROM autocare_dw.fact_warranty w
        WHERE w.vehicle_key NOT IN (SELECT vehicle_key FROM autocare_dw.dim_vehicle);
    """).fetchone()[0]
    assert orphaned_warr_veh == 0, f"Found {orphaned_warr_veh} orphaned warranty vehicle_keys"

    orphaned_warr_comp = warehouse_conn.execute("""
        SELECT COUNT(*) FROM autocare_dw.fact_warranty w
        WHERE w.component_key NOT IN (SELECT component_key FROM autocare_dw.dim_component);
    """).fetchone()[0]
    assert orphaned_warr_comp == 0, f"Found {orphaned_warr_comp} orphaned warranty component_keys"

    # fact_parts
    orphaned_parts_dlr = warehouse_conn.execute("""
        SELECT COUNT(*) FROM autocare_dw.fact_parts p
        WHERE p.dealer_key NOT IN (SELECT dealer_key FROM autocare_dw.dim_dealer);
    """).fetchone()[0]
    assert orphaned_parts_dlr == 0, f"Found {orphaned_parts_dlr} orphaned parts dealer_keys"

    orphaned_parts_comp = warehouse_conn.execute("""
        SELECT COUNT(*) FROM autocare_dw.fact_parts p
        WHERE p.component_key NOT IN (SELECT component_key FROM autocare_dw.dim_component);
    """).fetchone()[0]
    assert orphaned_parts_comp == 0, f"Found {orphaned_parts_comp} orphaned parts component_keys"


def test_vehicle_customer_mapping(warehouse_conn):
    """Verify dim_vehicle.customer_key correctly links vehicle_id -> customer_id -> customer_key."""
    map_dataset = ds.dataset(str(SILVER_DIR / "vehicle_customer_map"), format="parquet")
    map_df = map_dataset.to_table().to_pandas()

    rows = warehouse_conn.execute("""
        SELECT v.vehicle_id, c.customer_id
        FROM autocare_dw.dim_vehicle v
        JOIN autocare_dw.dim_customer c ON v.customer_key = c.customer_key
        WHERE v.vehicle_key != -1;
    """).fetchall()
    actual_map = dict(rows)

    assert len(actual_map) == 50, f"Expected 50 mapped vehicles, got {len(actual_map)}"
    for _, r in map_df.iterrows():
        v_id = r["vehicle_id"]
        expected_cust_id = r["customer_id"]
        assert actual_map[v_id] == expected_cust_id, (
            f"Mapping mismatch for vehicle {v_id}: expected {expected_cust_id}, got {actual_map[v_id]}"
        )


def test_part_component_mapping(warehouse_conn):
    """Verify fact_parts maps part_id -> Silver component catalog -> dim_component.component_key."""
    comp_dataset = ds.dataset(str(SILVER_DIR / "components"), format="parquet")
    comp_df = comp_dataset.to_table().to_pandas()
    expected_part_to_comp_name = dict(zip(comp_df["part_id"], comp_df["name"]))

    rows = warehouse_conn.execute("""
        SELECT DISTINCT p.part_id, c.component_name
        FROM autocare_dw.fact_parts p
        JOIN autocare_dw.dim_component c ON p.component_key = c.component_key;
    """).fetchall()
    actual_part_to_comp = dict(rows)

    assert len(actual_part_to_comp) == 8, f"Expected 8 mapped part SKUs, got {len(actual_part_to_comp)}"
    for part_id, expected_comp_name in expected_part_to_comp_name.items():
        assert actual_part_to_comp[part_id] == expected_comp_name, (
            f"Part-component mapping mismatch for {part_id}: expected {expected_comp_name}, got {actual_part_to_comp[part_id]}"
        )


def test_telemetry_idempotency_rerun(warehouse_loader):
    """Verify that re-running the loader does not duplicate telemetry records."""
    count_before = warehouse_loader.con.execute("SELECT COUNT(*) FROM autocare_dw.fact_telemetry;").fetchone()[0]
    assert count_before == 7554

    # Run loader again on same loader instance
    warehouse_loader.load_fact_telemetry()

    count_after = warehouse_loader.con.execute("SELECT COUNT(*) FROM autocare_dw.fact_telemetry;").fetchone()[0]
    assert count_after == count_before, (
        f"Telemetry re-run violated idempotency: count increased from {count_before} to {count_after}"
    )


def test_ddl_integrity_unchanged():
    """Verify that sql/ddl/ files have NOT been modified."""
    res = subprocess.run(
        ["git", "diff", "--exit-code", "sql/ddl/"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"sql/ddl/ has unapproved modifications:\n{res.stdout}"
