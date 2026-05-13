from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess

from testing.core.interfaces.hosted_trackstate_session_cli_probe import (
    HostedTrackStateSessionCliProbe,
)
from testing.core.models.cli_command_result import CliCommandResult


class PythonHostedTrackStateSessionCliFramework(HostedTrackStateSessionCliProbe):
    def __init__(self, repository_root: Path) -> None:
        self._repository_root = Path(repository_root)

    def run_session(
        self,
        *,
        repository: str,
        branch: str = "main",
        provider: str = "github",
    ) -> CliCommandResult:
        executable = shutil.which("trackstate")
        if executable is None:
            raise AssertionError(
                "Precondition failed: TS-409 requires the installed `trackstate` CLI "
                "to be available on PATH for the hosted session parity check."
            )

        token = (
            os.environ.get("TRACKSTATE_TOKEN")
            or os.environ.get("GH_TOKEN")
            or os.environ.get("GITHUB_TOKEN")
        )
        env = os.environ.copy()
        env.setdefault("CI", "true")
        env.setdefault("PUB_CACHE", str(Path.home() / ".pub-cache"))
        if token:
            env.setdefault("TRACKSTATE_TOKEN", token)

        command = (
            executable,
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
