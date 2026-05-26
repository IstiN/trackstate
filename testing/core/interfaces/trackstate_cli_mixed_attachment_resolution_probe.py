from __future__ import annotations

from typing import Protocol

from testing.core.config.trackstate_cli_mixed_attachment_resolution_config import (
    TrackStateCliMixedAttachmentResolutionConfig,
)
from testing.core.models.trackstate_cli_mixed_attachment_resolution_result import (
    TrackStateCliMixedAttachmentResolutionValidationResult,
)


class TrackStateCliMixedAttachmentResolutionProbe(Protocol):
    def observe_mixed_attachment_resolution(
        self,
        *,
        config: TrackStateCliMixedAttachmentResolutionConfig,
    ) -> TrackStateCliMixedAttachmentResolutionValidationResult: ...
