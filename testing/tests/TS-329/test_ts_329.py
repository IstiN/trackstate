from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import quote
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
from testing.core.interfaces.web_app_session import WebAppTimeoutError
from testing.frameworks.python.playwright_web_app_session import (
    PlaywrightStoredTokenWebAppRuntime,
)
from testing.tests.support.live_tracker_app_factory import create_live_tracker_app


OUTPUTS_DIR = REPO_ROOT / "outputs"
SCREENSHOT_PATH = OUTPUTS_DIR / "ts329_failure.png"
SEEDED_COMMENT_FRAGMENT = "This comment demonstrates markdown-backed collaboration history."
ATTACHMENT_METADATA_FALLBACK = "unknown from repo"
DOWNLOAD_BUTTON_LABEL_FRAGMENT = "Download"


class AttachmentMetadataRestrictedRuntime(PlaywrightStoredTokenWebAppRuntime):
    def __init__(self, *, repository: str, token: str, attachment_path: str) -> None:
        super().__init__(repository=repository, token=token)
        self._attachment_path = attachment_path
        self.intercepted_urls: list[str] = []

    def __enter__(self):
        session = super().__enter__()
        assert self._context is not None
        encoded_path = quote(self._attachment_path, safe="")

        def route_handler(route) -> None:
            url = route.request.url
            if "/commits?" in url and f"path={encoded_path}" in url:
                self.intercepted_urls.append(url)
                route.fulfill(
                    status=403,
                    content_type="application/json",
                    body=json.dumps(
                        {
                            "message": (
                                "TS-329 synthetic restriction: attachment metadata access denied"
                            ),
                        },
                    ),
                )
                return
            route.continue_(
                headers={
                    **route.request.headers,
                    "Authorization": f"Bearer {self._token}",
                },
            )

        self._context.route("https://api.github.com/**", route_handler)
        return session


class HostedIssueDetailMetadataRestrictionRegressionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = load_live_setup_test_config()
        self.repository_service = LiveSetupRepositoryService(config=self.config)

    def test_core_tabs_stay_visible_when_attachment_metadata_is_restricted(self) -> None:
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

        token = self.repository_service.token
        if not token:
            raise RuntimeError(
                "TS-329 requires GH_TOKEN or GITHUB_TOKEN to open the hosted live app.",
            )

        user = self.repository_service.fetch_authenticated_user()
        issue_fixture = self.repository_service.fetch_issue_fixture("DEMO/DEMO-1/DEMO-2")

        self.assertEqual(
            issue_fixture.key,
            "DEMO-2",
            "Precondition failed: TS-329 expected the seeded DEMO-2 fixture.",
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

        runtime = AttachmentMetadataRestrictedRuntime(
            repository=self.config.repository,
            token=token,
            attachment_path=issue_fixture.attachment_paths[0],
        )
        with create_live_tracker_app(
            self.config,
            runtime_factory=lambda: runtime,
        ) as tracker_page:
            live_issue_page = LiveIssueDetailCollaborationPage(tracker_page)
            try:
                runtime_observation = tracker_page.open()
                self.assertEqual(
                    runtime_observation.kind,
                    "ready",
                    "Step 1 failed: the deployed app did not reach the hosted tracker "
                    "shell before the restricted metadata scenario began.\n"
                    f"Observed body text:\n{runtime_observation.body_text}",
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

                issue_detail_text = live_issue_page.current_body_text()
                self.assertGreater(
                    live_issue_page.issue_detail_count(issue_fixture.key),
                    0,
                    "Step 1 failed: the hosted app did not open the requested issue "
                    f"detail for {issue_fixture.key}.\n"
                    f"Observed body text:\n{issue_detail_text}",
                )
                self.assertGreater(
                    len(runtime.intercepted_urls),
                    0,
                    "Step 2 failed: the test did not intercept the attachment metadata "
                    "request, so the restricted-access scenario was not exercised.",
                )

                comments_tabs = live_issue_page.tab_button_count("Comments")
                attachments_tabs = live_issue_page.tab_button_count("Attachments")
                history_tabs = live_issue_page.tab_button_count("History")

                self.assertGreater(
                    comments_tabs,
                    0,
                    "Step 3 failed: the issue detail did not keep the visible "
                    '"Comments" tab after attachment metadata access was restricted.\n'
                    f"Observed body text:\n{issue_detail_text}",
                )
                self.assertGreater(
                    attachments_tabs,
                    0,
                    "Step 3 failed: the issue detail did not keep the visible "
                    '"Attachments" tab after attachment metadata access was restricted.\n'
                    f"Observed body text:\n{issue_detail_text}",
                )
                self.assertGreater(
                    history_tabs,
                    0,
                    "Step 3 failed: the issue detail did not keep the visible "
                    '"History" tab after attachment metadata access was restricted.\n'
                    f"Observed body text:\n{issue_detail_text}",
                )

                live_issue_page.open_collaboration_tab("Comments")
                try:
                    tracker_page.session.wait_for_selector(
                        'flt-semantics[role="button"][aria-current="true"]',
                        has_text="Comments",
                        timeout_ms=30_000,
                    )
                    tracker_page.session.wait_for_text(
                        SEEDED_COMMENT_FRAGMENT,
                        timeout_ms=30_000,
                    )
                except WebAppTimeoutError as error:
                    raise AssertionError(
                        "Step 3 failed: the Comments tab was visible but did not become "
                        "the active collaboration view after it was opened.\n"
                        f"Observed body text:\n{live_issue_page.current_body_text()}",
                    ) from error
                comments_text = live_issue_page.current_body_text()
                self.assertGreater(
                    live_issue_page.selected_tab_count("Comments"),
                    0,
                    "Step 3 failed: the Comments tab was visible but did not become the "
                    "selected collaboration view when activated.\n"
                    f"Observed body text:\n{comments_text}",
                )
                self.assertIn(
                    SEEDED_COMMENT_FRAGMENT,
                    comments_text,
                    "Step 3 failed: the Comments tab did not stay interactive after "
                    "attachment metadata access was restricted.\n"
                    f"Observed body text:\n{comments_text}",
                )

                live_issue_page.open_collaboration_tab("History")
                try:
                    tracker_page.session.wait_for_selector(
                        'flt-semantics[role="button"][aria-current="true"]',
                        has_text="History",
                        timeout_ms=30_000,
                    )
                except WebAppTimeoutError as error:
                    raise AssertionError(
                        "Step 3 failed: the History tab was visible but did not become "
                        "the active collaboration view after it was opened.\n"
                        f"Observed body text:\n{live_issue_page.current_body_text()}",
                    ) from error
                history_text = live_issue_page.current_body_text()
                self.assertGreater(
                    live_issue_page.selected_tab_count("History"),
                    0,
                    "Step 3 failed: the History tab was visible but did not become the "
                    "selected collaboration view when activated.\n"
                    f"Observed body text:\n{history_text}",
                )

                live_issue_page.open_collaboration_tab("Attachments")
                try:
                    tracker_page.session.wait_for_selector(
                        'flt-semantics[role="button"][aria-current="true"]',
                        has_text="Attachments",
                        timeout_ms=30_000,
                    )
                    tracker_page.session.wait_for_text(
                        Path(issue_fixture.attachment_paths[0]).name,
                        timeout_ms=30_000,
                    )
                except WebAppTimeoutError as error:
                    raise AssertionError(
                        "Step 3 failed: the Attachments tab was visible but did not "
                        "become the active collaboration view after it was opened.\n"
                        f"Observed body text:\n{live_issue_page.current_body_text()}",
                    ) from error
                attachments_text = live_issue_page.current_body_text()
                self.assertGreater(
                    live_issue_page.selected_tab_count("Attachments"),
                    0,
                    "Step 3 failed: the Attachments tab was visible but did not become "
                    "the selected collaboration view when activated.\n"
                    f"Observed body text:\n{attachments_text}",
                )
                self.assertIn(
                    Path(issue_fixture.attachment_paths[0]).name,
                    attachments_text,
                    "Step 3 failed: the Attachments tab did not keep the seeded "
                    "attachment visible after metadata access was restricted.\n"
                    f"Observed body text:\n{attachments_text}",
                )
                self.assertIn(
                    ATTACHMENT_METADATA_FALLBACK,
                    attachments_text,
                    "Step 3 failed: restricting attachment metadata did not produce the "
                    'expected attachment-only fallback text "unknown from repo".\n'
                    f"Observed body text:\n{attachments_text}",
                )
                self.assertGreater(
                    live_issue_page.button_label_fragment_count(
                        DOWNLOAD_BUTTON_LABEL_FRAGMENT,
                    ),
                    0,
                    "Step 3 failed: the restricted attachment metadata state removed the "
                    "download action instead of isolating the degradation to metadata.\n"
                    f"Observed body text:\n{attachments_text}",
                )
            except Exception:
                live_issue_page.screenshot(str(SCREENSHOT_PATH))
                raise


if __name__ == "__main__":
    unittest.main()
