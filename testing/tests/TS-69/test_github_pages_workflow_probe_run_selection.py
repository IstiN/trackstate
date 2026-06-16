from __future__ import annotations

import time
import unittest

from testing.components.services.github_pages_workflow_probe import (
    GitHubCliError,
    GitHubPagesWorkflowProbe,
)
from testing.core.models.github_pages_workflow_probe_config import (
    GitHubPagesWorkflowProbeConfig,
)


class _UnusedGitHubApiClient:
    def request_text(self, **_: object) -> str:
        raise AssertionError("Run selection tests should not hit the gh client.")


class _UnusedUrlTextReader:
    def read_text(self, **_: object) -> str:
        raise AssertionError("Run selection tests should not fetch live URLs.")


class _RunSelectionProbe(GitHubPagesWorkflowProbe):
    def __init__(
        self,
        *,
        workflow_runs_by_poll: list[list[dict[str, object]]],
        run_details: dict[int, dict[str, object]],
        run_timeout_seconds: int = 2,
    ) -> None:
        super().__init__(
            GitHubPagesWorkflowProbeConfig(
                upstream_repository="IstiN/trackstate-setup",
                workflow_file="install-update-trackstate.yml",
                workflow_ref="main",
                trackstate_ref="main",
            ),
            github_api_client=_UnusedGitHubApiClient(),
            url_text_reader=_UnusedUrlTextReader(),
            poll_interval_seconds=0,
            run_timeout_seconds=run_timeout_seconds,
        )
        self._workflow_runs_by_poll = workflow_runs_by_poll
        self._run_details = run_details

    def _list_workflow_runs(self, repository: str) -> list[dict[str, object]]:
        if len(self._workflow_runs_by_poll) > 1:
            return self._workflow_runs_by_poll.pop(0)
        return self._workflow_runs_by_poll[0]

    def _gh_json(
        self,
        endpoint: str,
        *,
        method: str = "GET",
        field_args: list[str] | None = None,
        stdin_json: dict[str, object] | None = None,
    ) -> dict[str, object]:
        del method, field_args, stdin_json
        run_id = int(endpoint.rsplit("/", 1)[1])
        return self._run_details[run_id]


class GitHubPagesWorkflowProbeRunSelectionTest(unittest.TestCase):
    def test_waits_for_newest_non_cancelled_run_after_dispatch(self) -> None:
        dispatch_started_at = time.time()
        created_at = "2030-01-01T00:00:10Z"
        newer_created_at = "2030-01-01T00:00:20Z"
        probe = _RunSelectionProbe(
            workflow_runs_by_poll=[
                [
                    {"id": 101, "created_at": created_at, "event": "workflow_dispatch"},
                    {
                        "id": 102,
                        "created_at": newer_created_at,
                        "event": "workflow_dispatch",
                    },
                ],
                [
                    {"id": 101, "created_at": created_at, "event": "workflow_dispatch"},
                    {
                        "id": 102,
                        "created_at": newer_created_at,
                        "event": "workflow_dispatch",
                    },
                ],
            ],
            run_details={
                102: {"id": 102, "status": "completed", "conclusion": "success"},
            },
        )

        completed_run = probe._wait_for_post_dispatch_workflow_completion(
            "ai-teammate/trackstate-setup",
            runs_before_dispatch={100},
            dispatch_started_at=dispatch_started_at - 5,
        )

        self.assertEqual(completed_run["id"], 102)
        self.assertEqual(completed_run["conclusion"], "success")

    def test_times_out_when_only_cancelled_post_dispatch_run_exists(self) -> None:
        probe = _RunSelectionProbe(
            workflow_runs_by_poll=[
                [
                    {
                        "id": 201,
                        "created_at": "2030-01-01T00:00:30Z",
                        "event": "workflow_dispatch",
                    }
                ]
            ],
            run_details={
                201: {"id": 201, "status": "completed", "conclusion": "cancelled"},
            },
            run_timeout_seconds=1,
        )

        with self.assertRaisesRegex(
            GitHubCliError,
            "never reached a non-cancelled completed state",
        ):
            probe._wait_for_post_dispatch_workflow_completion(
                "ai-teammate/trackstate-setup",
                runs_before_dispatch=set(),
                dispatch_started_at=time.time() - 5,
            )


if __name__ == "__main__":
    unittest.main()
