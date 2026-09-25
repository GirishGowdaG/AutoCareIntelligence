"""Vehicle Physics Simulation for Correlated CAN Bus Telemetry."""

import random
from typing import Dict, Any, Tuple

class VehiclePhysicsSimulator:
    """Simulates correlated telemetry signals reflecting vehicle physical state."""

    STATE_NORMAL = "NORMAL"
    STATE_OVERHEATING = "OVERHEATING"
    STATE_LOW_BATTERY = "LOW_BATTERY"
    STATE_HIGH_VIBRATION = "HIGH_VIBRATION"

    def __init__(self, vehicle_id: str, model: str, engine_type: str):
        self.vehicle_id = vehicle_id
        self.model = model
        self.engine_type = engine_type
        # Baseline normal state parameters
        self.current_state = self.STATE_NORMAL
        self.state_countdown = 0

    def step(self, is_driving: bool = True, force_anomaly_type: str = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Advance one simulation step.
        Returns:
            telemetry: dict with rpm, temperature, battery, vibration
            dtc_event: optional dict with diagnostic trouble code event if triggered
        """
        # Determine operating state
        if force_anomaly_type:
            self.current_state = force_anomaly_type
            self.state_countdown = random.randint(3, 10)
        elif self.state_countdown > 0:
            self.state_countdown -= 1
            if self.state_countdown == 0:
                self.current_state = self.STATE_NORMAL
        else:
            # 3% chance to transition into a degradative state during operation
            if is_driving and random.random() < 0.03:
                self.current_state = random.choice([
                    self.STATE_OVERHEATING,
                    self.STATE_LOW_BATTERY,
                    self.STATE_HIGH_VIBRATION
                ])
                self.state_countdown = random.randint(4, 12)

        dtc_event = None

        if not is_driving:
            # Parked / Engine Off
            rpm = 0
            temperature = round(random.uniform(20.0, 35.0), 2)
            battery = round(random.uniform(12.3, 12.7), 2)
            vibration = round(random.uniform(0.01, 0.08), 3)
            return {"rpm": rpm, "temperature": temperature, "battery": battery, "vibration": vibration}, None

        # Active driving base values
        if self.engine_type == "EV":
            rpm = random.randint(1500, 6500)
            base_temp = random.uniform(35.0, 55.0)
            base_battery = random.uniform(13.6, 14.2)
        else:
            rpm = random.randint(1600, 3200)
            base_temp = random.uniform(88.0, 96.0)
            base_battery = random.uniform(13.8, 14.4)

        base_vib = random.uniform(0.7, 1.8)

        # Apply state distortions
        if self.current_state == self.STATE_OVERHEATING:
            temperature = round(base_temp + random.uniform(20.0, 38.0), 2)  # 108C - 134C
            rpm = rpm + random.randint(200, 600)
            battery = round(base_battery - random.uniform(0.2, 0.6), 2)
            vibration = round(base_vib + random.uniform(0.8, 2.2), 3)
            # Trigger critical coolant DTC
            dtc_event = {
                "code": "P0217",
                "component": "Cooling System",
                "severity": "CRITICAL"
            }
        elif self.current_state == self.STATE_LOW_BATTERY:
            temperature = round(base_temp + random.uniform(-2.0, 3.0), 2)
            rpm = rpm
            battery = round(random.uniform(9.8, 11.6), 2)  # Low voltage
            vibration = round(base_vib, 3)
            dtc_event = {
                "code": "P0562",
                "component": "Electrical",
                "severity": "HIGH"
            }
        elif self.current_state == self.STATE_HIGH_VIBRATION:
            temperature = round(base_temp + random.uniform(2.0, 6.0), 2)
            rpm = rpm + random.randint(400, 1000)
            battery = round(base_battery, 2)
            vibration = round(base_vib + random.uniform(3.5, 7.5), 3)  # 4.2 - 9.3 mm/s
            dtc_event = {
                "code": "P0300",
                "component": "Powertrain",
                "severity": "HIGH"
            }
        else:
            # Normal driving
            temperature = round(base_temp + random.uniform(-1.5, 2.0), 2)
            battery = round(base_battery + random.uniform(-0.1, 0.2), 2)
            vibration = round(base_vib + random.uniform(-0.2, 0.3), 3)

        # Clamp physical boundaries
        rpm = max(0, min(8500, rpm))
        temperature = max(-40.0, min(150.0, temperature))
        battery = max(9.0, min(16.0, battery))
        vibration = max(0.0, min(15.0, vibration))

        telemetry = {
            "rpm": rpm,
            "temperature": temperature,
            "battery": battery,
            "vibration": vibration
        }
        return telemetry, dtc_event
