from __future__ import annotations

from typing import Protocol

from testing.core.config.trackstate_cli_release_identity_conflict_config import (
    TrackStateCliReleaseIdentityConflictConfig,
)
from testing.core.models.trackstate_cli_release_identity_conflict_result import (
    TrackStateCliReleaseIdentityConflictValidationResult,
)


class TrackStateCliReleaseIdentityConflictProbe(Protocol):
    def observe(
        self,
        *,
        config: TrackStateCliReleaseIdentityConflictConfig,
    ) -> TrackStateCliReleaseIdentityConflictValidationResult: ...
