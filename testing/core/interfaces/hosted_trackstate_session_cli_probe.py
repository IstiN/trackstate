from __future__ import annotations

from typing import Protocol

from testing.core.models.cli_command_result import CliCommandResult


class HostedTrackStateSessionCliProbe(Protocol):
    def run_session(
        self,
        *,
        repository: str,
        branch: str = "main",
        provider: str = "github",
    ) -> CliCommandResult: ...
