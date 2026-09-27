"""DagBag loader for discovering and validating Airflow DAG definitions."""

import importlib.util
import logging
import os
import sys
from pathlib import Path
from typing import Optional, Union, Dict, Any, List

from airflow.models.dag import DAG

logger = logging.getLogger(__name__)


class DagBag:
    """Discovers, parses, and holds Airflow DAG instances from a folder."""

    def __init__(self, dag_folder: Optional[Union[str, Path]] = None, include_examples: bool = False):
        if dag_folder is None:
            dag_folder = Path(__file__).resolve().parent.parent / "dags"
        self.dag_folder = Path(dag_folder)
        self.dags: Dict[str, DAG] = {}
        self.import_errors: Dict[str, str] = {}
        self.collect_dags()

    def collect_dags(self) -> None:
        """Scan directory and load DAG instances."""
        if not self.dag_folder.exists():
            return

        for path in sorted(self.dag_folder.glob("*.py")):
            if path.name.startswith("__"):
                continue

            module_name = f"airflow_dags_{path.stem}"
            try:
                spec = importlib.util.spec_from_file_location(module_name, str(path))
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)

                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if isinstance(attr, DAG):
                            self.dags[attr.dag_id] = attr

            except Exception as e:
                logger.error(f"Failed to load DAG file {path}: {e}")
                self.import_errors[str(path)] = str(e)

    def get_dag(self, dag_id: str) -> Optional[DAG]:
        return self.dags.get(dag_id)
