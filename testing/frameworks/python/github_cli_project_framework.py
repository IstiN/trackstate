from __future__ import annotations

import json
from pathlib import Path
import subprocess

from testing.core.interfaces.project_cli_probe import ProjectCliProbe
from testing.core.models.cli_command_result import CliCommandResult


class GitHubCliProjectFramework(ProjectCliProbe):
    def __init__(self, repository_root: Path) -> None:
        self._repository_root = repository_root

    def auth_status(self) -> CliCommandResult:
        return self._run(("gh", "auth", "status"))

    def get_project(self, repository: str, project_path: str) -> CliCommandResult:
        command = (
            "gh",
            "api",
            f"repos/{repository}/contents/{project_path}",
            "-H",
            "Accept: application/vnd.github.raw+json",
        )
        result = self._run(command)
        payload: dict[str, object] | None = None
        if result.succeeded:
            payload = json.loads(result.stdout)
            result = CliCommandResult(
                command=result.command,
                exit_code=result.exit_code,
                stdout=result.stdout,
                stderr=result.stderr,
                json_payload=payload,
            )
        return result

    def _run(self, command: tuple[str, ...]) -> CliCommandResult:
        completed = subprocess.run(
            command,
            cwd=self._repository_root,
            capture_output=True,
            text=True,
            check=False,
        )
        return CliCommandResult(
            command=command,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
