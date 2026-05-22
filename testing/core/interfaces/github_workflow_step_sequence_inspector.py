from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class GitHubWorkflowStepContractObservation:
    job_id: str
    job_name: str
    step_name: str
    if_condition: str | None
    uses_always: bool


@dataclass(frozen=True)
class GitHubWorkflowRunStepObservation:
    job_name: str
    step_name: str
    number: int | None
    status: str | None
    conclusion: str | None
    started_at: str | None
    completed_at: str | None


@dataclass(frozen=True)
class GitHubWorkflowStepSequenceObservation:
    repository: str
    workflow_path: str
    workflow_ref: str
    workflow_url: str
    workflow_excerpt: str
    accessibility_job_name: str | None
    axe_step_contract: GitHubWorkflowStepContractObservation | None
    log_validation_step_contract: GitHubWorkflowStepContractObservation | None
    axe_step_run: GitHubWorkflowRunStepObservation | None
    log_validation_step_run: GitHubWorkflowRunStepObservation | None
    observed_job_names: list[str]
    observed_step_names: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class GitHubWorkflowStepSequenceInspector(Protocol):
    def inspect(
        self,
        *,
        repository: str,
        workflow_path: str,
        workflow_ref: str,
        run_id: int | None,
        accessibility_job_name: str,
        axe_step_name: str,
        log_validation_step_name: str,
    ) -> GitHubWorkflowStepSequenceObservation: ...
