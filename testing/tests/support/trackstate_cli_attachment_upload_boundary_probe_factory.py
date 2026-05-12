from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.trackstate_cli_attachment_upload_boundary_probe import (
    TrackStateCliAttachmentUploadBoundaryProbe,
)
from testing.frameworks.python.trackstate_cli_attachment_upload_boundary_framework import (
    PythonTrackStateCliAttachmentUploadBoundaryFramework,
)


def create_trackstate_cli_attachment_upload_boundary_probe(
    repository_root: Path,
) -> TrackStateCliAttachmentUploadBoundaryProbe:
    return PythonTrackStateCliAttachmentUploadBoundaryFramework(repository_root)
