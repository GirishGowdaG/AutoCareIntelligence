"""Model Monitoring and Data Drift Detector for AutoCare Intelligence.

Calculates Population Stability Index (PSI) and Kolmogorov-Smirnov (KS) tests
to detect feature and prediction drift against the baseline reference distribution.
"""

from typing import Dict, Any, List, Tuple
import numpy as np
import pandas as pd
from scipy.stats import ks_2samp


def calculate_psi(expected: np.ndarray, actual: np.ndarray, num_buckets: int = 10) -> float:
    """Calculate Population Stability Index (PSI) between reference and production distributions."""
    if len(expected) == 0 or len(actual) == 0:
        return 0.0

    # Determine quantile bins from expected distribution
    percentiles = np.linspace(0, 100, num_buckets + 1)
    bins = np.percentile(expected, percentiles)
    bins[0] -= 1e-5
    bins[-1] += 1e-5
    bins = np.unique(bins)

    if len(bins) < 2:
        return 0.0

    expected_counts, _ = np.histogram(expected, bins=bins)
    actual_counts, _ = np.histogram(actual, bins=bins)

    # Convert to fractions with small epsilon smoothing
    expected_pct = (expected_counts + 1e-4) / (len(expected) + 1e-4 * len(expected_counts))
    actual_pct = (actual_counts + 1e-4) / (len(actual) + 1e-4 * len(actual_counts))

    psi_val = np.sum((actual_pct - expected_pct) * np.log(actual_pct / expected_pct))
    return float(np.round(psi_val, 4))


class DriftDetector:
    """Monitors continuous feature drift and prediction score drift."""

    def __init__(self, psi_threshold: float = 0.20, ks_alpha: float = 0.05):
        self.psi_threshold = psi_threshold
        self.ks_alpha = ks_alpha

    def evaluate_feature_drift(
        self,
        reference_df: pd.DataFrame,
        current_df: pd.DataFrame,
        features: List[str],
    ) -> Dict[str, Any]:
        """Evaluate KS-test and PSI across all specified features."""
        results = {}
        any_drift = False

        for feat in features:
            if feat not in reference_df.columns or feat not in current_df.columns:
                continue

            ref_vals = reference_df[feat].dropna().values
            curr_vals = current_df[feat].dropna().values

            if len(ref_vals) < 5 or len(curr_vals) < 5:
                continue

            ks_stat, ks_pval = ks_2samp(ref_vals, curr_vals)
            psi = calculate_psi(ref_vals, curr_vals)

            is_drift = (psi >= self.psi_threshold) or (ks_pval < self.ks_alpha)
            if is_drift:
                any_drift = True

            results[feat] = {
                "psi": psi,
                "ks_statistic": round(float(ks_stat), 4),
                "ks_pvalue": round(float(ks_pval), 4),
                "drift_detected": is_drift,
            }

        return {
            "overall_drift_detected": any_drift,
            "feature_metrics": results,
        }
