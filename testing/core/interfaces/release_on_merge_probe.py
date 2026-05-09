from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class ReleaseOnMergeObservation:
    repository: str
    default_branch: str
    pull_request_number: int
    pull_request_url: str
    pull_request_head_branch: str
    pull_request_merged_at: str
    pull_request_merge_commit_sha: str
    release_id: int
    release_tag_name: str
    release_html_url: str
    release_published_at: str | None
    tag_name: str
    tag_commit_sha: str | None
    releases_page_url: str
    tags_page_url: str
    releases_page_contains_tag: bool
    tags_page_contains_tag: bool
    poll_attempts: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ReleaseOnMergeProbe(Protocol):
    def validate(self) -> ReleaseOnMergeObservation: ...
