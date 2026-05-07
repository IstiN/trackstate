from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class DartProbeExecution:
    succeeded: bool
    analyze_output: str
    run_output: str | None
    session_payload: dict[str, object] | None


class DartProbeRuntime(Protocol):
    def execute(self, *, probe_root: Path, entrypoint: Path) -> DartProbeExecution: ...
