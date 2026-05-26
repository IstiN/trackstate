from __future__ import annotations

from pathlib import Path

from testing.components.services.live_setup_repository_service import (
    LiveSetupRepositoryService,
)
from testing.core.interfaces.trackstate_cli_release_body_normalization_probe import (
    TrackStateCliReleaseBodyNormalizationProbe,
)
from testing.frameworks.python.trackstate_cli_release_body_normalization_framework import (
    PythonTrackStateCliReleaseBodyNormalizationFramework,
)


def create_trackstate_cli_release_body_normalization_probe(
    repository_root: Path,
    service: LiveSetupRepositoryService,
) -> TrackStateCliReleaseBodyNormalizationProbe:
    return PythonTrackStateCliReleaseBodyNormalizationFramework(
        repository_root,
        service,
    )
