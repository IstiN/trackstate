from __future__ import annotations

import base64
import json
import re
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

from testing.core.config.theme_token_ci_config import ThemeTokenCiConfig
from testing.core.interfaces.github_api_client import (
    GitHubApiClient,
    GitHubApiClientError,
)
from testing.core.interfaces.theme_token_ci_probe import ThemeTokenCiObservation


class ThemeTokenCiError(RuntimeError):
    pass


class ThemeTokenCiWorkflowProbe:
    _PULL_REQUEST_TRIGGER_PATTERN = re.compile(r"(?m)^\s*pull_request:\s*$")

    def __init__(
        self,
        config: ThemeTokenCiConfig,
        *,
        github_api_client: GitHubApiClient,
    ) -> None:
        self._config = config
        self._github_api_client = github_api_client

    def validate(self) -> ThemeTokenCiObservation:
        repository_info = self._read_json_object(f"/repos/{self._config.repository}")
        default_branch = self._default_branch(repository_info)
        default_branch_sha = self._branch_sha(default_branch)
        workflow = self._select_workflow()
        workflow_id = workflow.get("id")
        if not isinstance(workflow_id, int):
            raise ThemeTokenCiError(
                "TS-131 could not resolve a numeric workflow ID for "
                f"{self._config.workflow_path}."
            )

        workflow_text = self._read_workflow_text(default_branch)
        branch_name = self._probe_branch_name()
        pull_request_number: int | None = None

        try:
            self._create_branch(branch_name, default_branch_sha)
            probe_commit_sha = self._create_probe_commit(branch_name)
            pull_request = self._open_pull_request(
                branch_name=branch_name,
                base_branch=default_branch,
            )
            pull_request_number = self._require_int(
                pull_request,
                key="number",
                context="pull request creation response",
            )
            pull_request_url = self._require_non_empty_string(
                pull_request,
                key="html_url",
                context="pull request creation response",
            )
            completed_run = self._wait_for_pull_request_workflow_completion(
                workflow_id=workflow_id,
                branch_name=branch_name,
            )
            jobs = self._read_jobs(self._require_int(completed_run, "id", "workflow run"))
            theme_token_step, matched_job_name = self._find_theme_token_step(jobs)
            pull_request_state = self._observe_pull_request_state(pull_request_number)
        except Exception as error:
            for cleanup_error in self._cleanup(
                branch_name=branch_name,
                pull_request_number=pull_request_number,
            ):
                error.add_note(cleanup_error)
            raise

        cleanup_errors = self._cleanup(
            branch_name=branch_name,
            pull_request_number=pull_request_number,
        )
        if cleanup_errors:
            raise ThemeTokenCiError("\n".join(cleanup_errors))

        return ThemeTokenCiObservation(
            repository=self._config.repository,
            workflow_id=workflow_id,
            workflow_name=self._optional_string(workflow.get("name")) or "",
            workflow_path=self._config.workflow_path,
            workflow_html_url=self._optional_string(workflow.get("html_url")) or "",
            default_branch=default_branch,
            workflow_text=workflow_text,
            probe_branch_name=branch_name,
            probe_commit_sha=probe_commit_sha,
            probe_file_path=self._config.probe_file_path,
            probe_pull_request_number=pull_request_number,
            probe_pull_request_url=pull_request_url,
            probe_pull_request_mergeable_state=pull_request_state["mergeable_state"],
            probe_pull_request_merge_state_status=pull_request_state[
                "merge_state_status"
            ],
            probe_pull_request_status_check_rollup_state=pull_request_state[
                "status_check_rollup_state"
            ],
            probe_pull_request_head_sha=pull_request_state["head_sha"],
            workflow_run_id=self._require_int(completed_run, "id", "workflow run"),
            workflow_run_url=self._optional_string(completed_run.get("html_url")) or "",
            workflow_run_event=self._optional_string(completed_run.get("event")) or "",
            workflow_run_status=self._optional_string(completed_run.get("status")),
            workflow_run_conclusion=self._optional_string(completed_run.get("conclusion")),
            observed_job_names=self._job_names(jobs),
            observed_step_names=self._step_names(jobs),
            theme_token_job_name=matched_job_name,
            theme_token_step_status=self._optional_string(
                theme_token_step.get("status")
            )
            if theme_token_step
            else None,
            theme_token_step_conclusion=self._optional_string(
                theme_token_step.get("conclusion")
            )
            if theme_token_step
            else None,
            workflow_declares_pull_request_trigger=bool(
                self._PULL_REQUEST_TRIGGER_PATTERN.search(workflow_text),
            ),
            workflow_declares_gate_step=(
                f"- name: {self._config.workflow_step_name}" in workflow_text
            ),
            workflow_declares_gate_command=self._config.gate_command in workflow_text,
        )

    def _select_workflow(self) -> dict[str, Any]:
        payload = self._read_json_object(f"/repos/{self._config.repository}/actions/workflows")
        workflows = payload.get("workflows")
        if not isinstance(workflows, list):
            raise ThemeTokenCiError(
                "GitHub Actions workflows response did not return a workflows list."
            )

        for workflow in workflows:
            if not isinstance(workflow, dict):
                continue
            if workflow.get("path") == self._config.workflow_path:
                return workflow

        raise ThemeTokenCiError(
            "TS-131 could not find the configured workflow path "
            f"{self._config.workflow_path} in {self._config.repository}."
        )

    def _read_workflow_text(self, default_branch: str) -> str:
        path = quote(self._config.workflow_path, safe="/")
        payload = self._read_json_object(
            f"/repos/{self._config.repository}/contents/{path}?ref="
            f"{quote(default_branch, safe='')}"
        )
        encoded_content = payload.get("content")
        if not isinstance(encoded_content, str) or not encoded_content.strip():
            raise ThemeTokenCiError(
                "GitHub did not return base64 workflow contents for "
                f"{self._config.workflow_path}."
            )
        return base64.b64decode(encoded_content.replace("\n", "")).decode("utf-8")

    def _branch_sha(self, branch_name: str) -> str:
        payload = self._read_json_object(
            f"/repos/{self._config.repository}/branches/{quote(branch_name, safe='')}"
        )
        commit = payload.get("commit")
        if not isinstance(commit, dict):
            raise ThemeTokenCiError(
                f"Repository {self._config.repository} branch {branch_name} did not "
                "return a commit payload."
            )
        sha = commit.get("sha")
        if not isinstance(sha, str) or not sha.strip():
            raise ThemeTokenCiError(
                f"Repository {self._config.repository} branch {branch_name} did not "
                "return a commit SHA."
            )
        return sha.strip()

    def _create_branch(self, branch_name: str, sha: str) -> None:
        self._gh_text(
            f"/repos/{self._config.repository}/git/refs",
            method="POST",
            stdin_json={
                "ref": f"refs/heads/{branch_name}",
                "sha": sha,
            },
        )

    def _create_probe_commit(self, branch_name: str) -> str:
        payload = self._read_json_object(
            f"/repos/{self._config.repository}/contents/"
            f"{quote(self._config.probe_file_path, safe='/')}",
            method="PUT",
            stdin_json={
                "message": f"test: add TS-131 disposable probe ({branch_name})",
                "content": base64.b64encode(
                    self._probe_source().encode("utf-8")
                ).decode("ascii"),
                "branch": branch_name,
            },
        )
        commit = payload.get("commit")
        if not isinstance(commit, dict):
            raise ThemeTokenCiError(
                "GitHub did not return the commit payload after creating the TS-131 "
                "probe file."
            )
        sha = commit.get("sha")
        if not isinstance(sha, str) or not sha.strip():
            raise ThemeTokenCiError(
                "GitHub did not return the commit SHA after creating the TS-131 "
                "probe file."
            )
        return sha.strip()

    def _open_pull_request(
        self,
        *,
        branch_name: str,
        base_branch: str,
    ) -> dict[str, Any]:
        return self._read_json_object(
            f"/repos/{self._config.repository}/pulls",
            method="POST",
            stdin_json={
                "title": f"{self._config.pull_request_title_prefix} {branch_name}",
                "head": branch_name,
                "base": base_branch,
                "body": (
                    "Disposable TS-131 automation probe.\n\n"
                    "This PR intentionally adds a hardcoded Flutter color so the "
                    "theme-token CI gate can be observed failing on a real "
                    "pull_request workflow run."
                ),
            },
        )

    def _wait_for_pull_request_workflow_completion(
        self,
        *,
        workflow_id: int,
        branch_name: str,
    ) -> dict[str, Any]:
        deadline = time.time() + self._config.workflow_run_timeout_seconds
        latest_detail: dict[str, Any] | None = None
        while time.time() < deadline:
            run = self._latest_pull_request_run(workflow_id, branch_name)
            if run is None:
                time.sleep(self._config.poll_interval_seconds)
                continue

            run_id = run.get("id")
            if not isinstance(run_id, int):
                time.sleep(self._config.poll_interval_seconds)
                continue

            latest_detail = self._read_json_object(
                f"/repos/{self._config.repository}/actions/runs/{run_id}"
            )
            if latest_detail.get("status") != "completed":
                time.sleep(self._config.poll_interval_seconds)
                continue
            if latest_detail.get("conclusion") == "cancelled":
                time.sleep(self._config.poll_interval_seconds)
                continue
            return latest_detail

        if latest_detail is not None:
            raise ThemeTokenCiError(
                "The TS-131 disposable PR workflow run did not reach a non-cancelled "
                "completed state within "
                f"{self._config.workflow_run_timeout_seconds} seconds. "
                f"Last observed run {latest_detail.get('id')} had status="
                f"{latest_detail.get('status')} and conclusion="
                f"{latest_detail.get('conclusion')}."
            )

        raise ThemeTokenCiError(
            "No pull_request workflow run appeared for disposable branch "
            f"{branch_name} within {self._config.workflow_run_timeout_seconds} "
            "seconds."
        )

    def _latest_pull_request_run(
        self,
        workflow_id: int,
        branch_name: str,
    ) -> dict[str, Any] | None:
        payload = self._read_json_object(
            f"/repos/{self._config.repository}/actions/workflows/{workflow_id}/runs"
            f"?event=pull_request&branch={quote(branch_name, safe='')}"
            f"&per_page={self._config.recent_run_limit}"
        )
        runs = payload.get("workflow_runs")
        if not isinstance(runs, list):
            raise ThemeTokenCiError("GitHub Actions runs response did not return a list.")

        matching_runs = [
            run
            for run in runs
            if isinstance(run, dict) and run.get("head_branch") == branch_name
        ]
        if not matching_runs:
            return None
        return max(
            matching_runs,
            key=lambda run: (
                self._run_created_at_epoch(run) or 0.0,
                int(run.get("id", 0)),
            ),
        )

    def _run_created_at_epoch(self, run: dict[str, Any]) -> float | None:
        created_at = run.get("created_at")
        if not isinstance(created_at, str) or not created_at:
            return None
        try:
            return datetime.fromisoformat(created_at.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return None

    def _read_jobs(self, run_id: int) -> list[dict[str, Any]]:
        payload = self._read_json_object(
            f"/repos/{self._config.repository}/actions/runs/{run_id}/jobs?per_page=20"
        )
        jobs = payload.get("jobs")
        if not isinstance(jobs, list):
            raise ThemeTokenCiError(
                f"GitHub Actions jobs response for run {run_id} did not return a list."
            )
        return [job for job in jobs if isinstance(job, dict)]

    def _find_theme_token_step(
        self,
        jobs: list[dict[str, Any]],
    ) -> tuple[dict[str, Any] | None, str | None]:
        preferred_jobs = [
            job
            for job in jobs
            if self._optional_string(job.get("name")) == self._config.workflow_job_name
        ]
        jobs_to_search = preferred_jobs or jobs

        for job in jobs_to_search:
            steps = job.get("steps")
            if not isinstance(steps, list):
                continue
            for step in steps:
                if not isinstance(step, dict):
                    continue
                if self._optional_string(step.get("name")) == self._config.workflow_step_name:
                    return step, self._optional_string(job.get("name"))
        return None, None

    def _observe_pull_request_state(
        self,
        pull_request_number: int,
    ) -> dict[str, str | None]:
        deadline = time.time() + self._config.pull_request_state_timeout_seconds
        latest_state = {
            "mergeable_state": None,
            "merge_state_status": None,
            "status_check_rollup_state": None,
            "head_sha": None,
        }
        while time.time() < deadline:
            rest_pull_request = self._read_json_object(
                f"/repos/{self._config.repository}/pulls/{pull_request_number}"
            )
            graphql_pull_request = self._read_pull_request_graphql(pull_request_number)
            latest_state = {
                "mergeable_state": self._optional_string(
                    rest_pull_request.get("mergeable_state")
                ),
                "merge_state_status": self._optional_string(
                    graphql_pull_request.get("mergeStateStatus")
                ),
                "status_check_rollup_state": self._status_check_rollup_state(
                    graphql_pull_request,
                ),
                "head_sha": self._optional_string(
                    ((graphql_pull_request.get("commits") or {}).get("nodes") or [{}])[
                        0
                    ]
                    .get("commit", {})
                    .get("oid")
                ),
            }
            if (
                latest_state["mergeable_state"] == "blocked"
                and latest_state["merge_state_status"] == "BLOCKED"
                and latest_state["status_check_rollup_state"] == "FAILURE"
            ):
                return latest_state
            time.sleep(self._config.poll_interval_seconds)
        return latest_state

    def _read_pull_request_graphql(self, pull_request_number: int) -> dict[str, Any]:
        owner, repo = self._config.repository.split("/", 1)
        payload = self._read_json_object(
            "graphql",
            method="POST",
            stdin_json={
                "query": """
query($owner: String!, $repo: String!, $number: Int!) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $number) {
      mergeStateStatus
      commits(last: 1) {
        nodes {
          commit {
            oid
            statusCheckRollup {
              state
            }
          }
        }
      }
    }
  }
}
""",
                "variables": {
                    "owner": owner,
                    "repo": repo,
                    "number": pull_request_number,
                },
            },
        )
        repository = (payload.get("data") or {}).get("repository")
        if not isinstance(repository, dict):
            raise ThemeTokenCiError("GraphQL repository payload was missing for TS-131.")
        pull_request = repository.get("pullRequest")
        if not isinstance(pull_request, dict):
            raise ThemeTokenCiError(
                f"GraphQL pullRequest payload was missing for PR #{pull_request_number}."
            )
        return pull_request

    def _status_check_rollup_state(
        self,
        pull_request: dict[str, Any],
    ) -> str | None:
        commits = pull_request.get("commits")
        if not isinstance(commits, dict):
            return None
        nodes = commits.get("nodes")
        if not isinstance(nodes, list) or not nodes:
            return None
        first_node = nodes[0]
        if not isinstance(first_node, dict):
            return None
        commit = first_node.get("commit")
        if not isinstance(commit, dict):
            return None
        status_check_rollup = commit.get("statusCheckRollup")
        if not isinstance(status_check_rollup, dict):
            return None
        return self._optional_string(status_check_rollup.get("state"))

    def _cleanup(
        self,
        *,
        branch_name: str,
        pull_request_number: int | None,
    ) -> list[str]:
        errors: list[str] = []
        if pull_request_number is not None:
            try:
                self._gh_text(
                    f"/repos/{self._config.repository}/pulls/{pull_request_number}",
                    method="PATCH",
                    stdin_json={"state": "closed"},
                )
            except ThemeTokenCiError as error:
                errors.append(
                    f"Cleanup failed while closing disposable PR #{pull_request_number}: "
                    f"{error}"
                )
        try:
            self._gh_text(
                f"/repos/{self._config.repository}/git/refs/heads/"
                f"{quote(branch_name, safe='')}",
                method="DELETE",
            )
        except ThemeTokenCiError as error:
            errors.append(
                f"Cleanup failed while deleting disposable branch {branch_name}: {error}"
            )
        return errors

    def _probe_branch_name(self) -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"{self._config.probe_branch_prefix}-{timestamp}"

    def _probe_source(self) -> str:
        return f"""import 'package:flutter/material.dart';

class Ts131PullRequestProbe extends StatelessWidget {{
  const Ts131PullRequestProbe({{super.key}});

  @override
  Widget build(BuildContext context) {{
    return const ColoredBox(
      color: {self._config.hardcoded_color_expression},
      child: SizedBox(width: 32, height: 32),
    );
  }}
}}
"""

    @staticmethod
    def _default_branch(repository_info: dict[str, Any]) -> str:
        default_branch = repository_info.get("default_branch")
        if isinstance(default_branch, str) and default_branch.strip():
            return default_branch.strip()
        return "main"

    @staticmethod
    def _job_names(jobs: list[dict[str, Any]]) -> list[str]:
        names: list[str] = []
        for job in jobs:
            name = job.get("name")
            if isinstance(name, str) and name:
                names.append(name)
        return names

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
                name = step.get("name")
                if isinstance(name, str) and name:
                    names.append(name)
        return names

    def _read_json_object(
        self,
        endpoint: str,
        *,
        method: str = "GET",
        stdin_json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = self._read_json(endpoint, method=method, stdin_json=stdin_json)
        if not isinstance(payload, dict):
            raise ThemeTokenCiError(
                f"Expected a JSON object from gh api {endpoint}, got {type(payload)}."
            )
        return payload

    def _read_json(
        self,
        endpoint: str,
        *,
        method: str = "GET",
        stdin_json: dict[str, Any] | None = None,
    ) -> object:
        response_text = self._gh_text(
            endpoint,
            method=method,
            stdin_json=stdin_json,
        )
        return json.loads(response_text or "{}")

    def _gh_text(
        self,
        endpoint: str,
        *,
        method: str = "GET",
        stdin_json: dict[str, Any] | None = None,
    ) -> str:
        try:
            return self._github_api_client.request_text(
                endpoint=endpoint,
                method=method,
                stdin_json=stdin_json,
            )
        except GitHubApiClientError as error:
            raise ThemeTokenCiError(str(error)) from error

    @staticmethod
    def _require_int(payload: dict[str, Any], key: str, context: str) -> int:
        value = payload.get(key)
        if not isinstance(value, int):
            raise ThemeTokenCiError(
                f"Expected integer {key} in {context}, got {type(value)}."
            )
        return value

    @staticmethod
    def _require_non_empty_string(
        payload: dict[str, Any],
        key: str,
        context: str,
    ) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ThemeTokenCiError(
                f"Expected non-empty string {key} in {context}, got {type(value)}."
            )
        return value.strip()

    @staticmethod
    def _optional_string(value: object) -> str | None:
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None
