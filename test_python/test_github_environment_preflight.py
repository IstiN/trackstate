from __future__ import annotations

import subprocess
import unittest
from unittest import mock

from testing.core.interfaces.non_default_branch_release_repository import (
    NonDefaultBranchReleaseEnvironmentError,
)
from testing.frameworks.python.github_environment_preflight import (
    verify_github_environment,
)


class VerifyGitHubEnvironmentTest(unittest.TestCase):
    """Regression tests for the TS-252 environment preflight check.

    TS-252 previously hung for the full 300 s test timeout when live GitHub API
    access was unavailable. These tests verify that the preflight helper fails
    fast with a clear environment-unavailable error instead of attempting the
    long-running branch/PR/merge workflow.
    """

    def test_raises_environment_error_when_gh_is_missing(self) -> None:
        with mock.patch(
            "testing.frameworks.python.github_environment_preflight.shutil.which",
            return_value=None,
        ):
            with self.assertRaises(NonDefaultBranchReleaseEnvironmentError) as context:
                verify_github_environment("owner/repo", gh_executable="gh-missing")

        self.assertIn("not installed", str(context.exception).lower())

    @mock.patch(
        "testing.frameworks.python.github_environment_preflight.shutil.which",
        return_value="/usr/bin/gh",
    )
    def test_raises_environment_error_when_gh_auth_status_fails(
        self, _mock_which: mock.Mock
    ) -> None:
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["gh", "auth", "status"],
                returncode=1,
                stdout="",
                stderr="not logged into github.com",
            )

            with self.assertRaises(NonDefaultBranchReleaseEnvironmentError) as context:
                verify_github_environment("owner/repo")

        self.assertIn("not authenticated", str(context.exception).lower())

    @mock.patch(
        "testing.frameworks.python.github_environment_preflight.shutil.which",
        return_value="/usr/bin/gh",
    )
    def test_raises_environment_error_when_repository_api_fails(
        self, _mock_which: mock.Mock
    ) -> None:
        def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            if command[1] == "auth":
                return subprocess.CompletedProcess(
                    args=command,
                    returncode=0,
                    stdout="logged in to github.com",
                    stderr="",
                )
            return subprocess.CompletedProcess(
                args=command,
                returncode=404,
                stdout="",
                stderr="Not Found",
            )

        with mock.patch("subprocess.run", side_effect=fake_run):
            with self.assertRaises(NonDefaultBranchReleaseEnvironmentError) as context:
                verify_github_environment("owner/repo")

        self.assertIn("cannot access repository", str(context.exception).lower())

    @mock.patch(
        "testing.frameworks.python.github_environment_preflight.shutil.which",
        return_value="/usr/bin/gh",
    )
    def test_succeeds_when_auth_and_repository_access_pass(
        self, _mock_which: mock.Mock
    ) -> None:
        def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(
                args=command,
                returncode=0,
                stdout="ok",
                stderr="",
            )

        with mock.patch("subprocess.run", side_effect=fake_run):
            # Should not raise.
            verify_github_environment("owner/repo")

    @mock.patch(
        "testing.frameworks.python.github_environment_preflight.shutil.which",
        return_value="/usr/bin/gh",
    )
    def test_raises_environment_error_when_auth_command_times_out(
        self, _mock_which: mock.Mock
    ) -> None:
        with mock.patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(
                cmd=["gh", "auth", "status"],
                timeout=30,
                stderr="timed out",
            )

            with self.assertRaises(NonDefaultBranchReleaseEnvironmentError) as context:
                verify_github_environment("owner/repo")

        self.assertIn("timed out", str(context.exception).lower())


if __name__ == "__main__":
    unittest.main()
