from __future__ import annotations

from testing.core.config.trackstate_cli_release_identity_multiple_remotes_config import (
    TrackStateCliReleaseIdentityMultipleRemotesConfig,
)
from testing.core.interfaces.trackstate_cli_release_identity_multiple_remotes_probe import (
    TrackStateCliReleaseIdentityMultipleRemotesProbe,
)
from testing.core.models.trackstate_cli_release_identity_multiple_remotes_result import (
    TrackStateCliReleaseIdentityMultipleRemotesValidationResult,
)


class TrackStateCliReleaseIdentityMultipleRemotesValidator:
    def __init__(
        self,
        probe: TrackStateCliReleaseIdentityMultipleRemotesProbe,
    ) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateCliReleaseIdentityMultipleRemotesConfig,
    ) -> TrackStateCliReleaseIdentityMultipleRemotesValidationResult:
        return self._probe.observe_release_identity_multiple_remotes(config=config)
