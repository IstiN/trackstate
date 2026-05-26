from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class WorkflowRunObservation:
    id: int
    name: str
    event: str
    head_branch: str | None
    head_sha: str | None
    status: str | None
    conclusion: str | None
    html_url: str
    created_at: str | None
    display_title: str | None


@dataclass(frozen=True)
class WorkflowDefinitionObservation:
    workflow_name: str
    workflow_file: str
    workflow_path: str
    state: str
    html_url: str
    updated_at: str | None
    push_branches: list[str]
    push_tags: list[str]
    workflow_dispatch_enabled: bool
    semantic_tag_hint_present: bool
    raw_file_text: str
    recent_runs: list[WorkflowRunObservation]
    ui_url: str | None
    ui_body_text: str
    ui_error: str | None
    ui_screenshot_path: str | None


@dataclass(frozen=True)
class WorkflowRunTagEvidenceObservation:
    run: WorkflowRunObservation
    semantic_tags: list[str]
    log_excerpt: str


@dataclass(frozen=True)
class GitHubWorkflowTriggerIsolationObservation:
    repository: str
    default_branch: str
    current_default_branch_sha: str
    apple_release: WorkflowDefinitionObservation
    main_ci: WorkflowDefinitionObservation
    cutoff_timestamp: str | None
    apple_push_main_after_cutoff: list[WorkflowRunObservation]
    main_ci_push_main_after_cutoff: list[WorkflowRunObservation]
    apple_push_main_current_sha: list[WorkflowRunObservation]
    main_ci_push_main_current_sha: list[WorkflowRunObservation]
    apple_push_semver_tag_evidence: list[WorkflowRunTagEvidenceObservation]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class GitHubWorkflowTriggerIsolationProbe(Protocol):
    def validate(self) -> GitHubWorkflowTriggerIsolationObservation: ...
