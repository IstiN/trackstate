from __future__ import annotations

from testing.core.config.trackstate_cli_attachment_upload_boundary_config import (
    TrackStateCliAttachmentUploadBoundaryConfig,
)
from testing.core.interfaces.trackstate_cli_attachment_upload_boundary_probe import (
    TrackStateCliAttachmentUploadBoundaryProbe,
)
from testing.core.models.trackstate_cli_attachment_upload_boundary_result import (
    TrackStateCliAttachmentUploadBoundaryValidationResult,
)


class TrackStateCliAttachmentUploadBoundaryValidator:
    def __init__(
        self,
        probe: TrackStateCliAttachmentUploadBoundaryProbe,
    ) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateCliAttachmentUploadBoundaryConfig,
    ) -> TrackStateCliAttachmentUploadBoundaryValidationResult:
        return self._probe.observe_duplicate_file_boundary(config=config)
