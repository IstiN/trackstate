from __future__ import annotations

from typing import Protocol

from testing.core.config.trackstate_cli_standalone_compile_config import (
    TrackStateCliStandaloneCompileConfig,
)
from testing.core.models.trackstate_cli_standalone_compile_result import (
    TrackStateCliStandaloneCompileValidationResult,
)


class TrackStateCliStandaloneCompileProbe(Protocol):
    def observe_standalone_compile(
        self,
        *,
        config: TrackStateCliStandaloneCompileConfig,
    ) -> TrackStateCliStandaloneCompileValidationResult: ...
