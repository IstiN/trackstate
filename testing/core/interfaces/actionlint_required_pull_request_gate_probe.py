from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class ActionlintRequiredPullRequestGateObservation:
    repository: str
    default_branch: str
    target_workflow_name: str
    target_workflow_path: str
    target_workflow_present_on_default_branch: bool
    default_branch_workflow_paths: list[str]
    workflows_declaring_actionlint: list[str]
    required_rule_descriptions: list[str]
    required_check_contexts: list[str]
    required_check_workflow_paths: list[str]
    required_check_workflow_names: list[str]
    repository_declares_actionlint_required_check: bool
    pull_request_number: int
    pull_request_url: str
    pull_request_checks_url: str
    pull_request_head_branch: str
    pull_request_state: str | None
    pull_request_mergeable_state: str | None
    pull_request_mergeable: str | None
    pull_request_merge_state_status: str | None
    pull_request_status_state: str | None
    observed_status_check_names: list[str]
    observed_status_check_workflow_names: list[str]
    actionlint_status_check_name: str | None
    actionlint_status_check_workflow_name: str | None
    actionlint_status_check_status: str | None
    actionlint_status_check_conclusion: str | None
    actionlint_status_check_url: str | None
    observed_branch_run_count: int
    observed_branch_run_names: list[str]
    observed_branch_run_paths: list[str]
    observed_branch_run_urls: list[str]
    observed_branch_run_statuses: list[str]
    observed_branch_run_conclusions: list[str]
    observed_job_names: list[str]
    observed_step_names: list[str]
    actionlint_run_name: str | None
    actionlint_run_path: str | None
    actionlint_run_url: str | None
    actionlint_run_status: str | None
    actionlint_run_conclusion: str | None
    actionlint_job_name: str | None
    actionlint_step_name: str | None
    actionlint_step_conclusion: str | None
    mutated_line_preview: str
    cleanup_closed_pull_request: bool
    cleanup_deleted_branch: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ActionlintRequiredPullRequestGateProbe(Protocol):
    def validate(self) -> ActionlintRequiredPullRequestGateObservation: ...
