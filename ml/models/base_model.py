"""Base ML Model class and serialization envelope for AutoCare Intelligence.

Enforces reproducibility, pinned random seeds, metadata tracking, and SHA-256 data hashing.
"""

import hashlib
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
import joblib
import pandas as pd

from ml.config import RANDOM_SEED

logger = logging.getLogger(__name__)


def compute_df_sha256(df: pd.DataFrame) -> str:
    """Compute deterministic SHA-256 hash of a pandas DataFrame."""
    h = hashlib.sha256()
    h.update(pd.util.hash_pandas_object(df, index=True).values.tobytes())
    return h.hexdigest()


class BaseModel(ABC):
    """Abstract base estimator wrapper with standardized MLOps lifecycle."""

    def __init__(
        self,
        model_id: str,
        model_version: str = "v1.0.0",
        random_state: int = RANDOM_SEED,
    ):
        self.model_id = model_id
        self.model_version = model_version
        self.random_state = random_state
        self.estimator = None
        self.feature_names: List[str] = []
        self.metadata: Dict[str, Any] = {}
        self.is_fitted: bool = False

    @abstractmethod
    def fit(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> "BaseModel":
        """Fit estimator on training data."""
        pass

    @abstractmethod
    def predict(self, X: pd.DataFrame) -> Any:
        """Generate predictions."""
        pass

    @abstractmethod
    def evaluate(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> Dict[str, float]:
        """Compute performance metrics."""
        pass

    def save(self, output_dir: Path) -> Path:
        """Serialize model artifact (.joblib) and metadata manifest (manifest.json)."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        artifact_file = output_dir / "model.joblib"
        manifest_file = output_dir / "manifest.json"

        # Save model estimator
        payload = {
            "estimator": self.estimator,
            "feature_names": self.feature_names,
            "model_id": self.model_id,
            "model_version": self.model_version,
            "random_state": self.random_state,
        }
        joblib.dump(payload, artifact_file)

        # Update and save metadata manifest
        self.metadata["artifact_path"] = str(artifact_file.resolve())
        self.metadata["serialized_at"] = datetime.now(timezone.utc).isoformat()
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, indent=2)

        logger.info(f"Model {self.model_id} ({self.model_version}) saved to {output_dir}")
        return artifact_file

    def load(self, model_file: Path) -> "BaseModel":
        """Load serialized estimator and features."""
        model_file = Path(model_file)
        payload = joblib.load(model_file)

        self.estimator = payload["estimator"]
        self.feature_names = payload["feature_names"]
        self.model_id = payload["model_id"]
        self.model_version = payload["model_version"]
        self.random_state = payload["random_state"]
        self.is_fitted = True

        manifest_file = model_file.parent / "manifest.json"
        if manifest_file.exists():
            with open(manifest_file, "r", encoding="utf-8") as f:
                self.metadata = json.load(f)

        return self
