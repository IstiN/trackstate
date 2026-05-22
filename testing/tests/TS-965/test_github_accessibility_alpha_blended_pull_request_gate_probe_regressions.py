from __future__ import annotations

import unittest

from testing.components.services.github_accessibility_alpha_blended_pull_request_gate_probe import (
    GitHubAccessibilityAlphaBlendedPullRequestGateProbeService,
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
        raise AssertionError("Network access is not expected in TS-965 regressions.")


class GitHubAccessibilityAlphaBlendedPullRequestGateProbeRegressionTest(
    unittest.TestCase
):
    def test_probe_source_renders_alpha_text_and_publishes_flattened_signal(self) -> None:
        source = GitHubAccessibilityAlphaBlendedPullRequestGateProbeService._probe_source()

        self.assertIn("publishAccessibilityContrastProbeSignal(", source)
        self.assertIn(
            "final lowContrastColor = colorScheme.onSurface.withAlpha(89);",
            source,
        )
        self.assertIn(
            "final flattenedProbeColor = Color.alphaBlend(lowContrastColor, colorScheme.surface);",
            source,
        )
        self.assertIn("foreground: flattenedProbeColor", source)
        self.assertIn("background: colorScheme.surface", source)
        self.assertIn(
            "label: 'Alpha-blended sync status message'",
            source,
        )
        self.assertIn("ExcludeSemantics(", source)
        self.assertNotIn("label: 'button'", source)

    def test_flattened_probe_signal_matches_expected_runtime_contract(self) -> None:
        signal = GitHubAccessibilityAlphaBlendedPullRequestGateProbeService.flattened_probe_signal(
            foreground_rgb=(0x2D, 0x2A, 0x26),
            background_rgb=(0xFF, 0xFF, 0xFF),
        )

        self.assertEqual(signal["foreground_hex"], "#B6B5B3")
        self.assertEqual(signal["background_hex"], "#FFFFFF")
        self.assertAlmostEqual(signal["contrast_ratio"], 2.0554, places=4)
        self.assertLess(signal["contrast_ratio"], 4.5)

    def test_create_and_observe_pull_request_derives_label_and_indicator(self) -> None:
        class _DerivedProbeService(
            GitHubAccessibilityAlphaBlendedPullRequestGateProbeService
        ):
            @classmethod
            def _probe_source(cls) -> str:
                return """import 'package:flutter/material.dart';

class Ts965ProbeSurface extends StatelessWidget {
  const Ts965ProbeSurface({super.key});

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final lowContrastColor = colorScheme.onSurface.withAlpha(89);
    final flattenedProbeColor = Color.alphaBlend(lowContrastColor, colorScheme.surface);
    publishAccessibilityContrastProbeSignal(
      text: 'Alpha blended sync warning',
      semanticsLabel: 'Observed alpha label',
      foreground: flattenedProbeColor,
      background: colorScheme.surface,
    );
    return Semantics(
      label: 'Observed alpha label',
      child: Container(
        color: colorScheme.surface,
        child: Text(
          'Alpha blended sync warning',
          style: TextStyle(
            color: lowContrastColor,
          ),
        ),
      ),
    );
  }
}
"""

        config = GitHubAccessibilityPullRequestGateConfig(
            repository="IstiN/trackstate",
            base_branch="main",
            target_workflow_name="Flutter Required Checks",
            target_workflow_path=".github/workflows/unit-tests.yml",
            probe_path="lib/ts965_alpha_blended_probe.dart",
            probe_render_host_path="lib/main.dart",
            branch_prefix="ts965-alpha-blended-contrast",
            commit_message="TS-965 probe",
            pull_request_title="TS-965 disposable probe",
            pull_request_body="Disposable PR",
            expected_accessibility_markers=["accessibility"],
            contrast_evidence_markers=["contrast"],
            semantic_evidence_markers=["semantics"],
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

        self.assertTrue(observation["probe_contains_low_contrast_indicator"])
        self.assertTrue(observation["probe_contains_semantic_label_indicator"])
        self.assertEqual(observation["probe_semantic_label"], "Observed alpha label")
        self.assertIn("alpha-flattened foreground", observation["probe_contrast_technique"])


if __name__ == "__main__":
    unittest.main()
