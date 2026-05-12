from __future__ import annotations

from typing import Protocol

from testing.core.config.trackstate_cli_attachment_download_config import (
    TrackStateCliAttachmentDownloadConfig,
)
from testing.core.models.trackstate_cli_attachment_download_result import (
    TrackStateCliAttachmentDownloadValidationResult,
)


class TrackStateCliAttachmentDownloadProbe(Protocol):
    def observe_attachment_download(
        self,
        *,
        config: TrackStateCliAttachmentDownloadConfig,
    ) -> TrackStateCliAttachmentDownloadValidationResult: ...
