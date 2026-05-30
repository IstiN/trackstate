from __future__ import annotations

import unittest

from testing.components.services.actionlint_workflow_gate_probe import (
    ActionlintWorkflowGateProbeService,
)
from testing.core.config.actionlint_workflow_gate_config import (
    ActionlintWorkflowGateConfig,
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


class ActionlintWorkflowGateProbeLogExcerptTest(unittest.TestCase):
    def setUp(self) -> None:
        self.probe = ActionlintWorkflowGateProbeService(
            ActionlintWorkflowGateConfig(
                repository="IstiN/trackstate-setup",
                base_branch="main",
                target_workflow_name="New utility workflow",
                target_workflow_path=".github/workflows/new-utility.yml",
                branch_prefix="ts258-actionlint-directory-coverage",
                commit_message="TS-258 probe: add invalid workflow file",
                mutation_mode="create_file",
                mutation_replacement_text="workflow_dispatch branches",
                created_workflow_contents="name: New Utility",
                expected_actionlint_marker="actionlint",
                expected_log_markers=(
                    ".github/workflows/new-utility.yml",
                    "workflow_dispatch",
                    "branches",
                ),
            ),
            github_api_client=_UnusedGitHubApiClient(),
        )

    def test_extract_actionlint_log_excerpt_prefers_new_workflow_error_region(self) -> None:
        log_text = "\n".join(
            [
                "prepare\tSet up job\t2026-05-10T00:00:00Z",
                "lint\tCheckout\t2026-05-10T00:00:01Z",
                (
                    "lint\tRun actionlint\t2026-05-10T00:00:02Z "
                    ".github/workflows/new-utility.yml:3:5: unexpected key "
                    '"branches" for "workflow_dispatch" section'
                ),
                "lint\tPost Run actionlint\t2026-05-10T00:00:03Z",
                "cleanup\tComplete job\t2026-05-10T00:00:04Z",
            ]
        )

        excerpt = self.probe._extract_actionlint_log_excerpt(log_text)

        self.assertIn(".github/workflows/new-utility.yml", excerpt)
        self.assertIn("workflow_dispatch", excerpt)
        self.assertIn("branches", excerpt)
        self.assertNotIn("prepare\tSet up job", excerpt)


if __name__ == "__main__":
    unittest.main()
