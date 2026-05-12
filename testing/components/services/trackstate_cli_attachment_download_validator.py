from __future__ import annotations

from testing.core.config.trackstate_cli_attachment_download_config import (
    TrackStateCliAttachmentDownloadConfig,
)
from testing.core.interfaces.trackstate_cli_attachment_download_probe import (
    TrackStateCliAttachmentDownloadProbe,
)
from testing.core.models.trackstate_cli_attachment_download_result import (
    TrackStateCliAttachmentDownloadValidationResult,
)


class TrackStateCliAttachmentDownloadValidator:
    def __init__(self, probe: TrackStateCliAttachmentDownloadProbe) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateCliAttachmentDownloadConfig,
    ) -> TrackStateCliAttachmentDownloadValidationResult:
        return self._probe.observe_attachment_download(config=config)
