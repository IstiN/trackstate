from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path

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


TICKET_KEY = "TS-330"
ISSUE_PATH = "DEMO/DEMO-1/DEMO-4"
EXPECTED_ISSUE_KEY = "DEMO-4"
EXPECTED_ISSUE_SUMMARY = "Search with JQL"
EXPECTED_COMMENT = (
    "JQL support should remain Jira-compatible for the supported TrackState fields."
)
CONTROL_COMMENT = "This comment demonstrates markdown-backed collaboration history."
OUTPUTS_DIR = REPO_ROOT / "outputs"
SCREENSHOT_PATH = OUTPUTS_DIR / "ts330_failure.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-330 requires GH_TOKEN or GITHUB_TOKEN to open the hosted live app.",
        )

    issue_fixture = service.fetch_issue_fixture(ISSUE_PATH)
    _assert_fixture_preconditions(issue_fixture)
    user = service.fetch_authenticated_user()

    result: dict[str, object] = {
        "status": "failed",
        "ticket": TICKET_KEY,
        "app_url": config.app_url,
        "repository": service.repository,
        "repository_ref": service.ref,
        "issue_key": issue_fixture.key,
        "issue_summary": issue_fixture.summary,
        "steps": [],
        "human_verification": [],
    }

    try:
        with create_live_tracker_app_with_stored_token(
            config,
            token=token,
        ) as tracker_page:
            live_issue_page = LiveIssueDetailCollaborationPage(tracker_page)
            runtime = tracker_page.open()
            result["runtime_state"] = runtime.kind
            result["runtime_body_text"] = runtime.body_text
            if runtime.kind != "ready":
                raise AssertionError(
                    "Step 1 failed: the deployed app did not reach the hosted tracker "
                    "shell before the zero-attachment collaboration scenario began.\n"
                    f"Observed body text:\n{runtime.body_text}",
                )
            _record_step(
                result,
                step=1,
                status="passed",
                action="Open the deployed app and reach the hosted tracker shell.",
                observed=runtime.body_text,
            )

            live_issue_page.ensure_connected(
                token=token,
                repository=service.repository,
                user_login=user.login,
            )
            live_issue_page.dismiss_connection_banner()
            _record_step(
                result,
                step=2,
                status="passed",
                action="Connect the hosted GitHub session.",
                observed=live_issue_page.current_body_text(),
            )

            live_issue_page.search_and_select_issue(
                issue_key=issue_fixture.key,
                issue_summary=issue_fixture.summary,
            )
            filtered_body = live_issue_page.current_body_text()
            if "1 issue" not in filtered_body:
                raise AssertionError(
                    "Step 3 failed: filtering the hosted JQL Search view down to the "
                    "zero-attachment issue did not show the visible \"1 issue\" state.\n"
                    f"Observed body text:\n{filtered_body}",
                )
            comments_tabs = live_issue_page.tab_button_count("Comments")
            history_tabs = live_issue_page.tab_button_count("History")
            if comments_tabs == 0 or history_tabs == 0:
                raise AssertionError(
                    "Step 3 failed: the zero-attachment issue selection did not keep the "
                    'visible collaboration tab strip with both "Comments" and '
                    '"History" actions.\n'
                    f'Visible "Comments" tab count: {comments_tabs}\n'
                    f'Visible "History" tab count: {history_tabs}\n'
                    f"Observed body text:\n{filtered_body}",
                )
            _record_step(
                result,
                step=3,
                status="passed",
                action=(
                    "Filter JQL Search to the zero-attachment issue and verify the "
                    'visible "Comments" and "History" tabs remain on screen.'
                ),
                observed=filtered_body,
            )

            live_issue_page.open_collaboration_tab("Comments")
            comments_body = live_issue_page.wait_for_text(
                EXPECTED_COMMENT,
                timeout_ms=60_000,
            )
            if CONTROL_COMMENT in comments_body:
                raise AssertionError(
                    "Step 4 failed: opening Comments after selecting the zero-attachment "
                    "issue still showed the seeded DEMO-2 comment instead of the DEMO-4 "
                    "comment, so the user-facing issue context did not switch.\n"
                    f"Observed body text:\n{comments_body}",
                )
            _record_step(
                result,
                step=4,
                status="passed",
                action=(
                    "Open the Comments tab and verify the user sees the DEMO-4 comment "
                    "content."
                ),
                observed=comments_body,
            )
            _record_human_verification(
                result,
                check=(
                    'Verified the visible "Comments" tab label was reachable and the '
                    "page showed the exact DEMO-4 comment text with its timestamp."
                ),
                observed=comments_body,
            )

            live_issue_page.open_collaboration_tab("History")
            history_body = live_issue_page.wait_for_text_absent(
                EXPECTED_COMMENT,
                timeout_ms=60_000,
            )
            if (
                live_issue_page.tab_button_count("Comments") == 0
                or live_issue_page.tab_button_count("History") == 0
            ):
                raise AssertionError(
                    "Step 5 failed: after switching to History, the collaboration tab "
                    "strip no longer exposed both Comments and History actions.\n"
                    f"Observed body text:\n{history_body}",
                )
            _record_step(
                result,
                step=5,
                status="passed",
                action=(
                    "Open the History tab and verify the DEMO-4 comment content is no "
                    "longer shown, proving the user can switch panels."
                ),
                observed=history_body,
            )
            _record_human_verification(
                result,
                check=(
                    'Verified the visible "History" tab remained on screen and switching '
                    "to it removed the DEMO-4 comment from the page, matching a real tab "
                    "change."
                ),
                observed=history_body,
            )
    except AssertionError as error:
        result["error"] = str(error)
        result["traceback"] = traceback.format_exc()
        result["screenshot"] = str(SCREENSHOT_PATH)
        _capture_failure_screenshot(config, token, result_path=SCREENSHOT_PATH)
        _write_result_if_requested(result)
        print(json.dumps(result, indent=2))
        raise
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        result["screenshot"] = str(SCREENSHOT_PATH)
        _capture_failure_screenshot(config, token, result_path=SCREENSHOT_PATH)
        _write_result_if_requested(result)
        print(json.dumps(result, indent=2))
        raise
    else:
        result["status"] = "passed"
        result["summary"] = (
            "Verified the hosted zero-attachment issue keeps the visible collaboration "
            "tab strip, shows the DEMO-4 comment in Comments, and lets the user switch "
            "to History without losing the tab navigation."
        )
        _write_result_if_requested(result)
        print(json.dumps(result, indent=2))


def _assert_fixture_preconditions(issue_fixture) -> None:
    if issue_fixture.key != EXPECTED_ISSUE_KEY:
        raise AssertionError(
            "Precondition failed: TS-330 expected to validate the seeded DEMO-4 issue.\n"
            f"Observed key: {issue_fixture.key}",
        )
    if issue_fixture.summary != EXPECTED_ISSUE_SUMMARY:
        raise AssertionError(
            "Precondition failed: TS-330 expected the seeded DEMO-4 summary to remain "
            "stable.\n"
            f"Expected summary: {EXPECTED_ISSUE_SUMMARY}\n"
            f"Observed summary: {issue_fixture.summary}",
        )
    if issue_fixture.attachment_paths:
        raise AssertionError(
            "Precondition failed: TS-330 requires a seeded issue with zero attachments.\n"
            f"Observed attachment paths: {issue_fixture.attachment_paths}",
        )
    if (
        len(issue_fixture.comment_bodies) != 1
        or issue_fixture.comment_bodies[0] != EXPECTED_COMMENT
    ):
        raise AssertionError(
            "Precondition failed: TS-330 expected DEMO-4 to expose the seeded comment "
            "used for human-style verification.\n"
            f"Observed comment bodies: {issue_fixture.comment_bodies}",
        )


def _capture_failure_screenshot(config, token: str, *, result_path: Path) -> None:
    try:
        with create_live_tracker_app_with_stored_token(
            config,
            token=token,
        ) as tracker_page:
            tracker_page.open()
            tracker_page.screenshot(str(result_path))
    except Exception:
        return


def _record_step(
    result: dict[str, object],
    *,
    step: int,
    status: str,
    action: str,
    observed: str,
) -> None:
    steps = result.setdefault("steps", [])
    assert isinstance(steps, list)
    steps.append(
        {
            "step": step,
            "status": status,
            "action": action,
            "observed": observed,
        },
    )


def _record_human_verification(
    result: dict[str, object],
    *,
    check: str,
    observed: str,
) -> None:
    checks = result.setdefault("human_verification", [])
    assert isinstance(checks, list)
    checks.append({"check": check, "observed": observed})


def _write_result_if_requested(payload: dict[str, object]) -> None:
    result_path = os.environ.get("TS330_RESULT_PATH")
    if not result_path:
        return
    destination = Path(result_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
