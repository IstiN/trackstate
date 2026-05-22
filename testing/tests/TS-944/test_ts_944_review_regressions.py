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


def _load_ts_944_module():
    module_path = Path(__file__).with_name("test_ts_944.py")
    spec = importlib.util.spec_from_file_location("ts_944_runtime", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Ts944ReviewRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = _load_ts_944_module()

    def _observation(
        self,
        *,
        engine_entries: list[str],
        semantics_entries: list[str],
        runtime_surface_summary: str = "",
        run_log_excerpt: str = (
            "Accessibility checks 2026-05-22T11:02:00Z Flutter engine initialization: "
            "bootstrap requested\n"
            "Accessibility checks 2026-05-22T11:02:01Z Flutter engine initialization: "
            "page loaded\n"
            "TS-944 simulated Flutter engine crash after bootstrap"
        ),
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
            target_workflow_step_names=["Build web app", "Run axe-core accessibility checks"],
            target_workflow_accessibility_job_names=["Accessibility checks"],
            target_workflow_downstream_job_names=["Deploy preview"],
            target_workflow_downstream_job_depends_on_accessibility=True,
            target_workflow=GitHubAccessibilityWorkflowContractObservation(
                declares_pull_request_trigger=True,
                job_names=["Flutter checks", "Accessibility checks", "Deploy preview"],
                step_names=["Build web app", "Run axe-core accessibility checks"],
                accessibility_job_names=["Accessibility checks"],
                downstream_job_names=["Deploy preview"],
                downstream_job_depends_on_accessibility=True,
            ),
            pull_request_number=944,
            pull_request_url="https://github.com/IstiN/trackstate/pull/944",
            pull_request_checks_url="https://github.com/IstiN/trackstate/pull/944/checks",
            pull_request_head_branch="ts944-early-engine-crash",
            pull_request_head_sha="abc123",
            pull_request_probe_path="testing/accessibility/ts944_early_engine_crash_simulation.js",
            probe_render_host_path="testing/accessibility/accessibility_gate.spec.js",
            probe_rendered_in_application=True,
            pull_request_file_paths=[
                "testing/accessibility/accessibility_gate.spec.js",
                "testing/accessibility/ts944_early_engine_crash_simulation.js",
            ],
            pull_request_state="open",
            pull_request_mergeable_state="clean",
            pull_request_status_state="failure",
            latest_pull_request_run_id=456,
            latest_pull_request_run_url="https://github.com/IstiN/trackstate/actions/runs/456",
            latest_pull_request_run_event="pull_request",
            latest_pull_request_run_status="completed",
            latest_pull_request_run_conclusion="failure",
            observed_branch_run_names=["Flutter Required Checks"],
            observed_branch_run_urls=["https://github.com/IstiN/trackstate/actions/runs/456"],
            observed_branch_run_statuses=["completed"],
            observed_branch_run_conclusions=["failure"],
            observed_run_jobs=[
                GitHubActionsWorkflowJobObservation(
                    id=4561,
                    name="Accessibility checks",
                    status="completed",
                    conclusion="failure",
                    html_url="https://github.com/IstiN/trackstate/actions/runs/456/job/4561",
                    started_at="2026-05-22T11:05:00Z",
                    completed_at="2026-05-22T11:06:00Z",
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
            accessibility_status_check_conclusion="failure",
            accessibility_status_check_url="https://example.test/accessibility",
            matched_accessibility_markers=["accessibility", "flutter engine initialization"],
            matched_contrast_markers=["timeout"],
            matched_semantic_markers=["semantics"],
            run_log_matched_accessibility_markers=["accessibility", "flutter engine initialization"],
            run_log_matched_contrast_markers=["timeout"],
            run_log_matched_semantic_markers=["semantics"],
            run_log_mentions_accessibility=True,
            run_log_mentions_contrast_issue=True,
            run_log_mentions_semantic_issue=True,
            run_log_excerpt=run_log_excerpt,
            run_log_error=None,
            runtime_accessibility_surface_present=bool(runtime_surface_summary),
            runtime_accessibility_surface_summary=runtime_surface_summary,
            probe_contains_low_contrast_indicator=False,
            probe_contains_semantic_label_indicator=False,
            probe_semantic_label="",
            probe_contrast_technique="Simulated early engine crash through testing/accessibility only.",
            cleanup_closed_pull_request=True,
            cleanup_deleted_branch=True,
            flutter_engine_initialization_log_entries=engine_entries,
            flutter_engine_initialization_summary=" | ".join(engine_entries),
            semantics_tree_discovery_log_entries=semantics_entries,
            semantics_tree_discovery_summary=" | ".join(semantics_entries),
        )

    def test_step_3_requires_multiple_initial_engine_states(self) -> None:
        result: dict[str, object] = {"steps": [], "human_verification": []}
        failures: list[str] = []

        self.module._evaluate_startup_tokens(  # type: ignore[attr-defined]
            result,
            self._observation(
                engine_entries=["Flutter engine initialization: bootstrap requested"],
                semantics_entries=["Semantics tree discovery: waiting for nodes"],
            ),
            failures,
        )

        self.assertEqual(len(failures), 1)
        self.assertEqual(result["steps"][0]["status"], "failed")
        self.assertIn("missing states: ['page loaded']", failures[0])

    def test_step_3_rejects_surface_ready_evidence(self) -> None:
        result: dict[str, object] = {"steps": [], "human_verification": []}
        failures: list[str] = []

        self.module._evaluate_startup_tokens(  # type: ignore[attr-defined]
            result,
            self._observation(
                engine_entries=[
                    "Flutter engine initialization: bootstrap requested",
                    "Flutter engine initialization: page loaded",
                ],
                semantics_entries=[
                    "Semantics tree discovery: waiting for nodes",
                    "Accessibility runtime surface ready: hosts=1; nodes=5",
                ],
                runtime_surface_summary="Accessibility runtime surface ready: hosts=1; nodes=5",
            ),
            failures,
        )

        self.assertEqual(len(failures), 1)
        self.assertEqual(result["steps"][0]["status"], "failed")
        self.assertIn("still reached `Accessibility runtime surface ready`", failures[0])

    def test_step_3_accepts_partial_startup_before_crash(self) -> None:
        result: dict[str, object] = {"steps": [], "human_verification": []}
        failures: list[str] = []

        self.module._evaluate_startup_tokens(  # type: ignore[attr-defined]
            result,
            self._observation(
                engine_entries=[
                    "Flutter engine initialization: bootstrap requested",
                    "Flutter engine initialization: page loaded",
                ],
                semantics_entries=["Semantics tree discovery: waiting for nodes"],
            ),
            failures,
        )

        self.assertEqual(failures, [])
        self.assertEqual(result["steps"][0]["status"], "passed")


if __name__ == "__main__":
    unittest.main()
