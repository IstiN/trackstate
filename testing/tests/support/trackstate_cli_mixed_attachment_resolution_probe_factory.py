from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.trackstate_cli_mixed_attachment_resolution_probe import (
    TrackStateCliMixedAttachmentResolutionProbe,
)
from testing.frameworks.python.trackstate_cli_mixed_attachment_resolution_framework import (
    PythonTrackStateCliMixedAttachmentResolutionFramework,
)


def create_trackstate_cli_mixed_attachment_resolution_probe(
    repository_root: Path,
) -> TrackStateCliMixedAttachmentResolutionProbe:
    return PythonTrackStateCliMixedAttachmentResolutionFramework(repository_root)
