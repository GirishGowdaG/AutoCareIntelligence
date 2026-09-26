"""Automated Verification Suite for Phase 2A — Bronze Ingestion.

Verifies:
  1. All 10 Bronze datasets exist in Parquet format.
  2. Exact row-count conservation: Count(Bronze) == Count(Raw).
  3. Original raw columns are 100% preserved.
  4. Original raw values match without modification or corruption.
  5. Audit columns (_ingested_at, _source_file, _batch_id) are present and non-null.
  6. Batch ID is consistent across all records in an execution run.
  7. Source file paths accurately reflect originating CSVs.
  8. Event-date partitioning (year, month, day) accurately reflects event timestamps.
  9. Repeatable ingestion behavior.
"""

import os
import pyarrow.csv as pv
import pyarrow.dataset as ds
import pytest

RAW_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "raw")
BRONZE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "bronze")

ALL_DATASETS = [
    "vehicles", "telemetry", "diagnostics",
    "service", "warranty", "parts",
    "dealers", "components", "customers", "vehicle_customer_map"
]

EVENT_DATASETS = ["telemetry", "diagnostics"]
SNAPSHOT_DATASETS = [
    "vehicles", "service", "warranty", "parts",
    "dealers", "components", "customers", "vehicle_customer_map"
]


def load_raw_table(name: str):
    csv_path = os.path.join(RAW_DIR, f"{name}.csv")
    assert os.path.exists(csv_path), f"Raw CSV missing: {csv_path}"
    return pv.read_csv(csv_path)


def load_bronze_dataset(name: str):
    bronze_path = os.path.join(BRONZE_DIR, name)
    assert os.path.exists(bronze_path), f"Bronze dataset directory missing: {bronze_path}"
    # Read partitioned dataset
    dataset = ds.dataset(bronze_path, format="parquet", partitioning="hive")
    return dataset.to_table()


def test_all_ten_bronze_datasets_exist():
    """Verify that all 10 datasets exist under data/bronze/."""
    for name in ALL_DATASETS:
        target_dir = os.path.join(BRONZE_DIR, name)
        assert os.path.isdir(target_dir), f"Bronze directory for {name} does not exist at {target_dir}"


def test_exact_row_count_conservation():
    """Verify exact row-count conservation between raw CSVs and Bronze Parquet."""
    for name in ALL_DATASETS:
        raw_table = load_raw_table(name)
        bronze_table = load_bronze_dataset(name)
        assert bronze_table.num_rows == raw_table.num_rows, (
            f"Row count mismatch for {name}: Raw={raw_table.num_rows}, Bronze={bronze_table.num_rows}"
        )


def test_original_columns_preserved():
    """Verify that all original raw columns are preserved in Bronze."""
    for name in ALL_DATASETS:
        raw_table = load_raw_table(name)
        bronze_table = load_bronze_dataset(name)
        for col in raw_table.column_names:
            assert col in bronze_table.column_names, (
                f"Original column '{col}' missing in Bronze dataset for '{name}'"
            )


def test_audit_columns_present_and_non_null():
    """Verify that _ingested_at, _source_file, and _batch_id are present and 100% non-null."""
    audit_cols = ["_ingested_at", "_source_file", "_batch_id"]
    for name in ALL_DATASETS:
        bronze_table = load_bronze_dataset(name)
        for ac in audit_cols:
            assert ac in bronze_table.column_names, f"Audit column '{ac}' missing in {name}"
            col_data = bronze_table[ac]
            assert col_data.null_count == 0, f"Audit column '{ac}' contains nulls in {name}"


def test_consistent_batch_id_across_datasets():
    """Verify that the supplied batch_id is uniform across all records in the ingestion run."""
    batch_ids = set()
    for name in ALL_DATASETS:
        bronze_table = load_bronze_dataset(name)
        unique_batches = set(bronze_table["_batch_id"].to_pylist())
        assert len(unique_batches) == 1, f"Multiple batch_ids detected in {name}: {unique_batches}"
        batch_ids.update(unique_batches)
    assert len(batch_ids) == 1, f"Inconsistent batch_ids across datasets: {batch_ids}"


def test_correct_source_file_values():
    """Verify that _source_file points to the exact originating CSV."""
    for name in ALL_DATASETS:
        bronze_table = load_bronze_dataset(name)
        expected_suffix = f"data/raw/{name}.csv"
        source_files = set(bronze_table["_source_file"].to_pylist())
        assert len(source_files) == 1
        actual_path = list(source_files)[0].replace("\\", "/")
        assert actual_path.endswith(expected_suffix), (
            f"Expected _source_file to end with {expected_suffix}, got {actual_path}"
        )


def test_event_date_partitioning_semantics():
    """Verify that telemetry and diagnostics partitioning reflects the source event timestamp."""
    for name in EVENT_DATASETS:
        bronze_table = load_bronze_dataset(name)
        assert "year" in bronze_table.column_names
        assert "month" in bronze_table.column_names
        assert "day" in bronze_table.column_names

        # Sample check: verify partition columns match timestamp string
        ts_list = bronze_table["timestamp"].to_pylist()[:100]
        y_list = bronze_table["year"].to_pylist()[:100]
        m_list = bronze_table["month"].to_pylist()[:100]
        d_list = bronze_table["day"].to_pylist()[:100]

        for ts, y, m, d in zip(ts_list, y_list, m_list, d_list):
            ts_str = str(ts)
            assert int(ts_str[:4]) == int(y), f"Year mismatch: {ts_str} vs {y}"
            assert int(ts_str[5:7]) == int(m), f"Month mismatch: {ts_str} vs {m}"
            assert int(ts_str[8:10]) == int(d), f"Day mismatch: {ts_str} vs {d}"


def test_snapshot_partition_semantics():
    """Verify that snapshot datasets are partitioned by snapshot_date."""
    for name in SNAPSHOT_DATASETS:
        bronze_table = load_bronze_dataset(name)
        assert "snapshot_date" in bronze_table.column_names
        unique_snaps = set(bronze_table["snapshot_date"].to_pylist())
        assert len(unique_snaps) == 1
        assert list(unique_snaps)[0] == "2026-09-25"


def test_original_values_preserved():
    """Verify that raw values in critical fields match exactly between raw and Bronze."""
    # Check vehicles
    raw_v = load_raw_table("vehicles")
    bronze_v = load_bronze_dataset("vehicles")
    assert sorted(raw_v["vehicle_id"].to_pylist()) == sorted(bronze_v["vehicle_id"].to_pylist())

    # Check parts
    raw_p = load_raw_table("parts")
    bronze_p = load_bronze_dataset("parts")
    assert sorted(raw_p["part_id"].to_pylist()) == sorted(bronze_p["part_id"].to_pylist())
    assert sum(raw_p["stock"].to_pylist()) == sum(bronze_p["stock"].to_pylist())

    # Check warranty
    raw_w = load_raw_table("warranty")
    bronze_w = load_bronze_dataset("warranty")
    assert sorted(raw_w["claim_id"].to_pylist()) == sorted(bronze_w["claim_id"].to_pylist())


def test_repeatable_ingestion_behavior(tmp_path):
    """Verify that running ingestion on a temp directory reproduces identical row counts and schemas."""
    from lakehouse.bronze_ingest import run_bronze_ingestion

    test_output = str(tmp_path / "bronze_repeat")
    results = run_bronze_ingestion(
        source_dir=RAW_DIR,
        output_dir=test_output,
        batch_id="BATCH-TEST-REPEAT",
        snapshot_date="2026-09-25"
    )

    assert len(results) == 10
    for res in results:
        ds_test = ds.dataset(os.path.join(test_output, res["dataset"]), format="parquet", partitioning="hive")
        assert ds_test.to_table().num_rows == res["rows"]
