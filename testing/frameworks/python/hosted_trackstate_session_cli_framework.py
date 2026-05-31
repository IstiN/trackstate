from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from testing.core.interfaces.hosted_trackstate_session_cli_probe import (
    HostedTrackStateSessionCliProbe,
)
from testing.core.models.cli_command_result import CliCommandResult
from testing.frameworks.python.trackstate_cli_compiled_local_framework import (
    PythonTrackStateCliCompiledLocalFramework,
)


class PythonHostedTrackStateSessionCliFramework(
    PythonTrackStateCliCompiledLocalFramework,
    HostedTrackStateSessionCliProbe,
):
    def __init__(self, repository_root: Path) -> None:
        super().__init__(repository_root)

    def run_session(
        self,
        *,
        repository: str,
        branch: str = "main",
        provider: str = "github",
    ) -> CliCommandResult:
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

        command_suffix = (
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
        resolved_command = self._resolve_command()
        if resolved_command is not None:
            completed = subprocess.run(
                resolved_command + command_suffix,
                cwd=self._repository_root,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
        else:
            with tempfile.TemporaryDirectory(prefix="trackstate-hosted-cli-") as bin_dir:
                executable_path = Path(bin_dir) / "trackstate"
                self._compile_executable(executable_path)
                completed = subprocess.run(
                    (str(executable_path),) + command_suffix,
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
            command=tuple(completed.args),
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            json_payload=payload,
        )

    def _resolve_command(self) -> tuple[str, ...] | None:
        executable = shutil.which("trackstate")
        if executable is not None:
            return (executable,)
        return None
