from __future__ import annotations

import json
import platform
import re
import sys
import traceback
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_project_settings_page import (  # noqa: E402
    LiveProjectSettingsPage,
    ProjectSettingsSaveState,
)
from testing.components.services.hosted_project_settings_repository_service import (  # noqa: E402
    HostedProjectSettingsRepositoryService,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.utils.polling import poll_until  # noqa: E402
from testing.tests.support.live_startup_case_support import (  # noqa: E402
    build_annotated_steps,
    format_human_lines,
    format_step_lines,
    record_human_verification,
    record_not_reached_steps,
    record_step,
    snippet,
    write_test_automation_result,
)
from testing.tests.support.live_tracker_app_factory import (  # noqa: E402
    create_live_tracker_app_with_stored_token,
)

TICKET_KEY = "TS-1137"
TEST_CASE_TITLE = (
    "Atomic settings save with no Git commit produced — server-side guard throws error"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-1137/test_ts_1137.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
SAVE_OUTCOME_WAIT_SECONDS = 30.0
SAVE_OUTCOME_POLL_SECONDS = 1.0
LINKED_BUGS = ["TS-1148", "TS-1094", "TS-1090"]
LINKED_BUG_NOTES = (
   "Reviewed input/TS-1137/linked_bugs.md before writing the test. TS-1148 is "
   "Done and establishes that a zero-delta Settings save must surface a no-commit "
   "failure instead of a false success or unrelated Git error. TS-1094 confirms "
   "Settings writes must stay atomic, while TS-1090 confirms the shipped Settings "
   "flow already surfaces save failures for invalid catalog writes. This "
   "regression therefore drives the public zero-delta Save settings action and "
   "waits for the post-click state instead of asserting immediately."
)
REQUEST_STEPS = [
    "Navigate to the Settings Admin Workspace.",
    "Perform an action that triggers a 'Save' request but contains no changes to 'Statuses' or 'Workflows' (zero delta).",
    "Click the 'Save' button.",
    "Observe the API response and system behavior.",
]
EXPECTED_RESULT = (
    "The server-side guard throws an error indicating that no Git commit was "
    "produced; the system returns a failure response to the client instead of a "
    "false success."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
REVIEW_REPLIES_PATH = OUTPUTS_DIR / "review_replies.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1137_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1137_failure.png"
REVIEW_THREAD_REPLIES = (
    {
        "inReplyToId": 3306812201,
        "threadId": "PRRT_kwDOSU6Gf86E7LAe",
    },
    {
        "inReplyToId": None,
        "threadId": None,
    },
)


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-1137 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
        )

    user = service.fetch_authenticated_user()
    repository_service = HostedProjectSettingsRepositoryService(
        repository=config.repository,
        branch=config.ref,
        token=token,
    )
    baseline_head_sha = repository_service.branch_head_sha()

    result: dict[str, Any] = {
        "ticket": TICKET_KEY,
        "test_case_title": TEST_CASE_TITLE,
        "app_url": config.app_url,
        "repository": service.repository,
        "repository_ref": service.ref,
        "browser": "Chromium (Playwright)",
        "os": platform.platform(),
        "run_command": RUN_COMMAND,
        "expected_result": EXPECTED_RESULT,
        "desktop_viewport": DESKTOP_VIEWPORT,
        "linked_bugs": LINKED_BUGS,
        "linked_bug_notes": LINKED_BUG_NOTES,
        "baseline_head_sha": baseline_head_sha,
        "steps": [],
        "human_verification": [],
        "is_product_failure": False,
    }

    tracker_page = None
    try:
        with create_live_tracker_app_with_stored_token(config, token=token) as tracker_page:
            settings_page = LiveProjectSettingsPage(tracker_page)
            tracker_page.session.set_viewport_size(**DESKTOP_VIEWPORT)

            runtime = tracker_page.open()
            result["runtime_state"] = runtime.kind
            result["runtime_body_text"] = runtime.body_text
            if runtime.kind != "ready":
                message = (
                    "Step 1 failed: the deployed app did not reach the hosted tracker "
                    "shell before the Settings save scenario began.\n"
                    f"Observed body text:\n{runtime.body_text}"
                )
                result["is_product_failure"] = True
                record_step(
                    result,
                    step=1,
                    status="failed",
                    action=REQUEST_STEPS[0],
                    observed=message,
                )
                record_not_reached_steps(result, starting_step=2, request_steps=REQUEST_STEPS)
                raise AssertionError(message)

            connected_body = settings_page.ensure_write_capable_connection(
                token=token,
                repository=config.repository,
                user_login=user.login,
            )
            result["connected_body_text"] = connected_body
            settings_page.dismiss_connection_banner()

            settings_text = settings_page.open_settings()
            rendered_tab_labels = settings_page.rendered_tab_labels()
            result["settings_body_text"] = settings_text
            result["rendered_tab_labels"] = rendered_tab_labels
            required_labels = ("Statuses", "Workflows")
            missing_labels = [
                label for label in required_labels if label not in rendered_tab_labels
            ]
            if missing_labels:
                message = (
                    "Step 1 failed: the live Settings workspace did not render the required "
                    "Statuses and Workflows admin tabs before the zero-delta save attempt.\n"
                    f"Missing labels: {missing_labels}\n"
                    f"Observed rendered tab labels: {rendered_tab_labels}\n"
                    f"Observed body text:\n{settings_text}"
                )
                result["is_product_failure"] = True
                record_step(
                    result,
                    step=1,
                    status="failed",
                    action=REQUEST_STEPS[0],
                    observed=message,
                )
                record_not_reached_steps(result, starting_step=2, request_steps=REQUEST_STEPS)
                raise AssertionError(message)

            record_step(
                result,
                step=1,
                status="passed",
                action=REQUEST_STEPS[0],
                observed=(
                    "Opened the deployed hosted Settings workspace and confirmed the visible "
                    f"admin tabs {rendered_tab_labels!r} at viewport {DESKTOP_VIEWPORT!r}."
                ),
            )
            record_human_verification(
                result,
                check=(
                    "Viewed the live Settings screen before saving to confirm the user-facing "
                    "Project Settings surface, the administration heading, and the Statuses/"
                    "Workflows tabs were visibly present."
                ),
                observed=(
                    f"visible_tab_labels={rendered_tab_labels!r}; "
                    f"settings_body_text={snippet(settings_text)!r}"
                ),
            )

            pre_save_state = settings_page.read_save_state()
            result["pre_save_state"] = _save_state_payload(pre_save_state)
            if pre_save_state.save_failure_text is not None:
                message = (
                    "Precondition failed: the Settings screen already showed a visible save "
                    "error before the zero-delta save attempt started.\n"
                    f"Observed save error: {pre_save_state.save_failure_text}\n"
                    f"Observed body text:\n{pre_save_state.body_text}"
                )
                record_step(
                    result,
                    step=2,
                    status="failed",
                    action=REQUEST_STEPS[1],
                    observed=message,
                )
                record_not_reached_steps(result, starting_step=3, request_steps=REQUEST_STEPS)
                raise AssertionError(message)
            if not pre_save_state.save_button_enabled:
                message = (
                    "Step 2 failed: the untouched zero-delta Settings surface did not expose "
                    "an enabled Save settings action, so the test could not prove that a real "
                    "save request would be sent to the server-side no-commit guard.\n"
                    f"Baseline head: {baseline_head_sha}\n"
                    f"Observed body text:\n{pre_save_state.body_text}"
                )
                result["is_product_failure"] = True
                record_step(
                    result,
                    step=2,
                    status="failed",
                    action=REQUEST_STEPS[1],
                    observed=message,
                )
                record_not_reached_steps(result, starting_step=3, request_steps=REQUEST_STEPS)
                raise AssertionError(message)
            record_step(
                result,
                step=2,
                status="passed",
                action=REQUEST_STEPS[1],
                observed=(
                    "Kept the live Settings draft unchanged on the default Statuses view, so "
                    "clicking Save settings exercised a zero-delta persistence attempt "
                    "through the public UI. "
                    f"baseline_head_sha={baseline_head_sha}; "
                    f"save_button_enabled={pre_save_state.save_button_enabled!r}; "
                    f"visible_body_text={snippet(pre_save_state.body_text)!r}"
                ),
            )
            record_human_verification(
                result,
                check=(
                    "Watched the untouched live Settings screen before saving to confirm "
                    "the default Statuses view still exposed an enabled Save settings "
                    "control for the zero-delta request."
                ),
                observed=(
                    f"save_button_enabled={pre_save_state.save_button_enabled!r}; "
                    f"body_text={snippet(pre_save_state.body_text)!r}"
                ),
            )

            after_click_body = settings_page.click_save_settings()
            result["after_click_body_text"] = after_click_body
            settings_page.wait_for_save_cycle_completion()
            post_click_settle_state = settings_page.read_save_state()
            result["post_click_settle_state"] = _save_state_payload(post_click_settle_state)
            record_step(
                result,
                step=3,
                status="passed",
                action=REQUEST_STEPS[2],
                observed=(
                    "Clicked the visible Save settings action without editing the catalogs and "
                    "waited for the save control to become enabled again. "
                    f"post_click_save_button_enabled={post_click_settle_state.save_button_enabled!r}; "
                    f"post_click_visible_error={post_click_settle_state.save_failure_text!r}"
                ),
            )

            observed_failure, final_outcome = poll_until(
                probe=lambda: _observe_save_outcome(settings_page, repository_service),
                is_satisfied=lambda snapshot: snapshot["save_failure_text"] is not None,
                timeout_seconds=SAVE_OUTCOME_WAIT_SECONDS,
                interval_seconds=SAVE_OUTCOME_POLL_SECONDS,
            )
            result["final_outcome"] = final_outcome

            record_human_verification(
                result,
                check=(
                    "Watched the live Settings page after clicking Save without edits to see "
                    "whether a user-visible save failure appeared while the hosted repository "
                    "stayed on the same branch head."
                ),
                observed=(
                    f"observed_failure={observed_failure!r}; "
                    f"save_failure_text={final_outcome['save_failure_text']!r}; "
                    f"head_changed={final_outcome['head_changed']!r}; "
                    f"body_text={snippet(str(final_outcome['body_text']), limit=320)!r}"
                ),
            )

            step_four_error = _evaluate_final_outcome(
                baseline_head_sha=baseline_head_sha,
                final_outcome=final_outcome,
            )
            if step_four_error is not None:
                record_step(
                    result,
                    step=4,
                    status="failed",
                    action=REQUEST_STEPS[3],
                    observed=step_four_error,
                )
                result["error"] = step_four_error
                result["is_product_failure"] = True
                tracker_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                raise AssertionError(step_four_error)

            record_step(
                result,
                step=4,
                status="passed",
                action=REQUEST_STEPS[3],
                observed=(
                    "The live no-op save surfaced the expected failure response and did not "
                    "change the hosted repository head. "
                    f"save_failure_text={final_outcome['save_failure_text']!r}; "
                    f"final_head_sha={final_outcome['head_sha']!r}"
                ),
            )
            tracker_page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
            result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
            _write_pass_outputs(result)
            print(f"{TICKET_KEY} passed")
    except AssertionError as error:
        result["error"] = str(result.get("error", str(error)))
        result["traceback"] = traceback.format_exc()
        if tracker_page is not None and "screenshot" not in result:
            try:
                tracker_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
            except Exception as screenshot_error:  # pragma: no cover - diagnostics only
                result["screenshot_error"] = (
                    f"{type(screenshot_error).__name__}: {screenshot_error}"
                )
        _write_failure_outputs(result)
        raise
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        result["is_product_failure"] = False
        if tracker_page is not None:
            try:
                tracker_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
            except Exception as screenshot_error:  # pragma: no cover - diagnostics only
                result["screenshot_error"] = (
                    f"{type(screenshot_error).__name__}: {screenshot_error}"
                )
        _write_failure_outputs(result)
        raise


def _observe_save_outcome(
    settings_page: LiveProjectSettingsPage,
    repository_service: HostedProjectSettingsRepositoryService,
) -> dict[str, Any]:
    save_state = settings_page.read_save_state()
    head_sha = repository_service.branch_head_sha()
    return {
        "body_text": save_state.body_text,
        "save_button_enabled": save_state.save_button_enabled,
        "save_failure_text": save_state.save_failure_text,
        "head_sha": head_sha,
        "head_changed": False,
    }


def _evaluate_final_outcome(
    *,
    baseline_head_sha: str,
    final_outcome: dict[str, Any],
) -> str | None:
    head_sha = str(final_outcome.get("head_sha", ""))
    head_changed = bool(head_sha and head_sha != baseline_head_sha)
    final_outcome["head_changed"] = head_changed
    save_failure_text = final_outcome.get("save_failure_text")
    body_text = str(final_outcome.get("body_text", ""))

    if head_changed:
        return (
            "Step 4 failed: the zero-delta Settings save changed the hosted repository "
            "head instead of rejecting the save because no new Git commit should be "
            "produced.\n"
            f"Baseline head: {baseline_head_sha}\n"
            f"Observed head: {head_sha}\n"
            f"Observed save failure text: {save_failure_text!r}\n"
            f"Observed body text:\n{body_text}"
        )

    if save_failure_text is None:
        return (
            "Step 4 failed: clicking Save settings with no Statuses or Workflows changes "
            "did not surface any visible failure response even though the hosted "
            "repository head stayed unchanged.\n"
            f"Baseline head: {baseline_head_sha}\n"
            f"Observed head: {head_sha}\n"
            "Expected a visible save failure that explains no Git commit was produced, "
            "but the UI stayed on the Settings surface without that message.\n"
            f"Observed body text:\n{body_text}"
        )

    if not _looks_like_no_commit_error(save_failure_text):
        return (
            "Step 4 failed: the client received a visible save failure, but the message "
            "did not indicate that no Git commit was produced for the zero-delta save.\n"
            f"Observed save failure text: {save_failure_text}\n"
            f"Observed body text:\n{body_text}"
        )

    return None


def _looks_like_no_commit_error(message: str) -> bool:
    normalized = " ".join(message.lower().split())
    patterns = (
        r"no git commit",
        r"no commit was produced",
        r"did not produce .*commit",
        r"no .* commit .* produced",
        r"commit .* not produced",
    )
    return any(re.search(pattern, normalized) for pattern in patterns)


def _save_state_payload(save_state: ProjectSettingsSaveState) -> dict[str, Any]:
    return {
        "body_text": save_state.body_text,
        "save_button_enabled": save_state.save_button_enabled,
        "save_failure_text": save_state.save_failure_text,
    }


def _write_pass_outputs(result: dict[str, Any]) -> None:
    BUG_DESCRIPTION_PATH.unlink(missing_ok=True)
    write_test_automation_result(RESULT_PATH, passed=True)
    JIRA_COMMENT_PATH.write_text(_build_jira_comment(result, passed=True), encoding="utf-8")
    PR_BODY_PATH.write_text(_build_pr_body(result, passed=True), encoding="utf-8")
    RESPONSE_PATH.write_text(_build_response_summary(result, passed=True), encoding="utf-8")
    REVIEW_REPLIES_PATH.write_text(_build_review_replies(result, passed=True), encoding="utf-8")


def _write_failure_outputs(result: dict[str, Any]) -> None:
    error = str(result.get("error", f"AssertionError: {TICKET_KEY} failed"))
    write_test_automation_result(RESULT_PATH, passed=False, error=error)
    if result.get("is_product_failure"):
        BUG_DESCRIPTION_PATH.write_text(_build_bug_description(result), encoding="utf-8")
    else:
        BUG_DESCRIPTION_PATH.unlink(missing_ok=True)
    JIRA_COMMENT_PATH.write_text(_build_jira_comment(result, passed=False), encoding="utf-8")
    PR_BODY_PATH.write_text(_build_pr_body(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_build_response_summary(result, passed=False), encoding="utf-8")
    REVIEW_REPLIES_PATH.write_text(
        _build_review_replies(result, passed=False),
        encoding="utf-8",
    )


def _build_jira_comment(result: dict[str, Any], *, passed: bool) -> str:
    status_icon = "✅" if passed else "❌"
    status_word = "PASSED" if passed else "FAILED"
    lines = [
        f"h3. {status_icon} Automated test {status_word} — {TICKET_KEY}",
        "",
        f"*Test case*: {TEST_CASE_TITLE}",
        f"*Environment*: {result.get('app_url')} | Chromium (Playwright) | {result.get('os')}",
        f"*Repository*: {result.get('repository')}@{result.get('repository_ref')}",
        f"*Viewport*: {json.dumps(result.get('desktop_viewport', {}), ensure_ascii=True)}",
        f"*Linked bugs reviewed*: {', '.join(LINKED_BUGS)}",
        f"*Expected result*: {EXPECTED_RESULT}",
        "",
        "*Automation checks*:",
        *format_step_lines(result, jira=True),
        "",
        "*Human-style verification*:",
        *format_human_lines(result, jira=True),
        "",
        "*Observed outcome*: "
        + (
            "The live Settings flow rejected the zero-delta save with a visible no-commit error."
            if passed
            else "The live Settings flow did not satisfy the expected no-commit failure behavior."
        ),
        f"*Screenshot*: {result.get('screenshot', '<none>')}",
    ]
    if not passed:
        lines.extend(
            [
                "",
                "*Failure detail*:",
                f"{{code}}{result.get('error', '')}{{code}}",
            ]
        )
    return "\n".join(lines) + "\n"


def _build_pr_body(result: dict[str, Any], *, passed: bool) -> str:
    status_icon = "✅" if passed else "❌"
    status_word = "PASSED" if passed else "FAILED"
    lines = [
        f"## {status_icon} {TICKET_KEY} {status_word}",
        "",
        f"**Test case:** {TEST_CASE_TITLE}",
        f"**Environment:** {result.get('app_url')} | Chromium (Playwright) | {result.get('os')}",
        f"**Repository:** `{result.get('repository')}@{result.get('repository_ref')}`",
        f"**Viewport:** `{json.dumps(result.get('desktop_viewport', {}), ensure_ascii=True)}`",
        f"**Expected result:** {EXPECTED_RESULT}",
        "",
        "### Automation checks",
        *format_step_lines(result, jira=False),
        "",
        "### Human-style verification",
        *format_human_lines(result, jira=False),
        "",
        f"**Screenshot:** `{result.get('screenshot', '<none>')}`",
    ]
    if not passed:
        lines.extend(["", "### Failure detail", f"```text\n{result.get('error', '')}\n```"])
    return "\n".join(lines) + "\n"


def _build_response_summary(result: dict[str, Any], *, passed: bool) -> str:
    status_word = "passed" if passed else "failed"
    lines = [
        f"## {TICKET_KEY} {status_word}",
        "",
        f"- Test case: **{TEST_CASE_TITLE}**",
        f"- Environment: `{result.get('app_url')}` | Chromium (Playwright) | `{result.get('os')}`",
        f"- Repository: `{result.get('repository')}@{result.get('repository_ref')}`",
        "",
        "### Steps",
        *format_step_lines(result, jira=False),
        "",
        "### Human verification",
        *format_human_lines(result, jira=False),
    ]
    if not passed:
        lines.extend(["", "### Failure detail", f"```text\n{result.get('error', '')}\n```"])
    return "\n".join(lines) + "\n"


def _build_bug_description(result: dict[str, Any]) -> str:
    final_outcome = result.get("final_outcome", {})
    if not isinstance(final_outcome, dict):
        final_outcome = {}
    body_text = str(final_outcome.get("body_text", ""))
    save_failure_text = final_outcome.get("save_failure_text")
    baseline_head = result.get("baseline_head_sha")
    observed_head = final_outcome.get("head_sha")
    steps = build_annotated_steps(result, request_steps=REQUEST_STEPS)
    lines = [
        f"# {TICKET_KEY} — zero-delta Settings save does not return the expected no-commit failure",
        "",
        "## Steps to reproduce",
        *steps,
        "",
        "## Actual vs Expected",
        f"- **Expected:** {EXPECTED_RESULT}",
        (
            "- **Actual:** Clicking **Save settings** without changing the Statuses or "
            "Workflows catalogs left the hosted repository on the same head commit "
            f"(`{baseline_head}` -> `{observed_head}`) but did not surface a visible "
            "save failure that explained no Git commit was produced."
            if save_failure_text is None
            else "- **Actual:** The live Settings UI did show a save failure, but the "
            "message did not state that no Git commit was produced.\n"
            f"  Observed message: `{save_failure_text}`"
        ),
        "",
        "## Exact assertion failure / stack trace",
        "```text",
        str(result.get("traceback", result.get("error", ""))),
        "```",
        "",
        "## Environment",
        f"- URL: {result.get('app_url')}",
        f"- Browser: Chromium (Playwright)",
        f"- OS: {result.get('os')}",
        f"- Repository: {result.get('repository')}@{result.get('repository_ref')}",
        f"- Viewport: {json.dumps(result.get('desktop_viewport', {}), ensure_ascii=True)}",
        "",
        "## Visible UI / logs at failure",
        f"- Screenshot: {result.get('screenshot', '<none>')}",
        f"- Save failure text: {save_failure_text!r}",
        f"- Baseline head SHA: {baseline_head}",
        f"- Observed head SHA after save: {observed_head}",
        "```text",
        body_text,
        "```",
    ]
    return "\n".join(lines) + "\n"


def _build_review_replies(result: dict[str, Any], *, passed: bool) -> str:
    if passed:
        reply = (
            "Fixed: resolved the TS-1137 merge conflicts, kept the public zero-delta "
            "Save settings path, and now fail the scenario before Step 3 unless the "
            "visible Save settings control is enabled so the run only proceeds when a "
            "real save request can be sent. Reran the automation with the updated flow."
        )
    else:
        reply = (
            "Fixed: resolved the TS-1137 merge conflicts, kept the public zero-delta "
            "Save settings path, and now fail the scenario before Step 3 unless the "
            "visible Save settings control is enabled so the run only proceeds when a "
            "real save request can be sent. Reran the automation; the remaining failure "
            f"is product-visible: {result.get('error', 'see attached failure output')}."
        )
    return json.dumps(
        {
            "replies": [
                {
                    "inReplyToId": thread["inReplyToId"],
                    "threadId": thread["threadId"],
                    "reply": reply,
                }
                for thread in REVIEW_THREAD_REPLIES
            ],
        }
    ) + "\n"


if __name__ == "__main__":
    main()
