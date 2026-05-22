from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

from testing.core.interfaces.github_accessibility_pull_request_gate_probe import (
    GitHubAccessibilityWorkflowContractObservation,
    GitHubAccessibilityPullRequestGateObservation,
)
from testing.core.interfaces.github_actions_preflight_gate_probe import (
    GitHubActionsWorkflowJobObservation,
)


def _load_ts_908_module():
    module_path = Path(__file__).with_name("test_ts_908.py")
    spec = importlib.util.spec_from_file_location("ts_908_runtime", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Ts908ReviewRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = _load_ts_908_module()

    def _observation(
        self,
        *,
        run_conclusion: str | None,
        failed_status_check_names: list[str],
        run_log_matched_contrast_markers: list[str],
        run_log_matched_semantic_markers: list[str],
        runtime_accessibility_surface_present: bool = True,
        runtime_accessibility_surface_summary: str = (
            'Accessibility runtime surface ready: hosts=1; nodes=4; sample-labels=["button"]'
        ),
        runtime_accessibility_sample_labels: list[str] | None = None,
    ) -> GitHubAccessibilityPullRequestGateObservation:
        return GitHubAccessibilityPullRequestGateObservation(
            repository="IstiN/trackstate",
            default_branch="main",
            target_workflow_name="Flutter Required Checks",
            target_workflow_path=".github/workflows/unit-tests.yml",
            target_workflow_id=1,
            target_workflow_present_on_default_branch=True,
            target_workflow_declares_pull_request_trigger=True,
            target_workflow_job_names=["Flutter checks"],
            target_workflow_step_names=["Build web app"],
            target_workflow_accessibility_job_names=["Accessibility checks"],
            target_workflow_downstream_job_names=[],
            target_workflow_downstream_job_depends_on_accessibility=False,
            target_workflow=GitHubAccessibilityWorkflowContractObservation(
                declares_pull_request_trigger=True,
                job_names=["Flutter checks"],
                step_names=["Build web app"],
                accessibility_job_names=["Accessibility checks"],
                downstream_job_names=[],
                downstream_job_depends_on_accessibility=False,
            ),
            pull_request_number=123,
            pull_request_url="https://github.com/IstiN/trackstate/pull/123",
            pull_request_checks_url="https://github.com/IstiN/trackstate/pull/123/checks",
            pull_request_head_branch="ts908-accessibility-gate",
            pull_request_head_sha="abc123",
            pull_request_probe_path="lib/ts908_probe_surface.dart",
            probe_render_host_path="lib/main.dart",
            probe_rendered_in_application=True,
            pull_request_file_paths=["lib/main.dart", "lib/ts908_probe_surface.dart"],
            pull_request_state="open",
            pull_request_mergeable_state="clean",
            pull_request_status_state="failure" if failed_status_check_names else "success",
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
                    name="Flutter checks",
                    status="completed",
                    conclusion=run_conclusion,
                    html_url="https://github.com/IstiN/trackstate/actions/runs/456/job/4561",
                    started_at="2026-05-22T07:40:00Z",
                    completed_at="2026-05-22T07:41:00Z",
                )
            ],
            observed_job_names=["Flutter checks"],
            observed_step_names=["Accessibility probe"],
            observed_status_check_names=["Flutter checks"],
            observed_status_check_workflow_names=["Flutter Required Checks"],
            failed_status_check_names=failed_status_check_names,
            failed_status_check_workflow_names=["Flutter Required Checks"]
            if failed_status_check_names
            else [],
            accessibility_status_check_name=None,
            accessibility_status_check_workflow_name=None,
            accessibility_status_check_status=None,
            accessibility_status_check_conclusion=None,
            accessibility_status_check_url=None,
            matched_accessibility_markers=[],
            matched_contrast_markers=[],
            matched_semantic_markers=[],
            run_log_matched_accessibility_markers=[],
            run_log_matched_contrast_markers=run_log_matched_contrast_markers,
            run_log_matched_semantic_markers=run_log_matched_semantic_markers,
            run_log_mentions_accessibility=False,
            run_log_mentions_contrast_issue=bool(run_log_matched_contrast_markers),
            run_log_mentions_semantic_issue=bool(run_log_matched_semantic_markers),
            run_log_excerpt="color contrast violation and aria-label defect",
            run_log_error=None,
            runtime_accessibility_surface_present=runtime_accessibility_surface_present,
            runtime_accessibility_surface_summary=runtime_accessibility_surface_summary,
            runtime_accessibility_sample_labels=runtime_accessibility_sample_labels
            if runtime_accessibility_sample_labels is not None
            else ["button"],
            probe_contains_low_contrast_indicator=True,
            probe_contains_semantic_label_indicator=True,
            probe_semantic_label="button",
            probe_visible_text="Sync issue",
            probe_contrast_technique="Uses reduced contrast.",
            cleanup_closed_pull_request=True,
            cleanup_deleted_branch=True,
        )

    def test_step_4_accepts_generic_failed_workflow_with_live_log_evidence(self) -> None:
        result: dict[str, object] = {"steps": [], "human_verification": []}
        failures: list[str] = []

        self.module._evaluate_accessibility_gate_result(  # type: ignore[attr-defined]
            result,
            self._observation(
                run_conclusion="failure",
                failed_status_check_names=["Flutter checks"],
                run_log_matched_contrast_markers=["color-contrast", "4.5:1"],
                run_log_matched_semantic_markers=["aria-label", "semantic"],
            ),
            failures,
        )

        self.assertEqual(failures, [])
        self.assertEqual(result["steps"][0]["status"], "passed")

    def test_step_4_rejects_log_markers_without_failed_run_surface(self) -> None:
        result: dict[str, object] = {"steps": [], "human_verification": []}
        failures: list[str] = []

        self.module._evaluate_accessibility_gate_result(  # type: ignore[attr-defined]
            result,
            self._observation(
                run_conclusion="success",
                failed_status_check_names=[],
                run_log_matched_contrast_markers=["color-contrast", "4.5:1"],
                run_log_matched_semantic_markers=["aria-label", "semantic"],
            ),
            failures,
        )

        self.assertEqual(len(failures), 1)
        self.assertEqual(result["steps"][0]["status"], "failed")

    def test_step_4_rejects_ratio_only_contrast_noise(self) -> None:
        result: dict[str, object] = {"steps": [], "human_verification": []}
        failures: list[str] = []

        self.module._evaluate_accessibility_gate_result(  # type: ignore[attr-defined]
            result,
            self._observation(
                run_conclusion="failure",
                failed_status_check_names=["Accessibility checks"],
                run_log_matched_contrast_markers=["ratio"],
                run_log_matched_semantic_markers=["non-descriptive-label"],
            ),
            failures,
        )

        self.assertEqual(len(failures), 1)
        self.assertEqual(result["steps"][0]["status"], "failed")

    def test_step_2_requires_runtime_generic_semantic_label(self) -> None:
        result: dict[str, object] = {"steps": [], "human_verification": []}
        failures: list[str] = []

        self.module._evaluate_defective_component(  # type: ignore[attr-defined]
            result,
            self._observation(
                run_conclusion="success",
                failed_status_check_names=[],
                run_log_matched_contrast_markers=[],
                run_log_matched_semantic_markers=[],
                runtime_accessibility_sample_labels=["button"],
            ),
            failures,
        )

        self.assertEqual(failures, [])
        self.assertEqual(result["steps"][0]["status"], "passed")

    def test_step_2_rejects_runtime_label_that_keeps_visible_text(self) -> None:
        result: dict[str, object] = {"steps": [], "human_verification": []}
        failures: list[str] = []

        self.module._evaluate_defective_component(  # type: ignore[attr-defined]
            result,
            self._observation(
                run_conclusion="success",
                failed_status_check_names=[],
                run_log_matched_contrast_markers=[],
                run_log_matched_semantic_markers=[],
                runtime_accessibility_sample_labels=["button Sync issue"],
                runtime_accessibility_surface_summary=(
                    'Accessibility runtime surface ready: hosts=1; nodes=4; '
                    'sample-labels=["button Sync issue"]'
                ),
            ),
            failures,
        )

        self.assertEqual(len(failures), 1)
        self.assertEqual(result["steps"][0]["status"], "failed")


if __name__ == "__main__":
    unittest.main()
