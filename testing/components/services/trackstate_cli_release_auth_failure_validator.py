from __future__ import annotations

from testing.core.config.trackstate_cli_release_auth_failure_config import (
    TrackStateCliReleaseAuthFailureConfig,
)
from testing.core.interfaces.trackstate_cli_release_auth_failure_probe import (
    TrackStateCliReleaseAuthFailureProbe,
)
from testing.core.models.trackstate_cli_release_auth_failure_result import (
    TrackStateCliReleaseAuthFailureValidationResult,
)


class TrackStateCliReleaseAuthFailureValidator:
    def __init__(
        self,
        probe: TrackStateCliReleaseAuthFailureProbe,
    ) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateCliReleaseAuthFailureConfig,
    ) -> TrackStateCliReleaseAuthFailureValidationResult:
        return self._probe.observe_release_auth_failure(config=config)
