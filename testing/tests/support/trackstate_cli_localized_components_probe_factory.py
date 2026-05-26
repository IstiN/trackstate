from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.trackstate_cli_localized_components_probe import (
    TrackStateCliLocalizedComponentsProbe,
)
from testing.frameworks.python.trackstate_cli_localized_components_framework import (
    PythonTrackStateCliLocalizedComponentsFramework,
)


def create_trackstate_cli_localized_components_probe(
    repository_root: Path,
) -> TrackStateCliLocalizedComponentsProbe:
    return PythonTrackStateCliLocalizedComponentsFramework(repository_root)
