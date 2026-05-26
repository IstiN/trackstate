from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.trackstate_cli_attachment_discovery_probe import (
    TrackStateCliAttachmentDiscoveryProbe,
)
from testing.frameworks.python.trackstate_cli_attachment_discovery_framework import (
    PythonTrackStateCliAttachmentDiscoveryFramework,
)


def create_trackstate_cli_attachment_discovery_probe(
    repository_root: Path,
) -> TrackStateCliAttachmentDiscoveryProbe:
    return PythonTrackStateCliAttachmentDiscoveryFramework(repository_root)
