"""PythonOperator implementation for Airflow."""

from typing import Optional, Callable, Dict, Any, List
from airflow.models.baseoperator import BaseOperator
from airflow.models.dag import DAG


class PythonOperator(BaseOperator):
    """Operator that executes a Python callable."""

    def __init__(
        self,
        task_id: str,
        python_callable: Callable,
        op_args: Optional[List[Any]] = None,
        op_kwargs: Optional[Dict[str, Any]] = None,
        dag: Optional[DAG] = None,
        **kwargs,
    ):
        super().__init__(task_id=task_id, dag=dag or DAG.get_current_dag(), **kwargs)
        self.python_callable = python_callable
        self.op_args = op_args or []
        self.op_kwargs = op_kwargs or {}

    def execute(self, context: Optional[Dict[str, Any]] = None) -> Any:
        return self.python_callable(*self.op_args, **self.op_kwargs)
