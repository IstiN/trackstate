from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess

from testing.core.models.cli_command_result import CliCommandResult


class HostedTrackStateSessionCliService:
    def __init__(self, repository_root: Path) -> None:
        self._repository_root = Path(repository_root)

    def run_session(
        self,
        *,
        repository: str,
        branch: str = "main",
        provider: str = "github",
    ) -> CliCommandResult:
        dart_bin = os.environ.get("TRACKSTATE_DART_BIN", "dart")
        token = os.environ.get("TRACKSTATE_TOKEN") or os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        env = os.environ.copy()
        env.setdefault("CI", "true")
        env.setdefault("PUB_CACHE", str(Path.home() / ".pub-cache"))
        if token:
            env.setdefault("TRACKSTATE_TOKEN", token)

        command = (
            dart_bin,
            "run",
            "trackstate",
            "session",
            "--target",
            "hosted",
            "--provider",
            provider,
            "--repository",
            repository,
            "--branch",
            branch,
        )
        completed = subprocess.run(
            command,
            cwd=self._repository_root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        payload = None
        stdout = completed.stdout.strip()
        if stdout:
            try:
                payload = json.loads(stdout)
            except json.JSONDecodeError:
                payload = None
        return CliCommandResult(
            command=command,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            json_payload=payload,
        )
