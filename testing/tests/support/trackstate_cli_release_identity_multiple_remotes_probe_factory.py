from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.trackstate_cli_release_identity_multiple_remotes_probe import (
    TrackStateCliReleaseIdentityMultipleRemotesProbe,
)
from testing.frameworks.python.trackstate_cli_release_identity_multiple_remotes_framework import (
    PythonTrackStateCliReleaseIdentityMultipleRemotesFramework,
)


def create_trackstate_cli_release_identity_multiple_remotes_probe(
    repository_root: Path,
) -> TrackStateCliReleaseIdentityMultipleRemotesProbe:
    return PythonTrackStateCliReleaseIdentityMultipleRemotesFramework(repository_root)
