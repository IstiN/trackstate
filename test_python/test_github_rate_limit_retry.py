from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path
from unittest import mock

from testing.core.interfaces.github_api_client import GitHubApiClientError
from testing.frameworks.python.gh_cli_api_client import GhCliApiClient
from testing.frameworks.python.github_cli_project_framework import (
    GitHubCliProjectFramework,
)


class _RateLimitThenSuccess:
    """Fake subprocess result sequence: rate-limit failures then a success."""

    def __init__(
        self,
        success_stdout: str,
        *,
        failures_before_success: int,
        status_code: int = 403,
    ) -> None:
        self._success_stdout = success_stdout
        self._failures_before_success = failures_before_success
        self._status_code = status_code
        self._call_count = 0

    def __call__(self, *args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        self._call_count += 1
        if self._call_count <= self._failures_before_success:
            return subprocess.CompletedProcess(
                args=args,
                returncode=1,
                stdout="",
                stderr=(
                    f"gh api repos/test/repo failed with HTTP {self._status_code}.\n"
                    "API rate limit exceeded. Please wait a few minutes before "
                    "you try again.\n"
                ),
            )
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout=self._success_stdout,
            stderr="",
        )


class GhCliApiClientRateLimitRetryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = GhCliApiClient(Path("/tmp"))

    @mock.patch("testing.frameworks.python.gh_cli_api_client.subprocess.run")
    @mock.patch("time.sleep", autospec=True)
    def test_retries_rate_limited_request_and_returns_success(
        self,
        mock_sleep: mock.Mock,
        mock_run: mock.Mock,
    ) -> None:
        expected_payload = {"ok": True}
        fake_runner = _RateLimitThenSuccess(
            json.dumps(expected_payload),
            failures_before_success=2,
        )
        mock_run.side_effect = fake_runner

        result = self.client.request_text(
            endpoint="repos/test/repo",
            method="GET",
        )

        self.assertEqual(json.loads(result), expected_payload)
        self.assertEqual(mock_run.call_count, 3)
        self.assertGreater(len(mock_sleep.call_args_list), 0)

    @mock.patch("testing.frameworks.python.gh_cli_api_client.subprocess.run")
    @mock.patch("time.sleep", autospec=True)
    def test_raises_after_exhausting_retries(
        self,
        mock_sleep: mock.Mock,
        mock_run: mock.Mock,
    ) -> None:
        fake_runner = _RateLimitThenSuccess(
            "{}",
            failures_before_success=10,
        )
        mock_run.side_effect = fake_runner

        with self.assertRaises(GitHubApiClientError) as cm:
            self.client.request_text(endpoint="repos/test/repo")

        self.assertIn("rate limit", str(cm.exception).lower())
        self.assertEqual(mock_run.call_count, 5)

    @mock.patch("testing.frameworks.python.gh_cli_api_client.subprocess.run")
    @mock.patch("time.sleep", autospec=True)
    def test_non_rate_limit_failure_raises_immediately(
        self,
        mock_sleep: mock.Mock,
        mock_run: mock.Mock,
    ) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=(),
            returncode=1,
            stdout="",
            stderr="gh api repos/test/repo failed with HTTP 404: Not Found",
        )

        with self.assertRaises(GitHubApiClientError) as cm:
            self.client.request_text(endpoint="repos/test/repo")

        self.assertIn("404", str(cm.exception))
        self.assertEqual(mock_run.call_count, 1)
        mock_sleep.assert_not_called()

    @mock.patch("testing.frameworks.python.gh_cli_api_client.subprocess.run")
    @mock.patch("time.sleep", autospec=True)
    def test_permission_403_without_rate_limit_phrase_raises_immediately(
        self,
        mock_sleep: mock.Mock,
        mock_run: mock.Mock,
    ) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=(),
            returncode=1,
            stdout="",
            stderr=(
                "gh api repos/test/repo failed with HTTP 403: "
                "Resource not accessible by integration"
            ),
        )

        with self.assertRaises(GitHubApiClientError) as cm:
            self.client.request_text(endpoint="repos/test/repo")

        self.assertIn("403", str(cm.exception))
        self.assertEqual(mock_run.call_count, 1)
        mock_sleep.assert_not_called()


class GitHubCliProjectFrameworkRateLimitRetryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.framework = GitHubCliProjectFramework(Path("/tmp"))

    @mock.patch(
        "testing.frameworks.python.github_cli_project_framework.subprocess.run"
    )
    @mock.patch(
        "time.sleep",
        autospec=True,
    )
    def test_retries_rate_limited_repository_metadata(
        self,
        mock_sleep: mock.Mock,
        mock_run: mock.Mock,
    ) -> None:
        expected_payload = {"default_branch": "main", "full_name": "owner/repo"}
        fake_runner = _RateLimitThenSuccess(
            json.dumps(expected_payload),
            failures_before_success=1,
        )
        mock_run.side_effect = fake_runner

        result = self.framework.repository_metadata("owner/repo")

        self.assertTrue(result.succeeded)
        self.assertEqual(result.json_payload, expected_payload)
        self.assertEqual(mock_run.call_count, 2)

    @mock.patch(
        "testing.frameworks.python.github_cli_project_framework.subprocess.run"
    )
    @mock.patch(
        "time.sleep",
        autospec=True,
    )
    def test_returns_failure_after_exhausting_retries(
        self,
        mock_sleep: mock.Mock,
        mock_run: mock.Mock,
    ) -> None:
        fake_runner = _RateLimitThenSuccess(
            "{}",
            failures_before_success=10,
        )
        mock_run.side_effect = fake_runner

        result = self.framework.viewer_login()

        self.assertFalse(result.succeeded)
        self.assertIn("rate limit", result.stderr.lower())
        self.assertEqual(mock_run.call_count, 5)

    @mock.patch(
        "testing.frameworks.python.github_cli_project_framework.subprocess.run"
    )
    @mock.patch(
        "time.sleep",
        autospec=True,
    )
    def test_non_rate_limit_failure_returns_immediately(
        self,
        mock_sleep: mock.Mock,
        mock_run: mock.Mock,
    ) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=(),
            returncode=1,
            stdout="",
            stderr="gh api user failed with HTTP 404: Not Found",
        )

        result = self.framework.viewer_login()

        self.assertFalse(result.succeeded)
        self.assertIn("404", result.stderr)
        self.assertEqual(mock_run.call_count, 1)
        mock_sleep.assert_not_called()

    @mock.patch(
        "testing.frameworks.python.github_cli_project_framework.subprocess.run"
    )
    @mock.patch(
        "time.sleep",
        autospec=True,
    )
    def test_permission_403_without_rate_limit_phrase_returns_immediately(
        self,
        mock_sleep: mock.Mock,
        mock_run: mock.Mock,
    ) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=(),
            returncode=1,
            stdout="",
            stderr=(
                "gh api user failed with HTTP 403: "
                "Resource not accessible by integration"
            ),
        )

        result = self.framework.viewer_login()

        self.assertFalse(result.succeeded)
        self.assertIn("403", result.stderr)
        self.assertEqual(mock_run.call_count, 1)
        mock_sleep.assert_not_called()


if __name__ == "__main__":
    unittest.main()
