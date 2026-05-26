from __future__ import annotations

import os
from pathlib import Path
import subprocess


class GhCliWorkflowRunLogReader:
    def __init__(self, repository_root: Path) -> None:
        self._repository_root = Path(repository_root)

    def read_run_log(self, run_id: int) -> str:
        command = ["gh", "run", "view", str(run_id), "--log"]
        environment = os.environ.copy()
        environment.setdefault("GH_PAGER", "cat")
        completed = subprocess.run(
            command,
            cwd=self._repository_root,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                f"gh run view {run_id} --log failed with exit code {completed.returncode}."
                f"\nSTDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
            )
        return completed.stdout
