from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.trackstate_cli_multi_field_update_probe import (
    TrackStateCliMultiFieldUpdateProbe,
)
from testing.frameworks.python.trackstate_cli_multi_field_update_framework import (
    PythonTrackStateCliMultiFieldUpdateFramework,
)


def create_trackstate_cli_multi_field_update_probe(
    repository_root: Path,
) -> TrackStateCliMultiFieldUpdateProbe:
    return PythonTrackStateCliMultiFieldUpdateFramework(repository_root)
