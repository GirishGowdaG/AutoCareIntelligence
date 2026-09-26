"""AutoCare Intelligence — Bronze Ingestion Pipeline.

Ingests raw CSV datasets from data/raw/ into the Medallion Data Lakehouse (data/bronze/)
as immutable, Snappy-compressed Parquet datasets with enterprise audit metadata.

Audit Columns Appended:
  - _ingested_at: Exact UTC timestamp when record entered Bronze.
  - _source_file: Relative path to originating raw file.
  - _batch_id: Explicit ingestion batch identifier (supplied via --batch-id
               or defaulting to BATCH-YYYYMMDD-HHMMSS).

Partitioning Semantics:
  - Event streams (telemetry, diagnostics): Partitioned by (year, month, day)
    derived directly from the source event 'timestamp' column.
  - Snapshot & reference tables (vehicles, service, warranty, parts, dealers,
    components, customers, vehicle_customer_map): Partitioned by 'snapshot_date'
    representing the business snapshot extraction date.
"""

import os
import argparse
from datetime import datetime
from typing import Dict, Any

import pyarrow as pa
import pyarrow.csv as pv
import pyarrow.dataset as ds
import pyarrow.compute as pc

# Datasets to ingest
EVENT_DATASETS = ["telemetry", "diagnostics"]
SNAPSHOT_DATASETS = [
    "vehicles", "service", "warranty", "parts",
    "dealers", "components", "customers", "vehicle_customer_map"
]
ALL_DATASETS = EVENT_DATASETS + SNAPSHOT_DATASETS


def parse_args():
    parser = argparse.ArgumentParser(description="Ingest raw CSVs into Bronze Medallion Lake")
    parser.add_argument(
        "--source-dir",
        type=str,
        default="data/raw",
        help="Directory containing source CSV files (default: data/raw)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/bronze",
        help="Root directory for Bronze Parquet lakehouse (default: data/bronze)"
    )
    parser.add_argument(
        "--batch-id",
        type=str,
        default=None,
        help="Explicit ingestion batch ID. If omitted, defaults to BATCH-YYYYMMDD-HHMMSS (UTC)."
    )
    parser.add_argument(
        "--snapshot-date",
        type=str,
        default="2026-09-25",
        help="Business snapshot date (YYYY-MM-DD) for snapshot datasets (default: 2026-09-25)"
    )
    return parser.parse_args()


def ingest_dataset(
    dataset_name: str,
    source_dir: str,
    output_dir: str,
    batch_id: str,
    ingested_at: str,
    snapshot_date: str
) -> Dict[str, Any]:
    """Ingests a single CSV into Bronze Parquet with audit metadata and partitioning."""
    source_filename = f"{dataset_name}.csv"
    source_path = os.path.join(source_dir, source_filename)
    if not os.path.exists(source_path):
        raise FileNotFoundError(f"Source file not found: {source_path}")

    # Read raw CSV using PyArrow preserving exact raw rows
    # Read all columns as strings/native without dropping or altering rows
    table = pv.read_csv(source_path)
    num_rows = table.num_rows
    orig_column_names = list(table.column_names)

    # 1. Append technical audit columns
    ingested_at_array = pa.array([ingested_at] * num_rows, type=pa.string())
    source_file_array = pa.array([source_path.replace("\\", "/")] * num_rows, type=pa.string())
    batch_id_array = pa.array([batch_id] * num_rows, type=pa.string())

    table = table.append_column("_ingested_at", ingested_at_array)
    table = table.append_column("_source_file", source_file_array)
    table = table.append_column("_batch_id", batch_id_array)

    target_dataset_dir = os.path.join(output_dir, dataset_name)
    os.makedirs(target_dataset_dir, exist_ok=True)

    # 2. Derive partitioning columns
    if dataset_name in EVENT_DATASETS:
        # Event timestamp derived partitioning (year, month, day)
        # Parse timestamp column: format is YYYY-MM-DD HH:MM:SS
        ts_col = table["timestamp"]
        ts_str = pc.cast(ts_col, pa.string())
        # Extract substrings for year, month, day from 'timestamp'
        year_arr = pc.utf8_slice_codeunits(ts_str, 0, 4)
        month_arr = pc.utf8_slice_codeunits(ts_str, 5, 7)
        day_arr = pc.utf8_slice_codeunits(ts_str, 8, 10)

        table_with_part = table.append_column("year", year_arr)
        table_with_part = table_with_part.append_column("month", month_arr)
        table_with_part = table_with_part.append_column("day", day_arr)

        partitioning = ds.partitioning(
            schema=pa.schema([
                ("year", pa.string()),
                ("month", pa.string()),
                ("day", pa.string())
            ]),
            flavor="hive"
        )
    else:
        # Snapshot / reference dataset partitioning (snapshot_date)
        snap_arr = pa.array([snapshot_date] * num_rows, type=pa.string())
        table_with_part = table.append_column("snapshot_date", snap_arr)

        partitioning = ds.partitioning(
            schema=pa.schema([
                ("snapshot_date", pa.string())
            ]),
            flavor="hive"
        )

    # 3. Write immutable Snappy-compressed Parquet dataset
    ds.write_dataset(
        data=table_with_part,
        base_dir=target_dataset_dir,
        format="parquet",
        partitioning=partitioning,
        file_options=ds.ParquetFileFormat().make_write_options(compression="snappy"),
        existing_data_behavior="overwrite_or_ignore"
    )

    return {
        "dataset": dataset_name,
        "source_file": source_path,
        "rows": num_rows,
        "original_columns": orig_column_names,
        "target_dir": target_dataset_dir,
        "partition_type": "event (year/month/day)" if dataset_name in EVENT_DATASETS else "snapshot (snapshot_date)"
    }


def run_bronze_ingestion(source_dir: str, output_dir: str, batch_id: str = None, snapshot_date: str = "2026-09-25"):
    # Define clear documented default behavior for batch_id if omitted:
    # BATCH-<UTC-TIMESTAMP>
    now_utc = datetime.utcnow()
    if not batch_id:
        batch_id = f"BATCH-{now_utc.strftime('%Y%m%d-%H%M%S')}"

    ingested_at = now_utc.strftime("%Y-%m-%d %H:%M:%S")

    print(f"=== Starting AutoCare Bronze Ingestion ===")
    print(f"Batch ID: {batch_id}")
    print(f"Ingestion Timestamp: {ingested_at} UTC")
    print(f"Source Directory: {source_dir}")
    print(f"Target Directory: {output_dir}")
    print(f"Snapshot Date: {snapshot_date}")
    print("------------------------------------------")

    results = []
    for ds_name in ALL_DATASETS:
        res = ingest_dataset(
            dataset_name=ds_name,
            source_dir=source_dir,
            output_dir=output_dir,
            batch_id=batch_id,
            ingested_at=ingested_at,
            snapshot_date=snapshot_date
        )
        results.append(res)
        print(f"Ingested {res['dataset']:<22} | Rows: {res['rows']:<6} | Partition: {res['partition_type']}")

    print("------------------------------------------")
    print(f"=== Bronze Ingestion Completed Successfully for {len(results)} Datasets ===")
    return results


if __name__ == "__main__":
    args = parse_args()
    run_bronze_ingestion(
        source_dir=args.source_dir,
        output_dir=args.output_dir,
        batch_id=args.batch_id,
        snapshot_date=args.snapshot_date
    )
