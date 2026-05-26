from __future__ import annotations

from typing import Protocol

from testing.core.config.trackstate_cli_release_auth_failure_config import (
    TrackStateCliReleaseAuthFailureConfig,
)
from testing.core.models.trackstate_cli_release_auth_failure_result import (
    TrackStateCliReleaseAuthFailureValidationResult,
)


class TrackStateCliReleaseAuthFailureProbe(Protocol):
    def observe_release_auth_failure(
        self,
        *,
        config: TrackStateCliReleaseAuthFailureConfig,
    ) -> TrackStateCliReleaseAuthFailureValidationResult: ...
