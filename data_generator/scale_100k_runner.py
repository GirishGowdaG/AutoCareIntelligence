"""Isolated 100k+ Scale Dataset Generator & Medallion Pipeline Runner.

Generates the 120,950-record scale_100k dataset profile into data/scale_100k/raw/
and executes Bronze ingestion (data/scale_100k/bronze/) and Silver cleaning
(data/scale_100k/silver/) without modifying any baseline data or pipeline modules.

Target Record Distribution (120,950 total):
  - vehicles.csv:               1,000
  - customers.csv:                800
  - vehicle_customer_map.csv:   1,000
  - dealers.csv:                  100
  - components.csv:                50
  - parts.csv:                  1,000
  - telemetry.csv:            100,000
  - diagnostics.csv:           10,000
  - service.csv:                5,000
  - warranty.csv:               2,000
"""

import os
import csv
import json
import time
import random
import argparse
import tracemalloc
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple

from data_generator.config import (
    DEALERS as BASELINE_DEALERS,
    MODELS,
    COMPONENTS as BASELINE_COMPONENTS,
    DTC_CATALOG,
)
from data_generator.vehicle_physics import VehiclePhysicsSimulator
from lakehouse.bronze_ingest import run_bronze_ingestion
from lakehouse.silver_clean import run_silver_cleaning

PROJECT_ROOT = Path(__file__).resolve().parent.parent

PROTECTED_DIRS = [
    (PROJECT_ROOT / "data" / "raw").resolve(),
    (PROJECT_ROOT / "data" / "bronze").resolve(),
    (PROJECT_ROOT / "data" / "silver").resolve(),
    (PROJECT_ROOT / "data" / "warehouse").resolve(),
]

TARGET_COUNTS = {
    "vehicles": 1000,
    "customers": 800,
    "vehicle_customer_map": 1000,
    "dealers": 100,
    "components": 50,
    "parts": 1000,
    "telemetry": 100000,
    "diagnostics": 10000,
    "service": 5000,
    "warranty": 2000,
}

EXPECTED_TOTAL_ROWS = sum(TARGET_COUNTS.values())  # 120,950


def validate_isolated_path(target_path: str) -> Path:
    """Hard path-isolation guard: prevents writing to or inside protected baseline directories."""
    resolved = Path(target_path).resolve()
    for protected in PROTECTED_DIRS:
        if resolved == protected or protected in resolved.parents or resolved in protected.parents:
            # Allow PROJECT_ROOT/data as a parent of data/scale_100k, so only block if resolved == data or inside protected
            if resolved == PROJECT_ROOT / "data" or resolved == PROJECT_ROOT:
                raise ValueError(
                    f"Path safety violation: '{resolved}' overlaps with protected directory tree."
                )
        if resolved == protected or protected in resolved.parents:
            raise ValueError(
                f"Path safety violation: target path '{resolved}' targets protected baseline directory '{protected}'."
            )
    return resolved


def build_scale_dealers(target_count: int = 100) -> List[Dict[str, Any]]:
    """Preserves the 5 canonical dealers and generates 95 additional dealers."""
    dealers = [dict(d) for d in BASELINE_DEALERS]
    regions_cities = [
        ("North", ["Chicago", "Minneapolis", "Milwaukee", "Madison", "Duluth"]),
        ("South", ["Dallas", "Houston", "Austin", "Atlanta", "Charlotte"]),
        ("West", ["Seattle", "Portland", "San Jose", "Denver", "Phoenix"]),
        ("East", ["New York", "Boston", "Philadelphia", "Baltimore", "Pittsburgh"]),
        ("Midwest", ["Detroit", "Columbus", "Indianapolis", "St. Louis", "Kansas City"]),
    ]
    prefixes = [
        "Premier", "Summit", "Vanguard", "Horizon", "Continental",
        "Liberty", "Pioneer", "Crestview", "Heritage", "Keystone",
        "Velocity", "Sterling", "Precision", "National", "Crown",
        "Gateway", "Prime", "Atlas", "Encore", "Meridian",
    ]
    for idx in range(len(dealers) + 1, target_count + 1):
        reg_idx = (idx - 1) % len(regions_cities)
        region, cities = regions_cities[reg_idx]
        city = cities[((idx - 1) // len(regions_cities)) % len(cities)]
        prefix = prefixes[(idx - 1) % len(prefixes)]
        bays = 8 + ((idx * 3) % 18)  # 8..25 bays (>= 1)
        dealers.append({
            "dealer_id": f"DLR-{idx:03d}",
            "name": f"{prefix} {city} AutoCare #{idx:03d}",
            "region": region,
            "city": city,
            "bays": bays,
        })
    return dealers


def build_scale_components(target_count: int = 50) -> List[Dict[str, Any]]:
    """
    Preserves the exact 8 baseline components and adds 42 additional components
    using strictly the 6 canonical categories:
      Powertrain, Cooling System, Electrical, Braking, Chassis, Sensors
    All 50 part_ids and 50 names are strictly unique.
    """
    components = [dict(c) for c in BASELINE_COMPONENTS]

    additional_specs = [
        # Powertrain (7 additional)
        ("PRT-ENG-09", "Turbocharger Boost Assembly", "Powertrain", 160000, 1450.0, 10),
        ("PRT-ENG-10", "Direct Fuel Injector Rail", "Powertrain", 140000, 620.0, 6),
        ("PRT-ENG-11", "Timing Chain Tensioner Kit", "Powertrain", 180000, 540.0, 7),
        ("PRT-TRN-12", "Dual-Clutch Torque Converter", "Powertrain", 190000, 1850.0, 14),
        ("PRT-TRN-13", "Rear Differential Gear Set", "Powertrain", 220000, 1320.0, 12),
        ("PRT-ENG-14", "Variable Valve Timing Solenoid", "Powertrain", 130000, 380.0, 5),
        ("PRT-TRN-15", "Drive Axle Half-Shaft Assembly", "Powertrain", 150000, 490.0, 6),
        # Cooling System (7 additional)
        ("PRT-CLG-16", "Aluminum Crossflow Radiator", "Cooling System", 150000, 680.0, 7),
        ("PRT-CLG-17", "Brushless Cooling Fan Module", "Cooling System", 120000, 410.0, 5),
        ("PRT-CLG-18", "Thermal Expansion Valve Unit", "Cooling System", 110000, 340.0, 4),
        ("PRT-CLG-19", "Intercooler Charge Air Core", "Cooling System", 170000, 790.0, 8),
        ("PRT-CLG-20", "EV Battery Chiller Heat Exchanger", "Cooling System", 160000, 920.0, 9),
        ("PRT-CLG-21", "Heater Core Bypass Manifold", "Cooling System", 135000, 360.0, 5),
        ("PRT-CLG-22", "Pressurized Coolant Reservoir Tank", "Cooling System", 125000, 280.0, 3),
        # Electrical (7 additional)
        ("PRT-ELC-23", "High-Voltage DC-DC Converter", "Electrical", 180000, 1150.0, 11),
        ("PRT-ELC-24", "Powertrain Control Module ECM", "Electrical", 200000, 980.0, 9),
        ("PRT-ELC-25", "Body Control Gateway Module", "Electrical", 175000, 520.0, 6),
        ("PRT-ELC-26", "Starter Motor Solenoid Assembly", "Electrical", 130000, 390.0, 4),
        ("PRT-ELC-27", "Smart Junction Fuse Distribution Box", "Electrical", 190000, 440.0, 5),
        ("PRT-ELC-28", "Onboard Charging Inverter Unit", "Electrical", 185000, 1580.0, 13),
        ("PRT-ELC-29", "Main CAN Bus Wiring Harness", "Electrical", 210000, 670.0, 8),
        # Braking (7 additional)
        ("PRT-BRK-30", "Rear Vented Brake Rotor Set", "Braking", 80000, 270.0, 4),
        ("PRT-BRK-31", "Hydraulic ABS Modulator Pump", "Braking", 160000, 1120.0, 9),
        ("PRT-BRK-32", "Electronic Parking Brake Caliper", "Braking", 120000, 460.0, 5),
        ("PRT-BRK-33", "Tandem Brake Master Cylinder", "Braking", 140000, 395.0, 5),
        ("PRT-BRK-34", "Vacuum Brake Booster Assembly", "Braking", 150000, 430.0, 6),
        ("PRT-BRK-35", "Regenerative Blending Actuator", "Braking", 165000, 890.0, 8),
        ("PRT-BRK-36", "Stainless Braided Brake Line Kit", "Braking", 130000, 260.0, 3),
        # Chassis (7 additional)
        ("PRT-SUS-37", "Electric Power Steering Rack", "Chassis", 170000, 1280.0, 10),
        ("PRT-SUS-38", "Front Lower Control Arm Pair", "Chassis", 115000, 480.0, 5),
        ("PRT-SUS-39", "Anti-Roll Stabilizer Link Bar", "Chassis", 105000, 310.0, 4),
        ("PRT-SUS-40", "Sealed Wheel Hub Bearing Unit", "Chassis", 110000, 350.0, 4),
        ("PRT-SUS-41", "Rear Multi-Link Subframe Bushings", "Chassis", 140000, 420.0, 6),
        ("PRT-SUS-42", "Active Air Suspension Compressor", "Chassis", 130000, 960.0, 9),
        ("PRT-SUS-43", "Steering Column Intermediate Shaft", "Chassis", 160000, 510.0, 6),
        # Sensors (7 additional)
        ("PRT-SEN-44", "Mass Air Flow Sensor Module", "Sensors", 95000, 240.0, 3),
        ("PRT-SEN-45", "Manifold Absolute Pressure Sensor", "Sensors", 100000, 220.0, 3),
        ("PRT-SEN-46", "Crankshaft Position Hall Sensor", "Sensors", 115000, 250.0, 3),
        ("PRT-SEN-47", "Wheel Speed ABS Hall Sensor", "Sensors", 90000, 230.0, 2),
        ("PRT-SEN-48", "Coolant Temperature Thermistor", "Sensors", 105000, 195.0, 2),
        ("PRT-SEN-49", "Knock Piezoelectric Accelerometer", "Sensors", 120000, 275.0, 4),
        ("PRT-SEN-50", "Battery Current Shunt Monitor", "Sensors", 130000, 315.0, 4),
    ]

    for part_id, name, category, lifespan_km, base_cost, lead_time_days in additional_specs:
        components.append({
            "part_id": part_id,
            "name": name,
            "category": category,
            "lifespan_km": lifespan_km,
            "base_cost": base_cost,
            "lead_time_days": lead_time_days,
        })

    assert len(components) == target_count, f"Expected {target_count} components, got {len(components)}"
    return components


def get_directory_size_mb(directory: Path) -> float:
    """Calculates total size of all files under directory in megabytes."""
    total_bytes = 0
    if directory.exists():
        for root, _, files in os.walk(directory):
            for fname in files:
                fpath = Path(root) / fname
                if fpath.is_file():
                    total_bytes += fpath.stat().st_size
    return round(total_bytes / (1024 * 1024), 3)


def generate_scale_100k_raw(
    raw_dir: str = "data/scale_100k/raw",
    seed: int = 42,
    end_date_str: str = "2026-09-25",
) -> Dict[str, Any]:
    """
    Generates the 10 CSV files in raw_dir with exact target row counts (120,950 total).
    Reuses VehiclePhysicsSimulator and DTC_CATALOG without modifying existing code.
    """
    resolved_raw = validate_isolated_path(raw_dir)
    os.makedirs(resolved_raw, exist_ok=True)

    random.seed(seed)
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
    days_count = 100
    start_date = end_date - timedelta(days=days_count)

    # 1. Dealers (100 rows)
    dealers = build_scale_dealers(TARGET_COUNTS["dealers"])
    dealers_file = resolved_raw / "dealers.csv"
    with open(dealers_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["dealer_id", "name", "region", "city", "bays"])
        writer.writeheader()
        writer.writerows(dealers)

    # 2. Components (50 rows)
    components = build_scale_components(TARGET_COUNTS["components"])
    components_file = resolved_raw / "components.csv"
    with open(components_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["part_id", "name", "category", "lifespan_km", "base_cost", "lead_time_days"]
        )
        writer.writeheader()
        writer.writerows(components)

    # 3. Customers (800 rows)
    customers = []
    first_names = [
        "James", "Maria", "Robert", "Elena", "Michael", "Sophia", "David", "Amina",
        "Chen", "Priya", "Daniel", "Olivia", "Marcus", "Hannah", "Carlos", "Fatima",
    ]
    last_names = [
        "Smith", "Rodriguez", "Johnson", "Ivanov", "Williams", "Patel", "Brown", "Nguyen",
        "Kim", "Taylor", "Martinez", "Anderson", "Thomas", "Lee", "Walker", "Hall",
    ]
    segments = ["Consumer-Individual", "Corporate-Fleet", "RideShare-Commercial"]
    regions = ["North", "South", "East", "West", "Midwest"]

    for i in range(1, TARGET_COUNTS["customers"] + 1):
        cust_id = f"CUST-{i:05d}"
        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        customers.append({
            "customer_id": cust_id,
            "customer_name": name,
            "segment": random.choice(segments),
            "region": random.choice(regions),
        })

    customers_file = resolved_raw / "customers.csv"
    with open(customers_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["customer_id", "customer_name", "segment", "region"])
        writer.writeheader()
        writer.writerows(customers)

    # 4. Vehicles (1,000 rows) & VehiclePhysicsSimulators
    vehicles = []
    vehicle_simulators: Dict[str, VehiclePhysicsSimulator] = {}
    for i in range(1, TARGET_COUNTS["vehicles"] + 1):
        v_id = f"VH-{10000 + i}"
        model_choice = random.choice(MODELS)
        variant_choice = random.choice(model_choice["variants"])
        # Manufacture date between 180 and 1000 days before end_date (always < start_date)
        mfg_days_ago = random.randint(180, 1000)
        mfg_date = (end_date - timedelta(days=mfg_days_ago)).strftime("%Y-%m-%d")
        dealer_choice = dealers[(i - 1) % len(dealers)]["dealer_id"]
        vehicles.append({
            "vehicle_id": v_id,
            "model": model_choice["model"],
            "variant": variant_choice,
            "manufacture_date": mfg_date,
            "dealer_id": dealer_choice,
        })
        vehicle_simulators[v_id] = VehiclePhysicsSimulator(
            vehicle_id=v_id,
            model=model_choice["model"],
            engine_type=model_choice["engine_type"],
        )

    vehicles_file = resolved_raw / "vehicles.csv"
    with open(vehicles_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["vehicle_id", "model", "variant", "manufacture_date", "dealer_id"]
        )
        writer.writeheader()
        writer.writerows(vehicles)

    # 5. Vehicle-Customer Map (1,000 rows)
    vehicle_customer_mappings = []
    for idx, v in enumerate(vehicles):
        assigned_cust_id = customers[idx % len(customers)]["customer_id"]
        mfg_dt = datetime.strptime(v["manufacture_date"], "%Y-%m-%d")
        reg_date = (mfg_dt + timedelta(days=14)).strftime("%Y-%m-%d")
        vehicle_customer_mappings.append({
            "vehicle_id": v["vehicle_id"],
            "customer_id": assigned_cust_id,
            "registration_date": reg_date,
        })

    map_file = resolved_raw / "vehicle_customer_map.csv"
    with open(map_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["vehicle_id", "customer_id", "registration_date"])
        writer.writeheader()
        writer.writerows(vehicle_customer_mappings)

    # 6. Telemetry (100,000 rows) & Diagnostics (10,000 rows)
    # Schedule: 1,000 vehicles x 25 active days x 4 disjoint intra-day time slots = 100,000 steps.
    # Each vehicle has exactly 10 anomalous steps (grouped into two 5-step fault episodes)
    # totaling 1,000 x 10 = 10,000 physically correlated diagnostic events.
    dtc_by_code = {entry["code"]: entry for entry in DTC_CATALOG}
    state_to_dtc_codes = {
        VehiclePhysicsSimulator.STATE_OVERHEATING: ["P0217", "P0420"],
        VehiclePhysicsSimulator.STATE_LOW_BATTERY: ["P0562", "B0001", "U0100"],
        VehiclePhysicsSimulator.STATE_HIGH_VIBRATION: ["P0300", "C0035", "C0561"],
    }
    fault_states = [
        VehiclePhysicsSimulator.STATE_OVERHEATING,
        VehiclePhysicsSimulator.STATE_LOW_BATTERY,
        VehiclePhysicsSimulator.STATE_HIGH_VIBRATION,
    ]

    # Disjoint hour ranges for the 4 daily samples to guarantee strictly increasing timestamps
    slot_hour_ranges = [(6, 9), (10, 13), (14, 17), (18, 21)]

    telemetry_records = []
    diagnostics_records = []

    for v_idx, v in enumerate(vehicles):
        v_id = v["vehicle_id"]
        sim = vehicle_simulators[v_id]

        # Select 25 sorted active day offsets out of 100 days (0..99)
        active_day_offsets = sorted(random.sample(range(days_count), k=25))

        # Schedule 2 contiguous 5-step fault episodes within the 100 steps (steps 0..99)
        ep1_start = random.randint(5, 40)
        ep2_start = random.randint(55, 90)
        ep1_state = fault_states[v_idx % 3]
        ep2_state = fault_states[(v_idx + 1) % 3]

        step_idx = 0
        for day_offset in active_day_offsets:
            curr_day = start_date + timedelta(days=day_offset)
            for slot_idx in range(4):
                h_min, h_max = slot_hour_ranges[slot_idx]
                ts_dt = curr_day.replace(
                    hour=random.randint(h_min, h_max),
                    minute=random.randint(0, 59),
                    second=random.randint(0, 59),
                )
                ts_str = ts_dt.strftime("%Y-%m-%d %H:%M:%S")

                if ep1_start <= step_idx < ep1_start + 5:
                    active_fault = ep1_state
                elif ep2_start <= step_idx < ep2_start + 5:
                    active_fault = ep2_state
                else:
                    active_fault = None

                if active_fault is not None:
                    telemetry, dtc = sim.step(is_driving=True, force_anomaly_type=active_fault)
                    # Select verified DTC from DTC_CATALOG matching the physical fault state
                    # (70% primary simulator DTC, 30% secondary correlated catalog DTC)
                    if random.random() < 0.70 and dtc is not None:
                        chosen_dtc = dtc
                    else:
                        code_choice = random.choice(state_to_dtc_codes[active_fault])
                        cat_entry = dtc_by_code[code_choice]
                        chosen_dtc = {
                            "code": cat_entry["code"],
                            "component": cat_entry["component"],
                            "severity": cat_entry["severity"],
                        }

                    diagnostics_records.append({
                        "vehicle_id": v_id,
                        "timestamp": ts_str,
                        "code": chosen_dtc["code"],
                        "component": chosen_dtc["component"],
                        "severity": chosen_dtc["severity"],
                    })
                else:
                    # Force deterministic normal step without modifying vehicle_physics.py:
                    # Setting state_countdown = 1 makes step() decrement 1 -> 0, set STATE_NORMAL,
                    # and skip the random 3% transition branch.
                    sim.state_countdown = 1
                    telemetry, dtc = sim.step(is_driving=True, force_anomaly_type=None)
                    assert dtc is None, "Normal step must not emit a DTC event"

                telemetry_records.append({
                    "vehicle_id": v_id,
                    "timestamp": ts_str,
                    "rpm": telemetry["rpm"],
                    "temperature": telemetry["temperature"],
                    "battery": telemetry["battery"],
                    "vibration": telemetry["vibration"],
                })
                step_idx += 1

    telemetry_file = resolved_raw / "telemetry.csv"
    with open(telemetry_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["vehicle_id", "timestamp", "rpm", "temperature", "battery", "vibration"]
        )
        writer.writeheader()
        writer.writerows(telemetry_records)

    diagnostics_file = resolved_raw / "diagnostics.csv"
    with open(diagnostics_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["vehicle_id", "timestamp", "code", "component", "severity"]
        )
        writer.writeheader()
        writer.writerows(diagnostics_records)

    # 7. Service Visits (5,000 rows) & 8. Warranty Claims (2,000 rows)
    # Each of the 1,000 vehicles has 5 chronological service visits within the 100-day window.
    # 3 of the 5 visits per vehicle (3,000 total) are Component Replacement repairs (cost > 350.0)
    # linked directly to one of the 50 components.
    # 2 of the 5 visits per vehicle (2,000 total) are Routine Maintenance visits (cost <= 350.0).
    routine_issues = [
        ("Scheduled routine maintenance and multi-point inspection", 1.5),
        ("Synthetic oil and filter service with fluid top-off", 1.2),
        ("Four-wheel alignment and tire rotation inspection", 1.8),
        ("Brake fluid flush and cabin air filter replacement", 2.0),
    ]
    labor_rate = 110.0

    service_candidates = []
    for v in vehicles:
        visit_day_offsets = sorted(random.sample(range(days_count), k=5))
        # Randomly choose 3 indices out of 5 to be component replacement visits
        repair_slots = set(random.sample(range(5), k=3))
        for slot_i, day_offset in enumerate(visit_day_offsets):
            visit_dt = (start_date + timedelta(days=day_offset)).strftime("%Y-%m-%d")
            if slot_i in repair_slots:
                comp = random.choice(components)
                labor_hours = round(random.uniform(2.0, 4.5), 1)
                labor_cost = round(labor_hours * labor_rate, 2)
                parts_cost = round(comp["base_cost"] * random.uniform(1.05, 1.25), 2)
                total_cost = round(max(365.0, labor_cost + parts_cost), 2)
                issue_desc = f"{comp['name']} replacement and {comp['category'].lower()} diagnostic test"
                service_candidates.append({
                    "vehicle_id": v["vehicle_id"],
                    "dealer_id": v["dealer_id"],
                    "visit_date": visit_dt,
                    "issue": issue_desc,
                    "cost": total_cost,
                    "_repaired_component": comp["name"],
                })
            else:
                r_issue, r_hours = random.choice(routine_issues)
                total_cost = round(r_hours * labor_rate + random.uniform(25.0, 85.0), 2)
                service_candidates.append({
                    "vehicle_id": v["vehicle_id"],
                    "dealer_id": v["dealer_id"],
                    "visit_date": visit_dt,
                    "issue": r_issue,
                    "cost": total_cost,
                    "_repaired_component": None,
                })

    # Sort all 5,000 service visits chronologically by visit_date, then vehicle_id
    service_candidates.sort(key=lambda x: (x["visit_date"], x["vehicle_id"]))

    services = []
    eligible_repair_services = []
    for idx, item in enumerate(service_candidates, start=50001):
        srv_row = {
            "service_id": f"SRV-{idx}",
            "vehicle_id": item["vehicle_id"],
            "dealer_id": item["dealer_id"],
            "visit_date": item["visit_date"],
            "issue": item["issue"],
            "cost": item["cost"],
        }
        services.append(srv_row)
        if item["_repaired_component"] is not None and item["cost"] > 350.0:
            eligible_repair_services.append((srv_row, item["_repaired_component"]))

    service_file = resolved_raw / "service.csv"
    with open(service_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["service_id", "vehicle_id", "dealer_id", "visit_date", "issue", "cost"]
        )
        writer.writeheader()
        writer.writerows(services)

    # Deterministically select exactly 2,000 warranty claims from the 3,000 eligible part-repair visits
    selected_warranty_repairs = random.sample(eligible_repair_services, k=TARGET_COUNTS["warranty"])
    selected_warranty_repairs.sort(key=lambda x: (x[0]["visit_date"], x[0]["service_id"]))

    warranties = []
    for idx, (srv_row, comp_name) in enumerate(selected_warranty_repairs, start=90001):
        claim_amount = round(srv_row["cost"] * random.uniform(0.75, 0.95), 2)
        warranties.append({
            "claim_id": f"CLM-{idx}",
            "vehicle_id": srv_row["vehicle_id"],
            "component": comp_name,
            "claim_date": srv_row["visit_date"],
            "amount": claim_amount,
        })

    warranty_file = resolved_raw / "warranty.csv"
    with open(warranty_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["claim_id", "vehicle_id", "component", "claim_date", "amount"]
        )
        writer.writeheader()
        writer.writerows(warranties)

    # 9. Parts Inventory (1,000 rows: 100 dealers x 10 distinct parts per dealer)
    parts_inventory = []
    num_comps = len(components)
    for d_idx, d in enumerate(dealers):
        for offset in range(10):
            comp = components[(d_idx * 10 + offset) % num_comps]
            stock = random.randint(1, 40)
            lead_time = max(1, comp["lead_time_days"] + random.randint(-1, 3))
            parts_inventory.append({
                "part_id": comp["part_id"],
                "dealer_id": d["dealer_id"],
                "stock": stock,
                "lead_time": lead_time,
            })

    parts_file = resolved_raw / "parts.csv"
    with open(parts_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["part_id", "dealer_id", "stock", "lead_time"])
        writer.writeheader()
        writer.writerows(parts_inventory)

    generated_counts = {
        "vehicles": len(vehicles),
        "customers": len(customers),
        "vehicle_customer_map": len(vehicle_customer_mappings),
        "dealers": len(dealers),
        "components": len(components),
        "parts": len(parts_inventory),
        "telemetry": len(telemetry_records),
        "diagnostics": len(diagnostics_records),
        "service": len(services),
        "warranty": len(warranties),
    }

    for k, expected in TARGET_COUNTS.items():
        assert generated_counts[k] == expected, f"Count mismatch for {k}: {generated_counts[k]} != {expected}"

    return {
        "raw_dir": str(resolved_raw),
        "counts": generated_counts,
        "total_rows": sum(generated_counts.values()),
    }


def _measure_stage(stage_name: str, func, *args, **kwargs) -> Tuple[Any, Dict[str, Any]]:
    """Measures wall-clock time, rows/sec, and peak memory allocation for a pipeline stage."""
    tracemalloc.start()
    t0 = time.perf_counter()
    result = func(*args, **kwargs)
    elapsed = time.perf_counter() - t0
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    metrics = {
        "stage": stage_name,
        "wall_time_sec": round(elapsed, 4),
        "throughput_rows_per_sec": round(EXPECTED_TOTAL_ROWS / max(elapsed, 1e-6), 2),
        "peak_memory_mb": round(peak_bytes / (1024 * 1024), 3),
    }
    return result, metrics


def run_scale_100k_pipeline(
    base_dir: str = "data/scale_100k",
    seed: int = 42,
    end_date_str: str = "2026-09-25",
    batch_id: str = "BATCH-SCALE100K-20260925",
) -> Dict[str, Any]:
    """
    Executes the full isolated scale_100k pipeline:
      1. Raw CSV generation (120,950 rows)
      2. Bronze Parquet ingestion
      3. Silver validation & deduplication
      4. Empirical performance benchmarking
    """
    resolved_base = validate_isolated_path(base_dir)
    raw_dir = resolved_base / "raw"
    bronze_dir = resolved_base / "bronze"
    silver_dir = resolved_base / "silver"
    quarantine_dir = silver_dir / "quarantine"

    for p in (raw_dir, bronze_dir, silver_dir, quarantine_dir):
        validate_isolated_path(str(p))

    # Clean any prior scale_100k Bronze/Silver artifacts to avoid duplicate partition appends
    import shutil
    if bronze_dir.exists():
        shutil.rmtree(bronze_dir)
    if silver_dir.exists():
        shutil.rmtree(silver_dir)

    # Stage 1: Generate Raw CSVs
    gen_res, gen_metrics = _measure_stage(
        "raw_generation",
        generate_scale_100k_raw,
        raw_dir=str(raw_dir),
        seed=seed,
        end_date_str=end_date_str,
    )
    gen_metrics["disk_usage_mb"] = get_directory_size_mb(raw_dir)

    # Stage 2: Bronze Ingestion (using existing unmodified run_bronze_ingestion)
    bronze_res, bronze_metrics = _measure_stage(
        "bronze_ingestion",
        run_bronze_ingestion,
        source_dir=str(raw_dir),
        output_dir=str(bronze_dir),
        batch_id=batch_id,
        snapshot_date=end_date_str,
    )
    bronze_metrics["disk_usage_mb"] = get_directory_size_mb(bronze_dir)

    # Stage 3: Silver Cleaning (using existing unmodified run_silver_cleaning)
    silver_res, silver_metrics = _measure_stage(
        "silver_cleaning",
        run_silver_cleaning,
        bronze_dir=str(bronze_dir),
        silver_dir=str(silver_dir),
        quarantine_dir=str(quarantine_dir),
        batch_id=f"{batch_id}-SILVER",
        snapshot_date=end_date_str,
    )
    silver_metrics["disk_usage_mb"] = get_directory_size_mb(silver_dir)

    summary = {
        "profile": "scale_100k",
        "seed": seed,
        "snapshot_date": end_date_str,
        "total_rows": gen_res["total_rows"],
        "counts": gen_res["counts"],
        "bronze_results": bronze_res,
        "silver_results": silver_res,
        "benchmarks": {
            "raw_generation": gen_metrics,
            "bronze_ingestion": bronze_metrics,
            "silver_cleaning": silver_metrics,
            "total_wall_time_sec": round(
                gen_metrics["wall_time_sec"]
                + bronze_metrics["wall_time_sec"]
                + silver_metrics["wall_time_sec"],
                4,
            ),
            "total_disk_usage_mb": round(
                gen_metrics["disk_usage_mb"]
                + bronze_metrics["disk_usage_mb"]
                + silver_metrics["disk_usage_mb"],
                3,
            ),
        },
    }

    manifest_path = resolved_base / "_scale_100k_benchmark.json"
    with open(manifest_path, mode="w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n=== scale_100k Benchmark Summary ===")
    for stage_key in ("raw_generation", "bronze_ingestion", "silver_cleaning"):
        m = summary["benchmarks"][stage_key]
        print(
            f"{m['stage']:<20} | Time: {m['wall_time_sec']:>7.3f}s | "
            f"Throughput: {m['throughput_rows_per_sec']:>10.1f} rows/s | "
            f"Peak RAM: {m['peak_memory_mb']:>7.2f} MB | "
            f"Disk: {m['disk_usage_mb']:>6.2f} MB"
        )
    print(
        f"TOTAL Wall Time: {summary['benchmarks']['total_wall_time_sec']:.3f}s | "
        f"TOTAL Disk Usage: {summary['benchmarks']['total_disk_usage_mb']:.2f} MB"
    )
    return summary


def parse_args():
    parser = argparse.ArgumentParser(description="Run isolated scale_100k dataset & lakehouse benchmark")
    parser.add_argument(
        "--base-dir",
        type=str,
        default="data/scale_100k",
        help="Isolated root directory for scale_100k artifacts (default: data/scale_100k)",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    parser.add_argument(
        "--end-date",
        type=str,
        default="2026-09-25",
        help="Deterministic reference date YYYY-MM-DD (default: 2026-09-25)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_scale_100k_pipeline(
        base_dir=args.base_dir,
        seed=args.seed,
        end_date_str=args.end_date,
    )
