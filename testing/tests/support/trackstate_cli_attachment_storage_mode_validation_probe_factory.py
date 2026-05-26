from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.trackstate_cli_attachment_storage_mode_validation_probe import (
    TrackStateCliAttachmentStorageModeValidationProbe,
)
from testing.frameworks.python.trackstate_cli_attachment_storage_mode_validation_framework import (
    PythonTrackStateCliAttachmentStorageModeValidationFramework,
)


def create_trackstate_cli_attachment_storage_mode_validation_probe(
    repository_root: Path,
) -> TrackStateCliAttachmentStorageModeValidationProbe:
    return PythonTrackStateCliAttachmentStorageModeValidationFramework(repository_root)
