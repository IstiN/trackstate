from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class ThemeTokenCiObservation:
    repository: str
    workflow_id: int
    workflow_name: str
    workflow_path: str
    workflow_html_url: str
    default_branch: str
    workflow_text: str
    pull_request_number: int
    pull_request_url: str
    pull_request_head_branch: str
    pull_request_probe_path: str
    pull_request_state: str | None
    pull_request_mergeable_state: str | None
    pull_request_head_sha: str
    pull_request_status_state: str | None
    latest_pull_request_run_id: int
    latest_pull_request_run_url: str
    latest_pull_request_run_event: str
    latest_pull_request_run_status: str | None
    latest_pull_request_run_conclusion: str | None
    observed_job_names: list[str]
    observed_step_names: list[str]
    theme_token_job_name: str | None
    theme_token_step_status: str | None
    theme_token_step_conclusion: str | None
    workflow_declares_pull_request_trigger: bool
    workflow_declares_gate_step: bool
    workflow_declares_gate_command: bool
    cleanup_closed_pull_request: bool
    cleanup_deleted_branch: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ThemeTokenCiProbe(Protocol):
    def validate(self) -> ThemeTokenCiObservation: ...
