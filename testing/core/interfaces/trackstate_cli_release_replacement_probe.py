from __future__ import annotations

from typing import Protocol

from testing.core.config.trackstate_cli_release_replacement_config import (
    TrackStateCliReleaseReplacementConfig,
)
from testing.core.models.trackstate_cli_release_replacement_result import (
    TrackStateCliReleaseReplacementValidationResult,
)


class TrackStateCliReleaseReplacementProbe(Protocol):
    def observe_release_replacement(
        self,
        *,
        config: TrackStateCliReleaseReplacementConfig,
    ) -> TrackStateCliReleaseReplacementValidationResult: ...
