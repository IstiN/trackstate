from __future__ import annotations

import json
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from testing.components.services.non_default_branch_release_probe import (
    NonDefaultBranchReleaseProbeService,
)
from testing.core.config.non_default_branch_release_config import (
    NonDefaultBranchReleaseConfig,
)
from testing.core.interfaces.github_api_client import GitHubApiClient
from testing.core.interfaces.non_default_branch_release_repository import (
    NonDefaultBranchMergedPullRequest,
    NonDefaultBranchReleaseEnvironmentError,
    NonDefaultBranchReleaseRepository,
)
from testing.core.interfaces.url_text_reader import UrlTextReader


class _FakeGitHubApiClient(GitHubApiClient):
    def __init__(self, repository: str, default_branch: str = "main") -> None:
        self._repository = repository
        self._default_branch = default_branch
        self.requests: list[tuple[str, str]] = []

    def request_text(
        self,
        *,
        endpoint: str,
        method: str = "GET",
        field_args=None,
        stdin_json=None,
    ) -> str:
        del field_args, stdin_json
        self.requests.append((endpoint, method))
        if endpoint == f"/repos/{self._repository}":
            return json.dumps({"default_branch": self._default_branch})
        if endpoint.startswith(f"/repos/{self._repository}/releases?"):
            return json.dumps([])
        if endpoint.startswith(f"/repos/{self._repository}/tags?"):
            return json.dumps([])
        raise RuntimeError(f"Unexpected fake API call: {method} {endpoint}")


class _FakeUrlTextReader(UrlTextReader):
    def __init__(self, html: str = "") -> None:
        self._html = html
        self.requests: list[str] = []

    def read_text(
        self,
        *,
        url: str,
        headers: dict[str, str],
        timeout_seconds: int,
    ) -> str:
        del headers, timeout_seconds
        self.requests.append(url)
        return self._html


class _FakeNonDefaultBranchReleaseRepository(NonDefaultBranchReleaseRepository):
    def __init__(self, merge_commit_sha: str = "abc123def456") -> None:
        self._merge_commit_sha = merge_commit_sha
        self.cleaned_up = False

    def create_and_merge_pull_request(
        self,
        *,
        config: NonDefaultBranchReleaseConfig,
        default_branch: str,
    ) -> NonDefaultBranchMergedPullRequest:
        del config
        return NonDefaultBranchMergedPullRequest(
            number=42,
            url="https://github.com/test-owner/test-repo/pull/42",
            head_branch="ts252-regression-pr-branch",
            base_branch="ts252-regression-base-branch",
            merged_at="2030-01-01T00:00:00Z",
            merge_commit_sha=self._merge_commit_sha,
            target_branch_created_by_test=True,
            temp_repository_root=Path("/tmp/fake-ts252-repo"),
            source_branch_pushed=True,
            target_branch_pushed=True,
        )

    def cleanup_disposable_environment(
        self,
        merged_pull_request: NonDefaultBranchMergedPullRequest,
    ) -> None:
        del merged_pull_request
        self.cleaned_up = True


def _build_config(**overrides: object) -> NonDefaultBranchReleaseConfig:
    defaults = {
        "repository": "test-owner/test-repo",
        "default_branch": "main",
        "probe_file_path": "README.md",
        "branch_prefix": "ts252-regression",
        "pull_request_title": "TS-252 regression probe",
        "pull_request_body": "TS-252 regression probe body",
        "semver_tag_pattern": r"^v\d+\.\d+\.\d+$",
        "quiet_period_seconds": 1,
        "poll_interval_seconds": 0,
        "pull_request_timeout_seconds": 1,
        "releases_lookup_limit": 10,
        "tags_lookup_limit": 10,
    }
    defaults.update(overrides)
    return NonDefaultBranchReleaseConfig(**defaults)  # type: ignore[arg-type]


class NonDefaultBranchReleaseFailFastRegressionTest(unittest.TestCase):
    """Regression coverage for TS-1389 / TS-252.

    The original TS-252 live test hung for the full 300 s outer timeout when the
    GitHub environment was unreachable because it started long-running branch/PR/merge
    operations without a bounded preflight check. These tests verify:

    1. The probe fails fast with a dedicated environment-unavailable error instead
       of hanging.
    2. The business logic correctly reports that merging into a non-default branch
       produced no release and no semantic version tag.
    """

    def test_fails_fast_when_github_environment_is_unreachable(self) -> None:
        probe = NonDefaultBranchReleaseProbeService(
            _build_config(),
            github_api_client=_FakeGitHubApiClient("test-owner/test-repo"),
            repository_manager=_FakeNonDefaultBranchReleaseRepository(),
            url_text_reader=_FakeUrlTextReader(),
        )

        error_message = "Live GitHub API interactions are unavailable"
        with patch(
            "testing.components.services.non_default_branch_release_probe.verify_github_environment",
            side_effect=NonDefaultBranchReleaseEnvironmentError(error_message),
        ):
            started_at = time.monotonic()
            with self.assertRaises(NonDefaultBranchReleaseEnvironmentError) as context:
                probe.validate()
            elapsed = time.monotonic() - started_at

        self.assertLess(elapsed, 5, "Fail-fast took too long")
        self.assertIn("unavailable", str(context.exception).lower())

    def test_non_default_branch_merge_produces_no_release_or_tag(self) -> None:
        repository = "test-owner/test-repo"
        default_branch = "main"
        fake_api = _FakeGitHubApiClient(repository, default_branch)
        fake_repository = _FakeNonDefaultBranchReleaseRepository(
            merge_commit_sha="abc123def456"
        )
        fake_reader = _FakeUrlTextReader(
            html=(
                "<html><body>"
                "<h1>Releases</h1><p>No releases</p>"
                "<h1>Tags</h1><p>No tags</p>"
                "</body></html>"
            )
        )
        probe = NonDefaultBranchReleaseProbeService(
            _build_config(
                repository=repository,
                default_branch=default_branch,
                quiet_period_seconds=1,
                poll_interval_seconds=0,
            ),
            github_api_client=fake_api,
            repository_manager=fake_repository,
            url_text_reader=fake_reader,
        )

        with patch(
            "testing.components.services.non_default_branch_release_probe.verify_github_environment"
        ):
            observation = probe.validate()

        self.assertTrue(fake_repository.cleaned_up)
        self.assertEqual(observation.repository, repository)
        self.assertEqual(observation.default_branch, default_branch)
        self.assertNotEqual(observation.target_branch, observation.default_branch)
        self.assertTrue(observation.target_branch_created_by_test)
        self.assertEqual(observation.pull_request_number, 42)
        self.assertIn("/pull/42", observation.pull_request_url)
        self.assertEqual(observation.pull_request_base_branch, observation.target_branch)
        self.assertNotEqual(
            observation.pull_request_head_branch, observation.target_branch
        )
        self.assertTrue(observation.pull_request_merge_commit_sha)
        self.assertIsNone(
            observation.unexpected_release_id,
            "Merging into a non-default branch must not produce a GitHub release.",
        )
        self.assertIsNone(
            observation.unexpected_tag_name,
            "Merging into a non-default branch must not produce a semantic version tag.",
        )
        self.assertGreaterEqual(
            observation.elapsed_quiet_period_seconds,
            1,
            "The probe must wait through the configured quiet period.",
        )
        self.assertTrue(observation.releases_page_has_heading)
        self.assertTrue(observation.tags_page_has_heading)
        self.assertFalse(observation.releases_page_contains_unexpected_tag)
        self.assertFalse(observation.tags_page_contains_unexpected_tag)


if __name__ == "__main__":
    unittest.main()
