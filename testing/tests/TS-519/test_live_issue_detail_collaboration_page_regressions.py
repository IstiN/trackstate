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
        self.next_evaluate_result: object = 1

    def count(self, selector: str, *, has_text: str | None = None) -> int:
        del selector, has_text
        return 2

    def evaluate(self, expression: str, *, arg: object | None = None) -> object:
        self.evaluate_calls.append((expression, arg))
        return self.next_evaluate_result

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
        self.assertIn(
            "document.querySelectorAll('flt-semantics[aria-label]')",
            session.evaluate_calls[0][0],
        )

    def test_observe_attachment_upload_controls_tracks_visible_choose_and_upload_actions(
        self,
    ) -> None:
        session = _FakeSession()
        session.next_evaluate_result = {
            "chooseButtonCount": 1,
            "chooseButtonEnabled": True,
            "uploadButtonCount": 1,
            "uploadButtonEnabled": False,
        }
        page = LiveIssueDetailCollaborationPage(_FakeTrackerPage(session))

        controls = page.observe_attachment_upload_controls()

        self.assertEqual(controls.choose_button_count, 1)
        self.assertTrue(controls.choose_button_enabled)
        self.assertEqual(controls.upload_button_count, 1)
        self.assertFalse(controls.upload_button_enabled)
        self.assertEqual(len(session.evaluate_calls), 1)
        self.assertIn(
            'document.querySelectorAll(`flt-semantics[aria-label="${label}"]`)',
            session.evaluate_calls[0][0],
        )
        self.assertIn(
            "element?.querySelector('flt-semantics[flt-tappable]')",
            session.evaluate_calls[0][0],
        )

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
                    'flt-semantics[role="button"][flt-tappable]:text-is("Replace attachment")',
                    None,
                ),
            ],
        )


if __name__ == "__main__":
    unittest.main()
