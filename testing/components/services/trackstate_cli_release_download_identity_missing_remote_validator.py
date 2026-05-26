from __future__ import annotations

from testing.core.config.trackstate_cli_release_download_identity_missing_remote_config import (
    TrackStateCliReleaseDownloadIdentityMissingRemoteConfig,
)
from testing.core.interfaces.trackstate_cli_release_download_identity_missing_remote_probe import (
    TrackStateCliReleaseDownloadIdentityMissingRemoteProbe,
)
from testing.core.models.trackstate_cli_release_download_identity_missing_remote_result import (
    TrackStateCliReleaseDownloadIdentityMissingRemoteValidationResult,
)


class TrackStateCliReleaseDownloadIdentityMissingRemoteValidator:
    def __init__(
        self,
        probe: TrackStateCliReleaseDownloadIdentityMissingRemoteProbe,
    ) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateCliReleaseDownloadIdentityMissingRemoteConfig,
    ) -> TrackStateCliReleaseDownloadIdentityMissingRemoteValidationResult:
        return self._probe.observe_release_download_identity_missing_remote(
            config=config
        )
