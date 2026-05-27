from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile

from testing.core.config.trackstate_cli_session_contract_config import (
    TrackStateCliSessionContractConfig,
)
from testing.core.models.trackstate_cli_session_contract_result import (
    TrackStateCliSessionContractObservation,
)
from testing.frameworks.python.trackstate_cli_session_contract_framework import (
    PythonTrackStateCliSessionContractFramework,
)


class PythonTrackStateCliLocalTargetDefaultFramework(
    PythonTrackStateCliSessionContractFramework
):
    def observe_default_json_session(
        self,
        *,
        config: TrackStateCliSessionContractConfig,
    ) -> TrackStateCliSessionContractObservation:
        with tempfile.TemporaryDirectory(prefix="trackstate-ts-269-") as temp_dir:
            repository_path = Path(temp_dir)
            self._seed_local_repository(repository_path)
            with tempfile.TemporaryDirectory(prefix="trackstate-ts-269-bin-") as bin_dir:
                executable_path = Path(bin_dir) / "trackstate"
                self._compile_executable(executable_path)
                executed_command = (
                    str(executable_path),
                    *config.requested_command_prefix[1:],
                )
                return TrackStateCliSessionContractObservation(
                    requested_command=config.requested_command_prefix,
                    executed_command=executed_command,
                    repository_path=str(repository_path),
                    fallback_reason=(
                        "Pinned execution to a temporary executable compiled from this "
                        "checkout so the probe can preserve the seeded repository as "
                        "the current working directory without relying on an unrelated "
                        "`trackstate` binary from PATH."
                    ),
                    result=self._run(executed_command, cwd=repository_path),
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
                "Failed to compile a temporary TrackState CLI executable for TS-269.\n"
                f"Command: {dart_bin} compile exe bin/trackstate.dart -o {destination}\n"
                f"Exit code: {completed.returncode}\n"
                f"stdout:\n{completed.stdout}\n"
                f"stderr:\n{completed.stderr}"
            )
