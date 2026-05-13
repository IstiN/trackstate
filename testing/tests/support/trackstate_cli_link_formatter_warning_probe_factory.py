from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.trackstate_cli_link_formatter_warning_probe import (
    TrackStateCliLinkFormatterWarningProbe,
)
from testing.frameworks.python.trackstate_cli_link_formatter_warning_probe import (
    PythonTrackStateCliLinkFormatterWarningProbe,
)


def create_trackstate_cli_link_formatter_warning_probe(
    repository_root: Path,
) -> TrackStateCliLinkFormatterWarningProbe:
    return PythonTrackStateCliLinkFormatterWarningProbe(repository_root)
