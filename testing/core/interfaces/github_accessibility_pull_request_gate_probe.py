from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class GitHubAccessibilityPullRequestGateObservation:
    repository: str
    default_branch: str
    target_workflow_name: str
    target_workflow_path: str
    target_workflow_present_on_default_branch: bool
    target_workflow_state: str | None
    target_workflow_html_url: str | None
    target_workflow_declares_pull_request_trigger: bool
    target_workflow_job_names: list[str]
    target_workflow_step_names: list[str]
    default_branch_workflow_paths: list[str]
    pull_request_workflow_paths: list[str]
    workflows_with_accessibility_markers: list[str]
    workflow_accessibility_markers_found: dict[str, list[str]]
    required_rule_descriptions: list[str]
    required_check_contexts: list[str]
    required_check_workflow_paths: list[str]
    required_check_workflow_names: list[str]
    repository_declares_accessibility_required_check: bool
    expected_accessibility_markers: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class GitHubAccessibilityPullRequestGateProbe(Protocol):
    def validate(self) -> GitHubAccessibilityPullRequestGateObservation: ...
