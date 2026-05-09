from __future__ import annotations

import json
from pathlib import Path
import shlex
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

    def run_documented_command(self, command: str) -> CliCommandResult:
        try:
            parsed_command = tuple(shlex.split(command))
        except ValueError as error:
            return CliCommandResult(
                command=(command,),
                exit_code=1,
                stdout="",
                stderr=f"Could not parse documented CLI command: {error}",
            )
        if not parsed_command:
            return CliCommandResult(
                command=(command,),
                exit_code=1,
                stdout="",
                stderr="README quick-start command was empty.",
            )
        if parsed_command[0] != "gh":
            return CliCommandResult(
                command=parsed_command,
                exit_code=1,
                stdout="",
                stderr=(
                    "README quick-start command must invoke GitHub CLI (`gh`) so "
                    "the automation can execute it safely."
                ),
            )
        if any(self._contains_shell_metacharacters(token) for token in parsed_command):
            return CliCommandResult(
                command=parsed_command,
                exit_code=1,
                stdout="",
                stderr=(
                    "README quick-start command contains shell metacharacters. "
                    "Document a direct `gh ...` command instead of a shell pipeline."
                ),
            )
        return self._run(parsed_command)

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

    def get_contents(
        self,
        repository: str,
        ref: str,
        path: str,
    ) -> CliCommandResult:
        endpoint = f"repos/{repository}/contents/{path}?ref={ref}"
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
        return self.get_contents(repository, default_branch, project_path)

    def get_raw_file(
        self,
        repository: str,
        ref: str,
        path: str,
    ) -> CliCommandResult:
        encoded_path = quote(path)
        url = (
            f"https://raw.githubusercontent.com/{repository}/{ref}/"
            f"{encoded_path}"
        )
        command = ("GET", url)
        try:
            request = Request(url, headers={"Accept": "application/json"})
            with urlopen(request) as response:
                stdout = response.read().decode("utf-8")
            payload: object | None = None
            try:
                payload = json.loads(stdout)
            except json.JSONDecodeError:
                payload = None
            return CliCommandResult(
                command=command,
                exit_code=0,
                stdout=stdout,
                stderr="",
                json_payload=payload,
            )
        except (HTTPError, URLError) as error:
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

    def _contains_shell_metacharacters(self, token: str) -> bool:
        shell_metacharacters = ("|", "&&", ";", "`", "$(", ">", "<")
        return any(metacharacter in token for metacharacter in shell_metacharacters)
