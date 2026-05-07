from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ProviderContractProbeResult:
    succeeded: bool
    analyze_output: str
    run_output: str | None
    session_payload: dict[str, object] | None


class ProviderContractProbe(Protocol):
    def inspect(self) -> ProviderContractProbeResult: ...
