from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.trackstate_cli_field_resolution_probe import (
    TrackStateCliFieldResolutionProbe,
)
from testing.frameworks.python.trackstate_cli_field_resolution_framework import (
    PythonTrackStateCliFieldResolutionFramework,
)


def create_trackstate_cli_field_resolution_probe(
    repository_root: Path,
) -> TrackStateCliFieldResolutionProbe:
    return PythonTrackStateCliFieldResolutionFramework(repository_root)
