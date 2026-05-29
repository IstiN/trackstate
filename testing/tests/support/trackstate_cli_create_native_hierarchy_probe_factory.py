from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.trackstate_cli_create_native_hierarchy_probe import (
    TrackStateCliCreateNativeHierarchyProbe,
)
from testing.frameworks.python.trackstate_cli_create_native_hierarchy_framework import (
    PythonTrackStateCliCreateNativeHierarchyFramework,
)


def create_trackstate_cli_create_native_hierarchy_probe(
    repository_root: Path,
) -> TrackStateCliCreateNativeHierarchyProbe:
    return PythonTrackStateCliCreateNativeHierarchyFramework(repository_root)
