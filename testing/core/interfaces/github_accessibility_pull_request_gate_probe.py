from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Protocol

from testing.core.interfaces.github_actions_preflight_gate_probe import (
    GitHubActionsWorkflowJobObservation,
)


@dataclass(frozen=True)
class GitHubAccessibilityWorkflowContractObservation:
    declares_pull_request_trigger: bool
    job_names: list[str]
    step_names: list[str]
    accessibility_job_names: list[str]
    downstream_job_names: list[str]
    downstream_job_depends_on_accessibility: bool


@dataclass(frozen=True)
class GitHubAccessibilityPullRequestGateObservation:
    repository: str
    default_branch: str
    target_workflow_name: str
    target_workflow_path: str
    target_workflow_id: int
    target_workflow_present_on_default_branch: bool
    target_workflow_declares_pull_request_trigger: bool
    target_workflow_job_names: list[str]
    target_workflow_step_names: list[str]
    target_workflow_accessibility_job_names: list[str]
    target_workflow_downstream_job_names: list[str]
    target_workflow_downstream_job_depends_on_accessibility: bool
    target_workflow: GitHubAccessibilityWorkflowContractObservation
    pull_request_number: int
    pull_request_url: str
    pull_request_checks_url: str
    pull_request_head_branch: str
    pull_request_head_sha: str | None
    pull_request_probe_path: str
    probe_render_host_path: str
    probe_rendered_in_application: bool
    pull_request_file_paths: list[str]
    pull_request_state: str | None
    pull_request_mergeable_state: str | None
    pull_request_status_state: str | None
    latest_pull_request_run_id: int | None
    latest_pull_request_run_url: str | None
    latest_pull_request_run_event: str | None
    latest_pull_request_run_status: str | None
    latest_pull_request_run_conclusion: str | None
    observed_branch_run_names: list[str]
    observed_branch_run_urls: list[str]
    observed_branch_run_statuses: list[str]
    observed_branch_run_conclusions: list[str]
    observed_run_jobs: list[GitHubActionsWorkflowJobObservation]
    observed_job_names: list[str]
    observed_step_names: list[str]
    observed_status_check_names: list[str]
    observed_status_check_workflow_names: list[str]
    failed_status_check_names: list[str]
    failed_status_check_workflow_names: list[str]
    accessibility_status_check_name: str | None
    accessibility_status_check_workflow_name: str | None
    accessibility_status_check_status: str | None
    accessibility_status_check_conclusion: str | None
    accessibility_status_check_url: str | None
    matched_accessibility_markers: list[str]
    matched_contrast_markers: list[str]
    matched_semantic_markers: list[str]
    run_log_matched_accessibility_markers: list[str]
    run_log_matched_contrast_markers: list[str]
    run_log_matched_semantic_markers: list[str]
    run_log_mentions_accessibility: bool
    run_log_mentions_contrast_issue: bool
    run_log_mentions_semantic_issue: bool
    run_log_excerpt: str
    run_log_error: str | None
    runtime_accessibility_surface_present: bool
    runtime_accessibility_surface_summary: str
    probe_contains_low_contrast_indicator: bool
    probe_contains_semantic_label_indicator: bool
    probe_semantic_label: str
    probe_contrast_technique: str
    cleanup_closed_pull_request: bool
    cleanup_deleted_branch: bool
    default_branch_probe_host_present: bool = False
    default_branch_probe_host_summary: str = ""
    flutter_engine_initialization_log_entries: list[str] = field(default_factory=list)
    flutter_engine_initialization_summary: str = ""
    semantics_tree_discovery_log_entries: list[str] = field(default_factory=list)
    semantics_tree_discovery_summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class GitHubAccessibilityPullRequestGateProbe(Protocol):
    def validate(self) -> GitHubAccessibilityPullRequestGateObservation: ...
