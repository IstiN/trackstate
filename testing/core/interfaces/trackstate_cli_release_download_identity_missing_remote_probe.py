from __future__ import annotations

from typing import Protocol

from testing.core.config.trackstate_cli_release_download_identity_missing_remote_config import (
    TrackStateCliReleaseDownloadIdentityMissingRemoteConfig,
)
from testing.core.models.trackstate_cli_release_download_identity_missing_remote_result import (
    TrackStateCliReleaseDownloadIdentityMissingRemoteValidationResult,
)


class TrackStateCliReleaseDownloadIdentityMissingRemoteProbe(Protocol):
    def observe_release_download_identity_missing_remote(
        self,
        *,
        config: TrackStateCliReleaseDownloadIdentityMissingRemoteConfig,
    ) -> TrackStateCliReleaseDownloadIdentityMissingRemoteValidationResult: ...
