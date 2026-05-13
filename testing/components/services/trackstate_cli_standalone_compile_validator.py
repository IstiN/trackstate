from __future__ import annotations

from pathlib import Path

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

    def restore_output_path(
        self,
        *,
        output_path: Path,
        backup_path: Path | None,
    ) -> None:
        self._probe.restore_output_path(
            output_path=output_path,
            backup_path=backup_path,
        )
