from __future__ import annotations

import base64
import json
import re
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
        workflow = self._select_workflow()
        workflow_id = workflow.get("id")
        if not isinstance(workflow_id, int):
            raise ThemeTokenCiError(
                "TS-131 could not resolve a numeric workflow ID for "
                f"{self._config.workflow_path}."
            )

        workflow_text = self._read_workflow_text(default_branch)
        run, jobs, step, matched_job_name = self._select_recent_pull_request_run(
            workflow_id,
        )
        observed_job_names = self._job_names(jobs)
        observed_step_names = self._step_names(jobs)

        return ThemeTokenCiObservation(
            repository=self._config.repository,
            workflow_id=workflow_id,
            workflow_name=str(workflow.get("name", "")),
            workflow_path=self._config.workflow_path,
            workflow_html_url=str(workflow.get("html_url", "")),
            default_branch=default_branch,
            workflow_text=workflow_text,
            latest_pull_request_run_id=int(run["id"]),
            latest_pull_request_run_url=str(run.get("html_url", "")),
            latest_pull_request_run_event=str(run.get("event", "")),
            latest_pull_request_run_status=self._optional_string(run.get("status")),
            latest_pull_request_run_conclusion=self._optional_string(
                run.get("conclusion"),
            ),
            latest_pull_request_head_branch=self._optional_string(run.get("head_branch")),
            latest_pull_request_display_title=self._optional_string(
                run.get("display_title"),
            ),
            latest_pull_request_created_at=self._optional_string(run.get("created_at")),
            observed_job_names=observed_job_names,
            observed_step_names=observed_step_names,
            theme_token_job_name=matched_job_name,
            theme_token_step_status=self._optional_string(step.get("status"))
            if step
            else None,
            theme_token_step_conclusion=self._optional_string(step.get("conclusion"))
            if step
            else None,
            workflow_declares_pull_request_trigger=bool(
                re.search(r"(?m)^\s*pull_request:\s*$", workflow_text),
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
            path = workflow.get("path")
            if isinstance(path, str) and path == self._config.workflow_path:
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

    def _select_recent_pull_request_run(
        self,
        workflow_id: int,
    ) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any] | None, str | None]:
        payload = self._read_json_object(
            f"/repos/{self._config.repository}/actions/workflows/{workflow_id}/runs"
            f"?event=pull_request&status=completed&per_page={self._config.recent_run_limit}"
        )
        workflow_runs = payload.get("workflow_runs")
        if not isinstance(workflow_runs, list) or not workflow_runs:
            raise ThemeTokenCiError(
                "TS-131 could not find any completed pull_request runs for "
                f"{self._config.workflow_path} in {self._config.repository}."
            )

        fallback: tuple[
            dict[str, Any],
            list[dict[str, Any]],
            dict[str, Any] | None,
            str | None,
        ] | None = None
        for run in workflow_runs:
            if not isinstance(run, dict):
                continue
            if run.get("conclusion") == "cancelled":
                continue

            run_id = run.get("id")
            if not isinstance(run_id, int):
                continue

            jobs = self._read_jobs(run_id)
            step, matched_job_name = self._find_theme_token_step(jobs)
            candidate = (run, jobs, step, matched_job_name)
            if fallback is None:
                fallback = candidate
            if step is None:
                continue
            if step.get("conclusion") not in (None, "skipped"):
                return candidate

        if fallback is not None:
            return fallback

        raise ThemeTokenCiError(
            "TS-131 did not find a usable completed pull_request workflow run "
            f"for {self._config.workflow_path}."
        )

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
            if str(job.get("name", "")).strip() == self._config.workflow_job_name
        ]
        jobs_to_search = preferred_jobs or jobs

        for job in jobs_to_search:
            steps = job.get("steps")
            if not isinstance(steps, list):
                continue
            for step in steps:
                if not isinstance(step, dict):
                    continue
                if str(step.get("name", "")).strip() == self._config.workflow_step_name:
                    return step, self._optional_string(job.get("name"))
        return None, None

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

    def _read_json_object(self, endpoint: str) -> dict[str, Any]:
        payload = self._read_json(endpoint)
        if not isinstance(payload, dict):
            raise ThemeTokenCiError(
                f"Expected a JSON object from gh api {endpoint}, got {type(payload)}."
            )
        return payload

    def _read_json(self, endpoint: str) -> object:
        try:
            response_text = self._github_api_client.request_text(endpoint=endpoint)
        except GitHubApiClientError as error:
            raise ThemeTokenCiError(str(error)) from error
        return json.loads(response_text)

    @staticmethod
    def _optional_string(value: object) -> str | None:
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None
