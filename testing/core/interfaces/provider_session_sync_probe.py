from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ProviderSessionSyncProbeResult:
    succeeded: bool
    analyze_output: str
    run_output: str | None
    observation_payload: dict[str, object] | None


class ProviderSessionSyncProbe(Protocol):
    def inspect(self) -> ProviderSessionSyncProbeResult: ...
