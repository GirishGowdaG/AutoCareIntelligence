"""DAG model for Airflow directed acyclic graphs."""

from datetime import datetime
from typing import Optional, Dict, Any, List, Set, Union
import threading

_CURRENT_DAG: threading.local = threading.local()


class DAG:
    """Directed Acyclic Graph representation of Airflow workflow."""

    def __init__(
        self,
        dag_id: str,
        description: str = "",
        schedule_interval: Optional[Union[str, Any]] = None,
        schedule: Optional[Union[str, Any]] = None,
        start_date: Optional[datetime] = None,
        catchup: bool = False,
        default_args: Optional[Dict[str, Any]] = None,
        max_active_runs: int = 1,
        tags: Optional[List[str]] = None,
    ):
        self.dag_id = dag_id
        self.description = description
        self.schedule_interval = schedule if schedule is not None else schedule_interval
        self.start_date = start_date
        self.catchup = catchup
        self.default_args = default_args or {}
        self.max_active_runs = max_active_runs
        self.tags = tags or []
        self.tasks: Dict[str, Any] = {}

    def __enter__(self) -> "DAG":
        _CURRENT_DAG.dag = self
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        _CURRENT_DAG.dag = None

    @classmethod
    def get_current_dag(cls) -> Optional["DAG"]:
        return getattr(_CURRENT_DAG, "dag", None)

    def add_task(self, task: Any) -> None:
        if task.task_id in self.tasks:
            raise ValueError(f"Task with id '{task.task_id}' already registered in DAG '{self.dag_id}'")
        self.tasks[task.task_id] = task

    def get_task(self, task_id: str) -> Any:
        if task_id not in self.tasks:
            raise KeyError(f"Task '{task_id}' not found in DAG '{self.dag_id}'")
        return self.tasks[task_id]

    def has_cycle(self) -> bool:
        """Check for cycles in task dependency graph using depth-first search."""
        visited: Set[str] = set()
        recursion_stack: Set[str] = set()

        def dfs(task_id: str) -> bool:
            visited.add(task_id)
            recursion_stack.add(task_id)

            task = self.tasks[task_id]
            for downstream in task.downstream_list:
                d_id = downstream.task_id
                if d_id not in visited:
                    if dfs(d_id):
                        return True
                elif d_id in recursion_stack:
                    return True

            recursion_stack.remove(task_id)
            return False

        for t_id in self.tasks:
            if t_id not in visited:
                if dfs(t_id):
                    return True
        return False

    def topological_sort(self) -> List[Any]:
        """Return tasks ordered by dependency execution order."""
        if self.has_cycle():
            raise ValueError(f"Cycle detected in DAG '{self.dag_id}'")

        in_degree = {t_id: len(task.upstream_list) for t_id, task in self.tasks.items()}
        queue = [self.tasks[t_id] for t_id, deg in in_degree.items() if deg == 0]
        order = []

        while queue:
            task = queue.pop(0)
            order.append(task)
            for downstream in task.downstream_list:
                in_degree[downstream.task_id] -= 1
                if in_degree[downstream.task_id] == 0:
                    queue.append(downstream)

        return order
