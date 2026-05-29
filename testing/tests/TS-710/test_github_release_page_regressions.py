from __future__ import annotations

import unittest

from testing.components.pages.github_release_page import GitHubReleasePage


class _FakeSession:
    def __init__(self) -> None:
        self.snapshot_payload: object = {}
        self.focus_group = "asset"
        self.focus_sequences: dict[str, list[dict[str, object | None]]] = {
            "asset": [],
            "quick-start": [],
        }
        self.downloads: list[str] = []
        self.focus_calls: list[str] = []
        self.key_presses: list[str] = []

    def evaluate(self, expression: str, *, arg: object | None = None) -> object:
        del expression, arg
        if self.focus_calls:
            sequence = self.focus_sequences[self.focus_group]
            return sequence.pop(0)
        return self.snapshot_payload

    def focus(
        self,
        selector: str,
        *,
        has_text: str | None = None,
        index: int = 0,
        timeout_ms: int = 30_000,
    ) -> None:
        del has_text, index, timeout_ms
        self.focus_calls.append(selector)
        if 'data-ts710-focus-group="quick-start"' in selector:
            self.focus_group = "quick-start"
        else:
            self.focus_group = "asset"

    def press_key(self, key: str) -> None:
        self.key_presses.append(key)

    def wait_for_download_after_keypress(
        self,
        key: str,
        *,
        timeout_ms: int = 30_000,
    ) -> str:
        del key, timeout_ms
        return self.downloads.pop(0)

    def screenshot(self, path: str) -> None:
        del path


class GitHubReleasePageRegressionTest(unittest.TestCase):
    def test_observe_accessibility_preserves_full_focus_sequences(self) -> None:
        session = _FakeSession()
        session.snapshot_payload = {
            "releaseTitle": "TrackState v0.0.96",
            "assetSectionLabel": "Assets 3",
            "headings": [{"level": 2, "text": "Quick Start"}],
            "quickStartHeadingPresent": True,
            "quickStartHeadingIsLogical": True,
            "quickStartExpectedFocusOrder": [
                {
                    "tagName": "A",
                    "role": None,
                    "label": "Install TrackState",
                    "href": "https://example.test/install",
                },
                {
                    "tagName": "BUTTON",
                    "role": None,
                    "label": "",
                    "href": None,
                },
            ],
            "assets": [
                {
                    "label": "TrackState-macOS.dmg",
                    "ariaLabel": None,
                    "href": "/IstiN/trackstate/releases/download/v0.0.96/TrackState-macOS.dmg",
                    "tabindex": None,
                    "keyboardFocusable": True,
                },
            ],
            "digests": [
                {
                    "label": "Copy to clipboard digest for TrackState-macOS.dmg",
                    "value": "sha256:abc123",
                },
            ],
            "assetExpectedFocusOrder": [
                {
                    "tagName": "SUMMARY",
                    "role": None,
                    "label": "Assets 3",
                    "href": None,
                },
                {
                    "tagName": "A",
                    "role": None,
                    "label": "TrackState-macOS.dmg",
                    "href": "/IstiN/trackstate/releases/download/v0.0.96/TrackState-macOS.dmg",
                },
                {
                    "tagName": "CLIPBOARD-COPY",
                    "role": "button",
                    "label": "Copy to clipboard digest for TrackState-macOS.dmg",
                    "href": None,
                },
            ],
            "releaseNoteTextColor": "rgb(31, 35, 40)",
            "releaseNoteBackgroundColor": "rgb(255, 255, 255)",
        }
        session.focus_sequences["asset"] = [
            {
                "tagName": "SUMMARY",
                "role": None,
                "label": "Assets 3",
                "href": None,
            },
            {
                "tagName": "A",
                "role": None,
                "label": "TrackState-macOS.dmg",
                "href": "/IstiN/trackstate/releases/download/v0.0.96/TrackState-macOS.dmg",
            },
            {
                "tagName": "CLIPBOARD-COPY",
                "role": "button",
                "label": "Copy to clipboard digest for TrackState-macOS.dmg",
                "href": None,
            },
        ]
        session.focus_sequences["quick-start"] = [
            {
                "tagName": "A",
                "role": None,
                "label": "Install TrackState",
                "href": "https://example.test/install",
            },
            {
                "tagName": "BUTTON",
                "role": None,
                "label": "",
                "href": None,
            },
        ]
        session.downloads = ["TrackState-macOS.dmg"]

        observation = GitHubReleasePage(session).observe_accessibility(
            repository="IstiN/trackstate",
            tag_name="v0.0.96",
            release_page_url="https://github.com/IstiN/trackstate/releases/tag/v0.0.96",
        )

        self.assertEqual(
            [step.label for step in observation.asset_focus_order],
            [
                "Assets 3",
                "TrackState-macOS.dmg",
                "Copy to clipboard digest for TrackState-macOS.dmg",
            ],
        )
        self.assertEqual(
            [step.label for step in observation.quick_start_focus_order],
            ["Install TrackState", ""],
        )
        self.assertEqual(observation.quick_start_focus_labels, ["Install TrackState", ""])


if __name__ == "__main__":
    unittest.main()
