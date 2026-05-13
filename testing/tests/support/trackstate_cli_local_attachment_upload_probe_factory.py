from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.trackstate_cli_local_attachment_upload_probe import (
    TrackStateCliLocalAttachmentUploadProbe,
)
from testing.frameworks.python.trackstate_cli_local_attachment_upload_framework import (
    PythonTrackStateCliLocalAttachmentUploadFramework,
)


def create_trackstate_cli_local_attachment_upload_probe(
    repository_root: Path,
) -> TrackStateCliLocalAttachmentUploadProbe:
    return PythonTrackStateCliLocalAttachmentUploadFramework(repository_root)
