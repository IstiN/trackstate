from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any, Mapping, Sequence

from testing.core.interfaces.github_api_client import (
    GitHubApiClient,
    GitHubApiClientError,
)


_HTTP_STATUS_PATTERN = re.compile(r"HTTP\s+(\d{3})")


class GhCliApiClient(GitHubApiClient):
    def __init__(self, repository_root: Path) -> None:
        self._repository_root = Path(repository_root)
        self._gh_executable = _resolve_gh_executable()

    def request_text(
        self,
        *,
        endpoint: str,
        method: str = "GET",
        field_args: Sequence[str] | None = None,
        stdin_json: Mapping[str, Any] | None = None,
    ) -> str:
        command = [self._gh_executable, "api", "-X", method, endpoint]
        if field_args:
            command.extend(field_args)

        input_text: str | None = None
        if stdin_json is not None:
            command.extend(["--input", "-"])
            input_text = json.dumps(dict(stdin_json))

        environment = os.environ.copy()
        environment.setdefault("GH_PAGER", "cat")
        completed = subprocess.run(
            command,
            cwd=self._repository_root,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
            input=input_text,
        )
        if completed.returncode != 0:
            message = (
                f"gh api {' '.join(command[2:])} failed with exit code "
                f"{completed.returncode}.\nSTDOUT:\n{completed.stdout}\nSTDERR:\n"
                f"{completed.stderr}"
            )
            raise GitHubApiClientError(message, status_code=_extract_status_code(completed.stderr))
        return completed.stdout


def _resolve_gh_executable() -> str:
    configured = os.environ.get("GH_CLI_PATH", "").strip()
    if configured:
        return configured
    path_candidate = shutil.which("gh")
    if path_candidate:
        return path_candidate
    homebrew_candidate = Path("/opt/homebrew/bin/gh")
    if homebrew_candidate.exists():
        return str(homebrew_candidate)
    return "gh"


def _extract_status_code(stderr: str) -> int | None:
    match = _HTTP_STATUS_PATTERN.search(stderr)
    if match:
        return int(match.group(1))
    return None
