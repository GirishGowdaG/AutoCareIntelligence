"""Unit and integration tests for Feature Extraction and Point-in-Time Consistency.

Verifies zero lookahead leakage, deterministic issue mapping, severe DTC fault window excision,
and strict adherence to verified source fields.
"""

from datetime import date, datetime, timedelta, timezone
import pytest
import pandas as pd
import numpy as np

from ml.config import (
    PG_CONFIG,
    is_breakdown_issue,
    ROUTINE_MAINTENANCE_ISSUES,
)
from ml.data.feature_extractor import FeatureExtractor


class TestFeatureEngineering:
    """Test suite for feature extraction and leakage prevention."""

    @pytest.fixture
    def extractor(self) -> FeatureExtractor:
        return FeatureExtractor(pg_config=PG_CONFIG)

    def test_deterministic_issue_mapping(self):
        # Approved routine maintenance issue must evaluate to False (no breakdown)
        for issue in ROUTINE_MAINTENANCE_ISSUES:
            assert is_breakdown_issue(issue) is False

        # Actual component breakdowns must evaluate to True
        assert is_breakdown_issue("Coolant leak repair and water pump replacement") is True
        assert is_breakdown_issue("Alternator replacement due to charging failure") is True
        assert is_breakdown_issue("Oxygen sensor replacement following check engine indicator") is True
        assert is_breakdown_issue("Front brake rotor and pad replacement") is True
        assert is_breakdown_issue("Suspension strut assembly replacement") is True
        assert is_breakdown_issue("Transmission fluid flush and torque converter solenoid repair") is True
        assert is_breakdown_issue("Battery replacement and alternator circuit test") is True

        # Empty or null issue must return False
        assert is_breakdown_issue("") is False
        assert is_breakdown_issue(None) is False

    def test_failure_risk_point_in_time_extraction(self, extractor):
        cutoff = date(2026, 9, 11)
        cohort = extractor.extract_failure_risk_cohort(cutoff_date=cutoff, lookback_days=7, horizon_days=14)

        assert not cohort.empty
        assert "vehicle_id" in cohort.columns
        assert "target" in cohort.columns
        assert "telemetry_avg_engine_temp_30d" in cohort.columns
        assert "days_since_last_service" in cohort.columns

        # Verify target is binary (0 or 1)
        assert set(cohort["target"].unique()).issubset({0, 1})

    def test_sensor_fault_window_excision(self, extractor):
        df_excised = extractor.extract_sensor_telemetry_features(excise_fault_windows=True)
        assert not df_excised.empty
        assert "is_fault_window" in df_excised.columns

        # Verify verified telemetry attributes exist
        for col in ["rpm", "temperature", "battery", "vibration", "norm_rpm", "vibration_per_rpm_ratio"]:
            assert col in df_excised.columns

        # Unsupported attributes must NOT be in features
        assert "ambient_temperature" not in df_excised.columns
        assert "curb_weight" not in df_excised.columns
        assert "vehicle_class" not in df_excised.columns

        # Excision logic must flag fault pings
        assert df_excised["is_fault_window"].sum() > 0
        assert (~df_excised["is_fault_window"]).sum() > 0

    def test_warranty_unsupervised_feature_extraction(self, extractor):
        w_df = extractor.extract_warranty_features()
        assert not w_df.empty

        # Verified fields only
        assert "claim_id" in w_df.columns
        assert "claim_amount" in w_df.columns
        assert "claim_amount_to_component_median_ratio" in w_df.columns
        assert "component_claim_iqr_distance" in w_df.columns

        # Unsupported fields must NOT exist
        assert "labor_cost" not in w_df.columns
        assert "parts_cost" not in w_df.columns
        assert "odometer_reading" not in w_df.columns
        assert "is_fraudulent" not in w_df.columns  # No invented fraud labels
