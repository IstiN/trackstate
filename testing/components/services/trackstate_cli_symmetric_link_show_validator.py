from __future__ import annotations

from testing.core.config.trackstate_cli_symmetric_link_show_config import (
    TrackStateCliSymmetricLinkShowConfig,
)
from testing.core.interfaces.trackstate_cli_symmetric_link_show_probe import (
    TrackStateCliSymmetricLinkShowProbe,
)
from testing.core.models.trackstate_cli_symmetric_link_show_result import (
    TrackStateCliSymmetricLinkShowValidationResult,
)


class TrackStateCliSymmetricLinkShowValidator:
    def __init__(self, probe: TrackStateCliSymmetricLinkShowProbe) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateCliSymmetricLinkShowConfig,
    ) -> TrackStateCliSymmetricLinkShowValidationResult:
        return self._probe.observe_symmetric_link_show(config=config)
