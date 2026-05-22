from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

from testing.core.interfaces.github_accessibility_branch_protection_merge_block_probe import (
    GitHubAccessibilityBranchProtectionMergeBlockObservation,
)
from testing.core.interfaces.github_accessibility_pull_request_gate_probe import (
    GitHubAccessibilityPullRequestGateObservation,
    GitHubAccessibilityWorkflowContractObservation,
)
from testing.core.interfaces.github_actions_preflight_gate_probe import (
    GitHubActionsWorkflowJobObservation,
)


def _load_ts_936_module():
    module_path = Path(__file__).with_name("test_ts_936.py")
    spec = importlib.util.spec_from_file_location("ts_936_runtime", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Ts936ReviewRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = _load_ts_936_module()

    def _observation(
        self,
        *,
        accessibility_check_conclusion: str = "failure",
        run_conclusion: str = "success",
    ) -> GitHubAccessibilityBranchProtectionMergeBlockObservation:
        gate = GitHubAccessibilityPullRequestGateObservation(
            repository="IstiN/trackstate",
            default_branch="main",
            target_workflow_name="Flutter Required Checks",
            target_workflow_path=".github/workflows/unit-tests.yml",
            target_workflow_id=1,
            target_workflow_present_on_default_branch=True,
            target_workflow_declares_pull_request_trigger=True,
            target_workflow_job_names=["Flutter checks", "Accessibility checks", "Deploy preview"],
            target_workflow_step_names=["Run axe-core accessibility checks"],
            target_workflow_accessibility_job_names=["Accessibility checks"],
            target_workflow_downstream_job_names=["Deploy preview"],
            target_workflow_downstream_job_depends_on_accessibility=True,
            target_workflow=GitHubAccessibilityWorkflowContractObservation(
                declares_pull_request_trigger=True,
                job_names=["Flutter checks", "Accessibility checks", "Deploy preview"],
                step_names=["Run axe-core accessibility checks"],
                accessibility_job_names=["Accessibility checks"],
                downstream_job_names=["Deploy preview"],
                downstream_job_depends_on_accessibility=True,
            ),
            pull_request_number=936,
            pull_request_url="https://github.com/IstiN/trackstate/pull/936",
            pull_request_checks_url="https://github.com/IstiN/trackstate/pull/936/checks",
            pull_request_head_branch="ts936-review-regression",
            pull_request_head_sha="abc123",
            pull_request_probe_path="lib/ts936_probe_surface.dart",
            probe_render_host_path="lib/main.dart",
            probe_rendered_in_application=True,
            pull_request_file_paths=["lib/ts936_probe_surface.dart"],
            pull_request_state="open",
            pull_request_mergeable_state="blocked",
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
                    started_at="2026-05-22T18:05:00Z",
                    completed_at="2026-05-22T18:06:00Z",
                )
            ],
            observed_job_names=["Accessibility checks"],
            observed_step_names=["Run axe-core accessibility checks"],
            observed_status_check_names=["Accessibility checks"],
            observed_status_check_workflow_names=["Flutter Required Checks"],
            failed_status_check_names=["Accessibility checks"],
            failed_status_check_workflow_names=["Flutter Required Checks"],
            accessibility_status_check_name="Accessibility checks",
            accessibility_status_check_workflow_name="Flutter Required Checks",
            accessibility_status_check_status="completed",
            accessibility_status_check_conclusion=accessibility_check_conclusion,
            accessibility_status_check_url="https://github.com/IstiN/trackstate/actions/runs/456",
            matched_accessibility_markers=["axe-core", "accessibility"],
            matched_contrast_markers=["contrast", "wcag"],
            matched_semantic_markers=["semantic"],
            run_log_matched_accessibility_markers=["axe-core", "accessibility"],
            run_log_matched_contrast_markers=["contrast", "wcag"],
            run_log_matched_semantic_markers=["semantic"],
            run_log_mentions_accessibility=True,
            run_log_mentions_contrast_issue=True,
            run_log_mentions_semantic_issue=True,
            run_log_excerpt="Run axe-core accessibility checks\nFound 1 violation: contrast",
            run_log_error=None,
            runtime_accessibility_surface_present=True,
            runtime_accessibility_surface_summary="Accessibility runtime surface ready",
            probe_contains_low_contrast_indicator=True,
            probe_contains_semantic_label_indicator=True,
            probe_semantic_label="button Sync issue",
            probe_contrast_technique="Uses colorScheme.onSurface.withAlpha(89) on colorScheme.surface.",
            cleanup_closed_pull_request=True,
            cleanup_deleted_branch=True,
            default_branch_probe_host_present=True,
            default_branch_probe_host_summary="lib/main.dart@main already exposed Ts908ProbeSurface.",
        )
        return GitHubAccessibilityBranchProtectionMergeBlockObservation(
            gate=gate,
            required_rule_descriptions=[
                "effective_branch_rules.required_status_checks: ['Flutter checks', 'Accessibility checks']"
            ],
            required_check_contexts=["Flutter checks", "Accessibility checks"],
            repository_declares_accessibility_required_check=True,
            pull_request_mergeable="MERGEABLE",
            pull_request_merge_state_status="BLOCKED",
        )

    def test_step_3_accepts_failed_accessibility_check_when_workflow_is_success(self) -> None:
        result: dict[str, object] = {"steps": [], "human_verification": []}
        failures: list[str] = []

        self.module._evaluate_accessibility_failure(  # type: ignore[attr-defined]
            result,
            observation=self._observation(run_conclusion="success"),
            failures=failures,
        )

        self.assertEqual(failures, [])
        self.assertEqual(result["steps"][0]["status"], "passed")

    def test_step_3_still_requires_accessibility_check_failure(self) -> None:
        result: dict[str, object] = {"steps": [], "human_verification": []}
        failures: list[str] = []

        self.module._evaluate_accessibility_failure(  # type: ignore[attr-defined]
            result,
            observation=self._observation(accessibility_check_conclusion="success"),
            failures=failures,
        )

        self.assertEqual(len(failures), 1)
        self.assertEqual(result["steps"][0]["status"], "failed")
        self.assertIn("accessibility status check did not fail", failures[0])


if __name__ == "__main__":
    unittest.main()
