from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
from typing import Any
from urllib.parse import quote

import yaml

from testing.core.config.github_accessibility_pull_request_gate_config import (
    GitHubAccessibilityPullRequestGateConfig,
)
from testing.core.interfaces.github_accessibility_pull_request_gate_probe import (
    GitHubAccessibilityPullRequestGateObservation,
    GitHubAccessibilityWorkflowContractObservation,
)
from testing.core.interfaces.github_actions_preflight_gate_probe import (
    GitHubActionsWorkflowJobObservation,
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
        workflow = self._select_workflow()
        workflow_id = workflow.get("id")
        if not isinstance(workflow_id, int):
            raise GitHubAccessibilityPullRequestGateError(
                "TS-908 could not resolve a numeric workflow ID for "
                f"{self._config.target_workflow_path}."
            )

        workflow_text = self._read_workflow_text(
            self._config.target_workflow_path,
            default_branch,
        )
        workflow_contract = self._workflow_contract(workflow_text)

        pull_request_observation = self._create_and_observe_pull_request(workflow_id)
        observed_run_jobs = self._coerce_job_observations(
            pull_request_observation.get("observed_run_jobs")
        )

        return GitHubAccessibilityPullRequestGateObservation(
            repository=self._config.repository,
            default_branch=default_branch,
            target_workflow_name=self._config.target_workflow_name,
            target_workflow_path=self._config.target_workflow_path,
            target_workflow_id=workflow_id,
            target_workflow_present_on_default_branch=True,
            target_workflow_declares_pull_request_trigger=workflow_contract.declares_pull_request_trigger,
            target_workflow_job_names=workflow_contract.job_names,
            target_workflow_step_names=workflow_contract.step_names,
            target_workflow_accessibility_job_names=workflow_contract.accessibility_job_names,
            target_workflow_downstream_job_names=workflow_contract.downstream_job_names,
            target_workflow_downstream_job_depends_on_accessibility=(
                workflow_contract.downstream_job_depends_on_accessibility
            ),
            target_workflow=workflow_contract,
            pull_request_number=int(pull_request_observation["pull_request_number"]),
            pull_request_url=str(pull_request_observation["pull_request_url"]),
            pull_request_checks_url=str(
                pull_request_observation["pull_request_checks_url"]
            ),
            pull_request_head_branch=str(
                pull_request_observation["pull_request_head_branch"]
            ),
            pull_request_head_sha=self._optional_string(
                pull_request_observation.get("pull_request_head_sha")
            ),
            pull_request_probe_path=str(
                pull_request_observation["pull_request_probe_path"]
            ),
            probe_render_host_path=str(
                pull_request_observation["probe_render_host_path"]
            ),
            probe_rendered_in_application=bool(
                pull_request_observation["probe_rendered_in_application"]
            ),
            pull_request_file_paths=list(pull_request_observation["pull_request_file_paths"]),
            pull_request_state=self._optional_string(
                pull_request_observation.get("pull_request_state")
            ),
            pull_request_mergeable_state=self._optional_string(
                pull_request_observation.get("pull_request_mergeable_state")
            ),
            pull_request_status_state=self._optional_string(
                pull_request_observation.get("pull_request_status_state")
            ),
            latest_pull_request_run_id=self._optional_int(
                pull_request_observation.get("latest_pull_request_run_id")
            ),
            latest_pull_request_run_url=self._optional_string(
                pull_request_observation.get("latest_pull_request_run_url")
            ),
            latest_pull_request_run_event=self._optional_string(
                pull_request_observation.get("latest_pull_request_run_event")
            ),
            latest_pull_request_run_status=self._optional_string(
                pull_request_observation.get("latest_pull_request_run_status")
            ),
            latest_pull_request_run_conclusion=self._optional_string(
                pull_request_observation.get("latest_pull_request_run_conclusion")
            ),
            observed_branch_run_names=list(
                pull_request_observation["observed_branch_run_names"]
            ),
            observed_branch_run_urls=list(pull_request_observation["observed_branch_run_urls"]),
            observed_branch_run_statuses=list(
                pull_request_observation["observed_branch_run_statuses"]
            ),
            observed_branch_run_conclusions=list(
                pull_request_observation["observed_branch_run_conclusions"]
            ),
            observed_run_jobs=observed_run_jobs,
            observed_job_names=list(pull_request_observation["observed_job_names"]),
            observed_step_names=list(pull_request_observation["observed_step_names"]),
            observed_status_check_names=list(
                pull_request_observation["observed_status_check_names"]
            ),
            observed_status_check_workflow_names=list(
                pull_request_observation["observed_status_check_workflow_names"]
            ),
            failed_status_check_names=list(
                pull_request_observation["failed_status_check_names"]
            ),
            failed_status_check_workflow_names=list(
                pull_request_observation["failed_status_check_workflow_names"]
            ),
            accessibility_status_check_name=self._optional_string(
                pull_request_observation.get("accessibility_status_check_name")
            ),
            accessibility_status_check_workflow_name=self._optional_string(
                pull_request_observation.get("accessibility_status_check_workflow_name")
            ),
            accessibility_status_check_status=self._optional_string(
                pull_request_observation.get("accessibility_status_check_status")
            ),
            accessibility_status_check_conclusion=self._optional_string(
                pull_request_observation.get("accessibility_status_check_conclusion")
            ),
            accessibility_status_check_url=self._optional_string(
                pull_request_observation.get("accessibility_status_check_url")
            ),
            matched_accessibility_markers=list(
                pull_request_observation["matched_accessibility_markers"]
            ),
            matched_contrast_markers=list(
                pull_request_observation["matched_contrast_markers"]
            ),
            matched_semantic_markers=list(
                pull_request_observation["matched_semantic_markers"]
            ),
            run_log_matched_accessibility_markers=list(
                pull_request_observation["run_log_matched_accessibility_markers"]
            ),
            run_log_matched_contrast_markers=list(
                pull_request_observation["run_log_matched_contrast_markers"]
            ),
            run_log_matched_semantic_markers=list(
                pull_request_observation["run_log_matched_semantic_markers"]
            ),
            run_log_mentions_accessibility=bool(
                pull_request_observation["run_log_mentions_accessibility"]
            ),
            run_log_mentions_contrast_issue=bool(
                pull_request_observation["run_log_mentions_contrast_issue"]
            ),
            run_log_mentions_semantic_issue=bool(
                pull_request_observation["run_log_mentions_semantic_issue"]
            ),
            run_log_excerpt=str(pull_request_observation["run_log_excerpt"]),
            run_log_error=self._optional_string(
                pull_request_observation.get("run_log_error")
            ),
            runtime_accessibility_surface_present=bool(
                pull_request_observation["runtime_accessibility_surface_present"]
            ),
            runtime_accessibility_surface_summary=str(
                pull_request_observation["runtime_accessibility_surface_summary"]
            ),
            probe_contains_low_contrast_indicator=bool(
                pull_request_observation["probe_contains_low_contrast_indicator"]
            ),
            probe_contains_semantic_label_indicator=bool(
                pull_request_observation["probe_contains_semantic_label_indicator"]
            ),
            probe_semantic_label=str(pull_request_observation["probe_semantic_label"]),
            probe_contrast_technique=str(
                pull_request_observation["probe_contrast_technique"]
            ),
            cleanup_closed_pull_request=bool(
                pull_request_observation["cleanup_closed_pull_request"]
            ),
            cleanup_deleted_branch=bool(
                pull_request_observation["cleanup_deleted_branch"]
            ),
            default_branch_probe_host_present=bool(
                pull_request_observation.get("default_branch_probe_host_present")
            ),
            default_branch_probe_host_summary=str(
                pull_request_observation.get("default_branch_probe_host_summary", "")
            ),
            flutter_engine_initialization_log_entries=list(
                pull_request_observation.get("flutter_engine_initialization_log_entries", [])
            ),
            flutter_engine_initialization_summary=str(
                pull_request_observation.get("flutter_engine_initialization_summary", "")
            ),
            semantics_tree_discovery_log_entries=list(
                pull_request_observation.get("semantics_tree_discovery_log_entries", [])
            ),
            semantics_tree_discovery_summary=str(
                pull_request_observation.get("semantics_tree_discovery_summary", "")
            ),
        )

    def _create_and_observe_pull_request(self, workflow_id: int) -> dict[str, object]:
        temp_repository_root = Path(tempfile.mkdtemp(prefix="ts908-"))
        pull_request_number: int | None = None
        branch_name = self._unique_branch_name()
        branch_pushed = False
        cleanup_closed_pull_request = False
        cleanup_deleted_branch = False
        observation: dict[str, object] | None = None
        (
            default_branch_probe_host_present,
            default_branch_probe_host_summary,
        ) = self._default_branch_probe_host_details(self._config.base_branch)

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

            probe_source = self._probe_source()
            probe_file = temp_repository_root / self._config.probe_path
            probe_file.parent.mkdir(parents=True, exist_ok=True)
            probe_file.write_text(probe_source, encoding="utf-8")
            render_host_file = temp_repository_root / self._config.probe_render_host_path
            render_host_original_source = render_host_file.read_text(encoding="utf-8")
            render_host_source = self._inject_probe_into_render_host(
                render_host_original_source
            )
            render_host_file.write_text(render_host_source, encoding="utf-8")

            self._run_command(
                [
                    "git",
                    "add",
                    self._config.probe_path,
                    self._config.probe_render_host_path,
                ],
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
            pull_request = self._wait_for_pull_request(pull_request_number)
            pull_request_files = self._read_pull_request_files(pull_request_number)
            head_sha = self._optional_string(((pull_request.get("head") or {}).get("sha")))
            run_observation = self._wait_for_pull_request_run(
                workflow_id,
                branch_name,
                started_at,
            )
            run_id = self._optional_int(run_observation.get("latest_pull_request_run_id"))
            jobs = self._read_jobs(run_id) if run_id is not None else []
            surface_observation = self._wait_for_pull_request_surface(
                pull_request_number,
                head_sha=head_sha,
            )
            accessibility_check = self._find_accessibility_status_check(
                surface_observation["status_checks"]
            )
            run_log_text, run_log_error = self._try_read_run_log(run_id)
            accessibility_stage_run_log_text = self._accessibility_stage_run_log_text(
                run_log_text,
                jobs,
            )
            run_log_matched_accessibility_markers = self._matched_markers(
                accessibility_stage_run_log_text,
                self._config.expected_accessibility_markers,
            )
            run_log_matched_contrast_markers = self._matched_markers(
                accessibility_stage_run_log_text,
                self._config.contrast_evidence_markers,
            )
            run_log_matched_semantic_markers = self._matched_markers(
                accessibility_stage_run_log_text,
                self._config.semantic_evidence_markers,
            )
            evidence_text = "\n".join(
                [
                    *surface_observation["status_check_names"],
                    *surface_observation["status_check_workflow_names"],
                    *self._job_names(jobs),
                    *self._step_names(jobs),
                    accessibility_stage_run_log_text,
                ]
            )
            matched_accessibility_markers = self._matched_markers(
                evidence_text,
                self._config.expected_accessibility_markers,
            )
            matched_contrast_markers = self._matched_markers(
                evidence_text,
                self._config.contrast_evidence_markers,
            )
            matched_semantic_markers = self._matched_markers(
                evidence_text,
                self._config.semantic_evidence_markers,
            )
            probe_semantic_label = self._extract_probe_semantic_label(probe_source)
            runtime_accessibility_surface_summary = (
                self._extract_runtime_accessibility_surface_summary(
                    accessibility_stage_run_log_text
                )
            )
            flutter_engine_initialization_log_entries = (
                self._extract_flutter_engine_initialization_log_entries(
                    accessibility_stage_run_log_text
                )
            )
            semantics_tree_discovery_log_entries = (
                self._extract_semantics_tree_discovery_log_entries(
                    accessibility_stage_run_log_text
                )
            )

            observation = {
                "pull_request_number": pull_request_number,
                "pull_request_url": pr_url,
                "pull_request_checks_url": f"{pr_url}/checks",
                "pull_request_head_branch": branch_name,
                "pull_request_head_sha": head_sha,
                "pull_request_probe_path": self._config.probe_path,
                "probe_render_host_path": self._config.probe_render_host_path,
                "probe_rendered_in_application": (
                    self._config.probe_path in pull_request_files
                    and (
                        self._config.probe_render_host_path in pull_request_files
                        or default_branch_probe_host_present
                        or self._render_host_renders_probe(render_host_original_source)
                        or self._render_host_renders_probe(render_host_source)
                    )
                ),
                "pull_request_file_paths": pull_request_files,
                "pull_request_state": self._optional_string(pull_request.get("state")),
                "pull_request_mergeable_state": surface_observation[
                    "pull_request_mergeable_state"
                ],
                "pull_request_status_state": surface_observation[
                    "pull_request_status_state"
                ],
                **run_observation,
                "observed_run_jobs": self._to_workflow_job_observations(jobs),
                "observed_job_names": self._job_names(jobs),
                "observed_step_names": self._step_names(jobs),
                "observed_status_check_names": surface_observation["status_check_names"],
                "observed_status_check_workflow_names": surface_observation[
                    "status_check_workflow_names"
                ],
                "failed_status_check_names": surface_observation[
                    "failed_status_check_names"
                ],
                "failed_status_check_workflow_names": surface_observation[
                    "failed_status_check_workflow_names"
                ],
                "accessibility_status_check_name": None
                if accessibility_check is None
                else accessibility_check["name"],
                "accessibility_status_check_workflow_name": None
                if accessibility_check is None
                else accessibility_check["workflow_name"],
                "accessibility_status_check_status": None
                if accessibility_check is None
                else accessibility_check["status"],
                "accessibility_status_check_conclusion": None
                if accessibility_check is None
                else accessibility_check["conclusion"],
                "accessibility_status_check_url": None
                if accessibility_check is None
                else accessibility_check["details_url"],
                "matched_accessibility_markers": matched_accessibility_markers,
                "matched_contrast_markers": matched_contrast_markers,
                "matched_semantic_markers": matched_semantic_markers,
                "run_log_matched_accessibility_markers": (
                    run_log_matched_accessibility_markers
                ),
                "run_log_matched_contrast_markers": run_log_matched_contrast_markers,
                "run_log_matched_semantic_markers": run_log_matched_semantic_markers,
                "run_log_mentions_accessibility": bool(
                    run_log_matched_accessibility_markers
                ),
                "run_log_mentions_contrast_issue": bool(
                    run_log_matched_contrast_markers
                ),
                "run_log_mentions_semantic_issue": bool(
                    run_log_matched_semantic_markers
                ),
                "run_log_excerpt": self._extract_log_excerpt(
                    accessibility_stage_run_log_text,
                    evidence_text,
                ),
                "run_log_error": run_log_error,
                "runtime_accessibility_surface_present": bool(
                    runtime_accessibility_surface_summary
                ),
                "runtime_accessibility_surface_summary": (
                    runtime_accessibility_surface_summary
                ),
                "probe_contains_low_contrast_indicator": self._probe_has_low_contrast_indicator(
                    probe_source
                ),
                "probe_contains_semantic_label_indicator": probe_semantic_label is not None,
                "probe_semantic_label": probe_semantic_label or "",
                "probe_contrast_technique": self._probe_contrast_technique(probe_source),
                "cleanup_closed_pull_request": False,
                "cleanup_deleted_branch": False,
                "default_branch_probe_host_present": default_branch_probe_host_present,
                "default_branch_probe_host_summary": default_branch_probe_host_summary,
                "flutter_engine_initialization_log_entries": (
                    flutter_engine_initialization_log_entries
                ),
                "flutter_engine_initialization_summary": self._summarize_log_entries(
                    flutter_engine_initialization_log_entries
                ),
                "semantics_tree_discovery_log_entries": (
                    semantics_tree_discovery_log_entries
                ),
                "semantics_tree_discovery_summary": self._summarize_log_entries(
                    semantics_tree_discovery_log_entries
                ),
            }
        finally:
            if pull_request_number is not None:
                cleanup_closed_pull_request = self._close_pull_request(pull_request_number)
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
            raise GitHubAccessibilityPullRequestGateError(
                "TS-908 did not produce a disposable pull request observation."
            )
        return observation

    def _select_workflow(self) -> dict[str, Any]:
        payload = self._read_json_object(
            f"/repos/{self._config.repository}/actions/workflows?per_page=100"
        )
        workflows = payload.get("workflows")
        if not isinstance(workflows, list):
            raise GitHubAccessibilityPullRequestGateError(
                "GitHub Actions workflows response did not return a workflows list."
            )
        for workflow in workflows:
            if not isinstance(workflow, dict):
                continue
            path = self._optional_string(workflow.get("path"))
            if path == self._config.target_workflow_path:
                return workflow
        raise GitHubAccessibilityPullRequestGateError(
            "TS-908 could not find the configured workflow path "
            f"{self._config.target_workflow_path} in {self._config.repository}."
        )

    def _workflow_contract(
        self,
        workflow_text: str,
    ) -> GitHubAccessibilityWorkflowContractObservation:
        parsed = yaml.load(workflow_text, Loader=yaml.BaseLoader) or {}
        if not isinstance(parsed, dict):
            raise GitHubAccessibilityPullRequestGateError(
                f"{self._config.target_workflow_path} did not deserialize to a YAML mapping."
            )

        declares_pull_request = self._event_is_declared(
            parsed.get("on"),
            event_name="pull_request",
        )
        jobs_payload = parsed.get("jobs")
        if not isinstance(jobs_payload, dict):
            return GitHubAccessibilityWorkflowContractObservation(
                declares_pull_request_trigger=declares_pull_request,
                job_names=[],
                step_names=[],
                accessibility_job_names=[],
                downstream_job_names=[],
                downstream_job_depends_on_accessibility=False,
            )

        job_names: list[str] = []
        step_names: list[str] = []
        accessibility_job_names: list[str] = []
        accessibility_job_ids: list[str] = []
        downstream_job_names: list[str] = []
        downstream_dependencies: list[str] = []
        for job_id, job_payload in jobs_payload.items():
            if not isinstance(job_payload, dict):
                continue
            job_name = self._optional_string(job_payload.get("name")) or str(job_id)
            job_names.append(job_name)
            combined = f"{job_id} {job_name}".lower()
            if self._contains_any_marker(combined, self._config.accessibility_job_markers):
                accessibility_job_names.append(job_name)
                accessibility_job_ids.append(str(job_id))
            if self._contains_any_marker(combined, self._config.downstream_job_markers):
                downstream_job_names.append(job_name)
                needs = job_payload.get("needs")
                if isinstance(needs, list):
                    downstream_dependencies.extend(str(item) for item in needs)
                elif isinstance(needs, str):
                    downstream_dependencies.append(needs)
            raw_steps = job_payload.get("steps")
            if not isinstance(raw_steps, list):
                continue
            for step_payload in raw_steps:
                if not isinstance(step_payload, dict):
                    continue
                step_name = self._optional_string(step_payload.get("name"))
                if step_name:
                    step_names.append(step_name)
        accessibility_targets = set(accessibility_job_ids + accessibility_job_names)
        return GitHubAccessibilityWorkflowContractObservation(
            declares_pull_request_trigger=declares_pull_request,
            job_names=self._dedupe(job_names),
            step_names=self._dedupe(step_names),
            accessibility_job_names=self._dedupe(accessibility_job_names),
            downstream_job_names=self._dedupe(downstream_job_names),
            downstream_job_depends_on_accessibility=any(
                dependency in accessibility_targets for dependency in downstream_dependencies
            ),
        )

    def _read_workflow_text(self, workflow_path: str, ref: str) -> str:
        return self._github_api_client.request_text(
            endpoint=(
                f"/repos/{self._config.repository}/contents/"
                f"{quote(workflow_path, safe='/')}?ref={quote(ref, safe='')}"
            ),
            field_args=["-H", "Accept: application/vnd.github.raw+json"],
        )

    def _read_repository_file_text(self, file_path: str, ref: str) -> str:
        return self._github_api_client.request_text(
            endpoint=(
                f"/repos/{self._config.repository}/contents/"
                f"{quote(file_path, safe='/')}?ref={quote(ref, safe='')}"
            ),
            field_args=["-H", "Accept: application/vnd.github.raw+json"],
        )

    def _default_branch_probe_host_details(self, ref: str) -> tuple[bool, str]:
        try:
            source = self._read_repository_file_text(self._config.probe_render_host_path, ref)
        except GitHubApiClientError as error:
            return (
                False,
                f"Could not read {self._config.probe_render_host_path}@{ref}: {error}",
            )

        matched_indicators: list[str] = []
        probe_widget_name = self._probe_widget_name()
        rendered_probe_app_class_name = self._rendered_probe_app_class_name()
        if probe_widget_name in source:
            matched_indicators.append(probe_widget_name)
        if rendered_probe_app_class_name in source:
            matched_indicators.append(rendered_probe_app_class_name)

        if not matched_indicators:
            return (
                False,
                f"{self._config.probe_render_host_path}@{ref} did not expose "
                f"{probe_widget_name} or {rendered_probe_app_class_name}.",
            )

        return (
            True,
            f"{self._config.probe_render_host_path}@{ref} already exposed "
            f"{', '.join(matched_indicators)}.",
        )

    def _wait_for_pull_request_run(
        self,
        workflow_id: int,
        branch_name: str,
        started_at: float,
    ) -> dict[str, object]:
        deadline = time.time() + self._config.run_timeout_seconds
        latest_runs: list[dict[str, Any]] = []
        latest_run: dict[str, Any] | None = None

        while time.time() < deadline:
            latest_runs = self._list_branch_runs(branch_name, started_at)
            latest_run = self._find_target_run(latest_runs, workflow_id)
            if latest_run is not None and self._optional_string(latest_run.get("status")) == "completed":
                break
            time.sleep(self._config.poll_interval_seconds)

        return {
            "latest_pull_request_run_id": None
            if latest_run is None
            else self._optional_int(latest_run.get("id")),
            "latest_pull_request_run_url": None
            if latest_run is None
            else self._optional_string(latest_run.get("html_url")),
            "latest_pull_request_run_event": None
            if latest_run is None
            else self._optional_string(latest_run.get("event")),
            "latest_pull_request_run_status": None
            if latest_run is None
            else self._optional_string(latest_run.get("status")),
            "latest_pull_request_run_conclusion": None
            if latest_run is None
            else self._optional_string(latest_run.get("conclusion")),
            "observed_branch_run_names": self._run_names(latest_runs),
            "observed_branch_run_urls": self._run_urls(latest_runs),
            "observed_branch_run_statuses": self._run_statuses(latest_runs),
            "observed_branch_run_conclusions": self._run_conclusions(latest_runs),
        }

    def _wait_for_pull_request(self, pull_request_number: int) -> dict[str, Any]:
        deadline = time.time() + self._config.pull_request_timeout_seconds
        latest: dict[str, Any] | None = None
        while time.time() < deadline:
            latest = self._try_read_json_object(
                f"/repos/{self._config.repository}/pulls/{pull_request_number}"
            )
            if latest is None:
                time.sleep(self._config.poll_interval_seconds)
                continue
            head_sha = self._optional_string(((latest.get("head") or {}).get("sha")))
            if head_sha:
                return latest
            time.sleep(self._config.poll_interval_seconds)
        if latest is None:
            raise GitHubAccessibilityPullRequestGateError(
                f"TS-908 could not read pull request #{pull_request_number}."
            )
        return latest

    def _wait_for_pull_request_surface(
        self,
        pull_request_number: int,
        *,
        head_sha: str | None,
    ) -> dict[str, object]:
        deadline = time.time() + self._config.pull_request_timeout_seconds
        latest_state = {
            "pull_request_mergeable_state": None,
            "pull_request_status_state": None,
            "status_checks": [],
            "status_check_names": [],
            "status_check_workflow_names": [],
            "failed_status_check_names": [],
            "failed_status_check_workflow_names": [],
        }

        while time.time() < deadline:
            pull_request = self._try_read_json_object(
                f"/repos/{self._config.repository}/pulls/{pull_request_number}"
            )
            if pull_request is None:
                time.sleep(self._config.poll_interval_seconds)
                continue
            sha = self._optional_string(((pull_request.get("head") or {}).get("sha"))) or head_sha
            mergeable_state = self._optional_string(pull_request.get("mergeable_state"))
            status_state = self._read_check_runs_state(sha) if sha else None
            surface = self._read_pull_request_status_surface(pull_request_number)
            latest_state = {
                "pull_request_mergeable_state": mergeable_state,
                "pull_request_status_state": status_state,
                "status_checks": surface["status_checks"],
                "status_check_names": surface["status_check_names"],
                "status_check_workflow_names": surface["status_check_workflow_names"],
                "failed_status_check_names": surface["failed_status_check_names"],
                "failed_status_check_workflow_names": surface[
                    "failed_status_check_workflow_names"
                ],
            }
            if (
                mergeable_state
                and mergeable_state != "unknown"
                and status_state
                and status_state != "pending"
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
            raise GitHubAccessibilityPullRequestGateError(
                f"TS-908 expected gh pr view to return an object: {payload!r}"
            )
        normalized_checks = self._normalize_status_checks(payload.get("statusCheckRollup"))
        return {
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
            "failed_status_check_names": self._dedupe(
                [
                    check["name"]
                    for check in normalized_checks
                    if isinstance(check.get("name"), str)
                    and check.get("conclusion")
                    in {"failure", "cancelled", "timed_out", "action_required"}
                ]
            ),
            "failed_status_check_workflow_names": self._dedupe(
                [
                    check["workflow_name"]
                    for check in normalized_checks
                    if isinstance(check.get("workflow_name"), str)
                    and check.get("conclusion")
                    in {"failure", "cancelled", "timed_out", "action_required"}
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

    def _find_accessibility_status_check(
        self,
        status_checks: list[dict[str, str | None]],
    ) -> dict[str, str | None] | None:
        for check in status_checks:
            combined = " ".join(
                value
                for value in (check.get("name"), check.get("workflow_name"))
                if isinstance(value, str)
            )
            if self._matched_markers(combined, self._config.expected_accessibility_markers):
                return check
        return None

    def _read_check_runs_state(self, head_sha: str) -> str | None:
        payload = self._read_json_object(
            f"/repos/{self._config.repository}/commits/{head_sha}/check-runs?per_page=100"
        )
        check_runs = payload.get("check_runs")
        if isinstance(check_runs, list) and check_runs:
            runs_to_consider = [run for run in check_runs if isinstance(run, dict)]
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
            success_conclusions = {"success"}
            if all(
                self._optional_string(run.get("conclusion")) in success_conclusions
                for run in runs_to_consider
            ):
                return "success"
        payload = self._read_json_object(
            f"/repos/{self._config.repository}/commits/{head_sha}/status"
        )
        return self._optional_string(payload.get("state"))

    def _read_pull_request_files(self, pull_request_number: int) -> list[str]:
        payload = self._read_json_array(
            f"/repos/{self._config.repository}/pulls/{pull_request_number}/files?per_page=100"
        )
        paths: list[str] = []
        for entry in payload:
            if not isinstance(entry, dict):
                continue
            filename = self._optional_string(entry.get("filename"))
            if filename:
                paths.append(filename)
        return self._dedupe(paths)

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
            raise GitHubAccessibilityPullRequestGateError(
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

    def _find_target_run(
        self,
        runs: list[dict[str, Any]],
        workflow_id: int,
    ) -> dict[str, Any] | None:
        for run in runs:
            if self._optional_int(run.get("workflow_id")) == workflow_id:
                return run
        return None

    def _read_jobs(self, run_id: int) -> list[dict[str, Any]]:
        payload = self._read_json_object(
            f"/repos/{self._config.repository}/actions/runs/{run_id}/jobs?per_page=100"
        )
        jobs = payload.get("jobs")
        if not isinstance(jobs, list):
            raise GitHubAccessibilityPullRequestGateError(
                f"GitHub Actions jobs response for run {run_id} did not return a list."
            )
        return [job for job in jobs if isinstance(job, dict)]

    def _to_workflow_job_observations(
        self,
        jobs: list[dict[str, Any]],
    ) -> list[GitHubActionsWorkflowJobObservation]:
        return [
            job
            for entry in jobs
            if (job := self._coerce_job_observation(entry)) is not None
        ]

    def _coerce_job_observations(
        self,
        raw_jobs: object,
    ) -> list[GitHubActionsWorkflowJobObservation]:
        if not isinstance(raw_jobs, list):
            return []
        return [
            job
            for entry in raw_jobs
            if (job := self._coerce_job_observation(entry)) is not None
        ]

    def _coerce_job_observation(
        self,
        entry: object,
    ) -> GitHubActionsWorkflowJobObservation | None:
        if isinstance(entry, GitHubActionsWorkflowJobObservation):
            return entry
        if not isinstance(entry, dict):
            return None
        job_id = entry.get("id")
        if not isinstance(job_id, int):
            return None
        return GitHubActionsWorkflowJobObservation(
            id=job_id,
            name=self._optional_string(entry.get("name")) or "",
            status=self._optional_string(entry.get("status")),
            conclusion=self._optional_string(entry.get("conclusion")),
            html_url=self._optional_string(entry.get("html_url")) or "",
            started_at=self._optional_string(entry.get("started_at")),
            completed_at=self._optional_string(entry.get("completed_at")),
        )

    def _try_read_run_log(self, run_id: int | None) -> tuple[str, str | None]:
        if run_id is None:
            return "", None
        try:
            return (
                self._run_command(
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
                ).stdout,
                None,
            )
        except GitHubAccessibilityPullRequestGateError as error:
            return "", str(error)

    def _matched_markers(self, text: str, markers: list[str]) -> list[str]:
        normalized = text.lower()
        matches = [marker for marker in markers if marker.lower() in normalized]
        return self._dedupe(matches)

    def _accessibility_job_names(self, jobs: list[dict[str, Any]]) -> list[str]:
        accessibility_job_names: list[str] = []
        for job in jobs:
            name = job.get("name")
            if not isinstance(name, str) or not name.strip():
                continue
            if self._contains_any_marker(name, self._config.accessibility_job_markers):
                accessibility_job_names.append(name.strip())
        return self._dedupe(accessibility_job_names)

    @staticmethod
    def _extract_probe_semantic_label(probe_source: str) -> str | None:
        match = re.search(r"label:\s*['\"](?P<label>[^'\"]+)['\"]", probe_source)
        if match is None:
            return None
        return match.group("label")

    @staticmethod
    def _probe_contrast_technique(probe_source: str) -> str:
        if "final lowContrastColor = colorScheme.surface;" in " ".join(probe_source.split()):
            return (
                "Uses `colorScheme.surface` text on `colorScheme.surface` to guarantee a "
                "WCAG contrast failure while remaining theme-token-safe."
            )
        if "withAlpha(89)" in probe_source and "colorScheme.surface" in probe_source:
            return (
                "Uses `colorScheme.onSurface.withAlpha(89)` text on "
                "`colorScheme.surface` to reduce contrast while remaining theme-token-safe."
            )
        return (
            "Uses `colorScheme.onSurface.withAlpha(89)` text on "
            "`colorScheme.surface` or an equivalent theme-token-safe low-contrast signal."
        )

    @staticmethod
    def _probe_has_low_contrast_indicator(probe_source: str) -> bool:
        normalized = " ".join(probe_source.split())
        return (
            "final lowContrastColor = colorScheme.surface;" in normalized
            or (
                "withAlpha(89)" in probe_source and "colorScheme.surface" in probe_source
            )
        )

    @staticmethod
    def _probe_has_low_contrast_indicator(probe_source: str) -> bool:
        normalized = " ".join(probe_source.split())
        return (
            "final lowContrastColor = colorScheme.surface;" in normalized
            or (
                "withAlpha(89)" in probe_source and "colorScheme.surface" in probe_source
            )
        )

    def _extract_runtime_accessibility_surface_summary(self, run_log_text: str) -> str:
        for line in self._extract_matching_log_lines(
            run_log_text,
            markers=["accessibility runtime surface ready"],
        ):
            return line
        return ""

    def _extract_flutter_engine_initialization_log_entries(
        self,
        run_log_text: str,
    ) -> list[str]:
        return self._extract_matching_log_lines(
            run_log_text,
            markers=["flutter engine initialization"],
        )

    def _extract_semantics_tree_discovery_log_entries(
        self,
        run_log_text: str,
    ) -> list[str]:
        return self._extract_matching_log_lines(
            run_log_text,
            markers=[
                "semantics tree discovery",
                "accessibility runtime surface ready",
            ],
        )

    def _extract_matching_log_lines(
        self,
        run_log_text: str,
        *,
        markers: list[str],
    ) -> list[str]:
        if not run_log_text.strip():
            return []

        lowered_markers = [marker.lower() for marker in markers if marker.strip()]
        matches: list[str] = []
        for raw_line in run_log_text.splitlines():
            normalized_line = " ".join(raw_line.split()).strip()
            if not normalized_line:
                continue
            if any(
                self._line_contains_runtime_marker(normalized_line, marker)
                for marker in lowered_markers
            ):
                matches.append(self._snippet(normalized_line, limit=300))
        return self._dedupe(matches)

    @staticmethod
    def _line_contains_runtime_marker(normalized_line: str, marker: str) -> bool:
        lowered_line = normalized_line.lower()
        marker = marker.lower().strip()
        if not marker:
            return False
        return lowered_line.startswith(marker) or bool(
            re.search(
                r"\d{4}-\d{2}-\d{2}t[\d:.]+z\s+" + re.escape(marker),
                lowered_line,
            )
        )

    def _summarize_log_entries(self, entries: list[str]) -> str:
        if not entries:
            return ""
        return self._snippet(" | ".join(entries[:3]), limit=400)

    def _extract_log_excerpt(self, run_log_text: str, fallback_text: str) -> str:
        text = run_log_text or fallback_text
        if not text.strip():
            return ""
        lowered = text.lower()
        failure_markers = [
            "test timeout",
            "page.waitforfunction",
            "##[error]",
            "error context:",
            "1 failed",
            "process completed with exit code 1",
        ]
        for marker in failure_markers:
            index = lowered.find(marker)
            if index >= 0:
                start = max(index - 200, 0)
                end = min(index + 800, len(text))
                return self._snippet(text[start:end], limit=1000)
        preferred_runtime_markers = [
            "flutter engine initialization",
            "semantics tree discovery",
            "accessibility runtime surface ready",
        ]
        for marker in preferred_runtime_markers:
            index = lowered.find(marker)
            if index >= 0:
                start = max(index - 200, 0)
                end = min(index + 800, len(text))
                return self._snippet(text[start:end], limit=1000)
        markers = [
            *self._config.expected_accessibility_markers,
            *self._config.contrast_evidence_markers,
            *self._config.semantic_evidence_markers,
        ]
        for marker in markers:
            index = lowered.find(marker.lower())
            if index >= 0:
                start = max(index - 200, 0)
                end = min(index + 600, len(text))
                return self._snippet(text[start:end], limit=800)
        return self._snippet(text, limit=800)

    def _accessibility_stage_run_log_text(
        self,
        run_log_text: str,
        jobs: list[dict[str, Any]],
    ) -> str:
        if not run_log_text.strip():
            return ""
        accessibility_job_names = self._accessibility_job_names(jobs)
        if not accessibility_job_names:
            return ""

        scoped_lines: list[str] = []
        for raw_line in run_log_text.splitlines():
            normalized_line = " ".join(raw_line.split()).strip()
            if not normalized_line:
                continue
            if self._line_belongs_to_any_job(
                normalized_line,
                accessibility_job_names,
            ):
                scoped_lines.append(normalized_line)
        return "\n".join(scoped_lines)

    def _close_pull_request(self, pull_request_number: int) -> bool:
        try:
            self._read_json_object(
                f"/repos/{self._config.repository}/pulls/{pull_request_number}",
                method="PATCH",
                field_args=["-f", "state=closed"],
            )
        except GitHubAccessibilityPullRequestGateError:
            return False
        return True

    def _delete_branch(self, branch_name: str, *, cwd: Path) -> bool:
        try:
            self._run_command(["git", "push", "origin", "--delete", branch_name], cwd=cwd)
        except GitHubAccessibilityPullRequestGateError:
            return False
        return True

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
            raise GitHubAccessibilityPullRequestGateError(
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
            raise GitHubAccessibilityPullRequestGateError(
                f"Expected a JSON object from gh api {endpoint}, got {type(payload)}."
            )
        return payload

    def _try_read_json_object(
        self,
        endpoint: str,
        *,
        method: str = "GET",
        field_args: list[str] | None = None,
    ) -> dict[str, Any] | None:
        try:
            return self._read_json_object(endpoint, method=method, field_args=field_args)
        except GitHubAccessibilityPullRequestGateError as error:
            if "HTTP 404" in str(error):
                return None
            raise

    def _read_json_array(self, endpoint: str) -> list[Any]:
        payload = self._read_json(endpoint)
        if not isinstance(payload, list):
            raise GitHubAccessibilityPullRequestGateError(
                f"Expected a JSON array from gh api {endpoint}, got {type(payload)}."
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
            raise GitHubAccessibilityPullRequestGateError(str(error)) from error
        return json.loads(response_text)

    def _extract_pull_request_number(self, pull_request_url: str) -> int:
        match = re.search(r"/pull/(\d+)$", pull_request_url.strip())
        if match is None:
            raise GitHubAccessibilityPullRequestGateError(
                "gh pr create did not return a pull request URL ending in /pull/<number>: "
                f"{pull_request_url}"
            )
        return int(match.group(1))

    def _origin_clone_url(self) -> str:
        return f"https://github.com/{self._config.repository}.git"

    def _unique_branch_name(self) -> str:
        timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"{self._config.branch_prefix}-{timestamp}"

    @staticmethod
    def _probe_source() -> str:
        return """import 'package:flutter/material.dart';

import 'ui/features/tracker/services/accessibility_probe_signal.dart';

class Ts908ProbeSurface extends StatelessWidget {
  const Ts908ProbeSurface({super.key});

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final textStyle = Theme.of(context).textTheme.bodyMedium;
    final lowContrastColor = colorScheme.surface;
    const probeText = 'Sync issue';
    const semanticsLabel = 'button';

    publishAccessibilityContrastProbeSignal(
      text: probeText,
      semanticsLabel: semanticsLabel,
      foreground: lowContrastColor,
      background: colorScheme.surface,
    );

    return Semantics(
      label: semanticsLabel,
      button: true,
      child: Container(
        color: colorScheme.surface,
        padding: const EdgeInsets.all(12),
        child: Text(
          probeText,
          style: textStyle?.copyWith(color: lowContrastColor) ??
              TextStyle(color: lowContrastColor),
        ),
      ),
    );
  }
}
"""

    def _inject_probe_into_render_host(self, source: str) -> str:
        probe_widget_name = self._probe_widget_name()
        rendered_probe_app_class_name = self._rendered_probe_app_class_name()
        probe_import = f"import '{Path(self._config.probe_path).name}';"

        if (
            probe_widget_name in source
            or rendered_probe_app_class_name in source
        ):
            if probe_import in source:
                return source

            updated_source, replacements = re.subn(
                r"^import '[^']+_probe_surface\.dart';\n",
                f"{probe_import}\n",
                source,
                count=1,
                flags=re.MULTILINE,
            )
            if replacements > 0:
                return updated_source

            source = source.replace(
                "import 'ui/features/tracker/views/trackstate_app.dart';\n",
                "import 'ui/features/tracker/views/trackstate_app.dart';\n"
                f"{probe_import}\n",
            )
            return source

        if "package:flutter/material.dart" not in source:
            source = source.replace(
                "import 'package:flutter/widgets.dart';",
                "import 'package:flutter/material.dart';",
            )
        if "package:flutter/material.dart" not in source:
            source = "import 'package:flutter/material.dart';\n\n" + source.lstrip()

        if probe_import not in source:
            source = source.replace(
                "import 'ui/features/tracker/views/trackstate_app.dart';\n",
                "import 'ui/features/tracker/views/trackstate_app.dart';\n"
                f"{probe_import}\n",
            )

        run_app_match = re.search(
            r"runApp\(\s*(?P<child>[\s\S]*?)\s*\);\s*",
            source,
        )
        if run_app_match is None:
            raise GitHubAccessibilityPullRequestGateError(
                "TS-908 could not patch lib/main.dart to render the disposable probe."
            )
        original_child = run_app_match.group("child").strip()
        if "TrackStateApp" not in original_child:
            raise GitHubAccessibilityPullRequestGateError(
                "TS-908 could not find the TrackStateApp runApp target in lib/main.dart."
            )
        updated_source = self._replace_run_app_call(
            source,
            replacement=f"runApp({rendered_probe_app_class_name}(child: {original_child}));",
        )
        if updated_source is None:
            raise GitHubAccessibilityPullRequestGateError(
                "TS-908 could not patch lib/main.dart to render the disposable probe."
            )

        return (
            updated_source.rstrip()
            + "\n\n"
            + """class {app_class} extends StatelessWidget {{
  const {app_class}({{required this.child}});

  final Widget child;

  @override
  Widget build(BuildContext context) {{
    assert(() {{
      debugPrint(
        'Accessibility probe preserved original app entrypoint: ${{child.runtimeType}}',
      );
      return true;
    }}());
    return MaterialApp(
      title: 'TrackState.AI',
      home: Scaffold(
        body: Align(
          alignment: Alignment.topLeft,
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: const {probe_widget}(),
          ),
        ),
      ),
    );
  }}
}}
""".format(
                app_class=rendered_probe_app_class_name,
                probe_widget=probe_widget_name,
            )
        )

    @staticmethod
    def _replace_run_app_call(source: str, *, replacement: str) -> str | None:
        start = source.find("runApp(")
        if start < 0:
            return None

        index = start + len("runApp(")
        depth = 1
        while index < len(source):
            character = source[index]
            if character == "(":
                depth += 1
            elif character == ")":
                depth -= 1
                if depth == 0:
                    end = index + 1
                    break
            index += 1
        else:
            return None

        while end < len(source) and source[end].isspace():
            end += 1
        if end >= len(source) or source[end] != ";":
            return None

        return source[:start] + replacement + source[end + 1 :]

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
    def _default_branch(repository_info: dict[str, Any]) -> str:
        default_branch = repository_info.get("default_branch")
        if isinstance(default_branch, str) and default_branch.strip():
            return default_branch.strip()
        return "main"

    @staticmethod
    def _event_is_declared(on_payload: object, *, event_name: str) -> bool:
        if isinstance(on_payload, dict):
            return event_name in on_payload
        if isinstance(on_payload, list):
            return event_name in on_payload
        if isinstance(on_payload, str):
            return on_payload == event_name
        return False

    @staticmethod
    def _is_contributor_visible_pull_request_event(event: str | None) -> bool:
        return event in {"pull_request", "pull_request_target"}

    @staticmethod
    def _run_created_at_epoch(run: dict[str, Any]) -> float | None:
        created_at = run.get("created_at")
        if not isinstance(created_at, str) or not created_at.strip():
            return None
        try:
            return datetime.fromisoformat(created_at.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return None

    @staticmethod
    def _run_names(runs: list[dict[str, Any]]) -> list[str]:
        return [
            name
            for run in runs
            if isinstance((name := run.get("name")), str) and name.strip()
        ]

    @staticmethod
    def _run_urls(runs: list[dict[str, Any]]) -> list[str]:
        return [
            url
            for run in runs
            if isinstance((url := run.get("html_url")), str) and url.strip()
        ]

    @staticmethod
    def _run_statuses(runs: list[dict[str, Any]]) -> list[str]:
        return [
            status
            for run in runs
            if isinstance((status := run.get("status")), str) and status.strip()
        ]

    @staticmethod
    def _run_conclusions(runs: list[dict[str, Any]]) -> list[str]:
        return [
            conclusion
            for run in runs
            if isinstance((conclusion := run.get("conclusion")), str)
            and conclusion.strip()
        ]

    @staticmethod
    def _optional_string(value: object) -> str | None:
        if not isinstance(value, str):
            return None
        stripped = value.strip()
        return stripped or None

    @staticmethod
    def _optional_int(value: object) -> int | None:
        return value if isinstance(value, int) else None

    @staticmethod
    def _normalize_case(value: object) -> str | None:
        if not isinstance(value, str):
            return None
        stripped = value.strip()
        return stripped.lower() or None

    @staticmethod
    def _contains_any_marker(text: str, markers: list[str]) -> bool:
        lowered = text.lower()
        return any(marker.lower() in lowered for marker in markers if marker.strip())

    @staticmethod
    def _line_belongs_to_any_job(normalized_line: str, job_names: list[str]) -> bool:
        lowered_line = normalized_line.lower()
        for job_name in job_names:
            stripped_name = job_name.strip()
            if not stripped_name:
                continue
            lowered_job_name = stripped_name.lower()
            if (
                lowered_line == lowered_job_name
                or lowered_line.startswith(f"{lowered_job_name} ")
            ):
                return True
        return False

    def _render_host_renders_probe(self, render_host_source: str) -> bool:
        probe_import = Path(self._config.probe_path).name
        probe_widget_name = self._probe_widget_name()
        return probe_import in render_host_source and probe_widget_name in render_host_source

    @staticmethod
    def _dedupe(values: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            if value in seen:
                continue
            seen.add(value)
            result.append(value)
        return result

    @staticmethod
    def _snippet(text: str, *, limit: int) -> str:
        normalized = " ".join(text.split())
        if len(normalized) <= limit:
            return normalized
        return normalized[: limit - 3] + "..."

    @staticmethod
    def _probe_widget_name() -> str:
        return "Ts908ProbeSurface"

    @staticmethod
    def _rendered_probe_app_class_name() -> str:
        return "_Ts908RenderedProbeApp"

    @staticmethod
    def _rendered_probe_overlay_class_name() -> str:
        return "_Ts908ProbeOverlay"
