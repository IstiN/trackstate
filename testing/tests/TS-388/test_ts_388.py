from __future__ import annotations

import json
import platform
import re
import sys
import traceback
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_issue_detail_collaboration_page import (  # noqa: E402
    LiveIssueDetailCollaborationPage,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveHostedIssueFixture,
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.tests.support.live_tracker_app_factory import (  # noqa: E402
    create_live_tracker_app_with_stored_token,
)

TICKET_KEY = "TS-388"
ISSUE_PATH = "DEMO/DEMO-1/DEMO-2"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts388_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts388_failure.png"
TIMESTAMP_PATTERN = re.compile(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z)")


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-388 requires GH_TOKEN or GITHUB_TOKEN to open the hosted live app.",
        )

    user = service.fetch_authenticated_user()
    issue_fixture = service.fetch_issue_fixture(ISSUE_PATH)

    result: dict[str, object] = {
        "status": "failed",
        "ticket": TICKET_KEY,
        "app_url": config.app_url,
        "repository": service.repository,
        "repository_ref": service.ref,
        "issue_path": ISSUE_PATH,
        "issue_key": issue_fixture.key,
        "issue_summary": issue_fixture.summary,
        "comment_paths": list(issue_fixture.comment_paths),
        "attachment_paths": list(issue_fixture.attachment_paths),
        "comment_bodies": list(issue_fixture.comment_bodies),
        "steps": [],
        "human_verification": [],
    }

    try:
        _assert_fixture_preconditions(issue_fixture)
        with create_live_tracker_app_with_stored_token(
            config,
            token=token,
        ) as tracker_page:
            page = LiveIssueDetailCollaborationPage(tracker_page)
            try:
                runtime = tracker_page.open()
                result["runtime_state"] = runtime.kind
                result["runtime_body_text"] = runtime.body_text
                if runtime.kind != "ready":
                    raise AssertionError(
                        "Step 1 failed: the deployed app did not reach the hosted tracker "
                        "shell before the issue-detail ordering scenario began.\n"
                        f"Observed body text:\n{runtime.body_text}",
                    )

                page.ensure_connected(
                    token=token,
                    repository=service.repository,
                    user_login=user.login,
                )
                page.dismiss_connection_banner()
                page.open_issue(
                    issue_key=issue_fixture.key,
                    issue_summary=issue_fixture.summary,
                )
                issue_detail_text = page.issue_detail_accessible_label(
                    issue_fixture.key,
                    expected_fragment=issue_fixture.summary,
                    timeout_ms=60_000,
                )
                result["issue_detail_text"] = issue_detail_text
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action="Open the issue detail view.",
                    observed=issue_detail_text,
                )

                page.open_collaboration_tab("Comments")
                comments_body = page.wait_for_collaboration_section_to_settle("Comments")
                result["comments_body_text"] = comments_body
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action="Navigate to the 'Comments' tab and observe the list.",
                    observed=comments_body,
                )

                comment_rows = page.visible_timestamped_rows()
                result["comment_rows"] = list(comment_rows)
                _assert_comment_order(issue_fixture, comment_rows, comments_body)
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action=(
                        "Verify that the comment added first appears at the top and the "
                        "newest at the bottom (AC2)."
                    ),
                    observed=" | ".join(comment_rows),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Verified the visible top comment row showed the oldest comment "
                        "body and timestamp, and the bottom comment row showed the newest."
                    ),
                    observed=" | ".join(comment_rows),
                )

                page.open_collaboration_tab("Attachments")
                attachments_body = page.wait_for_collaboration_section_to_settle(
                    "Attachments",
                )
                result["attachments_body_text"] = attachments_body
                _record_step(
                    result,
                    step=4,
                    status="passed",
                    action="Navigate to the 'Attachments' tab and observe the list.",
                    observed=attachments_body,
                )

                if page.accessible_label_count_containing("Attachments error") > 0:
                    attachment_error = page.deferred_error_label(
                        "Attachments",
                        timeout_ms=30_000,
                    )
                    result["attachments_error_label"] = attachment_error
                    raise AssertionError(
                        "Step 5 failed: the Attachments tab surfaced a user-visible error "
                        "instead of rendering a sortable attachment list.\n"
                        f"Visible error label:\n{attachment_error}\n"
                        f"Observed body text:\n{attachments_body}",
                    )

                attachment_rows = page.visible_timestamped_rows()
                result["attachment_rows"] = list(attachment_rows)
                _assert_attachment_order(attachment_rows, attachments_body)
                _record_step(
                    result,
                    step=5,
                    status="passed",
                    action=(
                        "Verify that the most recently uploaded attachment appears at the "
                        "top of the list (AC3)."
                    ),
                    observed=" | ".join(attachment_rows),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Verified the visible attachment list showed the newest timestamp "
                        "first and the oldest timestamp last."
                    ),
                    observed=" | ".join(attachment_rows),
                )

                page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
                _write_pass_outputs(result)
                return
            except Exception:
                page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                raise
    except Exception as error:
        failed_step = _extract_failed_step_number(str(error))
        if failed_step is not None and _step_status(result, failed_step) == "failed":
            _record_step(
                result,
                step=failed_step,
                status="failed",
                action=_ticket_step_action(failed_step),
                observed=str(error),
            )
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        _write_failure_outputs(result)
        raise


def _assert_fixture_preconditions(issue_fixture: LiveHostedIssueFixture) -> None:
    if len(issue_fixture.comment_bodies) < 2:
        raise AssertionError(
            "Precondition failed: the live issue fixture does not expose at least two "
            "comments needed to verify chronological comment ordering.\n"
            f"Issue path: {ISSUE_PATH}\n"
            f"Observed comment paths: {issue_fixture.comment_paths}",
        )
    if len(issue_fixture.attachment_paths) < 2:
        raise AssertionError(
            "Precondition failed: the live issue fixture does not expose at least two "
            "attachments needed to verify newest-to-oldest attachment ordering.\n"
            f"Issue path: {ISSUE_PATH}\n"
            f"Observed attachment paths: {issue_fixture.attachment_paths}",
        )


def _assert_comment_order(
    issue_fixture: LiveHostedIssueFixture,
    comment_rows: tuple[str, ...],
    comments_body: str,
) -> None:
    if len(comment_rows) < 2:
        raise AssertionError(
            "Step 3 failed: the Comments tab did not render at least two visible comment "
            "rows, so oldest-to-newest ordering could not be verified.\n"
            f"Observed rows: {list(comment_rows)}\n"
            f"Observed body text:\n{comments_body}",
        )

    oldest_fragment = _body_fragment(issue_fixture.comment_bodies[0])
    newest_fragment = _body_fragment(issue_fixture.comment_bodies[-1])
    if oldest_fragment not in comment_rows[0]:
        raise AssertionError(
            "Step 3 failed: the oldest seeded comment was not visible at the top of the "
            "Comments list.\n"
            f"Expected oldest fragment: {oldest_fragment!r}\n"
            f"Top row: {comment_rows[0]!r}\n"
            f"All visible rows: {list(comment_rows)}",
        )
    if newest_fragment not in comment_rows[-1]:
        raise AssertionError(
            "Step 3 failed: the newest seeded comment was not visible at the bottom of "
            "the Comments list.\n"
            f"Expected newest fragment: {newest_fragment!r}\n"
            f"Bottom row: {comment_rows[-1]!r}\n"
            f"All visible rows: {list(comment_rows)}",
        )

    comment_timestamps = [_parse_row_timestamp(row) for row in comment_rows]
    if comment_timestamps != sorted(comment_timestamps):
        raise AssertionError(
            "Step 3 failed: the Comments tab was not ordered from oldest-to-newest.\n"
            f"Observed rows: {list(comment_rows)}\n"
            f"Observed timestamps: {[value.isoformat() for value in comment_timestamps]}",
        )


def _assert_attachment_order(
    attachment_rows: tuple[str, ...],
    attachments_body: str,
) -> None:
    if len(attachment_rows) < 2:
        raise AssertionError(
            "Step 5 failed: the Attachments tab did not render at least two visible "
            "attachment rows, so newest-to-oldest ordering could not be verified.\n"
            f"Observed rows: {list(attachment_rows)}\n"
            f"Observed body text:\n{attachments_body}",
        )

    attachment_timestamps = [_parse_row_timestamp(row) for row in attachment_rows]
    if attachment_timestamps != sorted(attachment_timestamps, reverse=True):
        raise AssertionError(
            "Step 5 failed: the Attachments tab was not ordered from newest-to-oldest.\n"
            f"Observed rows: {list(attachment_rows)}\n"
            f"Observed timestamps: {[value.isoformat() for value in attachment_timestamps]}",
        )


def _body_fragment(text: str) -> str:
    single_line = " ".join(text.split())
    if len(single_line) <= 72:
        return single_line
    return single_line[:72].rstrip()


def _parse_row_timestamp(row: str) -> datetime:
    match = TIMESTAMP_PATTERN.search(row)
    if match is None:
        raise AssertionError(
            "The visible collaboration row did not expose an ISO-8601 timestamp needed "
            f"for ordering verification: {row!r}",
        )
    return datetime.fromisoformat(match.group(1).replace("Z", "+00:00"))


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


def _extract_failed_step_number(message: str) -> int | None:
    match = re.search(r"Step (\d+) failed", message)
    if match is None:
        return None
    return int(match.group(1))


def _ticket_step_action(step: int) -> str:
    actions = {
        1: "Open the issue detail view.",
        2: "Navigate to the 'Comments' tab and observe the list.",
        3: "Verify that the comment added first appears at the top and the newest at the bottom (AC2).",
        4: "Navigate to the 'Attachments' tab and observe the list.",
        5: "Verify that the most recently uploaded attachment appears at the top of the list (AC3).",
    }
    return actions.get(step, "Observe the live issue detail behavior.")


def _write_pass_outputs(result: dict[str, object]) -> None:
    BUG_DESCRIPTION_PATH.unlink(missing_ok=True)
    RESULT_PATH.write_text(
        json.dumps(
            {
                "status": "passed",
                "passed": 1,
                "failed": 0,
                "skipped": 0,
                "summary": "1 passed, 0 failed",
            },
        )
        + "\n",
        encoding="utf-8",
    )
    JIRA_COMMENT_PATH.write_text(_jira_comment(result, passed=True), encoding="utf-8")
    PR_BODY_PATH.write_text(_pr_body(result, passed=True), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_summary(result, passed=True), encoding="utf-8")


def _write_failure_outputs(result: dict[str, object]) -> None:
    error = str(result.get("error", "AssertionError: unknown failure"))
    RESULT_PATH.write_text(
        json.dumps(
            {
                "status": "failed",
                "passed": 0,
                "failed": 1,
                "skipped": 0,
                "summary": "0 passed, 1 failed",
                "error": error,
            },
        )
        + "\n",
        encoding="utf-8",
    )
    JIRA_COMMENT_PATH.write_text(_jira_comment(result, passed=False), encoding="utf-8")
    PR_BODY_PATH.write_text(_pr_body(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_summary(result, passed=False), encoding="utf-8")
    BUG_DESCRIPTION_PATH.write_text(_bug_description(result), encoding="utf-8")


def _jira_comment(result: dict[str, object], *, passed: bool) -> str:
    status = "PASSED" if passed else "FAILED"
    steps = _steps_lines(result, jira=True)
    human_checks = _human_lines(result, jira=True)
    screenshot_path = result.get("screenshot", FAILURE_SCREENSHOT_PATH)
    outcome = (
        "Matched the expected result: visible comment rows stayed oldest-to-newest "
        "and visible attachment rows stayed newest-to-oldest."
        if passed
        else "Did not match the expected result. The Comments order check passed, but the Attachments verification did not complete successfully."
    )
    lines = [
        f"h3. {TICKET_KEY} {status}",
        "",
        "*Automation coverage*",
        f"* Opened the live hosted issue detail for {{{{{result['issue_key']}}}}} at {{{{{result['app_url']}}}}}.",
        "* Verified the visible Comments tab order from oldest comment at the top to newest at the bottom.",
        "* Verified the visible Attachments tab outcome, including the exact user-facing failure if the list did not render.",
        "",
        "*Observed result*",
        f"* {outcome}",
        (
            f"* Environment: URL {{{{{result['app_url']}}}}}, repository "
            f"{{{{{result['repository']}}}}} @ {{{{{result['repository_ref']}}}}}, "
            f"browser {{Chromium (Playwright)}}, OS {{{{{platform.system()}}}}}."
        ),
        f"* Screenshot: {{{{{screenshot_path}}}}}",
        "",
        "*Step results*",
        *steps,
        "",
        "*Human-style verification*",
        *human_checks,
    ]
    if not passed:
        lines.extend(
            [
                "",
                "*Exact error*",
                "{code}",
                str(result.get("traceback", result.get("error", ""))),
                "{code}",
            ],
        )
    return "\n".join(lines) + "\n"


def _pr_body(result: dict[str, object], *, passed: bool) -> str:
    status = "Passed" if passed else "Failed"
    steps = _steps_lines(result, jira=False)
    human_checks = _human_lines(result, jira=False)
    screenshot_path = result.get("screenshot", FAILURE_SCREENSHOT_PATH)
    outcome = (
        "Matched the expected result: visible comment rows stayed oldest-to-newest and visible attachment rows stayed newest-to-oldest."
        if passed
        else "Did not match the expected result. The Attachments tab did not provide a sortable two-item list."
    )
    lines = [
        f"## {TICKET_KEY} {status}",
        "",
        "### Automation",
        f"- Opened the live hosted issue detail for `{result['issue_key']}` on `{result['app_url']}`.",
        "- Verified the visible `Comments` tab order from oldest comment at the top to newest at the bottom.",
        "- Verified the visible `Attachments` tab outcome, including the exact user-facing failure if the list did not render.",
        "",
        "### Observed result",
        f"- {outcome}",
        (
            f"- Environment: URL `{result['app_url']}`, repository `{result['repository']}` "
            f"@ `{result['repository_ref']}`, browser `Chromium (Playwright)`, OS `{platform.system()}`."
        ),
        f"- Screenshot: `{screenshot_path}`",
        "",
        "### Step results",
        *steps,
        "",
        "### Human-style verification",
        *human_checks,
    ]
    if not passed:
        lines.extend(
            [
                "",
                "### Exact error",
                "```text",
                str(result.get("traceback", result.get("error", ""))),
                "```",
            ],
        )
    return "\n".join(lines) + "\n"


def _response_summary(result: dict[str, object], *, passed: bool) -> str:
    status = "passed" if passed else "failed"
    screenshot_path = result.get("screenshot", FAILURE_SCREENSHOT_PATH)
    lines = [
        f"# {TICKET_KEY} {status}",
        "",
        (
            f"Opened the live `{result['issue_key']}` collaboration view and checked "
            "comment chronology plus attachment recency ordering against the deployed app."
        ),
        "",
        "## Observed",
        f"- Comments rows: {result.get('comment_rows', [])}",
        f"- Attachment rows: {result.get('attachment_rows', [])}",
        f"- Attachments error: {result.get('attachments_error_label', '<none>')}",
        f"- Screenshot: `{screenshot_path}`",
        f"- Environment: `{result['app_url']}` on Chromium/Playwright ({platform.system()})",
    ]
    if not passed:
        lines.extend(
            [
                "",
                "## Error",
                "```text",
                str(result.get("traceback", result.get("error", ""))),
                "```",
            ],
        )
    return "\n".join(lines) + "\n"


def _bug_description(result: dict[str, object]) -> str:
    lines = [
        f"# {TICKET_KEY} - Attachments ordering cannot be verified in live issue detail",
        "",
        "## Steps to reproduce",
        f"1. Open the issue detail view for `{result['issue_key']}`.",
        (
            f"   - {'✅' if _step_status(result, 1) == 'passed' else '❌'} "
            f"{_step_observation(result, 1)}"
        ),
        "2. Navigate to the `Comments` tab and observe the list.",
        (
            f"   - {'✅' if _step_status(result, 2) == 'passed' else '❌'} "
            f"{_step_observation(result, 2)}"
        ),
        "3. Verify that the comment added first appears at the top and the newest at the bottom (AC2).",
        (
            f"   - {'✅' if _step_status(result, 3) == 'passed' else '❌'} "
            f"{_step_observation(result, 3)}"
        ),
        "4. Navigate to the `Attachments` tab and observe the list.",
        (
            f"   - {'✅' if _step_status(result, 4) == 'passed' else '❌'} "
            f"{_step_observation(result, 4)}"
        ),
        "5. Verify that the most recently uploaded attachment appears at the top of the list (AC3).",
        (
            f"   - {'✅' if _step_status(result, 5) == 'passed' else '❌'} "
            f"{_step_observation(result, 5)}"
        ),
        "",
        "## Actual vs Expected",
        "- Expected: the live issue detail renders a visible two-item attachment list and orders it newest-to-oldest, with the newest file at the top.",
        (
            "- Actual: "
            + str(
                result.get("error")
                or "the Attachments tab did not render a sortable list."
            )
        ),
        "",
        "## Exact error message",
        "```text",
        str(result.get("traceback", result.get("error", ""))),
        "```",
        "",
        "## Environment",
        f"- URL: `{result['app_url']}`",
        f"- Repository: `{result['repository']}` @ `{result['repository_ref']}`",
        f"- Issue path: `{result['issue_path']}`",
        f"- Issue key: `{result['issue_key']}`",
        "- Browser: `Chromium (Playwright)`",
        f"- OS: `{platform.platform()}`",
        "",
        "## Evidence",
        f"- Screenshot: `{result.get('screenshot', FAILURE_SCREENSHOT_PATH)}`",
        f"- Visible attachment rows: `{result.get('attachment_rows', [])}`",
        f"- Visible attachment error label: `{result.get('attachments_error_label', '<none>')}`",
        "",
        "## Observed attachments body text",
        "```text",
        str(result.get("attachments_body_text", "")),
        "```",
    ]
    return "\n".join(lines) + "\n"


def _steps_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    marker = "*" if jira else "-"
    rendered: list[str] = []
    for step in result.get("steps", []):
        if not isinstance(step, dict):
            continue
        status = str(step.get("status", "")).upper()
        action = str(step.get("action", ""))
        observed = str(step.get("observed", ""))
        rendered.append(f"{marker} Step {step.get('step')}: {status} - {action}")
        rendered.append(f"{marker} Observed: {observed}")
    if not rendered and "error" in result:
        rendered.append(f"{marker} Failure before step records: {result['error']}")
    return rendered or [f"{marker} No step data was recorded."]


def _human_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    marker = "*" if jira else "-"
    rendered: list[str] = []
    for check in result.get("human_verification", []):
        if not isinstance(check, dict):
            continue
        rendered.append(f"{marker} {check.get('check')}")
        rendered.append(f"{marker} Observed: {check.get('observed')}")
    if not rendered and "comment_rows" in result:
        rendered.append(
            f"{marker} Comments remained visibly readable in chronological order before the failure on Attachments.",
        )
        rendered.append(f"{marker} Observed: {result.get('comment_rows')}")
    return rendered or [f"{marker} No human-style verification data was recorded."]


def _step_status(result: dict[str, object], step_number: int) -> str:
    for step in result.get("steps", []):
        if isinstance(step, dict) and step.get("step") == step_number:
            return str(step.get("status", "failed"))
    return "failed"


def _step_observation(result: dict[str, object], step_number: int) -> str:
    for step in result.get("steps", []):
        if isinstance(step, dict) and step.get("step") == step_number:
            return str(step.get("observed", "No observation recorded."))
    return str(result.get("error", "No observation recorded."))


if __name__ == "__main__":
    main()
