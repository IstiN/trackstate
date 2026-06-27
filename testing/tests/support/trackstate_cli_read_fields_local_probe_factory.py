from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.trackstate_cli_read_fields_local_probe import (
    TrackStateCliReadFieldsLocalProbe,
)
from testing.frameworks.python.trackstate_cli_read_fields_local_framework import (
    PythonTrackStateCliReadFieldsLocalFramework,
)


def create_trackstate_cli_read_fields_local_probe(
    repository_root: Path,
) -> TrackStateCliReadFieldsLocalProbe:
    return PythonTrackStateCliReadFieldsLocalFramework(repository_root)
