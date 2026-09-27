"""EmptyOperator (DummyOperator) implementation for Airflow."""

from typing import Optional, Dict, Any
from airflow.models.baseoperator import BaseOperator
from airflow.models.dag import DAG


class EmptyOperator(BaseOperator):
    """Operator that performs no action, used for DAG structure and synchronization."""

    def __init__(self, task_id: str, dag: Optional[DAG] = None, **kwargs):
        super().__init__(task_id=task_id, dag=dag or DAG.get_current_dag(), **kwargs)

    def execute(self, context: Optional[Dict[str, Any]] = None) -> None:
        pass


# Backward compatibility alias
DummyOperator = EmptyOperator
