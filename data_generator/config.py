"""Configuration and Master Reference Data for AutoCare Intelligence."""

DEALERS = [
    {"dealer_id": "DLR-001", "name": "Metro Apex Motors", "region": "North", "city": "Chicago", "bays": 12},
    {"dealer_id": "DLR-002", "name": "Sunbelt AutoCare", "region": "South", "city": "Dallas", "bays": 16},
    {"dealer_id": "DLR-003", "name": "Pacific Coast Mobility", "region": "West", "city": "Seattle", "bays": 10},
    {"dealer_id": "DLR-004", "name": "Tri-State Automotive", "region": "East", "city": "New York", "bays": 14},
    {"dealer_id": "DLR-005", "name": "Midwest Fleet Center", "region": "Midwest", "city": "Detroit", "bays": 20},
]

MODELS = [
    {"model": "Apex", "variants": ["Base", "Sport", "Turbo-GT"], "engine_type": "ICE-Gasoline"},
    {"model": "Titan", "variants": ["HeavyDuty", "Pro-4x", "EcoDiesel"], "engine_type": "Diesel"},
    {"model": "Pulse", "variants": ["Standard", "LongRange", "DualMotor"], "engine_type": "EV"},
    {"model": "Horizon", "variants": ["Comfort", "Executive", "Hybrid-X"], "engine_type": "Hybrid"},
]

COMPONENTS = [
    {"part_id": "PRT-ENG-01", "name": "Engine Block Assembly", "category": "Powertrain", "lifespan_km": 250000, "base_cost": 4500.0, "lead_time_days": 14},
    {"part_id": "PRT-CLG-02", "name": "Water Pump & Thermostat", "category": "Cooling System", "lifespan_km": 100000, "base_cost": 320.0, "lead_time_days": 5},
    {"part_id": "PRT-ELC-03", "name": "12V AGM Auxiliary Battery", "category": "Electrical", "lifespan_km": 60000, "base_cost": 210.0, "lead_time_days": 3},
    {"part_id": "PRT-ALT-04", "name": "High-Output Alternator", "category": "Electrical", "lifespan_km": 120000, "base_cost": 480.0, "lead_time_days": 6},
    {"part_id": "PRT-BRK-05", "name": "Front Ceramic Brake Rotor Set", "category": "Braking", "lifespan_km": 70000, "base_cost": 290.0, "lead_time_days": 4},
    {"part_id": "PRT-TRN-06", "name": "Automatic Transmission Unit", "category": "Powertrain", "lifespan_km": 200000, "base_cost": 3800.0, "lead_time_days": 21},
    {"part_id": "PRT-SUS-07", "name": "Adaptive Suspension Strut", "category": "Chassis", "lifespan_km": 110000, "base_cost": 550.0, "lead_time_days": 8},
    {"part_id": "PRT-SEN-08", "name": "Oxygen & Exhaust Gas Sensor", "category": "Sensors", "lifespan_km": 90000, "base_cost": 160.0, "lead_time_days": 2},
]

DTC_CATALOG = [
    {"code": "P0217", "component": "Cooling System", "severity": "CRITICAL", "description": "Engine Coolant Over Temperature Condition"},
    {"code": "P0562", "component": "Electrical", "severity": "HIGH", "description": "System Voltage Low (Alternator/Battery Fault)"},
    {"code": "P0300", "component": "Powertrain", "severity": "HIGH", "description": "Random/Multiple Cylinder Misfire Detected"},
    {"code": "C0035", "component": "Braking", "severity": "MEDIUM", "description": "Left Front Wheel Speed Sensor Circuit Fault"},
    {"code": "P0420", "component": "Sensors", "severity": "MEDIUM", "description": "Catalyst System Efficiency Below Threshold"},
    {"code": "B0001", "component": "Electrical", "severity": "CRITICAL", "description": "Driver Frontal Stage 1 Deployment Control Fault"},
    {"code": "U0100", "component": "Electrical", "severity": "HIGH", "description": "Lost Communication With ECM/PCM 'A'"},
    {"code": "C0561", "component": "Chassis", "severity": "LOW", "description": "System Disabled Information Stored (Adaptive Strut)"},
]

COMMON_ISSUES = [
    {"issue": "Scheduled routine maintenance and multi-point inspection", "labor_hours": 1.5, "parts": []},
    {"issue": "Coolant leak repair and water pump replacement", "labor_hours": 3.5, "parts": ["PRT-CLG-02"]},
    {"issue": "Battery replacement and alternator circuit test", "labor_hours": 1.0, "parts": ["PRT-ELC-03"]},
    {"issue": "Alternator replacement due to charging failure", "labor_hours": 2.5, "parts": ["PRT-ALT-04"]},
    {"issue": "Front brake rotor and pad replacement", "labor_hours": 2.0, "parts": ["PRT-BRK-05"]},
    {"issue": "Transmission fluid flush and torque converter solenoid repair", "labor_hours": 4.0, "parts": ["PRT-TRN-06"]},
    {"issue": "Suspension strut assembly replacement", "labor_hours": 3.0, "parts": ["PRT-SUS-07"]},
    {"issue": "Oxygen sensor replacement following check engine indicator", "labor_hours": 1.2, "parts": ["PRT-SEN-08"]},
]
