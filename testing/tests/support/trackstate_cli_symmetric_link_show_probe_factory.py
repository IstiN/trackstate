from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.trackstate_cli_symmetric_link_show_probe import (
    TrackStateCliSymmetricLinkShowProbe,
)
from testing.frameworks.python.trackstate_cli_symmetric_link_show_framework import (
    PythonTrackStateCliSymmetricLinkShowFramework,
)


def create_trackstate_cli_symmetric_link_show_probe(
    repository_root: Path,
) -> TrackStateCliSymmetricLinkShowProbe:
    return PythonTrackStateCliSymmetricLinkShowFramework(repository_root)
