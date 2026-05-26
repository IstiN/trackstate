from __future__ import annotations

from typing import Protocol

from testing.core.config.trackstate_cli_fallback_boundaries_config import (
    TrackStateCliFallbackBoundariesConfig,
)
from testing.core.models.trackstate_cli_fallback_boundaries_result import (
    TrackStateCliFallbackBoundariesValidationResult,
)


class TrackStateCliFallbackBoundariesProbe(Protocol):
    def observe_rejections(
        self,
        *,
        config: TrackStateCliFallbackBoundariesConfig,
    ) -> TrackStateCliFallbackBoundariesValidationResult: ...
