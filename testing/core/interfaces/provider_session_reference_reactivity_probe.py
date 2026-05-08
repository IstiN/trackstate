from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ProviderSessionReferenceReactivityProbeResult:
    succeeded: bool
    analyze_output: str
    run_output: str | None
    observation_payload: dict[str, object] | None


class ProviderSessionReferenceReactivityProbe(Protocol):
    def inspect(self) -> ProviderSessionReferenceReactivityProbeResult: ...
