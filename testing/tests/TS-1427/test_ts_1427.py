from __future__ import annotations

import subprocess
import unittest
from unittest.mock import MagicMock, patch

from testing.frameworks.python.gh_cli_rate_limit import run_with_rate_limit_retry


class RateLimitExhaustionDiagnosticTest(unittest.TestCase):
    """Verify that exhausted rate-limit retries surface a clear, actionable diagnostic."""

    def _make_completed(
        self,
        *,
        returncode: int,
        stdout: str = "",
        stderr: str = "",
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=["gh", "api", "repos/IstiN/trackstate-setup/readme"],
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
        )

    @patch("testing.frameworks.python.gh_cli_rate_limit.time.sleep")
    def test_final_error_contains_rate_limit_indicator(self, sleep_mock: MagicMock) -> None:
        """After all retries are exhausted, the returned stderr still identifies rate limiting."""
        rate_limit_stderr = (
            "HTTP 403: API rate limit exceeded for IP address 203.0.113.4\n"
            "documentation_url: https://docs.github.com/rest/overview/rate-limits-for-the-rest-api"
        )

        def _run_once() -> subprocess.CompletedProcess[str]:
            return self._make_completed(returncode=1, stderr=rate_limit_stderr)

        completed = run_with_rate_limit_retry(_run_once)

        self.assertEqual(completed.returncode, 1)
        self.assertIn("rate limit", completed.stderr.lower())
        self.assertIn("403", completed.stderr)
        self.assertGreater(sleep_mock.call_count, 0)

    @patch("testing.frameworks.python.gh_cli_rate_limit.time.sleep")
    def test_final_error_persists_through_exponential_backoff(self, sleep_mock: MagicMock) -> None:
        """The diagnostic is preserved even when the helper performs multiple backoff sleeps."""
        rate_limit_stderr = "HTTP 403: you have triggered an abuse detection mechanism"

        def _run_once() -> subprocess.CompletedProcess[str]:
            return self._make_completed(returncode=1, stderr=rate_limit_stderr)

        completed = run_with_rate_limit_retry(_run_once)

        self.assertEqual(completed.returncode, 1)
        self.assertIn("abuse detection", completed.stderr.lower())
        self.assertIn("403", completed.stderr)

    @patch("testing.frameworks.python.gh_cli_rate_limit.time.sleep")
    def test_final_error_distinguishes_rate_limit_from_other_failures(self, sleep_mock: MagicMock) -> None:
        """A non-rate-limit error is returned untouched and does not look like rate-limit exhaustion."""
        auth_stderr = "HTTP 401: Bad credentials"

        def _run_once() -> subprocess.CompletedProcess[str]:
            return self._make_completed(returncode=1, stderr=auth_stderr)

        completed = run_with_rate_limit_retry(_run_once)

        self.assertEqual(completed.returncode, 1)
        self.assertIn("401", completed.stderr)
        self.assertNotIn("rate limit", completed.stderr.lower())
        self.assertEqual(sleep_mock.call_count, 0)


if __name__ == "__main__":
    unittest.main()
