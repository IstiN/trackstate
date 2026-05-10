from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class ActionlintWorkflowGateObservation:
    repository: str
    default_branch: str
    target_workflow_name: str
    target_workflow_path: str
    target_workflow_present_on_default_branch: bool
    default_branch_workflow_paths: list[str]
    workflows_declaring_actionlint: list[str]
    pushed_branch: str
    pushed_commit_sha: str
    branch_actions_page_url: str
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
    cleanup_deleted_branch: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ActionlintWorkflowGateProbe(Protocol):
    def validate(self) -> ActionlintWorkflowGateObservation: ...
