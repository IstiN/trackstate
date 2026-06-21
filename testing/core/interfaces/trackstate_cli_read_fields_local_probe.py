from __future__ import annotations

from typing import Protocol

from testing.core.config.trackstate_cli_read_fields_local_config import (
    TrackStateCliReadFieldsLocalConfig,
)
from testing.core.models.trackstate_cli_read_fields_local_result import (
    TrackStateCliReadFieldsLocalValidationResult,
)


class TrackStateCliReadFieldsLocalProbe(Protocol):
    def observe_local_fields_response(
        self,
        *,
        config: TrackStateCliReadFieldsLocalConfig,
    ) -> TrackStateCliReadFieldsLocalValidationResult: ...
