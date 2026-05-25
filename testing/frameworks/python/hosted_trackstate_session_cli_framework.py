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
        command_prefix = self._resolve_command_prefix()

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
            *command_prefix,
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

    def _resolve_command_prefix(self) -> tuple[str, ...]:
        executable = shutil.which("trackstate")
        if executable is not None:
            return (executable,)

        dart = shutil.which("dart")
        if dart is not None:
            return (dart, "run", "trackstate")

        flutter = shutil.which("flutter")
        if flutter is not None:
            return (flutter, "pub", "run", "trackstate")

        raise AssertionError(
            "Precondition failed: TS-409 requires either an installed `trackstate` "
            "CLI on PATH or a local Dart/Flutter toolchain that can run "
            "`trackstate` from this repository."
        )
