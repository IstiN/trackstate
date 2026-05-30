from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.trackstate_cli_help_probe import TrackStateCliHelpProbe
from testing.frameworks.python.trackstate_cli_help_framework import (
    PythonTrackStateCliHelpFramework,
)


def create_trackstate_cli_help_probe(repository_root: Path) -> TrackStateCliHelpProbe:
    return PythonTrackStateCliHelpFramework(repository_root)
