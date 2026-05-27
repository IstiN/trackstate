from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.trackstate_cli_invalid_link_type_probe import (
    TrackStateCliInvalidLinkTypeProbe,
)
from testing.frameworks.python.trackstate_cli_invalid_link_type_framework import (
    PythonTrackStateCliInvalidLinkTypeFramework,
)


def create_trackstate_cli_invalid_link_type_probe(
    repository_root: Path,
) -> TrackStateCliInvalidLinkTypeProbe:
    return PythonTrackStateCliInvalidLinkTypeFramework(repository_root)
