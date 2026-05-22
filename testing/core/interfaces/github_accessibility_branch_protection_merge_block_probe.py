from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Protocol

from testing.core.interfaces.github_accessibility_pull_request_gate_probe import (
    GitHubAccessibilityPullRequestGateObservation,
)


@dataclass(frozen=True)
class GitHubAccessibilityBranchProtectionMergeBlockObservation:
    gate: GitHubAccessibilityPullRequestGateObservation
    required_rule_descriptions: list[str]
    required_check_contexts: list[str]
    repository_declares_accessibility_required_check: bool
    pull_request_mergeable: str | None
    pull_request_merge_state_status: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class GitHubAccessibilityBranchProtectionMergeBlockProbe(Protocol):
    def validate(self) -> GitHubAccessibilityBranchProtectionMergeBlockObservation: ...
