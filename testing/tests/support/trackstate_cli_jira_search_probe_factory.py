from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.trackstate_cli_jira_search_probe import (
    TrackStateCliJiraSearchProbe,
)
from testing.frameworks.python.trackstate_cli_jira_search_framework import (
    PythonTrackStateCliJiraSearchFramework,
)


def create_trackstate_cli_jira_search_probe(
    repository_root: Path,
) -> TrackStateCliJiraSearchProbe:
    return PythonTrackStateCliJiraSearchFramework(repository_root)
