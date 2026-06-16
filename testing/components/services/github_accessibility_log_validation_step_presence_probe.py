from __future__ import annotations

from pathlib import Path
import re
import shutil
import tempfile
import time

from testing.components.services.github_accessibility_pull_request_gate_probe import (
    GitHubAccessibilityPullRequestGateError,
    GitHubAccessibilityPullRequestGateProbeService,
)


class GitHubAccessibilityLogValidationStepPresenceProbeService(
    GitHubAccessibilityPullRequestGateProbeService
):
    simulation_technique = (
        "Removes the contributor-visible `log-validation` step from "
        "`.github/workflows/unit-tests.yml` in a disposable pull request so the live "
        "CI schema contract must reject the workflow configuration before merge."
    )
    _LOG_VALIDATION_STEP_NAME = "log-validation"
    _ACCESSIBILITY_STEP_NAME = "Run axe-core accessibility checks"

    def _create_and_observe_pull_request(self, workflow_id: int) -> dict[str, object]:
        temp_repository_root = Path(tempfile.mkdtemp(prefix="ts950-"))
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

            workflow_file = temp_repository_root / self._config.target_workflow_path
            original_source = workflow_file.read_text(encoding="utf-8")
            mutated_source = self._remove_log_validation_step(original_source)
            workflow_file.write_text(mutated_source, encoding="utf-8")

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
            schema_check = self._find_accessibility_status_check(
                surface_observation["status_checks"]
            )
            run_log_text, run_log_error = self._try_read_run_log(run_id)
            evidence_text = "\n".join(
                [
                    *surface_observation["status_check_names"],
                    *surface_observation["status_check_workflow_names"],
                    *self._job_names(jobs),
                    *self._step_names(jobs),
                    run_log_text,
                ]
            )

            observation = {
                "pull_request_number": pull_request_number,
                "pull_request_url": pr_url,
                "pull_request_checks_url": f"{pr_url}/checks",
                "pull_request_head_branch": branch_name,
                "pull_request_head_sha": head_sha,
                "pull_request_probe_path": self._config.target_workflow_path,
                "probe_render_host_path": self._config.target_workflow_path,
                "probe_rendered_in_application": (
                    self._config.target_workflow_path in pull_request_files
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
                if schema_check is None
                else schema_check["name"],
                "accessibility_status_check_workflow_name": None
                if schema_check is None
                else schema_check["workflow_name"],
                "accessibility_status_check_status": None
                if schema_check is None
                else schema_check["status"],
                "accessibility_status_check_conclusion": None
                if schema_check is None
                else schema_check["conclusion"],
                "accessibility_status_check_url": None
                if schema_check is None
                else schema_check["details_url"],
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
                    run_log_text,
                    self._config.expected_accessibility_markers,
                ),
                "run_log_matched_contrast_markers": self._matched_markers(
                    run_log_text,
                    self._config.contrast_evidence_markers,
                ),
                "run_log_matched_semantic_markers": self._matched_markers(
                    run_log_text,
                    self._config.semantic_evidence_markers,
                ),
                "run_log_mentions_accessibility": bool(
                    self._matched_markers(
                        run_log_text,
                        self._config.expected_accessibility_markers,
                    )
                ),
                "run_log_mentions_contrast_issue": bool(
                    self._matched_markers(
                        run_log_text,
                        self._config.contrast_evidence_markers,
                    )
                ),
                "run_log_mentions_semantic_issue": bool(
                    self._matched_markers(
                        run_log_text,
                        self._config.semantic_evidence_markers,
                    )
                ),
                "run_log_excerpt": self._extract_log_excerpt(run_log_text, evidence_text),
                "run_log_error": run_log_error,
                "runtime_accessibility_surface_present": False,
                "runtime_accessibility_surface_summary": "",
                "probe_contains_low_contrast_indicator": False,
                "probe_contains_semantic_label_indicator": False,
                "probe_semantic_label": "",
                "probe_contrast_technique": self.simulation_technique,
                "cleanup_closed_pull_request": False,
                "cleanup_deleted_branch": False,
                "default_branch_probe_host_present": True,
                "default_branch_probe_host_summary": (
                    f"{self._config.target_workflow_path}@{self._config.base_branch} "
                    "contains the required `log-validation` step."
                ),
                "flutter_engine_initialization_log_entries": [],
                "flutter_engine_initialization_summary": "",
                "semantics_tree_discovery_log_entries": [],
                "semantics_tree_discovery_summary": "",
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
                "TS-950 did not produce a disposable pull request observation."
            )
        return observation

    @classmethod
    def _remove_log_validation_step(cls, source: str) -> str:
        lines = source.splitlines(keepends=True)
        step_index = next(
            (
                index
                for index, line in enumerate(lines)
                if line.strip() == f"- name: {cls._LOG_VALIDATION_STEP_NAME}"
            ),
            None,
        )
        if step_index is None:
            raise GitHubAccessibilityPullRequestGateError(
                "TS-950 could not find the `log-validation` step in "
                ".github/workflows/unit-tests.yml."
            )

        if cls._ACCESSIBILITY_STEP_NAME not in source:
            raise GitHubAccessibilityPullRequestGateError(
                "TS-950 could not find the accessibility scan step in "
                ".github/workflows/unit-tests.yml."
            )

        step_indent = len(lines[step_index]) - len(lines[step_index].lstrip(" "))
        end_index = step_index + 1
        while end_index < len(lines):
            stripped = lines[end_index].strip()
            if stripped:
                current_indent = len(lines[end_index]) - len(lines[end_index].lstrip(" "))
                if current_indent <= step_indent:
                    break
            end_index += 1

        mutated = "".join(lines[:step_index] + lines[end_index:])
        if f"- name: {cls._LOG_VALIDATION_STEP_NAME}" in mutated:
            raise GitHubAccessibilityPullRequestGateError(
                "TS-950 removed the wrong workflow region; `log-validation` is still present."
            )
        return mutated

    def _extract_log_excerpt(self, run_log_text: str, fallback_text: str) -> str:
        text = run_log_text or fallback_text
        if not text.strip():
            return ""

        lowered = text.lower()
        prioritized_markers = [
            "log-validation",
            "contributor-visible",
            "unit-tests.yml",
            "workflow configuration",
            "run unit and golden tests",
            "process completed with exit code 1",
        ]
        for marker in prioritized_markers:
            index = lowered.find(marker)
            if index >= 0:
                start = max(index - 250, 0)
                end = min(index + 1250, len(text))
                return self._snippet(text[start:end], limit=1800)

        return super()._extract_log_excerpt(run_log_text, fallback_text)
