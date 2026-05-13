from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.hosted_trackstate_session_cli_probe import (
    HostedTrackStateSessionCliProbe,
)
from testing.frameworks.python.hosted_trackstate_session_cli_framework import (
    PythonHostedTrackStateSessionCliFramework,
)


def create_hosted_trackstate_session_cli_probe(
    repository_root: Path,
) -> HostedTrackStateSessionCliProbe:
    return PythonHostedTrackStateSessionCliFramework(repository_root)
