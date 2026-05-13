from __future__ import annotations

from testing.core.config.trackstate_cli_release_body_normalization_config import (
    TrackStateCliReleaseBodyNormalizationConfig,
)
from testing.core.interfaces.trackstate_cli_release_body_normalization_probe import (
    TrackStateCliReleaseBodyNormalizationProbe,
)
from testing.core.models.trackstate_cli_release_body_normalization_result import (
    TrackStateCliReleaseBodyNormalizationValidationResult,
)


class TrackStateCliReleaseBodyNormalizationValidator:
    def __init__(
        self,
        probe: TrackStateCliReleaseBodyNormalizationProbe,
    ) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateCliReleaseBodyNormalizationConfig,
    ) -> TrackStateCliReleaseBodyNormalizationValidationResult:
        return self._probe.observe_release_body_normalization(config=config)
