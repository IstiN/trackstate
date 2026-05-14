from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.trackstate_release_artifact_probe import (
    TrackStateReleaseArtifactProbe,
)
from testing.frameworks.python.trackstate_release_artifact_framework import (
    PythonTrackStateReleaseArtifactFramework,
)


def create_trackstate_release_artifact_probe(
    repository_root: Path,
) -> TrackStateReleaseArtifactProbe:
    return PythonTrackStateReleaseArtifactFramework(repository_root)
