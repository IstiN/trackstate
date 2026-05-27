from __future__ import annotations

from typing import Protocol

from testing.core.config.trackstate_cli_invalid_link_type_config import (
    TrackStateCliInvalidLinkTypeConfig,
)
from testing.core.models.trackstate_cli_invalid_link_type_result import (
    TrackStateCliInvalidLinkTypeValidationResult,
)


class TrackStateCliInvalidLinkTypeProbe(Protocol):
    def observe_invalid_link_type_response(
        self,
        *,
        config: TrackStateCliInvalidLinkTypeConfig,
    ) -> TrackStateCliInvalidLinkTypeValidationResult: ...
