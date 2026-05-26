from __future__ import annotations

from typing import Protocol

from testing.core.config.trackstate_cli_field_resolution_config import (
    TrackStateCliFieldResolutionConfig,
)
from testing.core.models.trackstate_cli_field_resolution_result import (
    TrackStateCliFieldResolutionObservation,
)


class TrackStateCliFieldResolutionProbe(Protocol):
    def observe_field_resolution(
        self,
        *,
        config: TrackStateCliFieldResolutionConfig,
    ) -> TrackStateCliFieldResolutionObservation: ...
