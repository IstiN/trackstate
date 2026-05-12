from __future__ import annotations

from testing.core.config.trackstate_cli_multi_field_update_config import (
    TrackStateCliMultiFieldUpdateConfig,
)
from testing.core.interfaces.trackstate_cli_multi_field_update_probe import (
    TrackStateCliMultiFieldUpdateProbe,
)
from testing.core.models.trackstate_cli_multi_field_update_result import (
    TrackStateCliMultiFieldUpdateValidationResult,
)


class TrackStateCliMultiFieldUpdateValidator:
    def __init__(self, probe: TrackStateCliMultiFieldUpdateProbe) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateCliMultiFieldUpdateConfig,
    ) -> TrackStateCliMultiFieldUpdateValidationResult:
        return TrackStateCliMultiFieldUpdateValidationResult(
            observation=self._probe.observe_multi_field_update(config=config)
        )
