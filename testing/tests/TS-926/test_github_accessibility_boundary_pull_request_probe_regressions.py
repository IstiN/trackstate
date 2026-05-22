from __future__ import annotations

import json
import unittest

from testing.components.services.github_accessibility_boundary_pull_request_probe import (
    GitHubAccessibilityBoundaryPullRequestProbeService,
)
from testing.core.config.github_accessibility_boundary_pull_request_probe_config import (
    GitHubAccessibilityBoundaryPullRequestProbeConfig,
)


class _FakeGitHubApiClient:
    def __init__(self, responses: dict[str, object]) -> None:
        self._responses = responses

    def request_text(
        self,
        *,
        endpoint: str,
        method: str = "GET",
        field_args=None,
        stdin_json=None,
    ) -> str:
        del field_args, stdin_json
        if method != "GET":
            raise AssertionError(f"Unexpected method for regression probe: {method}")
        if endpoint not in self._responses:
            raise AssertionError(f"Unexpected endpoint: {endpoint}")
        response = self._responses[endpoint]
        if isinstance(response, str):
            return response
        return json.dumps(response)


class _StubProbeService(GitHubAccessibilityBoundaryPullRequestProbeService):
    def __init__(self, config: GitHubAccessibilityBoundaryPullRequestProbeConfig) -> None:
        super().__init__(config, github_api_client=_FakeGitHubApiClient({}))

    def _create_and_observe_pull_request(self, workflow_id: int) -> dict[str, object]:
        del workflow_id
        return {
            "pull_request_number": 123,
            "pull_request_url": "https://github.com/IstiN/trackstate/pull/123",
            "pull_request_checks_url": "https://github.com/IstiN/trackstate/pull/123/checks",
            "pull_request_head_branch": "ts926-accessibility-boundary-20260522000000",
            "pull_request_head_sha": "abc123",
            "pull_request_probe_path": "lib/ts926_accessibility_boundary_probe.dart",
            "probe_render_host_path": "lib/ui/features/tracker/views/trackstate_app.dart",
            "probe_rendered_in_application": True,
            "pull_request_file_paths": [
                "lib/ui/features/tracker/views/trackstate_app.dart",
                "lib/ts926_accessibility_boundary_probe.dart",
            ],
            "pull_request_state": "open",
            "pull_request_mergeable_state": "clean",
            "pull_request_status_state": "success",
            "latest_pull_request_run_id": 456,
            "latest_pull_request_run_url": "https://github.com/IstiN/trackstate/actions/runs/456",
            "latest_pull_request_run_event": "pull_request",
            "latest_pull_request_run_status": "completed",
            "latest_pull_request_run_conclusion": "success",
            "observed_branch_run_names": ["Flutter Required Checks"],
            "observed_branch_run_urls": ["https://github.com/IstiN/trackstate/actions/runs/456"],
            "observed_branch_run_statuses": ["completed"],
            "observed_branch_run_conclusions": ["success"],
            "observed_job_names": ["Flutter checks", "Accessibility checks"],
            "observed_step_names": ["Build web app", "Run axe-core accessibility checks"],
            "observed_status_check_names": ["Flutter checks", "Accessibility checks"],
            "observed_status_check_workflow_names": ["Flutter Required Checks"],
            "failed_status_check_names": [],
            "failed_status_check_workflow_names": [],
            "accessibility_status_check_name": "Accessibility checks",
            "accessibility_status_check_workflow_name": "Flutter Required Checks",
            "accessibility_status_check_status": "completed",
            "accessibility_status_check_conclusion": "success",
            "accessibility_status_check_url": "https://example.test/accessibility",
            "matched_accessibility_markers": ["accessibility", "axe-core"],
            "matched_contrast_markers": [],
            "matched_semantic_markers": [],
            "run_log_matched_accessibility_markers": ["axe-core"],
            "run_log_matched_contrast_markers": [],
            "run_log_matched_semantic_markers": [],
            "run_log_mentions_accessibility": True,
            "run_log_mentions_contrast_issue": False,
            "run_log_mentions_semantic_issue": False,
            "run_log_excerpt": "Run axe-core accessibility checks\n1 passed",
            "run_log_error": None,
            "runtime_accessibility_surface_present": True,
            "runtime_accessibility_surface_summary": (
                "Accessibility runtime surface ready: "
                "Boundary contrast sample | Open tracker settings"
            ),
            "probe_contains_low_contrast_indicator": False,
            "probe_contains_semantic_label_indicator": False,
            "probe_semantic_label": "Open tracker settings",
            "probe_contrast_technique": "Uses fixed RGB colors for an exact 4.5:1 boundary.",
            "cleanup_closed_pull_request": True,
            "cleanup_deleted_branch": True,
        }


class GitHubAccessibilityBoundaryPullRequestProbeRegressionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = GitHubAccessibilityBoundaryPullRequestProbeConfig(
            repository="IstiN/trackstate",
            base_branch="main",
            target_workflow_name="Flutter Required Checks",
            target_workflow_path=".github/workflows/unit-tests.yml",
            probe_path="lib/ts926_accessibility_boundary_probe.dart",
            probe_render_host_path="lib/ui/features/tracker/views/trackstate_app.dart",
            branch_prefix="ts926-accessibility-boundary",
            commit_message="TS-926 probe: verify CI accessibility boundary on disposable PR",
            pull_request_title="TS-926 disposable probe: exact accessibility boundary",
            pull_request_body="Disposable PR created by TS-926 automation.",
            expected_accessibility_markers=["accessibility", "axe-core", "playwright"],
            contrast_evidence_markers=["color-contrast"],
            semantic_evidence_markers=["non-descriptive-label"],
            poll_interval_seconds=5,
            run_timeout_seconds=900,
            pull_request_timeout_seconds=180,
            exact_contrast_ratio=4.5,
            contrast_tolerance=0.01,
            text_color="rgb(178, 67, 40)",
            background_color="rgb(241, 228, 213)",
            visible_text="Boundary contrast sample",
            accessible_button_label="Open tracker settings",
        )

    def test_validate_combines_workflow_contract_with_live_pr_observation(self) -> None:
        workflow_text = """
name: Flutter Required Checks
on:
  pull_request:
    types: [opened, synchronize]
jobs:
  accessibility-checks:
    name: Accessibility checks
    runs-on: ubuntu-latest
    steps:
      - name: Build web app for accessibility scan
        run: flutter build web
      - name: Run axe-core accessibility checks
        run: npm run test:a11y
""".strip()

        probe = GitHubAccessibilityBoundaryPullRequestProbeService(
            self.config,
            github_api_client=_FakeGitHubApiClient(
                {
                    "/repos/IstiN/trackstate": {"default_branch": "main"},
                    "/repos/IstiN/trackstate/actions/workflows?per_page=100": {
                        "workflows": [
                            {
                                "id": 1,
                                "name": "Flutter Required Checks",
                                "path": ".github/workflows/unit-tests.yml",
                            }
                        ]
                    },
                    "/repos/IstiN/trackstate/contents/.github/workflows/unit-tests.yml?ref=main": workflow_text,
                }
            ),
        )
        probe._create_and_observe_pull_request = _StubProbeService(  # type: ignore[method-assign]
            self.config
        )._create_and_observe_pull_request

        observation = probe.validate()

        self.assertTrue(observation.target_workflow_present_on_default_branch)
        self.assertTrue(observation.target_workflow_declares_pull_request_trigger)
        self.assertEqual(observation.target_workflow_job_names, ["Accessibility checks"])
        self.assertEqual(
            observation.target_workflow_step_names,
            [
                "Build web app for accessibility scan",
                "Run axe-core accessibility checks",
            ],
        )
        self.assertEqual(
            observation.pull_request_file_paths,
            [
                "lib/ui/features/tracker/views/trackstate_app.dart",
                "lib/ts926_accessibility_boundary_probe.dart",
            ],
        )
        self.assertEqual(observation.latest_pull_request_run_conclusion, "success")
        self.assertTrue(observation.run_log_mentions_accessibility)

    def test_probe_source_uses_ticket_boundary_values(self) -> None:
        probe = _StubProbeService(self.config)

        source = probe._probe_source()  # noqa: SLF001

        self.assertIn("import 'ui/core/trackstate_theme.dart';", source)
        self.assertIn("final colors = context.ts;", source)
        self.assertIn("color: colors.surfaceAlt", source)
        self.assertIn("color: colors.primary", source)
        self.assertIn("'Boundary contrast sample'", source)
        self.assertIn("Semantics(", source)
        self.assertIn("label: 'Open tracker settings'", source)


if __name__ == "__main__":
    unittest.main()
