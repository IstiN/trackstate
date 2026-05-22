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


def _load_ts_952_module():
    module_path = Path(__file__).with_name("test_ts_952.py")
    spec = importlib.util.spec_from_file_location("ts_952_runtime", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Ts952ReviewRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = _load_ts_952_module()

    def _observation(
        self,
        *,
        run_log_excerpt: str,
        run_log_error: str | None = None,
        run_log_matched_contrast_markers: list[str] | None = None,
        run_log_mentions_contrast_issue: bool | None = None,
        run_conclusion: str = "failure",
        accessibility_check_conclusion: str = "failure",
        run_status: str = "completed",
        runtime_accessibility_surface_present: bool = False,
        runtime_accessibility_surface_summary: str = "",
        semantics_tree_discovery_log_entries: list[str] | None = None,
        flutter_engine_initialization_log_entries: list[str] | None = None,
    ) -> GitHubAccessibilityPullRequestGateObservation:
        matched_contrast_markers = list(run_log_matched_contrast_markers or [])
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
            pull_request_head_branch="ts952-missing-semantics-placeholder",
            pull_request_head_sha="abc123",
            pull_request_probe_path="testing/accessibility/ts952_missing_placeholder_simulation.js",
            probe_render_host_path="testing/accessibility/accessibility_gate.spec.js",
            probe_rendered_in_application=True,
            pull_request_file_paths=[
                "testing/accessibility/ts952_missing_placeholder_simulation.js",
                "testing/accessibility/accessibility_gate.spec.js",
            ],
            pull_request_state="open",
            pull_request_mergeable_state="clean",
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
            observed_step_names=["Run axe-core accessibility checks"],
            observed_status_check_names=["Accessibility checks"],
            observed_status_check_workflow_names=["Flutter Required Checks"],
            failed_status_check_names=["Accessibility checks"],
            failed_status_check_workflow_names=["Flutter Required Checks"],
            accessibility_status_check_name="Accessibility checks",
            accessibility_status_check_workflow_name="Flutter Required Checks",
            accessibility_status_check_status=run_status,
            accessibility_status_check_conclusion=accessibility_check_conclusion,
            accessibility_status_check_url="https://example.test/accessibility",
            matched_accessibility_markers=["accessibility", "placeholder"],
            matched_contrast_markers=[],
            matched_semantic_markers=["placeholder", "pre-flight"],
            run_log_matched_accessibility_markers=["accessibility", "placeholder"],
            run_log_matched_contrast_markers=matched_contrast_markers,
            run_log_matched_semantic_markers=["placeholder", "pre-flight"],
            run_log_mentions_accessibility=True,
            run_log_mentions_contrast_issue=(
                bool(matched_contrast_markers)
                if run_log_mentions_contrast_issue is None
                else run_log_mentions_contrast_issue
            ),
            run_log_mentions_semantic_issue=True,
            run_log_excerpt=run_log_excerpt,
            run_log_error=run_log_error,
            runtime_accessibility_surface_present=runtime_accessibility_surface_present,
            runtime_accessibility_surface_summary=runtime_accessibility_surface_summary,
            probe_contains_low_contrast_indicator=False,
            probe_contains_semantic_label_indicator=False,
            probe_semantic_label="",
            probe_contrast_technique="TS-952 simulation",
            cleanup_closed_pull_request=True,
            cleanup_deleted_branch=True,
            flutter_engine_initialization_log_entries=list(
                flutter_engine_initialization_log_entries or []
            ),
            flutter_engine_initialization_summary="",
            semantics_tree_discovery_log_entries=list(
                semantics_tree_discovery_log_entries or []
            ),
            semantics_tree_discovery_summary="",
        )

    def test_step_3_accepts_descriptive_missing_placeholder_preflight_error(self) -> None:
        result: dict[str, object] = {"steps": [], "human_verification": []}
        failures: list[str] = []

        self.module._evaluate_error_log(  # type: ignore[attr-defined]
            result,
            self._observation(
                run_log_excerpt=(
                    "Error: Accessibility pre-flight failed because flt-semantics-placeholder "
                    "was missing before the scan could begin."
                )
            ),
            failures,
            stage_log_lines=[
                "Accessibility checks\tRun axe-core accessibility checks\t2026-05-22T11:02:01Z Accessibility pre-flight failed because flt-semantics-placeholder was missing before the scan could begin."
            ],
        )

        self.assertEqual(failures, [])
        self.assertEqual(result["steps"][0]["status"], "passed")

    def test_step_3_rejects_generic_waitforselector_timeout(self) -> None:
        result: dict[str, object] = {"steps": [], "human_verification": []}
        failures: list[str] = []

        self.module._evaluate_error_log(  # type: ignore[attr-defined]
            result,
            self._observation(
                run_log_excerpt="Error: page.waitForSelector: Test timeout of 15000ms exceeded.",
            ),
            failures,
            stage_log_lines=[
                "Accessibility checks\tRun axe-core accessibility checks\t2026-05-22T11:02:01Z Error: page.waitForSelector: Test timeout of 15000ms exceeded."
            ],
        )

        self.assertEqual(len(failures), 1)
        self.assertEqual(result["steps"][0]["status"], "failed")
        self.assertIn("generic Playwright timeout", failures[0])

    def test_step_3_rejects_full_log_timeout_markers_outside_excerpt(self) -> None:
        result: dict[str, object] = {"steps": [], "human_verification": []}
        failures: list[str] = []

        self.module._evaluate_error_log(  # type: ignore[attr-defined]
            result,
            self._observation(
                run_log_excerpt=(
                    "Error: Accessibility pre-flight failed because flt-semantics-placeholder "
                    "was missing before the scan could begin."
                ),
                run_log_matched_contrast_markers=["page.waitForSelector", "timeout"],
                run_log_mentions_contrast_issue=True,
            ),
            failures,
            stage_log_lines=[
                "Accessibility checks\tRun axe-core accessibility checks\t2026-05-22T11:02:01Z Accessibility pre-flight failed because flt-semantics-placeholder was missing before the scan could begin."
            ],
        )

        self.assertEqual(len(failures), 1)
        self.assertEqual(result["steps"][0]["status"], "failed")
        self.assertIn("generic Playwright timeout", failures[0])
        self.assertIn("Run-log timeout markers", failures[0])

    def test_step_3_rejects_polling_progression_after_missing_placeholder(self) -> None:
        result: dict[str, object] = {"steps": [], "human_verification": []}
        failures: list[str] = []
        stage_lines = [
            "Accessibility checks\tRun axe-core accessibility checks\t2026-05-22T11:02:01Z Accessibility pre-flight failed because flt-semantics-placeholder was missing before the scan could begin.",
            "Accessibility checks\tRun axe-core accessibility checks\t2026-05-22T11:02:03Z Semantics tree discovery: verified flt-semantics-placeholder",
        ]

        self.module._evaluate_error_log(  # type: ignore[attr-defined]
            result,
            self._observation(
                run_log_excerpt="\n".join(stage_lines),
                semantics_tree_discovery_log_entries=[stage_lines[1]],
            ),
            failures,
            stage_log_lines=stage_lines,
        )

        self.assertEqual(len(failures), 1)
        self.assertEqual(result["steps"][0]["status"], "failed")
        self.assertIn("unexpectedly continued into later polling/runtime evidence", failures[0])

    def test_step_3_rejects_full_log_polling_evidence_outside_excerpt(self) -> None:
        result: dict[str, object] = {"steps": [], "human_verification": []}
        failures: list[str] = []
        full_log_polling_line = (
            "Accessibility checks\tRun axe-core accessibility checks\t2026-05-22T11:02:03Z "
            "Semantics tree discovery: verified flt-semantics-placeholder"
        )

        self.module._evaluate_error_log(  # type: ignore[attr-defined]
            result,
            self._observation(
                run_log_excerpt=(
                    "Error: Accessibility pre-flight failed because flt-semantics-placeholder "
                    "was missing before the scan could begin."
                ),
                semantics_tree_discovery_log_entries=[full_log_polling_line],
            ),
            failures,
            stage_log_lines=[
                "Accessibility checks\tRun axe-core accessibility checks\t2026-05-22T11:02:01Z Accessibility pre-flight failed because flt-semantics-placeholder was missing before the scan could begin."
            ],
        )

        self.assertEqual(len(failures), 1)
        self.assertEqual(result["steps"][0]["status"], "failed")
        self.assertIn("unexpectedly continued into later polling/runtime evidence", failures[0])

    def test_step_2_requires_failed_accessibility_check(self) -> None:
        result: dict[str, object] = {"steps": [], "human_verification": []}
        failures: list[str] = []

        self.module._evaluate_preflight_stage_surface(  # type: ignore[attr-defined]
            result,
            self._observation(
                run_log_excerpt="Error: missing flt-semantics-placeholder",
                accessibility_check_conclusion="success",
            ),
            failures,
            stage_log_error=None,
            stage_log_lines=[
                "Accessibility checks\tRun axe-core accessibility checks\t2026-05-22T11:02:01Z Error: missing flt-semantics-placeholder"
            ],
        )

        self.assertEqual(len(failures), 1)
        self.assertEqual(result["steps"][0]["status"], "failed")
        self.assertIn("did not end in failure", failures[0])


if __name__ == "__main__":
    unittest.main()
