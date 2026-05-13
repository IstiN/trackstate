from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.trackstate_cli_standalone_compile_probe import (
    TrackStateCliStandaloneCompileProbe,
)
from testing.frameworks.python.trackstate_cli_standalone_compile_framework import (
    PythonTrackStateCliStandaloneCompileFramework,
)


def create_trackstate_cli_standalone_compile_probe(
    repository_root: Path,
) -> TrackStateCliStandaloneCompileProbe:
    return PythonTrackStateCliStandaloneCompileFramework(repository_root)
