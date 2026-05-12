from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.trackstate_cli_attachment_download_probe import (
    TrackStateCliAttachmentDownloadProbe,
)
from testing.frameworks.python.trackstate_cli_attachment_download_framework import (
    PythonTrackStateCliAttachmentDownloadFramework,
)


def create_trackstate_cli_attachment_download_probe(
    repository_root: Path,
) -> TrackStateCliAttachmentDownloadProbe:
    return PythonTrackStateCliAttachmentDownloadFramework(repository_root)
