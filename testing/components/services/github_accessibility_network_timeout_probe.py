from __future__ import annotations

from pathlib import Path
import shutil
import tempfile
import time

from testing.components.services.github_accessibility_pull_request_gate_probe import (
    GitHubAccessibilityPullRequestGateError,
    GitHubAccessibilityPullRequestGateProbeService,
)


class GitHubAccessibilityNetworkTimeoutProbeService(
    GitHubAccessibilityPullRequestGateProbeService
):
    helper_require_statement = (
        "const {\n"
        "  installTs953NetworkTimeoutSimulation,\n"
        "} = require('./ts953_network_timeout_simulation');"
    )
    simulation_call = "  await installTs953NetworkTimeoutSimulation(page);"
    simulation_technique = (
        "Adds a disposable Playwright route in `testing/accessibility/` that stalls the "
        "initial navigation request long enough for Playwright's normal page-load timeout "
        "path to fail before Flutter semantics initialization begins."
    )

    def _create_and_observe_pull_request(self, workflow_id: int) -> dict[str, object]:
        temp_repository_root = Path(tempfile.mkdtemp(prefix="ts953-"))
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

            helper_file = temp_repository_root / self._config.probe_path
            helper_file.parent.mkdir(parents=True, exist_ok=True)
            helper_file.write_text(self._helper_source(), encoding="utf-8")

            spec_file = temp_repository_root / self._config.probe_render_host_path
            spec_file.write_text(
                self._patch_spec_source(spec_file.read_text(encoding="utf-8")),
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
                "probe_contains_low_contrast_indicator": False,
                "probe_contains_semantic_label_indicator": False,
                "probe_semantic_label": "",
                "probe_contrast_technique": self.simulation_technique,
                "cleanup_closed_pull_request": False,
                "cleanup_deleted_branch": False,
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
                "TS-953 did not produce a disposable pull request observation."
            )
        return observation

    @staticmethod
    def _helper_source() -> str:
        return """async function installTs953NetworkTimeoutSimulation(page) {
  page.setDefaultNavigationTimeout(15000);
  await page.route('**/*', async (route) => {
    if (route.request().isNavigationRequest()) {
      await new Promise(() => {});
      return;
    }
    await route.continue();
  });
}

module.exports = {
  installTs953NetworkTimeoutSimulation,
};
"""

    @classmethod
    def _patch_spec_source(cls, source: str) -> str:
        if cls.helper_require_statement not in source:
            require_block = (
                "const {\n"
                "  captureFlutterStartupDiagnostics,\n"
                "  collectAccessibilityViolations,\n"
                "  formatViolations,\n"
                "} = require('./accessibility_gate');"
            )
            if require_block not in source:
                raise GitHubAccessibilityPullRequestGateError(
                    "TS-953 could not find the shared accessibility gate import block in "
                    "testing/accessibility/accessibility_gate.spec.js."
                )
            source = source.replace(
                require_block,
                require_block + "\n" + cls.helper_require_statement,
                1,
            )

        patched_block = (
            "  await installTs953NetworkTimeoutSimulation(page);\n"
            "  await captureFlutterStartupDiagnostics(page, {\n"
            "    log: (entry) => console.log(entry),\n"
            "  });"
        )
        if patched_block in source:
            return source

        original_block = (
            "  await captureFlutterStartupDiagnostics(page, {\n"
            "    log: (entry) => console.log(entry),\n"
            "  });"
        )
        if original_block not in source:
            raise GitHubAccessibilityPullRequestGateError(
                "TS-953 could not find the live accessibility diagnostics call in "
                "testing/accessibility/accessibility_gate.spec.js."
            )

        return source.replace(original_block, patched_block, 1)

    @classmethod
    def _probe_contrast_technique(cls, probe_source: str) -> str:
        del probe_source
        return cls.simulation_technique

    def _extract_log_excerpt(self, run_log_text: str, fallback_text: str) -> str:
        text = run_log_text or fallback_text
        if not text.strip():
            return ""

        lowered = text.lower()
        prioritized_markers = [
            "page.goto",
            "page.waitforloadstate",
            "navigation timeout",
            "networkidle",
            "net::err_",
            "test timeout",
            "process completed with exit code 1",
        ]
        for marker in prioritized_markers:
            index = lowered.find(marker)
            if index >= 0:
                start = max(index - 200, 0)
                end = min(index + 1000, len(text))
                return self._snippet(text[start:end], limit=1200)

        return super()._extract_log_excerpt(run_log_text, fallback_text)
