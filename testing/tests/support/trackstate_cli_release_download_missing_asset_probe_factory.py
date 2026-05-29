from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.trackstate_cli_release_download_missing_asset_probe import (
    TrackStateCliReleaseDownloadMissingAssetProbe,
)
from testing.frameworks.python.trackstate_cli_release_download_missing_asset_framework import (
    PythonTrackStateCliReleaseDownloadMissingAssetFramework,
)


def create_trackstate_cli_release_download_missing_asset_probe(
    repository_root: Path,
) -> TrackStateCliReleaseDownloadMissingAssetProbe:
    return PythonTrackStateCliReleaseDownloadMissingAssetFramework(repository_root)
