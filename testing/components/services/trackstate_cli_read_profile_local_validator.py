from __future__ import annotations

from testing.core.config.trackstate_cli_read_profile_local_config import (
    TrackStateCliReadProfileLocalConfig,
)
from testing.core.interfaces.trackstate_cli_read_profile_local_probe import (
    TrackStateCliReadProfileLocalProbe,
)
from testing.core.models.trackstate_cli_read_profile_local_result import (
    TrackStateCliReadProfileLocalValidationResult,
)


class TrackStateCliReadProfileLocalValidator:
    def __init__(self, probe: TrackStateCliReadProfileLocalProbe) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateCliReadProfileLocalConfig,
    ) -> TrackStateCliReadProfileLocalValidationResult:
        return self._probe.observe_local_profile_response(config=config)
