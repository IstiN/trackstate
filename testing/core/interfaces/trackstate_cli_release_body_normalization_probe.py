from __future__ import annotations

from typing import Protocol

from testing.core.config.trackstate_cli_release_body_normalization_config import (
    TrackStateCliReleaseBodyNormalizationConfig,
)
from testing.core.models.trackstate_cli_release_body_normalization_result import (
    TrackStateCliReleaseBodyNormalizationValidationResult,
)


class TrackStateCliReleaseBodyNormalizationProbe(Protocol):
    def observe_release_body_normalization(
        self,
        *,
        config: TrackStateCliReleaseBodyNormalizationConfig,
    ) -> TrackStateCliReleaseBodyNormalizationValidationResult: ...
