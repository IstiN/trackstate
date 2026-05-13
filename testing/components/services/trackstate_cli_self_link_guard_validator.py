from __future__ import annotations

from testing.core.config.trackstate_cli_self_link_guard_config import (
    TrackStateCliSelfLinkGuardConfig,
)
from testing.core.interfaces.trackstate_cli_self_link_guard_probe import (
    TrackStateCliSelfLinkGuardProbe,
)
from testing.core.models.trackstate_cli_self_link_guard_result import (
    TrackStateCliSelfLinkGuardValidationResult,
)


class TrackStateCliSelfLinkGuardValidator:
    def __init__(self, probe: TrackStateCliSelfLinkGuardProbe) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateCliSelfLinkGuardConfig,
    ) -> TrackStateCliSelfLinkGuardValidationResult:
        return self._probe.observe_self_link_guard(config=config)
