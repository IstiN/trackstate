from __future__ import annotations

from testing.core.config.trackstate_cli_standalone_compile_config import (
    TrackStateCliStandaloneCompileConfig,
)
from testing.core.interfaces.trackstate_cli_standalone_compile_probe import (
    TrackStateCliStandaloneCompileProbe,
)
from testing.core.models.trackstate_cli_standalone_compile_result import (
    TrackStateCliStandaloneCompileValidationResult,
)


class TrackStateCliStandaloneCompileValidator:
    def __init__(self, probe: TrackStateCliStandaloneCompileProbe) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateCliStandaloneCompileConfig,
    ) -> TrackStateCliStandaloneCompileValidationResult:
        return self._probe.observe_standalone_compile(config=config)
