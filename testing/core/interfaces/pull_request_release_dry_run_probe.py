from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class PullRequestReleaseDryRunObservation:
    repository: str
    workflow_id: int
    workflow_name: str
    workflow_path: str
    workflow_html_url: str
    default_branch: str
    workflow_text: str
    workflow_declares_pull_request_trigger: bool
    workflow_declares_dry_run_step: bool
    workflow_declares_dry_run_command: bool
    pull_request_number: int
    pull_request_url: str
    pull_request_checks_url: str
    pull_request_head_branch: str
    pull_request_probe_path: str
    pull_request_state: str | None
    pull_request_mergeable_state: str | None
    pull_request_head_sha: str | None
    pull_request_status_state: str | None
    observed_branch_run_count: int
    observed_branch_run_names: list[str]
    observed_branch_run_paths: list[str]
    observed_branch_run_urls: list[str]
    observed_branch_run_events: list[str]
    observed_branch_run_statuses: list[str]
    observed_branch_run_conclusions: list[str]
    observed_job_names: list[str]
    observed_step_names: list[str]
    dry_run_run_name: str | None
    dry_run_run_path: str | None
    dry_run_run_url: str | None
    dry_run_run_event: str | None
    dry_run_run_status: str | None
    dry_run_run_conclusion: str | None
    dry_run_job_name: str | None
    dry_run_step_name: str | None
    dry_run_step_status: str | None
    dry_run_step_conclusion: str | None
    cleanup_closed_pull_request: bool
    cleanup_deleted_branch: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class PullRequestReleaseDryRunProbe(Protocol):
    def validate(self) -> PullRequestReleaseDryRunObservation: ...
