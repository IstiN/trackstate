from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.trackstate_cli_fallback_boundaries_probe import (
    TrackStateCliFallbackBoundariesProbe,
)
from testing.frameworks.python.trackstate_cli_fallback_boundaries_framework import (
    PythonTrackStateCliFallbackBoundariesFramework,
)


def create_trackstate_cli_fallback_boundaries_probe(
    repository_root: Path,
) -> TrackStateCliFallbackBoundariesProbe:
    return PythonTrackStateCliFallbackBoundariesFramework(repository_root)
