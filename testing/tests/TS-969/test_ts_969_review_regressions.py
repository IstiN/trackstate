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


def _load_ts_969_module():
    module_path = Path(__file__).with_name("test_ts_969.py")
    spec = importlib.util.spec_from_file_location("ts_969_runtime", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Ts969ReviewRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = _load_ts_969_module()

    def _observation(self) -> GitHubAccessibilityPullRequestGateObservation:
        return GitHubAccessibilityPullRequestGateObservation(
            repository="IstiN/trackstate",
            default_branch="main",
            target_workflow_name="Flutter Required Checks",
            target_workflow_path=".github/workflows/unit-tests.yml",
            target_workflow_id=969,
            target_workflow_present_on_default_branch=True,
            target_workflow_declares_pull_request_trigger=True,
            target_workflow_job_names=["Accessibility checks", "Flutter checks"],
            target_workflow_step_names=[
                "Run axe-core accessibility checks",
                "Run unit and golden tests",
            ],
            target_workflow_accessibility_job_names=["Accessibility checks"],
            target_workflow_downstream_job_names=["Deploy preview"],
            target_workflow_downstream_job_depends_on_accessibility=True,
            target_workflow=GitHubAccessibilityWorkflowContractObservation(
                declares_pull_request_trigger=True,
                job_names=["Accessibility checks", "Flutter checks", "Deploy preview"],
                step_names=[
                    "Run axe-core accessibility checks",
                    "Run unit and golden tests",
                ],
                accessibility_job_names=["Accessibility checks"],
                downstream_job_names=["Deploy preview"],
                downstream_job_depends_on_accessibility=True,
            ),
            pull_request_number=969,
            pull_request_url="https://github.com/IstiN/trackstate/pull/969",
            pull_request_checks_url="https://github.com/IstiN/trackstate/pull/969/checks",
            pull_request_head_branch="ts969-wrapper-failure-propagation",
            pull_request_head_sha="abc123",
            pull_request_probe_path="testing/accessibility/ts969_wrapper_contract_failure.node.test.js",
            probe_render_host_path="package.json",
            probe_rendered_in_application=True,
            pull_request_file_paths=[
                "testing/accessibility/ts969_wrapper_contract_failure.node.test.js",
                "package.json",
            ],
            pull_request_state="open",
            pull_request_mergeable_state="blocked",
            pull_request_status_state="failure",
            latest_pull_request_run_id=123456,
            latest_pull_request_run_url="https://github.com/IstiN/trackstate/actions/runs/123456",
            latest_pull_request_run_event="pull_request",
            latest_pull_request_run_status="completed",
            latest_pull_request_run_conclusion="failure",
            observed_branch_run_names=["Flutter Required Checks"],
            observed_branch_run_urls=["https://github.com/IstiN/trackstate/actions/runs/123456"],
            observed_branch_run_statuses=["completed"],
            observed_branch_run_conclusions=["failure"],
            observed_run_jobs=[
                GitHubActionsWorkflowJobObservation(
                    id=1,
                    name="Accessibility checks",
                    status="completed",
                    conclusion="failure",
                    html_url="https://github.com/IstiN/trackstate/actions/runs/123456/job/1",
                    started_at="2026-05-23T00:00:00Z",
                    completed_at="2026-05-23T00:01:00Z",
                )
            ],
            observed_job_names=["Accessibility checks"],
            observed_step_names=["Run axe-core accessibility checks", "Run unit and golden tests"],
            observed_status_check_names=["Accessibility checks"],
            observed_status_check_workflow_names=["Flutter Required Checks"],
            failed_status_check_names=["Accessibility checks"],
            failed_status_check_workflow_names=["Flutter Required Checks"],
            accessibility_status_check_name="Accessibility checks",
            accessibility_status_check_workflow_name="Flutter Required Checks",
            accessibility_status_check_status="completed",
            accessibility_status_check_conclusion="failure",
            accessibility_status_check_url="https://github.com/IstiN/trackstate/actions/runs/123456/job/1",
            matched_accessibility_markers=["Accessibility checks", "Run axe-core accessibility checks"],
            matched_contrast_markers=["TS-969 simulated contract validation failure"],
            matched_semantic_markers=["npm run test:a11y", "node --test"],
            run_log_matched_accessibility_markers=["Accessibility checks"],
            run_log_matched_contrast_markers=["TS-969 simulated contract validation failure"],
            run_log_matched_semantic_markers=["npm run test:a11y", "node --test"],
            run_log_mentions_accessibility=True,
            run_log_mentions_contrast_issue=True,
            run_log_mentions_semantic_issue=True,
            run_log_excerpt="TS-969 simulated contract validation failure",
            run_log_error=None,
            runtime_accessibility_surface_present=False,
            runtime_accessibility_surface_summary="",
            probe_contains_low_contrast_indicator=False,
            probe_contains_semantic_label_indicator=False,
            probe_semantic_label="",
            probe_contrast_technique="TS-969 simulation",
            cleanup_closed_pull_request=True,
            cleanup_deleted_branch=True,
            default_branch_probe_host_present=True,
            default_branch_probe_host_summary="package.json@main exposes the original test:a11y script.",
            flutter_engine_initialization_log_entries=[],
            flutter_engine_initialization_summary="",
            semantics_tree_discovery_log_entries=[],
            semantics_tree_discovery_summary="",
        )

    def test_step_3_rejects_exit_code_from_other_step(self) -> None:
        result: dict[str, object] = {"steps": [], "human_verification": []}
        failures: list[str] = []
        full_run_log_text = (
            "Accessibility checks\tRun axe-core accessibility checks\t"
            "TS-969 simulated contract validation failure: standardized wrapper must propagate exit code 1.\n"
            "Flutter checks\tRun unit and golden tests\tProcess completed with exit code 1."
        )
        wrapper_step_output = self.module._extract_step_output(  # type: ignore[attr-defined]
            full_run_log_text,
            self.module.WRAPPER_STEP_PATTERN,  # type: ignore[attr-defined]
        )

        self.module._evaluate_wrapper_exit_code(  # type: ignore[attr-defined]
            result,
            self._observation(),
            failures,
            full_run_log_text=full_run_log_text,
            wrapper_step_output=wrapper_step_output,
        )

        self.assertEqual(len(failures), 1)
        self.assertEqual(result["steps"][0]["status"], "failed")
        self.assertIn("wrapper step did not report", failures[0])
        self.assertIn("observed exit code was `<none>`", failures[0])

    def test_step_3_accepts_exit_code_from_wrapper_step_output(self) -> None:
        result: dict[str, object] = {"steps": [], "human_verification": []}
        failures: list[str] = []
        full_run_log_text = (
            "Accessibility checks\tRun axe-core accessibility checks\t"
            "TS-969 simulated contract validation failure: standardized wrapper must propagate exit code 1.\n"
            "Accessibility checks\tRun axe-core accessibility checks\tProcess completed with exit code 1.\n"
            "Flutter checks\tRun unit and golden tests\tProcess completed with exit code 1."
        )
        wrapper_step_output = self.module._extract_step_output(  # type: ignore[attr-defined]
            full_run_log_text,
            self.module.WRAPPER_STEP_PATTERN,  # type: ignore[attr-defined]
        )

        self.module._evaluate_wrapper_exit_code(  # type: ignore[attr-defined]
            result,
            self._observation(),
            failures,
            full_run_log_text=full_run_log_text,
            wrapper_step_output=wrapper_step_output,
        )

        self.assertEqual(failures, [])
        self.assertEqual(result["steps"][0]["status"], "passed")


if __name__ == "__main__":
    unittest.main()
