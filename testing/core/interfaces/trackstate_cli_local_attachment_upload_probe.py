from __future__ import annotations

from typing import Protocol

from testing.core.config.trackstate_cli_local_attachment_upload_config import (
    TrackStateCliLocalAttachmentUploadConfig,
)
from testing.core.models.trackstate_cli_local_attachment_upload_result import (
    TrackStateCliLocalAttachmentUploadValidationResult,
)


class TrackStateCliLocalAttachmentUploadProbe(Protocol):
    def observe_local_attachment_upload(
        self,
        *,
        config: TrackStateCliLocalAttachmentUploadConfig,
    ) -> TrackStateCliLocalAttachmentUploadValidationResult: ...
