from __future__ import annotations

from typing import Protocol

from testing.core.config.trackstate_cli_attachment_storage_mode_validation_config import (
    TrackStateCliAttachmentStorageModeValidationConfig,
)
from testing.core.models.trackstate_cli_attachment_storage_mode_validation_result import (
    TrackStateCliAttachmentStorageModeValidationResult,
)


class TrackStateCliAttachmentStorageModeValidationProbe(Protocol):
    def observe_invalid_attachment_storage_mode(
        self,
        *,
        config: TrackStateCliAttachmentStorageModeValidationConfig,
    ) -> TrackStateCliAttachmentStorageModeValidationResult: ...
