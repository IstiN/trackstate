from __future__ import annotations

from testing.core.config.trackstate_cli_invalid_link_type_config import (
    TrackStateCliInvalidLinkTypeConfig,
)
from testing.core.interfaces.trackstate_cli_invalid_link_type_probe import (
    TrackStateCliInvalidLinkTypeProbe,
)
from testing.core.models.trackstate_cli_invalid_link_type_result import (
    TrackStateCliInvalidLinkTypeValidationResult,
)


class TrackStateCliInvalidLinkTypeValidator:
    def __init__(self, probe: TrackStateCliInvalidLinkTypeProbe) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateCliInvalidLinkTypeConfig,
    ) -> TrackStateCliInvalidLinkTypeValidationResult:
        return self._probe.observe_invalid_link_type_response(config=config)
