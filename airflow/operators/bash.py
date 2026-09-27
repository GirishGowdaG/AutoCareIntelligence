"""BashOperator implementation for Airflow."""

import subprocess
import os
from typing import Optional, Dict, Any
from airflow.models.baseoperator import BaseOperator
from airflow.models.dag import DAG


class BashOperator(BaseOperator):
    """Operator that executes a shell command."""

    def __init__(
        self,
        task_id: str,
        bash_command: str,
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None,
        dag: Optional[DAG] = None,
        **kwargs,
    ):
        super().__init__(task_id=task_id, dag=dag or DAG.get_current_dag(), **kwargs)
        self.bash_command = bash_command
        self.env = env
        self.cwd = cwd

    def execute(self, context: Optional[Dict[str, Any]] = None) -> int:
        cmd_env = os.environ.copy()
        if self.env:
            cmd_env.update(self.env)

        res = subprocess.run(
            self.bash_command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=self.cwd,
            env=cmd_env,
        )
        if res.returncode != 0:
            raise RuntimeError(f"Bash command failed with code {res.returncode}:\n{res.stderr}")
        return res.returncode
