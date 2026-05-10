from __future__ import annotations

import base64
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from typing import Any
from urllib.parse import quote

from testing.core.config.actionlint_workflow_gate_config import (
    ActionlintWorkflowGateConfig,
)
from testing.core.interfaces.actionlint_workflow_gate_probe import (
    ActionlintWorkflowGateObservation,
)
from testing.core.interfaces.github_api_client import (
    GitHubApiClient,
    GitHubApiClientError,
)


class ActionlintWorkflowGateError(RuntimeError):
    pass


class ActionlintWorkflowGateProbeService:
    def __init__(
        self,
        config: ActionlintWorkflowGateConfig,
        *,
        github_api_client: GitHubApiClient,
    ) -> None:
        self._config = config
        self._github_api_client = github_api_client

    def validate(self) -> ActionlintWorkflowGateObservation:
        repository_info = self._read_json_object(f"/repos/{self._config.repository}")
        default_branch = self._default_branch(repository_info)
        workflows = self._list_workflows()
        workflow_id_to_path = self._workflow_id_to_path(workflows)
        default_branch_workflow_paths = list(workflow_id_to_path.values())
        workflows_declaring_actionlint = self._workflows_declaring_actionlint(
            default_branch,
            default_branch_workflow_paths,
        )
        branch_observation = self._push_invalid_workflow_and_observe_runs(
            workflow_id_to_path,
            set(workflows_declaring_actionlint),
        )

        return ActionlintWorkflowGateObservation(
            repository=self._config.repository,
            default_branch=default_branch,
            target_workflow_name=self._config.target_workflow_name,
            target_workflow_path=self._config.target_workflow_path,
            target_workflow_present_on_default_branch=(
                self._config.target_workflow_path in default_branch_workflow_paths
            ),
            default_branch_workflow_paths=default_branch_workflow_paths,
            workflows_declaring_actionlint=workflows_declaring_actionlint,
            pushed_branch=str(branch_observation["pushed_branch"]),
            pushed_commit_sha=str(branch_observation["pushed_commit_sha"]),
            branch_actions_page_url=str(branch_observation["branch_actions_page_url"]),
            observed_branch_run_count=int(branch_observation["observed_branch_run_count"]),
            observed_branch_run_names=list(branch_observation["observed_branch_run_names"]),
            observed_branch_run_paths=list(branch_observation["observed_branch_run_paths"]),
            observed_branch_run_urls=list(branch_observation["observed_branch_run_urls"]),
            observed_branch_run_statuses=list(
                branch_observation["observed_branch_run_statuses"]
            ),
            observed_branch_run_conclusions=list(
                branch_observation["observed_branch_run_conclusions"]
            ),
            observed_job_names=list(branch_observation["observed_job_names"]),
            observed_step_names=list(branch_observation["observed_step_names"]),
            actionlint_run_name=self._optional_string(
                branch_observation.get("actionlint_run_name")
            ),
            actionlint_run_path=self._optional_string(
                branch_observation.get("actionlint_run_path")
            ),
            actionlint_run_url=self._optional_string(
                branch_observation.get("actionlint_run_url")
            ),
            actionlint_run_status=self._optional_string(
                branch_observation.get("actionlint_run_status")
            ),
            actionlint_run_conclusion=self._optional_string(
                branch_observation.get("actionlint_run_conclusion")
            ),
            actionlint_job_name=self._optional_string(
                branch_observation.get("actionlint_job_name")
            ),
            actionlint_step_name=self._optional_string(
                branch_observation.get("actionlint_step_name")
            ),
            actionlint_step_conclusion=self._optional_string(
                branch_observation.get("actionlint_step_conclusion")
            ),
            mutated_line_preview=str(branch_observation["mutated_line_preview"]),
            cleanup_deleted_branch=bool(branch_observation["cleanup_deleted_branch"]),
        )

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

    def _push_invalid_workflow_and_observe_runs(
        self,
        workflow_id_to_path: dict[int, str],
        actionlint_workflow_paths: set[str],
    ) -> dict[str, object]:
        temp_repository_root = Path(tempfile.mkdtemp(prefix="ts251-"))
        branch_name = self._unique_branch_name()
        branch_pushed = False
        cleanup_deleted_branch = False

        pushed_commit_sha = ""
        branch_actions_page_url = self._branch_actions_page_url(branch_name)
        mutated_line_preview = self._config.mutation_replacement_text
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

            target_workflow = temp_repository_root / self._config.target_workflow_path
            original_workflow_text = target_workflow.read_text(encoding="utf-8")
            mutated_workflow_text = original_workflow_text.replace(
                self._config.mutation_search_text,
                self._config.mutation_replacement_text,
                1,
            )
            if mutated_workflow_text == original_workflow_text:
                raise ActionlintWorkflowGateError(
                    "TS-251 could not apply the configured workflow mutation.\n"
                    f"Target file: {target_workflow}\n"
                    f"Expected to replace: {self._config.mutation_search_text}"
                )
            target_workflow.write_text(mutated_workflow_text, encoding="utf-8")

            self._run_command(
                ["git", "add", self._config.target_workflow_path],
                cwd=temp_repository_root,
            )
            self._run_command(
                ["git", "commit", "-m", self._config.commit_message],
                cwd=temp_repository_root,
            )
            pushed_commit_sha = self._run_command(
                ["git", "rev-parse", "HEAD"],
                cwd=temp_repository_root,
            ).stdout.strip()
            started_at = time.time()
            self._run_command(
                ["git", "push", "--set-upstream", "origin", branch_name],
                cwd=temp_repository_root,
            )
            branch_pushed = True

            branch_run_observation = self._wait_for_branch_runs(
                branch_name,
                started_at,
                workflow_id_to_path,
                actionlint_workflow_paths,
            )
            observation = {
                "pushed_branch": branch_name,
                "pushed_commit_sha": pushed_commit_sha,
                "branch_actions_page_url": branch_actions_page_url,
                "mutated_line_preview": mutated_line_preview,
                "cleanup_deleted_branch": False,
                **branch_run_observation,
            }
        finally:
            if branch_pushed:
                cleanup_deleted_branch = self._delete_branch(
                    branch_name,
                    cwd=temp_repository_root,
                )
            if temp_repository_root.exists():
                shutil.rmtree(temp_repository_root)
            if observation is not None:
                observation["cleanup_deleted_branch"] = cleanup_deleted_branch

        if observation is None:
            raise ActionlintWorkflowGateError(
                "TS-251 did not produce a disposable branch observation."
            )
        return observation

    def _wait_for_branch_runs(
        self,
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

        while time.time() < deadline:
            latest_runs = self._list_branch_runs(branch_name, started_at)
            candidate = self._find_actionlint_run(
                latest_runs,
                workflow_id_to_path,
                actionlint_workflow_paths,
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
                if actionlint_run_status == "completed":
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
        }

    def _find_actionlint_run(
        self,
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
            run_matches_marker = (
                marker in run_name.lower()
                or (
                    isinstance(workflow_path, str)
                    and (
                        workflow_path in actionlint_workflow_paths
                        or marker in workflow_path.lower()
                    )
                )
                or matched_step_name is not None
            )
            if not run_matches_marker:
                continue

            return {
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
            f"?branch={quote(branch_name, safe='')}&per_page=50"
        )
        workflow_runs = payload.get("workflow_runs")
        if not isinstance(workflow_runs, list):
            raise ActionlintWorkflowGateError(
                "GitHub Actions runs response did not return a workflow_runs list."
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
            raise ActionlintWorkflowGateError(
                "GitHub Actions workflows response did not return a workflows list."
            )
        return [workflow for workflow in workflows if isinstance(workflow, dict)]

    def _read_jobs(self, run_id: int) -> list[dict[str, Any]]:
        payload = self._read_json_object(
            f"/repos/{self._config.repository}/actions/runs/{run_id}/jobs?per_page=50"
        )
        jobs = payload.get("jobs")
        if not isinstance(jobs, list):
            raise ActionlintWorkflowGateError(
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
            raise ActionlintWorkflowGateError(
                "GitHub did not return base64 workflow contents for "
                f"{workflow_path}."
            )
        return base64.b64decode(encoded_content.replace("\n", "")).decode("utf-8")

    def _delete_branch(self, branch_name: str, *, cwd: Path) -> bool:
        try:
            self._run_command(
                ["git", "push", "origin", "--delete", branch_name],
                cwd=cwd,
            )
        except ActionlintWorkflowGateError:
            return False
        return True

    def _origin_clone_url(self) -> str:
        return f"https://github.com/{self._config.repository}.git"

    def _branch_actions_page_url(self, branch_name: str) -> str:
        branch_query = quote(f"branch:{branch_name}", safe="")
        return f"https://github.com/{self._config.repository}/actions?query={branch_query}"

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
            raise ActionlintWorkflowGateError(
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
            raise ActionlintWorkflowGateError(
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
            raise ActionlintWorkflowGateError(str(error)) from error
        return json.loads(response_text)

    def _workflow_id_to_path(self, workflows: list[dict[str, Any]]) -> dict[int, str]:
        mapping: dict[int, str] = {}
        for workflow in workflows:
            workflow_id = workflow.get("id")
            workflow_path = workflow.get("path")
            if isinstance(workflow_id, int) and isinstance(workflow_path, str):
                mapping[workflow_id] = workflow_path
        return mapping

    def _unique_branch_name(self) -> str:
        timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"{self._config.branch_prefix}-{timestamp}"

    @staticmethod
    def _default_branch(repository_info: dict[str, Any]) -> str:
        default_branch = repository_info.get("default_branch")
        if isinstance(default_branch, str) and default_branch.strip():
            return default_branch.strip()
        return "main"

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
    def _run_names(runs: list[dict[str, Any]]) -> list[str]:
        names: list[str] = []
        for run in runs:
            name = run.get("name")
            if isinstance(name, str) and name:
                names.append(name)
        return names

    @staticmethod
    def _run_paths(
        runs: list[dict[str, Any]],
        workflow_id_to_path: dict[int, str],
    ) -> list[str]:
        paths: list[str] = []
        for run in runs:
            workflow_id = run.get("workflow_id")
            if not isinstance(workflow_id, int):
                continue
            workflow_path = workflow_id_to_path.get(workflow_id)
            if isinstance(workflow_path, str) and workflow_path:
                paths.append(workflow_path)
        return paths

    @staticmethod
    def _run_urls(runs: list[dict[str, Any]]) -> list[str]:
        urls: list[str] = []
        for run in runs:
            url = run.get("html_url")
            if isinstance(url, str) and url:
                urls.append(url)
        return urls

    @staticmethod
    def _run_statuses(runs: list[dict[str, Any]]) -> list[str]:
        statuses: list[str] = []
        for run in runs:
            status = run.get("status")
            statuses.append(status.strip() if isinstance(status, str) else "")
        return statuses

    @staticmethod
    def _run_conclusions(runs: list[dict[str, Any]]) -> list[str]:
        conclusions: list[str] = []
        for run in runs:
            conclusion = run.get("conclusion")
            conclusions.append(conclusion.strip() if isinstance(conclusion, str) else "")
        return conclusions

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
