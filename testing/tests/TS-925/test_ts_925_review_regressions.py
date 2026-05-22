from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

from testing.components.pages.github_actions_page import GitHubActionsPageObservation
from testing.core.interfaces.github_accessibility_pull_request_gate_probe import (
    GitHubAccessibilityPullRequestGateObservation,
    GitHubAccessibilityWorkflowContractObservation,
)
from testing.core.interfaces.github_actions_preflight_gate_probe import (
    GitHubActionsWorkflowJobObservation,
)


def _load_ts_925_module():
    module_path = Path(__file__).with_name("test_ts_925.py")
    spec = importlib.util.spec_from_file_location("ts_925_runtime", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Ts925ReviewRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = _load_ts_925_module()

    def _observation(
        self,
        *,
        observed_step_names: list[str],
        run_log_matched_accessibility_markers: list[str],
        run_log_matched_contrast_markers: list[str],
        run_log_excerpt: str,
        run_conclusion: str = "failure",
        accessibility_check_conclusion: str = "failure",
    ) -> GitHubAccessibilityPullRequestGateObservation:
        return GitHubAccessibilityPullRequestGateObservation(
            repository="IstiN/trackstate",
            default_branch="main",
            target_workflow_name="Flutter Required Checks",
            target_workflow_path=".github/workflows/unit-tests.yml",
            target_workflow_id=1,
            target_workflow_present_on_default_branch=True,
            target_workflow_declares_pull_request_trigger=True,
            target_workflow_job_names=["Flutter checks", "Accessibility checks"],
            target_workflow_step_names=[
                "Build web app for accessibility scan",
                "Run axe-core accessibility checks",
            ],
            target_workflow_accessibility_job_names=["Accessibility checks"],
            target_workflow_downstream_job_names=["Deploy preview"],
            target_workflow_downstream_job_depends_on_accessibility=True,
            target_workflow=GitHubAccessibilityWorkflowContractObservation(
                declares_pull_request_trigger=True,
                job_names=["Flutter checks", "Accessibility checks"],
                step_names=[
                    "Build web app for accessibility scan",
                    "Run axe-core accessibility checks",
                ],
                accessibility_job_names=["Accessibility checks"],
                downstream_job_names=["Deploy preview"],
                downstream_job_depends_on_accessibility=True,
            ),
            pull_request_number=123,
            pull_request_url="https://github.com/IstiN/trackstate/pull/123",
            pull_request_checks_url="https://github.com/IstiN/trackstate/pull/123/checks",
            pull_request_head_branch="ts925-accessibility-fail-fast",
            pull_request_head_sha="abc123",
            pull_request_probe_path="lib/ts908_probe_surface.dart",
            probe_render_host_path="lib/main.dart",
            probe_rendered_in_application=True,
            pull_request_file_paths=["lib/ts908_probe_surface.dart"],
            pull_request_state="open",
            pull_request_mergeable_state="clean",
            pull_request_status_state="failure",
            latest_pull_request_run_id=456,
            latest_pull_request_run_url="https://github.com/IstiN/trackstate/actions/runs/456",
            latest_pull_request_run_event="pull_request",
            latest_pull_request_run_status="completed",
            latest_pull_request_run_conclusion=run_conclusion,
            observed_branch_run_names=["Flutter Required Checks"],
            observed_branch_run_urls=["https://github.com/IstiN/trackstate/actions/runs/456"],
            observed_branch_run_statuses=["completed"],
            observed_branch_run_conclusions=[run_conclusion],
            observed_run_jobs=[
                GitHubActionsWorkflowJobObservation(
                    id=4561,
                    name="Accessibility checks",
                    status="completed",
                    conclusion=accessibility_check_conclusion,
                    html_url="https://github.com/IstiN/trackstate/actions/runs/456/job/4561",
                    started_at="2026-05-22T09:10:00Z",
                    completed_at="2026-05-22T09:11:00Z",
                )
            ],
            observed_job_names=["Accessibility checks"],
            observed_step_names=observed_step_names,
            observed_status_check_names=["Accessibility checks"],
            observed_status_check_workflow_names=["Flutter Required Checks"],
            failed_status_check_names=["Accessibility checks"],
            failed_status_check_workflow_names=["Flutter Required Checks"],
            accessibility_status_check_name="Accessibility checks",
            accessibility_status_check_workflow_name="Flutter Required Checks",
            accessibility_status_check_status="completed",
            accessibility_status_check_conclusion=accessibility_check_conclusion,
            accessibility_status_check_url="https://example.test/accessibility",
            matched_accessibility_markers=["accessibility", "axe-core"],
            matched_contrast_markers=["contrast", "ratio"],
            matched_semantic_markers=[],
            run_log_matched_accessibility_markers=run_log_matched_accessibility_markers,
            run_log_matched_contrast_markers=run_log_matched_contrast_markers,
            run_log_matched_semantic_markers=[],
            run_log_mentions_accessibility=bool(run_log_matched_accessibility_markers),
            run_log_mentions_contrast_issue=bool(run_log_matched_contrast_markers),
            run_log_mentions_semantic_issue=False,
            run_log_excerpt=run_log_excerpt,
            run_log_error=None,
            runtime_accessibility_surface_present=True,
            runtime_accessibility_surface_summary="Accessibility runtime surface ready",
            probe_contains_low_contrast_indicator=True,
            probe_contains_semantic_label_indicator=True,
            probe_semantic_label="button",
            probe_contrast_technique="Uses colorScheme.surface text on colorScheme.surface.",
            cleanup_closed_pull_request=True,
            cleanup_deleted_branch=True,
        )

    def test_step_1_accepts_rendered_probe_file_without_render_host_diff(self) -> None:
        result: dict[str, object] = {"steps": [], "human_verification": []}
        failures: list[str] = []
        observation = self._observation(
            observed_step_names=[
                "Build web app for accessibility scan",
                "Run axe-core accessibility checks",
            ],
            run_log_matched_accessibility_markers=["axe-core", "accessibility"],
            run_log_matched_contrast_markers=["ratio"],
            run_log_excerpt="Run axe-core accessibility checks",
        )

        self.module._evaluate_pr_probe(  # type: ignore[attr-defined]
            result,
            observation,
            failures,
        )

        self.assertEqual(failures, [])
        self.assertEqual(result["steps"][0]["status"], "passed")

    def test_step_4_rejects_build_failure_before_audit_executes(self) -> None:
        result: dict[str, object] = {"steps": [], "human_verification": []}
        failures: list[str] = []
        observation = self._observation(
            observed_step_names=["Build web app for accessibility scan"],
            run_log_matched_accessibility_markers=[],
            run_log_matched_contrast_markers=["ratio"],
            run_log_excerpt=(
                "Build web app for accessibility scan\n"
                "Error: Failed to compile application for the Web"
            ),
        )

        self.module._evaluate_downstream_gate(  # type: ignore[attr-defined]
            result,
            observation=observation,
            jobs=list(observation.observed_run_jobs),
            accessibility_job=observation.observed_run_jobs[0],
            downstream_job=None,
            blocked_job_conclusions={"skipped", "cancelled", "neutral"},
            failures=failures,
        )

        self.assertEqual(len(failures), 1)
        self.assertEqual(result["steps"][0]["status"], "failed")
        self.assertIn("did not expose a verifiable accessibility audit failure", failures[0])
        self.assertIn("Run-log accessibility markers: []", failures[0])

    def test_step_4_accepts_explicit_audit_failure_before_downstream_check(self) -> None:
        result: dict[str, object] = {"steps": [], "human_verification": []}
        failures: list[str] = []
        observation = self._observation(
            observed_step_names=[
                "Build web app for accessibility scan",
                "Run axe-core accessibility checks",
            ],
            run_log_matched_accessibility_markers=["axe-core", "accessibility"],
            run_log_matched_contrast_markers=["ratio"],
            run_log_excerpt=(
                "Run axe-core accessibility checks\n"
                "Found 1 violation: color contrast ratio below 4.5:1"
            ),
        )

        self.module._evaluate_downstream_gate(  # type: ignore[attr-defined]
            result,
            observation=observation,
            jobs=list(observation.observed_run_jobs),
            accessibility_job=observation.observed_run_jobs[0],
            downstream_job=None,
            blocked_job_conclusions={"skipped", "cancelled", "neutral"},
            failures=failures,
        )

        self.assertEqual(len(failures), 1)
        self.assertEqual(result["steps"][0]["status"], "failed")
        self.assertIn("workflow contract defines a downstream deploy/publish stage", failures[0])

    def test_step_3_requires_browser_screenshot_evidence(self) -> None:
        result: dict[str, object] = {"steps": [], "human_verification": []}
        failures: list[str] = []
        observation = self._observation(
            observed_step_names=[
                "Build web app for accessibility scan",
                "Run axe-core accessibility checks",
            ],
            run_log_matched_accessibility_markers=["axe-core", "accessibility"],
            run_log_matched_contrast_markers=["ratio"],
            run_log_excerpt="Run axe-core accessibility checks",
        )
        run_page = GitHubActionsPageObservation(
            url=observation.latest_pull_request_run_url or "https://example.test/run",
            matched_text="Flutter Required Checks",
            body_text="Flutter Required Checks\nAccessibility checks\nDeploy preview",
            screenshot_path=None,
        )

        self.module._evaluate_actions_ui(  # type: ignore[attr-defined]
            result,
            observation=observation,
            run_page=run_page,
            run_page_error=None,
            failures=failures,
        )

        self.assertEqual(len(failures), 1)
        self.assertEqual(result["steps"][0]["status"], "failed")
        self.assertIn("browser-backed UI evidence was not captured", failures[0])

    def test_bug_description_distinguishes_non_verifiable_audit_runs(self) -> None:
        result: dict[str, object] = {
            "ticket": "TS-925",
            "repository": "IstiN/trackstate",
            "default_branch": "main",
            "browser": "Chromium (Playwright)",
            "os": "Linux",
            "pull_request_url": "https://github.com/IstiN/trackstate/pull/123",
            "pull_request_checks_url": "https://github.com/IstiN/trackstate/pull/123/checks",
            "latest_pull_request_run_url": "https://github.com/IstiN/trackstate/actions/runs/456",
            "run_log_excerpt": "Build web app for accessibility scan\nError: Failed to compile",
            "steps": [
                {"step": 1, "status": "passed", "action": "1", "observed": "probe created"},
                {"step": 2, "status": "passed", "action": "2", "observed": "run started"},
                {"step": 3, "status": "passed", "action": "3", "observed": "ui opened"},
                {
                    "step": 4,
                    "status": "failed",
                    "action": "4",
                    "observed": (
                        "Step 4 failed: the live workflow did not expose a verifiable "
                        "accessibility audit failure for the disposable contrast defect.\n"
                        "Accessibility check conclusion: failure"
                    ),
                },
            ],
            "observed_step_names": ["Build web app for accessibility scan"],
            "run_log_matched_accessibility_markers": [],
            "run_log_matched_contrast_markers": ["ratio"],
            "accessibility_status_check_conclusion": "failure",
            "error": "AssertionError: Step 4 failed",
            "traceback": "AssertionError: Step 4 failed",
        }

        bug_description = self.module._bug_description(result)  # type: ignore[attr-defined]

        self.assertIn(
            "Accessibility audit does not expose a verifiable result",
            bug_description,
        )
        self.assertNotIn(
            "Accessibility gate passes a low-contrast PR",
            bug_description,
        )


if __name__ == "__main__":
    unittest.main()
