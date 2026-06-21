from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from testing.core.config.non_default_branch_release_config import (
    NonDefaultBranchReleaseConfig,
)


class NonDefaultBranchReleaseRepositoryError(RuntimeError):
    pass


class NonDefaultBranchReleaseEnvironmentError(NonDefaultBranchReleaseRepositoryError):
    """Raised when the live GitHub environment required by the test is unavailable.

    This is a distinct subclass so callers can differentiate an infrastructure
    precondition failure (missing GitHub CLI, no authentication, no network, or
    missing repository permissions) from a genuine release-automation defect.
    """

    pass


@dataclass(frozen=True)
class NonDefaultBranchMergedPullRequest:
    number: int
    url: str
    head_branch: str
    base_branch: str
    merged_at: str
    merge_commit_sha: str
    target_branch_created_by_test: bool
    temp_repository_root: Path
    source_branch_pushed: bool
    target_branch_pushed: bool


class NonDefaultBranchReleaseRepository(Protocol):
    def create_and_merge_pull_request(
        self,
        *,
        config: NonDefaultBranchReleaseConfig,
        default_branch: str,
    ) -> NonDefaultBranchMergedPullRequest: ...

    def cleanup_disposable_environment(
        self,
        merged_pull_request: NonDefaultBranchMergedPullRequest,
    ) -> None: ...
