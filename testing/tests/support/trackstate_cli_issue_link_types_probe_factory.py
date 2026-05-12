from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.trackstate_cli_issue_link_types_probe import (
    TrackStateCliIssueLinkTypesProbe,
)
from testing.frameworks.python.trackstate_cli_issue_link_types_framework import (
    PythonTrackStateCliIssueLinkTypesFramework,
)


def create_trackstate_cli_issue_link_types_probe(
    repository_root: Path,
) -> TrackStateCliIssueLinkTypesProbe:
    return PythonTrackStateCliIssueLinkTypesFramework(repository_root)
