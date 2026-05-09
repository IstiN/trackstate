from __future__ import annotations

import json
import os
from pathlib import Path
import re
import unittest

from testing.core.config.release_on_merge_config import ReleaseOnMergeConfig
from testing.core.interfaces.release_on_merge_probe import ReleaseOnMergeProbe
from testing.tests.support.release_on_merge_probe_factory import (
    create_release_on_merge_probe,
)


class PullRequestMergeGeneratesReleaseAndTagTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = ReleaseOnMergeConfig.from_file(
            self.repository_root / "testing/tests/TS-230/config.yaml"
        )
        self.probe: ReleaseOnMergeProbe = create_release_on_merge_probe(
            self.repository_root
        )

    def test_merge_to_default_branch_generates_release_and_semantic_tag(self) -> None:
        observation = self.probe.validate()
        self._write_result_if_requested(observation.to_dict())

        self.assertEqual(
            observation.repository,
            self.config.repository,
            "Step 1 failed: TS-230 targeted the wrong repository.\n"
            f"Expected repository: {self.config.repository}\n"
            f"Observed repository: {observation.repository}",
        )
        self.assertEqual(
            observation.default_branch,
            self.config.default_branch,
            "Step 1 failed: TS-230 targeted the wrong default branch.\n"
            f"Expected default branch: {self.config.default_branch}\n"
            f"Observed default branch: {observation.default_branch}",
        )
        self.assertTrue(
            observation.pull_request_number > 0,
            "Step 2 failed: TS-230 did not create a disposable pull request number.\n"
            f"Observed pull request URL: {observation.pull_request_url}",
        )
        self.assertIn(
            "/pull/",
            observation.pull_request_url,
            "Step 2 failed: TS-230 did not return a GitHub Pull Request URL.\n"
            f"Observed URL: {observation.pull_request_url}",
        )
        self.assertTrue(
            observation.pull_request_merge_commit_sha,
            "Step 3 failed: GitHub did not return merge commit metadata after the "
            "disposable pull request merge.\n"
            f"Pull Request URL: {observation.pull_request_url}",
        )
        self.assertTrue(
            observation.release_id > 0,
            "Step 4 failed: TS-230 did not observe a newly published GitHub release.\n"
            f"Pull Request URL: {observation.pull_request_url}\n"
            f"Observed release ID: {observation.release_id}",
        )
        self.assertTrue(
            observation.release_tag_name,
            "Step 4 failed: the observed release did not expose tag_name.\n"
            f"Release URL: {observation.release_html_url}",
        )
        self.assertTrue(
            observation.tag_name,
            "Step 4 failed: TS-230 did not observe a matching newly created tag.\n"
            f"Observed release tag: {observation.release_tag_name}",
        )
        self.assertEqual(
            observation.release_tag_name,
            observation.tag_name,
            "Step 4 failed: the observed release tag and Git tag do not match.\n"
            f"Release tag: {observation.release_tag_name}\n"
            f"Tag name: {observation.tag_name}",
        )
        self.assertIsNotNone(
            re.fullmatch(self.config.semver_tag_pattern, observation.tag_name),
            "Step 4 failed: the generated tag does not follow the expected semantic "
            "version format.\n"
            f"Pattern: {self.config.semver_tag_pattern}\n"
            f"Observed tag: {observation.tag_name}",
        )
        self.assertTrue(
            observation.releases_page_contains_tag,
            "Human-style verification failed: the Releases page did not visibly include "
            "the generated semantic version tag.\n"
            f"Releases page: {observation.releases_page_url}\n"
            f"Expected visible tag: {observation.tag_name}",
        )
        self.assertTrue(
            observation.tags_page_contains_tag,
            "Human-style verification failed: the Tags page did not visibly include "
            "the generated semantic version tag.\n"
            f"Tags page: {observation.tags_page_url}\n"
            f"Expected visible tag: {observation.tag_name}",
        )

    def _write_result_if_requested(self, payload: dict[str, object]) -> None:
        result_path = os.environ.get("TS230_RESULT_PATH")
        if not result_path:
            return

        destination = Path(result_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    unittest.main()
