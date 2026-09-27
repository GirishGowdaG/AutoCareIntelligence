"""Frozen Model Threshold Governance for AutoCare Intelligence.

Authoritatively loads the calibrated sensor anomaly threshold from the
Phase 5 model artifact manifest without duplicating or hardcoding numeric constants.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Single authoritative source of truth for Phase 5 sensor anomaly model
SENSOR_MANIFEST_PATH = Path("data/ml/models/sensor_anomaly/v1.0.0/manifest.json")


def load_frozen_sensor_threshold(manifest_path: Path = SENSOR_MANIFEST_PATH) -> float:
    """Load authoritative sensor anomaly threshold directly from the frozen Phase 5 manifest.
    
    Contains zero hard-coded numeric values. Validates manifest structural metadata only.
    """
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"Frozen model manifest not found at '{manifest_path}'. "
            "Cannot initialize application without authoritative Phase 5 threshold."
        )

    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Structural validation: verify required calibration metadata keys exist
    hyperparams = data.get("hyperparameters", {})
    if "calibrated_threshold" not in hyperparams:
        raise KeyError(
            f"Integrity check failed: 'hyperparameters.calibrated_threshold' missing from '{manifest_path}'."
        )

    threshold = hyperparams["calibrated_threshold"]
    if threshold is None or not isinstance(threshold, (int, float)):
        raise ValueError(
            f"Integrity check failed: Invalid threshold value '{threshold}' in '{manifest_path}'."
        )

    return float(threshold)


def get_model_metadata(manifest_path: Path = SENSOR_MANIFEST_PATH) -> Dict[str, Any]:
    """Retrieve verified structural metadata from the sensor anomaly manifest."""
    if not manifest_path.exists():
        return {}
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)
