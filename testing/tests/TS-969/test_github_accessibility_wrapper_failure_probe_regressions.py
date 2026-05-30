from __future__ import annotations

import json
import unittest

from testing.components.services.github_accessibility_wrapper_failure_probe import (
    GitHubAccessibilityWrapperFailureProbeService,
)
from testing.core.config.github_accessibility_pull_request_gate_config import (
    GitHubAccessibilityPullRequestGateConfig,
)


class _FakeGitHubApiClient:
    def request_text(
        self,
        *,
        endpoint: str,
        method: str = "GET",
        field_args=None,
        stdin_json=None,
    ) -> str:
        del endpoint, method, field_args, stdin_json
        raise AssertionError("Regression tests should not call GitHub.")


class _StubProbeService(GitHubAccessibilityWrapperFailureProbeService):
    def __init__(self, config: GitHubAccessibilityPullRequestGateConfig) -> None:
        super().__init__(config, github_api_client=_FakeGitHubApiClient())


class GitHubAccessibilityWrapperFailureProbeRegressionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = GitHubAccessibilityPullRequestGateConfig(
            repository="IstiN/trackstate",
            base_branch="main",
            target_workflow_name="Flutter Required Checks",
            target_workflow_path=".github/workflows/unit-tests.yml",
            probe_path="testing/accessibility/ts969_wrapper_contract_failure.node.test.js",
            probe_render_host_path="package.json",
            branch_prefix="ts969-wrapper-failure-propagation",
            commit_message="TS-969 probe",
            pull_request_title="TS-969 disposable probe",
            pull_request_body="Disposable PR",
            expected_accessibility_markers=["Accessibility checks", "Run axe-core accessibility checks"],
            contrast_evidence_markers=["TS-969 simulated contract validation failure"],
            semantic_evidence_markers=["npm run test:a11y", "node --test"],
            poll_interval_seconds=5,
            run_timeout_seconds=900,
            pull_request_timeout_seconds=180,
        )
        self.probe = _StubProbeService(self.config)

    def test_probe_source_contains_failing_contract_validation_test(self) -> None:
        source = self.probe._probe_source()  # noqa: SLF001

        self.assertIn("TS-969 simulated contract validation failure", source)
        self.assertIn("standardized wrapper must propagate exit code 1", source)
        self.assertIn("assert.fail(", source)
        self.assertIn("node:test", source)

    def test_patch_package_json_source_updates_test_a11y_script_only(self) -> None:
        original = json.dumps(
            {
                "name": "trackstate-accessibility",
                "private": True,
                "scripts": {
                    "test:a11y": "playwright test",
                    "lint": "eslint .",
                },
                "devDependencies": {"@playwright/test": "^1.54.2"},
            },
            indent=2,
        )
        patched = self.probe._patch_package_json_source(original)  # noqa: SLF001
        payload = json.loads(patched)

        self.assertEqual(
            payload["scripts"]["test:a11y"],
            "node --test testing/accessibility/ts969_wrapper_contract_failure.node.test.js",
        )
        self.assertEqual(payload["scripts"]["lint"], "eslint .")
        self.assertEqual(payload["name"], "trackstate-accessibility")
        self.assertEqual(payload["devDependencies"]["@playwright/test"], "^1.54.2")

    def test_extract_log_excerpt_prioritizes_wrapper_failure_message(self) -> None:
        excerpt = self.probe._extract_log_excerpt(  # noqa: SLF001
            """
            prefix
            Accessibility checks\tRun axe-core accessibility checks\tTS-969 simulated contract validation failure: standardized wrapper must propagate exit code 1.
            Accessibility checks\tRun axe-core accessibility checks\tProcess completed with exit code 1.
            suffix
            """,
            "",
        )

        self.assertIn("TS-969 simulated contract validation failure", excerpt)
        self.assertIn("Process completed with exit code 1", excerpt)


if __name__ == "__main__":
    unittest.main()
