from __future__ import annotations

from typing import Protocol

from testing.core.config.trackstate_cli_attachment_upload_boundary_config import (
    TrackStateCliAttachmentUploadBoundaryConfig,
)
from testing.core.models.trackstate_cli_attachment_upload_boundary_result import (
    TrackStateCliAttachmentUploadBoundaryValidationResult,
)


class TrackStateCliAttachmentUploadBoundaryProbe(Protocol):
    def observe_duplicate_file_boundary(
        self,
        *,
        config: TrackStateCliAttachmentUploadBoundaryConfig,
    ) -> TrackStateCliAttachmentUploadBoundaryValidationResult: ...
