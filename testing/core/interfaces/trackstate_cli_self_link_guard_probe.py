from __future__ import annotations

from typing import Protocol

from testing.core.config.trackstate_cli_self_link_guard_config import (
    TrackStateCliSelfLinkGuardConfig,
)
from testing.core.models.trackstate_cli_self_link_guard_result import (
    TrackStateCliSelfLinkGuardValidationResult,
)


class TrackStateCliSelfLinkGuardProbe(Protocol):
    def observe_self_link_guard(
        self,
        *,
        config: TrackStateCliSelfLinkGuardConfig,
    ) -> TrackStateCliSelfLinkGuardValidationResult: ...
