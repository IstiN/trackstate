from __future__ import annotations

from typing import Protocol

from testing.core.config.trackstate_cli_release_identity_missing_remote_config import (
    TrackStateCliReleaseIdentityMissingRemoteConfig,
)
from testing.core.models.trackstate_cli_release_identity_missing_remote_result import (
    TrackStateCliReleaseIdentityMissingRemoteValidationResult,
)


class TrackStateCliReleaseIdentityMissingRemoteProbe(Protocol):
    def observe_release_identity_missing_remote(
        self,
        *,
        config: TrackStateCliReleaseIdentityMissingRemoteConfig,
    ) -> TrackStateCliReleaseIdentityMissingRemoteValidationResult: ...
