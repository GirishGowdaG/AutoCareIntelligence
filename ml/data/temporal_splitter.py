"""Temporal Splitting and Cutoff Validation Engine for AutoCare Intelligence.

Prevents lookahead leakage by enforcing chronological ordering and rejecting
censored cutoff dates whose forward outcome window is incomplete.
"""

from datetime import datetime, date, timedelta
from typing import Tuple, List, Optional
import pandas as pd


class TemporalSplitter:
    """Enforces strict chronological train/val/test splitting and cutoff validation."""

    def __init__(self, horizon_days: int = 14, lookback_days: int = 7):
        self.horizon_days = horizon_days
        self.lookback_days = lookback_days

    def validate_cutoff(self, cutoff_date: date, t_min: date, t_max: date) -> Tuple[bool, str]:
        """Validate if a cutoff date is eligible for supervised target evaluation.
        
        Rule: Cutoff must leave at least `horizon_days` of complete observable future history:
            cutoff_date <= t_max - horizon_days
        """
        max_eligible_cutoff = t_max - timedelta(days=self.horizon_days)
        if cutoff_date > max_eligible_cutoff:
            return False, (
                f"Cutoff date {cutoff_date} is censored: forward {self.horizon_days}-day "
                f"outcome window exceeds maximum available date {t_max} (max eligible cutoff is {max_eligible_cutoff})"
            )
        if cutoff_date < t_min:
            return False, f"Cutoff date {cutoff_date} precedes minimum available date {t_min}"
        return True, "Eligible"

    def split_by_cutoffs(
        self,
        df: pd.DataFrame,
        date_col: str,
        train_end_date: date,
        val_end_date: date,
        test_end_date: date,
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Chronologically split a dataframe into train, validation, and test subsets.
        
        Strict inequality ensures zero temporal leakage:
            Train: date <= train_end_date
            Val:   train_end_date < date <= val_end_date
            Test:  val_end_date < date <= test_end_date
        """
        assert train_end_date < val_end_date < test_end_date, (
            f"Chronological ordering violated: {train_end_date} < {val_end_date} < {test_end_date}"
        )

        dates = pd.to_datetime(df[date_col]).dt.date
        train_mask = dates <= train_end_date
        val_mask = (dates > train_end_date) & (dates <= val_end_date)
        test_mask = (dates > val_end_date) & (dates <= test_end_date)

        train_df = df[train_mask].copy()
        val_df = df[val_mask].copy()
        test_df = df[test_mask].copy()

        assert len(train_df) + len(val_df) + len(test_df) <= len(df), "Row count inconsistency in split"
        return train_df, val_df, test_df
