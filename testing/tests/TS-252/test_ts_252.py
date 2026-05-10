from __future__ import annotations

import json
import os
from pathlib import Path
import unittest

from testing.core.config.non_default_branch_release_config import (
    NonDefaultBranchReleaseConfig,
)
from testing.core.interfaces.non_default_branch_release_probe import (
    NonDefaultBranchReleaseProbe,
)
from testing.tests.support.non_default_branch_release_probe_factory import (
    create_non_default_branch_release_probe,
)


class PullRequestMergeToNonDefaultBranchDoesNotGenerateReleaseOrTagTest(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = NonDefaultBranchReleaseConfig.from_file(
            self.repository_root / "testing/tests/TS-252/config.yaml"
        )
        self.probe: NonDefaultBranchReleaseProbe = (
            create_non_default_branch_release_probe(self.repository_root)
        )

    def test_merge_to_non_default_branch_does_not_generate_release_or_semantic_tag(
        self,
    ) -> None:
        observation = self.probe.validate()
        self._write_result_if_requested(observation.to_dict())

        self.assertEqual(
            observation.repository,
            self.config.repository,
            "Step 1 failed: TS-252 targeted the wrong repository.\n"
            f"Expected repository: {self.config.repository}\n"
            f"Observed repository: {observation.repository}",
        )
        self.assertEqual(
            observation.default_branch,
            self.config.default_branch,
            "Step 1 failed: TS-252 targeted the wrong default branch.\n"
            f"Expected default branch: {self.config.default_branch}\n"
            f"Observed default branch: {observation.default_branch}",
        )
        self.assertNotEqual(
            observation.target_branch,
            observation.default_branch,
            "Step 1 failed: TS-252 did not create a non-default target branch.\n"
            f"Default branch: {observation.default_branch}\n"
            f"Observed target branch: {observation.target_branch}",
        )
        self.assertTrue(
            observation.target_branch_created_by_test,
            "Step 1 failed: TS-252 did not create its own disposable non-default "
            "target branch for the merge scenario.\n"
            f"Observed target branch: {observation.target_branch}",
        )
        self.assertTrue(
            observation.pull_request_number > 0,
            "Step 2 failed: TS-252 did not create a disposable pull request number.\n"
            f"Observed pull request URL: {observation.pull_request_url}",
        )
        self.assertIn(
            "/pull/",
            observation.pull_request_url,
            "Step 2 failed: TS-252 did not return a GitHub Pull Request URL.\n"
            f"Observed URL: {observation.pull_request_url}",
        )
        self.assertEqual(
            observation.pull_request_base_branch,
            observation.target_branch,
            "Step 2 failed: the disposable pull request did not target the disposable "
            "non-default branch.\n"
            f"Expected base branch: {observation.target_branch}\n"
            f"Observed base branch: {observation.pull_request_base_branch}",
        )
        self.assertNotEqual(
            observation.pull_request_head_branch,
            observation.target_branch,
            "Step 2 failed: TS-252 did not create a separate source branch for the "
            "pull request.\n"
            f"Target branch: {observation.target_branch}\n"
            f"Observed head branch: {observation.pull_request_head_branch}",
        )
        self.assertTrue(
            observation.pull_request_merge_commit_sha,
            "Step 3 failed: GitHub did not return merge commit metadata after the "
            "disposable pull request merge.\n"
            f"Pull Request URL: {observation.pull_request_url}",
        )
        self.assertIsNone(
            observation.unexpected_release_id,
            "Step 4 failed: merging into a non-default branch still produced a new "
            "GitHub release tied to the merged pull request commit.\n"
            f"Pull Request URL: {observation.pull_request_url}\n"
            f"Target branch: {observation.target_branch}\n"
            f"Merge commit: {observation.pull_request_merge_commit_sha}\n"
            f"Release ID: {observation.unexpected_release_id}\n"
            f"Release tag: {observation.unexpected_release_tag_name}\n"
            f"Release URL: {observation.unexpected_release_html_url}\n"
            f"Release tag commit: {observation.unexpected_release_tag_commit_sha}",
        )
        self.assertIsNone(
            observation.unexpected_tag_name,
            "Step 4 failed: merging into a non-default branch still produced a new "
            "semantic version tag tied to the merged pull request commit.\n"
            f"Pull Request URL: {observation.pull_request_url}\n"
            f"Target branch: {observation.target_branch}\n"
            f"Merge commit: {observation.pull_request_merge_commit_sha}\n"
            f"Observed tag: {observation.unexpected_tag_name}\n"
            f"Tag commit: {observation.unexpected_tag_commit_sha}",
        )
        self.assertGreaterEqual(
            observation.elapsed_quiet_period_seconds,
            self.config.quiet_period_seconds,
            "Step 4 failed: TS-252 did not wait through the configured quiet period "
            "before concluding no release or tag was created.\n"
            f"Configured quiet period: {self.config.quiet_period_seconds}s\n"
            f"Observed wait: {observation.elapsed_quiet_period_seconds}s",
        )
        self.assertTrue(
            observation.releases_page_has_heading,
            "Human-style verification failed: the Releases page did not visibly render "
            "the expected heading after the non-default-branch merge check.\n"
            f"URL: {observation.releases_page_url}",
        )
        self.assertTrue(
            observation.tags_page_has_heading,
            "Human-style verification failed: the Tags page did not visibly render the "
            "expected heading after the non-default-branch merge check.\n"
            f"URL: {observation.tags_page_url}",
        )
        self.assertFalse(
            observation.releases_page_contains_unexpected_tag,
            "Human-style verification failed: the Releases page visibly exposed an "
            "unexpected semantic release/tag after merging into the non-default branch.\n"
            f"URL: {observation.releases_page_url}\n"
            f"Unexpected tag: {observation.unexpected_tag_name or observation.unexpected_release_tag_name}",
        )
        self.assertFalse(
            observation.tags_page_contains_unexpected_tag,
            "Human-style verification failed: the Tags page visibly exposed an "
            "unexpected semantic tag after merging into the non-default branch.\n"
            f"URL: {observation.tags_page_url}\n"
            f"Unexpected tag: {observation.unexpected_tag_name or observation.unexpected_release_tag_name}",
        )

    def _write_result_if_requested(self, payload: dict[str, object]) -> None:
        result_path = os.environ.get("TS252_RESULT_PATH")
        if not result_path:
            return

        destination = Path(result_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    unittest.main()
