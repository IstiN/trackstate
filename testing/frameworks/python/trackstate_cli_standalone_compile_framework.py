from __future__ import annotations

import os
import shutil
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
        output_path = self._repository_root / requested_command[-1]
        backup_path = self._backup_preexisting_output(output_path)
        try:
            executed_command = (
                dart_bin,
                *requested_command[1:-1],
                requested_command[-1],
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
                fallback_reason=None,
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
                preexisting_output_backup_path=(
                    str(backup_path) if backup_path is not None else None
                ),
            )
        except Exception:
            self.restore_output_path(
                output_path=output_path,
                backup_path=backup_path,
            )
            raise

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

    @staticmethod
    def _backup_preexisting_output(output_path: Path) -> Path | None:
        if not output_path.exists():
            return None
        backup_dir = Path(tempfile.mkdtemp(prefix="trackstate-ts-596-backup-"))
        backup_path = backup_dir / output_path.name
        shutil.move(str(output_path), str(backup_path))
        return backup_path

    @staticmethod
    def restore_output_path(*, output_path: Path, backup_path: Path | None) -> None:
        if output_path.is_symlink() or output_path.is_file():
            output_path.unlink()
        elif output_path.is_dir():
            shutil.rmtree(output_path)

        if backup_path is None:
            return

        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(backup_path), str(output_path))
        backup_dir = backup_path.parent
        if backup_dir.exists():
            backup_dir.rmdir()
