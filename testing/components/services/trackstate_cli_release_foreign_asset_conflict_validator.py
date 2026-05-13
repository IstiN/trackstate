from __future__ import annotations

from testing.core.config.trackstate_cli_release_foreign_asset_conflict_config import (
    TrackStateCliReleaseForeignAssetConflictConfig,
)
from testing.core.interfaces.trackstate_cli_release_foreign_asset_conflict_probe import (
    TrackStateCliReleaseForeignAssetConflictProbe,
)
from testing.core.models.trackstate_cli_release_foreign_asset_conflict_result import (
    TrackStateCliReleaseForeignAssetConflictValidationResult,
)


class TrackStateCliReleaseForeignAssetConflictValidator:
    def __init__(
        self,
        probe: TrackStateCliReleaseForeignAssetConflictProbe,
    ) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateCliReleaseForeignAssetConflictConfig,
    ) -> TrackStateCliReleaseForeignAssetConflictValidationResult:
        return self._probe.observe_release_foreign_asset_conflict(config=config)
