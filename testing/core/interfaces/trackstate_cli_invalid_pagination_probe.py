from __future__ import annotations

from typing import Protocol

from testing.core.config.trackstate_cli_invalid_pagination_config import (
    TrackStateCliInvalidPaginationConfig,
)
from testing.core.models.trackstate_cli_invalid_pagination_result import (
    TrackStateCliInvalidPaginationValidationResult,
)


class TrackStateCliInvalidPaginationProbe(Protocol):
    def observe_invalid_pagination_responses(
        self,
        *,
        config: TrackStateCliInvalidPaginationConfig,
    ) -> TrackStateCliInvalidPaginationValidationResult: ...
