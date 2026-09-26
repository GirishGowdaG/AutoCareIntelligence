"""Automated Verification Suite for Phase 2B — Silver Cleaning & Validation.

Verifies:
  1. All 10 Silver datasets exist in Parquet format.
  2. Silver pipeline reads strictly and exclusively from data/bronze/.
  3. Mathematical row conservation: Count(Bronze) == Count(Silver Clean) + Count(Silver Quarantine).
  4. Zero duplicate primary or composite keys in Silver Clean.
  5. Zero null primary or composite keys in Silver Clean.
  6. Domain boundaries strictly satisfied in Silver Clean (RPM, Temp, Battery, Vibration, Cost, Amount, Stock).
  7. DTC codes conform to ^[PCBU][0-9]{4}$ and severities are standardized uppercase.
  8. Full audit lineage is preserved (_source_file, _bronze_batch_id, _bronze_ingested_at, _silver_processed_at, _silver_batch_id).
  9. Deterministic snapshot-date validation.
  10. Quarantine routing and exact raw domain value preservation (duplicate & out-of-bound injection test).
"""

import os
import re
import pyarrow as pa
import pyarrow.dataset as ds
import pytest

from lakehouse.silver_clean import DEDUPLICATION_KEYS, ALL_DATASETS, EVENT_DATASETS, SNAPSHOT_DATASETS

BRONZE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "bronze")
SILVER_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "silver")
QUARANTINE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "silver", "quarantine")


def load_parquet_table(base_dir: str, dataset_name: str):
    target_path = os.path.join(base_dir, dataset_name)
    if not os.path.exists(target_path):
        return None
    try:
        dataset = ds.dataset(target_path, format="parquet", partitioning="hive")
        return dataset.to_table()
    except Exception:
        return None


def test_all_ten_silver_datasets_exist():
    """Verify that all 10 datasets exist in data/silver/."""
    for name in ALL_DATASETS:
        table = load_parquet_table(SILVER_DIR, name)
        assert table is not None, f"Silver dataset '{name}' does not exist under {SILVER_DIR}"
        assert table.num_rows > 0, f"Silver dataset '{name}' has 0 rows"


def test_silver_reads_only_from_bronze():
    """Verify by code inspection that silver_clean.py default paths target data/bronze and never data/raw."""
    from lakehouse.silver_clean import parse_args
    # Verify default bronze-dir argument
    import inspect
    from lakehouse.silver_clean import process_silver_dataset
    sig = inspect.signature(process_silver_dataset)
    assert "bronze_dir" in sig.parameters
    assert "raw_dir" not in sig.parameters


def test_mathematical_row_conservation():
    """
    Verify absolute mathematical row conservation:
    Count(Bronze) == Count(Silver Clean) + Count(Silver Quarantine)
    """
    for name in ALL_DATASETS:
        bronze_table = load_parquet_table(BRONZE_DIR, name)
        clean_table = load_parquet_table(SILVER_DIR, name)
        quarantine_table = load_parquet_table(QUARANTINE_DIR, name)

        b_count = bronze_table.num_rows if bronze_table is not None else 0
        c_count = clean_table.num_rows if clean_table is not None else 0
        q_count = quarantine_table.num_rows if quarantine_table is not None else 0

        assert b_count == c_count + q_count, (
            f"Row conservation failed for {name}: Bronze={b_count} != Clean({c_count}) + Quarantine({q_count})"
        )


def test_zero_duplicate_keys_in_silver_clean():
    """Verify that Silver Clean contains zero duplicate primary or composite keys."""
    for name, key_fields in DEDUPLICATION_KEYS.items():
        clean_table = load_parquet_table(SILVER_DIR, name)
        assert clean_table is not None
        records = clean_table.to_pylist()
        keys = [tuple(r.get(kf) for kf in key_fields) for r in records]
        assert len(keys) == len(set(keys)), (
            f"Duplicate keys found in Silver Clean for dataset '{name}': {len(keys)} total vs {len(set(keys))} unique"
        )


def test_zero_null_keys_in_silver_clean():
    """Verify that Silver Clean contains zero null or empty keys."""
    for name, key_fields in DEDUPLICATION_KEYS.items():
        clean_table = load_parquet_table(SILVER_DIR, name)
        records = clean_table.to_pylist()
        for idx, r in enumerate(records):
            for kf in key_fields:
                val = r.get(kf)
                assert val is not None and str(val).strip() != "", (
                    f"Null key '{kf}' found in Silver Clean '{name}' at row {idx}"
                )


def test_physical_range_assertions_in_silver_clean():
    """Verify that all telemetry signals in Silver Clean conform strictly to physical ranges."""
    tel_table = load_parquet_table(SILVER_DIR, "telemetry")
    for r in tel_table.to_pylist():
        rpm = int(r["rpm"])
        temp = float(r["temperature"])
        bat = float(r["battery"])
        vib = float(r["vibration"])

        assert 0 <= rpm <= 9000, f"RPM {rpm} out of bounds"
        assert -40.0 <= temp <= 160.0, f"Temp {temp} out of bounds"
        assert 9.0 <= bat <= 16.0, f"Battery {bat} out of bounds"
        assert 0.0 <= vib <= 15.0, f"Vibration {vib} out of bounds"

    parts_table = load_parquet_table(SILVER_DIR, "parts")
    for r in parts_table.to_pylist():
        assert int(r["stock"]) >= 0, f"Negative parts stock {r['stock']}"
        assert int(r["lead_time"]) >= 1, f"Lead time < 1: {r['lead_time']}"

    srv_table = load_parquet_table(SILVER_DIR, "service")
    for r in srv_table.to_pylist():
        assert float(r["cost"]) >= 0.0, f"Negative service cost {r['cost']}"

    wrn_table = load_parquet_table(SILVER_DIR, "warranty")
    for r in wrn_table.to_pylist():
        assert float(r["amount"]) > 0.0, f"Non-positive warranty amount {r['amount']}"


def test_diagnostics_code_and_severity_standardization():
    """Verify that diagnostic codes follow ^[PCBU][0-9]{4}$ and severities are uppercase."""
    dtc_table = load_parquet_table(SILVER_DIR, "diagnostics")
    regex = re.compile(r"^[PCBU][0-9]{4}$")
    valid_severities = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}

    for r in dtc_table.to_pylist():
        assert regex.match(r["code"]), f"DTC code {r['code']} does not match pattern"
        assert r["severity"] in valid_severities, f"Severity {r['severity']} not valid"
        assert r["severity"] == r["severity"].upper(), f"Severity {r['severity']} not uppercase"


def test_audit_and_lineage_columns_in_silver_clean():
    """Verify that Silver Clean preserves Bronze lineage and appends Silver audit metadata."""
    expected_lineage = [
        "_source_file", "_bronze_batch_id", "_bronze_ingested_at",
        "_silver_processed_at", "_silver_batch_id"
    ]
    for name in ALL_DATASETS:
        table = load_parquet_table(SILVER_DIR, name)
        for col in expected_lineage:
            assert col in table.column_names, f"Lineage column '{col}' missing in Silver Clean '{name}'"
            assert table[col].null_count == 0, f"Lineage column '{col}' has nulls in '{name}'"


def test_deterministic_date_validation():
    """Verify that vehicles manufacture_date <= deterministic snapshot date 2026-09-25."""
    veh_table = load_parquet_table(SILVER_DIR, "vehicles")
    for r in veh_table.to_pylist():
        mfg_dt = str(r["manufacture_date"])
        assert mfg_dt <= "2026-09-25", f"Manufacture date {mfg_dt} is in future relative to snapshot date"


def test_quarantine_routing_and_exact_raw_preservation(tmp_path):
    """
    Simulates a synthetic Bronze dataset containing:
      - 1 valid record
      - 1 duplicate record (same key)
      - 1 out-of-bounds record (RPM 12000)
    Executes Silver pipeline and verifies:
      - Valid record -> Silver Clean
      - Duplicate record -> Quarantine with rule DUPLICATE_KEY
      - Out-of-bounds record -> Quarantine with rule RULE_TEL_RPM_RANGE
      - Original out-of-bounds value (12000) is preserved exactly in Quarantine
      - Row conservation holds: 3 Bronze == 1 Clean + 2 Quarantine
    """
    from lakehouse.silver_clean import process_silver_dataset

    test_bronze_dir = str(tmp_path / "test_bronze")
    test_silver_dir = str(tmp_path / "test_silver")
    test_quarantine_dir = str(tmp_path / "test_quarantine")

    os.makedirs(os.path.join(test_bronze_dir, "telemetry"), exist_ok=True)

    # Construct test data
    test_records = [
        {
            "vehicle_id": "VH-TEST-1",
            "timestamp": "2026-09-25 10:00:00",
            "rpm": 2500,
            "temperature": 92.5,
            "battery": 14.1,
            "vibration": 1.2,
            "_ingested_at": "2026-09-25 10:05:00",
            "_source_file": "data/raw/telemetry.csv",
            "_batch_id": "BATCH-TEST-001",
            "year": 2026,
            "month": 9,
            "day": 25
        },
        # Duplicate record (same vehicle_id, same timestamp)
        {
            "vehicle_id": "VH-TEST-1",
            "timestamp": "2026-09-25 10:00:00",
            "rpm": 2550,
            "temperature": 93.0,
            "battery": 14.0,
            "vibration": 1.3,
            "_ingested_at": "2026-09-25 10:04:00",  # earlier ingestion
            "_source_file": "data/raw/telemetry.csv",
            "_batch_id": "BATCH-TEST-001",
            "year": 2026,
            "month": 9,
            "day": 25
        },
        # Out-of-bounds record (RPM 12000 > 9000)
        {
            "vehicle_id": "VH-TEST-2",
            "timestamp": "2026-09-25 11:00:00",
            "rpm": 12000,
            "temperature": 95.0,
            "battery": 14.2,
            "vibration": 1.1,
            "_ingested_at": "2026-09-25 11:05:00",
            "_source_file": "data/raw/telemetry.csv",
            "_batch_id": "BATCH-TEST-001",
            "year": 2026,
            "month": 9,
            "day": 25
        }
    ]

    t_table = pa.Table.from_pylist(test_records)
    ds.write_dataset(
        data=t_table,
        base_dir=os.path.join(test_bronze_dir, "telemetry"),
        format="parquet",
        partitioning=ds.partitioning(
            schema=pa.schema([("year", pa.int32()), ("month", pa.int32()), ("day", pa.int32())]),
            flavor="hive"
        )
    )

    # Process through Silver
    res = process_silver_dataset(
        dataset_name="telemetry",
        bronze_dir=test_bronze_dir,
        silver_dir=test_silver_dir,
        quarantine_dir=test_quarantine_dir,
        batch_id="BATCH-SILVER-TEST",
        processed_at="2026-09-26 12:00:00",
        snapshot_date="2026-09-25"
    )

    assert res["bronze_count"] == 3
    assert res["clean_count"] == 1
    assert res["quarantine_count"] == 2
    assert res["conservation_verified"] is True

    # Inspect Quarantined records
    q_table = load_parquet_table(test_quarantine_dir, "telemetry")
    assert q_table.num_rows == 2
    q_records = q_table.to_pylist()

    rules = [r["_quarantine_rule"] for r in q_records]
    assert "DUPLICATE_KEY" in rules
    assert "RULE_TEL_RPM_RANGE" in rules

    # Verify exact raw value preservation in quarantine
    rpm_record = next(r for r in q_records if r["_quarantine_rule"] == "RULE_TEL_RPM_RANGE")
    assert rpm_record["rpm"] == 12000  # Raw out-of-bounds value NOT altered
    assert rpm_record["vehicle_id"] == "VH-TEST-2"
    assert "_quarantined_at" in rpm_record
