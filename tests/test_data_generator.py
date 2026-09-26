"""Automated Test Suite for AutoCare Intelligence Data Generator & Schema Contracts.

Verifies:
  1. File existence for all required datasets.
  2. Mandatory field presence as per AutoCare_Intelligence.pdf Section 4.
  3. Key uniqueness and no null values in primary keys.
  4. Physical valid-range boundary constraints.
  5. Referential integrity between related entities.
"""

import os
import csv
import re
import pytest

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "raw")

def read_csv_rows(filename):
    filepath = os.path.join(DATA_DIR, filename)
    assert os.path.exists(filepath), f"File {filename} does not exist in {DATA_DIR}"
    with open(filepath, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader), reader.fieldnames

def test_vehicles_schema_and_integrity():
    """Verify vehicles dataset matches Section 4: vehicle_id, model, variant, manufacture_date, dealer_id"""
    rows, fields = read_csv_rows("vehicles.csv")
    expected_fields = ["vehicle_id", "model", "variant", "manufacture_date", "dealer_id"]
    for field in expected_fields:
        assert field in fields, f"Missing required field {field} in vehicles.csv"

    assert len(rows) > 0, "vehicles.csv is empty"
    vehicle_ids = [r["vehicle_id"] for r in rows]
    assert len(vehicle_ids) == len(set(vehicle_ids)), "Duplicate vehicle_id found in vehicles.csv"

    for r in rows:
        assert r["vehicle_id"].startswith("VH-"), f"Invalid vehicle_id format: {r['vehicle_id']}"
        assert r["model"] in ["Apex", "Titan", "Pulse", "Horizon"], f"Unexpected model: {r['model']}"
        assert r["dealer_id"].startswith("DLR-"), f"Invalid dealer_id format: {r['dealer_id']}"

def test_telemetry_schema_and_physics_ranges():
    """Verify telemetry dataset matches Section 4: vehicle_id, timestamp, rpm, temperature, battery, vibration"""
    rows, fields = read_csv_rows("telemetry.csv")
    expected_fields = ["vehicle_id", "timestamp", "rpm", "temperature", "battery", "vibration"]
    for field in expected_fields:
        assert field in fields, f"Missing required field {field} in telemetry.csv"

    assert len(rows) > 0, "telemetry.csv is empty"

    for r in rows[:1000]:  # Sample first 1000 for fast test execution
        rpm = int(r["rpm"])
        temp = float(r["temperature"])
        battery = float(r["battery"])
        vibration = float(r["vibration"])

        assert 0 <= rpm <= 9000, f"RPM out of range: {rpm}"
        assert -40.0 <= temp <= 160.0, f"Temperature out of range: {temp}"
        assert 9.0 <= battery <= 16.0, f"Battery voltage out of range: {battery}"
        assert 0.0 <= vibration <= 15.0, f"Vibration out of range: {vibration}"

def test_diagnostics_schema_and_dtc_format():
    """Verify diagnostics matches Section 4: vehicle_id, timestamp, code, component, severity"""
    rows, fields = read_csv_rows("diagnostics.csv")
    expected_fields = ["vehicle_id", "timestamp", "code", "component", "severity"]
    for field in expected_fields:
        assert field in fields, f"Missing required field {field} in diagnostics.csv"

    assert len(rows) > 0, "diagnostics.csv is empty"
    dtc_pattern = re.compile(r"^[PCBU][0-9]{4}$")

    for r in rows:
        assert dtc_pattern.match(r["code"]), f"DTC code {r['code']} does not match standard pattern"
        assert r["severity"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"], f"Invalid severity: {r['severity']}"

def test_service_schema_and_costs():
    """Verify service dataset matches Section 4: service_id, vehicle_id, dealer_id, visit_date, issue, cost"""
    rows, fields = read_csv_rows("service.csv")
    expected_fields = ["service_id", "vehicle_id", "dealer_id", "visit_date", "issue", "cost"]
    for field in expected_fields:
        assert field in fields, f"Missing required field {field} in service.csv"

    assert len(rows) > 0, "service.csv is empty"
    service_ids = [r["service_id"] for r in rows]
    assert len(service_ids) == len(set(service_ids)), "Duplicate service_id found in service.csv"

    for r in rows:
        cost = float(r["cost"])
        assert cost >= 0.0, f"Negative service cost found: {cost}"
        assert r["vehicle_id"].startswith("VH-")
        assert r["dealer_id"].startswith("DLR-")

def test_warranty_schema_and_amounts():
    """Verify warranty matches Section 4: claim_id, vehicle_id, component, claim_date, amount"""
    rows, fields = read_csv_rows("warranty.csv")
    expected_fields = ["claim_id", "vehicle_id", "component", "claim_date", "amount"]
    for field in expected_fields:
        assert field in fields, f"Missing required field {field} in warranty.csv"

    assert len(rows) > 0, "warranty.csv is empty"
    claim_ids = [r["claim_id"] for r in rows]
    assert len(claim_ids) == len(set(claim_ids)), "Duplicate claim_id found in warranty.csv"

    for r in rows:
        amount = float(r["amount"])
        assert amount > 0.0, f"Invalid claim amount: {amount}"
        assert r["vehicle_id"].startswith("VH-")

def test_parts_schema_and_lead_times():
    """Verify parts matches Section 4: part_id, dealer_id, stock, lead_time"""
    rows, fields = read_csv_rows("parts.csv")
    expected_fields = ["part_id", "dealer_id", "stock", "lead_time"]
    for field in expected_fields:
        assert field in fields, f"Missing required field {field} in parts.csv"

    assert len(rows) > 0, "parts.csv is empty"

    for r in rows:
        stock = int(r["stock"])
        lead_time = int(r["lead_time"])
        assert stock >= 0, f"Negative stock level: {stock}"
        assert lead_time >= 1, f"Lead time must be at least 1 day: {lead_time}"
        assert r["part_id"].startswith("PRT-")
        assert r["dealer_id"].startswith("DLR-")

def test_referential_integrity():
    """Verify foreign key links between service/warranty/parts and vehicles/dealers/components."""
    vehicles, _ = read_csv_rows("vehicles.csv")
    vehicle_ids = {v["vehicle_id"] for v in vehicles}

    dealers, _ = read_csv_rows("dealers.csv")
    dealer_ids = {d["dealer_id"] for d in dealers}

    components, _ = read_csv_rows("components.csv")
    part_ids = {c["part_id"] for c in components}

    services, _ = read_csv_rows("service.csv")
    for s in services:
        assert s["vehicle_id"] in vehicle_ids, f"Orphaned service record for vehicle {s['vehicle_id']}"
        assert s["dealer_id"] in dealer_ids, f"Orphaned service record for dealer {s['dealer_id']}"

    warranties, _ = read_csv_rows("warranty.csv")
    for w in warranties:
        assert w["vehicle_id"] in vehicle_ids, f"Orphaned warranty claim for vehicle {w['vehicle_id']}"

    parts, _ = read_csv_rows("parts.csv")
    for p in parts:
        assert p["dealer_id"] in dealer_ids, f"Orphaned part dealer link {p['dealer_id']}"
        assert p["part_id"] in part_ids, f"Orphaned part component link {p['part_id']}"

    customers, _ = read_csv_rows("customers.csv")
    cust_ids = {c["customer_id"] for c in customers}
    maps, _ = read_csv_rows("vehicle_customer_map.csv")
    for m in maps:
        assert m["vehicle_id"] in vehicle_ids, f"Orphaned vehicle mapping {m['vehicle_id']}"
        assert m["customer_id"] in cust_ids, f"Orphaned customer mapping {m['customer_id']}"

def test_no_null_values_in_any_dataset():
    """Verify zero null or empty values across all generated datasets."""
    all_files = [
        "vehicles.csv", "telemetry.csv", "diagnostics.csv",
        "service.csv", "warranty.csv", "parts.csv",
        "dealers.csv", "components.csv", "customers.csv",
        "vehicle_customer_map.csv"
    ]
    for filename in all_files:
        rows, fields = read_csv_rows(filename)
        for idx, row in enumerate(rows):
            for col in fields:
                val = row.get(col)
                assert val is not None and val.strip() != "", (
                    f"Null/empty value in {filename} at row {idx} for column '{col}'"
                )

def test_no_duplicate_rows_in_any_dataset():
    """Verify zero duplicate rows across all generated datasets."""
    all_files = [
        "vehicles.csv", "telemetry.csv", "diagnostics.csv",
        "service.csv", "warranty.csv", "parts.csv",
        "dealers.csv", "components.csv", "customers.csv",
        "vehicle_customer_map.csv"
    ]
    for filename in all_files:
        rows, fields = read_csv_rows(filename)
        tuples = [tuple(r[f] for f in fields) for r in rows]
        assert len(tuples) == len(set(tuples)), f"Duplicate rows detected in {filename}"

def test_auxiliary_dimensions_validity():
    """Verify supporting dimensions: dealers, components, customers."""
    dealers, d_fields = read_csv_rows("dealers.csv")
    assert set(["dealer_id", "name", "region", "city", "bays"]).issubset(set(d_fields))
    assert len(dealers) >= 5

    components, c_fields = read_csv_rows("components.csv")
    assert set(["part_id", "name", "category", "lifespan_km", "base_cost", "lead_time_days"]).issubset(set(c_fields))
    assert len(components) >= 8

    customers, cust_fields = read_csv_rows("customers.csv")
    assert set(["customer_id", "customer_name", "segment", "region"]).issubset(set(cust_fields))
    assert len(customers) >= 20

def test_seed_reproducibility(tmp_path):
    """Verify that identical random seeds and end-dates generate identical datasets."""
    from data_generator.generate_all import generate_datasets

    dir1 = tmp_path / "run1"
    dir2 = tmp_path / "run2"

    generate_datasets(vehicles_count=10, days_count=5, samples_per_day=2, output_dir=str(dir1), seed=99, end_date_str="2026-09-25")
    generate_datasets(vehicles_count=10, days_count=5, samples_per_day=2, output_dir=str(dir2), seed=99, end_date_str="2026-09-25")

    for fname in ["vehicles.csv", "telemetry.csv", "diagnostics.csv", "service.csv", "warranty.csv", "parts.csv"]:
        content1 = (dir1 / fname).read_text(encoding="utf-8")
        content2 = (dir2 / fname).read_text(encoding="utf-8")
        assert content1 == content2, f"Seed reproducibility failed for {fname}"

