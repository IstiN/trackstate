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

from testing.core.config.pull_request_release_dry_run_config import (
    PullRequestReleaseDryRunConfig,
)
from testing.core.interfaces.github_api_client import (
    GitHubApiClient,
    GitHubApiClientError,
)
from testing.core.interfaces.pull_request_release_dry_run_probe import (
    PullRequestReleaseDryRunObservation,
)


class PullRequestReleaseDryRunError(RuntimeError):
    pass


class PullRequestReleaseDryRunProbeService:
    _CONTRIBUTOR_VISIBLE_PULL_REQUEST_EVENTS = (
        "pull_request",
        "pull_request_target",
    )

    def __init__(
        self,
        config: PullRequestReleaseDryRunConfig,
        *,
        github_api_client: GitHubApiClient,
    ) -> None:
        self._config = config
        self._github_api_client = github_api_client
        self._dry_run_name_markers = tuple(
            marker.lower() for marker in config.dry_run_name_markers
        )
        self._dry_run_command_markers = tuple(
            marker.lower() for marker in config.dry_run_command_markers
        )

    def validate(self) -> PullRequestReleaseDryRunObservation:
        repository_info = self._read_json_object(f"/repos/{self._config.repository}")
        default_branch = self._default_branch(repository_info)
        workflow = self._select_workflow()
        workflow_id = workflow.get("id")
        if not isinstance(workflow_id, int):
            raise PullRequestReleaseDryRunError(
                "TS-250 could not resolve a numeric workflow ID for "
                f"{self._config.workflow_path}."
            )

        workflow_text = self._read_workflow_text(default_branch)
        pull_request_observation = self._create_and_observe_pull_request(
            default_branch=default_branch,
            workflow_id=workflow_id,
        )

        return PullRequestReleaseDryRunObservation(
            repository=self._config.repository,
            workflow_id=workflow_id,
            workflow_name=str(workflow.get("name", "")),
            workflow_path=self._config.workflow_path,
            workflow_html_url=str(workflow.get("html_url", "")),
            default_branch=default_branch,
            workflow_text=workflow_text,
            workflow_declares_pull_request_trigger=self._workflow_declares_pull_request(
                workflow_text
            ),
            workflow_declares_dry_run_step=self._workflow_declares_dry_run_step(
                workflow_text
            ),
            workflow_declares_dry_run_command=self._workflow_declares_dry_run_command(
                workflow_text
            ),
            pull_request_number=int(pull_request_observation["pull_request_number"]),
            pull_request_url=str(pull_request_observation["pull_request_url"]),
            pull_request_checks_url=str(
                pull_request_observation["pull_request_checks_url"]
            ),
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
            pull_request_head_sha=self._optional_string(
                pull_request_observation.get("pull_request_head_sha")
            ),
            pull_request_status_state=self._optional_string(
                pull_request_observation.get("pull_request_status_state")
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
            observed_branch_run_events=list(
                pull_request_observation["observed_branch_run_events"]
            ),
            observed_branch_run_statuses=list(
                pull_request_observation["observed_branch_run_statuses"]
            ),
            observed_branch_run_conclusions=list(
                pull_request_observation["observed_branch_run_conclusions"]
            ),
            observed_job_names=list(pull_request_observation["observed_job_names"]),
            observed_step_names=list(pull_request_observation["observed_step_names"]),
            dry_run_run_name=self._optional_string(
                pull_request_observation.get("dry_run_run_name")
            ),
            dry_run_run_path=self._optional_string(
                pull_request_observation.get("dry_run_run_path")
            ),
            dry_run_run_url=self._optional_string(
                pull_request_observation.get("dry_run_run_url")
            ),
            dry_run_run_event=self._optional_string(
                pull_request_observation.get("dry_run_run_event")
            ),
            dry_run_run_status=self._optional_string(
                pull_request_observation.get("dry_run_run_status")
            ),
            dry_run_run_conclusion=self._optional_string(
                pull_request_observation.get("dry_run_run_conclusion")
            ),
            dry_run_job_name=self._optional_string(
                pull_request_observation.get("dry_run_job_name")
            ),
            dry_run_step_name=self._optional_string(
                pull_request_observation.get("dry_run_step_name")
            ),
            dry_run_step_status=self._optional_string(
                pull_request_observation.get("dry_run_step_status")
            ),
            dry_run_step_conclusion=self._optional_string(
                pull_request_observation.get("dry_run_step_conclusion")
            ),
            cleanup_closed_pull_request=bool(
                pull_request_observation["cleanup_closed_pull_request"]
            ),
            cleanup_deleted_branch=bool(
                pull_request_observation["cleanup_deleted_branch"]
            ),
        )

    def _create_and_observe_pull_request(
        self,
        *,
        default_branch: str,
        workflow_id: int,
    ) -> dict[str, object]:
        temp_repository_root = Path(tempfile.mkdtemp(prefix="ts250-"))
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
                    f"origin/{default_branch}",
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

            probe_file = temp_repository_root / self._config.probe_file_path
            if not probe_file.exists():
                raise PullRequestReleaseDryRunError(
                    "TS-250 precondition failed: probe file path does not exist in the "
                    f"target repository.\nRepository: {self._config.repository}\n"
                    f"Path: {self._config.probe_file_path}"
                )

            marker = datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")
            with probe_file.open("a", encoding="utf-8") as stream:
                stream.write(f"\n<!-- TS-250 probe {marker} -->\n")

            self._run_command(
                ["git", "add", self._config.probe_file_path],
                cwd=temp_repository_root,
            )
            self._run_command(
                [
                    "git",
                    "commit",
                    "-m",
                    "TS-250 probe: verify pull-request release dry-run",
                ],
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
                    default_branch,
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
                workflow_id=workflow_id,
            )
            pull_request_state = self._wait_for_pull_request_state(pull_request_number)

            pull_request_observation = {
                "pull_request_number": pull_request_number,
                "pull_request_url": pr_url,
                "pull_request_checks_url": f"{pr_url}/checks",
                "pull_request_head_branch": branch_name,
                "pull_request_probe_path": self._config.probe_file_path,
                "pull_request_state": pull_request_state.get("state"),
                "pull_request_mergeable_state": pull_request_state.get(
                    "mergeable_state"
                ),
                "pull_request_head_sha": pull_request_state.get("head_sha"),
                "pull_request_status_state": pull_request_state.get("status_state"),
                "cleanup_closed_pull_request": False,
                "cleanup_deleted_branch": False,
                **run_observation,
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

            if pull_request_observation is not None:
                pull_request_observation["cleanup_closed_pull_request"] = (
                    cleanup_closed_pull_request
                )
                pull_request_observation["cleanup_deleted_branch"] = (
                    cleanup_deleted_branch
                )

        if pull_request_observation is None:
            raise PullRequestReleaseDryRunError(
                "TS-250 did not produce a disposable pull request observation."
            )
        return pull_request_observation

    def _wait_for_pull_request_runs(
        self,
        *,
        branch_name: str,
        started_at: float,
        workflow_id: int,
    ) -> dict[str, object]:
        deadline = time.time() + self._config.run_timeout_seconds
        latest_runs: list[dict[str, Any]] = []
        latest_jobs: list[dict[str, Any]] = []
        dry_run_run_name: str | None = None
        dry_run_run_path: str | None = None
        dry_run_run_url: str | None = None
        dry_run_run_event: str | None = None
        dry_run_run_status: str | None = None
        dry_run_run_conclusion: str | None = None
        dry_run_job_name: str | None = None
        dry_run_step_name: str | None = None
        dry_run_step_status: str | None = None
        dry_run_step_conclusion: str | None = None

        while time.time() < deadline:
            latest_runs = self._list_branch_runs(branch_name, started_at)
            candidate = self._find_target_workflow_run(latest_runs, workflow_id)
            if candidate is not None:
                dry_run_run_name = candidate["run_name"]
                dry_run_run_path = candidate["run_path"]
                dry_run_run_url = candidate["run_url"]
                dry_run_run_event = candidate["run_event"]
                dry_run_run_status = candidate["run_status"]
                dry_run_run_conclusion = candidate["run_conclusion"]
                latest_jobs = candidate["jobs"]
                dry_run_job_name = candidate["job_name"]
                dry_run_step_name = candidate["step_name"]
                dry_run_step_status = candidate["step_status"]
                dry_run_step_conclusion = candidate["step_conclusion"]
                if self._dry_run_step_has_terminal_conclusion(
                    dry_run_step_status,
                    dry_run_step_conclusion,
                ):
                    break
                if dry_run_run_status == "completed" and dry_run_step_name is None:
                    break
            time.sleep(self._config.poll_interval_seconds)

        return {
            "observed_branch_run_count": len(latest_runs),
            "observed_branch_run_names": self._run_names(latest_runs),
            "observed_branch_run_paths": self._run_paths(latest_runs),
            "observed_branch_run_urls": self._run_urls(latest_runs),
            "observed_branch_run_events": self._run_events(latest_runs),
            "observed_branch_run_statuses": self._run_statuses(latest_runs),
            "observed_branch_run_conclusions": self._run_conclusions(latest_runs),
            "observed_job_names": self._job_names(latest_jobs),
            "observed_step_names": self._step_names(latest_jobs),
            "dry_run_run_name": dry_run_run_name,
            "dry_run_run_path": dry_run_run_path,
            "dry_run_run_url": dry_run_run_url,
            "dry_run_run_event": dry_run_run_event,
            "dry_run_run_status": dry_run_run_status,
            "dry_run_run_conclusion": dry_run_run_conclusion,
            "dry_run_job_name": dry_run_job_name,
            "dry_run_step_name": dry_run_step_name,
            "dry_run_step_status": dry_run_step_status,
            "dry_run_step_conclusion": dry_run_step_conclusion,
        }

    def _find_target_workflow_run(
        self,
        runs: list[dict[str, Any]],
        workflow_id: int,
    ) -> dict[str, object] | None:
        for run in runs:
            run_id = run.get("id")
            run_workflow_id = run.get("workflow_id")
            if not isinstance(run_id, int) or run_workflow_id != workflow_id:
                continue

            jobs = self._read_jobs(run_id)

            step_name, job_name, step_status, step_conclusion = self._find_dry_run_step(
                jobs
            )
            return {
                "jobs": jobs,
                "run_name": self._optional_string(run.get("name")),
                "run_path": self._config.workflow_path,
                "run_url": self._optional_string(run.get("html_url")),
                "run_event": self._optional_string(run.get("event")),
                "run_status": self._optional_string(run.get("status")),
                "run_conclusion": self._optional_string(run.get("conclusion")),
                "job_name": job_name,
                "step_name": step_name,
                "step_status": step_status,
                "step_conclusion": step_conclusion,
            }
        return None

    def _find_dry_run_step(
        self,
        jobs: list[dict[str, Any]],
    ) -> tuple[str | None, str | None, str | None, str | None]:
        for job in jobs:
            job_name = self._optional_string(job.get("name"))
            steps = job.get("steps")
            if not isinstance(steps, list):
                continue
            for step in steps:
                if not isinstance(step, dict):
                    continue
                step_name = self._optional_string(step.get("name"))
                if self._has_dry_run_marker(step_name):
                    return (
                        step_name,
                        job_name,
                        self._optional_string(step.get("status")),
                        self._optional_string(step.get("conclusion")),
                    )
        return None, None, None, None

    @staticmethod
    def _dry_run_step_has_terminal_conclusion(
        step_status: str | None,
        step_conclusion: str | None,
    ) -> bool:
        return step_status == "completed" and step_conclusion is not None

    def _wait_for_pull_request_state(
        self,
        pull_request_number: int,
    ) -> dict[str, str | None]:
        deadline = time.time() + self._config.pull_request_timeout_seconds
        latest_state = {
            "state": None,
            "mergeable_state": None,
            "head_sha": None,
            "status_state": None,
        }

        while time.time() < deadline:
            payload = self._read_json_object(
                f"/repos/{self._config.repository}/pulls/{pull_request_number}"
            )
            head_sha = self._optional_string(((payload.get("head") or {}).get("sha")))
            mergeable_state = self._optional_string(payload.get("mergeable_state"))
            latest_state = {
                "state": self._optional_string(payload.get("state")),
                "mergeable_state": mergeable_state,
                "head_sha": head_sha,
                "status_state": self._read_check_runs_state(head_sha)
                if head_sha
                else None,
            }
            if head_sha and mergeable_state and mergeable_state != "unknown":
                return latest_state
            time.sleep(self._config.poll_interval_seconds)

        return latest_state

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
                and (
                    self._optional_string(run.get("name")) == self._config.workflow_name
                    or self._has_dry_run_marker(self._optional_string(run.get("name")))
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
            raise PullRequestReleaseDryRunError(
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

    def _select_workflow(self) -> dict[str, Any]:
        payload = self._read_json_object(f"/repos/{self._config.repository}/actions/workflows")
        workflows = payload.get("workflows")
        if not isinstance(workflows, list):
            raise PullRequestReleaseDryRunError(
                "GitHub Actions workflows response did not return a workflows list."
            )

        for workflow in workflows:
            if not isinstance(workflow, dict):
                continue
            path = workflow.get("path")
            if isinstance(path, str) and path == self._config.workflow_path:
                return workflow

        raise PullRequestReleaseDryRunError(
            "TS-250 could not find the configured workflow path "
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
            raise PullRequestReleaseDryRunError(
                "GitHub did not return base64 workflow contents for "
                f"{self._config.workflow_path}."
            )
        return base64.b64decode(encoded_content.replace("\n", "")).decode("utf-8")

    def _close_pull_request(self, pull_request_number: int) -> bool:
        try:
            self._read_json_object(
                f"/repos/{self._config.repository}/pulls/{pull_request_number}",
                method="PATCH",
                field_args=["-f", "state=closed"],
            )
        except PullRequestReleaseDryRunError:
            return False
        return True

    def _delete_branch(self, branch_name: str, *, cwd: Path) -> bool:
        try:
            self._run_command(
                ["git", "push", "origin", "--delete", branch_name],
                cwd=cwd,
            )
        except PullRequestReleaseDryRunError:
            return False
        return True

    def _read_jobs(self, run_id: int) -> list[dict[str, Any]]:
        payload = self._read_json_object(
            f"/repos/{self._config.repository}/actions/runs/{run_id}/jobs?per_page=50"
        )
        jobs = payload.get("jobs")
        if not isinstance(jobs, list):
            raise PullRequestReleaseDryRunError(
                f"GitHub Actions jobs response for run {run_id} did not return a list."
            )
        return [job for job in jobs if isinstance(job, dict)]

    def _workflow_declares_pull_request(self, workflow_text: str) -> bool:
        if re.search(
            r"(?m)^\s*on\s*:\s*['\"]?pull_request(?:_target)?['\"]?\s*$",
            workflow_text,
        ):
            return True
        if re.search(
            r"(?m)^\s*on\s*:\s*\[(?:[^\]]*\bpull_request(?:_target)?\b[^\]]*)\]\s*$",
            workflow_text,
        ):
            return True
        if re.search(
            r"(?m)^\s*on\s*:\s*\{(?:[^}]*\bpull_request(?:_target)?\s*:[^}]*)\}\s*$",
            workflow_text,
        ):
            return True
        return bool(
            re.search(r"(?m)^\s*pull_request(?:_target)?\s*:\s*(?:.*)?$", workflow_text)
        )

    def _workflow_declares_dry_run_step(self, workflow_text: str) -> bool:
        step_names = re.findall(r"(?im)^\s*-\s*name:\s*(.+?)\s*$", workflow_text)
        return any(self._has_dry_run_marker(step_name) for step_name in step_names)

    def _workflow_declares_dry_run_command(self, workflow_text: str) -> bool:
        lowered = workflow_text.lower()
        return any(marker in lowered for marker in self._dry_run_command_markers)

    def _has_dry_run_marker(self, value: str | None) -> bool:
        if value is None:
            return False
        lowered = value.lower()
        return any(marker in lowered for marker in self._dry_run_name_markers)

    def _is_contributor_visible_pull_request_event(self, event: str | None) -> bool:
        if event is None:
            return False
        return event in self._CONTRIBUTOR_VISIBLE_PULL_REQUEST_EVENTS

    def _origin_clone_url(self) -> str:
        return f"https://github.com/{self._config.repository}.git"

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
            raise PullRequestReleaseDryRunError(
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
            raise PullRequestReleaseDryRunError(
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
            raise PullRequestReleaseDryRunError(str(error)) from error
        return json.loads(response_text)

    def _unique_branch_name(self) -> str:
        timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"{self._config.branch_prefix}-{timestamp}"

    @staticmethod
    def _extract_pull_request_number(pull_request_url: str) -> int:
        match = re.search(r"/pull/(\d+)$", pull_request_url.strip())
        if match is None:
            raise PullRequestReleaseDryRunError(
                "gh pr create did not return a pull request URL ending in /pull/<number>: "
                f"{pull_request_url}"
            )
        return int(match.group(1))

    @staticmethod
    def _default_branch(repository_info: dict[str, Any]) -> str:
        default_branch = repository_info.get("default_branch")
        if isinstance(default_branch, str) and default_branch.strip():
            return default_branch.strip()
        return "main"

    @staticmethod
    def _run_created_at_epoch(run: dict[str, Any]) -> float | None:
        created_at = PullRequestReleaseDryRunProbeService._optional_string(
            run.get("created_at")
        )
        if created_at is None:
            return None
        try:
            normalized = created_at.replace("Z", "+00:00")
            return datetime.fromisoformat(normalized).timestamp()
        except ValueError:
            return None

    @staticmethod
    def _run_names(runs: list[dict[str, Any]]) -> list[str]:
        return [
            name
            for name in (
                PullRequestReleaseDryRunProbeService._optional_string(run.get("name"))
                for run in runs
            )
            if name is not None
        ]

    def _run_paths(self, runs: list[dict[str, Any]]) -> list[str]:
        return [
            path
            for path in (
                self._optional_string(run.get("path")) for run in runs
            )
            if path is not None
        ]

    @staticmethod
    def _run_urls(runs: list[dict[str, Any]]) -> list[str]:
        return [
            url
            for url in (
                PullRequestReleaseDryRunProbeService._optional_string(
                    run.get("html_url")
                )
                for run in runs
            )
            if url is not None
        ]

    @staticmethod
    def _run_events(runs: list[dict[str, Any]]) -> list[str]:
        return [
            event
            for event in (
                PullRequestReleaseDryRunProbeService._optional_string(run.get("event"))
                for run in runs
            )
            if event is not None
        ]

    @staticmethod
    def _run_statuses(runs: list[dict[str, Any]]) -> list[str]:
        return [
            status
            for status in (
                PullRequestReleaseDryRunProbeService._optional_string(run.get("status"))
                for run in runs
            )
            if status is not None
        ]

    @staticmethod
    def _run_conclusions(runs: list[dict[str, Any]]) -> list[str]:
        return [
            conclusion
            for conclusion in (
                PullRequestReleaseDryRunProbeService._optional_string(
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
                PullRequestReleaseDryRunProbeService._optional_string(job.get("name"))
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
                step_name = PullRequestReleaseDryRunProbeService._optional_string(
                    step.get("name")
                )
                if step_name is not None:
                    names.append(step_name)
        return names

    @staticmethod
    def _optional_string(value: object) -> str | None:
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None
