from __future__ import annotations

import subprocess
import unittest
from unittest.mock import MagicMock, patch

from testing.frameworks.python.gh_cli_rate_limit import (
    MAX_RATE_LIMIT_RETRIES,
    run_with_rate_limit_retry,
)


class GitHubApiRateLimitResilienceTest(unittest.TestCase):
    """Verify that the CI harness retry helper handles GitHub rate-limit responses."""

    def _make_completed(
        self,
        *,
        returncode: int,
        stdout: str = "",
        stderr: str = "",
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=["gh", "api", "repos/test/repo"],
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
        )

    @patch("testing.frameworks.python.gh_cli_rate_limit.time.sleep")
    def test_retries_on_rate_limit_and_succeeds(self, sleep_mock: MagicMock) -> None:
        """A transient 403 rate-limit response is retried and the eventual success is returned."""
        attempts = [
            self._make_completed(
                returncode=1,
                stderr="HTTP 403: API rate limit exceeded for user ID 12345.",
            ),
            self._make_completed(
                returncode=1,
                stderr="HTTP 403: you have exceeded a secondary rate limit.",
            ),
            self._make_completed(returncode=0, stdout='{"id": 42}'),
        ]
        call_count = 0

        def _run_once() -> subprocess.CompletedProcess[str]:
            nonlocal call_count
            result = attempts[call_count]
            call_count += 1
            return result

        completed = run_with_rate_limit_retry(_run_once)

        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stdout, '{"id": 42}')
        self.assertEqual(call_count, 3)
        self.assertGreaterEqual(sleep_mock.call_count, 2)

    @patch("testing.frameworks.python.gh_cli_rate_limit.time.sleep")
    def test_gives_up_after_max_retries(self, sleep_mock: MagicMock) -> None:
        """When every attempt is rate-limited, the helper returns the final failure."""
        rate_limit_stderr = (
            "HTTP 403: API rate limit exceeded\n"
            "Retry-After: 0\n"
            "documentation_url: https://docs.github.com/rest/overview/rate-limits-for-the-rest-api"
        )

        def _run_once() -> subprocess.CompletedProcess[str]:
            return self._make_completed(
                returncode=1,
                stderr=rate_limit_stderr,
            )

        completed = run_with_rate_limit_retry(_run_once)

        self.assertEqual(completed.returncode, 1)
        self.assertIn("rate limit", completed.stderr.lower())
        self.assertEqual(sleep_mock.call_count, MAX_RATE_LIMIT_RETRIES)

    @patch("testing.frameworks.python.gh_cli_rate_limit.time.sleep")
    def test_does_not_retry_non_rate_limit_errors(self, sleep_mock: MagicMock) -> None:
        """A 404 or authentication error is returned immediately without retrying."""

        def _run_once() -> subprocess.CompletedProcess[str]:
            return self._make_completed(
                returncode=1,
                stderr="HTTP 404: Not Found",
            )

        completed = run_with_rate_limit_retry(_run_once)

        self.assertEqual(completed.returncode, 1)
        self.assertEqual(sleep_mock.call_count, 0)

    @patch("testing.frameworks.python.gh_cli_rate_limit.time.sleep")
    def test_respects_retry_after_header(self, sleep_mock: MagicMock) -> None:
        """When GitHub provides Retry-After, the helper sleeps for exactly that many seconds."""
        attempts = [
            self._make_completed(
                returncode=1,
                stderr="HTTP 403: rate limit exceeded\nRetry-After: 7",
            ),
            self._make_completed(returncode=0, stdout="ok"),
        ]
        call_count = 0

        def _run_once() -> subprocess.CompletedProcess[str]:
            nonlocal call_count
            result = attempts[call_count]
            call_count += 1
            return result

        completed = run_with_rate_limit_retry(_run_once)

        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stdout, "ok")
        sleep_mock.assert_called_once_with(7.0)


if __name__ == "__main__":
    unittest.main()
