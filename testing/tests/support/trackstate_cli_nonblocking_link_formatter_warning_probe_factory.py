from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.trackstate_cli_nonblocking_link_formatter_warning_probe import (
    TrackStateCliNonblockingLinkFormatterWarningProbe,
)
from testing.frameworks.python.dart_probe_runtime import PythonDartProbeRuntime
from testing.frameworks.python.trackstate_cli_nonblocking_link_formatter_warning_probe import (
    PythonTrackStateCliNonblockingLinkFormatterWarningProbe,
)


def create_trackstate_cli_nonblocking_link_formatter_warning_probe(
    repository_root: Path,
) -> TrackStateCliNonblockingLinkFormatterWarningProbe:
    return PythonTrackStateCliNonblockingLinkFormatterWarningProbe(
        repository_root,
        runtime=PythonDartProbeRuntime(repository_root),
    )
