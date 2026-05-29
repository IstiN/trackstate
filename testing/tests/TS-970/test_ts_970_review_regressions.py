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


def _load_ts_970_module():
    module_path = Path(__file__).with_name("test_ts_970.py")
    spec = importlib.util.spec_from_file_location("ts_970_runtime", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Ts970ReviewRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = _load_ts_970_module()

    def _observation(
        self,
        *,
        pull_request_status_state: str = "failure",
        pull_request_mergeable_state: str = "blocked",
        failed_status_check_workflow_names: list[str] | None = None,
        latest_pull_request_run_status: str = "completed",
        latest_pull_request_run_conclusion: str = "failure",
    ) -> GitHubAccessibilityPullRequestGateObservation:
        return GitHubAccessibilityPullRequestGateObservation(
            repository="IstiN/trackstate",
            default_branch="main",
            target_workflow_name="Flutter Required Checks",
            target_workflow_path=".github/workflows/unit-tests.yml",
            target_workflow_id=970,
            target_workflow_present_on_default_branch=True,
            target_workflow_declares_pull_request_trigger=True,
            target_workflow_job_names=["Flutter checks", "Accessibility checks"],
            target_workflow_step_names=[
                "Run axe-core accessibility checks",
                "Run unit and golden tests",
            ],
            target_workflow_accessibility_job_names=["Accessibility checks"],
            target_workflow_downstream_job_names=["Deploy preview"],
            target_workflow_downstream_job_depends_on_accessibility=True,
            target_workflow=GitHubAccessibilityWorkflowContractObservation(
                declares_pull_request_trigger=True,
                job_names=["Flutter checks", "Accessibility checks", "Deploy preview"],
                step_names=[
                    "Run axe-core accessibility checks",
                    "Run unit and golden tests",
                ],
                accessibility_job_names=["Accessibility checks"],
                downstream_job_names=["Deploy preview"],
                downstream_job_depends_on_accessibility=True,
            ),
            pull_request_number=970,
            pull_request_url="https://github.com/IstiN/trackstate/pull/970",
            pull_request_checks_url="https://github.com/IstiN/trackstate/pull/970/checks",
            pull_request_head_branch="ts970-required-checks-contract",
            pull_request_head_sha="abc123",
            pull_request_probe_path=".github/workflows/unit-tests.yml",
            probe_render_host_path=".github/workflows/unit-tests.yml",
            probe_rendered_in_application=True,
            pull_request_file_paths=[".github/workflows/unit-tests.yml"],
            pull_request_state="open",
            pull_request_mergeable_state=pull_request_mergeable_state,
            pull_request_status_state=pull_request_status_state,
            latest_pull_request_run_id=123456,
            latest_pull_request_run_url="https://github.com/IstiN/trackstate/actions/runs/123456",
            latest_pull_request_run_event="pull_request",
            latest_pull_request_run_status=latest_pull_request_run_status,
            latest_pull_request_run_conclusion=latest_pull_request_run_conclusion,
            observed_branch_run_names=["Flutter Required Checks"],
            observed_branch_run_urls=["https://github.com/IstiN/trackstate/actions/runs/123456"],
            observed_branch_run_statuses=[latest_pull_request_run_status],
            observed_branch_run_conclusions=[latest_pull_request_run_conclusion],
            observed_run_jobs=[
                GitHubActionsWorkflowJobObservation(
                    id=1,
                    name="Accessibility checks",
                    status=latest_pull_request_run_status,
                    conclusion=latest_pull_request_run_conclusion,
                    html_url="https://github.com/IstiN/trackstate/actions/runs/123456/job/1",
                    started_at="2026-05-23T00:00:00Z",
                    completed_at="2026-05-23T00:01:00Z",
                )
            ],
            observed_job_names=["Accessibility checks"],
            observed_step_names=[
                "Run axe-core accessibility checks",
                "Run unit and golden tests",
            ],
            observed_status_check_names=["Accessibility checks"],
            observed_status_check_workflow_names=["Flutter Required Checks"],
            failed_status_check_names=["Accessibility checks"]
            if failed_status_check_workflow_names
            else [],
            failed_status_check_workflow_names=failed_status_check_workflow_names or [],
            accessibility_status_check_name="Accessibility checks",
            accessibility_status_check_workflow_name="Flutter Required Checks",
            accessibility_status_check_status=latest_pull_request_run_status,
            accessibility_status_check_conclusion=latest_pull_request_run_conclusion,
            accessibility_status_check_url="https://github.com/IstiN/trackstate/actions/runs/123456/job/1",
            matched_accessibility_markers=["Flutter Required Checks", "log-validation"],
            matched_contrast_markers=["log-validation", "missing"],
            matched_semantic_markers=["Flutter Required Checks"],
            run_log_matched_accessibility_markers=["Flutter Required Checks", "log-validation"],
            run_log_matched_contrast_markers=["log-validation", "missing"],
            run_log_matched_semantic_markers=["Flutter Required Checks"],
            run_log_mentions_accessibility=True,
            run_log_mentions_contrast_issue=True,
            run_log_mentions_semantic_issue=True,
            run_log_excerpt=(
                "Expected the accessibility workflow to expose a contributor-visible "
                "`log-validation` step."
            ),
            run_log_error=None,
            runtime_accessibility_surface_present=False,
            runtime_accessibility_surface_summary="",
            probe_contains_low_contrast_indicator=False,
            probe_contains_semantic_label_indicator=False,
            probe_semantic_label="",
            probe_contrast_technique="Remove log-validation from the workflow file.",
            cleanup_closed_pull_request=True,
            cleanup_deleted_branch=True,
            default_branch_probe_host_present=True,
            default_branch_probe_host_summary=(
                ".github/workflows/unit-tests.yml@main contains the required `log-validation` step."
            ),
            flutter_engine_initialization_log_entries=[],
            flutter_engine_initialization_summary="",
            semantics_tree_discovery_log_entries=[],
            semantics_tree_discovery_summary="",
        )

    def test_step_2_requires_flutter_required_checks_to_fail(self) -> None:
        result: dict[str, object] = {"steps": [], "human_verification": []}
        failures: list[str] = []

        self.module._evaluate_aggregate_required_status(  # type: ignore[attr-defined]
            result,
            self._observation(failed_status_check_workflow_names=[]),
            failures,
            expected_workflow_name="Flutter Required Checks",
            full_run_log_text=(
                "Expected the accessibility workflow to expose a contributor-visible "
                "`log-validation` step."
            ),
            full_run_log_error=None,
        )

        self.assertEqual(len(failures), 1)
        self.assertEqual(result["steps"][0]["status"], "failed")
        self.assertIn("Flutter Required Checks", failures[0])
        self.assertIn("did not show `Flutter Required Checks` as a failed workflow", failures[0])

    def test_step_2_accepts_failed_flutter_required_checks_with_contract_message(self) -> None:
        result: dict[str, object] = {"steps": [], "human_verification": []}
        failures: list[str] = []

        self.module._evaluate_aggregate_required_status(  # type: ignore[attr-defined]
            result,
            self._observation(failed_status_check_workflow_names=["Flutter Required Checks"]),
            failures,
            expected_workflow_name="Flutter Required Checks",
            full_run_log_text=(
                "Expected the accessibility workflow to expose a contributor-visible "
                "`log-validation` step."
            ),
            full_run_log_error=None,
        )

        self.assertEqual(failures, [])
        self.assertEqual(result["steps"][0]["status"], "passed")

    def test_step_3_requires_merge_blocked_state(self) -> None:
        result: dict[str, object] = {"steps": [], "human_verification": []}
        failures: list[str] = []

        self.module._evaluate_merge_block(  # type: ignore[attr-defined]
            result,
            self._observation(
                pull_request_mergeable_state="clean",
                failed_status_check_workflow_names=["Flutter Required Checks"],
            ),
            failures,
            expected_workflow_name="Flutter Required Checks",
        )

        self.assertEqual(len(failures), 1)
        self.assertEqual(result["steps"][0]["status"], "failed")
        self.assertIn("merge-blocked", failures[0])


if __name__ == "__main__":
    unittest.main()
