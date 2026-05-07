from __future__ import annotations

import json
from pathlib import Path
import subprocess
from urllib.error import HTTPError, URLError
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

    def list_tree(
        self,
        repository: str,
        ref: str,
    ) -> CliCommandResult:
        command = ("gh", "api", f"repos/{repository}/git/trees/{ref}?recursive=1")
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

    def get_project(
        self,
        repository: str,
        default_branch: str,
        project_path: str,
    ) -> CliCommandResult:
        endpoint = f"repos/{repository}/contents/{project_path}?ref={default_branch}"
        command = ("gh", "api", endpoint)
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
        except (HTTPError, URLError, json.JSONDecodeError) as error:
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
