from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.trackstate_cli_release_download_identity_missing_remote_probe import (
    TrackStateCliReleaseDownloadIdentityMissingRemoteProbe,
)
from testing.frameworks.python.trackstate_cli_release_download_identity_missing_remote_framework import (
    PythonTrackStateCliReleaseDownloadIdentityMissingRemoteFramework,
)


def create_trackstate_cli_release_download_identity_missing_remote_probe(
    repository_root: Path,
) -> TrackStateCliReleaseDownloadIdentityMissingRemoteProbe:
    return PythonTrackStateCliReleaseDownloadIdentityMissingRemoteFramework(
        repository_root
    )
