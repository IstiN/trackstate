from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.trackstate_cli_release_identity_missing_remote_probe import (
    TrackStateCliReleaseIdentityMissingRemoteProbe,
)
from testing.frameworks.python.trackstate_cli_release_identity_missing_remote_framework import (
    PythonTrackStateCliReleaseIdentityMissingRemoteFramework,
)


def create_trackstate_cli_release_identity_missing_remote_probe(
    repository_root: Path,
) -> TrackStateCliReleaseIdentityMissingRemoteProbe:
    return PythonTrackStateCliReleaseIdentityMissingRemoteFramework(repository_root)
