from __future__ import annotations

from testing.core.config.trackstate_cli_release_identity_conflict_config import (
    TrackStateCliReleaseIdentityConflictConfig,
)
from testing.core.interfaces.trackstate_cli_release_identity_conflict_probe import (
    TrackStateCliReleaseIdentityConflictProbe,
)
from testing.core.models.trackstate_cli_release_identity_conflict_result import (
    TrackStateCliReleaseIdentityConflictValidationResult,
)


class TrackStateCliReleaseIdentityConflictValidator:
    def __init__(
        self,
        probe: TrackStateCliReleaseIdentityConflictProbe,
    ) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateCliReleaseIdentityConflictConfig,
    ) -> TrackStateCliReleaseIdentityConflictValidationResult:
        return self._probe.observe(config=config)
