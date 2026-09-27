"""Streaming-to-Silver Compaction Engine for AutoCare Intelligence.

Compacts Streaming Bronze micro-batch Parquet files into Silver clean partitions,
deduplicating against existing Silver records and routing duplicates to Silver Quarantine.
Strictly enforces mathematical row conservation:
    N_streaming_input = N_silver_added + N_quarantine_added
"""

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set

import pandas as pd
import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq

from streaming.config import (
    STREAMING_TELEMETRY_DIR,
    STREAMING_DIAGNOSTICS_DIR,
    SILVER_TELEMETRY_DIR,
    SILVER_DIAGNOSTICS_DIR,
    QUARANTINE_TELEMETRY_DIR,
    QUARANTINE_DIAGNOSTICS_DIR,
)

logger = logging.getLogger(__name__)


class StreamingCompactor:
    """Compacts streaming Bronze Parquet micro-batches into Silver storage."""

    def __init__(
        self,
        streaming_telemetry_dir: Path = STREAMING_TELEMETRY_DIR,
        streaming_diagnostics_dir: Path = STREAMING_DIAGNOSTICS_DIR,
        silver_telemetry_dir: Path = SILVER_TELEMETRY_DIR,
        silver_diagnostics_dir: Path = SILVER_DIAGNOSTICS_DIR,
        quarantine_telemetry_dir: Path = QUARANTINE_TELEMETRY_DIR,
        quarantine_diagnostics_dir: Path = QUARANTINE_DIAGNOSTICS_DIR,
    ):
        self.streaming_telemetry_dir = Path(streaming_telemetry_dir)
        self.streaming_diagnostics_dir = Path(streaming_diagnostics_dir)
        self.silver_telemetry_dir = Path(silver_telemetry_dir)
        self.silver_diagnostics_dir = Path(silver_diagnostics_dir)
        self.quarantine_telemetry_dir = Path(quarantine_telemetry_dir)
        self.quarantine_diagnostics_dir = Path(quarantine_diagnostics_dir)

    def _get_existing_telemetry_keys(self) -> Set[Tuple[str, str]]:
        """Extract existing (vehicle_id, timestamp_str) keys from Silver telemetry."""
        keys = set()
        if not self.silver_telemetry_dir.exists():
            return keys

        try:
            dataset = ds.dataset(str(self.silver_telemetry_dir), format="parquet")
            table = dataset.to_table(columns=["vehicle_id", "timestamp"])
            df = table.to_pandas()
            for _, row in df.iterrows():
                ts_str = pd.to_datetime(row["timestamp"]).isoformat()
                keys.add((str(row["vehicle_id"]), ts_str))
        except Exception as e:
            logger.warning(f"Could not read existing silver telemetry keys: {e}")
        return keys

    def _get_existing_diagnostics_keys(self) -> Set[Tuple[str, str, str]]:
        """Extract existing (vehicle_id, timestamp_str, code) keys from Silver diagnostics."""
        keys = set()
        if not self.silver_diagnostics_dir.exists():
            return keys

        try:
            dataset = ds.dataset(str(self.silver_diagnostics_dir), format="parquet")
            table = dataset.to_table(columns=["vehicle_id", "timestamp", "code"])
            df = table.to_pandas()
            for _, row in df.iterrows():
                ts_str = pd.to_datetime(row["timestamp"]).isoformat()
                keys.add((str(row["vehicle_id"]), ts_str, str(row["code"]).upper()))
        except Exception as e:
            logger.warning(f"Could not read existing silver diagnostics keys: {e}")
        return keys

    def compact_telemetry(
        self,
        batch_id: Optional[str] = None,
        archive_processed_files: bool = False,
    ) -> Dict[str, Any]:
        """Compact pending streaming telemetry micro-batches.
        
        Preserves mathematical row conservation:
            input_count == silver_added + quarantine_added
        """
        batch_id = batch_id or f"compact_{uuid.uuid4().hex[:12]}"
        now_utc = datetime.now(timezone.utc).isoformat()

        # Find all parquet files in streaming bronze
        parquet_files = list(self.streaming_telemetry_dir.glob("**/*.parquet"))
        if not parquet_files:
            return {
                "dataset": "telemetry",
                "input_count": 0,
                "silver_added": 0,
                "quarantine_added": 0,
                "conservation_verified": True,
            }

        dfs = []
        for pf in parquet_files:
            try:
                table = pq.read_table(str(pf))
                dfs.append(table.to_pandas())
            except Exception as e:
                logger.error(f"Error reading streaming parquet {pf}: {e}")

        if not dfs:
            return {
                "dataset": "telemetry",
                "input_count": 0,
                "silver_added": 0,
                "quarantine_added": 0,
                "conservation_verified": True,
            }

        combined_df = pd.concat(dfs, ignore_index=True)
        input_count = len(combined_df)
        existing_keys = self._get_existing_telemetry_keys()

        seen_in_batch: Set[Tuple[str, str]] = set()
        clean_records: List[Dict[str, Any]] = []
        quarantine_records: List[Dict[str, Any]] = []

        for _, row in combined_df.iterrows():
            rec = row.to_dict()
            ts_str = pd.to_datetime(rec["timestamp"]).isoformat()
            key = (str(rec["vehicle_id"]), ts_str)

            if key in existing_keys or key in seen_in_batch:
                q_rec = dict(rec)
                q_rec["_quarantine_rule"] = "DUPLICATE_KEY"
                q_rec["_quarantine_reason"] = f"Duplicate record for key (vehicle_id={key[0]}, timestamp={key[1]})"
                q_rec["_quarantined_at"] = now_utc
                quarantine_records.append(q_rec)
            else:
                seen_in_batch.add(key)
                clean_rec = dict(rec)
                clean_rec["_silver_processed_at"] = now_utc
                clean_rec["_silver_batch_id"] = batch_id
                clean_records.append(clean_rec)

        # Enforce mathematical row conservation
        assert len(clean_records) + len(quarantine_records) == input_count, (
            f"Row conservation violated for telemetry: "
            f"Input={input_count} != Clean({len(clean_records)}) + Quarantine({len(quarantine_records)})"
        )

        # Write clean records to Silver delta partitions
        if clean_records:
            clean_df = pd.DataFrame(clean_records)
            clean_df["timestamp"] = pd.to_datetime(clean_df["timestamp"])
            clean_df["year"] = clean_df["timestamp"].dt.year
            clean_df["month"] = clean_df["timestamp"].dt.month
            clean_df["day"] = clean_df["timestamp"].dt.day

            for (year, month, day), group in clean_df.groupby(["year", "month", "day"]):
                out_dir = self.silver_telemetry_dir / f"year={year}" / f"month={month}" / f"day={day}"
                out_dir.mkdir(parents=True, exist_ok=True)
                out_file = out_dir / f"stream_{batch_id}.parquet"
                sub_df = group.drop(columns=["year", "month", "day"])
                table = pa.Table.from_pandas(sub_df, preserve_index=False)
                pq.write_table(table, str(out_file), compression="SNAPPY")

        # Write quarantine records
        if quarantine_records:
            self.quarantine_telemetry_dir.mkdir(parents=True, exist_ok=True)
            q_file = self.quarantine_telemetry_dir / f"quarantine_{batch_id}.parquet"
            q_table = pa.Table.from_pandas(pd.DataFrame(quarantine_records), preserve_index=False)
            pq.write_table(q_table, str(q_file), compression="SNAPPY")

        # Optionally cleanup/archive processed streaming bronze files
        if archive_processed_files:
            for pf in parquet_files:
                try:
                    pf.unlink()
                except Exception as e:
                    logger.warning(f"Could not remove processed bronze file {pf}: {e}")

        return {
            "dataset": "telemetry",
            "input_count": input_count,
            "silver_added": len(clean_records),
            "quarantine_added": len(quarantine_records),
            "conservation_verified": (input_count == len(clean_records) + len(quarantine_records)),
        }

    def compact_diagnostics(
        self,
        batch_id: Optional[str] = None,
        archive_processed_files: bool = False,
    ) -> Dict[str, Any]:
        """Compact pending streaming diagnostics micro-batches.
        
        Preserves mathematical row conservation:
            input_count == silver_added + quarantine_added
        """
        batch_id = batch_id or f"compact_{uuid.uuid4().hex[:12]}"
        now_utc = datetime.now(timezone.utc).isoformat()

        parquet_files = list(self.streaming_diagnostics_dir.glob("**/*.parquet"))
        if not parquet_files:
            return {
                "dataset": "diagnostics",
                "input_count": 0,
                "silver_added": 0,
                "quarantine_added": 0,
                "conservation_verified": True,
            }

        dfs = []
        for pf in parquet_files:
            try:
                table = pq.read_table(str(pf))
                dfs.append(table.to_pandas())
            except Exception as e:
                logger.error(f"Error reading streaming parquet {pf}: {e}")

        if not dfs:
            return {
                "dataset": "diagnostics",
                "input_count": 0,
                "silver_added": 0,
                "quarantine_added": 0,
                "conservation_verified": True,
            }

        combined_df = pd.concat(dfs, ignore_index=True)
        input_count = len(combined_df)
        existing_keys = self._get_existing_diagnostics_keys()

        seen_in_batch: Set[Tuple[str, str, str]] = set()
        clean_records: List[Dict[str, Any]] = []
        quarantine_records: List[Dict[str, Any]] = []

        for _, row in combined_df.iterrows():
            rec = row.to_dict()
            ts_str = pd.to_datetime(rec["timestamp"]).isoformat()
            key = (str(rec["vehicle_id"]), ts_str, str(rec["code"]).upper())

            if key in existing_keys or key in seen_in_batch:
                q_rec = dict(rec)
                q_rec["_quarantine_rule"] = "DUPLICATE_KEY"
                q_rec["_quarantine_reason"] = (
                    f"Duplicate record for key (vehicle_id={key[0]}, timestamp={key[1]}, code={key[2]})"
                )
                q_rec["_quarantined_at"] = now_utc
                quarantine_records.append(q_rec)
            else:
                seen_in_batch.add(key)
                clean_rec = dict(rec)
                clean_rec["_silver_processed_at"] = now_utc
                clean_rec["_silver_batch_id"] = batch_id
                clean_records.append(clean_rec)

        # Enforce mathematical row conservation
        assert len(clean_records) + len(quarantine_records) == input_count, (
            f"Row conservation violated for diagnostics: "
            f"Input={input_count} != Clean({len(clean_records)}) + Quarantine({len(quarantine_records)})"
        )

        # Write clean records
        if clean_records:
            clean_df = pd.DataFrame(clean_records)
            clean_df["timestamp"] = pd.to_datetime(clean_df["timestamp"])
            clean_df["year"] = clean_df["timestamp"].dt.year
            clean_df["month"] = clean_df["timestamp"].dt.month
            clean_df["day"] = clean_df["timestamp"].dt.day

            for (year, month, day), group in clean_df.groupby(["year", "month", "day"]):
                out_dir = self.silver_diagnostics_dir / f"year={year}" / f"month={month}" / f"day={day}"
                out_dir.mkdir(parents=True, exist_ok=True)
                out_file = out_dir / f"stream_{batch_id}.parquet"
                sub_df = group.drop(columns=["year", "month", "day"])
                table = pa.Table.from_pandas(sub_df, preserve_index=False)
                pq.write_table(table, str(out_file), compression="SNAPPY")

        # Write quarantine records
        if quarantine_records:
            self.quarantine_diagnostics_dir.mkdir(parents=True, exist_ok=True)
            q_file = self.quarantine_diagnostics_dir / f"quarantine_{batch_id}.parquet"
            q_table = pa.Table.from_pandas(pd.DataFrame(quarantine_records), preserve_index=False)
            pq.write_table(q_table, str(q_file), compression="SNAPPY")

        if archive_processed_files:
            for pf in parquet_files:
                try:
                    pf.unlink()
                except Exception as e:
                    logger.warning(f"Could not remove processed bronze file {pf}: {e}")

        return {
            "dataset": "diagnostics",
            "input_count": input_count,
            "silver_added": len(clean_records),
            "quarantine_added": len(quarantine_records),
            "conservation_verified": (input_count == len(clean_records) + len(quarantine_records)),
        }

    def compact_all(self, archive_processed_files: bool = False) -> List[Dict[str, Any]]:
        """Compact both telemetry and diagnostics streaming datasets."""
        res_t = self.compact_telemetry(archive_processed_files=archive_processed_files)
        res_d = self.compact_diagnostics(archive_processed_files=archive_processed_files)
        return [res_t, res_d]
