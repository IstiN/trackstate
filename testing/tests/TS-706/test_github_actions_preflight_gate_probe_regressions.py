from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from testing.components.services.github_actions_preflight_gate_probe import (
    GitHubActionsPreflightGatePreconditionError,
    GitHubActionsPreflightGateProbeService,
)
from testing.core.config.github_actions_preflight_gate_config import (
    GitHubActionsPreflightGateConfig,
)
from testing.core.interfaces.github_actions_preflight_gate_probe import (
    GitHubActionsWorkflowRunObservation,
)


class _FakeGitHubApiClient:
    def __init__(self, responses: dict[tuple[str, str], list[object]]) -> None:
        self._responses = {
            key: list(value)
            for key, value in responses.items()
        }
        self.calls: list[tuple[str, str]] = []

    def request_text(
        self,
        *,
        endpoint: str,
        method: str = "GET",
        field_args=None,
        stdin_json=None,
    ) -> str:
        del field_args, stdin_json
        key = (method, endpoint)
        self.calls.append(key)
        queue = self._responses.get(key)
        if not queue:
            raise AssertionError(f"Unexpected GitHub API request: {key}")
        response = queue.pop(0)
        if isinstance(response, Exception):
            raise response
        if isinstance(response, str):
            return response
        return json.dumps(response)


class _UnusedWorkflowRunLogReader:
    def read_run_log(self, run_id: int) -> str:
        raise AssertionError(f"Log reader should not be used for run {run_id}")


class _FakeWorkflowRunLogReader:
    def __init__(self, log_text: str) -> None:
        self._log_text = log_text

    def read_run_log(self, run_id: int) -> str:
        del run_id
        return self._log_text


class _FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


class GitHubActionsPreflightGateProbeRegressionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = GitHubActionsPreflightGateConfig(
            repository="IstiN/trackstate",
            default_branch="main",
            workflow_name="Apple Release Builds",
            workflow_file="build-native.yml",
            workflow_path=".github/workflows/build-native.yml",
            preflight_job_name="Verify macOS runner availability",
            downstream_job_name="Build macOS desktop and CLI artifacts",
            expected_preflight_runner="ubuntu-latest",
            expected_runner_labels=[
                "self-hosted",
                "macOS",
                "trackstate-release",
                "ARM64",
            ],
            expected_failure_markers=["No runner registered for", "none are online"],
            recent_runs_limit=20,
            poll_interval_seconds=1,
            run_timeout_seconds=5,
            ui_timeout_seconds=60,
        )
        self.workflow_yaml = """
env:
  required_runner_labels: self-hosted,macOS,trackstate-release,ARM64
jobs:
  verify_runner:
    name: Verify macOS runner availability
    runs-on: ubuntu-latest
  build_release:
    name: Build macOS desktop and CLI artifacts
    runs-on:
      - self-hosted
      - macOS
      - trackstate-release
      - ARM64
""".strip()

    def test_validate_uses_live_workflow_signal_without_runner_inventory_api(self) -> None:
        completed_run = GitHubActionsWorkflowRunObservation(
            id=91,
            event="push",
            head_branch="main",
            head_sha="head-sha",
            status="completed",
            conclusion="failure",
            html_url="https://github.com/IstiN/trackstate/actions/runs/91",
            created_at="2026-05-14T18:37:30Z",
            display_title="TS-706",
        )
        github_api_client = _FakeGitHubApiClient(
            {
                ("GET", "/repos/IstiN/trackstate"): [
                    {"default_branch": "main"},
                ],
                (
                    "GET",
                    "/repos/IstiN/trackstate/actions/workflows/build-native.yml",
                ): [
                    {
                        "html_url": "https://github.com/IstiN/trackstate/actions/workflows/build-native.yml",
                        "state": "active",
                        "path": ".github/workflows/build-native.yml",
                    }
                ],
                (
                    "GET",
                    "/repos/IstiN/trackstate/contents/.github/workflows/build-native.yml?ref=main",
                ): [self.workflow_yaml],
                ("GET", "/repos/IstiN/trackstate/branches/main"): [
                    {"commit": {"sha": "head-sha"}}
                ],
                (
                    "GET",
                    "/repos/IstiN/trackstate/actions/workflows/build-native.yml/runs?event=push&per_page=50",
                ): [{"workflow_runs": []}],
                ("POST", "/repos/IstiN/trackstate/git/refs"): [""],
                ("GET", "/repos/IstiN/trackstate/actions/runs/91/jobs?per_page=20"): [
                    {
                        "jobs": [
                            {
                                "id": 101,
                                "name": "Verify macOS runner availability",
                                "status": "completed",
                                "conclusion": "failure",
                                "html_url": "https://github.com/IstiN/trackstate/actions/runs/91/job/101",
                            },
                            {
                                "id": 202,
                                "name": "Build macOS desktop and CLI artifacts",
                                "status": "completed",
                                "conclusion": "skipped",
                                "html_url": "https://github.com/IstiN/trackstate/actions/runs/91/job/202",
                            },
                        ]
                    }
                ],
                ("DELETE", "/repos/IstiN/trackstate/git/refs/tags/v98.test"): [""],
            }
        )
        probe = GitHubActionsPreflightGateProbeService(
            self.config,
            github_api_client=github_api_client,
            workflow_run_log_reader=_FakeWorkflowRunLogReader(
                "No runner registered for IstiN/trackstate"
            ),
        )
        probe._build_tag_name = lambda: "v98.test"  # type: ignore[method-assign]
        probe._wait_for_new_push_run = lambda **_: completed_run  # type: ignore[method-assign]
        probe._wait_for_completed_run = lambda _run_id: completed_run  # type: ignore[method-assign]

        observation = probe.validate()

        self.assertEqual(observation.matching_runners, [])
        self.assertNotIn(
            ("GET", "/repos/IstiN/trackstate/actions/runners?per_page=100"),
            github_api_client.calls,
        )
        self.assertIn(("POST", "/repos/IstiN/trackstate/git/refs"), github_api_client.calls)

    def test_validate_waits_for_settled_runner_mismatch_before_raising(self) -> None:
        config = GitHubActionsPreflightGateConfig(
            repository=self.config.repository,
            default_branch=self.config.default_branch,
            workflow_name=self.config.workflow_name,
            workflow_file=self.config.workflow_file,
            workflow_path=self.config.workflow_path,
            preflight_job_name=self.config.preflight_job_name,
            downstream_job_name=self.config.downstream_job_name,
            expected_preflight_runner=self.config.expected_preflight_runner,
            expected_runner_labels=list(self.config.expected_runner_labels),
            expected_failure_markers=list(self.config.expected_failure_markers),
            recent_runs_limit=self.config.recent_runs_limit,
            poll_interval_seconds=1,
            run_timeout_seconds=2,
            ui_timeout_seconds=self.config.ui_timeout_seconds,
        )
        github_api_client = _FakeGitHubApiClient(
            {
                ("GET", "/repos/IstiN/trackstate"): [
                    {"default_branch": "main"},
                ],
                (
                    "GET",
                    "/repos/IstiN/trackstate/actions/workflows/build-native.yml",
                ): [
                    {
                        "html_url": "https://github.com/IstiN/trackstate/actions/workflows/build-native.yml",
                        "state": "active",
                        "path": ".github/workflows/build-native.yml",
                    }
                ],
                (
                    "GET",
                    "/repos/IstiN/trackstate/contents/.github/workflows/build-native.yml?ref=main",
                ): [self.workflow_yaml],
                ("GET", "/repos/IstiN/trackstate/branches/main"): [
                    {"commit": {"sha": "head-sha"}}
                ],
                (
                    "GET",
                    "/repos/IstiN/trackstate/actions/workflows/build-native.yml/runs?event=push&per_page=50",
                ): [{"workflow_runs": []}],
                ("POST", "/repos/IstiN/trackstate/git/refs"): [""],
                ("GET", "/repos/IstiN/trackstate/actions/runs/91"): [
                    {
                        "id": 91,
                        "event": "push",
                        "head_branch": "main",
                        "head_sha": "head-sha",
                        "status": "in_progress",
                        "conclusion": None,
                        "html_url": "https://github.com/IstiN/trackstate/actions/runs/91",
                        "created_at": "2026-05-14T18:37:30Z",
                        "display_title": "TS-706",
                    },
                    {
                        "id": 91,
                        "event": "push",
                        "head_branch": "main",
                        "head_sha": "head-sha",
                        "status": "in_progress",
                        "conclusion": None,
                        "html_url": "https://github.com/IstiN/trackstate/actions/runs/91",
                        "created_at": "2026-05-14T18:37:30Z",
                        "display_title": "TS-706",
                    }
                ],
                ("GET", "/repos/IstiN/trackstate/actions/runs/91/jobs?per_page=20"): [
                    {
                        "jobs": [
                            {
                                "id": 101,
                                "name": "Verify macOS runner availability",
                                "status": "completed",
                                "conclusion": "success",
                                "html_url": "https://github.com/IstiN/trackstate/actions/runs/91/job/101",
                            },
                            {
                                "id": 202,
                                "name": "Build macOS desktop and CLI artifacts",
                                "status": "queued",
                                "conclusion": None,
                                "html_url": "https://github.com/IstiN/trackstate/actions/runs/91/job/202",
                            },
                        ]
                    },
                    {
                        "jobs": [
                            {
                                "id": 101,
                                "name": "Verify macOS runner availability",
                                "status": "completed",
                                "conclusion": "success",
                                "html_url": "https://github.com/IstiN/trackstate/actions/runs/91/job/101",
                            },
                            {
                                "id": 202,
                                "name": "Build macOS desktop and CLI artifacts",
                                "status": "queued",
                                "conclusion": None,
                                "html_url": "https://github.com/IstiN/trackstate/actions/runs/91/job/202",
                            },
                        ]
                    }
                ],
                ("DELETE", "/repos/IstiN/trackstate/git/refs/tags/v98.test"): [""],
            }
        )

        probe = GitHubActionsPreflightGateProbeService(
            config,
            github_api_client=github_api_client,
            workflow_run_log_reader=_UnusedWorkflowRunLogReader(),
        )
        probe._build_tag_name = lambda: "v98.test"  # type: ignore[method-assign]
        probe._wait_for_new_push_run = lambda **_: GitHubActionsWorkflowRunObservation(  # type: ignore[method-assign]
            id=91,
            event="push",
            head_branch="main",
            head_sha="head-sha",
            status="in_progress",
            conclusion=None,
            html_url="https://github.com/IstiN/trackstate/actions/runs/91",
            created_at="2026-05-14T18:37:30Z",
            display_title="TS-706",
        )
        clock = _FakeClock()

        with (
            patch(
                "testing.components.services.github_actions_preflight_gate_probe.time.time",
                side_effect=clock.time,
            ),
            patch(
                "testing.components.services.github_actions_preflight_gate_probe.time.sleep",
                side_effect=clock.sleep,
            ),
            self.assertRaisesRegex(
                GitHubActionsPreflightGatePreconditionError,
                "kept waiting for a runner for at least 2 seconds",
            ) as raised,
        ):
            probe.validate()

        self.assertNotIn(
            ("GET", "/repos/IstiN/trackstate/actions/runners?per_page=100"),
            github_api_client.calls,
        )
        self.assertEqual(
            github_api_client.calls.count(("GET", "/repos/IstiN/trackstate/actions/runs/91")),
            2,
        )
        self.assertEqual(
            raised.exception.partial_result.get("tag_name"),
            "v98.test",
        )
        self.assertTrue(raised.exception.partial_result.get("stable_runner_mismatch"))
        self.assertEqual(
            raised.exception.partial_result.get("run", {}).get("html_url"),
            "https://github.com/IstiN/trackstate/actions/runs/91",
        )
        self.assertEqual(
            raised.exception.partial_result.get("preflight_job", {}).get("html_url"),
            "https://github.com/IstiN/trackstate/actions/runs/91/job/101",
        )
        self.assertEqual(
            raised.exception.partial_result.get("downstream_job", {}).get("html_url"),
            "https://github.com/IstiN/trackstate/actions/runs/91/job/202",
        )


if __name__ == "__main__":
    unittest.main()
