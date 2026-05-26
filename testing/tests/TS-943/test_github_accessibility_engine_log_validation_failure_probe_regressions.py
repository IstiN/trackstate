from __future__ import annotations

import json
import unittest

from testing.components.services.github_accessibility_engine_log_validation_failure_probe import (
    GitHubAccessibilityEngineLogValidationFailureProbeService,
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


class _StubProbeService(GitHubAccessibilityEngineLogValidationFailureProbeService):
    def __init__(self, config: GitHubAccessibilityPullRequestGateConfig) -> None:
        super().__init__(config, github_api_client=_FakeGitHubApiClient({}))


class GitHubAccessibilityEngineLogValidationFailureProbeRegressionTest(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.config = GitHubAccessibilityPullRequestGateConfig(
            repository="IstiN/trackstate",
            base_branch="main",
            target_workflow_name="Flutter Required Checks",
            target_workflow_path=".github/workflows/unit-tests.yml",
            probe_path="testing/accessibility/ts943_silent_engine_logger.js",
            probe_render_host_path="testing/accessibility/accessibility_gate.spec.js",
            branch_prefix="ts943-engine-log-validation",
            commit_message="TS-943 probe",
            pull_request_title="TS-943 disposable probe",
            pull_request_body="Disposable PR",
            expected_accessibility_markers=["log-validation", "engine state tokens"],
            contrast_evidence_markers=["failed"],
            semantic_evidence_markers=["Flutter engine initialization"],
            poll_interval_seconds=5,
            run_timeout_seconds=900,
            pull_request_timeout_seconds=180,
        )
        self.probe = _StubProbeService(self.config)

    def test_patch_spec_source_injects_silent_logger(self) -> None:
        original = """const { test, expect } = require('@playwright/test');
const {
  captureFlutterStartupDiagnostics,
  collectAccessibilityViolations,
  formatViolations,
} = require('./accessibility_gate');

test('TrackState web app has no axe-core accessibility violations', async ({
  page,
}) => {
  await captureFlutterStartupDiagnostics(page, {
    log: (entry) => console.log(entry),
  });
  await expect(page).toHaveTitle(/TrackState\\.AI/);

  const results = await collectAccessibilityViolations(page);

  expect(results, formatViolations(results)).toEqual([]);
});
"""

        patched = self.probe._patch_spec_source(original)  # noqa: SLF001

        self.assertIn("createTs943SilentEngineLogger", patched)
        self.assertIn("const silentEngineLogger = createTs943SilentEngineLogger();", patched)
        self.assertIn("log: silentEngineLogger,", patched)
        self.assertNotIn("log: (entry) => console.log(entry),", patched)

    def test_extract_log_excerpt_prioritizes_missing_token_failure(self) -> None:
        excerpt = self.probe._extract_log_excerpt(  # noqa: SLF001
            """
            prefix
            Accessibility checks\tRun axe-core accessibility checks\t2026-05-22T11:02:00Z log-validation failed because mandatory engine state tokens were not found in the output.
            suffix
            """,
            "",
        )
        self.assertIn("mandatory engine state tokens were not found", excerpt)
        self.assertIn("mandatory engine state tokens were not found", excerpt)

    def test_runtime_marker_extractors_ignore_missing_token_list_message(self) -> None:
        log_text = """
        Accessibility checks\tlog-validation\t2026-05-22T11:02:00Z log-validation failed because mandatory engine state tokens were not found in the output. Missing tokens: Flutter engine initialization:, Semantics tree discovery:, Accessibility runtime surface ready:.
        """

        self.assertEqual(
            self.probe._extract_flutter_engine_initialization_log_entries(log_text),  # noqa: SLF001
            [],
        )
        self.assertEqual(
            self.probe._extract_semantics_tree_discovery_log_entries(log_text),  # noqa: SLF001
            [],
        )
        self.assertEqual(
            self.probe._extract_runtime_accessibility_surface_summary(log_text),  # noqa: SLF001
            "",
        )
    def test_helper_source_returns_noop_logger(self) -> None:
        source = self.probe._helper_source()  # noqa: SLF001

        self.assertIn("function createTs943SilentEngineLogger()", source)
        self.assertIn("return () => {};", source)


if __name__ == "__main__":
    unittest.main()
