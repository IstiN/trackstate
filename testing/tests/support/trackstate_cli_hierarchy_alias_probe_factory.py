from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.trackstate_cli_hierarchy_alias_probe import (
    TrackStateCliHierarchyAliasProbe,
)
from testing.frameworks.python.trackstate_cli_hierarchy_alias_framework import (
    PythonTrackStateCliHierarchyAliasFramework,
)


def create_trackstate_cli_hierarchy_alias_probe(
    repository_root: Path,
) -> TrackStateCliHierarchyAliasProbe:
    return PythonTrackStateCliHierarchyAliasFramework(repository_root)
