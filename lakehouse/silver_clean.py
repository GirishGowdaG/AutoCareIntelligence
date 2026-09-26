"""AutoCare Intelligence — Silver Cleaning & Validation Pipeline.

Reads raw immutable datasets strictly and exclusively from the Bronze layer (data/bronze/).
Performs:
  1. Deterministic deduplication (duplicate records routed to Silver Quarantine).
  2. Domain validation & boundary constraint enforcement (out-of-bound records routed to Silver Quarantine).
  3. Standardization & cleaning on surviving Silver Clean records (whitespace trimming, uppercase severities).
  4. Exact preservation of original domain values in Silver Quarantine (zero alteration of rejected data).
  5. Strict mathematical row conservation:
     Count(Bronze) == Count(Silver Clean) + Count(Silver Quarantine)

Audit Lineage:
  - Preserves Bronze metadata: _source_file, _bronze_batch_id, _bronze_ingested_at.
  - Silver Clean appends: _silver_processed_at, _silver_batch_id.
  - Silver Quarantine appends: _quarantine_rule, _quarantine_reason, _quarantined_at.
"""

import os
import re
import argparse
from datetime import datetime
from typing import Dict, Any, List, Tuple

import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.compute as pc

EVENT_DATASETS = ["telemetry", "diagnostics"]
SNAPSHOT_DATASETS = [
    "vehicles", "service", "warranty", "parts",
    "dealers", "components", "customers", "vehicle_customer_map"
]
ALL_DATASETS = EVENT_DATASETS + SNAPSHOT_DATASETS

DTC_REGEX = re.compile(r"^[PCBU][0-9]{4}$")
VALID_SEVERITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}

# Primary / composite business keys per dataset for deterministic deduplication
DEDUPLICATION_KEYS = {
    "telemetry": ["vehicle_id", "timestamp"],
    "diagnostics": ["vehicle_id", "timestamp", "code"],
    "vehicles": ["vehicle_id"],
    "service": ["service_id"],
    "warranty": ["claim_id"],
    "parts": ["part_id", "dealer_id"],
    "dealers": ["dealer_id"],
    "components": ["part_id"],
    "customers": ["customer_id"],
    "vehicle_customer_map": ["vehicle_id"],
}


def parse_args():
    parser = argparse.ArgumentParser(description="Clean and validate Bronze datasets into Silver Medallion Lake")
    parser.add_argument(
        "--bronze-dir",
        type=str,
        default="data/bronze",
        help="Root directory of Bronze Parquet lake (default: data/bronze)"
    )
    parser.add_argument(
        "--silver-dir",
        type=str,
        default="data/silver",
        help="Root directory for Silver Clean lake (default: data/silver)"
    )
    parser.add_argument(
        "--quarantine-dir",
        type=str,
        default="data/silver/quarantine",
        help="Root directory for Silver Quarantine lake (default: data/silver/quarantine)"
    )
    parser.add_argument(
        "--batch-id",
        type=str,
        default=None,
        help="Explicit Silver processing batch ID. If omitted, defaults to BATCH-SILVER-YYYYMMDD-HHMMSS (UTC)."
    )
    parser.add_argument(
        "--snapshot-date",
        type=str,
        default="2026-09-25",
        help="Deterministic snapshot reference date (YYYY-MM-DD) for date validations (default: 2026-09-25)"
    )
    return parser.parse_args()


def validate_record(dataset_name: str, record: Dict[str, Any], snapshot_date: str) -> Tuple[bool, str, str]:
    """
    Evaluates a single record against domain boundary assertions.
    Returns: (is_valid, quarantine_rule_code, quarantine_reason)
    """
    if dataset_name == "telemetry":
        v_id = str(record.get("vehicle_id") or "").strip()
        ts = record.get("timestamp")
        if not v_id or ts is None:
            return False, "RULE_TEL_PK_NOT_NULL", "Mandatory vehicle_id or timestamp is null/empty"

        try:
            rpm = int(record["rpm"])
            temp = float(record["temperature"])
            bat = float(record["battery"])
            vib = float(record["vibration"])
        except (ValueError, TypeError) as e:
            return False, "RULE_TEL_TYPE_ERROR", f"Failed to parse numerical sensor signals: {e}"

        if not (0 <= rpm <= 9000):
            return False, "RULE_TEL_RPM_RANGE", f"RPM value {rpm} outside valid range [0, 9000]"
        if not (-40.0 <= temp <= 160.0):
            return False, "RULE_TEL_TEMP_RANGE", f"Temperature {temp}°C outside valid range [-40.0, 160.0]"
        if not (9.0 <= bat <= 16.0):
            return False, "RULE_TEL_BATTERY_RANGE", f"Battery voltage {bat}V outside valid range [9.0, 16.0]"
        if not (0.0 <= vib <= 15.0):
            return False, "RULE_TEL_VIB_RANGE", f"Vibration index {vib} mm/s outside valid range [0.0, 15.0]"

    elif dataset_name == "diagnostics":
        v_id = str(record.get("vehicle_id") or "").strip()
        ts = record.get("timestamp")
        code = str(record.get("code") or "").strip()
        sev = str(record.get("severity") or "").strip().upper()

        if not v_id or ts is None or not code:
            return False, "RULE_DTC_PK_NOT_NULL", "Mandatory vehicle_id, timestamp, or code is null/empty"
        if not DTC_REGEX.match(code):
            return False, "RULE_DTC_CODE_REGEX", f"Diagnostic code '{code}' does not match standard OBD-II regex ^[PCBU][0-9]{{4}}$"
        if sev not in VALID_SEVERITIES:
            return False, "RULE_DTC_SEVERITY", f"Invalid severity tier '{record.get('severity')}'; must be LOW, MEDIUM, HIGH, or CRITICAL"

    elif dataset_name == "vehicles":
        v_id = str(record.get("vehicle_id") or "").strip()
        model = str(record.get("model") or "").strip()
        dealer = str(record.get("dealer_id") or "").strip()
        mfg_dt = str(record.get("manufacture_date") or "").strip()

        if not v_id or not model or not dealer:
            return False, "RULE_VEH_NOT_NULL", "Mandatory vehicle_id, model, or dealer_id is null/empty"
        if mfg_dt > snapshot_date:
            return False, "RULE_VEH_DATE_RANGE", f"Manufacture date {mfg_dt} is in the future relative to snapshot date {snapshot_date}"

    elif dataset_name == "service":
        s_id = str(record.get("service_id") or "").strip()
        v_id = str(record.get("vehicle_id") or "").strip()
        visit_dt = str(record.get("visit_date") or "").strip()
        try:
            cost = float(record["cost"])
        except (ValueError, TypeError) as e:
            return False, "RULE_SRV_TYPE_ERROR", f"Invalid cost value: {e}"

        if not s_id or not v_id:
            return False, "RULE_SRV_PK_NOT_NULL", "Mandatory service_id or vehicle_id is null/empty"
        if cost < 0.0:
            return False, "RULE_SRV_COST_RANGE", f"Negative service repair invoice cost {cost:.2f} detected"
        if visit_dt > snapshot_date:
            return False, "RULE_SRV_DATE_VALID", f"Service visit date {visit_dt} is in the future relative to snapshot date {snapshot_date}"

    elif dataset_name == "warranty":
        c_id = str(record.get("claim_id") or "").strip()
        v_id = str(record.get("vehicle_id") or "").strip()
        claim_dt = str(record.get("claim_date") or "").strip()
        try:
            amount = float(record["amount"])
        except (ValueError, TypeError) as e:
            return False, "RULE_WRN_TYPE_ERROR", f"Invalid claim amount value: {e}"

        if not c_id or not v_id:
            return False, "RULE_WRN_PK_NOT_NULL", "Mandatory claim_id or vehicle_id is null/empty"
        if amount <= 0.0:
            return False, "RULE_WRN_AMOUNT_POS", f"Non-positive warranty claim amount {amount:.2f} detected; must be > 0.00"
        if claim_dt > snapshot_date:
            return False, "RULE_WRN_DATE_VALID", f"Warranty claim date {claim_dt} is in the future relative to snapshot date {snapshot_date}"

    elif dataset_name == "parts":
        p_id = str(record.get("part_id") or "").strip()
        d_id = str(record.get("dealer_id") or "").strip()
        try:
            stock = int(record["stock"])
            lead = int(record["lead_time"])
        except (ValueError, TypeError) as e:
            return False, "RULE_PRT_TYPE_ERROR", f"Invalid stock or lead_time value: {e}"

        if not p_id or not d_id:
            return False, "RULE_PRT_PK_NOT_NULL", "Mandatory part_id or dealer_id is null/empty"
        if stock < 0:
            return False, "RULE_PRT_STOCK_RANGE", f"Negative inventory stock level {stock} detected; must be >= 0"
        if lead < 1:
            return False, "RULE_PRT_LEAD_RANGE", f"Procurement lead time {lead} is invalid; must be >= 1"

    elif dataset_name == "dealers":
        d_id = str(record.get("dealer_id") or "").strip()
        if not d_id:
            return False, "RULE_DLR_NOT_NULL", "Mandatory dealer_id is null or empty"

    elif dataset_name == "components":
        p_id = str(record.get("part_id") or "").strip()
        if not p_id:
            return False, "RULE_CMP_NOT_NULL", "Mandatory part_id is null or empty"

    elif dataset_name == "customers":
        c_id = str(record.get("customer_id") or "").strip()
        if not c_id:
            return False, "RULE_CUST_NOT_NULL", "Mandatory customer_id is null or empty"

    elif dataset_name == "vehicle_customer_map":
        v_id = str(record.get("vehicle_id") or "").strip()
        c_id = str(record.get("customer_id") or "").strip()
        if not v_id or not c_id:
            return False, "RULE_VCM_NOT_NULL", "Mandatory vehicle_id or customer_id is null or empty"

    return True, "", ""


def clean_record(dataset_name: str, record: Dict[str, Any]) -> Dict[str, Any]:
    """Applies standardization and cleaning transformations to valid records for Silver Clean."""
    cleaned = dict(record)
    for k, v in cleaned.items():
        if isinstance(v, str):
            cleaned[k] = v.strip()

    if dataset_name == "diagnostics" and "severity" in cleaned:
        cleaned["severity"] = str(cleaned["severity"]).strip().upper()

    return cleaned


def process_silver_dataset(
    dataset_name: str,
    bronze_dir: str,
    silver_dir: str,
    quarantine_dir: str,
    batch_id: str,
    processed_at: str,
    snapshot_date: str
) -> Dict[str, Any]:
    """
    Reads a single Bronze dataset, applies deduplication and validation,
    and writes Silver Clean and Silver Quarantine datasets.
    """
    bronze_path = os.path.join(bronze_dir, dataset_name)
    if not os.path.isdir(bronze_path):
        raise FileNotFoundError(f"Bronze dataset directory not found: {bronze_path}")

    # Read Bronze dataset strictly using PyArrow dataset API
    dataset = ds.dataset(bronze_path, format="parquet", partitioning="hive")
    bronze_table = dataset.to_table()
    bronze_count = bronze_table.num_rows

    # Convert to Python dict records for deterministic row-level processing
    records = bronze_table.to_pylist()
    key_fields = DEDUPLICATION_KEYS[dataset_name]

    # Deterministic Deduplication:
    # Group records by composite business key
    key_groups: Dict[Tuple, List[Tuple[int, Dict[str, Any]]]] = {}
    for idx, rec in enumerate(records):
        key = tuple(rec.get(kf) for kf in key_fields)
        if key not in key_groups:
            key_groups[key] = []
        key_groups[key].append((idx, rec))

    clean_records = []
    quarantine_records = []

    for key, group in key_groups.items():
        # Deterministic selection:
        # Sort group by _ingested_at descending, tie-break by original row index descending
        # The first record is the selected primary record; subsequent records are duplicates
        group_sorted = sorted(
            group,
            key=lambda x: (str(x[1].get("_ingested_at") or ""), x[0]),
            reverse=True
        )

        primary_idx, primary_rec = group_sorted[0]
        duplicate_entries = group_sorted[1:]

        # 1. Route duplicate records to Quarantine (exact raw values preserved)
        for dup_idx, dup_rec in duplicate_entries:
            q_rec = dict(dup_rec)
            q_rec["_quarantine_rule"] = "DUPLICATE_KEY"
            q_rec["_quarantine_reason"] = f"Duplicate record for key {dict(zip(key_fields, key))}; superseded by primary record"
            q_rec["_quarantined_at"] = processed_at
            quarantine_records.append(q_rec)

        # 2. Validate primary record against domain rules
        is_valid, rule_code, reason = validate_record(dataset_name, primary_rec, snapshot_date)
        if is_valid:
            # Clean and standardize record for Silver Clean
            c_rec = clean_record(dataset_name, primary_rec)
            # Lineage renaming / additions
            c_rec["_bronze_ingested_at"] = c_rec.pop("_ingested_at", None)
            c_rec["_bronze_batch_id"] = c_rec.pop("_batch_id", None)
            c_rec["_silver_processed_at"] = processed_at
            c_rec["_silver_batch_id"] = batch_id
            clean_records.append(c_rec)
        else:
            # Route failed record to Quarantine retaining EXACT raw Bronze domain values
            q_rec = dict(primary_rec)
            q_rec["_quarantine_rule"] = rule_code
            q_rec["_quarantine_reason"] = reason
            q_rec["_quarantined_at"] = processed_at
            quarantine_records.append(q_rec)

    # Absolute Row Conservation Check
    assert len(clean_records) + len(quarantine_records) == bronze_count, (
        f"Row conservation violated for {dataset_name}: "
        f"Bronze={bronze_count} != Clean({len(clean_records)}) + Quarantine({len(quarantine_records)})"
    )

    # 3. Write Silver Clean Dataset
    clean_target_dir = os.path.join(silver_dir, dataset_name)
    os.makedirs(clean_target_dir, exist_ok=True)
    if clean_records:
        clean_table = pa.Table.from_pylist(clean_records)
        if dataset_name in EVENT_DATASETS:
            partitioning = ds.partitioning(
                schema=pa.schema([
                    ("year", pa.int32()),
                    ("month", pa.int32()),
                    ("day", pa.int32())
                ]),
                flavor="hive"
            )
        else:
            partitioning = ds.partitioning(
                schema=pa.schema([("snapshot_date", pa.string())]),
                flavor="hive"
            )

        ds.write_dataset(
            data=clean_table,
            base_dir=clean_target_dir,
            format="parquet",
            partitioning=partitioning,
            file_options=ds.ParquetFileFormat().make_write_options(compression="snappy"),
            existing_data_behavior="overwrite_or_ignore"
        )

    # 4. Write Silver Quarantine Dataset
    quarantine_target_dir = os.path.join(quarantine_dir, dataset_name)
    os.makedirs(quarantine_target_dir, exist_ok=True)
    if quarantine_records:
        quarantine_table = pa.Table.from_pylist(quarantine_records)
        # Quarantine written as Parquet preserving exact fields
        ds.write_dataset(
            data=quarantine_table,
            base_dir=quarantine_target_dir,
            format="parquet",
            file_options=ds.ParquetFileFormat().make_write_options(compression="snappy"),
            existing_data_behavior="overwrite_or_ignore"
        )

    return {
        "dataset": dataset_name,
        "bronze_count": bronze_count,
        "clean_count": len(clean_records),
        "quarantine_count": len(quarantine_records),
        "conservation_verified": (bronze_count == len(clean_records) + len(quarantine_records))
    }


def run_silver_cleaning(
    bronze_dir: str = "data/bronze",
    silver_dir: str = "data/silver",
    quarantine_dir: str = "data/silver/quarantine",
    batch_id: str = None,
    snapshot_date: str = "2026-09-25"
) -> List[Dict[str, Any]]:
    now_utc = datetime.utcnow()
    if not batch_id:
        batch_id = f"BATCH-SILVER-{now_utc.strftime('%Y%m%d-%H%M%S')}"

    processed_at = now_utc.strftime("%Y-%m-%d %H:%M:%S")

    print(f"=== Starting AutoCare Silver Cleaning & Validation ===")
    print(f"Silver Batch ID: {batch_id}")
    print(f"Processed Timestamp: {processed_at} UTC")
    print(f"Bronze Directory: {bronze_dir}")
    print(f"Silver Directory: {silver_dir}")
    print(f"Quarantine Directory: {quarantine_dir}")
    print(f"Deterministic Snapshot Date: {snapshot_date}")
    print("-------------------------------------------------------")

    results = []
    for ds_name in ALL_DATASETS:
        res = process_silver_dataset(
            dataset_name=ds_name,
            bronze_dir=bronze_dir,
            silver_dir=silver_dir,
            quarantine_dir=quarantine_dir,
            batch_id=batch_id,
            processed_at=processed_at,
            snapshot_date=snapshot_date
        )
        results.append(res)
        print(
            f"Dataset: {res['dataset']:<22} | "
            f"Bronze: {res['bronze_count']:<6} | "
            f"Clean: {res['clean_count']:<6} | "
            f"Quarantine: {res['quarantine_count']:<4} | "
            f"Conserved: {res['conservation_verified']}"
        )

    print("-------------------------------------------------------")
    print(f"=== Silver Pipeline Completed Successfully for {len(results)} Datasets ===")
    return results


if __name__ == "__main__":
    args = parse_args()
    run_silver_cleaning(
        bronze_dir=args.bronze_dir,
        silver_dir=args.silver_dir,
        quarantine_dir=args.quarantine_dir,
        batch_id=args.batch_id,
        snapshot_date=args.snapshot_date
    )
