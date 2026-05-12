from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.trackstate_cli_read_profile_local_probe import (
    TrackStateCliReadProfileLocalProbe,
)
from testing.frameworks.python.trackstate_cli_read_profile_local_framework import (
    PythonTrackStateCliReadProfileLocalFramework,
)


def create_trackstate_cli_read_profile_local_probe(
    repository_root: Path,
) -> TrackStateCliReadProfileLocalProbe:
    return PythonTrackStateCliReadProfileLocalFramework(repository_root)
