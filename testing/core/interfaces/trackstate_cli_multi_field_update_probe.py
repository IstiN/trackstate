from __future__ import annotations

from typing import Protocol

from testing.core.config.trackstate_cli_multi_field_update_config import (
    TrackStateCliMultiFieldUpdateConfig,
)
from testing.core.models.trackstate_cli_multi_field_update_result import (
    TrackStateCliMultiFieldUpdateObservation,
)


class TrackStateCliMultiFieldUpdateProbe(Protocol):
    def observe_multi_field_update(
        self,
        *,
        config: TrackStateCliMultiFieldUpdateConfig,
    ) -> TrackStateCliMultiFieldUpdateObservation: ...
