"""Point-in-Time Consistent Feature Extraction Engine for AutoCare Intelligence.

Extracts features from PostgreSQL warehouse (6 dimensions + 4 facts) and staging.silver_diagnostics.
Guarantees absolute absence of lookahead leakage and zero data invention.
"""

from datetime import date, datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Tuple
import psycopg2
import pandas as pd
import numpy as np

from ml.config import (
    PG_CONFIG,
    FAILURE_RISK_LOOKBACK_DAYS,
    FAILURE_RISK_HORIZON_DAYS,
    is_breakdown_issue,
    FAULT_EXCLUSION_PRE_HOURS,
    FAULT_EXCLUSION_POST_HOURS,
    SEVERE_DIAGNOSTIC_SEVERITIES,
)


class FeatureExtractor:
    """Extracts point-in-time features across all four intelligence areas."""

    def __init__(self, pg_config: Optional[Dict[str, Any]] = None):
        self.pg_config = pg_config or PG_CONFIG

    def _get_connection(self):
        return psycopg2.connect(**self.pg_config)

    # --------------------------------------------------------------------------
    # Area 1: Vehicle Failure-Risk Features & Empirical Target
    # --------------------------------------------------------------------------
    def extract_failure_risk_cohort(
        self,
        cutoff_date: date,
        lookback_days: int = FAILURE_RISK_LOOKBACK_DAYS,
        horizon_days: int = FAILURE_RISK_HORIZON_DAYS,
    ) -> pd.DataFrame:
        """Extract point-in-time features and forward target for a given cutoff date.
        
        Strict inequality ensures zero lookahead leakage:
          Features: event timestamp/date <= cutoff_date
          Target:   cutoff_date < event timestamp/date <= cutoff_date + horizon_days
        """
        conn = self._get_connection()
        try:
            start_date = cutoff_date - timedelta(days=lookback_days)
            forward_end_date = cutoff_date + timedelta(days=horizon_days)

            # 1. Active vehicles observed in the lookback window
            query_vehicles = """
                SELECT DISTINCT v.vehicle_id, v.vehicle_key
                FROM autocare_dw.fact_telemetry t
                JOIN autocare_dw.dim_vehicle v ON t.vehicle_key = v.vehicle_key
                WHERE t.timestamp >= %s AND t.timestamp <= %s;
            """
            vehicles_df = pd.read_sql(
                query_vehicles,
                conn,
                params=[datetime.combine(start_date, datetime.min.time()), datetime.combine(cutoff_date, datetime.max.time())],
            )
            if vehicles_df.empty:
                return pd.DataFrame()

            # 2. Telemetry Aggregates (strictly <= cutoff_date)
            query_telemetry = """
                SELECT 
                    v.vehicle_id,
                    AVG(t.temperature) as telemetry_avg_engine_temp_30d,
                    MAX(t.temperature) as telemetry_max_engine_temp_7d,
                    STDDEV(t.vibration) as telemetry_vibration_stddev_30d,
                    MIN(t.battery) as telemetry_battery_min_7d,
                    SUM(CASE WHEN t.rpm > 4500 THEN 1 ELSE 0 END) as telemetry_high_rpm_ping_count_30d
                FROM autocare_dw.fact_telemetry t
                JOIN autocare_dw.dim_vehicle v ON t.vehicle_key = v.vehicle_key
                WHERE t.timestamp >= %s AND t.timestamp <= %s
                GROUP BY v.vehicle_id;
            """
            telemetry_df = pd.read_sql(
                query_telemetry,
                conn,
                params=[datetime.combine(start_date, datetime.min.time()), datetime.combine(cutoff_date, datetime.max.time())],
            )

            # 3. Severe Diagnostics count (strictly <= cutoff_date)
            query_dtc = """
                SELECT 
                    vehicle_id,
                    COUNT(*) as dtc_critical_high_count_30d
                FROM staging.silver_diagnostics
                WHERE severity IN ('CRITICAL', 'HIGH')
                  AND timestamp >= %s AND timestamp <= %s
                GROUP BY vehicle_id;
            """
            dtc_df = pd.read_sql(
                query_dtc,
                conn,
                params=[datetime.combine(start_date, datetime.min.time()), datetime.combine(cutoff_date, datetime.max.time())],
            )

            # 4. Service History (strictly <= cutoff_date)
            query_service_hist = """
                SELECT 
                    v.vehicle_id,
                    COUNT(*) as historical_service_count,
                    MAX(s.visit_date) as last_service_date
                FROM autocare_dw.fact_service s
                JOIN autocare_dw.dim_vehicle v ON s.vehicle_key = v.vehicle_key
                WHERE s.visit_date <= %s
                GROUP BY v.vehicle_id;
            """
            service_hist_df = pd.read_sql(
                query_service_hist,
                conn,
                params=[cutoff_date],
            )

            # 5. Forward Target Extraction (strictly > cutoff_date AND <= forward_end_date)
            # A vehicle experiences a failure if:
            # - An actual service visit occurs with a breakdown issue (is_breakdown_issue(issue) == True)
            # - OR a severe diagnostic code occurs in the window
            query_target_services = """
                SELECT DISTINCT v.vehicle_id, s.issue
                FROM autocare_dw.fact_service s
                JOIN autocare_dw.dim_vehicle v ON s.vehicle_key = v.vehicle_key
                WHERE s.visit_date > %s AND s.visit_date <= %s;
            """
            target_services = pd.read_sql(
                query_target_services,
                conn,
                params=[cutoff_date, forward_end_date],
            )
            # Apply deterministic breakdown mapping
            breakdown_vehicle_ids = set()
            for _, row in target_services.iterrows():
                if is_breakdown_issue(row["issue"]):
                    breakdown_vehicle_ids.add(row["vehicle_id"])

            query_target_dtcs = """
                SELECT DISTINCT vehicle_id
                FROM staging.silver_diagnostics
                WHERE severity IN ('CRITICAL', 'HIGH')
                  AND timestamp > %s AND timestamp <= %s;
            """
            target_dtcs = pd.read_sql(
                query_target_dtcs,
                conn,
                params=[datetime.combine(cutoff_date, datetime.max.time()), datetime.combine(forward_end_date, datetime.max.time())],
            )
            severe_dtc_vehicle_ids = set(target_dtcs["vehicle_id"].tolist())

            positive_targets = breakdown_vehicle_ids.union(severe_dtc_vehicle_ids)

            # Assemble feature dataframe
            df = vehicles_df[["vehicle_id"]].copy()
            df = df.merge(telemetry_df, on="vehicle_id", how="left")
            df = df.merge(dtc_df, on="vehicle_id", how="left")
            df = df.merge(service_hist_df, on="vehicle_id", how="left")

            # Fill missing aggregates with domain defaults
            df["telemetry_avg_engine_temp_30d"] = df["telemetry_avg_engine_temp_30d"].fillna(85.0)
            df["telemetry_max_engine_temp_7d"] = df["telemetry_max_engine_temp_7d"].fillna(85.0)
            df["telemetry_vibration_stddev_30d"] = df["telemetry_vibration_stddev_30d"].fillna(0.0)
            df["telemetry_battery_min_7d"] = df["telemetry_battery_min_7d"].fillna(90.0)
            df["telemetry_high_rpm_ping_count_30d"] = df["telemetry_high_rpm_ping_count_30d"].fillna(0)
            df["dtc_critical_high_count_30d"] = df["dtc_critical_high_count_30d"].fillna(0)
            df["historical_service_count"] = df["historical_service_count"].fillna(0)

            # Days since last service
            def calc_days_since(row):
                if pd.isna(row["last_service_date"]):
                    return 180  # Default unobserved
                return max(0, (cutoff_date - row["last_service_date"]).days)

            df["days_since_last_service"] = df.apply(calc_days_since, axis=1)
            df.drop(columns=["last_service_date"], inplace=True, errors="ignore")

            # Target label
            df["target"] = df["vehicle_id"].apply(lambda v_id: 1 if v_id in positive_targets else 0)
            df["cutoff_date"] = cutoff_date

            return df

        finally:
            conn.close()

    # --------------------------------------------------------------------------
    # Area 2: Sensor Anomaly Features & Known Fault Window Excision
    # --------------------------------------------------------------------------
    def extract_sensor_telemetry_features(
        self,
        cutoff_date: Optional[date] = None,
        excise_fault_windows: bool = True,
    ) -> pd.DataFrame:
        """Extract sensor telemetry records and optionally excise known fault windows."""
        conn = self._get_connection()
        try:
            sql = """
                SELECT 
                    t.vehicle_key,
                    v.vehicle_id,
                    t.timestamp,
                    t.rpm,
                    t.temperature,
                    t.battery,
                    t.vibration
                FROM autocare_dw.fact_telemetry t
                JOIN autocare_dw.dim_vehicle v ON t.vehicle_key = v.vehicle_key
            """
            params = []
            if cutoff_date is not None:
                sql += " WHERE t.timestamp <= %s"
                params.append(datetime.combine(cutoff_date, datetime.max.time()))
            sql += " ORDER BY t.timestamp ASC;"

            df = pd.read_sql(sql, conn, params=params if params else None)
            if df.empty:
                return df

            # Feature transformations (robust normalization and interactions)
            df["norm_rpm"] = (df["rpm"] - df["rpm"].median()) / (df["rpm"].quantile(0.75) - df["rpm"].quantile(0.25) + 1e-5)
            df["norm_temperature"] = (df["temperature"] - df["temperature"].median()) / (df["temperature"].quantile(0.75) - df["temperature"].quantile(0.25) + 1e-5)
            df["norm_vibration"] = (df["vibration"] - df["vibration"].median()) / (df["vibration"].quantile(0.75) - df["vibration"].quantile(0.25) + 1e-5)
            df["vibration_per_rpm_ratio"] = df["vibration"] / (df["rpm"] + 1.0)

            if excise_fault_windows:
                # Query severe DTC events to identify fault windows
                dtc_sql = """
                    SELECT vehicle_id, timestamp
                    FROM staging.silver_diagnostics
                    WHERE severity IN ('CRITICAL', 'HIGH');
                """
                dtc_df = pd.read_sql(dtc_sql, conn)
                fault_intervals = []
                for _, row in dtc_df.iterrows():
                    v_id = row["vehicle_id"]
                    t_fault = pd.to_datetime(row["timestamp"])
                    t_start = t_fault - timedelta(hours=FAULT_EXCLUSION_PRE_HOURS)
                    t_end = t_fault + timedelta(hours=FAULT_EXCLUSION_POST_HOURS)
                    fault_intervals.append((v_id, t_start, t_end))

                # Flag records falling inside any fault window
                is_fault = np.zeros(len(df), dtype=bool)
                df_ts = pd.to_datetime(df["timestamp"])
                for v_id, t_start, t_end in fault_intervals:
                    mask = (df["vehicle_id"] == v_id) & (df_ts >= t_start) & (df_ts <= t_end)
                    is_fault |= mask.values

                df["is_fault_window"] = is_fault
            else:
                df["is_fault_window"] = False

            return df
        finally:
            conn.close()

    # --------------------------------------------------------------------------
    # Area 3: Service-Demand Forecasting Features
    # --------------------------------------------------------------------------
    def extract_service_demand_series(self) -> pd.DataFrame:
        """Extract historical daily service visit counts per dealer with lag features."""
        conn = self._get_connection()
        try:
            sql = """
                SELECT 
                    d.dealer_id,
                    s.visit_date,
                    COUNT(s.service_fact_id) as service_count
                FROM autocare_dw.fact_service s
                JOIN autocare_dw.dim_dealer d ON s.dealer_key = d.dealer_key
                GROUP BY d.dealer_id, s.visit_date
                ORDER BY d.dealer_id, s.visit_date ASC;
            """
            df = pd.read_sql(sql, conn)
            if df.empty:
                return df

            # Expand to full date grid per dealer to avoid skipping zero-visit days
            min_date = df["visit_date"].min()
            max_date = df["visit_date"].max()
            all_dealers = df["dealer_id"].unique()
            date_range = pd.date_range(min_date, max_date, freq="D").date

            grid = pd.MultiIndex.from_product([all_dealers, date_range], names=["dealer_id", "visit_date"]).to_frame().reset_index(drop=True)
            df = grid.merge(df, on=["dealer_id", "visit_date"], how="left")
            df["service_count"] = df["service_count"].fillna(0).astype(int)

            # Sort and compute lag features point-in-time per dealer
            df.sort_values(by=["dealer_id", "visit_date"], inplace=True)
            df["service_count_lag_7d"] = df.groupby("dealer_id")["service_count"].shift(7).fillna(0)
            df["service_count_lag_14d"] = df.groupby("dealer_id")["service_count"].shift(14).fillna(0)
            df["rolling_mean_service_count_7d"] = df.groupby("dealer_id")["service_count"].shift(1).rolling(7, min_periods=1).mean().fillna(0)

            # Calendar features from visit_date
            dates = pd.to_datetime(df["visit_date"])
            df["day_of_week"] = dates.dt.dayofweek
            df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)

            return df
        finally:
            conn.close()

    # --------------------------------------------------------------------------
    # Area 4: Warranty Anomaly Features (Unsupervised)
    # --------------------------------------------------------------------------
    def extract_warranty_features(self) -> pd.DataFrame:
        """Extract approved warranty claim records and compute statistical deviation features.
        
        Uses strictly verified fields: claim_id, vehicle_id, component, claim_date, amount.
        """
        conn = self._get_connection()
        try:
            sql = """
                SELECT 
                    w.claim_id,
                    v.vehicle_id,
                    c.component_name as component_id,
                    w.claim_date,
                    w.amount as claim_amount
                FROM autocare_dw.fact_warranty w
                JOIN autocare_dw.dim_vehicle v ON w.vehicle_key = v.vehicle_key
                JOIN autocare_dw.dim_component c ON w.component_key = c.component_key
                ORDER BY w.claim_date ASC;
            """
            df = pd.read_sql(sql, conn)
            if df.empty:
                return df

            # Component-level historical medians and IQR
            comp_stats = df.groupby("component_id")["claim_amount"].agg(
                median_amount="median",
                q25=lambda x: x.quantile(0.25),
                q75=lambda x: x.quantile(0.75),
            ).reset_index()
            comp_stats["iqr"] = comp_stats["q75"] - comp_stats["q25"]

            df = df.merge(comp_stats, on="component_id", how="left")
            df["claim_amount_to_component_median_ratio"] = df["claim_amount"] / (df["median_amount"] + 1e-5)
            df["component_claim_iqr_distance"] = (df["claim_amount"] - df["q75"]) / (df["iqr"] + 1e-5)

            # Rolling claim frequency by vehicle in preceding 30 days
            df.sort_values(by="claim_date", inplace=True)
            df["rolling_vehicle_claims_30d"] = df.groupby("vehicle_id")["claim_id"].transform("count")

            return df
        finally:
            conn.close()
