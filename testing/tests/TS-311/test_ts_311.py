from __future__ import annotations

import sys
from pathlib import Path
import unittest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_issue_detail_collaboration_page import (
    LiveIssueDetailCollaborationPage,
)
from testing.components.services.live_setup_repository_service import (
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config
from testing.tests.support.live_tracker_app_factory import (
    create_live_tracker_app_with_stored_token,
)


OUTPUTS_DIR = REPO_ROOT / "outputs"
SCREENSHOT_PATH = OUTPUTS_DIR / "ts311_failure.png"
SEEDED_COMMENT_FRAGMENT = "This comment demonstrates markdown-backed collaboration history."
READ_ONLY_ATTACHMENT_MESSAGE = "download-only for Git LFS attachments"
DOWNLOAD_BUTTON_LABEL_FRAGMENT = "Download"
UPLOAD_BUTTON_LABEL_FRAGMENT = "Upload attachment to"


class IssueDetailCollaborationTabsHostedCapabilityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = load_live_setup_test_config()
        self.repository_service = LiveSetupRepositoryService(config=self.config)

    def test_issue_detail_uses_tabs_and_gates_attachment_actions(self) -> None:
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

        token = self.repository_service.token
        if not token:
            raise RuntimeError(
                "TS-311 requires GH_TOKEN or GITHUB_TOKEN to open the hosted live app.",
            )

        user = self.repository_service.fetch_authenticated_user()
        issue_fixture = self.repository_service.fetch_issue_fixture("DEMO/DEMO-1/DEMO-2")

        self.assertEqual(
            issue_fixture.key,
            "DEMO-2",
            "Precondition failed: TS-311 expected the seeded DEMO-2 fixture.",
        )
        self.assertTrue(
            issue_fixture.attachment_paths,
            "Precondition failed: DEMO-2 does not contain any seeded attachments in "
            f"{issue_fixture.path}.",
        )
        self.assertTrue(
            issue_fixture.comment_paths,
            "Precondition failed: DEMO-2 does not contain any seeded comments in "
            f"{issue_fixture.path}.",
        )

        with create_live_tracker_app_with_stored_token(
            self.config,
            token=token,
        ) as tracker_page:
            live_issue_page = LiveIssueDetailCollaborationPage(tracker_page)
            try:
                runtime = tracker_page.open()
                self.assertEqual(
                    runtime.kind,
                    "ready",
                    "Step 1 failed: the deployed app did not reach the hosted tracker "
                    "shell before the collaboration scenario began.\n"
                    f"Observed body text:\n{runtime.body_text}",
                )

                live_issue_page.ensure_connected(
                    token=token,
                    repository=self.repository_service.repository,
                    user_login=user.login,
                )
                live_issue_page.open_issue(
                    issue_key=issue_fixture.key,
                    issue_summary=issue_fixture.summary,
                )

                self.assertGreater(
                    live_issue_page.issue_detail_count(issue_fixture.key),
                    0,
                    "Step 1 failed: the hosted app did not open the requested issue "
                    f"detail for {issue_fixture.key}.\n"
                    f"Observed body text:\n{live_issue_page.current_body_text()}",
                )

                comments_tabs = live_issue_page.tab_button_count("Comments")
                attachments_tabs = live_issue_page.tab_button_count("Attachments")
                history_tabs = live_issue_page.tab_button_count("History")
                seeded_attachment_name = Path(issue_fixture.attachment_paths[0]).name
                inline_comment_count = live_issue_page.text_fragment_count(
                    SEEDED_COMMENT_FRAGMENT,
                )
                seeded_attachment_count = live_issue_page.text_fragment_count(
                    seeded_attachment_name,
                )

                self.assertGreater(
                    comments_tabs,
                    0,
                    "Step 2 failed: the issue detail did not expose a dedicated "
                    '"Comments" tab button in the hosted session.\n'
                    f"Observed body text:\n{live_issue_page.current_body_text()}",
                )
                self.assertGreater(
                    attachments_tabs,
                    0,
                    "Step 2 failed: the issue detail did not expose a dedicated "
                    '"Attachments" tab button for an issue that has seeded attachments.\n'
                    f"Seeded attachments: {issue_fixture.attachment_paths}\n"
                    f"Inline attachment visibility count: {seeded_attachment_count}\n"
                    f"Observed body text:\n{live_issue_page.current_body_text()}",
                )
                self.assertGreater(
                    history_tabs,
                    0,
                    "Step 2 failed: the issue detail did not expose a dedicated "
                    '"History" tab button in the hosted session.\n'
                    f"Observed body text:\n{live_issue_page.current_body_text()}",
                )
                self.assertEqual(
                    inline_comment_count,
                    0,
                    "Step 2 failed: collaboration content was rendered inline inside the "
                    "issue detail surface instead of being isolated behind tabs.\n"
                    f"Inline comment visibility count: {inline_comment_count}\n"
                    f"Observed body text:\n{live_issue_page.current_body_text()}",
                )
                self.assertEqual(
                    seeded_attachment_count,
                    0,
                    "Step 2 failed: seeded attachment content was visible on the initial "
                    "issue detail surface before the Attachments tab was opened.\n"
                    f"Seeded attachment: {seeded_attachment_name}\n"
                    f"Inline attachment visibility count: {seeded_attachment_count}\n"
                    f"Observed body text:\n{live_issue_page.current_body_text()}",
                )

                live_issue_page.open_collaboration_tab("Comments")
                self.assertGreater(
                    live_issue_page.text_fragment_count(SEEDED_COMMENT_FRAGMENT),
                    0,
                    "Step 2 failed: opening the Comments tab did not reveal the seeded "
                    "comment content for DEMO-2.\n"
                    f"Observed body text:\n{live_issue_page.current_body_text()}",
                )

                live_issue_page.open_collaboration_tab("History")
                self.assertEqual(
                    live_issue_page.text_fragment_count(SEEDED_COMMENT_FRAGMENT),
                    0,
                    "Step 2 failed: opening the History tab left the Comments tab content "
                    "visible, so tab navigation did not switch collaboration panels.\n"
                    f"Observed body text:\n{live_issue_page.current_body_text()}",
                )
                self.assertEqual(
                    live_issue_page.text_fragment_count(seeded_attachment_name),
                    0,
                    "Step 2 failed: opening the History tab left the Attachments tab "
                    "content visible, so tab navigation did not switch collaboration "
                    "panels.\n"
                    f"Observed body text:\n{live_issue_page.current_body_text()}",
                )

                live_issue_page.open_collaboration_tab("Attachments")
                self.assertGreater(
                    live_issue_page.text_fragment_count(seeded_attachment_name),
                    0,
                    "Step 3 failed: opening the Attachments tab did not reveal the seeded "
                    f"attachment {seeded_attachment_name}.\n"
                    f"Observed body text:\n{live_issue_page.current_body_text()}",
                )

                read_only_message_count = live_issue_page.text_fragment_count(
                    READ_ONLY_ATTACHMENT_MESSAGE,
                )
                download_button_count = live_issue_page.button_label_fragment_count(
                    DOWNLOAD_BUTTON_LABEL_FRAGMENT,
                )
                upload_button_count = live_issue_page.button_label_fragment_count(
                    UPLOAD_BUTTON_LABEL_FRAGMENT,
                )

                self.assertEqual(
                    upload_button_count,
                    0,
                    "Step 3 failed: the hosted Attachments tab still exposed an upload "
                    "action even though Git LFS uploads are unsupported in the hosted "
                    "session.\n"
                    f"Observed body text:\n{live_issue_page.current_body_text()}",
                )
                self.assertGreater(
                    read_only_message_count,
                    0,
                    "Step 3 failed: the hosted Attachments tab did not explain that this "
                    "session is read-only/download-only for Git LFS attachments.\n"
                    f"Observed body text:\n{live_issue_page.current_body_text()}",
                )
                self.assertGreater(
                    download_button_count,
                    0,
                    "Step 3 failed: the hosted Attachments tab did not expose any "
                    "download action for the seeded LFS attachment.\n"
                    f"Seeded attachment: {seeded_attachment_name}\n"
                    f"Observed body text:\n{live_issue_page.current_body_text()}",
                )
            except Exception:
                live_issue_page.screenshot(str(SCREENSHOT_PATH))
                raise


if __name__ == "__main__":
    unittest.main()
