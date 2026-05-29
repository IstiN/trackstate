from __future__ import annotations

from typing import Protocol

from testing.core.config.trackstate_cli_release_foreign_asset_conflict_config import (
    TrackStateCliReleaseForeignAssetConflictConfig,
)
from testing.core.models.trackstate_cli_release_foreign_asset_conflict_result import (
    TrackStateCliReleaseForeignAssetConflictValidationResult,
)


class TrackStateCliReleaseForeignAssetConflictProbe(Protocol):
    def observe_release_foreign_asset_conflict(
        self,
        *,
        config: TrackStateCliReleaseForeignAssetConflictConfig,
    ) -> TrackStateCliReleaseForeignAssetConflictValidationResult: ...
