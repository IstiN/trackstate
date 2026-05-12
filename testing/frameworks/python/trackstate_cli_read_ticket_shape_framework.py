from __future__ import annotations

import tempfile
from pathlib import Path

from testing.core.config.trackstate_cli_read_ticket_shape_config import (
    TrackStateCliReadTicketShapeConfig,
)
from testing.core.interfaces.trackstate_cli_read_ticket_shape_probe import (
    TrackStateCliReadTicketShapeProbe,
)
from testing.core.models.trackstate_cli_read_ticket_shape_result import (
    TrackStateCliReadTicketShapeValidationResult,
)
from testing.frameworks.python.trackstate_cli_read_alias_framework import (
    PythonTrackStateCliReadAliasFramework,
)


class PythonTrackStateCliReadTicketShapeFramework(
    PythonTrackStateCliReadAliasFramework,
    TrackStateCliReadTicketShapeProbe,
):
    def __init__(self, repository_root: Path) -> None:
        super().__init__(repository_root)

    def observe_read_ticket_shape(
        self,
        *,
        config: TrackStateCliReadTicketShapeConfig,
    ) -> TrackStateCliReadTicketShapeValidationResult:
        with tempfile.TemporaryDirectory(prefix="trackstate-ts-375-bin-") as bin_dir:
            executable_path = Path(bin_dir) / "trackstate"
            self._compile_executable(executable_path)
            with tempfile.TemporaryDirectory(
                prefix="trackstate-ts-375-repo-"
            ) as temp_dir:
                repository_path = Path(temp_dir)
                self._seed_local_repository(repository_path, config=config)
                fallback_reason = (
                    "Pinned execution to a temporary executable compiled from this "
                    "checkout so TS-375 can run the canonical read ticket command "
                    "from a seeded disposable TrackState repository."
                )
                return TrackStateCliReadTicketShapeValidationResult(
                    observation=self._observe_command(
                        requested_command=config.requested_command,
                        repository_path=repository_path,
                        executable_path=executable_path,
                        fallback_reason=fallback_reason,
                    )
                )
