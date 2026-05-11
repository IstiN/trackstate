from __future__ import annotations

from testing.core.config.trackstate_cli_read_alias_config import (
    TrackStateCliReadAliasConfig,
)
from testing.core.interfaces.trackstate_cli_read_alias_probe import (
    TrackStateCliReadAliasProbe,
)
from testing.core.models.trackstate_cli_read_alias_result import (
    TrackStateCliReadAliasValidationResult,
)


class TrackStateCliReadAliasValidator:
    def __init__(self, probe: TrackStateCliReadAliasProbe) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateCliReadAliasConfig,
    ) -> TrackStateCliReadAliasValidationResult:
        return self._probe.observe_read_alias_responses(config=config)
