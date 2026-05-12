from __future__ import annotations

from testing.core.config.trackstate_cli_fallback_boundaries_config import (
    TrackStateCliFallbackBoundariesConfig,
)
from testing.core.interfaces.trackstate_cli_fallback_boundaries_probe import (
    TrackStateCliFallbackBoundariesProbe,
)
from testing.core.models.trackstate_cli_fallback_boundaries_result import (
    TrackStateCliFallbackBoundariesValidationResult,
)


class TrackStateCliFallbackBoundariesValidator:
    def __init__(self, probe: TrackStateCliFallbackBoundariesProbe) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateCliFallbackBoundariesConfig,
    ) -> TrackStateCliFallbackBoundariesValidationResult:
        return self._probe.observe_rejections(config=config)
