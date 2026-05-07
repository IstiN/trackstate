from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class GitHubPagesWorkflowObservation:
    repository: str
    requested_repository: str
    expected_pages_url: str
    workflow_file: str
    workflow_run_id: int
    workflow_run_url: str
    workflow_run_conclusion: str | None
    branch_sha_before: str
    branch_sha_after: str
    pages_url: str
    pages_build_type: str | None
    pages_source_branch: str | None
    pages_source_path: str | None
    html_title: str | None
    html_base_href: str | None
    html_contains_bootstrap_script: bool
    bootstrap_asset_url: str
    bootstrap_asset_mentions_main_dart_js: bool
    build_assets_committed_to_branch: list[str]
    required_step_names: list[str]
    observed_required_steps: list[str]
    missing_required_steps: list[str]
    failed_required_steps: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class GitHubPagesWorkflowProbe(Protocol):
    def validate(self) -> GitHubPagesWorkflowObservation: ...
