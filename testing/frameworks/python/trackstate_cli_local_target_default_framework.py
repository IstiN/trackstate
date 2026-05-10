from __future__ import annotations

import os
from pathlib import Path
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
            dart_bin = os.environ.get("TRACKSTATE_DART_BIN", "dart")
            executed_command = (
                dart_bin,
                str(self._repository_root / "bin" / "trackstate.dart"),
                *config.requested_command_prefix[1:],
            )
            return TrackStateCliSessionContractObservation(
                requested_command=config.requested_command_prefix,
                executed_command=executed_command,
                repository_path=str(repository_path),
                fallback_reason=(
                    "Pinned execution to the repository-local CLI entrypoint via "
                    "`dart <repo>/bin/trackstate.dart` so the probe can preserve the "
                    "seeded repository as the current working directory."
                ),
                result=self._run(executed_command, cwd=repository_path),
            )
