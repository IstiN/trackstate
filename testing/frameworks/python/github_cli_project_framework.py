from __future__ import annotations

import json
from pathlib import Path
import subprocess
from urllib.parse import quote
from urllib.request import Request, urlopen

from testing.core.interfaces.project_cli_probe import ProjectCliProbe
from testing.core.models.cli_command_result import CliCommandResult


class GitHubCliProjectFramework(ProjectCliProbe):
    def __init__(self, repository_root: Path) -> None:
        self._repository_root = repository_root

    def auth_status(self) -> CliCommandResult:
        return self._run(("gh", "auth", "status"))

    def viewer_login(self) -> CliCommandResult:
        command = ("gh", "api", "user", "--jq", ".login")
        result = self._run(command)
        login = result.stdout.strip()
        return CliCommandResult(
            command=result.command,
            exit_code=result.exit_code,
            stdout=result.stdout,
            stderr=result.stderr,
            json_payload=login if result.succeeded else None,
        )

    def repository_metadata(self, repository: str) -> CliCommandResult:
        command = ("gh", "api", f"repos/{repository}")
        result = self._run(command)
        payload: dict[str, object] | None = None
        if result.succeeded:
            payload = json.loads(result.stdout)
        return CliCommandResult(
            command=result.command,
            exit_code=result.exit_code,
            stdout=result.stdout,
            stderr=result.stderr,
            json_payload=payload,
        )

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

    def get_raw_project(
        self,
        repository: str,
        default_branch: str,
        project_path: str,
    ) -> CliCommandResult:
        encoded_path = quote(project_path)
        url = (
            f"https://raw.githubusercontent.com/{repository}/{default_branch}/"
            f"{encoded_path}"
        )
        command = ("GET", url)
        try:
            request = Request(url, headers={"Accept": "application/json"})
            with urlopen(request) as response:
                stdout = response.read().decode("utf-8")
            payload = json.loads(stdout)
            return CliCommandResult(
                command=command,
                exit_code=0,
                stdout=stdout,
                stderr="",
                json_payload=payload,
            )
        except Exception as error:
            return CliCommandResult(
                command=command,
                exit_code=1,
                stdout="",
                stderr=str(error),
            )

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
