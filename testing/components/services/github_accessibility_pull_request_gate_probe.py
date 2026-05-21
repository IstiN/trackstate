from __future__ import annotations

import json
from typing import Any
from urllib.parse import quote

import yaml

from testing.core.config.github_accessibility_pull_request_gate_config import (
    GitHubAccessibilityPullRequestGateConfig,
)
from testing.core.interfaces.github_accessibility_pull_request_gate_probe import (
    GitHubAccessibilityPullRequestGateObservation,
)
from testing.core.interfaces.github_api_client import (
    GitHubApiClient,
    GitHubApiClientError,
)


class GitHubAccessibilityPullRequestGateError(RuntimeError):
    pass


class GitHubAccessibilityPullRequestGateProbeService:
    def __init__(
        self,
        config: GitHubAccessibilityPullRequestGateConfig,
        *,
        github_api_client: GitHubApiClient,
    ) -> None:
        self._config = config
        self._github_api_client = github_api_client

    def validate(self) -> GitHubAccessibilityPullRequestGateObservation:
        repository_info = self._read_json_object(f"/repos/{self._config.repository}")
        default_branch = self._default_branch(repository_info)

        workflows = self._list_workflows()
        workflow_id_to_path = self._workflow_id_to_path(workflows)
        workflow_path_to_name = self._workflow_path_to_name(workflows)
        workflow_path_to_state = self._workflow_path_to_state(workflows)
        workflow_path_to_url = self._workflow_path_to_url(workflows)
        default_branch_workflow_paths = list(workflow_id_to_path.values())

        pull_request_workflow_paths: list[str] = []
        workflow_accessibility_markers_found: dict[str, list[str]] = {}
        target_workflow_job_names: list[str] = []
        target_workflow_step_names: list[str] = []
        target_workflow_declares_pull_request_trigger = False

        for workflow_path in default_branch_workflow_paths:
            try:
                workflow_text = self._read_workflow_text(workflow_path, default_branch)
            except GitHubApiClientError:
                if workflow_path == self._config.target_workflow_path:
                    raise
                continue
            if self._workflow_declares_event(workflow_text, "pull_request"):
                pull_request_workflow_paths.append(workflow_path)
            matched_markers = self._matched_accessibility_markers(workflow_text)
            if matched_markers:
                workflow_accessibility_markers_found[workflow_path] = matched_markers
            if workflow_path == self._config.target_workflow_path:
                (
                    target_workflow_declares_pull_request_trigger,
                    target_workflow_job_names,
                    target_workflow_step_names,
                ) = self._workflow_contract(workflow_text)

        required_rules = self._read_required_check_rules(workflow_path_to_name)
        repository_declares_accessibility_required_check = self._has_accessibility_marker(
            [
                *required_rules["descriptions"],
                *required_rules["contexts"],
                *required_rules["workflow_paths"],
                *required_rules["workflow_names"],
            ]
        )

        return GitHubAccessibilityPullRequestGateObservation(
            repository=self._config.repository,
            default_branch=default_branch,
            target_workflow_name=self._config.target_workflow_name,
            target_workflow_path=self._config.target_workflow_path,
            target_workflow_present_on_default_branch=(
                self._config.target_workflow_path in default_branch_workflow_paths
            ),
            target_workflow_state=workflow_path_to_state.get(
                self._config.target_workflow_path
            ),
            target_workflow_html_url=workflow_path_to_url.get(
                self._config.target_workflow_path
            ),
            target_workflow_declares_pull_request_trigger=(
                target_workflow_declares_pull_request_trigger
            ),
            target_workflow_job_names=target_workflow_job_names,
            target_workflow_step_names=target_workflow_step_names,
            default_branch_workflow_paths=default_branch_workflow_paths,
            pull_request_workflow_paths=self._dedupe(pull_request_workflow_paths),
            workflows_with_accessibility_markers=sorted(
                workflow_accessibility_markers_found.keys()
            ),
            workflow_accessibility_markers_found={
                key: list(value)
                for key, value in sorted(workflow_accessibility_markers_found.items())
            },
            required_rule_descriptions=list(required_rules["descriptions"]),
            required_check_contexts=list(required_rules["contexts"]),
            required_check_workflow_paths=list(required_rules["workflow_paths"]),
            required_check_workflow_names=list(required_rules["workflow_names"]),
            repository_declares_accessibility_required_check=(
                repository_declares_accessibility_required_check
            ),
            expected_accessibility_markers=list(
                self._config.expected_accessibility_markers
            ),
        )

    def _list_workflows(self) -> list[dict[str, Any]]:
        payload = self._read_json_object(
            f"/repos/{self._config.repository}/actions/workflows?per_page=100"
        )
        workflows = payload.get("workflows")
        if not isinstance(workflows, list):
            raise GitHubAccessibilityPullRequestGateError(
                "GitHub Actions workflows response did not include a workflows list."
            )
        return [entry for entry in workflows if isinstance(entry, dict)]

    def _workflow_id_to_path(self, workflows: list[dict[str, Any]]) -> dict[int, str]:
        mapping: dict[int, str] = {}
        for workflow in workflows:
            workflow_id = workflow.get("id")
            path = self._optional_string(workflow.get("path"))
            if isinstance(workflow_id, int) and path:
                mapping[workflow_id] = path
        return mapping

    def _workflow_path_to_name(self, workflows: list[dict[str, Any]]) -> dict[str, str]:
        mapping: dict[str, str] = {}
        for workflow in workflows:
            path = self._optional_string(workflow.get("path"))
            name = self._optional_string(workflow.get("name"))
            if path and name:
                mapping[path] = name
        return mapping

    def _workflow_path_to_state(self, workflows: list[dict[str, Any]]) -> dict[str, str]:
        mapping: dict[str, str] = {}
        for workflow in workflows:
            path = self._optional_string(workflow.get("path"))
            state = self._optional_string(workflow.get("state"))
            if path and state:
                mapping[path] = state
        return mapping

    def _workflow_path_to_url(self, workflows: list[dict[str, Any]]) -> dict[str, str]:
        mapping: dict[str, str] = {}
        for workflow in workflows:
            path = self._optional_string(workflow.get("path"))
            url = self._optional_string(workflow.get("html_url"))
            if path and url:
                mapping[path] = url
        return mapping

    def _read_workflow_text(self, workflow_path: str, ref: str) -> str:
        return self._github_api_client.request_text(
            endpoint=(
                f"/repos/{self._config.repository}/contents/"
                f"{quote(workflow_path, safe='/')}?ref={quote(ref, safe='')}"
            ),
            field_args=["-H", "Accept: application/vnd.github.raw+json"],
        )

    def _workflow_contract(self, workflow_text: str) -> tuple[bool, list[str], list[str]]:
        parsed = yaml.load(workflow_text, Loader=yaml.BaseLoader) or {}
        if not isinstance(parsed, dict):
            raise GitHubAccessibilityPullRequestGateError(
                f"{self._config.target_workflow_path} did not deserialize to a YAML mapping."
            )

        on_payload = parsed.get("on")
        declares_pull_request = self._event_is_declared(on_payload, event_name="pull_request")

        jobs_payload = parsed.get("jobs")
        if not isinstance(jobs_payload, dict):
            return declares_pull_request, [], []

        job_names: list[str] = []
        step_names: list[str] = []
        for job_id, job_payload in jobs_payload.items():
            if not isinstance(job_payload, dict):
                continue
            job_name = self._optional_string(job_payload.get("name")) or str(job_id)
            job_names.append(job_name)
            raw_steps = job_payload.get("steps")
            if not isinstance(raw_steps, list):
                continue
            for step_payload in raw_steps:
                if not isinstance(step_payload, dict):
                    continue
                step_name = self._optional_string(step_payload.get("name"))
                if step_name:
                    step_names.append(step_name)
        return declares_pull_request, self._dedupe(job_names), self._dedupe(step_names)

    def _matched_accessibility_markers(self, text: str) -> list[str]:
        normalized = text.lower()
        matches = [
            marker
            for marker in self._config.expected_accessibility_markers
            if marker.lower() in normalized
        ]
        return self._dedupe(matches)

    def _has_accessibility_marker(self, values: list[str]) -> bool:
        return any(
            marker.lower() in value.lower()
            for marker in self._config.expected_accessibility_markers
            for value in values
        )

    def _workflow_declares_event(self, workflow_text: str, event_name: str) -> bool:
        parsed = yaml.load(workflow_text, Loader=yaml.BaseLoader) or {}
        if not isinstance(parsed, dict):
            return False
        return self._event_is_declared(parsed.get("on"), event_name=event_name)

    def _event_is_declared(self, on_payload: object, *, event_name: str) -> bool:
        if isinstance(on_payload, dict):
            return event_name in on_payload
        if isinstance(on_payload, list):
            return event_name in on_payload
        if isinstance(on_payload, str):
            return on_payload == event_name
        return False

    def _read_required_check_rules(
        self,
        workflow_path_to_name: dict[str, str],
    ) -> dict[str, object]:
        descriptions: list[str] = []
        contexts: list[str] = []
        workflow_paths: list[str] = []

        rules_payload = self._try_read_json_array(
            f"/repos/{self._config.repository}/rules/branches/{self._config.base_branch}"
        )
        if isinstance(rules_payload, list):
            for rule in rules_payload:
                if not isinstance(rule, dict):
                    continue
                rule_type = self._optional_string(rule.get("type")) or "unknown"
                parameters = rule.get("parameters")
                parameter_map = parameters if isinstance(parameters, dict) else {}
                if rule_type == "required_status_checks":
                    extracted = self._collect_required_status_check_contexts(parameter_map)
                    contexts.extend(extracted)
                    descriptions.append(
                        f"required_status_checks: {extracted or ['<none>']}"
                    )
                    continue
                if rule_type == "workflows":
                    extracted_paths = self._collect_required_workflow_paths(parameter_map)
                    workflow_paths.extend(extracted_paths)
                    extracted_names = [
                        workflow_path_to_name.get(path, path) for path in extracted_paths
                    ]
                    descriptions.append(f"workflows: {extracted_names or ['<none>']}")
                    continue
                descriptions.append(rule_type)

        branch_protection = self._try_read_json_object(
            f"/repos/{self._config.repository}/branches/{self._config.base_branch}/protection"
        )
        if isinstance(branch_protection, dict):
            required_status_checks = branch_protection.get("required_status_checks")
            if isinstance(required_status_checks, dict):
                extracted_contexts = self._collect_required_status_check_contexts(
                    required_status_checks
                )
                if extracted_contexts:
                    contexts.extend(extracted_contexts)
                    descriptions.append(
                        "branch_protection.required_status_checks: "
                        f"{extracted_contexts}"
                    )

        unique_contexts = self._dedupe(contexts)
        unique_workflow_paths = self._dedupe(workflow_paths)
        workflow_names = self._dedupe(
            [workflow_path_to_name.get(path, path) for path in unique_workflow_paths]
        )
        return {
            "descriptions": self._dedupe(descriptions),
            "contexts": unique_contexts,
            "workflow_paths": unique_workflow_paths,
            "workflow_names": workflow_names,
        }

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
                if isinstance(entry, str):
                    if entry.strip():
                        values.append(entry.strip())
                    continue
                if not isinstance(entry, dict):
                    continue
                context = self._optional_string(entry.get("context"))
                if context:
                    values.append(context)
                    continue
                name = self._optional_string(entry.get("name"))
                if name:
                    values.append(name)
        return self._dedupe(values)

    def _collect_required_workflow_paths(self, payload: dict[str, Any]) -> list[str]:
        workflows = payload.get("workflows")
        if not isinstance(workflows, list):
            return []
        values: list[str] = []
        for entry in workflows:
            if not isinstance(entry, dict):
                continue
            path = self._optional_string(entry.get("path"))
            if path:
                values.append(path)
        return self._dedupe(values)

    def _default_branch(self, repository_info: dict[str, Any]) -> str:
        default_branch = self._optional_string(repository_info.get("default_branch"))
        if default_branch:
            return default_branch
        return self._config.base_branch

    def _read_json_object(self, endpoint: str) -> dict[str, Any]:
        payload = json.loads(self._github_api_client.request_text(endpoint=endpoint))
        if not isinstance(payload, dict):
            raise GitHubAccessibilityPullRequestGateError(
                f"GitHub API endpoint {endpoint} did not return a JSON object."
            )
        return payload

    def _try_read_json_object(self, endpoint: str) -> dict[str, Any] | None:
        try:
            payload = json.loads(self._github_api_client.request_text(endpoint=endpoint))
        except (GitHubApiClientError, json.JSONDecodeError):
            return None
        return payload if isinstance(payload, dict) else None

    def _try_read_json_array(self, endpoint: str) -> list[Any] | None:
        try:
            payload = json.loads(self._github_api_client.request_text(endpoint=endpoint))
        except (GitHubApiClientError, json.JSONDecodeError):
            return None
        return payload if isinstance(payload, list) else None

    def _optional_string(self, value: object) -> str | None:
        if not isinstance(value, str):
            return None
        stripped = value.strip()
        return stripped or None

    def _dedupe(self, values: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            if value in seen:
                continue
            seen.add(value)
            result.append(value)
        return result
