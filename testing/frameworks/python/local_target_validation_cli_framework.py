from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from testing.core.config.local_target_validation_cli_config import (
    LocalTargetValidationCliConfig,
)
from testing.core.interfaces.local_target_validation_cli_probe import (
    LocalTargetValidationCliProbe,
)
from testing.core.models.cli_command_result import CliCommandResult
from testing.core.models.local_target_validation_cli_result import (
    LocalTargetValidationCliObservation,
)


class PythonLocalTargetValidationCliFramework(LocalTargetValidationCliProbe):
    def __init__(self, repository_root: Path) -> None:
        self._repository_root = Path(repository_root)

    def invalid_local_repository(
        self,
        *,
        config: LocalTargetValidationCliConfig,
    ) -> LocalTargetValidationCliObservation:
        preferred_binary = shutil.which(config.requested_command[0])
        with tempfile.TemporaryDirectory(prefix="trackstate-ts-270-") as temp_dir:
            working_directory = Path(temp_dir)
            if preferred_binary:
                executed_command = (preferred_binary, *config.requested_command[1:])
                return LocalTargetValidationCliObservation(
                    requested_command=config.requested_command,
                    executed_command=executed_command,
                    fallback_reason=None,
                    working_directory=str(working_directory),
                    compiled_binary_path=None,
                    result=self._run(executed_command, cwd=working_directory),
                )

            with tempfile.TemporaryDirectory(prefix="trackstate-ts-270-bin-") as bin_dir:
                executable_path = Path(bin_dir) / "trackstate"
                self._compile_executable(executable_path)
                executed_command = (
                    str(executable_path),
                    *config.requested_command[1:],
                )
                return LocalTargetValidationCliObservation(
                    requested_command=config.requested_command,
                    executed_command=executed_command,
                    fallback_reason=(
                        '"trackstate" was not available on PATH, so the probe compiled '
                        "a temporary repository-local executable to reproduce the "
                        "standalone invocation from a non-repository working directory."
                    ),
                    working_directory=str(working_directory),
                    compiled_binary_path=str(executable_path),
                    result=self._run(executed_command, cwd=working_directory),
                )

    def _compile_executable(self, destination: Path) -> None:
        dart_bin = os.environ.get("TRACKSTATE_DART_BIN", "dart")
        env = os.environ.copy()
        env.setdefault("CI", "true")
        env.setdefault("PUB_CACHE", str(Path.home() / ".pub-cache"))
        completed = subprocess.run(
            (
                dart_bin,
                "compile",
                "exe",
                "bin/trackstate.dart",
                "-o",
                str(destination),
            ),
            cwd=self._repository_root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise AssertionError(
                "Failed to compile a temporary TrackState CLI executable for TS-270.\n"
                f"Command: {dart_bin} compile exe bin/trackstate.dart -o {destination}\n"
                f"Exit code: {completed.returncode}\n"
                f"stdout:\n{completed.stdout}\n"
                f"stderr:\n{completed.stderr}"
            )

    def _run(self, command: tuple[str, ...], *, cwd: Path) -> CliCommandResult:
        env = os.environ.copy()
        env.setdefault("CI", "true")
        env.setdefault("PUB_CACHE", str(Path.home() / ".pub-cache"))
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        return CliCommandResult(
            command=command,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            json_payload=self._parse_json(completed.stdout),
        )

    @staticmethod
    def _parse_json(stdout: str) -> object | None:
        payload = stdout.strip()
        if not payload:
            return None
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            return None
