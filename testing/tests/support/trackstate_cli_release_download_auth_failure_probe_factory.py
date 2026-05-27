from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.trackstate_cli_release_download_auth_failure_probe import (
    TrackStateCliReleaseDownloadAuthFailureProbe,
)
from testing.frameworks.python.trackstate_cli_release_download_auth_failure_framework import (
    PythonTrackStateCliReleaseDownloadAuthFailureFramework,
)


def create_trackstate_cli_release_download_auth_failure_probe(
    repository_root: Path,
) -> TrackStateCliReleaseDownloadAuthFailureProbe:
    return PythonTrackStateCliReleaseDownloadAuthFailureFramework(repository_root)
