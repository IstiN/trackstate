from __future__ import annotations

from typing import Protocol

from testing.core.config.trackstate_cli_symmetric_link_show_config import (
    TrackStateCliSymmetricLinkShowConfig,
)
from testing.core.models.trackstate_cli_symmetric_link_show_result import (
    TrackStateCliSymmetricLinkShowValidationResult,
)


class TrackStateCliSymmetricLinkShowProbe(Protocol):
    def observe_symmetric_link_show(
        self,
        *,
        config: TrackStateCliSymmetricLinkShowConfig,
    ) -> TrackStateCliSymmetricLinkShowValidationResult: ...
