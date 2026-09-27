"""BaseOperator model for Airflow tasks."""

from datetime import timedelta
from typing import Optional, List, Set, Any, Dict, Callable


class BaseOperator:
    """Base class for all Airflow operators."""

    def __init__(
        self,
        task_id: str,
        dag: Optional[Any] = None,
        retries: int = 0,
        retry_delay: Optional[timedelta] = None,
        email: Optional[List[str]] = None,
        email_on_failure: bool = False,
        email_on_retry: bool = False,
        **kwargs,
    ):
        self.task_id = task_id
        self.retries = retries
        self.retry_delay = retry_delay or timedelta(seconds=300)
        self.email = email
        self.email_on_failure = email_on_failure
        self.email_on_retry = email_on_retry
        self.upstream_list: Set["BaseOperator"] = set()
        self.downstream_list: Set["BaseOperator"] = set()
        self.dag = dag
        self.extra_kwargs = kwargs

        if dag is not None:
            dag.add_task(self)

    def set_downstream(self, other: Any) -> Any:
        """Set downstream task or list of tasks."""
        if isinstance(other, (list, tuple, set)):
            for o in other:
                self.set_downstream(o)
            return other

        self.downstream_list.add(other)
        other.upstream_list.add(self)
        return other

    def set_upstream(self, other: Any) -> Any:
        """Set upstream task or list of tasks."""
        if isinstance(other, (list, tuple, set)):
            for o in other:
                self.set_upstream(o)
            return other

        self.upstream_list.add(other)
        other.downstream_list.add(self)
        return other

    def __rshift__(self, other: Any) -> Any:
        """Self >> other."""
        return self.set_downstream(other)

    def __lshift__(self, other: Any) -> Any:
        """Self << other."""
        return self.set_upstream(other)

    def __rrshift__(self, other: Any) -> Any:
        """Other >> self when other is a list."""
        if isinstance(other, (list, tuple)):
            for o in other:
                o.set_downstream(self)
            return self
        return self.set_upstream(other)

    def __rlshift__(self, other: Any) -> Any:
        """Other << self when other is a list."""
        if isinstance(other, (list, tuple)):
            for o in other:
                o.set_upstream(self)
            return self
        return self.set_downstream(other)

    def execute(self, context: Optional[Dict[str, Any]] = None) -> Any:
        """Execute operator logic."""
        raise NotImplementedError()
