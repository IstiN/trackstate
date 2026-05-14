from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class GitHubActionsWorkflowRunObservation:
    id: int
    event: str
    head_branch: str | None
    head_sha: str | None
    status: str | None
    conclusion: str | None
    html_url: str
    created_at: str | None
    display_title: str | None


@dataclass(frozen=True)
class GitHubActionsWorkflowJobObservation:
    id: int
    name: str
    status: str | None
    conclusion: str | None
    html_url: str
    started_at: str | None
    completed_at: str | None


@dataclass(frozen=True)
class GitHubActionsPreflightWorkflowObservation:
    html_url: str
    state: str
    path: str
    updated_at: str | None
    preflight_runs_on: list[str]
    downstream_runs_on: list[str]
    required_runner_labels: list[str]
    raw_file_text: str


@dataclass(frozen=True)
class GitHubActionsPreflightGateObservation:
    repository: str
    default_branch: str
    head_sha: str
    tag_name: str
    workflow_name: str
    workflow: GitHubActionsPreflightWorkflowObservation
    run: GitHubActionsWorkflowRunObservation
    preflight_job: GitHubActionsWorkflowJobObservation | None
    downstream_job: GitHubActionsWorkflowJobObservation | None
    matched_failure_text: str | None
    log_excerpt: str
    log_text: str
    expected_failure_markers: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class GitHubActionsPreflightGateProbe(Protocol):
    def validate(self) -> GitHubActionsPreflightGateObservation: ...
