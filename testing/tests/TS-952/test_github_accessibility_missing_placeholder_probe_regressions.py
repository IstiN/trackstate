from __future__ import annotations

import json
import unittest

from testing.components.services.github_accessibility_missing_placeholder_probe import (
    GitHubAccessibilityMissingPlaceholderProbeService,
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


class _StubProbeService(GitHubAccessibilityMissingPlaceholderProbeService):
    def __init__(self, config: GitHubAccessibilityPullRequestGateConfig) -> None:
        super().__init__(config, github_api_client=_FakeGitHubApiClient({}))


class GitHubAccessibilityMissingPlaceholderProbeRegressionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = GitHubAccessibilityPullRequestGateConfig(
            repository="IstiN/trackstate",
            base_branch="main",
            target_workflow_name="Flutter Required Checks",
            target_workflow_path=".github/workflows/unit-tests.yml",
            probe_path="testing/accessibility/ts952_missing_placeholder_simulation.js",
            probe_render_host_path="testing/accessibility/accessibility_gate.spec.js",
            branch_prefix="ts952-missing-semantics-placeholder",
            commit_message="TS-952 probe",
            pull_request_title="TS-952 disposable probe",
            pull_request_body="Disposable PR",
            expected_accessibility_markers=["placeholder", "pre-flight"],
            contrast_evidence_markers=["timeout"],
            semantic_evidence_markers=["flt-semantics-placeholder"],
            poll_interval_seconds=5,
            run_timeout_seconds=900,
            pull_request_timeout_seconds=180,
        )
        self.probe = _StubProbeService(self.config)

    def test_patch_spec_source_injects_missing_placeholder_simulation(self) -> None:
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

        self.assertIn("installTs952MissingPlaceholderSimulation", patched)
        self.assertIn(
            "await installTs952MissingPlaceholderSimulation(page);",
            patched,
        )
        self.assertLess(
            patched.index("await installTs952MissingPlaceholderSimulation(page);"),
            patched.index("await captureFlutterStartupDiagnostics(page, {"),
        )

    def test_helper_source_hides_placeholder_selectors(self) -> None:
        source = self.probe._simulation_helper_source()  # noqa: SLF001

        self.assertIn("flt-semantics-placeholder", source)
        self.assertIn("Document.prototype.querySelectorAll", source)
        self.assertIn("Element.prototype.querySelectorAll", source)
        self.assertIn("MutationObserver", source)
        self.assertIn("removePlaceholders", source)

    def test_extract_log_excerpt_prioritizes_missing_placeholder_failure(self) -> None:
        excerpt = self.probe._extract_log_excerpt(  # noqa: SLF001
            """
            prefix
            Accessibility checks\tRun axe-core accessibility checks\t2026-05-22T11:02:00Z Accessibility pre-flight failed: missing flt-semantics-placeholder before scan.
            suffix
            """,
            "",
        )

        self.assertIn("missing flt-semantics-placeholder", excerpt)


if __name__ == "__main__":
    unittest.main()
