from __future__ import annotations

from testing.core.config.trackstate_cli_release_replacement_config import (
    TrackStateCliReleaseReplacementConfig,
)
from testing.core.interfaces.trackstate_cli_release_replacement_probe import (
    TrackStateCliReleaseReplacementProbe,
)
from testing.core.models.trackstate_cli_release_replacement_result import (
    TrackStateCliReleaseReplacementValidationResult,
)


class TrackStateCliReleaseReplacementValidator:
    def __init__(self, probe: TrackStateCliReleaseReplacementProbe) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateCliReleaseReplacementConfig,
    ) -> TrackStateCliReleaseReplacementValidationResult:
        return self._probe.observe_release_replacement(config=config)
