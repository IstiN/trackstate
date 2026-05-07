from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
from typing import Any, Mapping, Sequence

from testing.core.interfaces.github_api_client import (
    GitHubApiClient,
    GitHubApiClientError,
)


class GhCliApiClient(GitHubApiClient):
    def __init__(self, repository_root: Path) -> None:
        self._repository_root = Path(repository_root)

    def request_text(
        self,
        *,
        endpoint: str,
        method: str = "GET",
        field_args: Sequence[str] | None = None,
        stdin_json: Mapping[str, Any] | None = None,
    ) -> str:
        command = ["gh", "api", "-X", method, endpoint]
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
            raise GitHubApiClientError(
                f"gh api {' '.join(command[2:])} failed with exit code "
                f"{completed.returncode}.\nSTDOUT:\n{completed.stdout}\nSTDERR:\n"
                f"{completed.stderr}"
            )
        return completed.stdout
