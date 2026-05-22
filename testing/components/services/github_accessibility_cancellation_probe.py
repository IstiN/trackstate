from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import shutil
import tempfile
import time

from testing.components.services.github_accessibility_pull_request_gate_probe import (
    GitHubAccessibilityPullRequestGateError,
    GitHubAccessibilityPullRequestGateProbeService,
)
from testing.core.interfaces.github_accessibility_cancellation_probe import (
    GitHubAccessibilityCancellationProbeObservation,
)
from testing.core.interfaces.github_workflow_step_sequence_inspector import (
    GitHubWorkflowRunStepObservation,
)


class GitHubAccessibilityCancellationProbeService(
    GitHubAccessibilityPullRequestGateProbeService
):
    helper_require_statement = (
        "const {\n"
        "  holdTs962CancellationWindow,\n"
        "} = require('./ts962_accessibility_cancellation_delay');"
    )
    simulation_call = "  await holdTs962CancellationWindow();"
    hold_start_marker = "TS-962 cancellation hold started"
    hold_finish_marker = "TS-962 cancellation hold completed"
    simulation_technique = (
        "Adds a disposable delay inside the hosted accessibility Playwright spec so the "
        "`Run axe-core accessibility checks` step stays in progress long enough to cancel "
        "the live GitHub Actions run and observe whether `log-validation` still starts."
    )

    def __init__(
        self,
        config,
        *,
        github_api_client,
        accessibility_job_name: str,
        axe_step_name: str,
        log_validation_step_name: str,
        cancellation_hold_seconds: int,
    ) -> None:
        super().__init__(config, github_api_client=github_api_client)
        self._accessibility_job_name = accessibility_job_name
        self._axe_step_name = axe_step_name
        self._log_validation_step_name = log_validation_step_name
        self._cancellation_hold_seconds = cancellation_hold_seconds
        self._latest_details: dict[str, object] | None = None

    def validate(self) -> GitHubAccessibilityCancellationProbeObservation:
        self._latest_details = None
        workflow_observation = super().validate()
        details = self._latest_details
        if details is None:
            raise GitHubAccessibilityPullRequestGateError(
                "TS-962 did not retain cancellation details after validation."
            )
        return GitHubAccessibilityCancellationProbeObservation(
            workflow_observation=workflow_observation,
            cancellation_requested=bool(details.get("cancellation_requested")),
            cancellation_requested_at=self._optional_string(
                details.get("cancellation_requested_at")
            ),
            cancellation_request_error=self._optional_string(
                details.get("cancellation_request_error")
            ),
            pre_cancel_axe_step=self._coerce_step_observation(
                details.get("pre_cancel_axe_step")
            ),
            pre_cancel_log_validation_step=self._coerce_step_observation(
                details.get("pre_cancel_log_validation_step")
            ),
            post_cancel_axe_step=self._coerce_step_observation(
                details.get("post_cancel_axe_step")
            ),
            post_cancel_log_validation_step=self._coerce_step_observation(
                details.get("post_cancel_log_validation_step")
            ),
            observed_job_names_pre_cancel=list(
                details.get("observed_job_names_pre_cancel", [])
            ),
            observed_step_names_pre_cancel=list(
                details.get("observed_step_names_pre_cancel", [])
            ),
            observed_job_names_post_cancel=list(
                details.get("observed_job_names_post_cancel", [])
            ),
            observed_step_names_post_cancel=list(
                details.get("observed_step_names_post_cancel", [])
            ),
            step_poll_trace=list(details.get("step_poll_trace", [])),
            run_status_trace=list(details.get("run_status_trace", [])),
        )

    def _create_and_observe_pull_request(self, workflow_id: int) -> dict[str, object]:
        temp_repository_root = Path(tempfile.mkdtemp(prefix="ts962-"))
        pull_request_number: int | None = None
        branch_name = self._unique_branch_name()
        branch_pushed = False
        cleanup_closed_pull_request = False
        cleanup_deleted_branch = False
        observation: dict[str, object] | None = None
        details: dict[str, object] | None = None

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

            helper_file = temp_repository_root / self._config.probe_path
            helper_file.parent.mkdir(parents=True, exist_ok=True)
            helper_file.write_text(self._simulation_helper_source(), encoding="utf-8")

            spec_file = temp_repository_root / self._config.probe_render_host_path
            original_spec_source = spec_file.read_text(encoding="utf-8")
            spec_file.write_text(
                self._patch_spec_source(original_spec_source),
                encoding="utf-8",
            )

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

            initial_run, initial_branch_runs = self._wait_for_run_to_appear(
                workflow_id,
                branch_name,
                started_at,
            )
            run_id = self._optional_int(initial_run.get("id"))
            if run_id is None:
                raise GitHubAccessibilityPullRequestGateError(
                    "TS-962 could not resolve the live workflow run ID before cancellation."
                )

            (
                pre_cancel_jobs,
                pre_cancel_axe_step,
                pre_cancel_log_validation_step,
                step_poll_trace,
            ) = self._wait_for_axe_step_in_progress(run_id)

            cancellation_requested_at = datetime.now(tz=timezone.utc).isoformat()
            cancellation_requested = False
            cancellation_request_error: str | None = None
            try:
                self._run_command(
                    [
                        "gh",
                        "run",
                        "cancel",
                        str(run_id),
                        "--repo",
                        self._config.repository,
                    ],
                    cwd=None,
                )
                cancellation_requested = True
            except GitHubAccessibilityPullRequestGateError as error:
                cancellation_request_error = str(error)

            final_run, run_status_trace = self._wait_for_run_completion(run_id)
            post_cancel_jobs = self._read_jobs(run_id)
            post_cancel_axe_step = self._find_run_step_observation(
                post_cancel_jobs,
                job_name=self._accessibility_job_name,
                step_name=self._axe_step_name,
            )
            post_cancel_log_validation_step = self._find_run_step_observation(
                post_cancel_jobs,
                job_name=self._accessibility_job_name,
                step_name=self._log_validation_step_name,
            )
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
                post_cancel_jobs,
            )
            evidence_text = "\n".join(
                [
                    *surface_observation["status_check_names"],
                    *surface_observation["status_check_workflow_names"],
                    *self._job_names(post_cancel_jobs),
                    *self._step_names(post_cancel_jobs),
                    accessibility_stage_run_log_text,
                ]
            )
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
            latest_branch_runs = self._list_branch_runs(branch_name, started_at)

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
                    and self._config.probe_render_host_path in pull_request_files
                ),
                "pull_request_file_paths": pull_request_files,
                "pull_request_state": self._optional_string(pull_request.get("state")),
                "pull_request_mergeable_state": surface_observation[
                    "pull_request_mergeable_state"
                ],
                "pull_request_status_state": surface_observation[
                    "pull_request_status_state"
                ],
                "latest_pull_request_run_id": run_id,
                "latest_pull_request_run_url": self._optional_string(
                    final_run.get("html_url")
                ),
                "latest_pull_request_run_event": self._optional_string(
                    final_run.get("event")
                ),
                "latest_pull_request_run_status": self._optional_string(
                    final_run.get("status")
                ),
                "latest_pull_request_run_conclusion": self._optional_string(
                    final_run.get("conclusion")
                ),
                "observed_branch_run_names": self._run_names(
                    latest_branch_runs or initial_branch_runs
                ),
                "observed_branch_run_urls": self._run_urls(
                    latest_branch_runs or initial_branch_runs
                ),
                "observed_branch_run_statuses": self._run_statuses(
                    latest_branch_runs or initial_branch_runs
                ),
                "observed_branch_run_conclusions": self._run_conclusions(
                    latest_branch_runs or initial_branch_runs
                ),
                "observed_run_jobs": self._to_workflow_job_observations(post_cancel_jobs),
                "observed_job_names": self._job_names(post_cancel_jobs),
                "observed_step_names": self._step_names(post_cancel_jobs),
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
                "matched_accessibility_markers": self._matched_markers(
                    evidence_text,
                    self._config.expected_accessibility_markers,
                ),
                "matched_contrast_markers": self._matched_markers(
                    evidence_text,
                    self._config.contrast_evidence_markers,
                ),
                "matched_semantic_markers": self._matched_markers(
                    evidence_text,
                    self._config.semantic_evidence_markers,
                ),
                "run_log_matched_accessibility_markers": self._matched_markers(
                    accessibility_stage_run_log_text,
                    self._config.expected_accessibility_markers,
                ),
                "run_log_matched_contrast_markers": self._matched_markers(
                    accessibility_stage_run_log_text,
                    self._config.contrast_evidence_markers,
                ),
                "run_log_matched_semantic_markers": self._matched_markers(
                    accessibility_stage_run_log_text,
                    self._config.semantic_evidence_markers,
                ),
                "run_log_mentions_accessibility": bool(
                    self._matched_markers(
                        accessibility_stage_run_log_text,
                        self._config.expected_accessibility_markers,
                    )
                ),
                "run_log_mentions_contrast_issue": bool(
                    self._matched_markers(
                        accessibility_stage_run_log_text,
                        self._config.contrast_evidence_markers,
                    )
                ),
                "run_log_mentions_semantic_issue": bool(
                    self._matched_markers(
                        accessibility_stage_run_log_text,
                        self._config.semantic_evidence_markers,
                    )
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
                "probe_contains_low_contrast_indicator": False,
                "probe_contains_semantic_label_indicator": False,
                "probe_semantic_label": "",
                "probe_contrast_technique": self.simulation_technique,
                "cleanup_closed_pull_request": False,
                "cleanup_deleted_branch": False,
                "default_branch_probe_host_present": True,
                "default_branch_probe_host_summary": (
                    f"{self._config.probe_render_host_path}@{self._config.base_branch} "
                    "was patched in the disposable PR to hold the accessibility step open "
                    "for cancellation."
                ),
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
            details = {
                "cancellation_requested": cancellation_requested,
                "cancellation_requested_at": cancellation_requested_at,
                "cancellation_request_error": cancellation_request_error,
                "pre_cancel_axe_step": None
                if pre_cancel_axe_step is None
                else asdict(pre_cancel_axe_step),
                "pre_cancel_log_validation_step": None
                if pre_cancel_log_validation_step is None
                else asdict(pre_cancel_log_validation_step),
                "post_cancel_axe_step": None
                if post_cancel_axe_step is None
                else asdict(post_cancel_axe_step),
                "post_cancel_log_validation_step": None
                if post_cancel_log_validation_step is None
                else asdict(post_cancel_log_validation_step),
                "observed_job_names_pre_cancel": self._job_names(pre_cancel_jobs),
                "observed_step_names_pre_cancel": self._step_names(pre_cancel_jobs),
                "observed_job_names_post_cancel": self._job_names(post_cancel_jobs),
                "observed_step_names_post_cancel": self._step_names(post_cancel_jobs),
                "step_poll_trace": step_poll_trace,
                "run_status_trace": run_status_trace,
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

        if observation is None or details is None:
            raise GitHubAccessibilityPullRequestGateError(
                "TS-962 did not produce a disposable pull request cancellation observation."
            )
        self._latest_details = details
        return observation

    def _wait_for_run_to_appear(
        self,
        workflow_id: int,
        branch_name: str,
        started_at: float,
    ) -> tuple[dict[str, object], list[dict[str, object]]]:
        deadline = time.time() + self._config.run_timeout_seconds
        latest_runs: list[dict[str, object]] = []
        latest_run: dict[str, object] | None = None
        while time.time() < deadline:
            latest_runs = self._list_branch_runs(branch_name, started_at)
            latest_run = self._find_target_run(latest_runs, workflow_id)
            if latest_run is not None and self._optional_int(latest_run.get("id")) is not None:
                return latest_run, latest_runs
            time.sleep(self._config.poll_interval_seconds)
        raise GitHubAccessibilityPullRequestGateError(
            "TS-962 could not find a live pull-request workflow run to cancel."
        )

    def _wait_for_axe_step_in_progress(
        self,
        run_id: int,
    ) -> tuple[
        list[dict[str, object]],
        GitHubWorkflowRunStepObservation | None,
        GitHubWorkflowRunStepObservation | None,
        list[str],
    ]:
        deadline = time.time() + self._config.run_timeout_seconds
        last_jobs: list[dict[str, object]] = []
        last_axe_step: GitHubWorkflowRunStepObservation | None = None
        last_log_validation_step: GitHubWorkflowRunStepObservation | None = None
        trace: list[str] = []
        while time.time() < deadline:
            last_jobs = self._read_jobs(run_id)
            last_axe_step = self._find_run_step_observation(
                last_jobs,
                job_name=self._accessibility_job_name,
                step_name=self._axe_step_name,
            )
            last_log_validation_step = self._find_run_step_observation(
                last_jobs,
                job_name=self._accessibility_job_name,
                step_name=self._log_validation_step_name,
            )
            trace.append(
                f"{datetime.now(tz=timezone.utc).isoformat()} axe={self._step_summary(last_axe_step)} "
                f"log_validation={self._step_summary(last_log_validation_step)}"
            )
            if (last_axe_step is not None and (last_axe_step.status or "").lower() == "in_progress"):
                return last_jobs, last_axe_step, last_log_validation_step, trace
            run_payload = self._read_json_object(
                f"/repos/{self._config.repository}/actions/runs/{run_id}"
            )
            if self._optional_string(run_payload.get("status")) == "completed":
                break
            time.sleep(self._config.poll_interval_seconds)
        return last_jobs, last_axe_step, last_log_validation_step, trace

    def _wait_for_run_completion(self, run_id: int) -> tuple[dict[str, object], list[str]]:
        deadline = time.time() + self._config.run_timeout_seconds
        latest_run: dict[str, object] | None = None
        trace: list[str] = []
        while time.time() < deadline:
            latest_run = self._read_json_object(
                f"/repos/{self._config.repository}/actions/runs/{run_id}"
            )
            status = self._optional_string(latest_run.get("status")) or "<none>"
            conclusion = self._optional_string(latest_run.get("conclusion")) or "<none>"
            trace.append(
                f"{datetime.now(tz=timezone.utc).isoformat()} status={status} conclusion={conclusion}"
            )
            if status == "completed":
                return latest_run, trace
            time.sleep(self._config.poll_interval_seconds)
        if latest_run is None:
            raise GitHubAccessibilityPullRequestGateError(
                f"TS-962 could not read workflow run {run_id} after requesting cancellation."
            )
        return latest_run, trace

    def _simulation_helper_source(self) -> str:
        hold_ms = self._cancellation_hold_seconds * 1_000
        return f"""async function holdTs962CancellationWindow() {{
  console.log({self.hold_start_marker!r});
  await new Promise((resolve) => setTimeout(resolve, {hold_ms}));
  console.log({self.hold_finish_marker!r});
}}

module.exports = {{
  holdTs962CancellationWindow,
}};
"""

    @classmethod
    def _patch_spec_source(cls, source: str) -> str:
        if cls.helper_require_statement not in source:
            import_anchor = "} = require('./accessibility_gate');"
            if import_anchor not in source:
                raise GitHubAccessibilityPullRequestGateError(
                    "TS-962 could not find the shared accessibility gate import block in "
                    "testing/accessibility/accessibility_gate.spec.js."
                )
            source = source.replace(
                import_anchor,
                import_anchor + "\n" + cls.helper_require_statement,
                1,
            )

        if cls.simulation_call not in source:
            target = "  const results = await collectAccessibilityViolations(page);"
            if target not in source:
                raise GitHubAccessibilityPullRequestGateError(
                    "TS-962 could not find the accessibility scan call in "
                    "testing/accessibility/accessibility_gate.spec.js."
                )
            source = source.replace(
                target,
                f"{cls.simulation_call}\n{target}",
                1,
            )

        return source

    def _extract_log_excerpt(self, run_log_text: str, fallback_text: str) -> str:
        text = run_log_text or fallback_text
        if not text.strip():
            return ""
        lowered = text.lower()
        prioritized_markers = [
            self.hold_start_marker.lower(),
            "log-validation",
            "cancelled",
            "canceled",
            "run axe-core accessibility checks",
            "process completed with exit code",
        ]
        for marker in prioritized_markers:
            index = lowered.find(marker)
            if index >= 0:
                start = max(index - 250, 0)
                end = min(index + 1250, len(text))
                return self._snippet(text[start:end], limit=1800)
        return super()._extract_log_excerpt(run_log_text, fallback_text)

    def _find_run_step_observation(
        self,
        jobs: list[dict[str, object]],
        *,
        job_name: str,
        step_name: str,
    ) -> GitHubWorkflowRunStepObservation | None:
        normalized_job_name = job_name.strip().lower()
        normalized_step_name = step_name.strip().lower()
        for job in jobs:
            actual_job_name = self._optional_string(job.get("name"))
            if actual_job_name is None or actual_job_name.strip().lower() != normalized_job_name:
                continue
            steps = job.get("steps")
            if not isinstance(steps, list):
                return None
            for step in steps:
                if not isinstance(step, dict):
                    continue
                actual_step_name = self._optional_string(step.get("name"))
                if (
                    actual_step_name is None
                    or actual_step_name.strip().lower() != normalized_step_name
                ):
                    continue
                number = step.get("number")
                return GitHubWorkflowRunStepObservation(
                    job_name=actual_job_name,
                    step_name=actual_step_name,
                    number=number if isinstance(number, int) else None,
                    status=self._optional_string(step.get("status")),
                    conclusion=self._optional_string(step.get("conclusion")),
                    started_at=self._optional_string(step.get("started_at")),
                    completed_at=self._optional_string(step.get("completed_at")),
                )
        return None

    @staticmethod
    def _coerce_step_observation(
        value: object,
    ) -> GitHubWorkflowRunStepObservation | None:
        if isinstance(value, GitHubWorkflowRunStepObservation):
            return value
        if not isinstance(value, dict):
            return None
        return GitHubWorkflowRunStepObservation(
            job_name=str(value.get("job_name", "")),
            step_name=str(value.get("step_name", "")),
            number=value.get("number") if isinstance(value.get("number"), int) else None,
            status=value.get("status") if isinstance(value.get("status"), str) else None,
            conclusion=(
                value.get("conclusion")
                if isinstance(value.get("conclusion"), str)
                else None
            ),
            started_at=(
                value.get("started_at")
                if isinstance(value.get("started_at"), str)
                else None
            ),
            completed_at=(
                value.get("completed_at")
                if isinstance(value.get("completed_at"), str)
                else None
            ),
        )

    @staticmethod
    def _step_summary(step: GitHubWorkflowRunStepObservation | None) -> str:
        if step is None:
            return "<missing>"
        return (
            f"job={step.job_name}, step={step.step_name}, number={step.number}, "
            f"status={step.status or '<none>'}, conclusion={step.conclusion or '<none>'}, "
            f"started_at={step.started_at or '<none>'}, "
            f"completed_at={step.completed_at or '<none>'}"
        )
