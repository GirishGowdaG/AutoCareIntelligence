"""Automated Verification & Benchmark Test Suite for the Isolated scale_100k Dataset Profile.

Verifies:
  1. Path-isolation guardrails preventing accidental writes to data/raw, data/bronze, data/silver, data/warehouse.
  2. Exact target record counts (120,950 total across 10 CSVs).
  3. Exact canonical CSV column headers (zero invented or altered columns).
  4. Primary key uniqueness and foreign key referential integrity.
  5. Chronological ordering and date window invariants.
  6. Physical & semantic invariants (sensor bounds, DTC catalog, anomaly coupling, warranty-service linkage).
  7. Bronze Parquet row conservation (120,950 rows).
  8. Silver Clean row conservation (120,950 Clean rows, 0 Quarantine rows on clean data).
  9. Isolated fault-injection tests (DUPLICATE_KEY and boundary rule quarantine + raw value preservation).
 10. Deterministic seed reproducibility.
 11. Baseline data/raw SHA-256 hash and row-count (9,286) preservation.
"""

import os
import csv
import json
import hashlib
from pathlib import Path
from datetime import datetime

import pytest
import psycopg2
import pyarrow as pa
import pyarrow.dataset as ds

_ORIG_PSYCOPG2_CONNECT = psycopg2.connect


def pytest_configure(config):
    """If AUTOCARE_DB_PORT is set, route hardcoded port=5432 test connections to AUTOCARE_DB_PORT."""
    env_port = os.environ.get("AUTOCARE_DB_PORT")
    if env_port and str(env_port) != "5432":
        def _patched_connect(*args, **kwargs):
            if kwargs.get("port") == 5432:
                kwargs["port"] = int(env_port)
            return _ORIG_PSYCOPG2_CONNECT(*args, **kwargs)
        psycopg2.connect = _patched_connect

from data_generator.config import (
    DEALERS as BASELINE_DEALERS,
    COMPONENTS as BASELINE_COMPONENTS,
    DTC_CATALOG,
)
from data_generator.scale_100k_runner import (
    PROJECT_ROOT,
    TARGET_COUNTS,
    EXPECTED_TOTAL_ROWS,
    validate_isolated_path,
    generate_scale_100k_raw,
    run_scale_100k_pipeline,
)
from lakehouse.bronze_ingest import run_bronze_ingestion
from lakehouse.silver_clean import run_silver_cleaning, DEDUPLICATION_KEYS

SCALE_BASE_DIR = PROJECT_ROOT / "data" / "scale_100k"
SCALE_RAW_DIR = SCALE_BASE_DIR / "raw"
SCALE_BRONZE_DIR = SCALE_BASE_DIR / "bronze"
SCALE_SILVER_DIR = SCALE_BASE_DIR / "silver"
SCALE_QUARANTINE_DIR = SCALE_SILVER_DIR / "quarantine"
BASELINE_RAW_DIR = PROJECT_ROOT / "data" / "raw"

EXPECTED_BASELINE_RAW = {
    "components.csv": (8, "c5415f69b94a44597216b87666d139854ee300eeb805a522350184bb3c674384"),
    "customers.csv": (40, "e194c7bc248cd43078519dd08d7791305ca3445134fa54aed770b0f4060807d6"),
    "dealers.csv": (5, "48d53c13fa804e65b37b6ade44da0ad193e06360da435256413d98adf9dcfb98"),
    "diagnostics.csv": (1483, "295faec46a2b7209807dc9c20aa999dd0ef5f23b447cf85cad5b3b514f0d781b"),
    "parts.csv": (40, "626b114e8cfde762795b2fb16d0c5760ba159bb34788ef32846eb95ec9a14c6e"),
    "service.csv": (46, "9009542cee726d3b779184e1a68776ad856b27dcd67c3d126dc6a20ce1928362"),
    "telemetry.csv": (7554, "c3712bd86f6010f24c2e353cd18deee9d507200dffde8c1e599e00f6cc6f9d2d"),
    "vehicle_customer_map.csv": (50, "73a40c168e415c23ae16d8ea3582ba33d1edb7a6c39a654c89a2214786d778e6"),
    "vehicles.csv": (50, "de7b1ecf75d4623eadeac90cac4bd6fb6f07e16db8c7a1368b319fbcea1f13d0"),
    "warranty.csv": (10, "0e04e5f2fea50856b938be8495f1dc6df8a6a59e3b8fa3475fd2555cf915e23a"),
}

EXPECTED_HEADERS = {
    "vehicles": ["vehicle_id", "model", "variant", "manufacture_date", "dealer_id"],
    "customers": ["customer_id", "customer_name", "segment", "region"],
    "vehicle_customer_map": ["vehicle_id", "customer_id", "registration_date"],
    "dealers": ["dealer_id", "name", "region", "city", "bays"],
    "components": ["part_id", "name", "category", "lifespan_km", "base_cost", "lead_time_days"],
    "parts": ["part_id", "dealer_id", "stock", "lead_time"],
    "telemetry": ["vehicle_id", "timestamp", "rpm", "temperature", "battery", "vibration"],
    "diagnostics": ["vehicle_id", "timestamp", "code", "component", "severity"],
    "service": ["service_id", "vehicle_id", "dealer_id", "visit_date", "issue", "cost"],
    "warranty": ["claim_id", "vehicle_id", "component", "claim_date", "amount"],
}

CANONICAL_CATEGORIES = {
    "Powertrain",
    "Cooling System",
    "Electrical",
    "Braking",
    "Chassis",
    "Sensors",
}


@pytest.fixture(scope="module", autouse=True)
def ensure_scale_100k_generated():
    """Ensures data/scale_100k/{raw,bronze,silver} exists before running scale tests."""
    manifest_file = SCALE_BASE_DIR / "_scale_100k_benchmark.json"
    if not manifest_file.exists() or not (SCALE_RAW_DIR / "telemetry.csv").exists():
        run_scale_100k_pipeline(base_dir=str(SCALE_BASE_DIR), seed=42, end_date_str="2026-09-25")


def _read_scale_csv(dataset_name: str):
    fpath = SCALE_RAW_DIR / f"{dataset_name}.csv"
    assert fpath.exists(), f"Missing scale_100k CSV: {fpath}"
    with open(fpath, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader), list(reader.fieldnames or [])


def test_path_isolation_guards():
    """Verify hard path guards block writing to protected baseline directories."""
    for protected in ("data/raw", "data/bronze", "data/silver", "data/warehouse", "data/raw/sub"):
        with pytest.raises(ValueError, match="Path safety violation"):
            validate_isolated_path(str(PROJECT_ROOT / protected))

    # Valid isolated path succeeds
    valid = validate_isolated_path(str(SCALE_RAW_DIR))
    assert valid == SCALE_RAW_DIR.resolve()


def test_exact_target_row_counts_and_headers():
    """Verify exact 120,950 record distribution and 100% canonical CSV headers."""
    total_rows = 0
    for ds_name, expected_count in TARGET_COUNTS.items():
        rows, headers = _read_scale_csv(ds_name)
        assert headers == EXPECTED_HEADERS[ds_name], (
            f"Header mismatch for {ds_name}: got {headers}, expected {EXPECTED_HEADERS[ds_name]}"
        )
        assert len(rows) == expected_count, (
            f"Row count mismatch for {ds_name}: got {len(rows)}, expected {expected_count}"
        )
        total_rows += len(rows)

    assert total_rows == EXPECTED_TOTAL_ROWS == 120950


def test_primary_key_uniqueness_and_referential_integrity():
    """Verify all primary/deduplication keys are unique and all foreign keys resolve."""
    datasets = {ds_name: _read_scale_csv(ds_name)[0] for ds_name in TARGET_COUNTS}

    # 1. Verify zero duplicate business keys across all 10 datasets
    for ds_name, key_cols in DEDUPLICATION_KEYS.items():
        rows = datasets[ds_name]
        keys = [tuple(r[k] for k in key_cols) for r in rows]
        assert len(keys) == len(set(keys)), f"Duplicate business keys found in {ds_name}"

    # 2. Verify components have unique names as well as unique part_ids
    comp_names = [c["name"] for c in datasets["components"]]
    assert len(comp_names) == len(set(comp_names)) == 50

    # 3. Verify baseline 8 components and 5 dealers are preserved intact
    by_part_id = {c["part_id"]: c for c in datasets["components"]}
    for base_c in BASELINE_COMPONENTS:
        assert base_c["part_id"] in by_part_id
        assert by_part_id[base_c["part_id"]]["name"] == base_c["name"]
        assert by_part_id[base_c["part_id"]]["category"] == base_c["category"]

    for c in datasets["components"]:
        assert c["part_id"].startswith("PRT-")
        assert c["category"] in CANONICAL_CATEGORIES

    by_dealer_id = {d["dealer_id"]: d for d in datasets["dealers"]}
    for base_d in BASELINE_DEALERS:
        assert base_d["dealer_id"] in by_dealer_id
        assert by_dealer_id[base_d["dealer_id"]]["name"] == base_d["name"]

    # 4. Foreign Key Referential Integrity
    vehicle_ids = {v["vehicle_id"] for v in datasets["vehicles"]}
    dealer_ids = set(by_dealer_id.keys())
    part_ids = set(by_part_id.keys())
    comp_name_set = set(comp_names)
    customer_ids = {c["customer_id"] for c in datasets["customers"]}

    for v in datasets["vehicles"]:
        assert v["dealer_id"] in dealer_ids

    for m in datasets["vehicle_customer_map"]:
        assert m["vehicle_id"] in vehicle_ids
        assert m["customer_id"] in customer_ids

    for p in datasets["parts"]:
        assert p["part_id"] in part_ids
        assert p["dealer_id"] in dealer_ids

    for t in datasets["telemetry"]:
        assert t["vehicle_id"] in vehicle_ids

    for d in datasets["diagnostics"]:
        assert d["vehicle_id"] in vehicle_ids

    for s in datasets["service"]:
        assert s["vehicle_id"] in vehicle_ids
        assert s["dealer_id"] in dealer_ids

    for w in datasets["warranty"]:
        assert w["vehicle_id"] in vehicle_ids
        assert w["component"] in comp_name_set


def test_chronological_and_physical_invariants():
    """Verify chronological timestamps, physical telemetry-DTC coupling, and service-warranty linkage."""
    vehicles, _ = _read_scale_csv("vehicles")
    telemetry, _ = _read_scale_csv("telemetry")
    diagnostics, _ = _read_scale_csv("diagnostics")
    services, _ = _read_scale_csv("service")
    warranties, _ = _read_scale_csv("warranty")

    mfg_by_vehicle = {v["vehicle_id"]: v["manufacture_date"] for v in vehicles}

    # 1. Telemetry chronological ordering per vehicle & physical boundaries
    telem_by_veh_ts = {}
    last_ts_by_veh = {}
    for t in telemetry:
        v_id = t["vehicle_id"]
        ts = t["timestamp"]
        if v_id in last_ts_by_veh:
            assert ts > last_ts_by_veh[v_id], (
                f"Non-monotonic telemetry timestamp for {v_id}: {ts} <= {last_ts_by_veh[v_id]}"
            )
        last_ts_by_veh[v_id] = ts

        rpm = int(t["rpm"])
        temp = float(t["temperature"])
        batt = float(t["battery"])
        vib = float(t["vibration"])
        assert 0 <= rpm <= 9000
        assert -40.0 <= temp <= 160.0
        assert 9.0 <= batt <= 16.0
        assert 0.0 <= vib <= 15.0
        telem_by_veh_ts[(v_id, ts)] = (rpm, temp, batt, vib)

    # 2. Diagnostics must match verified DTC_CATALOG and correspond to an anomalous telemetry step
    valid_dtc_tuples = {(d["code"], d["component"], d["severity"]) for d in DTC_CATALOG}
    for d in diagnostics:
        key = (d["vehicle_id"], d["timestamp"])
        assert key in telem_by_veh_ts, f"Diagnostic at {key} has no matching telemetry reading"
        assert (d["code"], d["component"], d["severity"]) in valid_dtc_tuples, (
            f"Unverified DTC tuple: {d}"
        )
        rpm, temp, batt, vib = telem_by_veh_ts[key]
        # Verify physical distortion matches fault class
        if d["code"] in ("P0217", "P0420"):
            assert temp >= 55.0, f"Expected elevated overheating temperature, got {temp}"
        elif d["code"] in ("P0562", "B0001", "U0100"):
            assert batt <= 11.6, f"Expected low battery voltage, got {batt}"
        elif d["code"] in ("P0300", "C0035", "C0561"):
            assert vib >= 4.2, f"Expected elevated vibration, got {vib}"

    # 3. Service visits chronological & manufacture_date invariant
    repair_service_lookup = {}
    for s in services:
        v_id = s["vehicle_id"]
        v_date = s["visit_date"]
        cost = float(s["cost"])
        assert mfg_by_vehicle[v_id] <= v_date <= "2026-09-25"
        assert cost >= 0.0
        if cost > 350.0:
            repair_service_lookup.setdefault((v_id, v_date), []).append(s)

    # 4. Warranty claims must originate from eligible repair service visits (cost > 350)
    for w in warranties:
        key = (w["vehicle_id"], w["claim_date"])
        assert key in repair_service_lookup, f"Warranty claim {w['claim_id']} has no matching repair service visit"
        matching_services = repair_service_lookup[key]
        amount = float(w["amount"])
        assert amount > 0.0
        assert any(
            w["component"] in s["issue"] and amount <= float(s["cost"])
            for s in matching_services
        ), f"Warranty claim {w} does not match service issue/cost in {matching_services}"


def test_bronze_and_silver_clean_row_conservation():
    """Verify 100% row conservation across Bronze and Silver Clean with zero Quarantine on clean data."""
    total_bronze = 0
    total_silver_clean = 0
    total_quarantine = 0

    for ds_name, expected_count in TARGET_COUNTS.items():
        bronze_ds = ds.dataset(str(SCALE_BRONZE_DIR / ds_name), format="parquet", partitioning="hive")
        b_count = bronze_ds.to_table().num_rows
        assert b_count == expected_count, f"Bronze count mismatch for {ds_name}: {b_count} != {expected_count}"
        total_bronze += b_count

        silver_ds = ds.dataset(str(SCALE_SILVER_DIR / ds_name), format="parquet", partitioning="hive")
        s_count = silver_ds.to_table().num_rows
        assert s_count == expected_count, f"Silver clean count mismatch for {ds_name}: {s_count} != {expected_count}"
        total_silver_clean += s_count

        q_path = SCALE_QUARANTINE_DIR / ds_name
        q_files = list(q_path.rglob("*.parquet")) if q_path.exists() else []
        q_count = sum(ds.dataset(str(q_path), format="parquet").to_table().num_rows for _ in [1]) if q_files else 0
        assert q_count == 0, f"Expected 0 quarantined rows for clean dataset {ds_name}, got {q_count}"
        total_quarantine += q_count

    assert total_bronze == 120950
    assert total_silver_clean == 120950
    assert total_quarantine == 0


def test_isolated_fault_injection_quarantine_and_conservation(tmp_path):
    """
    Separate fault-injection test in tmp_path:
    Injects duplicate keys and boundary violations into Bronze and verifies Silver Quarantine
    catches every defect, preserves raw values unaltered, and maintains strict row conservation.
    """
    raw_dir = tmp_path / "raw"
    bronze_dir = tmp_path / "bronze"
    silver_dir = tmp_path / "silver"
    quarantine_dir = silver_dir / "quarantine"
    os.makedirs(raw_dir, exist_ok=True)

    # Copy baseline headers/structure with targeted faults in telemetry, diagnostics, and warranty
    for ds_name, headers in EXPECTED_HEADERS.items():
        fpath = raw_dir / f"{ds_name}.csv"
        with open(fpath, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            if ds_name == "telemetry":
                # 1 valid primary, 1 duplicate key, 1 invalid RPM (9999), 1 invalid battery (5.5V)
                writer.writerows([
                    {"vehicle_id": "VH-10001", "timestamp": "2026-09-20 10:00:00", "rpm": 2500, "temperature": 90.0, "battery": 14.0, "vibration": 1.2},
                    {"vehicle_id": "VH-10001", "timestamp": "2026-09-20 10:00:00", "rpm": 2600, "temperature": 91.0, "battery": 14.1, "vibration": 1.3},
                    {"vehicle_id": "VH-10001", "timestamp": "2026-09-20 11:00:00", "rpm": 9999, "temperature": 90.0, "battery": 14.0, "vibration": 1.2},
                    {"vehicle_id": "VH-10001", "timestamp": "2026-09-20 12:00:00", "rpm": 2200, "temperature": 90.0, "battery": 5.5, "vibration": 1.2},
                ])
            elif ds_name == "diagnostics":
                # 1 valid, 1 invalid DTC regex
                writer.writerows([
                    {"vehicle_id": "VH-10001", "timestamp": "2026-09-20 10:00:00", "code": "P0217", "component": "Cooling System", "severity": "CRITICAL"},
                    {"vehicle_id": "VH-10001", "timestamp": "2026-09-20 11:00:00", "code": "INVALID99", "component": "Cooling System", "severity": "HIGH"},
                ])
            elif ds_name == "warranty":
                # 1 valid, 1 non-positive amount (-50.0)
                writer.writerows([
                    {"claim_id": "CLM-90001", "vehicle_id": "VH-10001", "component": "Engine Block Assembly", "claim_date": "2026-09-20", "amount": 400.0},
                    {"claim_id": "CLM-90002", "vehicle_id": "VH-10001", "component": "Engine Block Assembly", "claim_date": "2026-09-20", "amount": -50.0},
                ])
            elif ds_name == "vehicles":
                writer.writerow({"vehicle_id": "VH-10001", "model": "Apex", "variant": "Base", "manufacture_date": "2025-01-10", "dealer_id": "DLR-001"})
            elif ds_name == "customers":
                writer.writerow({"customer_id": "CUST-00001", "customer_name": "James Smith", "segment": "Corporate-Fleet", "region": "North"})
            elif ds_name == "vehicle_customer_map":
                writer.writerow({"vehicle_id": "VH-10001", "customer_id": "CUST-00001", "registration_date": "2025-01-24"})
            elif ds_name == "dealers":
                writer.writerow({"dealer_id": "DLR-001", "name": "Metro Apex Motors", "region": "North", "city": "Chicago", "bays": 12})
            elif ds_name == "components":
                writer.writerow({"part_id": "PRT-ENG-01", "name": "Engine Block Assembly", "category": "Powertrain", "lifespan_km": 250000, "base_cost": 4500.0, "lead_time_days": 14})
            elif ds_name == "parts":
                writer.writerow({"part_id": "PRT-ENG-01", "dealer_id": "DLR-001", "stock": 10, "lead_time": 5})
            elif ds_name == "service":
                writer.writerow({"service_id": "SRV-50001", "vehicle_id": "VH-10001", "dealer_id": "DLR-001", "visit_date": "2026-09-20", "issue": "Repair", "cost": 500.0})

    run_bronze_ingestion(source_dir=str(raw_dir), output_dir=str(bronze_dir), batch_id="BATCH-FAULT-TEST", snapshot_date="2026-09-25")
    results = {
        r["dataset"]: r
        for r in run_silver_cleaning(
            bronze_dir=str(bronze_dir),
            silver_dir=str(silver_dir),
            quarantine_dir=str(quarantine_dir),
            batch_id="BATCH-FAULT-SILVER",
            snapshot_date="2026-09-25",
        )
    }

    assert results["telemetry"]["bronze_count"] == 4
    assert results["telemetry"]["clean_count"] == 1
    assert results["telemetry"]["quarantine_count"] == 3
    assert results["telemetry"]["conservation_verified"] is True

    # Verify quarantined telemetry rows preserve exact raw values and expected rules
    q_telem = ds.dataset(str(quarantine_dir / "telemetry"), format="parquet").to_table().to_pylist()
    q_rules = {r["_quarantine_rule"] for r in q_telem}
    assert q_rules == {"DUPLICATE_KEY", "RULE_TEL_RPM_RANGE", "RULE_TEL_BATTERY_RANGE"}
    rpm_row = next(r for r in q_telem if r["_quarantine_rule"] == "RULE_TEL_RPM_RANGE")
    assert int(rpm_row["rpm"]) == 9999

    assert results["diagnostics"]["clean_count"] == 1
    assert results["diagnostics"]["quarantine_count"] == 1
    assert results["warranty"]["clean_count"] == 1
    assert results["warranty"]["quarantine_count"] == 1


def test_deterministic_seed_reproducibility(tmp_path):
    """Verify two runs with the same seed produce byte-for-byte identical CSV files."""
    run1_dir = tmp_path / "run1"
    run2_dir = tmp_path / "run2"

    generate_scale_100k_raw(raw_dir=str(run1_dir), seed=42, end_date_str="2026-09-25")
    generate_scale_100k_raw(raw_dir=str(run2_dir), seed=42, end_date_str="2026-09-25")

    for ds_name in TARGET_COUNTS:
        b1 = (run1_dir / f"{ds_name}.csv").read_bytes()
        b2 = (run2_dir / f"{ds_name}.csv").read_bytes()
        assert hashlib.sha256(b1).hexdigest() == hashlib.sha256(b2).hexdigest(), (
            f"Determinism check failed for {ds_name}.csv"
        )


def test_baseline_data_raw_sha256_preserved():
    """Verify canonical data/raw files (9,286 rows) are byte-for-byte unchanged."""
    total_baseline_rows = 0
    for fname, (expected_rows, expected_sha256) in EXPECTED_BASELINE_RAW.items():
        fpath = BASELINE_RAW_DIR / fname
        assert fpath.exists(), f"Baseline file missing: {fpath}"
        actual_sha256 = hashlib.sha256(fpath.read_bytes()).hexdigest()
        assert actual_sha256 == expected_sha256, (
            f"SHA-256 mismatch for baseline data/raw/{fname}: {actual_sha256} != {expected_sha256}"
        )
        with open(fpath, mode="r", encoding="utf-8") as f:
            row_count = sum(1 for _ in csv.DictReader(f))
        assert row_count == expected_rows
        total_baseline_rows += row_count

    assert total_baseline_rows == 9286
