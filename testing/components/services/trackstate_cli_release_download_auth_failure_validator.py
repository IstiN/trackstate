from __future__ import annotations

from testing.core.config.trackstate_cli_release_download_auth_failure_config import (
    TrackStateCliReleaseDownloadAuthFailureConfig,
)
from testing.core.interfaces.trackstate_cli_release_download_auth_failure_probe import (
    TrackStateCliReleaseDownloadAuthFailureProbe,
)
from testing.core.models.trackstate_cli_release_download_auth_failure_result import (
    TrackStateCliReleaseDownloadAuthFailureValidationResult,
)


class TrackStateCliReleaseDownloadAuthFailureValidator:
    def __init__(
        self,
        probe: TrackStateCliReleaseDownloadAuthFailureProbe,
    ) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateCliReleaseDownloadAuthFailureConfig,
    ) -> TrackStateCliReleaseDownloadAuthFailureValidationResult:
        return self._probe.observe_release_download_auth_failure(config=config)
