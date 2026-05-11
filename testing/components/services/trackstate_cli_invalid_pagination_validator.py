from __future__ import annotations

from testing.core.config.trackstate_cli_invalid_pagination_config import (
    TrackStateCliInvalidPaginationConfig,
)
from testing.core.interfaces.trackstate_cli_invalid_pagination_probe import (
    TrackStateCliInvalidPaginationProbe,
)
from testing.core.models.trackstate_cli_invalid_pagination_result import (
    TrackStateCliInvalidPaginationValidationResult,
)


class TrackStateCliInvalidPaginationValidator:
    def __init__(self, probe: TrackStateCliInvalidPaginationProbe) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateCliInvalidPaginationConfig,
    ) -> TrackStateCliInvalidPaginationValidationResult:
        return self._probe.observe_invalid_pagination_responses(config=config)
