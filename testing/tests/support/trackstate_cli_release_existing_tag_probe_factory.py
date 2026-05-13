from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.trackstate_cli_release_existing_tag_probe import (
    TrackStateCliReleaseExistingTagProbe,
)
from testing.frameworks.python.trackstate_cli_release_existing_tag_framework import (
    PythonTrackStateCliReleaseExistingTagFramework,
)


def create_trackstate_cli_release_existing_tag_probe(
    repository_root: Path,
) -> TrackStateCliReleaseExistingTagProbe:
    return PythonTrackStateCliReleaseExistingTagFramework(repository_root)
