from __future__ import annotations

from testing.core.config.trackstate_cli_read_fields_config import (
    TrackStateCliReadFieldsConfig,
)
from testing.core.interfaces.trackstate_cli_read_fields_probe import (
    TrackStateCliReadFieldsProbe,
)
from testing.core.models.trackstate_cli_read_fields_result import (
    TrackStateCliReadFieldsValidationResult,
)


class TrackStateCliReadFieldsValidator:
    def __init__(self, probe: TrackStateCliReadFieldsProbe) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateCliReadFieldsConfig,
    ) -> TrackStateCliReadFieldsValidationResult:
        return self._probe.observe_fields_response_shape(config=config)
