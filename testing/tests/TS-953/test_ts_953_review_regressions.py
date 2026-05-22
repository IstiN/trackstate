from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

from testing.components.services.github_accessibility_network_timeout_probe import (
    GitHubAccessibilityNetworkTimeoutProbeService,
)
from testing.core.interfaces.github_accessibility_pull_request_gate_probe import (
    GitHubAccessibilityPullRequestGateObservation,
    GitHubAccessibilityWorkflowContractObservation,
)
from testing.core.interfaces.github_actions_preflight_gate_probe import (
    GitHubActionsWorkflowJobObservation,
)


def _load_ts_953_module():
    module_path = Path(__file__).with_name("test_ts_953.py")
    spec = importlib.util.spec_from_file_location("ts_953_runtime", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Ts953ReviewRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = _load_ts_953_module()

    def _observation(
        self,
        *,
        run_log_excerpt: str,
        run_log_error: str | None = None,
        run_log_matched_contrast_markers: list[str] | None = None,
        run_log_mentions_contrast_issue: bool | None = None,
        run_log_matched_semantic_markers: list[str] | None = None,
        run_log_mentions_semantic_issue: bool = False,
        run_conclusion: str = "failure",
        accessibility_check_conclusion: str = "failure",
        run_status: str = "completed",
    ) -> GitHubAccessibilityPullRequestGateObservation:
        matched_contrast_markers = list(run_log_matched_contrast_markers or [])
        matched_semantic_markers = list(run_log_matched_semantic_markers or [])
        return GitHubAccessibilityPullRequestGateObservation(
            repository="IstiN/trackstate",
            default_branch="main",
            target_workflow_name="Flutter Required Checks",
            target_workflow_path=".github/workflows/unit-tests.yml",
            target_workflow_id=1,
            target_workflow_present_on_default_branch=True,
            target_workflow_declares_pull_request_trigger=True,
            target_workflow_job_names=["Accessibility checks"],
            target_workflow_step_names=["Run axe-core accessibility checks"],
            target_workflow_accessibility_job_names=["Accessibility checks"],
            target_workflow_downstream_job_names=["Deploy preview"],
            target_workflow_downstream_job_depends_on_accessibility=True,
            target_workflow=GitHubAccessibilityWorkflowContractObservation(
                declares_pull_request_trigger=True,
                job_names=["Accessibility checks"],
                step_names=["Run axe-core accessibility checks"],
                accessibility_job_names=["Accessibility checks"],
                downstream_job_names=["Deploy preview"],
                downstream_job_depends_on_accessibility=True,
            ),
            pull_request_number=123,
            pull_request_url="https://github.com/IstiN/trackstate/pull/123",
            pull_request_checks_url="https://github.com/IstiN/trackstate/pull/123/checks",
            pull_request_head_branch="ts953-network-timeout",
            pull_request_head_sha="abc123",
            pull_request_probe_path="testing/accessibility/ts953_network_timeout_simulation.js",
            probe_render_host_path="testing/accessibility/accessibility_gate.spec.js",
            probe_rendered_in_application=True,
            pull_request_file_paths=[
                "testing/accessibility/ts953_network_timeout_simulation.js",
                "testing/accessibility/accessibility_gate.spec.js",
            ],
            pull_request_state="open",
            pull_request_mergeable_state="dirty",
            pull_request_status_state="failure",
            latest_pull_request_run_id=456,
            latest_pull_request_run_url="https://github.com/IstiN/trackstate/actions/runs/456",
            latest_pull_request_run_event="pull_request",
            latest_pull_request_run_status=run_status,
            latest_pull_request_run_conclusion=run_conclusion,
            observed_branch_run_names=["Flutter Required Checks"],
            observed_branch_run_urls=["https://github.com/IstiN/trackstate/actions/runs/456"],
            observed_branch_run_statuses=[run_status],
            observed_branch_run_conclusions=[run_conclusion],
            observed_run_jobs=[
                GitHubActionsWorkflowJobObservation(
                    id=4561,
                    name="Accessibility checks",
                    status=run_status,
                    conclusion=accessibility_check_conclusion,
                    html_url="https://github.com/IstiN/trackstate/actions/runs/456/job/4561",
                    started_at="2026-05-22T12:00:00Z",
                    completed_at="2026-05-22T12:01:00Z",
                )
            ],
            observed_job_names=["Accessibility checks"],
            observed_step_names=["Run axe-core accessibility checks", "log-validation"],
            observed_status_check_names=["Accessibility checks"],
            observed_status_check_workflow_names=["Flutter Required Checks"],
            failed_status_check_names=["Accessibility checks"],
            failed_status_check_workflow_names=["Flutter Required Checks"],
            accessibility_status_check_name="Accessibility checks",
            accessibility_status_check_workflow_name="Flutter Required Checks",
            accessibility_status_check_status=run_status,
            accessibility_status_check_conclusion=accessibility_check_conclusion,
            accessibility_status_check_url="https://example.test/accessibility",
            matched_accessibility_markers=["accessibility", "timeout"],
            matched_contrast_markers=matched_contrast_markers,
            matched_semantic_markers=matched_semantic_markers,
            run_log_matched_accessibility_markers=["accessibility", "timeout"],
            run_log_matched_contrast_markers=matched_contrast_markers,
            run_log_matched_semantic_markers=matched_semantic_markers,
            run_log_mentions_accessibility=True,
            run_log_mentions_contrast_issue=(
                bool(matched_contrast_markers)
                if run_log_mentions_contrast_issue is None
                else run_log_mentions_contrast_issue
            ),
            run_log_mentions_semantic_issue=run_log_mentions_semantic_issue,
            run_log_excerpt=run_log_excerpt,
            run_log_error=run_log_error,
            runtime_accessibility_surface_present=False,
            runtime_accessibility_surface_summary="",
            probe_contains_low_contrast_indicator=False,
            probe_contains_semantic_label_indicator=False,
            probe_semantic_label="",
            probe_contrast_technique="TS-953 simulation",
            cleanup_closed_pull_request=True,
            cleanup_deleted_branch=True,
            flutter_engine_initialization_log_entries=[
                "Flutter engine initialization: bootstrap requested"
            ],
            flutter_engine_initialization_summary="Flutter engine initialization: bootstrap requested",
            semantics_tree_discovery_log_entries=[],
            semantics_tree_discovery_summary="",
        )

    def test_step_3_accepts_generic_page_goto_timeout(self) -> None:
        result: dict[str, object] = {"steps": [], "human_verification": []}
        failures: list[str] = []

        self.module._evaluate_error_log(  # type: ignore[attr-defined]
            result,
            self._observation(
                run_log_excerpt="Error: page.goto: Timeout 15000ms exceeded while waiting for networkidle.",
                run_log_matched_contrast_markers=["timeout", "page.goto", "networkidle"],
            ),
            failures,
        )

        self.assertEqual(failures, [])
        self.assertEqual(result["steps"][0]["status"], "passed")

    def test_step_3_rejects_semantics_failure_wording(self) -> None:
        result: dict[str, object] = {"steps": [], "human_verification": []}
        failures: list[str] = []

        self.module._evaluate_error_log(  # type: ignore[attr-defined]
            result,
            self._observation(
                run_log_excerpt=(
                    "Error: Flutter engine failed to render semantics nodes during "
                    "initialization after the polling threshold."
                ),
                run_log_matched_semantic_markers=[
                    "Flutter engine failed to render semantics nodes during initialization"
                ],
                run_log_mentions_semantic_issue=True,
            ),
            failures,
        )

        self.assertEqual(len(failures), 1)
        self.assertEqual(result["steps"][0]["status"], "failed")
        self.assertIn("incorrectly reported a Flutter semantics initialization failure", failures[0])

    def test_step_3_rejects_full_log_semantics_failure_even_with_generic_excerpt(self) -> None:
        result: dict[str, object] = {"steps": [], "human_verification": []}
        failures: list[str] = []

        self.module._evaluate_error_log(  # type: ignore[attr-defined]
            result,
            self._observation(
                run_log_excerpt=(
                    "Error: page.goto: Timeout 15000ms exceeded while waiting for load state."
                ),
                run_log_matched_contrast_markers=["timeout", "page.goto"],
                run_log_matched_semantic_markers=[
                    "Flutter engine failed to render semantics nodes during initialization"
                ],
                run_log_mentions_semantic_issue=True,
            ),
            failures,
        )

        self.assertEqual(len(failures), 1)
        self.assertEqual(result["steps"][0]["status"], "failed")
        self.assertIn("incorrectly reported a Flutter semantics initialization failure", failures[0])

    def test_step_3_requires_generic_timeout_signal(self) -> None:
        result: dict[str, object] = {"steps": [], "human_verification": []}
        failures: list[str] = []

        self.module._evaluate_error_log(  # type: ignore[attr-defined]
            result,
            self._observation(
                run_log_excerpt="log-validation failed because mandatory engine state tokens were not found.",
            ),
            failures,
        )

        self.assertEqual(len(failures), 1)
        self.assertEqual(result["steps"][0]["status"], "failed")
        self.assertIn("did not surface a standard network or Playwright timeout", failures[0])

    def test_step_2_requires_failed_accessibility_check(self) -> None:
        result: dict[str, object] = {"steps": [], "human_verification": []}
        failures: list[str] = []

        self.module._evaluate_network_timeout_simulation(  # type: ignore[attr-defined]
            result,
            self._observation(
                run_log_excerpt="Error: page.goto: Timeout 15000ms exceeded.",
                accessibility_check_conclusion="success",
            ),
            failures,
        )

        self.assertEqual(len(failures), 1)
        self.assertEqual(result["steps"][0]["status"], "failed")
        self.assertIn("did not end in failure", failures[0])

    def test_probe_helper_source_stalls_navigation_request(self) -> None:
        source = GitHubAccessibilityNetworkTimeoutProbeService._helper_source()  # noqa: SLF001

        self.assertIn("installTs953NetworkTimeoutSimulation", source)
        self.assertIn("page.setDefaultNavigationTimeout(15000);", source)
        self.assertIn("route.request().isNavigationRequest()", source)
        self.assertIn("await new Promise(() => {});", source)

    def test_patch_spec_source_injects_timeout_simulation_before_diagnostics(self) -> None:
        original = """const { test, expect } = require('@playwright/test');
const {
  captureFlutterStartupDiagnostics,
  collectAccessibilityViolations,
  formatViolations,
} = require('./accessibility_gate');

test('TrackState web app has no axe-core accessibility violations', async ({
  page,
}) => {
  await captureFlutterStartupDiagnostics(page, {
    log: (entry) => console.log(entry),
  });
  await expect(page).toHaveTitle(/TrackState\\.AI/);

  const results = await collectAccessibilityViolations(page);

  expect(results, formatViolations(results)).toEqual([]);
});
"""

        patched = GitHubAccessibilityNetworkTimeoutProbeService._patch_spec_source(  # noqa: SLF001
            original
        )

        self.assertIn("installTs953NetworkTimeoutSimulation", patched)
        self.assertIn("await installTs953NetworkTimeoutSimulation(page);", patched)
        self.assertIn("await captureFlutterStartupDiagnostics(page, {", patched)


if __name__ == "__main__":
    unittest.main()
