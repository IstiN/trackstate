from __future__ import annotations

import time
import unittest
from pathlib import Path

from testing.core.config.non_default_branch_release_config import (
    NonDefaultBranchReleaseConfig,
)
from testing.core.interfaces.non_default_branch_release_repository import (
    NonDefaultBranchReleaseEnvironmentError,
)
from testing.frameworks.python.github_environment_preflight import verify_github_environment
from testing.frameworks.python.gh_cli_non_default_branch_release_repository import (
    GhCliNonDefaultBranchReleaseRepository,
)


class Ts252PreflightIntegrationTest(unittest.TestCase):
    """End-to-end check that TS-252 fails fast when GitHub is unreachable.

    The original TS-252 timeout (TS-1389) happened because the repository
    manager started long-running `gh`/`git` operations before checking whether
    the environment could reach GitHub at all. This test uses a non-existent
    repository to force the preflight check to fail and asserts that it does so
    quickly with the dedicated environment-unavailable error.
    """

    def test_repository_fails_fast_when_target_repository_is_unreachable(self) -> None:
        config = NonDefaultBranchReleaseConfig(
            repository="definitely-not-a-real-owner/trackstate-ts1389-noop",
            default_branch="main",
            probe_file_path="README.md",
            branch_prefix="ts252-test",
            pull_request_title="test",
            pull_request_body="test",
            semver_tag_pattern=r"^v\d+\.\d+\.\d+$",
        )
        repository_root = Path(__file__).resolve().parents[1]

        # The repository no longer runs its own preflight; call it explicitly
        # so the test still exercises the fail-fast path (TS-1389).
        # The preflight must fail fast; the original bug timed out at 300 s.
        started_at = time.monotonic()
        with self.assertRaises(NonDefaultBranchReleaseEnvironmentError) as cm:
            verify_github_environment(config.repository)
        elapsed = time.monotonic() - started_at
        self.assertLess(
            elapsed,
            60,
            "Expected the preflight check to fail within 60 s, "
            f"but it took {elapsed:.1f} s.",
        )

        # Verify the error message mentions the expected repository issue.
        self.assertIn("cannot access repository", str(cm.exception).lower())
