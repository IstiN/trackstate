from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class ActionlintRulesetEnforcementObservation:
    repository: str
    default_branch: str
    protected_branches: list[str]
    active_ruleset_ids: list[int]
    active_ruleset_names: list[str]
    active_ruleset_urls: list[str]
    matching_ruleset_ids: list[int]
    matching_ruleset_names: list[str]
    matching_ruleset_urls: list[str]
    matching_ruleset_include_patterns: dict[str, list[str]]
    matching_ruleset_exclude_patterns: dict[str, list[str]]
    matching_ruleset_scope_covered_branches: dict[str, list[str]]
    matching_ruleset_required_status_checks: dict[str, list[str]]
    branch_required_check_contexts: dict[str, list[str]]
    branch_required_rule_descriptions: dict[str, list[str]]
    branch_actionlint_ruleset_ids: dict[str, list[int]]
    protected_branches_missing_matching_ruleset_scope: list[str]
    branches_with_actionlint_required: list[str]
    branches_missing_actionlint_required: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ActionlintRulesetEnforcementProbe(Protocol):
    def validate(self) -> ActionlintRulesetEnforcementObservation: ...
