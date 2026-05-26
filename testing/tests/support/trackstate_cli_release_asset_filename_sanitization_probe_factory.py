from __future__ import annotations

from pathlib import Path

from testing.components.services.live_setup_repository_service import (
    LiveSetupRepositoryService,
)
from testing.core.interfaces.trackstate_cli_release_asset_filename_sanitization_probe import (
    TrackStateCliReleaseAssetFilenameSanitizationProbe,
)
from testing.frameworks.python.trackstate_cli_release_asset_filename_sanitization_framework import (
    PythonTrackStateCliReleaseAssetFilenameSanitizationFramework,
)


def create_trackstate_cli_release_asset_filename_sanitization_probe(
    repository_root: Path,
) -> TrackStateCliReleaseAssetFilenameSanitizationProbe:
    return PythonTrackStateCliReleaseAssetFilenameSanitizationFramework(
        repository_root,
        LiveSetupRepositoryService(),
    )
