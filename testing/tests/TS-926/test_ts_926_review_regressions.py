from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

from testing.core.interfaces.github_accessibility_pull_request_gate_probe import (
    GitHubAccessibilityPullRequestGateObservation,
    GitHubAccessibilityWorkflowContractObservation,
)
from testing.core.interfaces.github_actions_preflight_gate_probe import (
    GitHubActionsWorkflowJobObservation,
)


def _load_ts_926_module():
    module_path = Path(__file__).with_name("test_ts_926.py")
    spec = importlib.util.spec_from_file_location("ts_926_runtime", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Ts926ReviewRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = _load_ts_926_module()

    def _observation(
        self,
        *,
        run_conclusion: str | None,
        matched_accessibility_markers: list[str],
        run_log_matched_contrast_markers: list[str],
        run_log_matched_semantic_markers: list[str],
        run_log_matched_accessibility_markers: list[str] | None = None,
        runtime_accessibility_surface_present: bool = True,
        runtime_accessibility_surface_summary: str = (
            "Accessibility runtime surface ready: "
            "Boundary contrast sample | Open tracker settings"
        ),
        accessibility_status_check_conclusion: str | None = None,
    ) -> GitHubAccessibilityPullRequestGateObservation:
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
                job_names=["Accessibility checks", "Deploy preview"],
                step_names=["Run axe-core accessibility checks"],
                accessibility_job_names=["Accessibility checks"],
                downstream_job_names=["Deploy preview"],
                downstream_job_depends_on_accessibility=True,
            ),
            pull_request_number=123,
            pull_request_url="https://github.com/IstiN/trackstate/pull/123",
            pull_request_checks_url="https://github.com/IstiN/trackstate/pull/123/checks",
            pull_request_head_branch="ts926-accessibility-boundary",
            pull_request_head_sha="abc123",
            pull_request_probe_path="lib/ts926_accessibility_boundary_probe.dart",
            probe_render_host_path="lib/ui/features/tracker/views/trackstate_app.dart",
            probe_rendered_in_application=True,
            pull_request_file_paths=[
                "lib/ui/features/tracker/views/trackstate_app.dart",
                "lib/ts926_accessibility_boundary_probe.dart",
            ],
            pull_request_state="open",
            pull_request_mergeable_state="clean",
            pull_request_status_state="success" if run_conclusion == "success" else "failure",
            latest_pull_request_run_id=456,
            latest_pull_request_run_url="https://github.com/IstiN/trackstate/actions/runs/456",
            latest_pull_request_run_event="pull_request",
            latest_pull_request_run_status="completed",
            latest_pull_request_run_conclusion=run_conclusion,
            observed_branch_run_names=["Flutter Required Checks"],
            observed_branch_run_urls=["https://github.com/IstiN/trackstate/actions/runs/456"],
            observed_branch_run_statuses=["completed"],
            observed_branch_run_conclusions=[run_conclusion or ""],
            observed_run_jobs=[
                GitHubActionsWorkflowJobObservation(
                    id=4561,
                    name="Accessibility checks",
                    status="completed",
                    conclusion=run_conclusion,
                    html_url="https://github.com/IstiN/trackstate/actions/runs/456/job/4561",
                    started_at="2026-05-22T10:55:00Z",
                    completed_at="2026-05-22T10:56:00Z",
                )
            ],
            observed_job_names=["Accessibility checks"],
            observed_step_names=["Run axe-core accessibility checks"],
            observed_status_check_names=["Accessibility checks"],
            observed_status_check_workflow_names=["Flutter Required Checks"],
            failed_status_check_names=[] if run_conclusion == "success" else ["Accessibility checks"],
            failed_status_check_workflow_names=[]
            if run_conclusion == "success"
            else ["Flutter Required Checks"],
            accessibility_status_check_name="Accessibility checks",
            accessibility_status_check_workflow_name="Flutter Required Checks",
            accessibility_status_check_status="completed",
            accessibility_status_check_conclusion=(
                accessibility_status_check_conclusion
                if accessibility_status_check_conclusion is not None
                else run_conclusion
            ),
            accessibility_status_check_url="https://example.test/accessibility",
            matched_accessibility_markers=matched_accessibility_markers,
            matched_contrast_markers=[],
            matched_semantic_markers=[],
            run_log_matched_accessibility_markers=(
                run_log_matched_accessibility_markers
                if run_log_matched_accessibility_markers is not None
                else (["axe-core"] if matched_accessibility_markers else [])
            ),
            run_log_matched_contrast_markers=run_log_matched_contrast_markers,
            run_log_matched_semantic_markers=run_log_matched_semantic_markers,
            run_log_mentions_accessibility=bool(
                run_log_matched_accessibility_markers
                if run_log_matched_accessibility_markers is not None
                else matched_accessibility_markers
            ),
            run_log_mentions_contrast_issue=bool(run_log_matched_contrast_markers),
            run_log_mentions_semantic_issue=bool(run_log_matched_semantic_markers),
            run_log_excerpt="Run axe-core accessibility checks\n1 passed",
            run_log_error=None,
            runtime_accessibility_surface_present=runtime_accessibility_surface_present,
            runtime_accessibility_surface_summary=runtime_accessibility_surface_summary,
            probe_contains_low_contrast_indicator=False,
            probe_contains_semantic_label_indicator=False,
            probe_semantic_label="Open tracker settings",
            probe_contrast_technique="Uses fixed RGB colors for an exact 4.5:1 boundary.",
            cleanup_closed_pull_request=True,
            cleanup_deleted_branch=True,
        )

    def test_step_3_accepts_clean_live_accessibility_logs(self) -> None:
        result: dict[str, object] = {"steps": [], "human_verification": []}
        failures: list[str] = []

        self.module._evaluate_accessibility_audit_logs(  # type: ignore[attr-defined]
            result,
            observation=self._observation(
                run_conclusion="success",
                matched_accessibility_markers=["accessibility", "axe-core"],
                run_log_matched_contrast_markers=[],
                run_log_matched_semantic_markers=[],
            ),
            failures=failures,
        )

        self.assertEqual(failures, [])
        self.assertEqual(result["steps"][0]["status"], "passed")

    def test_step_3_rejects_forbidden_violation_markers(self) -> None:
        result: dict[str, object] = {"steps": [], "human_verification": []}
        failures: list[str] = []

        self.module._evaluate_accessibility_audit_logs(  # type: ignore[attr-defined]
            result,
            observation=self._observation(
                run_conclusion="success",
                matched_accessibility_markers=["accessibility", "axe-core"],
                run_log_matched_contrast_markers=["color-contrast"],
                run_log_matched_semantic_markers=[],
            ),
            failures=failures,
        )

        self.assertEqual(len(failures), 1)
        self.assertEqual(result["steps"][0]["status"], "failed")

    def test_step_2_rejects_skipped_accessibility_check(self) -> None:
        result: dict[str, object] = {"steps": [], "human_verification": []}
        failures: list[str] = []

        self.module._evaluate_live_ci_trigger(  # type: ignore[attr-defined]
            result,
            observation=self._observation(
                run_conclusion="success",
                matched_accessibility_markers=["accessibility", "axe-core"],
                run_log_matched_contrast_markers=[],
                run_log_matched_semantic_markers=[],
                accessibility_status_check_conclusion="skipped",
            ),
            failures=failures,
        )

        self.assertEqual(len(failures), 1)
        self.assertIn("accessibility check did not complete successfully", failures[0])
        self.assertEqual(result["steps"][0]["status"], "failed")

    def test_step_3_rejects_missing_runtime_accessibility_evidence(self) -> None:
        result: dict[str, object] = {"steps": [], "human_verification": []}
        failures: list[str] = []

        self.module._evaluate_accessibility_audit_logs(  # type: ignore[attr-defined]
            result,
            observation=self._observation(
                run_conclusion="success",
                matched_accessibility_markers=["accessibility", "axe-core"],
                run_log_matched_contrast_markers=[],
                run_log_matched_semantic_markers=[],
                run_log_matched_accessibility_markers=["axe-core"],
                runtime_accessibility_surface_present=False,
                runtime_accessibility_surface_summary="",
            ),
            failures=failures,
        )

        self.assertEqual(len(failures), 1)
        self.assertIn("never exposed rendered accessibility output", failures[0])
        self.assertEqual(result["steps"][0]["status"], "failed")


if __name__ == "__main__":
    unittest.main()
