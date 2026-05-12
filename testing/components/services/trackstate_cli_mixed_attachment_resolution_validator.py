from __future__ import annotations

from testing.core.config.trackstate_cli_mixed_attachment_resolution_config import (
    TrackStateCliMixedAttachmentResolutionConfig,
)
from testing.core.interfaces.trackstate_cli_mixed_attachment_resolution_probe import (
    TrackStateCliMixedAttachmentResolutionProbe,
)
from testing.core.models.trackstate_cli_mixed_attachment_resolution_result import (
    TrackStateCliMixedAttachmentResolutionValidationResult,
)


class TrackStateCliMixedAttachmentResolutionValidator:
    def __init__(
        self,
        probe: TrackStateCliMixedAttachmentResolutionProbe,
    ) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateCliMixedAttachmentResolutionConfig,
    ) -> TrackStateCliMixedAttachmentResolutionValidationResult:
        return self._probe.observe_mixed_attachment_resolution(config=config)
