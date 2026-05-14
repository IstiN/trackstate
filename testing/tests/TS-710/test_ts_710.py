from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import unittest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.core.config.github_release_accessibility_config import (  # noqa: E402
    GitHubReleaseAccessibilityConfig,
)
from testing.core.interfaces.github_release_accessibility_probe import (  # noqa: E402
    GitHubReleaseAccessibilityObservation,
)
from testing.tests.support.github_release_accessibility_probe_factory import (  # noqa: E402
    create_github_release_accessibility_probe,
)


class GitHubReleaseAccessibilityTest(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.repository_root = REPO_ROOT
        self.config = GitHubReleaseAccessibilityConfig.from_file(
            self.repository_root / "testing/tests/TS-710/config.yaml",
        )
        self.probe = create_github_release_accessibility_probe(self.repository_root)

    def test_latest_release_page_assets_and_instructions_are_accessible(self) -> None:
        observation = self.probe.validate()
        self._write_result_if_requested(observation)

        self.assertIn(
            "/releases/tag/",
            observation.release_page_url,
            "Step 1 failed: TS-710 did not open a GitHub release tag page.\n"
            f"Observed URL: {observation.release_page_url}",
        )
        self.assertTrue(
            observation.tag_name.startswith("v"),
            "Step 1 failed: TS-710 did not resolve a stable `v*` release tag.\n"
            f"Observed tag: {observation.tag_name}",
        )
        self.assertIn(
            observation.tag_name,
            observation.release_title,
            "Step 1 failed: the live release page title did not include the resolved "
            "stable release tag.\n"
            f"Observed title: {observation.release_title}",
        )

        self.assertIn(
            "Assets",
            observation.asset_section_label,
            "Step 2 failed: the live release page did not render a visible Assets "
            "section label.\n"
            f"Observed label: {observation.asset_section_label}",
        )
        self.assertTrue(
            observation.assets,
            "Step 2 failed: the live Assets section did not expose any focusable "
            "download links.\n"
            f"Release page: {observation.release_page_url}",
        )

        downloadable_assets = [
            asset for asset in observation.assets if "/releases/download/" in asset.href
        ]
        self.assertTrue(
            downloadable_assets,
            "Step 2 failed: the live release page did not expose any published release "
            "artifact links under `/releases/download/`.\n"
            f"Observed assets: {[asset.href for asset in observation.assets]}",
        )

        for asset in observation.assets:
            accessible_label = asset.aria_label or asset.label
            self.assertTrue(
                accessible_label.strip(),
                "Step 3 failed: a release asset link did not expose a non-empty visible "
                "label or ARIA label.\n"
                f"Observed asset: {asset}",
            )
            self.assertTrue(
                asset.keyboard_focusable,
                "Step 3 failed: a release asset link was not keyboard focusable.\n"
                f"Observed asset: {asset}",
            )

        self.assertTrue(
            observation.digests,
            "Step 3 failed: the live Assets section did not expose any checksum or "
            "digest control for the published release artifact.\n"
            f"Observed assets: {downloadable_assets}",
        )
        for digest in observation.digests:
            self.assertTrue(
                digest.label.strip(),
                "Step 3 failed: a checksum control did not expose a descriptive "
                "accessible label.\n"
                f"Observed digest: {digest}",
            )
            self.assertTrue(
                digest.value.startswith("sha256:"),
                "Step 3 failed: a checksum control did not expose a SHA-256 digest.\n"
                f"Observed digest: {digest}",
            )

        focused_asset_labels = [
            step.label
            for step in observation.asset_focus_order
            if step.href is not None and step.label is not None
        ]
        expected_asset_labels = [asset.aria_label or asset.label for asset in observation.assets]
        self.assertEqual(
            focused_asset_labels,
            expected_asset_labels,
            "Step 4 failed: keyboard traversal through the Assets section did not keep "
            "the asset links in logical order.\n"
            f"Focused asset labels: {focused_asset_labels}\n"
            f"Expected asset labels: {expected_asset_labels}",
        )
        self.assertTrue(
            observation.asset_focus_order and observation.asset_focus_order[0].label is not None,
            "Step 4 failed: keyboard traversal never reached the Assets section control.",
        )
        self.assertIn(
            "Assets",
            observation.asset_focus_order[0].label or "",
            "Step 4 failed: keyboard traversal did not begin from the Assets section "
            "toggle before moving into the asset links.\n"
            f"Observed focus order: {observation.asset_focus_order}",
        )

        self.assertEqual(
            len(observation.downloads),
            len(observation.assets),
            "Step 5 failed: keyboard activation did not trigger downloads for every "
            "visible asset link.\n"
            f"Observed downloads: {observation.downloads}\n"
            f"Observed assets: {observation.assets}",
        )
        for download, asset in zip(observation.downloads, observation.assets, strict=True):
            self.assertEqual(
                download.href,
                asset.href,
                "Step 5 failed: the keyboard-triggered download did not correspond to "
                "the focused asset link.\n"
                f"Observed download: {download}\n"
                f"Observed asset: {asset}",
            )
            self.assertTrue(
                download.suggested_filename.strip(),
                "Step 5 failed: activating an asset link from the keyboard did not "
                "produce a downloadable filename.\n"
                f"Observed download: {download}",
            )

        self.assertGreaterEqual(
            observation.release_note_contrast_ratio,
            4.5,
            "Expected result failed: the rendered release-note text contrast was below "
            "WCAG AA.\n"
            f"Observed contrast ratio: {observation.release_note_contrast_ratio:.2f}:1\n"
            f"Text color: {observation.release_note_text_color_hex}\n"
            f"Background color: {observation.release_note_background_color_hex}",
        )

        self.assertTrue(
            observation.headings,
            "Human-style verification failed: the visible release notes did not expose "
            "any headings for screen-reader navigation.\n"
            f"Release page: {observation.release_page_url}",
        )
        if observation.quick_start_heading_present:
            self.assertTrue(
                observation.quick_start_heading_is_logical,
                "Human-style verification failed: the visible Quick Start heading "
                "jumped to an illogical level within the release notes.\n"
                f"Observed headings: {observation.headings}",
            )
            for label in observation.quick_start_focus_labels:
                self.assertTrue(
                    label.strip(),
                    "Human-style verification failed: a Quick Start control did not "
                    "expose a non-empty accessible label.\n"
                    f"Observed labels: {observation.quick_start_focus_labels}",
                )

    def _write_result_if_requested(
        self,
        observation: GitHubReleaseAccessibilityObservation,
    ) -> None:
        result_path = os.environ.get("TS710_RESULT_PATH")
        if not result_path:
            return

        destination = Path(result_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(observation.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
