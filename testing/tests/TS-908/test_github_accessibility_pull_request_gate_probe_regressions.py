from __future__ import annotations

import json
import unittest

from testing.components.services.github_accessibility_pull_request_gate_probe import (
    GitHubAccessibilityPullRequestGateProbeService,
)
from testing.core.config.github_accessibility_pull_request_gate_config import (
    GitHubAccessibilityPullRequestGateConfig,
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


class GitHubAccessibilityPullRequestGateProbeRegressionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = GitHubAccessibilityPullRequestGateConfig(
            repository="IstiN/trackstate",
            base_branch="main",
            target_workflow_name="Flutter Required Checks",
            target_workflow_path=".github/workflows/unit-tests.yml",
            expected_accessibility_markers=[
                "axe-core",
                "accessibility",
                "wcag",
                "contrast",
                "aria-label",
                "aria label",
                "semantics label",
            ],
            ui_timeout_seconds=60,
        )

    def test_validate_reports_missing_accessibility_gate_when_pr_workflow_has_no_markers(
        self,
    ) -> None:
        workflow_text = """
name: Flutter Required Checks
on:
  pull_request:
    types: [opened, synchronize]
jobs:
  flutter-checks:
    name: Flutter checks
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
      - name: Analyze
        run: flutter analyze
      - name: Run unit and golden tests
        run: flutter test --coverage
""".strip()

        probe = GitHubAccessibilityPullRequestGateProbeService(
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
                                "state": "active",
                                "html_url": "https://github.com/IstiN/trackstate/actions/workflows/unit-tests.yml",
                            }
                        ]
                    },
                    "/repos/IstiN/trackstate/contents/.github/workflows/unit-tests.yml?ref=main": workflow_text,
                    "/repos/IstiN/trackstate/rules/branches/main": [
                        {
                            "type": "required_status_checks",
                            "parameters": {
                                "contexts": ["Flutter checks"],
                            },
                        }
                    ],
                    "/repos/IstiN/trackstate/branches/main/protection": {
                        "required_status_checks": {
                            "contexts": ["Flutter checks"],
                        }
                    },
                }
            ),
        )

        observation = probe.validate()

        self.assertTrue(observation.target_workflow_present_on_default_branch)
        self.assertTrue(observation.target_workflow_declares_pull_request_trigger)
        self.assertEqual(
            observation.pull_request_workflow_paths,
            [".github/workflows/unit-tests.yml"],
        )
        self.assertEqual(observation.workflows_with_accessibility_markers, [])
        self.assertFalse(observation.repository_declares_accessibility_required_check)
        self.assertIn("Flutter checks", observation.required_check_contexts)


if __name__ == "__main__":
    unittest.main()
