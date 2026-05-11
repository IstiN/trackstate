from __future__ import annotations

from pathlib import Path

from testing.core.config.trackstate_cli_help_config import TrackStateCliHelpConfig
from testing.core.interfaces.trackstate_cli_help_probe import TrackStateCliHelpProbe
from testing.core.models.trackstate_cli_help_result import (
    TrackStateCliHelpValidationResult,
)


class TrackStateCliHelpValidator:
    def __init__(self, repository_root: Path, probe: TrackStateCliHelpProbe) -> None:
        self._repository_root = Path(repository_root)
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateCliHelpConfig,
    ) -> TrackStateCliHelpValidationResult:
        return TrackStateCliHelpValidationResult(
            root_help=self._probe.root_help(),
            session_help=self._probe.session_help(),
        )
