"""dbt Operator and execution plugin for AutoCare Intelligence Airflow DAGs.

Executes dbt-core commands against the PostgreSQL analytical warehouse
within the isolated dbt_autocare project.
"""

import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

DEFAULT_DBT_PROJECT_DIR = Path(__file__).resolve().parent.parent.parent / "dbt_autocare"


def execute_dbt_command(
    command: str,
    project_dir: Optional[Path] = None,
    profiles_dir: Optional[Path] = None,
    select: Optional[str] = None,
    vars_dict: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Execute a dbt command via the virtual environment CLI."""
    p_dir = Path(project_dir or DEFAULT_DBT_PROJECT_DIR).resolve()
    prof_dir = Path(profiles_dir or p_dir).resolve()

    base_dir = p_dir.parent
    venv_dbt = base_dir / ".venv" / "Scripts" / "dbt.exe"
    dbt_bin = str(venv_dbt) if venv_dbt.exists() else "dbt"

    cmd = [
        dbt_bin,
        command,
        "--project-dir",
        str(p_dir),
        "--profiles-dir",
        str(prof_dir),
    ]

    if select:
        cmd.extend(["--select", select])

    if vars_dict:
        import json
        cmd.extend(["--vars", json.dumps(vars_dict)])

    logger.info(f"Executing dbt command: {' '.join(cmd)}")
    start_time = time.time()

    env = os.environ.copy()
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(p_dir),
        env=env,
    )
    elapsed = time.time() - start_time

    success = result.returncode == 0
    if not success:
        logger.error(f"dbt {command} failed (code {result.returncode}):\n{result.stdout}\n{result.stderr}")
    else:
        logger.info(f"dbt {command} completed successfully in {elapsed:.2f}s")

    return {
        "command": command,
        "return_code": result.returncode,
        "success": success,
        "elapsed_seconds": elapsed,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


class DbtOperator:
    """Wrapper class for dbt tasks in Airflow PythonOperator workflows."""

    def __init__(
        self,
        command: str = "build",
        project_dir: Optional[Path] = None,
        select: Optional[str] = None,
    ):
        self.command = command
        self.project_dir = project_dir or DEFAULT_DBT_PROJECT_DIR
        self.select = select

    def execute(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute dbt task and raise if failed."""
        res = execute_dbt_command(
            command=self.command,
            project_dir=self.project_dir,
            select=self.select,
        )
        if not res["success"]:
            raise RuntimeError(f"dbt {self.command} failed with return code {res['return_code']}")
        return res
