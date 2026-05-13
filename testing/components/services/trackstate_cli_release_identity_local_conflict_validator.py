from __future__ import annotations

from testing.core.config.trackstate_cli_release_identity_local_conflict_config import (
    TrackStateCliReleaseIdentityLocalConflictConfig,
)
from testing.core.interfaces.trackstate_cli_release_identity_local_conflict_probe import (
    TrackStateCliReleaseIdentityLocalConflictProbe,
)
from testing.core.models.trackstate_cli_release_identity_local_conflict_result import (
    TrackStateCliReleaseIdentityLocalConflictValidationResult,
)


class TrackStateCliReleaseIdentityLocalConflictValidator:
    def __init__(
        self,
        probe: TrackStateCliReleaseIdentityLocalConflictProbe,
    ) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateCliReleaseIdentityLocalConflictConfig,
    ) -> TrackStateCliReleaseIdentityLocalConflictValidationResult:
        return self._probe.observe(config=config)
