from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
import json
from datetime import datetime, timezone
import re
import time
from typing import Any
from urllib.parse import quote

import yaml

from testing.core.config.github_actions_preflight_gate_config import (
    GitHubActionsPreflightGateConfig,
)
from testing.core.interfaces.github_actions_preflight_gate_probe import (
    GitHubActionsPreflightGateObservation,
    GitHubActionsSelfHostedRunnerObservation,
    GitHubActionsPreflightWorkflowObservation,
    GitHubActionsWorkflowJobObservation,
    GitHubActionsWorkflowRunObservation,
)
from testing.core.interfaces.github_api_client import GitHubApiClient, GitHubApiClientError
from testing.core.interfaces.github_workflow_run_log_reader import (
    GitHubWorkflowRunLogReader,
)


class GitHubActionsPreflightGateProbeError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        partial_result: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.partial_result = deepcopy(partial_result or {})


class GitHubActionsPreflightGateProbeService:
    def __init__(
        self,
        config: GitHubActionsPreflightGateConfig,
        *,
        github_api_client: GitHubApiClient,
        workflow_run_log_reader: GitHubWorkflowRunLogReader,
    ) -> None:
        self._config = config
        self._github_api_client = github_api_client
        self._workflow_run_log_reader = workflow_run_log_reader

    def validate(self) -> GitHubActionsPreflightGateObservation:
        partial_result: dict[str, Any] = {
            "repository": self._config.repository,
            "default_branch": self._config.default_branch,
            "workflow_name": self._config.workflow_name,
            "expected_failure_markers": list(self._config.expected_failure_markers),
        }
        repository_metadata = self._load_json_object(
            endpoint=f"/repos/{self._config.repository}"
        )
        default_branch = self._read_string(repository_metadata, "default_branch")
        if default_branch is None:
            default_branch = self._config.default_branch
        partial_result["default_branch"] = default_branch

        workflow_metadata = self._load_json_object(
            endpoint=(
                f"/repos/{self._config.repository}/actions/workflows/"
                f"{quote(self._config.workflow_file, safe='')}"
            )
        )
        raw_file_text = self._github_api_client.request_text(
            endpoint=(
                f"/repos/{self._config.repository}/contents/"
                f"{quote(self._config.workflow_path, safe='/')}?ref="
                f"{quote(default_branch, safe='')}"
            ),
            field_args=["-H", "Accept: application/vnd.github.raw+json"],
        )
        workflow_observation = self._parse_workflow_observation(
            metadata=workflow_metadata,
            raw_file_text=raw_file_text,
        )
        partial_result["workflow"] = asdict(workflow_observation)
        head_sha = self._load_branch_sha(default_branch)
        partial_result["head_sha"] = head_sha
        matching_runners = self._load_matching_runners(partial_result=partial_result)
        partial_result["matching_runners"] = [
            asdict(runner) for runner in matching_runners
        ]
        online_matching_runners = [
            runner
            for runner in matching_runners
            if (runner.status or "").lower() == "online"
        ]
        if online_matching_runners:
            raise GitHubActionsPreflightGateProbeError(
                "Precondition failed: TS-706 requires all repository runners matching "
                f"{self._config.expected_runner_labels} to be offline before creating the "
                "disposable release tag. Matching online runners: "
                + ", ".join(
                    f"{runner.name} (status={runner.status}, busy={runner.busy})"
                    for runner in online_matching_runners
                ),
                partial_result=partial_result,
            )
        baseline_run_ids = {
            run.id for run in self._list_workflow_runs(event="push", per_page=50)
        }

        tag_name = self._build_tag_name()
        partial_result["tag_name"] = tag_name
        started_at = time.time()
        try:
            self._create_tag(tag_name=tag_name, sha=head_sha)
            run = self._wait_for_new_push_run(
                head_sha=head_sha,
                started_at=started_at,
                baseline_run_ids=baseline_run_ids,
            )
            partial_result["run"] = asdict(run)
            completed_run = self._wait_for_completed_run(run.id)
            partial_result["run"] = asdict(completed_run)
            jobs = self._read_jobs(completed_run.id)
            preflight_job = self._find_job(jobs, self._config.preflight_job_name)
            downstream_job = self._find_job(jobs, self._config.downstream_job_name)
            partial_result["preflight_job"] = (
                asdict(preflight_job) if preflight_job is not None else None
            )
            partial_result["downstream_job"] = (
                asdict(downstream_job) if downstream_job is not None else None
            )
            log_text = self._workflow_run_log_reader.read_run_log(completed_run.id)
            matched_failure_text = self._match_failure_text(log_text)
            log_excerpt = self._extract_log_excerpt(
                log_text,
                markers=[
                    *self._config.expected_failure_markers,
                    "Resource not accessible by integration",
                    "Unhandled error: HttpError",
                ],
            )
            partial_result["matched_failure_text"] = matched_failure_text
            partial_result["log_excerpt"] = log_excerpt
        except GitHubActionsPreflightGateProbeError as error:
            merged_partial_result = deepcopy(partial_result)
            if error.partial_result:
                merged_partial_result.update(error.partial_result)
            raise GitHubActionsPreflightGateProbeError(
                str(error),
                partial_result=merged_partial_result,
            ) from error
        finally:
            self._delete_tag(tag_name)

        return GitHubActionsPreflightGateObservation(
            repository=self._config.repository,
            default_branch=default_branch,
            head_sha=head_sha,
            tag_name=tag_name,
            workflow_name=self._config.workflow_name,
            workflow=workflow_observation,
            matching_runners=matching_runners,
            run=completed_run,
            preflight_job=preflight_job,
            downstream_job=downstream_job,
            matched_failure_text=matched_failure_text,
            log_excerpt=log_excerpt,
            log_text=log_text,
            expected_failure_markers=list(self._config.expected_failure_markers),
        )

    def _load_matching_runners(
        self,
        *,
        partial_result: dict[str, Any],
    ) -> list[GitHubActionsSelfHostedRunnerObservation]:
        try:
            payload = self._load_json_object(
                endpoint=(
                    f"/repos/{self._config.repository}/actions/runners?per_page=100"
                )
            )
        except GitHubActionsPreflightGateProbeError as error:
            partial_result["runner_inventory_error"] = str(error)
            raise GitHubActionsPreflightGateProbeError(
                "Precondition failed: TS-706 could not verify whether the "
                f"{self._config.expected_runner_labels} runners were offline before "
                "creating the disposable release tag because the repository runners API "
                "was not accessible.\n"
                f"Inventory error: {error}",
                partial_result=partial_result,
            ) from error

        runners = payload.get("runners")
        if not isinstance(runners, list):
            raise GitHubActionsPreflightGateProbeError(
                "Precondition failed: TS-706 could not verify the repository runner "
                "inventory because the GitHub API response did not include a runners list.",
                partial_result=partial_result,
            )
        matching_runners = [
            self._to_runner_observation(entry)
            for entry in runners
            if isinstance(entry, dict)
            and self._runner_has_required_labels(entry)
        ]
        return matching_runners

    def _parse_workflow_observation(
        self,
        *,
        metadata: dict[str, Any],
        raw_file_text: str,
    ) -> GitHubActionsPreflightWorkflowObservation:
        parsed = yaml.load(raw_file_text, Loader=yaml.BaseLoader) or {}
        if not isinstance(parsed, dict):
            raise GitHubActionsPreflightGateProbeError(
                "TS-706 expected the Apple release workflow file to deserialize to a mapping."
            )

        env_payload = parsed.get("env")
        if not isinstance(env_payload, dict):
            env_payload = {}
        jobs = parsed.get("jobs")
        if not isinstance(jobs, dict):
            jobs = {}

        preflight_job = self._find_job_definition(
            jobs,
            expected_name=self._config.preflight_job_name,
        )
        downstream_job = self._find_job_definition(
            jobs,
            expected_name=self._config.downstream_job_name,
        )
        if not isinstance(preflight_job, dict) or not isinstance(downstream_job, dict):
            raise GitHubActionsPreflightGateProbeError(
                "TS-706 expected workflow jobs named "
                f"`{self._config.preflight_job_name}` and "
                f"`{self._config.downstream_job_name}` in {self._config.workflow_path}."
            )

        downstream_runs_on = self._normalize_runs_on(downstream_job.get("runs-on"))
        return GitHubActionsPreflightWorkflowObservation(
            html_url=self._read_string(metadata, "html_url") or "",
            state=self._read_string(metadata, "state") or "",
            path=self._read_string(metadata, "path") or self._config.workflow_path,
            updated_at=self._read_string(metadata, "updated_at"),
            preflight_runs_on=self._normalize_runs_on(preflight_job.get("runs-on")),
            downstream_runs_on=downstream_runs_on,
            required_runner_labels=self._read_required_runner_labels(
                env_payload=env_payload,
                downstream_runs_on=downstream_runs_on,
            ),
            raw_file_text=raw_file_text,
        )

    def _find_job_definition(
        self,
        jobs: dict[str, Any],
        *,
        expected_name: str,
    ) -> dict[str, Any] | None:
        for job_payload in jobs.values():
            if not isinstance(job_payload, dict):
                continue
            if self._read_string(job_payload, "name") == expected_name:
                return job_payload
        return None

    def _read_required_runner_labels(
        self,
        *,
        env_payload: dict[str, Any],
        downstream_runs_on: list[str],
    ) -> list[str]:
        configured_labels = self._split_csv(
            self._read_string(env_payload, "required_runner_labels") or ""
        )
        if configured_labels:
            return configured_labels
        return downstream_runs_on

    def _build_tag_name(self) -> str:
        moment = datetime.now(tz=timezone.utc)
        return f"v98.{moment.strftime('%m%d%H')}.{moment.strftime('%M%S%f')[:8]}"

    def _create_tag(self, *, tag_name: str, sha: str) -> None:
        try:
            self._github_api_client.request_text(
                endpoint=f"/repos/{self._config.repository}/git/refs",
                method="POST",
                stdin_json={"ref": f"refs/tags/{tag_name}", "sha": sha},
            )
        except GitHubApiClientError as error:
            raise GitHubActionsPreflightGateProbeError(
                f"TS-706 could not create disposable tag `{tag_name}` on "
                f"{self._config.repository}@{sha}.\n{error}"
            ) from error

    def _delete_tag(self, tag_name: str) -> None:
        try:
            self._github_api_client.request_text(
                endpoint=(
                    f"/repos/{self._config.repository}/git/refs/tags/"
                    f"{quote(tag_name, safe='')}"
                ),
                method="DELETE",
            )
        except GitHubApiClientError:
            return

    def _wait_for_new_push_run(
        self,
        *,
        head_sha: str,
        started_at: float,
        baseline_run_ids: set[int],
    ) -> GitHubActionsWorkflowRunObservation:
        deadline = time.time() + self._config.run_timeout_seconds
        started_floor = started_at - max(self._config.poll_interval_seconds, 1)
        latest_candidate: GitHubActionsWorkflowRunObservation | None = None

        while time.time() < deadline:
            runs = self._list_workflow_runs(
                event="push",
                per_page=self._config.recent_runs_limit,
            )
            candidates = [
                run
                for run in runs
                if run.id not in baseline_run_ids
                and run.head_sha == head_sha
                and self._run_created_at_epoch(run.created_at) is not None
                and (self._run_created_at_epoch(run.created_at) or 0.0) >= started_floor
            ]
            if candidates:
                latest_candidate = max(
                    candidates,
                    key=lambda run: (
                        self._run_created_at_epoch(run.created_at) or 0.0,
                        run.id,
                    ),
                )
                return latest_candidate
            time.sleep(self._config.poll_interval_seconds)

        raise GitHubActionsPreflightGateProbeError(
            "TS-706 did not observe a new Apple Release Builds push run after creating "
            f"the disposable tag within {self._config.run_timeout_seconds} seconds. "
            f"Last candidate: {latest_candidate}"
        )

    def _wait_for_completed_run(self, run_id: int) -> GitHubActionsWorkflowRunObservation:
        deadline = time.time() + self._config.run_timeout_seconds
        latest_run: GitHubActionsWorkflowRunObservation | None = None

        while time.time() < deadline:
            latest_run = self._read_run(run_id)
            if latest_run.status == "completed":
                return latest_run
            self._raise_if_runner_is_available(latest_run)
            time.sleep(self._config.poll_interval_seconds)

        raise GitHubActionsPreflightGateProbeError(
            "TS-706 timed out waiting for Apple Release Builds run "
            f"{run_id} to complete. Last status={latest_run.status if latest_run else None}. "
            f"Run URL: {latest_run.html_url if latest_run is not None else f'https://github.com/{self._config.repository}/actions/runs/{run_id}'}"
        )

    def _raise_if_runner_is_available(
        self,
        run: GitHubActionsWorkflowRunObservation,
    ) -> None:
        jobs = self._read_jobs(run.id)
        preflight_job = self._find_job(jobs, self._config.preflight_job_name)
        downstream_job = self._find_job(jobs, self._config.downstream_job_name)
        if preflight_job is None or downstream_job is None:
            return
        if preflight_job.conclusion != "success":
            return
        if downstream_job.status not in {"queued", "in_progress", "waiting"}:
            return
        raise GitHubActionsPreflightGateProbeError(
            "TS-706 could not reproduce the no-runner failure condition because the "
            f"preflight job `{preflight_job.name}` succeeded and the downstream macOS "
            f"job `{downstream_job.name}` entered `{downstream_job.status}`. This "
            "repository currently appears to have a matching online macOS release runner. "
            f"Run URL: {run.html_url}. "
            f"Preflight job URL: {preflight_job.html_url}. "
            f"Downstream job URL: {downstream_job.html_url}.",
            partial_result={
                "repository": self._config.repository,
                "default_branch": self._config.default_branch,
                "workflow_name": self._config.workflow_name,
                "run": asdict(run),
                "preflight_job": asdict(preflight_job),
                "downstream_job": asdict(downstream_job),
            },
        )

    def _list_workflow_runs(
        self,
        *,
        event: str,
        per_page: int,
    ) -> list[GitHubActionsWorkflowRunObservation]:
        payload = self._load_json_object(
            endpoint=(
                f"/repos/{self._config.repository}/actions/workflows/"
                f"{quote(self._config.workflow_file, safe='')}/runs"
                f"?event={quote(event, safe='')}&per_page={per_page}"
            )
        )
        workflow_runs = payload.get("workflow_runs")
        if not isinstance(workflow_runs, list):
            raise GitHubActionsPreflightGateProbeError(
                "GitHub Actions workflow runs response did not return a workflow_runs list."
            )
        return [
            self._to_run_observation(entry)
            for entry in workflow_runs
            if isinstance(entry, dict)
        ]

    def _read_run(self, run_id: int) -> GitHubActionsWorkflowRunObservation:
        payload = self._load_json_object(
            endpoint=f"/repos/{self._config.repository}/actions/runs/{run_id}"
        )
        return self._to_run_observation(payload)

    def _read_jobs(self, run_id: int) -> list[GitHubActionsWorkflowJobObservation]:
        payload = self._load_json_object(
            endpoint=f"/repos/{self._config.repository}/actions/runs/{run_id}/jobs?per_page=20"
        )
        jobs = payload.get("jobs")
        if not isinstance(jobs, list):
            raise GitHubActionsPreflightGateProbeError(
                f"GitHub Actions jobs response for run {run_id} did not return a list."
            )
        observations: list[GitHubActionsWorkflowJobObservation] = []
        for entry in jobs:
            if not isinstance(entry, dict):
                continue
            job_id = entry.get("id")
            if not isinstance(job_id, int):
                continue
            observations.append(
                GitHubActionsWorkflowJobObservation(
                    id=job_id,
                    name=self._read_string(entry, "name") or "",
                    status=self._read_string(entry, "status"),
                    conclusion=self._read_string(entry, "conclusion"),
                    html_url=self._read_string(entry, "html_url") or "",
                    started_at=self._read_string(entry, "started_at"),
                    completed_at=self._read_string(entry, "completed_at"),
                )
            )
        return observations

    def _find_job(
        self,
        jobs: list[GitHubActionsWorkflowJobObservation],
        job_name: str,
    ) -> GitHubActionsWorkflowJobObservation | None:
        for job in jobs:
            if job.name == job_name:
                return job
        return None

    def _match_failure_text(self, log_text: str) -> str | None:
        for marker in self._config.expected_failure_markers:
            if marker in log_text:
                return marker
        return None

    def _extract_log_excerpt(self, log_text: str, *, markers: list[str]) -> str:
        for marker in markers:
            if not marker:
                continue
            index = log_text.find(marker)
            if index < 0:
                continue
            start = max(index - 300, 0)
            end = min(index + len(marker) + 900, len(log_text))
            return log_text[start:end].strip()
        return log_text[:1200].strip()

    def _load_branch_sha(self, branch: str) -> str:
        payload = self._load_json_object(
            endpoint=f"/repos/{self._config.repository}/branches/{quote(branch, safe='')}"
        )
        commit = payload.get("commit")
        if isinstance(commit, dict):
            sha = commit.get("sha")
            if isinstance(sha, str) and sha.strip():
                return sha.strip()
        raise GitHubActionsPreflightGateProbeError(
            f"TS-706 could not read the branch head SHA for {self._config.repository}@{branch}."
        )

    def _to_run_observation(
        self,
        payload: dict[str, Any],
    ) -> GitHubActionsWorkflowRunObservation:
        run_id = payload.get("id")
        if not isinstance(run_id, int):
            raise GitHubActionsPreflightGateProbeError(
                f"GitHub Actions run payload did not include an integer id: {payload}"
            )
        return GitHubActionsWorkflowRunObservation(
            id=run_id,
            event=self._read_string(payload, "event") or "",
            head_branch=self._read_string(payload, "head_branch"),
            head_sha=self._read_string(payload, "head_sha"),
            status=self._read_string(payload, "status"),
            conclusion=self._read_string(payload, "conclusion"),
            html_url=self._read_string(payload, "html_url") or "",
            created_at=self._read_string(payload, "created_at"),
            display_title=self._read_string(payload, "display_title"),
        )

    def _to_runner_observation(
        self,
        payload: dict[str, Any],
    ) -> GitHubActionsSelfHostedRunnerObservation:
        runner_id = payload.get("id")
        if not isinstance(runner_id, int):
            raise GitHubActionsPreflightGateProbeError(
                f"GitHub Actions runner payload did not include an integer id: {payload}"
            )
        busy = payload.get("busy")
        if not isinstance(busy, bool):
            busy = None
        return GitHubActionsSelfHostedRunnerObservation(
            id=runner_id,
            name=self._read_string(payload, "name") or "",
            status=self._read_string(payload, "status"),
            busy=busy,
            labels=self._read_runner_labels(payload),
        )

    def _load_json_object(self, *, endpoint: str) -> dict[str, Any]:
        try:
            response_text = self._github_api_client.request_text(endpoint=endpoint)
        except GitHubApiClientError as error:
            raise GitHubActionsPreflightGateProbeError(str(error)) from error
        payload = json.loads(response_text)
        if not isinstance(payload, dict):
            raise GitHubActionsPreflightGateProbeError(
                f"Expected GitHub API payload for {endpoint} to decode to a mapping."
            )
        return payload

    def _normalize_runs_on(self, value: object) -> list[str]:
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return []

    def _read_runner_labels(self, payload: dict[str, Any]) -> list[str]:
        labels = payload.get("labels")
        if not isinstance(labels, list):
            return []
        names: list[str] = []
        for entry in labels:
            if not isinstance(entry, dict):
                continue
            name = self._read_string(entry, "name")
            if name is not None:
                names.append(name)
        return names

    def _runner_has_required_labels(self, payload: dict[str, Any]) -> bool:
        runner_labels = set(self._read_runner_labels(payload))
        required_labels = set(self._config.expected_runner_labels)
        return required_labels.issubset(runner_labels)

    def _split_csv(self, value: str) -> list[str]:
        return [item.strip() for item in value.split(",") if item.strip()]

    def _run_created_at_epoch(self, value: str | None) -> float | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return None

    def _read_string(self, payload: dict[str, Any], key: str) -> str | None:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None
