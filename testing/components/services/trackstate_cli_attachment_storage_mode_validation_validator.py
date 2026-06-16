from __future__ import annotations

from testing.core.config.trackstate_cli_attachment_storage_mode_validation_config import (
    TrackStateCliAttachmentStorageModeValidationConfig,
)
from testing.core.interfaces.trackstate_cli_attachment_storage_mode_validation_probe import (
    TrackStateCliAttachmentStorageModeValidationProbe,
)
from testing.core.models.trackstate_cli_attachment_storage_mode_validation_result import (
    TrackStateCliAttachmentStorageModeValidationResult,
)


class TrackStateCliAttachmentStorageModeValidationValidator:
    def __init__(
        self,
        probe: TrackStateCliAttachmentStorageModeValidationProbe,
    ) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateCliAttachmentStorageModeValidationConfig,
    ) -> TrackStateCliAttachmentStorageModeValidationResult:
        return self._probe.observe_invalid_attachment_storage_mode(config=config)
