from __future__ import annotations

import unittest

from testing.components.services.github_accessibility_compliant_pull_request_gate_probe import (
    GitHubAccessibilityCompliantPullRequestGateProbeService,
)
from testing.components.services.github_accessibility_pull_request_gate_probe import (
    GitHubAccessibilityPullRequestGateProbeService,
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
        raise AssertionError("Network access is not expected in compliant probe regressions.")


class GitHubAccessibilityCompliantPullRequestGateProbeRegressionTest(
    unittest.TestCase
):
    def test_probe_source_uses_descriptive_label_without_low_contrast_signal(self) -> None:
        source = GitHubAccessibilityCompliantPullRequestGateProbeService._probe_source()

        self.assertIn(
            "label: 'Sync status message: accessibility checks passed'",
            source,
        )
        self.assertIn("container: true", source)
        self.assertIn("readOnly: true", source)
        self.assertIn("ExcludeSemantics(", source)
        self.assertIn("colorScheme.onSurface", source)
        self.assertIn("colorScheme.surface", source)
        self.assertNotIn("withAlpha(89)", source)
        self.assertNotIn("label: 'button'", source)

    def test_create_and_observe_pull_request_derives_label_from_generated_source(self) -> None:
        class _DerivedProbeService(GitHubAccessibilityCompliantPullRequestGateProbeService):
            @classmethod
            def _probe_source(cls) -> str:
                return """import 'package:flutter/material.dart';

class Ts924ProbeSurface extends StatelessWidget {
  const Ts924ProbeSurface({super.key});

  @override
  Widget build(BuildContext context) {
    return const Semantics(
      label: 'Observed runtime-safe label',
      child: SizedBox.shrink(),
    );
  }
}
"""

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
        probe = _DerivedProbeService(config, github_api_client=_FakeGitHubApiClient())
        original = GitHubAccessibilityPullRequestGateProbeService._create_and_observe_pull_request

        def _fake_super_call(self, workflow_id: int) -> dict[str, object]:
            del self, workflow_id
            return {}

        GitHubAccessibilityPullRequestGateProbeService._create_and_observe_pull_request = (  # type: ignore[method-assign]
            _fake_super_call
        )
        try:
            observation = probe._create_and_observe_pull_request(1)  # noqa: SLF001
        finally:
            GitHubAccessibilityPullRequestGateProbeService._create_and_observe_pull_request = (  # type: ignore[method-assign]
                original
            )

        self.assertTrue(observation["probe_contains_semantic_label_indicator"])
        self.assertEqual(
            observation["probe_semantic_label"],
            "Observed runtime-safe label",
        )


if __name__ == "__main__":
    unittest.main()
