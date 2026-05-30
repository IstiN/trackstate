from __future__ import annotations

from pathlib import Path

from testing.components.services.live_setup_repository_service import (
    LiveSetupRepositoryService,
)
from testing.core.interfaces.trackstate_cli_release_foreign_asset_conflict_probe import (
    TrackStateCliReleaseForeignAssetConflictProbe,
)
from testing.frameworks.python.trackstate_cli_release_foreign_asset_conflict_framework import (
    PythonTrackStateCliReleaseForeignAssetConflictFramework,
)


def create_trackstate_cli_release_foreign_asset_conflict_probe(
    repository_root: Path,
) -> TrackStateCliReleaseForeignAssetConflictProbe:
    return PythonTrackStateCliReleaseForeignAssetConflictFramework(
        repository_root,
        LiveSetupRepositoryService(),
    )
