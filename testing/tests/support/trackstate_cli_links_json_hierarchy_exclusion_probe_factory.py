from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.trackstate_cli_links_json_hierarchy_exclusion_probe import (
    TrackStateCliLinksJsonHierarchyExclusionProbe,
)
from testing.frameworks.python.trackstate_cli_links_json_hierarchy_exclusion_framework import (
    PythonTrackStateCliLinksJsonHierarchyExclusionFramework,
)


def create_trackstate_cli_links_json_hierarchy_exclusion_probe(
    repository_root: Path,
) -> TrackStateCliLinksJsonHierarchyExclusionProbe:
    return PythonTrackStateCliLinksJsonHierarchyExclusionFramework(repository_root)
