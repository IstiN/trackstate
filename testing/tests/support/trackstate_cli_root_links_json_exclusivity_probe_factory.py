from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.trackstate_cli_root_links_json_exclusivity_probe import (
    TrackStateCliRootLinksJsonExclusivityProbe,
)
from testing.frameworks.python.trackstate_cli_root_links_json_exclusivity_framework import (
    PythonTrackStateCliRootLinksJsonExclusivityFramework,
)


def create_trackstate_cli_root_links_json_exclusivity_probe(
    repository_root: Path,
) -> TrackStateCliRootLinksJsonExclusivityProbe:
    return PythonTrackStateCliRootLinksJsonExclusivityFramework(repository_root)
