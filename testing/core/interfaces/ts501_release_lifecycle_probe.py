from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Ts501ReleaseLifecycleProbeRequest:
    repository: str
    ref: str
    token: str
    issue_key: str
    attachment_name: str
    attachment_text: str
    release_tag_prefix: str


@dataclass(frozen=True)
class Ts501ReleaseLifecycleProbeResult:
    succeeded: bool
    analyze_output: str
    run_output: str | None
    session_payload: dict[str, object] | None


class Ts501ReleaseLifecycleProbe(Protocol):
    def execute(
        self,
        *,
        request: Ts501ReleaseLifecycleProbeRequest,
    ) -> Ts501ReleaseLifecycleProbeResult: ...
