from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.trackstate_cli_canonical_link_formatter_probe import (
    TrackStateCliCanonicalLinkFormatterProbe,
)
from testing.frameworks.python.dart_probe_runtime import PythonDartProbeRuntime
from testing.frameworks.python.trackstate_cli_canonical_link_formatter_probe import (
    PythonTrackStateCliCanonicalLinkFormatterProbe,
)


def create_trackstate_cli_canonical_link_formatter_probe(
    repository_root: Path,
) -> TrackStateCliCanonicalLinkFormatterProbe:
    return PythonTrackStateCliCanonicalLinkFormatterProbe(
        repository_root,
        runtime=PythonDartProbeRuntime(repository_root),
    )
