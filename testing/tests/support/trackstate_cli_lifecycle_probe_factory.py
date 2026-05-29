from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.trackstate_cli_lifecycle_probe import (
    TrackStateCliLifecycleProbe,
)
from testing.frameworks.python.trackstate_cli_lifecycle_framework import (
    PythonTrackStateCliLifecycleFramework,
)


def create_trackstate_cli_lifecycle_probe(
    repository_root: Path,
) -> TrackStateCliLifecycleProbe:
    return PythonTrackStateCliLifecycleFramework(repository_root)
