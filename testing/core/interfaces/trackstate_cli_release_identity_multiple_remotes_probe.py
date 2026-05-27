from __future__ import annotations

from typing import Protocol

from testing.core.config.trackstate_cli_release_identity_multiple_remotes_config import (
    TrackStateCliReleaseIdentityMultipleRemotesConfig,
)
from testing.core.models.trackstate_cli_release_identity_multiple_remotes_result import (
    TrackStateCliReleaseIdentityMultipleRemotesValidationResult,
)


class TrackStateCliReleaseIdentityMultipleRemotesProbe(Protocol):
    def observe_release_identity_multiple_remotes(
        self,
        *,
        config: TrackStateCliReleaseIdentityMultipleRemotesConfig,
    ) -> TrackStateCliReleaseIdentityMultipleRemotesValidationResult: ...
