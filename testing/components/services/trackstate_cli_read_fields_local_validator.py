from __future__ import annotations

from testing.core.config.trackstate_cli_read_fields_local_config import (
    TrackStateCliReadFieldsLocalConfig,
)
from testing.core.interfaces.trackstate_cli_read_fields_local_probe import (
    TrackStateCliReadFieldsLocalProbe,
)
from testing.core.models.trackstate_cli_read_fields_local_result import (
    TrackStateCliReadFieldsLocalValidationResult,
)


class TrackStateCliReadFieldsLocalValidator:
    def __init__(self, probe: TrackStateCliReadFieldsLocalProbe) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateCliReadFieldsLocalConfig,
    ) -> TrackStateCliReadFieldsLocalValidationResult:
        return self._probe.observe_local_fields_response(config=config)
