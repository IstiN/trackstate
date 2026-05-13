from __future__ import annotations

from testing.core.interfaces.hosted_trackstate_session_cli_probe import (
    HostedTrackStateSessionCliProbe,
)
from testing.core.models.cli_command_result import CliCommandResult


class HostedTrackStateSessionCliService:
    def __init__(self, probe: HostedTrackStateSessionCliProbe) -> None:
        self._probe = probe

    def run_session(
        self,
        *,
        repository: str,
        branch: str = "main",
        provider: str = "github",
    ) -> CliCommandResult:
        return self._probe.run_session(
            repository=repository,
            branch=branch,
            provider=provider,
        )
