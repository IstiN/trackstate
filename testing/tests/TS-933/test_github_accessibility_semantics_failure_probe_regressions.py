from __future__ import annotations

import json
import unittest

from testing.components.services.github_accessibility_semantics_failure_probe import (
    GitHubAccessibilitySemanticsFailureProbeService,
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


class _StubProbeService(GitHubAccessibilitySemanticsFailureProbeService):
    def __init__(self, config: GitHubAccessibilityPullRequestGateConfig) -> None:
        super().__init__(config, github_api_client=_FakeGitHubApiClient({}))


class GitHubAccessibilitySemanticsFailureProbeRegressionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = GitHubAccessibilityPullRequestGateConfig(
            repository="IstiN/trackstate",
            base_branch="main",
            target_workflow_name="Flutter Required Checks",
            target_workflow_path=".github/workflows/unit-tests.yml",
            probe_path="testing/accessibility/ts933_semantics_failure_simulation.js",
            probe_render_host_path="testing/accessibility/accessibility_gate.spec.js",
            branch_prefix="ts933-semantics-init-failure",
            commit_message="TS-933 probe",
            pull_request_title="TS-933 disposable probe",
            pull_request_body="Disposable PR",
            expected_accessibility_markers=["accessibility", "semantics"],
            contrast_evidence_markers=["timeout"],
            semantic_evidence_markers=["semantics", "nodes"],
            poll_interval_seconds=5,
            run_timeout_seconds=900,
            pull_request_timeout_seconds=180,
        )
        self.probe = _StubProbeService(self.config)

    def test_patch_spec_source_injects_require_and_simulation_call(self) -> None:
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

        self.assertIn(
            "installTs933SemanticsFailureSimulation",
            patched,
        )
        self.assertIn(
            "await installTs933SemanticsFailureSimulation(page);",
            patched,
        )
        self.assertEqual(
            patched.count("installTs933SemanticsFailureSimulation"),
            2,
        )
        self.assertLess(
            patched.index("await installTs933SemanticsFailureSimulation(page);"),
            patched.index("await captureFlutterStartupDiagnostics(page, {"),
        )

    def test_patch_spec_source_supports_legacy_navigation_flow(self) -> None:
        original = """const { test, expect } = require('@playwright/test');
const {
  collectAccessibilityViolations,
  enableFlutterSemantics,
  formatFlutterSemanticsEvidence,
  formatViolations,
} = require('./accessibility_gate');

test('TrackState web app has no axe-core accessibility violations', async ({
  page,
}) => {
  await page.goto('/');
  await expect(page).toHaveTitle(/TrackState\\.AI/);
  await page.waitForLoadState('networkidle');

  const semanticsEvidence = await enableFlutterSemantics(page);
  console.log(formatFlutterSemanticsEvidence(semanticsEvidence));

  const results = await collectAccessibilityViolations(page);

  expect(results, formatViolations(results)).toEqual([]);
});
"""

        patched = self.probe._patch_spec_source(original)  # noqa: SLF001

        self.assertIn(
            "installTs933SemanticsFailureSimulation",
            patched,
        )
        self.assertIn(
            "await installTs933SemanticsFailureSimulation(page);",
            patched,
        )
        self.assertEqual(
            patched.count("installTs933SemanticsFailureSimulation"),
            2,
        )
        self.assertLess(
            patched.index("await installTs933SemanticsFailureSimulation(page);"),
            patched.index("await page.goto('/');"),
        )

    def test_extract_log_excerpt_prioritizes_semantics_failure_message(self) -> None:
        excerpt = self.probe._extract_log_excerpt(  # noqa: SLF001
            """
            prefix
            Error: Flutter engine failed to render semantics nodes during initialization.
            suffix
            """,
            "",
        )

        self.assertIn("Flutter engine failed to render semantics nodes", excerpt)

    def test_accessibility_stage_log_text_excludes_other_jobs(self) -> None:
        stage_log_text = self.probe._accessibility_stage_run_log_text(  # noqa: SLF001
            "\n".join(
                [
                    "Flutter checks\tDetect Flutter changes\t2026-05-22T11:02:00Z waiting for nodes",
                    "Accessibility checks\tRun axe-core accessibility checks\t2026-05-22T11:02:15Z Error: Flutter engine failed to render semantics nodes during initialization.",
                ]
            ),
            jobs=[
                {"name": "Flutter checks"},
                {"name": "Accessibility checks"},
            ],
        )

        self.assertIn(
            "Accessibility checks Run axe-core accessibility checks",
            stage_log_text,
        )
        self.assertNotIn("Flutter checks Detect Flutter changes", stage_log_text)

    def test_simulation_helper_source_hides_flt_semantics_nodes(self) -> None:
        source = self.probe._simulation_helper_source()  # noqa: SLF001

        self.assertIn("Document.prototype.querySelectorAll", source)
        self.assertIn("selectors === 'flt-semantics'", source)
        self.assertIn(
            GitHubAccessibilitySemanticsFailureProbeService.simulation_selector,
            source,
        )


if __name__ == "__main__":
    unittest.main()
