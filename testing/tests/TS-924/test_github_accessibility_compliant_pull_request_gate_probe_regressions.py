from __future__ import annotations

import unittest

from testing.components.services.github_accessibility_compliant_pull_request_gate_probe import (
    GitHubAccessibilityCompliantPullRequestGateProbeService,
)


class GitHubAccessibilityCompliantPullRequestGateProbeRegressionTest(
    unittest.TestCase
):
    def test_probe_source_uses_descriptive_label_without_low_contrast_signal(self) -> None:
        source = GitHubAccessibilityCompliantPullRequestGateProbeService._probe_source()

        self.assertIn(
            "label: 'Sync status message: accessibility checks passed'",
            source,
        )
        self.assertIn("colorScheme.onSurface", source)
        self.assertIn("colorScheme.surface", source)
        self.assertNotIn("withAlpha(89)", source)
        self.assertNotIn("label: 'button'", source)


if __name__ == "__main__":
    unittest.main()
