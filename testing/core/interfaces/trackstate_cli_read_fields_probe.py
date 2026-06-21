from __future__ import annotations

from typing import Protocol

from testing.core.config.trackstate_cli_read_fields_config import (
    TrackStateCliReadFieldsConfig,
)
from testing.core.models.trackstate_cli_read_fields_result import (
    TrackStateCliReadFieldsValidationResult,
)


class TrackStateCliReadFieldsProbe(Protocol):
    def observe_read_fields_response(
        self,
        *,
        config: TrackStateCliReadFieldsConfig,
    ) -> TrackStateCliReadFieldsValidationResult: ...
