from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.trackstate_cli_comment_creation_probe import (
    TrackStateCliCommentCreationProbe,
)
from testing.frameworks.python.trackstate_cli_comment_creation_framework import (
    PythonTrackStateCliCommentCreationFramework,
)


def create_trackstate_cli_comment_creation_probe(
    repository_root: Path,
) -> TrackStateCliCommentCreationProbe:
    return PythonTrackStateCliCommentCreationFramework(repository_root)
