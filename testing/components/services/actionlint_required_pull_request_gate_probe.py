from __future__ import annotations

import base64
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
from typing import Any
from urllib.parse import quote

from testing.core.config.actionlint_required_pull_request_gate_config import (
    ActionlintRequiredPullRequestGateConfig,
)
from testing.core.interfaces.actionlint_required_pull_request_gate_probe import (
    ActionlintRequiredPullRequestGateObservation,
)
from testing.core.interfaces.github_api_client import (
    GitHubApiClient,
    GitHubApiClientError,
)


class ActionlintRequiredPullRequestGateError(RuntimeError):
    pass


class ActionlintRequiredPullRequestGateProbeService:
    _CONTRIBUTOR_VISIBLE_PULL_REQUEST_EVENTS = (
        "pull_request",
        "pull_request_target",
    )

    def __init__(
        self,
        config: ActionlintRequiredPullRequestGateConfig,
        *,
        github_api_client: GitHubApiClient,
    ) -> None:
        self._config = config
        self._github_api_client = github_api_client

    def validate(self) -> ActionlintRequiredPullRequestGateObservation:
        repository_info = self._read_json_object(f"/repos/{self._config.repository}")
        default_branch = self._default_branch(repository_info)
        workflows = self._list_workflows()
        workflow_id_to_path = self._workflow_id_to_path(workflows)
        workflow_path_to_name = self._workflow_path_to_name(workflows)
        default_branch_workflow_paths = list(workflow_id_to_path.values())
        workflows_declaring_actionlint = self._workflows_declaring_actionlint(
            default_branch,
            default_branch_workflow_paths,
        )
        required_rules = self._read_required_check_rules(workflow_path_to_name)
        pull_request_observation = self._create_and_observe_pull_request(
            workflow_id_to_path=workflow_id_to_path,
            actionlint_workflow_paths=set(workflows_declaring_actionlint),
        )

        return ActionlintRequiredPullRequestGateObservation(
            repository=self._config.repository,
            default_branch=default_branch,
            target_workflow_name=self._config.target_workflow_name,
            target_workflow_path=self._config.target_workflow_path,
            target_workflow_present_on_default_branch=(
                self._config.target_workflow_path in default_branch_workflow_paths
            ),
            default_branch_workflow_paths=default_branch_workflow_paths,
            workflows_declaring_actionlint=workflows_declaring_actionlint,
            required_rule_descriptions=list(required_rules["descriptions"]),
            required_check_contexts=list(required_rules["contexts"]),
            required_check_workflow_paths=list(required_rules["workflow_paths"]),
            required_check_workflow_names=list(required_rules["workflow_names"]),
            repository_declares_actionlint_required_check=bool(
                required_rules["actionlint_required"]
            ),
            pull_request_number=int(pull_request_observation["pull_request_number"]),
            pull_request_url=str(pull_request_observation["pull_request_url"]),
            pull_request_checks_url=str(pull_request_observation["pull_request_checks_url"]),
            pull_request_head_branch=str(
                pull_request_observation["pull_request_head_branch"]
            ),
            pull_request_state=self._optional_string(
                pull_request_observation.get("pull_request_state")
            ),
            pull_request_mergeable_state=self._optional_string(
                pull_request_observation.get("pull_request_mergeable_state")
            ),
            pull_request_mergeable=self._optional_string(
                pull_request_observation.get("pull_request_mergeable")
            ),
            pull_request_merge_state_status=self._optional_string(
                pull_request_observation.get("pull_request_merge_state_status")
            ),
            pull_request_status_state=self._optional_string(
                pull_request_observation.get("pull_request_status_state")
            ),
            observed_status_check_names=list(
                pull_request_observation["observed_status_check_names"]
            ),
            observed_status_check_workflow_names=list(
                pull_request_observation["observed_status_check_workflow_names"]
            ),
            actionlint_status_check_name=self._optional_string(
                pull_request_observation.get("actionlint_status_check_name")
            ),
            actionlint_status_check_workflow_name=self._optional_string(
                pull_request_observation.get("actionlint_status_check_workflow_name")
            ),
            actionlint_status_check_status=self._optional_string(
                pull_request_observation.get("actionlint_status_check_status")
            ),
            actionlint_status_check_conclusion=self._optional_string(
                pull_request_observation.get("actionlint_status_check_conclusion")
            ),
            actionlint_status_check_url=self._optional_string(
                pull_request_observation.get("actionlint_status_check_url")
            ),
            observed_branch_run_count=int(
                pull_request_observation["observed_branch_run_count"]
            ),
            observed_branch_run_names=list(
                pull_request_observation["observed_branch_run_names"]
            ),
            observed_branch_run_paths=list(
                pull_request_observation["observed_branch_run_paths"]
            ),
            observed_branch_run_urls=list(
                pull_request_observation["observed_branch_run_urls"]
            ),
            observed_branch_run_statuses=list(
                pull_request_observation["observed_branch_run_statuses"]
            ),
            observed_branch_run_conclusions=list(
                pull_request_observation["observed_branch_run_conclusions"]
            ),
            observed_job_names=list(pull_request_observation["observed_job_names"]),
            observed_step_names=list(pull_request_observation["observed_step_names"]),
            actionlint_run_name=self._optional_string(
                pull_request_observation.get("actionlint_run_name")
            ),
            actionlint_run_path=self._optional_string(
                pull_request_observation.get("actionlint_run_path")
            ),
            actionlint_run_url=self._optional_string(
                pull_request_observation.get("actionlint_run_url")
            ),
            actionlint_run_status=self._optional_string(
                pull_request_observation.get("actionlint_run_status")
            ),
            actionlint_run_conclusion=self._optional_string(
                pull_request_observation.get("actionlint_run_conclusion")
            ),
            actionlint_job_name=self._optional_string(
                pull_request_observation.get("actionlint_job_name")
            ),
            actionlint_step_name=self._optional_string(
                pull_request_observation.get("actionlint_step_name")
            ),
            actionlint_step_conclusion=self._optional_string(
                pull_request_observation.get("actionlint_step_conclusion")
            ),
            actionlint_log_excerpt=self._optional_string(
                pull_request_observation.get("actionlint_log_excerpt")
            ),
            mutated_line_preview=str(pull_request_observation["mutated_line_preview"]),
            cleanup_closed_pull_request=bool(
                pull_request_observation["cleanup_closed_pull_request"]
            ),
            cleanup_deleted_branch=bool(
                pull_request_observation["cleanup_deleted_branch"]
            ),
        )

    def _read_required_check_rules(
        self,
        workflow_path_to_name: dict[str, str],
    ) -> dict[str, object]:
        rules_payload = self._try_read_json_object(
            f"/repos/{self._config.repository}/rules/branches/{self._config.base_branch}"
        )
        descriptions: list[str] = []
        contexts: list[str] = []
        workflow_paths: list[str] = []

        if isinstance(rules_payload, list):
            for rule in rules_payload:
                if not isinstance(rule, dict):
                    continue
                rule_type = self._optional_string(rule.get("type")) or "unknown"
                parameters = rule.get("parameters")
                parameter_map = parameters if isinstance(parameters, dict) else {}
                if rule_type == "required_status_checks":
                    extracted = self._collect_required_status_check_contexts(
                        parameter_map
                    )
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
        marker = self._config.expected_actionlint_marker.lower()
        actionlint_required = any(marker in entry.lower() for entry in unique_contexts) or any(
            marker in entry.lower()
            for entry in [*unique_workflow_paths, *workflow_names, *descriptions]
        )

        return {
            "descriptions": self._dedupe(descriptions),
            "contexts": unique_contexts,
            "workflow_paths": unique_workflow_paths,
            "workflow_names": workflow_names,
            "actionlint_required": actionlint_required,
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
                if isinstance(entry, str) and entry.strip():
                    values.append(entry.strip())
                    continue
                if not isinstance(entry, dict):
                    continue
                context = self._optional_string(entry.get("context"))
                if context is not None:
                    values.append(context)
                    continue
                name = self._optional_string(entry.get("name"))
                if name is not None:
                    values.append(name)
        return values

    def _collect_required_workflow_paths(
        self,
        payload: dict[str, Any],
    ) -> list[str]:
        values: list[str] = []
        raw_workflows = payload.get("workflows")
        if not isinstance(raw_workflows, list):
            return values
        for workflow in raw_workflows:
            if not isinstance(workflow, dict):
                continue
            path = self._optional_string(workflow.get("path"))
            if path is not None:
                values.append(path)
        return values

    def _workflows_declaring_actionlint(
        self,
        default_branch: str,
        workflow_paths: list[str],
    ) -> list[str]:
        marker = self._config.expected_actionlint_marker.lower()
        matches: list[str] = []
        for workflow_path in workflow_paths:
            if not workflow_path.startswith(".github/workflows/"):
                continue
            workflow_text = self._read_workflow_text(workflow_path, default_branch)
            if marker in workflow_text.lower():
                matches.append(workflow_path)
        return matches

    def _create_and_observe_pull_request(
        self,
        *,
        workflow_id_to_path: dict[int, str],
        actionlint_workflow_paths: set[str],
    ) -> dict[str, object]:
        temp_repository_root = Path(tempfile.mkdtemp(prefix="ts257-"))
        pull_request_number: int | None = None
        branch_name = self._unique_branch_name()
        branch_pushed = False
        cleanup_closed_pull_request = False
        cleanup_deleted_branch = False
        observation: dict[str, object] | None = None

        try:
            self._run_command(["gh", "auth", "setup-git"], cwd=None)
            self._run_command(
                [
                    "git",
                    "clone",
                    "--quiet",
                    self._origin_clone_url(),
                    str(temp_repository_root),
                ],
                cwd=None,
            )
            self._run_command(
                [
                    "git",
                    "checkout",
                    "-b",
                    branch_name,
                    f"origin/{self._config.base_branch}",
                ],
                cwd=temp_repository_root,
            )
            self._run_command(
                ["git", "config", "user.name", "ai-teammate"],
                cwd=temp_repository_root,
            )
            self._run_command(
                ["git", "config", "user.email", "agent.ai.native@gmail.com"],
                cwd=temp_repository_root,
            )

            mutated_line_preview = self._apply_workflow_change(temp_repository_root)
            self._run_command(
                ["git", "add", self._config.target_workflow_path],
                cwd=temp_repository_root,
            )
            self._run_command(
                ["git", "commit", "-m", self._config.commit_message],
                cwd=temp_repository_root,
            )
            started_at = time.time()
            self._run_command(
                ["git", "push", "--set-upstream", "origin", branch_name],
                cwd=temp_repository_root,
            )
            branch_pushed = True

            pr_url = self._run_command(
                [
                    "gh",
                    "pr",
                    "create",
                    "--repo",
                    self._config.repository,
                    "--base",
                    self._config.base_branch,
                    "--head",
                    branch_name,
                    "--title",
                    self._config.pull_request_title,
                    "--body",
                    self._config.pull_request_body,
                ],
                cwd=temp_repository_root,
            ).stdout.strip()
            pull_request_number = self._extract_pull_request_number(pr_url)

            run_observation = self._wait_for_pull_request_runs(
                branch_name=branch_name,
                started_at=started_at,
                workflow_id_to_path=workflow_id_to_path,
                actionlint_workflow_paths=actionlint_workflow_paths,
            )
            state_observation = self._wait_for_pull_request_surface(pull_request_number)

            observation = {
                "pull_request_number": pull_request_number,
                "pull_request_url": pr_url,
                "pull_request_checks_url": f"{pr_url}/checks",
                "pull_request_head_branch": branch_name,
                "mutated_line_preview": mutated_line_preview,
                "cleanup_closed_pull_request": False,
                "cleanup_deleted_branch": False,
                **run_observation,
                **state_observation,
            }
        finally:
            if pull_request_number is not None:
                cleanup_closed_pull_request = self._close_pull_request(
                    pull_request_number
                )
            if branch_pushed:
                cleanup_deleted_branch = self._delete_branch(
                    branch_name,
                    cwd=temp_repository_root,
                )
            if temp_repository_root.exists():
                shutil.rmtree(temp_repository_root)
            if observation is not None:
                observation["cleanup_closed_pull_request"] = cleanup_closed_pull_request
                observation["cleanup_deleted_branch"] = cleanup_deleted_branch

        if observation is None:
            raise ActionlintRequiredPullRequestGateError(
                "TS-257 did not produce a disposable pull request observation."
            )
        return observation

    def _apply_workflow_change(self, temp_repository_root: Path) -> str:
        target_workflow = temp_repository_root / self._config.target_workflow_path
        original_workflow_text = target_workflow.read_text(encoding="utf-8")
        mutated_workflow_text = original_workflow_text.replace(
            self._config.mutation_search_text,
            self._config.mutation_replacement_text,
            1,
        )
        if mutated_workflow_text == original_workflow_text:
            raise ActionlintRequiredPullRequestGateError(
                "TS-257 could not apply the configured workflow mutation.\n"
                f"Target file: {target_workflow}\n"
                f"Expected to replace: {self._config.mutation_search_text}"
            )
        target_workflow.write_text(mutated_workflow_text, encoding="utf-8")
        return self._config.mutation_replacement_text

    def _wait_for_pull_request_runs(
        self,
        *,
        branch_name: str,
        started_at: float,
        workflow_id_to_path: dict[int, str],
        actionlint_workflow_paths: set[str],
    ) -> dict[str, object]:
        deadline = time.time() + self._config.run_timeout_seconds
        latest_runs: list[dict[str, Any]] = []
        latest_jobs: list[dict[str, Any]] = []
        actionlint_run_name: str | None = None
        actionlint_run_path: str | None = None
        actionlint_run_url: str | None = None
        actionlint_run_status: str | None = None
        actionlint_run_conclusion: str | None = None
        actionlint_job_name: str | None = None
        actionlint_step_name: str | None = None
        actionlint_step_conclusion: str | None = None
        actionlint_run_id: int | None = None
        actionlint_log_excerpt: str | None = None

        while time.time() < deadline:
            latest_runs = self._list_branch_runs(branch_name, started_at)
            candidate = self._find_actionlint_run(
                runs=latest_runs,
                workflow_id_to_path=workflow_id_to_path,
                actionlint_workflow_paths=actionlint_workflow_paths,
            )
            if candidate is not None:
                latest_jobs = candidate["jobs"]
                actionlint_run_name = candidate["run_name"]
                actionlint_run_path = candidate["run_path"]
                actionlint_run_url = candidate["run_url"]
                actionlint_run_status = candidate["run_status"]
                actionlint_run_conclusion = candidate["run_conclusion"]
                actionlint_job_name = candidate["job_name"]
                actionlint_step_name = candidate["step_name"]
                actionlint_step_conclusion = candidate["step_conclusion"]
                actionlint_run_id = int(candidate["run_id"])
                if actionlint_run_status == "completed":
                    actionlint_log_excerpt = self._extract_actionlint_log_excerpt(
                        self._read_actionlint_run_log(actionlint_run_id)
                    )
                    break
            time.sleep(self._config.poll_interval_seconds)

        return {
            "observed_branch_run_count": len(latest_runs),
            "observed_branch_run_names": self._run_names(latest_runs),
            "observed_branch_run_paths": self._run_paths(latest_runs, workflow_id_to_path),
            "observed_branch_run_urls": self._run_urls(latest_runs),
            "observed_branch_run_statuses": self._run_statuses(latest_runs),
            "observed_branch_run_conclusions": self._run_conclusions(latest_runs),
            "observed_job_names": self._job_names(latest_jobs),
            "observed_step_names": self._step_names(latest_jobs),
            "actionlint_run_name": actionlint_run_name,
            "actionlint_run_path": actionlint_run_path,
            "actionlint_run_url": actionlint_run_url,
            "actionlint_run_status": actionlint_run_status,
            "actionlint_run_conclusion": actionlint_run_conclusion,
            "actionlint_job_name": actionlint_job_name,
            "actionlint_step_name": actionlint_step_name,
            "actionlint_step_conclusion": actionlint_step_conclusion,
            "actionlint_log_excerpt": actionlint_log_excerpt,
        }

    def _wait_for_pull_request_surface(
        self,
        pull_request_number: int,
    ) -> dict[str, object]:
        deadline = time.time() + self._config.pull_request_timeout_seconds
        latest_state = {
            "pull_request_state": None,
            "pull_request_mergeable_state": None,
            "pull_request_status_state": None,
            "pull_request_mergeable": None,
            "pull_request_merge_state_status": None,
            "observed_status_check_names": [],
            "observed_status_check_workflow_names": [],
            "actionlint_status_check_name": None,
            "actionlint_status_check_workflow_name": None,
            "actionlint_status_check_status": None,
            "actionlint_status_check_conclusion": None,
            "actionlint_status_check_url": None,
        }

        while time.time() < deadline:
            pull_request = self._read_json_object(
                f"/repos/{self._config.repository}/pulls/{pull_request_number}"
            )
            head_sha = self._optional_string(((pull_request.get("head") or {}).get("sha")))
            mergeable_state = self._optional_string(pull_request.get("mergeable_state"))
            status_state = self._read_check_runs_state(head_sha) if head_sha else None
            surface = self._read_pull_request_status_surface(pull_request_number)
            actionlint_check = self._find_actionlint_status_check(surface["status_checks"])
            latest_state = {
                "pull_request_state": self._optional_string(pull_request.get("state")),
                "pull_request_mergeable_state": mergeable_state,
                "pull_request_status_state": status_state,
                "pull_request_mergeable": surface["mergeable"],
                "pull_request_merge_state_status": surface["merge_state_status"],
                "observed_status_check_names": surface["status_check_names"],
                "observed_status_check_workflow_names": surface[
                    "status_check_workflow_names"
                ],
                "actionlint_status_check_name": None
                if actionlint_check is None
                else actionlint_check["name"],
                "actionlint_status_check_workflow_name": None
                if actionlint_check is None
                else actionlint_check["workflow_name"],
                "actionlint_status_check_status": None
                if actionlint_check is None
                else actionlint_check["status"],
                "actionlint_status_check_conclusion": None
                if actionlint_check is None
                else actionlint_check["conclusion"],
                "actionlint_status_check_url": None
                if actionlint_check is None
                else actionlint_check["details_url"],
            }
            if (
                mergeable_state
                and mergeable_state != "unknown"
                and status_state
                and status_state != "pending"
                and surface["merge_state_status"] not in (None, "UNKNOWN")
                and actionlint_check is not None
                and self._status_check_is_terminal(actionlint_check)
            ):
                return latest_state
            time.sleep(self._config.poll_interval_seconds)

        return latest_state

    def _read_pull_request_status_surface(
        self,
        pull_request_number: int,
    ) -> dict[str, object]:
        payload = json.loads(
            self._run_command(
                [
                    "gh",
                    "pr",
                    "view",
                    str(pull_request_number),
                    "--repo",
                    self._config.repository,
                    "--json",
                    "number,mergeable,mergeStateStatus,statusCheckRollup,reviewDecision,isDraft,headRefName",
                ],
                cwd=None,
            ).stdout
        )
        if not isinstance(payload, dict):
            raise ActionlintRequiredPullRequestGateError(
                f"TS-257 expected gh pr view to return an object: {payload!r}"
            )
        raw_checks = payload.get("statusCheckRollup")
        normalized_checks = self._normalize_status_checks(raw_checks)
        return {
            "mergeable": self._optional_string(payload.get("mergeable")),
            "merge_state_status": self._optional_string(payload.get("mergeStateStatus")),
            "status_checks": normalized_checks,
            "status_check_names": self._dedupe(
                [
                    check["name"]
                    for check in normalized_checks
                    if isinstance(check.get("name"), str)
                ]
            ),
            "status_check_workflow_names": self._dedupe(
                [
                    check["workflow_name"]
                    for check in normalized_checks
                    if isinstance(check.get("workflow_name"), str)
                ]
            ),
        }

    def _normalize_status_checks(self, raw_checks: object) -> list[dict[str, str | None]]:
        if not isinstance(raw_checks, list):
            return []
        normalized: list[dict[str, str | None]] = []
        for entry in raw_checks:
            if not isinstance(entry, dict):
                continue
            typename = self._optional_string(entry.get("__typename"))
            if typename == "CheckRun":
                normalized.append(
                    {
                        "name": self._optional_string(entry.get("name")),
                        "workflow_name": self._optional_string(entry.get("workflowName")),
                        "status": self._normalize_case(entry.get("status")),
                        "conclusion": self._normalize_case(entry.get("conclusion")),
                        "details_url": self._optional_string(entry.get("detailsUrl")),
                    }
                )
                continue
            if typename == "StatusContext":
                normalized.append(
                    {
                        "name": self._optional_string(entry.get("context")),
                        "workflow_name": None,
                        "status": None,
                        "conclusion": self._normalize_case(entry.get("state")),
                        "details_url": self._optional_string(entry.get("targetUrl")),
                    }
                )
        return normalized

    def _find_actionlint_status_check(
        self,
        status_checks: list[dict[str, str | None]],
    ) -> dict[str, str | None] | None:
        marker = self._config.expected_actionlint_marker.lower()
        for check in status_checks:
            name = (check.get("name") or "").lower()
            workflow_name = (check.get("workflow_name") or "").lower()
            if marker in name or marker in workflow_name:
                return check
        return None

    @staticmethod
    def _status_check_is_terminal(check: dict[str, str | None]) -> bool:
        status = check.get("status")
        conclusion = check.get("conclusion")
        if status is None:
            return conclusion is not None
        return status == "completed" and conclusion is not None

    def _find_actionlint_run(
        self,
        *,
        runs: list[dict[str, Any]],
        workflow_id_to_path: dict[int, str],
        actionlint_workflow_paths: set[str],
    ) -> dict[str, object] | None:
        marker = self._config.expected_actionlint_marker.lower()
        for run in runs:
            run_id = run.get("id")
            if not isinstance(run_id, int):
                continue
            run_name = self._optional_string(run.get("name")) or ""
            workflow_path = workflow_id_to_path.get(int(run.get("workflow_id", 0)))
            jobs: list[dict[str, Any]] = []
            if self._optional_string(run.get("status")) == "completed":
                jobs = self._read_jobs(run_id)
            matched_step_name, matched_job_name, matched_step_conclusion = (
                self._find_actionlint_step(jobs)
            )
            if not (
                marker in run_name.lower()
                or (
                    isinstance(workflow_path, str)
                    and (
                        workflow_path in actionlint_workflow_paths
                        or marker in workflow_path.lower()
                    )
                )
                or matched_step_name is not None
            ):
                continue
            return {
                "run_id": run_id,
                "jobs": jobs,
                "run_name": run_name or None,
                "run_path": workflow_path,
                "run_url": self._optional_string(run.get("html_url")),
                "run_status": self._optional_string(run.get("status")),
                "run_conclusion": self._optional_string(run.get("conclusion")),
                "job_name": matched_job_name,
                "step_name": matched_step_name,
                "step_conclusion": matched_step_conclusion,
            }
        return None

    def _find_actionlint_step(
        self,
        jobs: list[dict[str, Any]],
    ) -> tuple[str | None, str | None, str | None]:
        marker = self._config.expected_actionlint_marker.lower()
        for job in jobs:
            job_name = self._optional_string(job.get("name"))
            if job_name is not None and marker in job_name.lower():
                return job_name, job_name, self._optional_string(job.get("conclusion"))
            steps = job.get("steps")
            if not isinstance(steps, list):
                continue
            for step in steps:
                if not isinstance(step, dict):
                    continue
                step_name = self._optional_string(step.get("name"))
                if step_name is not None and marker in step_name.lower():
                    return (
                        step_name,
                        job_name,
                        self._optional_string(step.get("conclusion")),
                    )
        return None, None, None

    def _list_branch_runs(
        self,
        branch_name: str,
        started_at: float,
    ) -> list[dict[str, Any]]:
        payload = self._read_json_object(
            f"/repos/{self._config.repository}/actions/runs"
            f"?branch={quote(branch_name, safe='')}&per_page=100"
        )
        workflow_runs = payload.get("workflow_runs")
        if not isinstance(workflow_runs, list):
            raise ActionlintRequiredPullRequestGateError(
                "GitHub Actions runs response did not return a workflow_runs list."
            )

        started_floor = started_at - max(self._config.poll_interval_seconds, 1)
        matching_runs: list[dict[str, Any]] = []
        for run in workflow_runs:
            if not isinstance(run, dict):
                continue
            if self._optional_string(run.get("head_branch")) != branch_name:
                continue
            if not self._is_contributor_visible_pull_request_event(
                self._optional_string(run.get("event"))
            ):
                continue
            created_at = self._run_created_at_epoch(run)
            if created_at is None or created_at < started_floor:
                continue
            matching_runs.append(run)

        return sorted(
            matching_runs,
            key=lambda run: (
                self._run_created_at_epoch(run) or 0.0,
                int(run.get("id", 0)),
            ),
            reverse=True,
        )

    def _list_workflows(self) -> list[dict[str, Any]]:
        payload = self._read_json_object(f"/repos/{self._config.repository}/actions/workflows")
        workflows = payload.get("workflows")
        if not isinstance(workflows, list):
            raise ActionlintRequiredPullRequestGateError(
                "GitHub Actions workflows response did not return a workflows list."
            )
        return [workflow for workflow in workflows if isinstance(workflow, dict)]

    def _read_jobs(self, run_id: int) -> list[dict[str, Any]]:
        payload = self._read_json_object(
            f"/repos/{self._config.repository}/actions/runs/{run_id}/jobs?per_page=100"
        )
        jobs = payload.get("jobs")
        if not isinstance(jobs, list):
            raise ActionlintRequiredPullRequestGateError(
                f"GitHub Actions jobs response for run {run_id} did not return a list."
            )
        return [job for job in jobs if isinstance(job, dict)]

    def _read_workflow_text(self, workflow_path: str, default_branch: str) -> str:
        path = quote(workflow_path, safe="/")
        payload = self._read_json_object(
            f"/repos/{self._config.repository}/contents/{path}?ref="
            f"{quote(default_branch, safe='')}"
        )
        encoded_content = payload.get("content")
        if not isinstance(encoded_content, str) or not encoded_content.strip():
            raise ActionlintRequiredPullRequestGateError(
                "GitHub did not return base64 workflow contents for "
                f"{workflow_path}."
            )
        return base64.b64decode(encoded_content.replace("\n", "")).decode("utf-8")

    def _read_check_runs_state(self, head_sha: str) -> str | None:
        payload = self._read_json_object(
            f"/repos/{self._config.repository}/commits/{head_sha}/check-runs?per_page=100"
        )
        check_runs = payload.get("check_runs")
        if isinstance(check_runs, list) and check_runs:
            relevant_runs = [
                run
                for run in check_runs
                if isinstance(run, dict)
                and any(
                    self._config.expected_actionlint_marker.lower()
                    in value.lower()
                    for value in (
                        self._optional_string(run.get("name")) or "",
                        self._optional_string(((run.get("app") or {}).get("name"))) or "",
                    )
                )
            ]
            runs_to_consider = relevant_runs or [
                run for run in check_runs if isinstance(run, dict)
            ]
            if any(
                self._optional_string(run.get("status")) != "completed"
                for run in runs_to_consider
            ):
                return "pending"
            failure_conclusions = {"failure", "cancelled", "timed_out", "action_required"}
            if any(
                self._optional_string(run.get("conclusion")) in failure_conclusions
                for run in runs_to_consider
            ):
                return "failure"
            success_conclusions = {"success", "neutral", "skipped"}
            if all(
                self._optional_string(run.get("conclusion")) in success_conclusions
                for run in runs_to_consider
            ):
                return "success"
        payload = self._read_json_object(
            f"/repos/{self._config.repository}/commits/{head_sha}/status"
        )
        return self._optional_string(payload.get("state"))

    def _close_pull_request(self, pull_request_number: int) -> bool:
        try:
            self._read_json_object(
                f"/repos/{self._config.repository}/pulls/{pull_request_number}",
                method="PATCH",
                field_args=["-f", "state=closed"],
            )
        except ActionlintRequiredPullRequestGateError:
            return False
        return True

    def _delete_branch(self, branch_name: str, *, cwd: Path) -> bool:
        try:
            self._run_command(
                ["git", "push", "origin", "--delete", branch_name],
                cwd=cwd,
            )
        except ActionlintRequiredPullRequestGateError:
            return False
        return True

    def _origin_clone_url(self) -> str:
        return f"https://github.com/{self._config.repository}.git"

    def _read_actionlint_run_log(self, run_id: int) -> str:
        return self._run_command(
            [
                "gh",
                "run",
                "view",
                str(run_id),
                "--repo",
                self._config.repository,
                "--log",
            ],
            cwd=None,
        ).stdout

    def _extract_actionlint_log_excerpt(self, log_text: str) -> str:
        lines = [line.rstrip() for line in log_text.splitlines()]
        if not lines:
            return ""

        primary_markers = [
            self._config.target_workflow_path.lower(),
            self._config.target_workflow_name.lower(),
        ]
        fallback_markers = (
            "##[error]",
            " error ",
            "\terror\t",
            "unable to resolve action",
            "failed",
        )

        match_index: int | None = None
        for index, line in enumerate(lines):
            lowered_line = line.lower()
            if any(marker and marker in lowered_line for marker in primary_markers):
                match_index = index
                break

        if match_index is None:
            for index, line in enumerate(lines):
                lowered_line = line.lower()
                if any(marker in lowered_line for marker in fallback_markers):
                    match_index = index
                    break

        if match_index is None:
            for index, line in enumerate(lines):
                lowered_line = line.lower()
                if self._config.expected_actionlint_marker.lower() in lowered_line:
                    match_index = index
                    break

        if match_index is None:
            excerpt_lines = lines[-40:]
        else:
            if any(marker in lines[match_index].lower() for marker in fallback_markers):
                excerpt_lines = lines[max(0, match_index - 3) : min(len(lines), match_index + 8)]
            else:
                excerpt_lines = lines[max(0, match_index - 1) : min(len(lines), match_index + 15)]

        excerpt = "\n".join(excerpt_lines).strip()
        if len(excerpt) <= 4000:
            return excerpt
        return excerpt[:4000].rstrip()

    def _extract_pull_request_number(self, pull_request_url: str) -> int:
        match = re.search(r"/pull/(\d+)$", pull_request_url.strip())
        if match is None:
            raise ActionlintRequiredPullRequestGateError(
                "gh pr create did not return a pull request URL ending in /pull/<number>: "
                f"{pull_request_url}"
            )
        return int(match.group(1))

    def _run_command(
        self,
        command: list[str],
        *,
        cwd: Path | None,
    ) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment.setdefault("GH_PAGER", "cat")
        environment.setdefault("GIT_TERMINAL_PROMPT", "0")
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise ActionlintRequiredPullRequestGateError(
                f"Command failed with exit code {completed.returncode}: {' '.join(command)}\n"
                f"stdout:\n{completed.stdout}\n"
                f"stderr:\n{completed.stderr}"
            )
        return completed

    def _read_json_object(
        self,
        endpoint: str,
        *,
        method: str = "GET",
        field_args: list[str] | None = None,
    ) -> dict[str, Any]:
        try:
            response = self._github_api_client.request_text(
                endpoint=endpoint,
                method=method,
                field_args=field_args,
            )
        except GitHubApiClientError as error:
            raise ActionlintRequiredPullRequestGateError(str(error)) from error
        payload = json.loads(response)
        if not isinstance(payload, dict):
            raise ActionlintRequiredPullRequestGateError(
                f"GitHub API endpoint {endpoint} returned {type(payload).__name__}, expected object."
            )
        return payload

    def _try_read_json_object(
        self,
        endpoint: str,
    ) -> dict[str, Any] | list[Any] | None:
        try:
            response = self._github_api_client.request_text(endpoint=endpoint)
        except GitHubApiClientError as error:
            if "HTTP 404" in str(error):
                return None
            raise ActionlintRequiredPullRequestGateError(str(error)) from error
        payload = json.loads(response)
        if isinstance(payload, (dict, list)):
            return payload
        raise ActionlintRequiredPullRequestGateError(
            f"GitHub API endpoint {endpoint} returned {type(payload).__name__}, expected object or list."
        )

    @staticmethod
    def _default_branch(repository_info: dict[str, Any]) -> str:
        default_branch = repository_info.get("default_branch")
        if not isinstance(default_branch, str) or not default_branch.strip():
            raise ActionlintRequiredPullRequestGateError(
                "Repository response did not include a default_branch."
            )
        return default_branch

    @staticmethod
    def _workflow_id_to_path(workflows: list[dict[str, Any]]) -> dict[int, str]:
        result: dict[int, str] = {}
        for workflow in workflows:
            workflow_id = workflow.get("id")
            path = workflow.get("path")
            if isinstance(workflow_id, int) and isinstance(path, str):
                result[workflow_id] = path
        return result

    @staticmethod
    def _workflow_path_to_name(workflows: list[dict[str, Any]]) -> dict[str, str]:
        result: dict[str, str] = {}
        for workflow in workflows:
            path = workflow.get("path")
            name = workflow.get("name")
            if isinstance(path, str) and isinstance(name, str) and name.strip():
                result[path] = name.strip()
        return result

    @staticmethod
    def _optional_string(value: object) -> str | None:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return None

    @staticmethod
    def _normalize_case(value: object) -> str | None:
        if not isinstance(value, str):
            return None
        stripped = value.strip()
        if not stripped:
            return None
        return stripped.lower()

    @staticmethod
    def _run_created_at_epoch(run: dict[str, Any]) -> float | None:
        created_at = run.get("created_at")
        if not isinstance(created_at, str):
            return None
        try:
            return datetime.fromisoformat(created_at.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return None

    def _unique_branch_name(self) -> str:
        stamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"{self._config.branch_prefix}-{stamp}"

    def _is_contributor_visible_pull_request_event(self, value: str | None) -> bool:
        return value in self._CONTRIBUTOR_VISIBLE_PULL_REQUEST_EVENTS

    @staticmethod
    def _run_names(runs: list[dict[str, Any]]) -> list[str]:
        return [
            name
            for name in (
                ActionlintRequiredPullRequestGateProbeService._optional_string(
                    run.get("name")
                )
                for run in runs
            )
            if name is not None
        ]

    @staticmethod
    def _run_paths(
        runs: list[dict[str, Any]],
        workflow_id_to_path: dict[int, str],
    ) -> list[str]:
        paths: list[str] = []
        for run in runs:
            workflow_id = run.get("workflow_id")
            if isinstance(workflow_id, int):
                path = workflow_id_to_path.get(workflow_id)
                if path is not None:
                    paths.append(path)
        return paths

    @staticmethod
    def _run_urls(runs: list[dict[str, Any]]) -> list[str]:
        return [
            url
            for url in (
                ActionlintRequiredPullRequestGateProbeService._optional_string(
                    run.get("html_url")
                )
                for run in runs
            )
            if url is not None
        ]

    @staticmethod
    def _run_statuses(runs: list[dict[str, Any]]) -> list[str]:
        return [
            status
            for status in (
                ActionlintRequiredPullRequestGateProbeService._optional_string(
                    run.get("status")
                )
                for run in runs
            )
            if status is not None
        ]

    @staticmethod
    def _run_conclusions(runs: list[dict[str, Any]]) -> list[str]:
        return [
            conclusion
            for conclusion in (
                ActionlintRequiredPullRequestGateProbeService._optional_string(
                    run.get("conclusion")
                )
                for run in runs
            )
            if conclusion is not None
        ]

    @staticmethod
    def _job_names(jobs: list[dict[str, Any]]) -> list[str]:
        return [
            name
            for name in (
                ActionlintRequiredPullRequestGateProbeService._optional_string(
                    job.get("name")
                )
                for job in jobs
            )
            if name is not None
        ]

    @staticmethod
    def _step_names(jobs: list[dict[str, Any]]) -> list[str]:
        names: list[str] = []
        for job in jobs:
            steps = job.get("steps")
            if not isinstance(steps, list):
                continue
            for step in steps:
                if not isinstance(step, dict):
                    continue
                name = ActionlintRequiredPullRequestGateProbeService._optional_string(
                    step.get("name")
                )
                if name is not None:
                    names.append(name)
        return names

    @staticmethod
    def _dedupe(values: list[str]) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for value in values:
            if value in seen:
                continue
            seen.add(value)
            ordered.append(value)
        return ordered
