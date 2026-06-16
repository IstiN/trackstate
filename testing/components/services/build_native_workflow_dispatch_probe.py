from __future__ import annotations

import json
import time
from typing import Any
from urllib.parse import quote

import yaml

from testing.core.config.build_native_workflow_dispatch_config import (
    BuildNativeWorkflowDispatchConfig,
)
from testing.core.interfaces.build_native_workflow_dispatch_probe import (
    BuildNativeWorkflowDispatchObservation,
)
from testing.core.interfaces.github_api_client import GitHubApiClient, GitHubApiClientError


class BuildNativeWorkflowDispatchProbeError(RuntimeError):
    pass


class BuildNativeWorkflowDispatchProbeService:
    def __init__(
        self,
        config: BuildNativeWorkflowDispatchConfig,
        *,
        github_api_client: GitHubApiClient,
    ) -> None:
        self._config = config
        self._github_api_client = github_api_client

    def validate(self) -> BuildNativeWorkflowDispatchObservation:
        workflow_dispatch_enabled, dispatch_failure_reason = self._workflow_dispatch_enabled()
        runner_available, online_runner_names, runner_failure_reason = (
            self._check_runner_availability()
        )

        if not workflow_dispatch_enabled:
            return self._observation(
                workflow_dispatch_enabled=False,
                runner_available=runner_available,
                online_runner_names=online_runner_names,
                dispatched=False,
                failure_reason=dispatch_failure_reason
                or f"{self._config.workflow_path} does not declare a workflow_dispatch trigger.",
            )

        if not runner_available:
            return self._observation(
                workflow_dispatch_enabled=True,
                runner_available=False,
                online_runner_names=online_runner_names,
                dispatched=False,
                failure_reason=runner_failure_reason
                or (
                    f"No online runners found with required labels "
                    f"{list(self._config.required_runner_labels)} for {self._config.repository}. "
                    "Provision the TrackState maintainer-owned macOS release runner before "
                    "rerunning this test."
                ),
            )

        run_id = self._dispatch_workflow()
        run_detail = self._wait_for_run_completion(run_id)
        jobs = self._list_jobs(run_id)

        build_macos_job = self._find_build_macos_job(jobs)
        reusable_workflow_invoked = self._reusable_workflow_invoked(jobs)

        return self._observation(
            workflow_dispatch_enabled=True,
            runner_available=True,
            online_runner_names=online_runner_names,
            dispatched=True,
            run_id=run_id,
            run_url=self._read_string(run_detail, "html_url"),
            run_status=self._read_string(run_detail, "status"),
            run_conclusion=self._read_string(run_detail, "conclusion"),
            build_macos_job_name=build_macos_job.get("name") if build_macos_job else None,
            build_macos_job_conclusion=self._read_string(build_macos_job, "conclusion")
            if build_macos_job
            else None,
            reusable_workflow_path=self._config.reusable_workflow_path,
            reusable_workflow_invoked=reusable_workflow_invoked,
            failure_reason=None,
        )

    def _workflow_dispatch_enabled(self) -> tuple[bool, str | None]:
        try:
            raw_text = self._github_api_client.request_text(
                endpoint=(
                    f"/repos/{self._config.repository}/contents/"
                    f"{quote(self._config.workflow_path, safe='/')}?ref="
                    f"{quote(self._config.default_branch, safe='')}"
                ),
                field_args=["-H", "Accept: application/vnd.github.raw+json"],
            )
        except (GitHubApiClientError, BuildNativeWorkflowDispatchProbeError) as error:
            reason = (
                f"Could not read {self._config.workflow_path} from "
                f"{self._config.repository}: {error}"
            )
            return (False, reason)

        parsed = yaml.safe_load(raw_text)
        if not isinstance(parsed, dict):
            return (False, f"{self._config.workflow_path} did not parse as a YAML mapping.")
        for key in ("on", "true", True):
            on_payload = parsed.get(key)
            if isinstance(on_payload, dict):
                return ("workflow_dispatch" in on_payload, None)
            if isinstance(on_payload, list):
                return ("workflow_dispatch" in on_payload, None)
            if isinstance(on_payload, str):
                return (on_payload == "workflow_dispatch", None)
        return (
            False,
            f"{self._config.workflow_path} does not declare a workflow_dispatch trigger.",
        )

    def _check_runner_availability(
        self,
    ) -> tuple[bool, list[str], str | None]:
        try:
            payload = self._load_json(
                f"/repos/{self._config.repository}/actions/runners?per_page=100"
            )
        except (GitHubApiClientError, BuildNativeWorkflowDispatchProbeError) as error:
            error_text = str(error)
            if "HTTP 403" in error_text or "HTTP 401" in error_text:
                status = "403" if "HTTP 403" in error_text else "401"
                reason = (
                    f"GitHub API returned HTTP {status} when querying runners for "
                    f"{self._config.repository}. Ensure GH_TOKEN or GITHUB_TOKEN has "
                    "read access to repository runners."
                )
                return (False, [], reason)
            raise BuildNativeWorkflowDispatchProbeError(
                f"Could not query runners for {self._config.repository}: {error}"
            ) from error

        runners = payload.get("runners", [])
        if not isinstance(runners, list):
            return (False, [], "GitHub API runners response was not a list.")

        required_labels = [label.lower() for label in self._config.required_runner_labels]
        online_names: list[str] = []
        for runner in runners:
            if not isinstance(runner, dict):
                continue
            if runner.get("status") != "online":
                continue
            labels = runner.get("labels", [])
            if not isinstance(labels, list):
                continue
            runner_label_names = {
                str(label.get("name", "")).lower()
                for label in labels
                if isinstance(label, dict)
            }
            if all(required in runner_label_names for required in required_labels):
                name = runner.get("name")
                if isinstance(name, str) and name.strip():
                    online_names.append(name.strip())

        if online_names:
            return (True, sorted(online_names), None)

        reason = (
            f"No online runners found with required labels "
            f"{list(self._config.required_runner_labels)} for {self._config.repository}. "
            "Provision the TrackState maintainer-owned macOS release runner before "
            "rerunning this test."
        )
        return (False, sorted(online_names), reason)

    def _dispatch_workflow(self) -> int:
        runs_before = self._recent_workflow_dispatch_run_ids()
        try:
            self._github_api_client.request_text(
                endpoint=(
                    f"/repos/{self._config.repository}/actions/workflows/"
                    f"{quote(self._config.workflow_file, safe='')}/dispatches"
                ),
                method="POST",
                field_args=[
                    "-f",
                    f"ref={self._config.default_branch}",
                    "-f",
                    f"inputs[release_ref]={self._config.release_ref}",
                ],
            )
        except GitHubApiClientError as error:
            raise BuildNativeWorkflowDispatchProbeError(
                f"Failed to dispatch {self._config.workflow_path}: {error}"
            ) from error

        deadline = time.time() + 120
        while time.time() < deadline:
            time.sleep(self._config.poll_interval_seconds)
            runs_after = self._recent_workflow_dispatch_run_ids()
            new_runs = runs_after - runs_before
            if new_runs:
                return min(new_runs)

        raise BuildNativeWorkflowDispatchProbeError(
            "Dispatched workflow but no new workflow_dispatch run appeared within 120 seconds."
        )

    def _recent_workflow_dispatch_run_ids(self) -> set[int]:
        payload = self._load_json(
            f"/repos/{self._config.repository}/actions/workflows/"
            f"{quote(self._config.workflow_file, safe='')}/runs"
            "?event=workflow_dispatch&per_page=20"
        )
        runs = payload.get("workflow_runs", [])
        if not isinstance(runs, list):
            return set()
        return {
            int(run.get("id"))
            for run in runs
            if isinstance(run, dict) and isinstance(run.get("id"), int)
        }

    def _wait_for_run_completion(self, run_id: int) -> dict[str, Any]:
        deadline = time.time() + self._config.run_timeout_seconds
        latest_detail: dict[str, Any] | None = None
        while time.time() < deadline:
            latest_detail = self._load_json(
                f"/repos/{self._config.repository}/actions/runs/{run_id}"
            )
            status = latest_detail.get("status")
            if status != "completed":
                time.sleep(self._config.poll_interval_seconds)
                continue
            conclusion = latest_detail.get("conclusion")
            if conclusion == "cancelled":
                time.sleep(self._config.poll_interval_seconds)
                continue
            return latest_detail

        if latest_detail is not None:
            raise BuildNativeWorkflowDispatchProbeError(
                f"Run {run_id} did not reach a non-cancelled completed state within "
                f"{self._config.run_timeout_seconds} seconds. "
                f"Last status={latest_detail.get('status')}, "
                f"conclusion={latest_detail.get('conclusion')}."
            )
        raise BuildNativeWorkflowDispatchProbeError(
            f"Run {run_id} disappeared before it could be observed."
        )

    def _list_jobs(self, run_id: int) -> list[dict[str, Any]]:
        payload = self._load_json(
            f"/repos/{self._config.repository}/actions/runs/{run_id}/jobs?per_page=100"
        )
        jobs = payload.get("jobs", [])
        if not isinstance(jobs, list):
            return []
        return [job for job in jobs if isinstance(job, dict)]

    def _find_build_macos_job(self, jobs: list[dict[str, Any]]) -> dict[str, Any] | None:
        for job in jobs:
            name = job.get("name")
            if isinstance(name, str) and name.strip() == self._config.build_macos_job_name:
                return job
        return None

    def _reusable_workflow_invoked(self, jobs: list[dict[str, Any]]) -> bool:
        for job in jobs:
            name = self._read_string(job, "name")
            if name in (
                "Verify macOS runner availability",
                "Build macOS desktop and CLI artifacts",
            ):
                return True
        return False

    def _observation(
        self,
        *,
        workflow_dispatch_enabled: bool,
        runner_available: bool,
        online_runner_names: list[str],
        dispatched: bool,
        run_id: int | None = None,
        run_url: str | None = None,
        run_status: str | None = None,
        run_conclusion: str | None = None,
        build_macos_job_name: str | None = None,
        build_macos_job_conclusion: str | None = None,
        reusable_workflow_invoked: bool = False,
        failure_reason: str | None = None,
    ) -> BuildNativeWorkflowDispatchObservation:
        return BuildNativeWorkflowDispatchObservation(
            repository=self._config.repository,
            workflow_path=self._config.workflow_path,
            workflow_dispatch_enabled=workflow_dispatch_enabled,
            runner_labels=self._config.required_runner_labels,
            runner_available=runner_available,
            online_runner_names=online_runner_names,
            dispatched=dispatched,
            run_id=run_id,
            run_url=run_url,
            run_status=run_status,
            run_conclusion=run_conclusion,
            build_macos_job_name=build_macos_job_name,
            build_macos_job_conclusion=build_macos_job_conclusion,
            reusable_workflow_path=self._config.reusable_workflow_path,
            reusable_workflow_invoked=reusable_workflow_invoked,
            failure_reason=failure_reason,
        )

    def _load_json(self, endpoint: str) -> dict[str, Any]:
        try:
            text = self._github_api_client.request_text(endpoint=endpoint)
        except GitHubApiClientError as error:
            raise BuildNativeWorkflowDispatchProbeError(str(error)) from error
        try:
            payload = json.loads(text or "{}")
        except json.JSONDecodeError as error:
            raise BuildNativeWorkflowDispatchProbeError(
                f"GitHub API response for {endpoint} was not valid JSON."
            ) from error
        if not isinstance(payload, dict):
            raise BuildNativeWorkflowDispatchProbeError(
                f"GitHub API response for {endpoint} was not a JSON object."
            )
        return payload

    @staticmethod
    def _read_string(payload: dict[str, Any] | None, key: str) -> str | None:
        if payload is None:
            return None
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

