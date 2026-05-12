from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.trackstate_cli_raw_jira_comment_response_probe import (
    TrackStateCliRawJiraCommentResponseProbe,
)
from testing.frameworks.python.trackstate_cli_raw_jira_comment_response_framework import (
    PythonTrackStateCliRawJiraCommentResponseFramework,
)


def create_trackstate_cli_raw_jira_comment_response_probe(
    repository_root: Path,
) -> TrackStateCliRawJiraCommentResponseProbe:
    return PythonTrackStateCliRawJiraCommentResponseFramework(repository_root)
