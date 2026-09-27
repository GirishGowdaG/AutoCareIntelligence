"""Ingestion Manifest Manager for AutoCare Intelligence.

Maintains state metadata tracking for ingested raw files at airflow/state/ingestion_manifest.json.
Guarantees frozen Phase 2 Bronze data is never modified by orchestration control files.
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

DEFAULT_MANIFEST_PATH = Path(__file__).resolve().parent / "ingestion_manifest.json"


def compute_sha256(file_path: Path, chunk_size: int = 65536) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


class IngestionManifest:
    """Manages ingestion state and file hash change detection."""

    def __init__(self, manifest_path: Path = DEFAULT_MANIFEST_PATH):
        self.manifest_path = Path(manifest_path)
        self.entries: Dict[str, Dict[str, Any]] = {}
        self.load()

    def load(self) -> None:
        """Load manifest from disk if it exists."""
        if self.manifest_path.exists():
            try:
                with open(self.manifest_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.entries = data.get("files", {})
            except Exception as e:
                logger.warning(f"Error loading ingestion manifest ({e}), starting with empty state.")
                self.entries = {}
        else:
            self.entries = {}

    def save(self) -> None:
        """Save manifest atomically to disk."""
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.manifest_path.with_suffix(".tmp")
        payload = {
            "version": "1.0",
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "total_files_tracked": len(self.entries),
            "files": self.entries,
        }
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        temp_path.replace(self.manifest_path)

    def scan_directory(self, base_dir: Path) -> List[Tuple[Path, bool]]:
        """Scan directory and determine which files are new or modified.
        
        Returns: list of (file_path, is_new_or_modified)
        """
        results = []
        base_dir = Path(base_dir)
        if not base_dir.exists():
            return results

        for path in sorted(base_dir.glob("**/*")):
            if not path.is_file():
                continue
            if path.name.startswith(".") or path.suffix in [".tmp", ".lock"]:
                continue

            rel_key = str(path.relative_to(base_dir.parent if base_dir.parent.exists() else base_dir)).replace("\\", "/")
            curr_size = path.stat().st_size
            curr_hash = compute_sha256(path)

            existing = self.entries.get(rel_key)
            if existing is None:
                is_changed = True
            elif existing.get("sha256") != curr_hash or existing.get("file_size") != curr_size:
                is_changed = True
            else:
                is_changed = False

            results.append((path, is_changed))
        return results

    def record_processed_file(
        self,
        file_path: Path,
        base_dir: Path,
        batch_id: str,
    ) -> None:
        """Record a successfully processed file into the manifest."""
        path = Path(file_path)
        base_dir = Path(base_dir)
        rel_key = str(path.relative_to(base_dir.parent if base_dir.parent.exists() else base_dir)).replace("\\", "/")
        curr_size = path.stat().st_size
        curr_hash = compute_sha256(path)

        self.entries[rel_key] = {
            "source_path": str(path.resolve()),
            "file_size": curr_size,
            "sha256": curr_hash,
            "ingestion_batch_id": batch_id,
            "processed_at": datetime.now(timezone.utc).isoformat(),
        }
