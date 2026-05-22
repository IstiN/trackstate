from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

from testing.components.services.github_accessibility_pull_request_gate_probe import (
    GitHubAccessibilityPullRequestGateProbeService,
)
from testing.core.config.github_accessibility_pull_request_gate_config import (
    GitHubAccessibilityPullRequestGateConfig,
)
from testing.core.interfaces.github_accessibility_pull_request_gate_probe import (
    GitHubAccessibilityPullRequestGateObservation,
    GitHubAccessibilityWorkflowContractObservation,
)
from testing.core.interfaces.github_actions_preflight_gate_probe import (
    GitHubActionsWorkflowJobObservation,
)


def _load_ts_924_module():
    module_path = Path(__file__).with_name("test_ts_924.py")
    spec = importlib.util.spec_from_file_location("ts_924_runtime", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Ts924ReviewRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = _load_ts_924_module()

    def _observation(
        self,
        *,
        runtime_accessibility_surface_present: bool,
        runtime_accessibility_surface_summary: str,
        accessibility_status_check_conclusion: str | None,
        observed_step_names: list[str] | None = None,
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
            pull_request_number=123,
            pull_request_url="https://github.com/IstiN/trackstate/pull/123",
            pull_request_checks_url="https://github.com/IstiN/trackstate/pull/123/checks",
            pull_request_head_branch="ts924-accessibility-pass-gate",
            pull_request_head_sha="abc123",
            pull_request_probe_path="lib/ts924_probe_surface.dart",
            probe_render_host_path="lib/main.dart",
            probe_rendered_in_application=True,
            pull_request_file_paths=["lib/main.dart", "lib/ts924_probe_surface.dart"],
            pull_request_state="open",
            pull_request_mergeable_state="clean",
            pull_request_status_state="success",
            latest_pull_request_run_id=456,
            latest_pull_request_run_url="https://github.com/IstiN/trackstate/actions/runs/456",
            latest_pull_request_run_event="pull_request",
            latest_pull_request_run_status="completed",
            latest_pull_request_run_conclusion="success",
            observed_branch_run_names=["Flutter Required Checks"],
            observed_branch_run_urls=["https://github.com/IstiN/trackstate/actions/runs/456"],
            observed_branch_run_statuses=["completed"],
            observed_branch_run_conclusions=["success"],
            observed_run_jobs=[
                GitHubActionsWorkflowJobObservation(
                    id=4561,
                    name="Accessibility checks",
                    status="completed",
                    conclusion="success",
                    html_url="https://github.com/IstiN/trackstate/actions/runs/456/job/4561",
                    started_at="2026-05-22T10:50:00Z",
                    completed_at="2026-05-22T10:51:00Z",
                )
            ],
            observed_job_names=["Flutter checks", "Accessibility checks"],
            observed_step_names=observed_step_names
            or ["Build web app for accessibility scan", "Run axe-core accessibility checks"],
            observed_status_check_names=["Flutter checks", "Accessibility checks"],
            observed_status_check_workflow_names=["Flutter Required Checks"],
            failed_status_check_names=[],
            failed_status_check_workflow_names=[],
            accessibility_status_check_name="Accessibility checks",
            accessibility_status_check_workflow_name="Flutter Required Checks",
            accessibility_status_check_status="completed",
            accessibility_status_check_conclusion=accessibility_status_check_conclusion,
            accessibility_status_check_url="https://example.test/accessibility",
            matched_accessibility_markers=["accessibility", "axe-core"],
            matched_contrast_markers=[],
            matched_semantic_markers=["semantics", "label"],
            run_log_matched_accessibility_markers=["accessibility", "axe-core"],
            run_log_matched_contrast_markers=[],
            run_log_matched_semantic_markers=["semantics", "label"],
            run_log_mentions_accessibility=True,
            run_log_mentions_contrast_issue=False,
            run_log_mentions_semantic_issue=True,
            run_log_excerpt="Accessibility runtime surface ready",
            run_log_error=None,
            runtime_accessibility_surface_present=runtime_accessibility_surface_present,
            runtime_accessibility_surface_summary=runtime_accessibility_surface_summary,
            probe_contains_low_contrast_indicator=False,
            probe_contains_semantic_label_indicator=True,
            probe_semantic_label="Sync status message: accessibility checks passed",
            probe_contrast_technique="Uses onSurface text on surface.",
            cleanup_closed_pull_request=True,
            cleanup_deleted_branch=True,
        )

    def test_step_2_requires_runtime_accessibility_surface_evidence(self) -> None:
        result: dict[str, object] = {"steps": []}
        failures: list[str] = []

        self.module._evaluate_compliant_component(  # type: ignore[attr-defined]
            result,
            self._observation(
                runtime_accessibility_surface_present=False,
                runtime_accessibility_surface_summary="",
                accessibility_status_check_conclusion="success",
            ),
            failures,
        )

        self.assertEqual(len(failures), 1)
        self.assertEqual(result["steps"][0]["status"], "failed")
        self.assertIn("browser-visible runtime semantics evidence", result["steps"][0]["observed"])

    def test_step_2_requires_runtime_accessibility_surface_to_include_probe_label(self) -> None:
        result: dict[str, object] = {"steps": []}
        failures: list[str] = []

        self.module._evaluate_compliant_component(  # type: ignore[attr-defined]
            result,
            self._observation(
                runtime_accessibility_surface_present=True,
                runtime_accessibility_surface_summary=(
                    'Accessibility runtime surface ready: hosts=1; nodes=4; '
                    'sample-labels=["Different runtime label"]'
                ),
                accessibility_status_check_conclusion="success",
            ),
            failures,
        )

        self.assertEqual(len(failures), 1)
        self.assertEqual(result["steps"][0]["status"], "failed")
        self.assertIn(
            "did not include the expected descriptive semantics label",
            result["steps"][0]["observed"],
        )

    def test_step_4_rejects_skipped_accessibility_check(self) -> None:
        result: dict[str, object] = {"steps": [], "human_verification": []}
        failures: list[str] = []

        self.module._evaluate_accessibility_gate_result(  # type: ignore[attr-defined]
            result,
            self._observation(
                runtime_accessibility_surface_present=True,
                runtime_accessibility_surface_summary=(
                    'Accessibility runtime surface ready: hosts=1; nodes=4; '
                    'sample-labels=["Sync status message: accessibility checks passed"]'
                ),
                accessibility_status_check_conclusion="skipped",
            ),
            failures,
        )

        self.assertEqual(len(failures), 1)
        self.assertEqual(result["steps"][0]["status"], "failed")

    def test_step_4_rejects_neutral_accessibility_check(self) -> None:
        result: dict[str, object] = {"steps": [], "human_verification": []}
        failures: list[str] = []

        self.module._evaluate_accessibility_gate_result(  # type: ignore[attr-defined]
            result,
            self._observation(
                runtime_accessibility_surface_present=True,
                runtime_accessibility_surface_summary=(
                    'Accessibility runtime surface ready: hosts=1; nodes=4; '
                    'sample-labels=["Sync status message: accessibility checks passed"]'
                ),
                accessibility_status_check_conclusion="neutral",
            ),
            failures,
        )

        self.assertEqual(len(failures), 1)
        self.assertEqual(result["steps"][0]["status"], "failed")


class _ReadCheckRunsStateProbe(GitHubAccessibilityPullRequestGateProbeService):
    def __init__(self, check_runs_payload: dict[str, object]) -> None:
        config = GitHubAccessibilityPullRequestGateConfig(
            repository="IstiN/trackstate",
            base_branch="main",
            target_workflow_name="Flutter Required Checks",
            target_workflow_path=".github/workflows/unit-tests.yml",
            probe_path="lib/ts924_probe_surface.dart",
            probe_render_host_path="lib/main.dart",
            branch_prefix="ts924-accessibility-pass-gate",
            commit_message="TS-924 probe",
            pull_request_title="TS-924 disposable probe",
            pull_request_body="Disposable PR",
            expected_accessibility_markers=["accessibility"],
            contrast_evidence_markers=["contrast"],
            semantic_evidence_markers=["semantic"],
            poll_interval_seconds=5,
            run_timeout_seconds=900,
            pull_request_timeout_seconds=180,
        )
        super().__init__(config, github_api_client=object())  # type: ignore[arg-type]
        self._check_runs_payload = check_runs_payload

    def _read_json_object(  # type: ignore[override]
        self,
        endpoint: str,
        *,
        method: str = "GET",
        field_args: list[str] | None = None,
    ) -> dict[str, object]:
        del method, field_args
        if endpoint.endswith("/check-runs?per_page=100"):
            return self._check_runs_payload
        if endpoint.endswith("/status"):
            return {"state": "pending"}
        raise AssertionError(f"Unexpected endpoint: {endpoint}")


class GitHubAccessibilityPullRequestGateProbeRegressionTest(unittest.TestCase):
    def test_read_check_runs_state_does_not_treat_neutral_or_skipped_as_success(self) -> None:
        neutral_probe = _ReadCheckRunsStateProbe(
            {
                "check_runs": [
                    {"status": "completed", "conclusion": "neutral"},
                    {"status": "completed", "conclusion": "success"},
                ]
            }
        )
        skipped_probe = _ReadCheckRunsStateProbe(
            {
                "check_runs": [
                    {"status": "completed", "conclusion": "skipped"},
                    {"status": "completed", "conclusion": "success"},
                ]
            }
        )

        self.assertEqual(neutral_probe._read_check_runs_state("abc123"), "pending")  # noqa: SLF001
        self.assertEqual(skipped_probe._read_check_runs_state("abc123"), "pending")  # noqa: SLF001


if __name__ == "__main__":
    unittest.main()
