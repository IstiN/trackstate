from __future__ import annotations

from typing import Protocol

from testing.core.config.trackstate_cli_read_profile_local_config import (
    TrackStateCliReadProfileLocalConfig,
)
from testing.core.models.trackstate_cli_read_profile_local_result import (
    TrackStateCliReadProfileLocalValidationResult,
)


class TrackStateCliReadProfileLocalProbe(Protocol):
    def observe_local_profile_response(
        self,
        *,
        config: TrackStateCliReadProfileLocalConfig,
    ) -> TrackStateCliReadProfileLocalValidationResult: ...
