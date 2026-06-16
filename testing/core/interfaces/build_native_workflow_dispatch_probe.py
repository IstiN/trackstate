from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class BuildNativeWorkflowDispatchObservation:
    repository: str
    workflow_path: str
    workflow_dispatch_enabled: bool
    runner_labels: tuple[str, ...]
    runner_available: bool
    online_runner_names: list[str]
    dispatched: bool
    run_id: int | None
    run_url: str | None
    run_status: str | None
    run_conclusion: str | None
    build_macos_job_name: str | None
    build_macos_job_conclusion: str | None
    reusable_workflow_path: str | None
    reusable_workflow_invoked: bool
    failure_reason: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BuildNativeWorkflowDispatchProbe(Protocol):
    def validate(self) -> BuildNativeWorkflowDispatchObservation: ...
