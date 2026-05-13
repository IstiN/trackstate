from __future__ import annotations

from pathlib import Path
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

    def restore_output_path(
        self,
        *,
        output_path: Path,
        backup_path: Path | None,
    ) -> None: ...
