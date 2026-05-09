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
    latest_pull_request_run_id: int
    latest_pull_request_run_url: str
    latest_pull_request_run_event: str
    latest_pull_request_run_status: str | None
    latest_pull_request_run_conclusion: str | None
    latest_pull_request_head_branch: str | None
    latest_pull_request_display_title: str | None
    latest_pull_request_created_at: str | None
    observed_job_names: list[str]
    observed_step_names: list[str]
    theme_token_job_name: str | None
    theme_token_step_status: str | None
    theme_token_step_conclusion: str | None
    workflow_declares_pull_request_trigger: bool
    workflow_declares_gate_step: bool
    workflow_declares_gate_command: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ThemeTokenCiProbe(Protocol):
    def validate(self) -> ThemeTokenCiObservation: ...
