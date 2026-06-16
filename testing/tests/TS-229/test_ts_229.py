from __future__ import annotations

import json
import os
from pathlib import Path
import unittest

from testing.core.config.repository_release_tags_config import (
    RepositoryReleaseTagsConfig,
)
from testing.core.interfaces.repository_release_tags_probe import (
    RepositoryReleaseTagsProbe,
)
from testing.tests.support.repository_release_tags_probe_factory import (
    create_repository_release_tags_probe,
)


class RepositoryReleaseTagsApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = RepositoryReleaseTagsConfig.from_file(
            self.repository_root / "testing/tests/TS-229/config.yaml"
        )
        self.probe: RepositoryReleaseTagsProbe = create_repository_release_tags_probe(
            self.repository_root
        )

    def test_releases_and_tags_endpoints_return_non_empty_stable_versions(self) -> None:
        observation = self.probe.validate()
        self._write_result_if_requested(observation.to_dict())

        self.assertEqual(
            observation.releases_status_code,
            200,
            "Step 1 failed: GET releases endpoint did not return HTTP 200.\n"
            f"Endpoint: {observation.releases_api_url}\n"
            f"Observed status: {observation.releases_status_code}",
        )
        self.assertEqual(
            observation.tags_status_code,
            200,
            "Step 2 failed: GET tags endpoint did not return HTTP 200.\n"
            f"Endpoint: {observation.tags_api_url}\n"
            f"Observed status: {observation.tags_status_code}",
        )

        self.assertTrue(
            observation.release_tag_names,
            "Step 3 failed: releases endpoint returned an empty array.\n"
            f"Endpoint: {observation.releases_api_url}",
        )
        self.assertTrue(
            observation.tag_names,
            "Step 3 failed: tags endpoint returned an empty array.\n"
            f"Endpoint: {observation.tags_api_url}",
        )
        self.assertTrue(
            observation.stable_release_versions,
            "Step 3 failed: releases endpoint returned data, but no stable version "
            "tags in `v<major>.<minor>.<patch>` format were found.\n"
            f"Observed release tag names: {observation.release_tag_names}",
        )
        self.assertTrue(
            observation.stable_tag_versions,
            "Step 3 failed: tags endpoint returned data, but no stable version tags "
            "in `v<major>.<minor>.<patch>` format were found.\n"
            f"Observed tag names: {observation.tag_names}",
        )
        self.assertTrue(
            observation.common_stable_versions,
            "Expected both endpoint arrays to expose at least one common stable "
            "version, but none matched.\n"
            f"Stable versions in releases: {observation.stable_release_versions}\n"
            f"Stable versions in tags: {observation.stable_tag_versions}",
        )

        if self.config.expected_stable_version:
            self.assertIn(
                self.config.expected_stable_version,
                observation.common_stable_versions,
                "Expected stable version was not present in both releases and tags.\n"
                f"Expected: {self.config.expected_stable_version}\n"
                f"Common stable versions: {observation.common_stable_versions}",
            )

        latest_common_version = observation.latest_common_stable_version
        self.assertIsNotNone(
            latest_common_version,
            "Human-style verification failed: no common stable version was "
            "available to verify on the GitHub releases/tags pages.",
        )
        assert latest_common_version is not None

        self.assertIn(
            "Releases",
            observation.releases_page_text,
            "Human-style verification failed: the releases page did not render "
            "the expected visible heading text.\n"
            f"URL: {observation.releases_page_url}",
        )
        self.assertIn(
            "Tags",
            observation.tags_page_text,
            "Human-style verification failed: the tags page did not render the "
            "expected visible heading text.\n"
            f"URL: {observation.tags_page_url}",
        )
        self.assertIn(
            latest_common_version,
            observation.releases_page_text,
            "Human-style verification failed: the stable version was not visible on "
            "the releases page HTML output.\n"
            f"Version: {latest_common_version}\n"
            f"URL: {observation.releases_page_url}",
        )
        self.assertIn(
            latest_common_version,
            observation.tags_page_text,
            "Human-style verification failed: the stable version was not visible on "
            "the tags page HTML output.\n"
            f"Version: {latest_common_version}\n"
            f"URL: {observation.tags_page_url}",
        )

    def _write_result_if_requested(self, payload: dict[str, object]) -> None:
        result_path = os.environ.get("TS229_RESULT_PATH")
        if not result_path:
            return

        destination = Path(result_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    unittest.main()
