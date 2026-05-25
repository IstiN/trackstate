from __future__ import annotations

from pathlib import Path

from testing.components.services.live_setup_repository_service import (
    LiveSetupRepositoryService,
)
from testing.core.interfaces.trackstate_cli_release_replacement_probe import (
    TrackStateCliReleaseReplacementProbe,
)
from testing.frameworks.python.trackstate_cli_release_replacement_framework import (
    PythonTrackStateCliReleaseReplacementFramework,
)


def create_trackstate_cli_release_replacement_probe(
    repository_root: Path,
) -> TrackStateCliReleaseReplacementProbe:
    return PythonTrackStateCliReleaseReplacementFramework(
        repository_root,
        LiveSetupRepositoryService(),
    )
