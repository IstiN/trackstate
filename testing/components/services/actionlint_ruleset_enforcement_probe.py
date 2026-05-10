from __future__ import annotations

from fnmatch import fnmatchcase
import json
from typing import Any

from testing.core.config.actionlint_ruleset_enforcement_config import (
    ActionlintRulesetEnforcementConfig,
)
from testing.core.interfaces.actionlint_ruleset_enforcement_probe import (
    ActionlintRulesetEnforcementObservation,
)
from testing.core.interfaces.github_api_client import (
    GitHubApiClient,
    GitHubApiClientError,
)


class ActionlintRulesetEnforcementError(RuntimeError):
    pass


class ActionlintRulesetEnforcementProbeService:
    def __init__(
        self,
        config: ActionlintRulesetEnforcementConfig,
        *,
        github_api_client: GitHubApiClient,
    ) -> None:
        self._config = config
        self._github_api_client = github_api_client

    def validate(self) -> ActionlintRulesetEnforcementObservation:
        repository_info = self._read_json_object(f"/repos/{self._config.repository}")
        default_branch = self._require_string(
            repository_info.get("default_branch"),
            "Repository metadata did not expose a default branch.",
        )

        protected_branches = self._list_protected_branches()
        active_branch_rulesets = self._list_active_branch_rulesets()

        matching_rulesets = [
            ruleset
            for ruleset in active_branch_rulesets
            if self._ruleset_requires_actionlint(ruleset)
        ]
        matching_ruleset_scope_covered_branches = {
            self._ruleset_name(ruleset): [
                branch_name
                for branch_name in protected_branches
                if self._ruleset_scope_covers_branch(
                    ruleset,
                    branch_name=branch_name,
                    default_branch=default_branch,
                )
            ]
            for ruleset in matching_rulesets
        }
        protected_branches_missing_matching_ruleset_scope = [
            branch_name
            for branch_name in protected_branches
            if not any(
                branch_name in covered_branches
                for covered_branches in matching_ruleset_scope_covered_branches.values()
            )
        ]

        branch_required_check_contexts: dict[str, list[str]] = {}
        branch_required_rule_descriptions: dict[str, list[str]] = {}
        branch_actionlint_ruleset_ids: dict[str, list[int]] = {}
        branches_with_actionlint_required: list[str] = []
        branches_missing_actionlint_required: list[str] = []

        for branch_name in protected_branches:
            branch_rules = self._read_effective_branch_rules(branch_name)
            contexts, descriptions, actionlint_ruleset_ids = (
                self._extract_effective_required_status_check_details(branch_rules)
            )
            branch_required_check_contexts[branch_name] = contexts
            branch_required_rule_descriptions[branch_name] = descriptions
            branch_actionlint_ruleset_ids[branch_name] = actionlint_ruleset_ids
            if actionlint_ruleset_ids:
                branches_with_actionlint_required.append(branch_name)
            else:
                branches_missing_actionlint_required.append(branch_name)

        return ActionlintRulesetEnforcementObservation(
            repository=self._config.repository,
            default_branch=default_branch,
            protected_branches=protected_branches,
            active_ruleset_ids=[int(ruleset["id"]) for ruleset in active_branch_rulesets],
            active_ruleset_names=[
                self._require_string(ruleset.get("name"), "Ruleset is missing a name.")
                for ruleset in active_branch_rulesets
            ],
            active_ruleset_urls=[
                self._ruleset_html_url(ruleset) for ruleset in active_branch_rulesets
            ],
            matching_ruleset_ids=[int(ruleset["id"]) for ruleset in matching_rulesets],
            matching_ruleset_names=[
                self._require_string(ruleset.get("name"), "Ruleset is missing a name.")
                for ruleset in matching_rulesets
            ],
            matching_ruleset_urls=[
                self._ruleset_html_url(ruleset) for ruleset in matching_rulesets
            ],
            matching_ruleset_include_patterns={
                self._ruleset_name(ruleset): self._ruleset_ref_patterns(
                    ruleset,
                    pattern_key="include",
                )
                for ruleset in matching_rulesets
            },
            matching_ruleset_exclude_patterns={
                self._ruleset_name(ruleset): self._ruleset_ref_patterns(
                    ruleset,
                    pattern_key="exclude",
                )
                for ruleset in matching_rulesets
            },
            matching_ruleset_scope_covered_branches=matching_ruleset_scope_covered_branches,
            matching_ruleset_required_status_checks={
                self._ruleset_name(ruleset): self._ruleset_required_status_checks(ruleset)
                for ruleset in matching_rulesets
            },
            branch_required_check_contexts=branch_required_check_contexts,
            branch_required_rule_descriptions=branch_required_rule_descriptions,
            branch_actionlint_ruleset_ids=branch_actionlint_ruleset_ids,
            protected_branches_missing_matching_ruleset_scope=(
                protected_branches_missing_matching_ruleset_scope
            ),
            branches_with_actionlint_required=branches_with_actionlint_required,
            branches_missing_actionlint_required=branches_missing_actionlint_required,
        )

    def _list_protected_branches(self) -> list[str]:
        payload = self._read_json_array(
            f"/repos/{self._config.repository}/branches?protected=true&per_page=100"
        )
        branches: list[str] = []
        for entry in payload:
            if not isinstance(entry, dict):
                continue
            branch_name = entry.get("name")
            if isinstance(branch_name, str) and branch_name.strip():
                branches.append(branch_name.strip())
        return self._dedupe(branches)

    def _list_active_branch_rulesets(self) -> list[dict[str, Any]]:
        payload = self._read_json_array(
            f"/repos/{self._config.repository}/rulesets?per_page=100"
        )
        active_rulesets: list[dict[str, Any]] = []
        for entry in payload:
            if not isinstance(entry, dict):
                continue
            if entry.get("target") != "branch" or entry.get("enforcement") != "active":
                continue
            ruleset_id = entry.get("id")
            if not isinstance(ruleset_id, int):
                continue
            active_rulesets.append(
                self._read_json_object(
                    f"/repos/{self._config.repository}/rulesets/{ruleset_id}"
                )
            )
        return active_rulesets

    def _ruleset_requires_actionlint(self, ruleset: dict[str, Any]) -> bool:
        marker = self._config.expected_actionlint_context.lower()
        return any(
            marker in context.lower()
            for context in self._ruleset_required_status_checks(ruleset)
        )

    def _ruleset_required_status_checks(self, ruleset: dict[str, Any]) -> list[str]:
        raw_rules = ruleset.get("rules")
        if not isinstance(raw_rules, list):
            return []

        contexts: list[str] = []
        for rule in raw_rules:
            if not isinstance(rule, dict):
                continue
            if rule.get("type") != "required_status_checks":
                continue
            parameters = rule.get("parameters")
            parameter_map = parameters if isinstance(parameters, dict) else {}
            contexts.extend(self._collect_required_status_check_contexts(parameter_map))
        return self._dedupe(contexts)

    def _ruleset_ref_patterns(
        self,
        ruleset: dict[str, Any],
        *,
        pattern_key: str,
    ) -> list[str]:
        conditions = ruleset.get("conditions")
        if not isinstance(conditions, dict):
            return []
        ref_name = conditions.get("ref_name")
        if not isinstance(ref_name, dict):
            return []
        raw_patterns = ref_name.get(pattern_key)
        if not isinstance(raw_patterns, list):
            return []
        values = [pattern.strip() for pattern in raw_patterns if isinstance(pattern, str)]
        return self._dedupe([value for value in values if value])

    def _ruleset_scope_covers_branch(
        self,
        ruleset: dict[str, Any],
        *,
        branch_name: str,
        default_branch: str,
    ) -> bool:
        include_patterns = self._ruleset_ref_patterns(ruleset, pattern_key="include")
        if not any(
            self._ref_pattern_matches_branch(
                pattern,
                branch_name=branch_name,
                default_branch=default_branch,
            )
            for pattern in include_patterns
        ):
            return False

        exclude_patterns = self._ruleset_ref_patterns(ruleset, pattern_key="exclude")
        return not any(
            self._ref_pattern_matches_branch(
                pattern,
                branch_name=branch_name,
                default_branch=default_branch,
            )
            for pattern in exclude_patterns
        )

    def _ref_pattern_matches_branch(
        self,
        pattern: str,
        *,
        branch_name: str,
        default_branch: str,
    ) -> bool:
        if pattern == "~DEFAULT_BRANCH":
            return branch_name == default_branch
        if pattern == "~ALL":
            return True

        branch_ref = f"refs/heads/{branch_name}"
        return fnmatchcase(branch_name, pattern) or fnmatchcase(branch_ref, pattern)

    def _read_effective_branch_rules(self, branch_name: str) -> list[dict[str, Any]]:
        payload = self._read_json_array(
            f"/repos/{self._config.repository}/rules/branches/{branch_name}"
        )
        return [rule for rule in payload if isinstance(rule, dict)]

    def _extract_effective_required_status_check_details(
        self,
        branch_rules: list[dict[str, Any]],
    ) -> tuple[list[str], list[str], list[int]]:
        marker = self._config.expected_actionlint_context.lower()
        contexts: list[str] = []
        descriptions: list[str] = []
        actionlint_ruleset_ids: list[int] = []

        for rule in branch_rules:
            rule_type = rule.get("type")
            if rule_type != "required_status_checks":
                continue

            parameters = rule.get("parameters")
            parameter_map = parameters if isinstance(parameters, dict) else {}
            rule_contexts = self._collect_required_status_check_contexts(parameter_map)
            contexts.extend(rule_contexts)
            descriptions.append(f"required_status_checks: {rule_contexts or ['<none>']}")

            if any(marker in context.lower() for context in rule_contexts):
                ruleset_id = rule.get("ruleset_id")
                if isinstance(ruleset_id, int):
                    actionlint_ruleset_ids.append(ruleset_id)

        return (
            self._dedupe(contexts),
            self._dedupe(descriptions),
            self._dedupe_ints(actionlint_ruleset_ids),
        )

    def _collect_required_status_check_contexts(
        self,
        payload: dict[str, Any],
    ) -> list[str]:
        values: list[str] = []
        for key in ("contexts", "required_status_checks", "checks"):
            raw_entries = payload.get(key)
            if not isinstance(raw_entries, list):
                continue
            for entry in raw_entries:
                if isinstance(entry, str) and entry.strip():
                    values.append(entry.strip())
                    continue
                if not isinstance(entry, dict):
                    continue
                context = entry.get("context")
                if isinstance(context, str) and context.strip():
                    values.append(context.strip())
                    continue
                name = entry.get("name")
                if isinstance(name, str) and name.strip():
                    values.append(name.strip())
        return values

    def _ruleset_name(self, ruleset: dict[str, Any]) -> str:
        return self._require_string(ruleset.get("name"), "Ruleset is missing a name.")

    def _ruleset_html_url(self, ruleset: dict[str, Any]) -> str:
        links = ruleset.get("_links")
        if not isinstance(links, dict):
            raise ActionlintRulesetEnforcementError("Ruleset did not expose _links data.")
        html_link = links.get("html")
        if not isinstance(html_link, dict):
            raise ActionlintRulesetEnforcementError(
                "Ruleset did not expose an HTML settings URL."
            )
        return self._require_string(
            html_link.get("href"),
            "Ruleset HTML settings URL was empty.",
        )

    def _read_json_object(self, endpoint: str) -> dict[str, Any]:
        payload = self._read_json(endpoint)
        if not isinstance(payload, dict):
            raise ActionlintRulesetEnforcementError(
                f"Expected GitHub API endpoint {endpoint} to return an object."
            )
        return payload

    def _read_json_array(self, endpoint: str) -> list[Any]:
        payload = self._read_json(endpoint)
        if not isinstance(payload, list):
            raise ActionlintRulesetEnforcementError(
                f"Expected GitHub API endpoint {endpoint} to return an array."
            )
        return payload

    def _read_json(self, endpoint: str) -> Any:
        try:
            response_text = self._github_api_client.request_text(endpoint=endpoint)
        except GitHubApiClientError as error:
            raise ActionlintRulesetEnforcementError(str(error)) from error
        try:
            return json.loads(response_text)
        except json.JSONDecodeError as error:
            raise ActionlintRulesetEnforcementError(
                f"GitHub API endpoint {endpoint} did not return valid JSON."
            ) from error

    def _require_string(self, value: object, error_message: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ActionlintRulesetEnforcementError(error_message)
        return value.strip()

    def _dedupe(self, values: list[str]) -> list[str]:
        seen: set[str] = set()
        deduped: list[str] = []
        for value in values:
            if value in seen:
                continue
            seen.add(value)
            deduped.append(value)
        return deduped

    def _dedupe_ints(self, values: list[int]) -> list[int]:
        seen: set[int] = set()
        deduped: list[int] = []
        for value in values:
            if value in seen:
                continue
            seen.add(value)
            deduped.append(value)
        return deduped
