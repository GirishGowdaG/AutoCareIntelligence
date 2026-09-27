"""Unit tests for ML Model Architectures, Training, Serialization, and Inference in Phase 5.

Verifies fit, predict, evaluate, serialization/deserialization, streaming scorer, and drift detection.
"""

from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from ml.models.base_model import compute_df_sha256
from ml.models.failure_risk_model import FailureRiskModel
from ml.models.sensor_anomaly_model import SensorAnomalyModel
from ml.models.demand_forecast_model import DemandForecastModel
from ml.models.warranty_anomaly_model import WarrantyAnomalyModel
from ml.inference.streaming_inference import StreamingSensorScorer
from ml.monitoring.drift_detector import DriftDetector, calculate_psi


class TestMLModels:
    """Test suite for Phase 5 ML model implementations."""

    def test_failure_risk_lifecycle_and_serialization(self, tmp_path):
        X = pd.DataFrame({
            "temp": [80.0, 90.0, 110.0, 85.0, 115.0],
            "rpm_count": [0, 5, 20, 2, 25],
            "vib": [0.5, 0.8, 3.2, 0.6, 4.0],
        })
        y = pd.Series([0, 0, 1, 0, 1])

        model = FailureRiskModel(n_estimators=10)
        model.fit(X, y)

        probs = model.predict_proba(X)
        assert len(probs) == len(X)
        assert all(0.0 <= p <= 1.0 for p in probs)

        metrics = model.evaluate(X, y)
        assert "pr_auc" in metrics
        assert "roc_auc" in metrics
        assert "brier_score" in metrics

        # Serialization & Deserialization
        art_dir = tmp_path / "model_out"
        model.save(art_dir)
        assert (art_dir / "model.joblib").exists()
        assert (art_dir / "manifest.json").exists()

        loaded_model = FailureRiskModel().load(art_dir / "model.joblib")
        loaded_probs = loaded_model.predict_proba(X)
        np.testing.assert_allclose(probs, loaded_probs)

    def test_sensor_anomaly_scorer(self):
        X_train = pd.DataFrame({
            "rpm": [2000.0, 2200.0, 2100.0, 2300.0, 2050.0],
            "temperature": [85.0, 86.0, 84.0, 85.5, 84.5],
            "battery": [95.0, 94.0, 95.0, 94.5, 95.0],
            "vibration": [0.8, 0.9, 0.8, 0.85, 0.82],
        })
        model = SensorAnomalyModel(n_estimators=20, contamination=0.05)
        model.fit(X_train)

        # Calibrate on nominal validation
        thresh = model.calibrate_threshold(X_train, target_fpr=0.05)
        assert 0.0 <= thresh <= 1.0

        scores = model.score_samples(X_train)
        assert len(scores) == len(X_train)
        assert all(0.0 <= s <= 1.0 for s in scores)

        # Severe outlier should score high
        X_outlier = pd.DataFrame({
            "rpm": [9500.0],
            "temperature": [145.0],
            "battery": [15.0],
            "vibration": [9.5],
        })
        outlier_score = model.score_samples(X_outlier)[0]
        assert outlier_score >= scores[0]

        # Streaming scorer integration
        scorer = StreamingSensorScorer(model=model)
        res = scorer.score_event({"rpm": 9500, "temperature": 145, "battery": 15, "vibration": 9.5})
        assert "anomaly_score" in res
        assert "algorithmic_latency_ms" in res
        assert res["algorithmic_latency_ms"] < 50.0  # Engineering measurement target (< 10ms typical)
        assert res["inference_mode"] == "STREAMING_REALTIME"

    def test_demand_forecast_model(self):
        X = pd.DataFrame({
            "lag_7": [5.0, 6.0, 4.0, 5.0, 7.0],
            "lag_14": [4.0, 5.0, 5.0, 6.0, 6.0],
            "day": [0, 1, 2, 3, 4],
        })
        y = pd.Series([5.0, 6.0, 4.0, 5.0, 7.0])

        model = DemandForecastModel(n_estimators=10)
        model.fit(X, y)

        point, lower, upper = model.predict_with_intervals(X)
        assert len(point) == len(X)
        assert all(lower <= point)
        assert all(point <= upper)

        metrics = model.evaluate(X, y)
        assert "wape" in metrics
        assert "mae" in metrics
        assert metrics["mae"] >= 0.0

    def test_warranty_anomaly_model(self):
        X = pd.DataFrame({
            "claim_amount": [150.0, 200.0, 180.0, 4500.0],
            "median_ratio": [1.0, 1.2, 1.1, 15.0],
            "iqr_dist": [0.2, 0.5, 0.3, 12.0],
        })
        model = WarrantyAnomalyModel()
        model.fit(X)

        scores = model.score_samples(X)
        assert len(scores) == len(X)
        # Percentile rank scaling: min is 0.0, max is 1.0
        assert np.isclose(np.min(scores), 0.0)
        assert np.isclose(np.max(scores), 1.0)
        assert scores[3] > scores[0]


    def test_drift_detector_psi_and_ks(self):
        rng = np.random.default_rng(42)
        baseline = rng.normal(loc=85.0, scale=5.0, size=200)
        identical = rng.normal(loc=85.0, scale=5.0, size=200)
        drifted = rng.normal(loc=115.0, scale=15.0, size=200)

        # Baseline vs identical should have low PSI
        psi_low = calculate_psi(baseline, identical)
        assert psi_low < 0.20

        # Baseline vs drifted should have high PSI
        psi_high = calculate_psi(baseline, drifted)
        assert psi_high > 0.20

        detector = DriftDetector(psi_threshold=0.20)
        ref_df = pd.DataFrame({"temp": baseline})
        curr_df = pd.DataFrame({"temp": drifted})
        res = detector.evaluate_feature_drift(ref_df, curr_df, ["temp"])
        assert res["overall_drift_detected"] is True
