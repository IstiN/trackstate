from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.trackstate_cli_read_fields_probe import (
    TrackStateCliReadFieldsProbe,
)
from testing.frameworks.python.trackstate_cli_read_fields_framework import (
    PythonTrackStateCliReadFieldsFramework,
)


def create_trackstate_cli_read_fields_probe(
    repository_root: Path,
) -> TrackStateCliReadFieldsProbe:
    return PythonTrackStateCliReadFieldsFramework(repository_root)
