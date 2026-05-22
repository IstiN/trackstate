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


def _load_ts_943_module():
    module_path = Path(__file__).with_name("test_ts_943.py")
    spec = importlib.util.spec_from_file_location("ts_943_runtime", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Ts943ReviewRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = _load_ts_943_module()

    def _observation(
        self,
        *,
        run_conclusion: str,
        accessibility_conclusion: str,
        observed_step_names: list[str],
        engine_entries: list[str],
        semantics_entries: list[str],
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
            target_workflow_step_names=observed_step_names,
            target_workflow_accessibility_job_names=["Accessibility checks"],
            target_workflow_downstream_job_names=["Deploy preview"],
            target_workflow_downstream_job_depends_on_accessibility=True,
            target_workflow=GitHubAccessibilityWorkflowContractObservation(
                declares_pull_request_trigger=True,
                job_names=["Flutter checks", "Accessibility checks", "Deploy preview"],
                step_names=observed_step_names,
                accessibility_job_names=["Accessibility checks"],
                downstream_job_names=["Deploy preview"],
                downstream_job_depends_on_accessibility=True,
            ),
            pull_request_number=943,
            pull_request_url="https://github.com/IstiN/trackstate/pull/943",
            pull_request_checks_url="https://github.com/IstiN/trackstate/pull/943/checks",
            pull_request_head_branch="ts943-engine-log-validation",
            pull_request_head_sha="abc123",
            pull_request_probe_path="testing/accessibility/ts943_silent_engine_logger.js",
            probe_render_host_path="testing/accessibility/accessibility_gate.spec.js",
            probe_rendered_in_application=True,
            pull_request_file_paths=[
                "testing/accessibility/ts943_silent_engine_logger.js",
                "testing/accessibility/accessibility_gate.spec.js",
            ],
            pull_request_state="open",
            pull_request_mergeable_state="clean",
            pull_request_status_state=run_conclusion,
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
                    conclusion=accessibility_conclusion,
                    html_url="https://github.com/IstiN/trackstate/actions/runs/456/job/4561",
                    started_at="2026-05-22T11:05:00Z",
                    completed_at="2026-05-22T11:06:00Z",
                )
            ],
            observed_job_names=["Accessibility checks"],
            observed_step_names=observed_step_names,
            observed_status_check_names=["Accessibility checks"],
            observed_status_check_workflow_names=["Flutter Required Checks"],
            failed_status_check_names=[],
            failed_status_check_workflow_names=[],
            accessibility_status_check_name="Accessibility checks",
            accessibility_status_check_workflow_name="Flutter Required Checks",
            accessibility_status_check_status="completed",
            accessibility_status_check_conclusion=accessibility_conclusion,
            accessibility_status_check_url="https://example.test/accessibility",
            matched_accessibility_markers=[],
            matched_contrast_markers=[],
            matched_semantic_markers=[],
            run_log_matched_accessibility_markers=[],
            run_log_matched_contrast_markers=[],
            run_log_matched_semantic_markers=[],
            run_log_mentions_accessibility=False,
            run_log_mentions_contrast_issue=False,
            run_log_mentions_semantic_issue=False,
            run_log_excerpt="Run axe-core accessibility checks",
            run_log_error=None,
            runtime_accessibility_surface_present=bool(semantics_entries),
            runtime_accessibility_surface_summary=(
                semantics_entries[0] if semantics_entries else ""
            ),
            probe_contains_low_contrast_indicator=False,
            probe_contains_semantic_label_indicator=False,
            probe_semantic_label="",
            probe_contrast_technique="silent logger",
            cleanup_closed_pull_request=True,
            cleanup_deleted_branch=True,
            flutter_engine_initialization_log_entries=engine_entries,
            flutter_engine_initialization_summary=" | ".join(engine_entries),
            semantics_tree_discovery_log_entries=semantics_entries,
            semantics_tree_discovery_summary=" | ".join(semantics_entries),
        )

    def test_step_2_requires_failed_build_conclusion(self) -> None:
        result: dict[str, object] = {"steps": [], "human_verification": []}
        failures: list[str] = []

        self.module._evaluate_execution_phase(  # type: ignore[attr-defined]
            result,
            self._observation(
                run_conclusion="success",
                accessibility_conclusion="success",
                observed_step_names=["Run axe-core accessibility checks"],
                engine_entries=[],
                semantics_entries=[],
            ),
            failures,
        )

        self.assertEqual(len(failures), 1)
        self.assertEqual(result["steps"][0]["status"], "failed")
        self.assertIn("observed run conclusion was `success`", failures[0])

    def test_step_3_requires_log_validation_surface_and_missing_token_message(self) -> None:
        result: dict[str, object] = {"steps": [], "human_verification": []}
        failures: list[str] = []

        self.module._evaluate_log_validation_output(  # type: ignore[attr-defined]
            result,
            self._observation(
                run_conclusion="failure",
                accessibility_conclusion="failure",
                observed_step_names=["Run axe-core accessibility checks"],
                engine_entries=[],
                semantics_entries=[],
            ),
            failures,
            full_run_log_text="workflow completed",
            full_run_log_error=None,
        )

        self.assertEqual(len(failures), 1)
        self.assertEqual(result["steps"][0]["status"], "failed")
        self.assertIn("did not expose a `log-validation` step", failures[0])
        self.assertIn("did not report that mandatory engine state tokens were missing", failures[0])

    def test_log_validation_message_substring_does_not_count_as_step_surface(self) -> None:
        self.assertFalse(
            self.module._has_log_validation_step(  # type: ignore[attr-defined]
                ["Run axe-core accessibility checks"],
                (
                    "Accessibility checks\tRun axe-core accessibility checks\t"
                    "2026-05-22T11:02:00Z log-validation failed because mandatory "
                    "engine state tokens were not found in the output."
                ),
            )
        )

    def test_stage_isolated_log_validation_step_counts_as_visible_surface(self) -> None:
        self.assertTrue(
            self.module._has_log_validation_step(  # type: ignore[attr-defined]
                ["Run axe-core accessibility checks"],
                (
                    "Accessibility checks\tlog-validation\t2026-05-22T11:02:00Z "
                    "mandatory engine state tokens were not found in the output."
                ),
            )
        )

    def test_step_3_rejects_missing_token_message_from_other_step_output(self) -> None:
        result: dict[str, object] = {"steps": [], "human_verification": []}
        failures: list[str] = []

        self.module._evaluate_log_validation_output(  # type: ignore[attr-defined]
            result,
            self._observation(
                run_conclusion="failure",
                accessibility_conclusion="failure",
                observed_step_names=[
                    "Run axe-core accessibility checks",
                    "log-validation",
                ],
                engine_entries=[],
                semantics_entries=[],
            ),
            failures,
            full_run_log_text=(
                "Accessibility checks\tRun axe-core accessibility checks\t"
                "2026-05-22T11:02:00Z log-validation failed because mandatory "
                "engine state tokens were not found in the output.\n"
                "Accessibility checks\tlog-validation\t2026-05-22T11:02:05Z "
                "node testing/accessibility/log_validation.js accessibility.log"
            ),
            full_run_log_error=None,
        )

        self.assertEqual(len(failures), 1)
        self.assertEqual(result["steps"][0]["status"], "failed")
        self.assertIn(
            "did not report that mandatory engine state tokens were missing",
            failures[0],
        )

    def test_runtime_module_keeps_framework_wiring_inside_support_factory(self) -> None:
        module_source = Path(__file__).with_name("test_ts_943.py").read_text(
            encoding="utf-8"
        )

        self.assertNotIn("GhCliWorkflowRunLogReader", module_source)
        self.assertIn(
            "create_github_accessibility_engine_log_validation_run_log_reader",
            module_source,
        )


if __name__ == "__main__":
    unittest.main()
