from __future__ import annotations

from testing.core.config.trackstate_cli_field_resolution_config import (
    TrackStateCliFieldResolutionConfig,
)
from testing.core.interfaces.trackstate_cli_field_resolution_probe import (
    TrackStateCliFieldResolutionProbe,
)
from testing.core.models.trackstate_cli_field_resolution_result import (
    TrackStateCliFieldResolutionValidationResult,
)


class TrackStateCliFieldResolutionValidator:
    def __init__(self, probe: TrackStateCliFieldResolutionProbe) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateCliFieldResolutionConfig,
    ) -> TrackStateCliFieldResolutionValidationResult:
        return TrackStateCliFieldResolutionValidationResult(
            observation=self._probe.observe_field_resolution(config=config)
        )
