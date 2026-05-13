from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Protocol


@dataclass(frozen=True)
class DartProbeExecution:
    succeeded: bool
    analyze_output: str
    run_output: str | None
    session_payload: dict[str, object] | None
    run_stderr: str | None = None


class DartProbeRuntime(Protocol):
    def execute(
        self,
        *,
        probe_root: Path,
        entrypoint: Path,
        extra_env: Mapping[str, str] | None = None,
    ) -> DartProbeExecution: ...
