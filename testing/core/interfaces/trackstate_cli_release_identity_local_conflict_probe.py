from __future__ import annotations

from typing import Protocol

from testing.core.config.trackstate_cli_release_identity_local_conflict_config import (
    TrackStateCliReleaseIdentityLocalConflictConfig,
)
from testing.core.models.trackstate_cli_release_identity_local_conflict_result import (
    TrackStateCliReleaseIdentityLocalConflictValidationResult,
)


class TrackStateCliReleaseIdentityLocalConflictProbe(Protocol):
    def observe(
        self,
        *,
        config: TrackStateCliReleaseIdentityLocalConflictConfig,
    ) -> TrackStateCliReleaseIdentityLocalConflictValidationResult: ...
