from __future__ import annotations

import tempfile
from pathlib import Path

from testing.core.config.trackstate_cli_ticket_show_help_config import (
    TrackStateCliTicketShowHelpConfig,
)
from testing.core.interfaces.trackstate_cli_ticket_show_help_probe import (
    TrackStateCliTicketShowHelpProbe,
)
from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)
from testing.core.models.trackstate_cli_ticket_show_help_result import (
    TrackStateCliTicketShowHelpValidationResult,
)
from testing.frameworks.python.trackstate_cli_compiled_local_framework import (
    PythonTrackStateCliCompiledLocalFramework,
)


class PythonTrackStateCliTicketShowHelpFramework(
    PythonTrackStateCliCompiledLocalFramework,
    TrackStateCliTicketShowHelpProbe,
):
    def __init__(self, repository_root: Path) -> None:
        super().__init__(repository_root)

    def observe_ticket_help(
        self,
        *,
        config: TrackStateCliTicketShowHelpConfig,
    ) -> TrackStateCliTicketShowHelpValidationResult:
        with tempfile.TemporaryDirectory(prefix="trackstate-ts-671-bin-") as bin_dir:
            executable_path = Path(bin_dir) / "trackstate"
            self._compile_executable(executable_path)
            return TrackStateCliTicketShowHelpValidationResult(
                observation=self._observe_help_command(
                    requested_command=config.requested_command,
                    executable_path=executable_path,
                )
            )

    def _observe_help_command(
        self,
        *,
        requested_command: tuple[str, ...],
        executable_path: Path,
    ) -> TrackStateCliCommandObservation:
        executed_command = (str(executable_path), *requested_command[1:])
        return TrackStateCliCommandObservation(
            requested_command=requested_command,
            executed_command=executed_command,
            fallback_reason=(
                "Pinned execution to a temporary executable compiled from this "
                "checkout so TS-671 validates the visible compiled `trackstate "
                "ticket --help` surface."
            ),
            repository_path=str(self._repository_root),
            compiled_binary_path=str(executable_path),
            result=self._run(executed_command, cwd=self._repository_root),
        )
