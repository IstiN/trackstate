from __future__ import annotations

import json
import unittest

from testing.components.services.pull_request_release_dry_run_probe import (
    PullRequestReleaseDryRunProbeService,
)
from testing.core.config.pull_request_release_dry_run_config import (
    PullRequestReleaseDryRunConfig,
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
    ) -> str:
        del method, field_args
        return json.dumps(self._responses[endpoint])


def _build_probe(responses: dict[str, object] | None = None) -> PullRequestReleaseDryRunProbeService:
    return PullRequestReleaseDryRunProbeService(
        PullRequestReleaseDryRunConfig(
            repository="IstiN/trackstate-setup",
            workflow_path=".github/workflows/release-on-main.yml",
            workflow_name="Release on main",
            dry_run_name_markers=("dry run", "dry-run"),
            dry_run_command_markers=("--dry-run", "dry-run"),
            base_branch="main",
            probe_file_path="README.md",
            branch_prefix="ts250-release-dry-run-probe",
            pull_request_title="TS-250 disposable probe",
            pull_request_body="TS-250 disposable probe body",
        ),
        github_api_client=_FakeGitHubApiClient(responses or {}),
    )


class PullRequestReleaseDryRunProbeSelectionTest(unittest.TestCase):
    def test_workflow_declares_pull_request_for_inline_and_target_triggers(self) -> None:
        probe = _build_probe()

        self.assertTrue(
            probe._workflow_declares_pull_request(
                "on:\n  pull_request: [opened, synchronize]\n"
            )
        )
        self.assertTrue(
            probe._workflow_declares_pull_request(
                "on:\n  pull_request: {branches: [main]}\n"
            )
        )
        self.assertTrue(
            probe._workflow_declares_pull_request(
                "on:\n  pull_request_target:\n    branches: [main]\n"
            )
        )

    def test_list_branch_runs_accepts_pull_request_target_runs(self) -> None:
        branch_name = "ts250-probe-branch"
        probe = _build_probe(
            {
                (
                    "/repos/IstiN/trackstate-setup/actions/runs"
                    f"?branch={branch_name}&per_page=100"
                ): {
                    "workflow_runs": [
                        {
                            "id": 1,
                            "event": "push",
                            "head_branch": branch_name,
                            "created_at": "2030-01-01T00:00:20Z",
                        },
                        {
                            "id": 2,
                            "event": "pull_request_target",
                            "head_branch": branch_name,
                            "created_at": "2030-01-01T00:00:30Z",
                        },
                        {
                            "id": 3,
                            "event": "pull_request",
                            "head_branch": branch_name,
                            "created_at": "2030-01-01T00:00:10Z",
                        },
                    ]
                }
            }
        )

        runs = probe._list_branch_runs(branch_name, started_at=0)

        self.assertEqual([run["id"] for run in runs], [2, 3])
        self.assertEqual(
            [run["event"] for run in runs],
            ["pull_request_target", "pull_request"],
        )


if __name__ == "__main__":
    unittest.main()
