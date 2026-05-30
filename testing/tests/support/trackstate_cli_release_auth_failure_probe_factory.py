from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.trackstate_cli_release_auth_failure_probe import (
    TrackStateCliReleaseAuthFailureProbe,
)
from testing.frameworks.python.trackstate_cli_release_auth_failure_framework import (
    PythonTrackStateCliReleaseAuthFailureFramework,
)


def create_trackstate_cli_release_auth_failure_probe(
    repository_root: Path,
) -> TrackStateCliReleaseAuthFailureProbe:
    return PythonTrackStateCliReleaseAuthFailureFramework(repository_root)
