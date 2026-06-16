from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.trackstate_cli_invalid_pagination_probe import (
    TrackStateCliInvalidPaginationProbe,
)
from testing.frameworks.python.trackstate_cli_invalid_pagination_framework import (
    PythonTrackStateCliInvalidPaginationFramework,
)


def create_trackstate_cli_invalid_pagination_probe(
    repository_root: Path,
) -> TrackStateCliInvalidPaginationProbe:
    return PythonTrackStateCliInvalidPaginationFramework(repository_root)
