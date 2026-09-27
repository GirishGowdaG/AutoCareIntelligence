"""Unit tests for Temporal Splitting and Censored Cutoff Rejection in Phase 5 ML.

Verifies strict chronological ordering, lookahead leakage prevention, and rejection of censored cutoffs.
"""

from datetime import date, timedelta
import pandas as pd
import pytest

from ml.data.temporal_splitter import TemporalSplitter


class TestTemporalSplitter:
    """Test suite for temporal splitting logic."""

    @pytest.fixture
    def splitter(self) -> TemporalSplitter:
        return TemporalSplitter(horizon_days=14, lookback_days=7)

    def test_censored_cutoff_rejection(self, splitter):
        t_min = date(2026, 8, 27)
        t_max = date(2026, 9, 25)
        max_eligible = t_max - timedelta(days=14)  # 2026-09-11

        # Cutoff on or before max_eligible is valid
        is_valid, msg = splitter.validate_cutoff(max_eligible, t_min, t_max)
        assert is_valid is True
        assert msg == "Eligible"

        # Cutoff after max_eligible is rejected as censored
        censored_cutoff = max_eligible + timedelta(days=1)  # 2026-09-12
        is_valid_censored, msg_censored = splitter.validate_cutoff(censored_cutoff, t_min, t_max)
        assert is_valid_censored is False
        assert "censored" in msg_censored.lower()

        # Cutoff before t_min is rejected
        is_valid_early, _ = splitter.validate_cutoff(t_min - timedelta(days=1), t_min, t_max)
        assert is_valid_early is False

    def test_chronological_splitting_ordering(self, splitter):
        # Sample dataset spanning 30 days
        dates = pd.date_range("2026-08-27", "2026-09-25", freq="D").date
        df = pd.DataFrame({
            "visit_date": dates,
            "value": range(len(dates)),
        })

        train_end = date(2026, 9, 5)
        val_end = date(2026, 9, 8)
        test_end = date(2026, 9, 11)

        train_df, val_df, test_df = splitter.split_by_cutoffs(
            df=df,
            date_col="visit_date",
            train_end_date=train_end,
            val_end_date=val_end,
            test_end_date=test_end,
        )

        assert len(train_df) > 0
        assert len(val_df) > 0
        assert len(test_df) > 0

        # Strict chronological separation
        assert train_df["visit_date"].max() <= train_end
        assert val_df["visit_date"].min() > train_end
        assert val_df["visit_date"].max() <= val_end
        assert test_df["visit_date"].min() > val_end
        assert test_df["visit_date"].max() <= test_end

    def test_out_of_order_cutoffs_raise_assertion(self, splitter):
        df = pd.DataFrame({"visit_date": [date(2026, 9, 1)], "val": [1]})
        with pytest.raises(AssertionError):
            splitter.split_by_cutoffs(
                df=df,
                date_col="visit_date",
                train_end_date=date(2026, 9, 10),
                val_end_date=date(2026, 9, 5),  # Out of order
                test_end_date=date(2026, 9, 15),
            )
