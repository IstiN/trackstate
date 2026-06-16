from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.trackstate_cli_self_link_guard_probe import (
    TrackStateCliSelfLinkGuardProbe,
)
from testing.frameworks.python.trackstate_cli_self_link_guard_framework import (
    PythonTrackStateCliSelfLinkGuardFramework,
)


def create_trackstate_cli_self_link_guard_probe(
    repository_root: Path,
) -> TrackStateCliSelfLinkGuardProbe:
    return PythonTrackStateCliSelfLinkGuardFramework(repository_root)
