from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class NonDefaultBranchReleaseObservation:
    repository: str
    default_branch: str
    target_branch: str
    target_branch_created_by_test: bool
    pull_request_number: int
    pull_request_url: str
    pull_request_head_branch: str
    pull_request_base_branch: str
    pull_request_merged_at: str
    pull_request_merge_commit_sha: str
    releases_page_url: str
    tags_page_url: str
    releases_page_has_heading: bool
    tags_page_has_heading: bool
    releases_page_contains_unexpected_tag: bool
    tags_page_contains_unexpected_tag: bool
    unexpected_release_id: int | None
    unexpected_release_tag_name: str | None
    unexpected_release_html_url: str | None
    unexpected_release_tag_commit_sha: str | None
    unexpected_tag_name: str | None
    unexpected_tag_commit_sha: str | None
    baseline_release_ids: list[int]
    baseline_semver_tag_names: list[str]
    observed_new_release_ids: list[int]
    observed_new_semver_tag_names: list[str]
    poll_attempts: int
    quiet_period_seconds: int
    elapsed_quiet_period_seconds: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class NonDefaultBranchReleaseProbe(Protocol):
    def validate(self) -> NonDefaultBranchReleaseObservation: ...
