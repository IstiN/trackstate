from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.trackstate_cli_release_download_success_probe import (
    TrackStateCliReleaseDownloadSuccessProbe,
)
from testing.frameworks.python.trackstate_cli_release_download_success_framework import (
    PythonTrackStateCliReleaseDownloadSuccessFramework,
)


def create_trackstate_cli_release_download_success_probe(
    repository_root: Path,
) -> TrackStateCliReleaseDownloadSuccessProbe:
    return PythonTrackStateCliReleaseDownloadSuccessFramework(repository_root)
