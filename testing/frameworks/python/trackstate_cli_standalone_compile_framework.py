from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from testing.core.config.trackstate_cli_standalone_compile_config import (
    TrackStateCliStandaloneCompileConfig,
)
from testing.core.interfaces.trackstate_cli_standalone_compile_probe import (
    TrackStateCliStandaloneCompileProbe,
)
from testing.core.models.cli_command_result import CliCommandResult
from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)
from testing.core.models.trackstate_cli_standalone_compile_result import (
    TrackStateCliStandaloneCompileValidationResult,
)


class PythonTrackStateCliStandaloneCompileFramework(
    TrackStateCliStandaloneCompileProbe
):
    def __init__(self, repository_root: Path) -> None:
        self._repository_root = Path(repository_root)

    def observe_standalone_compile(
        self,
        *,
        config: TrackStateCliStandaloneCompileConfig,
    ) -> TrackStateCliStandaloneCompileValidationResult:
        requested_command = config.requested_command
        if len(requested_command) < 6:
            raise ValueError(
                "Standalone compile config requested_command must contain the full "
                "compiler invocation including the output path."
            )

        entrypoint = self._repository_root / config.source_entrypoint
        if not entrypoint.is_file():
            raise AssertionError(
                "Precondition failed: the standalone CLI entrypoint does not exist.\n"
                f"Expected path: {entrypoint}"
            )

        dart_bin = os.environ.get("TRACKSTATE_DART_BIN", requested_command[0])
        dart_version = self._dart_version(dart_bin)
        env = os.environ.copy()
        env.setdefault("CI", "true")
        env.setdefault("PUB_CACHE", str(Path.home() / ".pub-cache"))

        with tempfile.TemporaryDirectory(prefix="trackstate-ts-596-bin-") as temp_dir:
            output_path = Path(temp_dir) / config.output_file_name
            executed_command = (
                dart_bin,
                *requested_command[1:-1],
                str(output_path),
            )
            completed = subprocess.run(
                executed_command,
                cwd=self._repository_root,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            observation = TrackStateCliCommandObservation(
                requested_command=requested_command,
                executed_command=executed_command,
                fallback_reason=(
                    "Redirected the compiler output path to a temporary executable so "
                    "TS-596 exercises the exact standalone Dart compile flow without "
                    "writing build artifacts into the repository checkout."
                ),
                repository_path=str(self._repository_root),
                compiled_binary_path=str(output_path),
                result=CliCommandResult(
                    command=executed_command,
                    exit_code=completed.returncode,
                    stdout=completed.stdout,
                    stderr=completed.stderr,
                ),
            )
            output_exists = output_path.is_file()
            output_size_bytes = output_path.stat().st_size if output_exists else None
            output_is_executable = os.access(output_path, os.X_OK) if output_exists else False
            return TrackStateCliStandaloneCompileValidationResult(
                observation=observation,
                dart_version=dart_version,
                output_exists=output_exists,
                output_size_bytes=output_size_bytes,
                output_is_executable=output_is_executable,
            )

    @staticmethod
    def _dart_version(dart_bin: str) -> str:
        completed = subprocess.run(
            (dart_bin, "--version"),
            capture_output=True,
            text=True,
            check=False,
        )
        version_text = "\n".join(
            fragment.strip()
            for fragment in (completed.stdout, completed.stderr)
            if fragment.strip()
        ).strip()
        return version_text or "<unknown>"
