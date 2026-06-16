from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.trackstate_cli_read_alias_probe import (
    TrackStateCliReadAliasProbe,
)
from testing.frameworks.python.trackstate_cli_read_alias_framework import (
    PythonTrackStateCliReadAliasFramework,
)


def create_trackstate_cli_read_alias_probe(
    repository_root: Path,
) -> TrackStateCliReadAliasProbe:
    return PythonTrackStateCliReadAliasFramework(repository_root)
