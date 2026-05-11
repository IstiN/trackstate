from __future__ import annotations

import unittest

from testing.components.services.actionlint_required_pull_request_gate_probe import (
    ActionlintRequiredPullRequestGateProbeService,
)
from testing.core.config.actionlint_required_pull_request_gate_config import (
    ActionlintRequiredPullRequestGateConfig,
)


class _UnusedGitHubApiClient:
    def request_text(
        self,
        *,
        endpoint: str,
        method: str = "GET",
        field_args=None,
        stdin_json=None,
    ) -> str:
        del endpoint, method, field_args, stdin_json
        raise NotImplementedError


class ActionlintRequiredPullRequestGateProbeLogExcerptTest(unittest.TestCase):
    def setUp(self) -> None:
        self.probe = ActionlintRequiredPullRequestGateProbeService(
            ActionlintRequiredPullRequestGateConfig(
                repository="IstiN/trackstate-setup",
                base_branch="main",
                target_workflow_name="Release on main",
                target_workflow_path=".github/workflows/release-on-main.yml",
                branch_prefix="ts257-actionlint-required-pr",
                commit_message="TS-257 probe",
                mutation_search_text="branches: [main]",
                mutation_replacement_text="branches: [main",
                pull_request_title="TS-257 probe",
                pull_request_body="Disposable PR",
                expected_actionlint_marker="actionlint",
            ),
            github_api_client=_UnusedGitHubApiClient(),
        )

    def test_extract_actionlint_log_excerpt_prefers_target_workflow_error_region(self) -> None:
        log_text = "\n".join(
            [
                "prepare\tSet up job\t2026-05-10T00:00:00Z",
                "lint\tCheckout\t2026-05-10T00:00:01Z",
                (
                    "lint\tRun actionlint\t2026-05-10T00:00:02Z "
                    ".github/workflows/release-on-main.yml:4:21: syntax error: "
                    "did not find expected ',' or ']'"
                ),
                "lint\tPost Run actionlint\t2026-05-10T00:00:03Z",
                "cleanup\tComplete job\t2026-05-10T00:00:04Z",
            ]
        )

        excerpt = self.probe._extract_actionlint_log_excerpt(log_text)

        self.assertIn(".github/workflows/release-on-main.yml", excerpt)
        self.assertIn("syntax error", excerpt)
        self.assertNotIn("prepare\tSet up job", excerpt)


if __name__ == "__main__":
    unittest.main()
