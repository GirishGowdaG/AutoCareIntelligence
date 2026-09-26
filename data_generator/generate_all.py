"""Master Synthetic Data Generator for AutoCare Intelligence.

Generates all 6 datasets required by AutoCare_Intelligence.pdf Section 4:
  1. vehicles (vehicle_id, model, variant, manufacture_date, dealer_id)
  2. telemetry (vehicle_id, timestamp, rpm, temperature, battery, vibration)
  3. diagnostics (vehicle_id, timestamp, code, component, severity)
  4. service (service_id, vehicle_id, dealer_id, visit_date, issue, cost)
  5. warranty (claim_id, vehicle_id, component, claim_date, amount)
  6. parts (part_id, dealer_id, stock, lead_time)
"""

import os
import argparse
import random
import csv
from datetime import datetime, timedelta
from typing import List, Dict, Any

from data_generator.config import (
    DEALERS,
    MODELS,
    COMPONENTS,
    DTC_CATALOG,
    COMMON_ISSUES
)
from data_generator.vehicle_physics import VehiclePhysicsSimulator

def parse_args():
    parser = argparse.ArgumentParser(description="Generate AutoCare Intelligence Datasets")
    parser.add_argument("--vehicles", type=int, default=100, help="Number of vehicles in fleet (default: 100)")
    parser.add_argument("--days", type=int, default=60, help="Number of historical days to simulate (default: 60)")
    parser.add_argument("--months", type=int, default=None, help="Number of historical months to simulate (overrides --days with months * 30)")
    parser.add_argument("--telemetry-samples-per-day", type=int, default=6, help="Telemetry sample count per vehicle per active day (default: 6)")
    parser.add_argument("--telemetry-frequency", type=int, default=None, help="Alias for --telemetry-samples-per-day")
    parser.add_argument("--end-date", type=str, default="2026-09-25", help="Reference end date (YYYY-MM-DD) for deterministic generation (default: 2026-09-25)")
    parser.add_argument("--output-dir", type=str, default="data/raw", help="Output directory for generated CSVs (default: data/raw)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility (default: 42)")
    return parser.parse_args()

def generate_datasets(vehicles_count: int, days_count: int, samples_per_day: int, output_dir: str, seed: int = 42, end_date_str: str = "2026-09-25"):
    random.seed(seed)
    os.makedirs(output_dir, exist_ok=True)
    if end_date_str:
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
    else:
        end_date = datetime.now().replace(microsecond=0)
    start_date = end_date - timedelta(days=days_count)

    print(f"=== Generating AutoCare Intelligence Data ===")
    print(f"Fleet Size: {vehicles_count} vehicles | Period: {days_count} days | End Date: {end_date.strftime('%Y-%m-%d')} | Output: {output_dir}")

    # 1. Master Seed Data: Dealers, Components, Customers
    # Save Dealers
    dealers_file = os.path.join(output_dir, "dealers.csv")
    with open(dealers_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["dealer_id", "name", "region", "city", "bays"])
        writer.writeheader()
        for d in DEALERS:
            writer.writerow(d)

    # Save Components
    components_file = os.path.join(output_dir, "components.csv")
    with open(components_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["part_id", "name", "category", "lifespan_km", "base_cost", "lead_time_days"])
        writer.writeheader()
        for c in COMPONENTS:
            writer.writerow(c)

    # Generate Customers
    customers = []
    first_names = ["James", "Maria", "Robert", "Elena", "Michael", "Sophia", "David", "Amina", "Chen", "Priya"]
    last_names = ["Smith", "Rodriguez", "Johnson", "Ivanov", "Williams", "Patel", "Brown", "Nguyen", "Kim", "Taylor"]
    segments = ["Consumer-Individual", "Corporate-Fleet", "RideShare-Commercial"]
    for i in range(1, int(vehicles_count * 0.8) + 1):
        cust_id = f"CUST-{i:05d}"
        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        customers.append({
            "customer_id": cust_id,
            "customer_name": name,
            "segment": random.choice(segments),
            "region": random.choice(["North", "South", "East", "West", "Midwest"])
        })
    customers_file = os.path.join(output_dir, "customers.csv")
    with open(customers_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["customer_id", "customer_name", "segment", "region"])
        writer.writeheader()
        for c in customers:
            writer.writerow(c)

    # 2. Dataset: Vehicles (vehicle_id, model, variant, manufacture_date, dealer_id)
    vehicles = []
    vehicle_simulators = {}
    for i in range(1, vehicles_count + 1):
        v_id = f"VH-{10000 + i}"
        model_choice = random.choice(MODELS)
        variant_choice = random.choice(model_choice["variants"])
        mfg_days_ago = random.randint(180, 1000)
        mfg_date = (end_date - timedelta(days=mfg_days_ago)).strftime("%Y-%m-%d")
        dealer_choice = random.choice(DEALERS)["dealer_id"]
        vehicles.append({
            "vehicle_id": v_id,
            "model": model_choice["model"],
            "variant": variant_choice,
            "manufacture_date": mfg_date,
            "dealer_id": dealer_choice
        })
        vehicle_simulators[v_id] = VehiclePhysicsSimulator(
            vehicle_id=v_id,
            model=model_choice["model"],
            engine_type=model_choice["engine_type"]
        )

    vehicles_file = os.path.join(output_dir, "vehicles.csv")
    with open(vehicles_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["vehicle_id", "model", "variant", "manufacture_date", "dealer_id"])
        writer.writeheader()
        for v in vehicles:
            writer.writerow(v)
    print(f"Generated {len(vehicles)} vehicle records -> {vehicles_file}")

    # 2b. Proposed Supporting Registration Mapping: vehicle_customer_map
    # Establishes deterministic vehicle -> customer attribution to support Section 7's customer dimension
    # without altering the PDF-required schema of vehicles.csv
    vehicle_customer_mappings = []
    for idx, v in enumerate(vehicles):
        assigned_cust_id = customers[idx % len(customers)]["customer_id"]
        mfg_dt = datetime.strptime(v["manufacture_date"], "%Y-%m-%d")
        reg_date = (mfg_dt + timedelta(days=14)).strftime("%Y-%m-%d")
        vehicle_customer_mappings.append({
            "vehicle_id": v["vehicle_id"],
            "customer_id": assigned_cust_id,
            "registration_date": reg_date
        })
    map_file = os.path.join(output_dir, "vehicle_customer_map.csv")
    with open(map_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["vehicle_id", "customer_id", "registration_date"])
        writer.writeheader()
        for m in vehicle_customer_mappings:
            writer.writerow(m)
    print(f"Generated {len(vehicle_customer_mappings)} vehicle-customer mappings -> {map_file}")

    # 3. Datasets: Telemetry & Diagnostics
    telemetry_records = []
    diagnostics_records = []

    for day_offset in range(days_count):
        curr_day = start_date + timedelta(days=day_offset)
        # Vehicles active on this day
        active_vehicles = random.sample(vehicles, k=int(vehicles_count * random.uniform(0.75, 0.95)))

        for v in active_vehicles:
            v_id = v["vehicle_id"]
            sim = vehicle_simulators[v_id]

            for s in range(samples_per_day):
                timestamp = curr_day + timedelta(hours=random.randint(6, 21), minutes=random.randint(0, 59), seconds=random.randint(0, 59))
                # Step physics
                telemetry, dtc = sim.step(is_driving=True)
                telemetry_records.append({
                    "vehicle_id": v_id,
                    "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "rpm": telemetry["rpm"],
                    "temperature": telemetry["temperature"],
                    "battery": telemetry["battery"],
                    "vibration": telemetry["vibration"]
                })

                if dtc:
                    diagnostics_records.append({
                        "vehicle_id": v_id,
                        "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                        "code": dtc["code"],
                        "component": dtc["component"],
                        "severity": dtc["severity"]
                    })

    # Save Telemetry
    telemetry_file = os.path.join(output_dir, "telemetry.csv")
    with open(telemetry_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["vehicle_id", "timestamp", "rpm", "temperature", "battery", "vibration"])
        writer.writeheader()
        for t in telemetry_records:
            writer.writerow(t)
    print(f"Generated {len(telemetry_records)} telemetry records -> {telemetry_file}")

    # Save Diagnostics
    diagnostics_file = os.path.join(output_dir, "diagnostics.csv")
    with open(diagnostics_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["vehicle_id", "timestamp", "code", "component", "severity"])
        writer.writeheader()
        for d in diagnostics_records:
            writer.writerow(d)
    print(f"Generated {len(diagnostics_records)} diagnostics records -> {diagnostics_file}")

    # 4. Dataset: Service (service_id, vehicle_id, dealer_id, visit_date, issue, cost)
    services = []
    service_id_counter = 50001
    for day_offset in range(days_count):
        curr_day = start_date + timedelta(days=day_offset)
        # 2% to 6% of fleet visits service daily
        service_sample_size = random.randint(1, max(2, int(vehicles_count * 0.05)))
        serviced_vehicles = random.sample(vehicles, k=service_sample_size)

        for v in serviced_vehicles:
            issue_item = random.choice(COMMON_ISSUES)
            labor_rate = 110.0
            labor_cost = round(issue_item["labor_hours"] * labor_rate, 2)
            parts_cost = 0.0
            if issue_item["parts"]:
                part_meta = next((c for c in COMPONENTS if c["part_id"] == issue_item["parts"][0]), None)
                if part_meta:
                    parts_cost = round(part_meta["base_cost"] * random.uniform(1.0, 1.25), 2)
            total_cost = round(labor_cost + parts_cost, 2)

            services.append({
                "service_id": f"SRV-{service_id_counter}",
                "vehicle_id": v["vehicle_id"],
                "dealer_id": v["dealer_id"],
                "visit_date": curr_day.strftime("%Y-%m-%d"),
                "issue": issue_item["issue"],
                "cost": total_cost
            })
            service_id_counter += 1

    service_file = os.path.join(output_dir, "service.csv")
    with open(service_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["service_id", "vehicle_id", "dealer_id", "visit_date", "issue", "cost"])
        writer.writeheader()
        for s in services:
            writer.writerow(s)
    print(f"Generated {len(services)} service records -> {service_file}")

    # 5. Dataset: Warranty (claim_id, vehicle_id, component, claim_date, amount)
    warranties = []
    claim_id_counter = 90001
    # Generate warranty claims for services that replaced parts on eligible vehicles
    for s in services:
        # 35% of part repair services result in a warranty claim
        if s["cost"] > 350.0 and random.random() < 0.35:
            component_choice = random.choice(COMPONENTS)
            claim_amount = round(s["cost"] * random.uniform(0.75, 0.95), 2)
            warranties.append({
                "claim_id": f"CLM-{claim_id_counter}",
                "vehicle_id": s["vehicle_id"],
                "component": component_choice["name"],
                "claim_date": s["visit_date"],
                "amount": claim_amount
            })
            claim_id_counter += 1

    warranty_file = os.path.join(output_dir, "warranty.csv")
    with open(warranty_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["claim_id", "vehicle_id", "component", "claim_date", "amount"])
        writer.writeheader()
        for w in warranties:
            writer.writerow(w)
    print(f"Generated {len(warranties)} warranty claim records -> {warranty_file}")

    # 6. Dataset: Parts (part_id, dealer_id, stock, lead_time)
    parts_inventory = []
    for d in DEALERS:
        for c in COMPONENTS:
            # Baseline stock levels with realistic variation
            stock = random.randint(1, 25)
            lead_time = c["lead_time_days"] + random.randint(-1, 3)
            lead_time = max(1, lead_time)
            parts_inventory.append({
                "part_id": c["part_id"],
                "dealer_id": d["dealer_id"],
                "stock": stock,
                "lead_time": lead_time
            })

    parts_file = os.path.join(output_dir, "parts.csv")
    with open(parts_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["part_id", "dealer_id", "stock", "lead_time"])
        writer.writeheader()
        for p in parts_inventory:
            writer.writerow(p)
    print(f"Generated {len(parts_inventory)} parts inventory records -> {parts_file}")

    print("=== All 6 Required Datasets Successfully Generated ===")

if __name__ == "__main__":
    args = parse_args()
    days_to_run = args.months * 30 if args.months is not None else args.days
    frequency = args.telemetry_frequency if args.telemetry_frequency is not None else args.telemetry_samples_per_day
    generate_datasets(
        vehicles_count=args.vehicles,
        days_count=days_to_run,
        samples_per_day=frequency,
        output_dir=args.output_dir,
        seed=args.seed,
        end_date_str=args.end_date
    )
