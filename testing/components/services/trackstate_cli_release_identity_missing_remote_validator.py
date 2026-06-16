from __future__ import annotations

from testing.core.config.trackstate_cli_release_identity_missing_remote_config import (
    TrackStateCliReleaseIdentityMissingRemoteConfig,
)
from testing.core.interfaces.trackstate_cli_release_identity_missing_remote_probe import (
    TrackStateCliReleaseIdentityMissingRemoteProbe,
)
from testing.core.models.trackstate_cli_release_identity_missing_remote_result import (
    TrackStateCliReleaseIdentityMissingRemoteValidationResult,
)


class TrackStateCliReleaseIdentityMissingRemoteValidator:
    def __init__(
        self,
        probe: TrackStateCliReleaseIdentityMissingRemoteProbe,
    ) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateCliReleaseIdentityMissingRemoteConfig,
    ) -> TrackStateCliReleaseIdentityMissingRemoteValidationResult:
        return self._probe.observe_release_identity_missing_remote(config=config)
