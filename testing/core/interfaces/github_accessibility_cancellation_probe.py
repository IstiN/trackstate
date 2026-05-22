from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Protocol

from testing.core.interfaces.github_accessibility_pull_request_gate_probe import (
    GitHubAccessibilityPullRequestGateObservation,
)
from testing.core.interfaces.github_workflow_step_sequence_inspector import (
    GitHubWorkflowRunStepObservation,
)


@dataclass(frozen=True)
class GitHubAccessibilityCancellationProbeObservation:
    workflow_observation: GitHubAccessibilityPullRequestGateObservation
    cancellation_requested: bool
    cancellation_requested_at: str | None
    cancellation_request_error: str | None
    pre_cancel_axe_step: GitHubWorkflowRunStepObservation | None
    pre_cancel_log_validation_step: GitHubWorkflowRunStepObservation | None
    post_cancel_axe_step: GitHubWorkflowRunStepObservation | None
    post_cancel_log_validation_step: GitHubWorkflowRunStepObservation | None
    observed_job_names_pre_cancel: list[str]
    observed_step_names_pre_cancel: list[str]
    observed_job_names_post_cancel: list[str]
    observed_step_names_post_cancel: list[str]
    step_poll_trace: list[str]
    run_status_trace: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class GitHubAccessibilityCancellationProbe(Protocol):
    def validate(self) -> GitHubAccessibilityCancellationProbeObservation: ...
