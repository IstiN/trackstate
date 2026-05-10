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
        pull_request_observation = self._create_and_observe_pull_request(workflow_id)

        return ThemeTokenCiObservation(
            repository=self._config.repository,
            workflow_id=workflow_id,
            workflow_name=str(workflow.get("name", "")),
            workflow_path=self._config.workflow_path,
            workflow_html_url=str(workflow.get("html_url", "")),
            default_branch=default_branch,
            workflow_text=workflow_text,
            pull_request_number=int(pull_request_observation["pull_request_number"]),
            pull_request_url=str(pull_request_observation["pull_request_url"]),
            pull_request_head_branch=str(
                pull_request_observation["pull_request_head_branch"]
            ),
            pull_request_probe_path=str(
                pull_request_observation["pull_request_probe_path"]
            ),
            pull_request_state=self._optional_string(
                pull_request_observation.get("pull_request_state")
            ),
            pull_request_mergeable_state=self._optional_string(
                pull_request_observation.get("pull_request_mergeable_state")
            ),
            pull_request_head_sha=str(pull_request_observation["pull_request_head_sha"]),
            pull_request_status_state=self._optional_string(
                pull_request_observation.get("pull_request_status_state")
            ),
            latest_pull_request_run_id=int(
                pull_request_observation["latest_pull_request_run_id"]
            ),
            latest_pull_request_run_url=str(
                pull_request_observation["latest_pull_request_run_url"]
            ),
            latest_pull_request_run_event=str(
                pull_request_observation["latest_pull_request_run_event"]
            ),
            latest_pull_request_run_status=self._optional_string(
                pull_request_observation.get("latest_pull_request_run_status")
            ),
            latest_pull_request_run_conclusion=self._optional_string(
                pull_request_observation.get("latest_pull_request_run_conclusion")
            ),
            observed_job_names=list(pull_request_observation["observed_job_names"]),
            observed_step_names=list(pull_request_observation["observed_step_names"]),
            theme_token_job_name=self._optional_string(
                pull_request_observation.get("theme_token_job_name")
            ),
            theme_token_step_status=self._optional_string(
                pull_request_observation.get("theme_token_step_status")
            ),
            theme_token_step_conclusion=self._optional_string(
                pull_request_observation.get("theme_token_step_conclusion")
            ),
            workflow_declares_pull_request_trigger=bool(
                re.search(r"(?m)^\s*pull_request:\s*$", workflow_text),
            ),
            workflow_declares_gate_step=(
                f"- name: {self._config.workflow_step_name}" in workflow_text
            ),
            workflow_declares_gate_command=self._config.gate_command in workflow_text,
            cleanup_closed_pull_request=bool(
                pull_request_observation["cleanup_closed_pull_request"]
            ),
            cleanup_deleted_branch=bool(
                pull_request_observation["cleanup_deleted_branch"]
            ),
        )

    def _create_and_observe_pull_request(self, workflow_id: int) -> dict[str, object]:
        temp_repository_root = Path(tempfile.mkdtemp(prefix="ts131-"))
        pull_request_number: int | None = None
        branch_name = self._unique_branch_name()
        branch_pushed = False
        cleanup_closed_pull_request = False
        cleanup_deleted_branch = False
        pull_request_observation: dict[str, object] | None = None

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

            probe_file = temp_repository_root / self._config.probe_path
            probe_file.parent.mkdir(parents=True, exist_ok=True)
            probe_file.write_text(self._probe_source(), encoding="utf-8")

            self._run_command(
                ["git", "add", self._config.probe_path],
                cwd=temp_repository_root,
            )
            self._run_command(
                [
                    "git",
                    "commit",
                    "-m",
                    "TS-131 probe: verify non-tokenized color gate",
                ],
                cwd=temp_repository_root,
            )
            self._run_command(
                ["git", "push", "--set-upstream", "origin", branch_name],
                cwd=temp_repository_root,
            )
            branch_pushed = True

            started_at = time.time()
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
                    self._config.pr_title,
                    "--body",
                    self._config.pr_body,
                ],
                cwd=temp_repository_root,
            ).stdout.strip()
            pull_request_number = self._extract_pull_request_number(pr_url)

            run = self._wait_for_pull_request_run(
                workflow_id,
                branch_name,
                started_at,
            )
            jobs = self._read_jobs(int(run["id"]))
            step, matched_job_name = self._find_theme_token_step(jobs)

            pull_request = self._wait_for_pull_request_state(pull_request_number)
            head_sha = self._require_string(pull_request, "head_sha")

            pull_request_observation = {
                "pull_request_number": pull_request_number,
                "pull_request_url": pr_url,
                "pull_request_head_branch": branch_name,
                "pull_request_probe_path": self._config.probe_path,
                "pull_request_state": pull_request.get("state"),
                "pull_request_mergeable_state": pull_request.get("mergeable_state"),
                "pull_request_head_sha": head_sha,
                "pull_request_status_state": pull_request.get("status_state"),
                "latest_pull_request_run_id": int(run["id"]),
                "latest_pull_request_run_url": str(run.get("html_url", "")),
                "latest_pull_request_run_event": str(run.get("event", "")),
                "latest_pull_request_run_status": run.get("status"),
                "latest_pull_request_run_conclusion": run.get("conclusion"),
                "observed_job_names": self._job_names(jobs),
                "observed_step_names": self._step_names(jobs),
                "theme_token_job_name": matched_job_name,
                "theme_token_step_status": step.get("status") if step else None,
                "theme_token_step_conclusion": (
                    step.get("conclusion") if step else None
                ),
                "cleanup_closed_pull_request": False,
                "cleanup_deleted_branch": False,
            }
        finally:
            if pull_request_number is not None:
                cleanup_closed_pull_request = self._close_pull_request(
                    pull_request_number
                )
            if branch_pushed:
                cleanup_deleted_branch = self._delete_branch(branch_name)
            if temp_repository_root.exists():
                shutil.rmtree(temp_repository_root)

            if pull_request_observation is not None:
                pull_request_observation["cleanup_closed_pull_request"] = (
                    cleanup_closed_pull_request
                )
                pull_request_observation["cleanup_deleted_branch"] = (
                    cleanup_deleted_branch
                )

        if pull_request_observation is None:
            raise ThemeTokenCiError(
                "TS-131 did not produce a disposable pull request observation."
            )
        return pull_request_observation

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

    def _wait_for_pull_request_run(
        self,
        workflow_id: int,
        branch_name: str,
        started_at: float,
    ) -> dict[str, Any]:
        deadline = time.time() + self._config.run_timeout_seconds
        latest_run_detail: dict[str, Any] | None = None

        while time.time() < deadline:
            latest_run = self._latest_branch_run(workflow_id, branch_name, started_at)
            if latest_run is None:
                time.sleep(self._config.poll_interval_seconds)
                continue

            run_id = latest_run.get("id")
            if not isinstance(run_id, int):
                time.sleep(self._config.poll_interval_seconds)
                continue

            latest_run_detail = self._read_json_object(
                f"/repos/{self._config.repository}/actions/runs/{run_id}"
            )
            if latest_run_detail.get("status") != "completed":
                time.sleep(self._config.poll_interval_seconds * 2)
                continue
            if latest_run_detail.get("conclusion") == "cancelled":
                time.sleep(self._config.poll_interval_seconds)
                continue
            return latest_run_detail

        if latest_run_detail is not None:
            raise ThemeTokenCiError(
                "The disposable TS-131 pull_request run did not reach a non-cancelled "
                f"completed state within {self._config.run_timeout_seconds} seconds. "
                f"Last observed run {latest_run_detail.get('id')} had status="
                f"{latest_run_detail.get('status')} and conclusion="
                f"{latest_run_detail.get('conclusion')}."
            )

        raise ThemeTokenCiError(
            "TS-131 did not observe a new pull_request workflow run for branch "
            f"{branch_name} within {self._config.run_timeout_seconds} seconds."
        )

    def _latest_branch_run(
        self,
        workflow_id: int,
        branch_name: str,
        started_at: float,
    ) -> dict[str, Any] | None:
        payload = self._read_json_object(
            f"/repos/{self._config.repository}/actions/workflows/{workflow_id}/runs"
            f"?event=pull_request&branch={quote(branch_name, safe='')}&per_page=20"
        )
        workflow_runs = payload.get("workflow_runs")
        if not isinstance(workflow_runs, list):
            raise ThemeTokenCiError(
                "GitHub Actions workflow runs response did not return a workflow_runs list."
            )

        started_floor = started_at - max(self._config.poll_interval_seconds, 1)
        matching_runs: list[dict[str, Any]] = []
        for run in workflow_runs:
            if not isinstance(run, dict):
                continue
            if self._optional_string(run.get("head_branch")) != branch_name:
                continue
            created_at = self._run_created_at_epoch(run)
            if created_at is None or created_at < started_floor:
                continue
            matching_runs.append(run)

        if not matching_runs:
            return None

        return max(
            matching_runs,
            key=lambda run: (
                self._run_created_at_epoch(run) or 0.0,
                int(run.get("id", 0)),
            ),
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

    def _wait_for_pull_request_state(self, pull_request_number: int) -> dict[str, Any]:
        deadline = time.time() + self._config.pull_request_timeout_seconds
        latest_pull_request: dict[str, Any] | None = None

        while time.time() < deadline:
            latest_pull_request = self._read_pull_request(pull_request_number)
            mergeable_state = self._optional_string(
                latest_pull_request.get("mergeable_state")
            )
            head_sha = self._optional_string(
                ((latest_pull_request.get("head") or {}).get("sha"))
            )
            status_state = self._read_check_runs_state(head_sha) if head_sha else None
            if (
                mergeable_state
                and mergeable_state != "unknown"
                and head_sha
                and status_state
                and status_state != "pending"
            ):
                return {
                    "state": self._optional_string(latest_pull_request.get("state")),
                    "mergeable_state": mergeable_state,
                    "head_sha": head_sha,
                    "status_state": status_state,
                }
            time.sleep(self._config.poll_interval_seconds)

        raise ThemeTokenCiError(
            "TS-131 did not observe a stable pull request mergeable state within "
            f"{self._config.pull_request_timeout_seconds} seconds for PR "
            f"#{pull_request_number}. Last observed payload: {latest_pull_request}"
        )

    def _read_pull_request(self, pull_request_number: int) -> dict[str, Any]:
        return self._read_json_object(
            f"/repos/{self._config.repository}/pulls/{pull_request_number}"
        )

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
                and self._optional_string(run.get("name"))
                in {self._config.workflow_name, self._config.workflow_job_name}
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
        except ThemeTokenCiError:
            return False
        return True

    def _delete_branch(self, branch_name: str) -> bool:
        try:
            self._run_command(
                ["git", "push", "origin", "--delete", branch_name],
                cwd=None,
            )
        except ThemeTokenCiError:
            return False
        return True

    def _origin_clone_url(self) -> str:
        repository = self._config.repository
        return f"https://github.com/{repository}.git"

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
            command_text = " ".join(command)
            raise ThemeTokenCiError(
                f"{command_text} failed with exit code {completed.returncode}.\n"
                f"STDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
            )
        return completed

    def _read_json_object(
        self,
        endpoint: str,
        *,
        method: str = "GET",
        field_args: list[str] | None = None,
    ) -> dict[str, Any]:
        payload = self._read_json(endpoint, method=method, field_args=field_args)
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
        field_args: list[str] | None = None,
    ) -> object:
        try:
            response_text = self._github_api_client.request_text(
                endpoint=endpoint,
                method=method,
                field_args=field_args,
            )
        except GitHubApiClientError as error:
            raise ThemeTokenCiError(str(error)) from error
        return json.loads(response_text)

    def _extract_pull_request_number(self, pull_request_url: str) -> int:
        match = re.search(r"/pull/(\d+)$", pull_request_url.strip())
        if match is None:
            raise ThemeTokenCiError(
                "gh pr create did not return a pull request URL ending in /pull/<number>: "
                f"{pull_request_url}"
            )
        return int(match.group(1))

    def _unique_branch_name(self) -> str:
        timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"{self._config.branch_prefix}-{timestamp}"

    @staticmethod
    def _probe_source() -> str:
        return """import 'package:flutter/material.dart';

class Ts131PullRequestProbe extends StatelessWidget {
  const Ts131PullRequestProbe({super.key});

  @override
  Widget build(BuildContext context) {
    return const ColoredBox(
      color: Color(0xFF000000),
      child: SizedBox(width: 32, height: 32),
    );
  }
}
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

    @staticmethod
    def _optional_string(value: object) -> str | None:
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    @staticmethod
    def _run_created_at_epoch(run: dict[str, Any]) -> float | None:
        created_at = run.get("created_at")
        if not isinstance(created_at, str) or not created_at:
            return None
        try:
            return datetime.fromisoformat(created_at.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return None

    @staticmethod
    def _require_string(payload: dict[str, object], key: str) -> str:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        raise ThemeTokenCiError(f"TS-131 expected {key} to be a non-empty string.")
