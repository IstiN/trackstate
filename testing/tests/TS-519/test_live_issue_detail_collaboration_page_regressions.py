from __future__ import annotations

import unittest

from testing.components.pages.live_issue_detail_collaboration_page import (
    LiveIssueDetailCollaborationPage,
)


class _FakeSession:
    def __init__(self) -> None:
        self.evaluate_calls: list[tuple[str, object | None]] = []
        self.file_picker_calls: list[tuple[str, tuple[str, ...], str | None]] = []
        self.click_calls: list[tuple[str, str | None]] = []

    def count(self, selector: str, *, has_text: str | None = None) -> int:
        del selector, has_text
        return 2

    def evaluate(self, expression: str, *, arg: object | None = None) -> object:
        self.evaluate_calls.append((expression, arg))
        return 1

    def click_and_set_files(
        self,
        selector: str,
        files: list[str],
        *,
        has_text: str | None = None,
        index: int = 0,
        timeout_ms: int = 30_000,
    ) -> None:
        del index, timeout_ms
        self.file_picker_calls.append((selector, tuple(files), has_text))

    def click(
        self,
        selector: str,
        *,
        has_text: str | None = None,
        timeout_ms: int = 30_000,
    ) -> None:
        del timeout_ms
        self.click_calls.append((selector, has_text))


class _FakeTrackerPage:
    def __init__(self, session: _FakeSession) -> None:
        self.session = session


class LiveIssueDetailCollaborationPageRegressionTest(unittest.TestCase):
    def test_attachment_download_button_count_uses_exact_visible_aria_label(self) -> None:
        session = _FakeSession()
        page = LiveIssueDetailCollaborationPage(_FakeTrackerPage(session))

        count = page.attachment_download_button_count("manual.pdf")

        self.assertEqual(count, 1)
        self.assertEqual(len(session.evaluate_calls), 1)

    def test_choose_attachment_file_targets_exact_attachment_button(self) -> None:
        session = _FakeSession()
        page = LiveIssueDetailCollaborationPage(_FakeTrackerPage(session))

        page.choose_attachment_file("/tmp/manual.pdf")

        self.assertEqual(
            session.file_picker_calls,
            [
                (
                    'flt-semantics[aria-label="Choose attachment"] flt-semantics[flt-tappable]',
                    ("/tmp/manual.pdf",),
                    None,
                ),
            ],
        )

    def test_confirm_replace_attachment_targets_exact_dialog_action(self) -> None:
        session = _FakeSession()
        page = LiveIssueDetailCollaborationPage(_FakeTrackerPage(session))

        page.confirm_replace_attachment()

        self.assertEqual(
            session.click_calls,
            [
                (
                    'flt-semantics[aria-label="Replace attachment"] flt-semantics[flt-tappable]',
                    None,
                ),
            ],
        )


if __name__ == "__main__":
    unittest.main()
