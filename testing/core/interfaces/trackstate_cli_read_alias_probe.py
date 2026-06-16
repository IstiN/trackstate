from __future__ import annotations

from typing import Protocol

from testing.core.config.trackstate_cli_read_alias_config import (
    TrackStateCliReadAliasConfig,
)
from testing.core.models.trackstate_cli_read_alias_result import (
    TrackStateCliReadAliasValidationResult,
)


class TrackStateCliReadAliasProbe(Protocol):
    def observe_read_alias_responses(
        self,
        *,
        config: TrackStateCliReadAliasConfig,
    ) -> TrackStateCliReadAliasValidationResult: ...
