from __future__ import annotations

from testing.core.config.trackstate_cli_local_attachment_upload_config import (
    TrackStateCliLocalAttachmentUploadConfig,
)
from testing.core.interfaces.trackstate_cli_local_attachment_upload_probe import (
    TrackStateCliLocalAttachmentUploadProbe,
)
from testing.core.models.trackstate_cli_local_attachment_upload_result import (
    TrackStateCliLocalAttachmentUploadValidationResult,
)


class TrackStateCliLocalAttachmentUploadValidator:
    def __init__(
        self,
        probe: TrackStateCliLocalAttachmentUploadProbe,
    ) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateCliLocalAttachmentUploadConfig,
    ) -> TrackStateCliLocalAttachmentUploadValidationResult:
        return self._probe.observe_local_attachment_upload(config=config)
