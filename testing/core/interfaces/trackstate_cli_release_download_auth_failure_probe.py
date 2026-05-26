from __future__ import annotations

from typing import Protocol

from testing.core.config.trackstate_cli_release_download_auth_failure_config import (
    TrackStateCliReleaseDownloadAuthFailureConfig,
)
from testing.core.models.trackstate_cli_release_download_auth_failure_result import (
    TrackStateCliReleaseDownloadAuthFailureValidationResult,
)


class TrackStateCliReleaseDownloadAuthFailureProbe(Protocol):
    def observe_release_download_auth_failure(
        self,
        *,
        config: TrackStateCliReleaseDownloadAuthFailureConfig,
    ) -> TrackStateCliReleaseDownloadAuthFailureValidationResult: ...
