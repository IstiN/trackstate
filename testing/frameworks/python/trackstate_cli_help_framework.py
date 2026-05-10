from __future__ import annotations

from pathlib import Path
import os
import shutil
import subprocess

from testing.core.interfaces.trackstate_cli_help_probe import TrackStateCliHelpProbe
from testing.core.models.cli_command_result import CliCommandResult
from testing.core.models.trackstate_cli_help_result import TrackStateCliHelpObservation


class PythonTrackStateCliHelpFramework(TrackStateCliHelpProbe):
    def __init__(self, repository_root: Path) -> None:
        self._repository_root = Path(repository_root)

    def root_help(self) -> TrackStateCliHelpObservation:
        return self._run_preferred_command(
            requested_command=("trackstate", "--help"),
            fallback_command=("dart", "run", "trackstate", "--help"),
        )

    def session_help(self) -> TrackStateCliHelpObservation:
        return self._run_preferred_command(
            requested_command=("trackstate", "session", "--help"),
            fallback_command=("dart", "run", "trackstate", "session", "--help"),
        )

    def _run_preferred_command(
        self,
        *,
        requested_command: tuple[str, ...],
        fallback_command: tuple[str, ...],
    ) -> TrackStateCliHelpObservation:
        preferred_binary = shutil.which(requested_command[0])
        if preferred_binary:
            executed_command = (preferred_binary, *requested_command[1:])
            return TrackStateCliHelpObservation(
                requested_command=requested_command,
                executed_command=executed_command,
                fallback_reason=None,
                result=self._run(executed_command),
            )

        configured_dart = os.environ.get("TRACKSTATE_DART_BIN")
        if configured_dart:
            fallback_command = (configured_dart, *fallback_command[1:])
        return TrackStateCliHelpObservation(
            requested_command=requested_command,
            executed_command=fallback_command,
            fallback_reason=(
                f'"{requested_command[0]}" was not available on PATH, so the test '
                'used the package executable via `dart run trackstate`.'
            ),
            result=self._run(fallback_command),
        )

    def _run(self, command: tuple[str, ...]) -> CliCommandResult:
        env = os.environ.copy()
        env.setdefault("CI", "true")
        env.setdefault("PUB_CACHE", str(Path.home() / ".pub-cache"))
        completed = subprocess.run(
            command,
            cwd=self._repository_root,
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
        )
