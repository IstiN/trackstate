from __future__ import annotations

import json
import platform
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_issue_detail_collaboration_page import (  # noqa: E402
    CommentComposerObservation,
    LiveIssueDetailCollaborationPage,
)
from testing.components.pages.live_multi_view_refresh_page import (  # noqa: E402
    EditSurfaceObservation,
    LiveMultiViewRefreshPage,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveHostedIssueFixture,
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.tests.support.live_tracker_app_factory import (  # noqa: E402
    create_live_tracker_app_with_stored_token,
)

TICKET_KEY = "TS-373"
ISSUE_PATH = "DEMO/DEMO-1/DEMO-2"
EXPECTED_LIMITED_TITLE = "Some attachment uploads still require local Git"
EXPECTED_LIMITED_MESSAGE = (
    "Issue edits, comments, and browser-supported attachment uploads can continue "
    "here. Files that follow the Git LFS attachment path still need to be added "
    "from a local Git runtime."
)
UNEXPECTED_READ_ONLY_FRAGMENTS = (
    "This repository session is read-only",
    "Create, edit, comment, and status changes stay read-only",
    "Attachments stay download-only in the browser",
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts373_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts373_failure.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-373 requires GH_TOKEN or GITHUB_TOKEN to open the hosted live app.",
        )

    user = service.fetch_authenticated_user()
    issue_fixture = service.fetch_issue_fixture(ISSUE_PATH)
    _assert_preconditions(issue_fixture)

    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "app_url": config.app_url,
        "repository": service.repository,
        "repository_ref": service.ref,
        "issue_key": issue_fixture.key,
        "issue_summary": issue_fixture.summary,
        "issue_path": issue_fixture.path,
        "steps": [],
        "human_verification": [],
    }

    try:
        with create_live_tracker_app_with_stored_token(
            config,
            token=token,
        ) as tracker_page:
            issue_page = LiveIssueDetailCollaborationPage(tracker_page)
            edit_page = LiveMultiViewRefreshPage(tracker_page)
            try:
                runtime = tracker_page.open()
                result["runtime_state"] = runtime.kind
                result["runtime_body_text"] = runtime.body_text
                if runtime.kind != "ready":
                    raise AssertionError(
                        "Step 1 failed: the deployed app did not reach the hosted tracker "
                        "shell before the attachment access-message scenario began.\n"
                        f"Observed body text:\n{runtime.body_text}",
                    )

                issue_page.ensure_connected(
                    token=token,
                    repository=service.repository,
                    user_login=user.login,
                )
                issue_page.dismiss_connection_banner()
                issue_page.open_issue(
                    issue_key=issue_fixture.key,
                    issue_summary=issue_fixture.summary,
                )
                issue_detail_text = issue_page.issue_detail_accessible_label(
                    issue_fixture.key,
                    expected_fragment=issue_fixture.summary,
                    timeout_ms=60_000,
                )
                result["issue_detail_text"] = issue_detail_text
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action="Navigate to the live issue detail screen.",
                    observed=issue_detail_text,
                )

                edit_dialog_text = edit_page.open_edit_dialog_from_current_issue_detail(
                    issue_key=issue_fixture.key,
                )
                edit_surface = edit_page.observe_edit_surface(
                    viewport_width=1280,
                    viewport_height=720,
                )
                result["edit_dialog_text"] = edit_dialog_text
                result["edit_surface"] = _edit_surface_payload(edit_surface)
                _assert_editing_enabled(edit_surface, issue_fixture)
                edit_page.close_edit_dialog()

                issue_page.open_collaboration_tab("Comments")
                comments_body = issue_page.wait_for_collaboration_section_to_settle(
                    "Comments",
                )
                comment_composer = issue_page.wait_for_comment_composer(timeout_ms=60_000)
                result["comments_body_text"] = comments_body
                result["comment_composer"] = _comment_composer_payload(comment_composer)
                _assert_commenting_enabled(comment_composer, comments_body)
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=(
                        "Verify field editing and commenting stay enabled for the hosted "
                        "write-capable session."
                    ),
                    observed=(
                        f"edit_dialog_opened={'Edit issue' in edit_dialog_text}; "
                        f"priority_control={edit_surface.priority_text!r}; "
                        f"comment_field_enabled={comment_composer.field_enabled}; "
                        f"post_comment_enabled={comment_composer.button_enabled}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Verified the issue detail still opened the writable Edit issue "
                        "surface, and the Comments tab showed a writable comment field "
                        "with an enabled Post comment button."
                    ),
                    observed=(
                        f"edit_dialog_text={edit_dialog_text!r}; "
                        f"priority_text={edit_surface.priority_text!r}; "
                        f"comment_field_label={comment_composer.field_label!r}; "
                        f"comment_button_label={comment_composer.button_label!r}"
                    ),
                )

                issue_page.open_collaboration_tab("Attachments")
                attachments_accessible_text = _wait_for_accessible_fragments(
                    issue_page,
                    (EXPECTED_LIMITED_TITLE, EXPECTED_LIMITED_MESSAGE),
                    timeout_ms=60_000,
                )
                attachments_body = issue_page.current_body_text()
                result["attachments_accessible_text"] = attachments_accessible_text
                result["attachments_body_text"] = attachments_body
                if issue_page.button_label_fragment_count("Choose attachment") == 0:
                    raise AssertionError(
                        "Step 3 failed: the attachment-restricted hosted session did not "
                        "keep the visible `Choose attachment` action available.\n"
                        f"Observed body text:\n{attachments_body}",
                    )
                if issue_page.button_label_fragment_count("Upload attachment") == 0:
                    raise AssertionError(
                        "Step 3 failed: the attachment-restricted hosted session did not "
                        "keep the visible `Upload attachment` action available.\n"
                        f"Observed body text:\n{attachments_body}",
                    )
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action="Open the Attachments section.",
                    observed=attachments_accessible_text,
                )

                _assert_granular_attachment_message(issue_page, attachments_body)
                _record_step(
                    result,
                    step=4,
                    status="passed",
                    action=(
                        "Verify the inline attachment message specifically describes the "
                        "upload restriction."
                    ),
                    observed=attachments_accessible_text,
                )
                _record_human_verification(
                    result,
                    check=(
                        "Verified the visible Attachments callout used attachment-specific "
                        "copy about local Git / Git LFS instead of a generic write-access "
                        "warning."
                    ),
                    observed=attachments_accessible_text,
                )

                _assert_no_read_only_implication(issue_page, attachments_body)
                _record_step(
                    result,
                    step=5,
                    status="passed",
                    action=(
                        "Verify the message does not imply that the entire repository is "
                        "read-only."
                    ),
                    observed=attachments_body,
                )
                _record_human_verification(
                    result,
                    check=(
                        "Verified the user-facing Attachments state kept upload controls on "
                        "screen and did not show any `read-only` repository warning."
                    ),
                    observed=(
                        "visible_actions=Choose attachment, Upload attachment; "
                        f"body_text={attachments_body}"
                    ),
                )

                issue_page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
                _write_pass_outputs(result)
                return
            except Exception:
                issue_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                raise
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        _write_failure_outputs(result)
        raise


def _assert_preconditions(issue_fixture: LiveHostedIssueFixture) -> None:
    if issue_fixture.key != "DEMO-2":
        raise AssertionError(
            "Precondition failed: TS-373 expected the seeded DEMO-2 issue fixture.\n"
            f"Observed issue key: {issue_fixture.key}",
        )
    if not issue_fixture.attachment_paths:
        raise AssertionError(
            "Precondition failed: TS-373 requires a seeded issue with visible attachments.\n"
            f"Issue path: {issue_fixture.path}",
        )
    if not issue_fixture.comment_paths:
        raise AssertionError(
            "Precondition failed: TS-373 requires a seeded issue with comments so the "
            "Comments tab is production-like.\n"
            f"Issue path: {issue_fixture.path}",
        )


def _assert_editing_enabled(
    edit_surface: EditSurfaceObservation,
    issue_fixture: LiveHostedIssueFixture,
) -> None:
    if "Edit issue" not in edit_surface.body_text:
        raise AssertionError(
            "Step 2 failed: opening the live Edit action did not expose the issue-editing "
            "surface.\n"
            f"Observed dialog text:\n{edit_surface.body_text}",
        )
    if not edit_surface.priority_text.strip():
        raise AssertionError(
            "Step 2 failed: opening Edit issue did not expose any writable issue-form "
            "controls in the hosted write-capable session.\n"
            f"Observed dialog text:\n{edit_surface.body_text}",
        )
    for fragment in UNEXPECTED_READ_ONLY_FRAGMENTS[:2]:
        if fragment in edit_surface.body_text:
            raise AssertionError(
                "Step 2 failed: opening Edit issue still surfaced repository-wide read-only "
                "copy even though the session should remain writable.\n"
                f"Unexpected fragment: {fragment}\n"
                f"Observed dialog text:\n{edit_surface.body_text}",
            )


def _assert_commenting_enabled(
    comment_composer: CommentComposerObservation,
    comments_body: str,
) -> None:
    if comment_composer.field_label != "Comments":
        raise AssertionError(
            "Step 2 failed: the Comments tab did not expose the expected comment text "
            "field label.\n"
            f"Observed field label: {comment_composer.field_label!r}\n"
            f"Observed body text:\n{comments_body}",
        )
    if not comment_composer.field_enabled:
        raise AssertionError(
            "Step 2 failed: the Comments composer was visible but disabled even though "
            "the hosted session has repository write access.\n"
            f"Observed body text:\n{comments_body}",
        )
    if comment_composer.button_label != "Post comment":
        raise AssertionError(
            "Step 2 failed: the Comments tab did not expose the expected `Post comment` "
            "action label.\n"
            f"Observed button label: {comment_composer.button_label!r}\n"
            f"Observed body text:\n{comments_body}",
        )
    if not comment_composer.button_enabled:
        raise AssertionError(
            "Step 2 failed: the visible `Post comment` action was disabled even though "
            "commenting should stay available in the hosted session.\n"
            f"Observed body text:\n{comments_body}",
        )


def _assert_granular_attachment_message(
    issue_page: LiveIssueDetailCollaborationPage,
    attachments_body: str,
) -> None:
    if issue_page.text_fragment_count(EXPECTED_LIMITED_TITLE) == 0:
        raise AssertionError(
            "Step 4 failed: the Attachments section did not show the granular title for "
            "limited upload capability.\n"
            f"Expected title: {EXPECTED_LIMITED_TITLE}\n"
            f"Observed body text:\n{attachments_body}",
        )
    if issue_page.text_fragment_count(EXPECTED_LIMITED_MESSAGE) == 0:
        raise AssertionError(
            "Step 4 failed: the Attachments section did not show the granular upload-"
            "restriction message for no-LFS hosted access.\n"
            f"Expected message: {EXPECTED_LIMITED_MESSAGE}\n"
            f"Observed body text:\n{attachments_body}",
        )


def _assert_no_read_only_implication(
    issue_page: LiveIssueDetailCollaborationPage,
    attachments_body: str,
) -> None:
    for fragment in UNEXPECTED_READ_ONLY_FRAGMENTS:
        if issue_page.text_fragment_count(fragment) > 0:
            raise AssertionError(
                "Step 5 failed: the attachment-restricted state still implied the entire "
                "repository was read-only instead of attachment-specific.\n"
                f"Unexpected fragment: {fragment}\n"
                f"Observed body text:\n{attachments_body}",
            )


def _wait_for_accessible_fragments(
    page: LiveIssueDetailCollaborationPage,
    fragments: tuple[str, ...],
    *,
    timeout_ms: int,
) -> str:
    labels: list[str] = []
    for fragment in fragments:
        label = page.wait_for_accessible_label_fragment(fragment, timeout_ms=timeout_ms)
        if label:
            labels.append(label)
    combined = " ".join(labels)
    normalized = _normalize_whitespace(combined)
    missing = [fragment for fragment in fragments if fragment not in normalized]
    if missing:
        raise AssertionError(
            "Expected accessible text fragments were not all visible in the Attachments "
            "section after waiting.\n"
            f"Missing fragments: {missing}\n"
            f"Observed labels:\n{combined}",
        )
    return combined


def _normalize_whitespace(value: str) -> str:
    return " ".join(value.split())


def _comment_composer_payload(
    observation: CommentComposerObservation,
) -> dict[str, object]:
    return {
        "field_label": observation.field_label,
        "field_enabled": observation.field_enabled,
        "button_label": observation.button_label,
        "button_enabled": observation.button_enabled,
    }


def _edit_surface_payload(observation: EditSurfaceObservation) -> dict[str, object]:
    return {
        "summary_value": observation.summary_value,
        "description_value": observation.description_value,
        "priority_label": observation.priority_label,
        "priority_text": observation.priority_text,
        "body_text": observation.body_text,
    }


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
    screenshot_path = result.get("screenshot", FAILURE_SCREENSHOT_PATH)
    lines = [
        f"h3. {TICKET_KEY} {status}",
        "",
        "*Automation coverage*",
        "* Opened the deployed hosted TrackState app against the live setup repository and navigated to the seeded issue detail screen.",
        "* Verified field editing remained available by opening the live Edit issue dialog and observing writable issue controls.",
        "* Verified commenting remained available by checking the visible Comments composer field and Post comment action state.",
        "* Opened the Attachments section and checked the exact user-facing limited-upload title/message.",
        "* Verified the Attachments state did not show any repository-wide read-only wording.",
        "",
        "*Observed result*",
        (
            "* Matched the expected result: attachment messaging stayed granular while edit and comment actions remained enabled."
            if passed
            else "* Did not match the expected result."
        ),
        (
            f"* Environment: URL {{{{{result['app_url']}}}}}, repository "
            f"{{{{{result['repository']}}}}} @ {{{{{result['repository_ref']}}}}}, "
            f"browser {{Chromium (Playwright)}}, OS {{{{{platform.system()}}}}}."
        ),
        f"* Screenshot: {{{{{screenshot_path}}}}}",
        "",
        "*Step results*",
        *_step_lines(result, jira=True),
        "",
        "*Human-style verification*",
        *_human_lines(result, jira=True),
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
    screenshot_path = result.get("screenshot", FAILURE_SCREENSHOT_PATH)
    lines = [
        f"## {TICKET_KEY} {status}",
        "",
        "### Automation",
        "- Opened the deployed hosted TrackState app against the live setup repository and navigated to the seeded issue detail screen.",
        "- Verified field editing remained available by opening the live Edit issue dialog and observing writable issue controls.",
        "- Verified commenting remained available by checking the visible Comments composer field and `Post comment` action state.",
        "- Opened the Attachments section and checked the exact limited-upload title/message.",
        "- Verified the Attachments state did not show any repository-wide read-only wording.",
        "",
        "### Observed result",
        (
            "- Matched the expected result: attachment messaging stayed granular while edit and comment actions remained enabled."
            if passed
            else "- Did not match the expected result."
        ),
        (
            f"- Environment: URL `{result['app_url']}`, repository `{result['repository']}` "
            f"@ `{result['repository_ref']}`, browser `Chromium (Playwright)`, OS `{platform.system()}`."
        ),
        f"- Screenshot: `{screenshot_path}`",
        "",
        "### Step results",
        *_step_lines(result, jira=False),
        "",
        "### Human-style verification",
        *_human_lines(result, jira=False),
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
        "Ran the deployed hosted issue-detail attachment access scenario with a write-capable GitHub session.",
        "",
        "## Observed",
        f"- Issue: `{result.get('issue_key', '')}`",
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
        f"# {TICKET_KEY} - Granular attachment messaging regression",
        "",
        "## Steps to reproduce",
        "1. Navigate to the live hosted issue detail screen.",
        f"   - {'✅' if _step_status(result, 1) == 'passed' else '❌'} {_step_observation(result, 1)}",
        "2. Verify field editing and commenting remain enabled/allowed.",
        f"   - {'✅' if _step_status(result, 2) == 'passed' else '❌'} {_step_observation(result, 2)}",
        "3. Open the Attachments section.",
        f"   - {'✅' if _step_status(result, 3) == 'passed' else '❌'} {_step_observation(result, 3)}",
        "4. Verify the inline message specifically addresses the upload restriction.",
        f"   - {'✅' if _step_status(result, 4) == 'passed' else '❌'} {_step_observation(result, 4)}",
        "5. Verify the message does not imply the entire repository is read-only.",
        f"   - {'✅' if _step_status(result, 5) == 'passed' else '❌'} {_step_observation(result, 5)}",
        "",
        "## Actual vs Expected",
        (
            "- Expected: the hosted issue detail keeps edit and comment actions enabled, "
            "and the Attachments panel shows `Some attachment uploads still require local Git` "
            "with attachment-specific guidance instead of any repository-wide read-only text."
        ),
        (
            "- Actual: "
            + str(
                result.get("error")
                or "the live hosted issue detail did not keep the expected granular attachment messaging.",
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
        f"- Issue: `{result.get('issue_key', '')}` (`{result.get('issue_path', '')}`)",
        "- Browser: `Chromium (Playwright)`",
        f"- OS: `{platform.platform()}`",
        "",
        "## Evidence",
        f"- Screenshot: `{result.get('screenshot', FAILURE_SCREENSHOT_PATH)}`",
        "",
        "## Observed body text",
        "```text",
        str(
            result.get("attachments_body_text")
            or result.get("comments_body_text")
            or result.get("edit_dialog_text")
            or result.get("issue_detail_text")
            or result.get("runtime_body_text", "")
        ),
        "```",
    ]
    return "\n".join(lines) + "\n"


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for step in result.get("steps", []):
        if not isinstance(step, dict):
            continue
        prefix = "#" if jira else "1."
        status = str(step.get("status", "")).upper() if jira else str(step.get("status", ""))
        lines.append(
            f"{prefix} Step {step['step']} — {step['action']} — {status}: {step['observed']}"
        )
    if not lines:
        lines.append(
            "# No step details were recorded."
            if jira
            else "1. No step details were recorded."
        )
    return lines


def _human_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for check in result.get("human_verification", []):
        if not isinstance(check, dict):
            continue
        prefix = "*" if jira else "-"
        lines.append(f"{prefix} {check['check']} Observed: {check['observed']}")
    if not lines:
        lines.append(
            "* No human-style verification was recorded."
            if jira
            else "- No human-style verification was recorded."
        )
    return lines


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
