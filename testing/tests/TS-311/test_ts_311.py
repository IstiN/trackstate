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
    LiveIssueDetailCollaborationPage,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.interfaces.web_app_session import WebAppTimeoutError  # noqa: E402
from testing.tests.support.live_tracker_app_factory import (  # noqa: E402
    create_live_tracker_app_with_stored_token,
)

TICKET_KEY = "TS-311"
TICKET_SUMMARY = (
    "Issue detail tab navigation — collaboration surfaces gated by capability"
)
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts311_failure.png"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts311_success.png"
TEST_FILE_PATH = "testing/tests/TS-311/test_ts_311.py"
RUN_COMMAND = "python testing/tests/TS-311/test_ts_311.py"

ISSUE_PATH = "DEMO/DEMO-1/DEMO-2"
DOWNLOAD_ONLY_MESSAGE = "This repository session is download-only for Git LFS attachments."
UPLOAD_CONTROL_FRAGMENTS = (
    "Upload",
    "Choose attachment",
    "Choose file",
    "Select file",
    "Add attachment",
)


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_live_setup_test_config()
    repository_service = LiveSetupRepositoryService(config=config)
    token = repository_service.token
    if not token:
        raise RuntimeError(
            "TS-311 requires GH_TOKEN or GITHUB_TOKEN to open the hosted live app.",
        )

    user = repository_service.fetch_authenticated_user()
    issue_fixture = repository_service.fetch_issue_fixture(ISSUE_PATH)
    _assert_preconditions(issue_fixture)

    comment_body = issue_fixture.comment_bodies[0].strip()
    attachment_name = Path(issue_fixture.attachment_paths[0]).name
    expected_download_label = f"Download {attachment_name}"

    result: dict[str, object] = {
        "status": "failed",
        "ticket": TICKET_KEY,
        "ticket_summary": TICKET_SUMMARY,
        "app_url": config.app_url,
        "repository": repository_service.repository,
        "repository_ref": repository_service.ref,
        "issue_key": issue_fixture.key,
        "issue_summary": issue_fixture.summary,
        "os": platform.system(),
        "browser": "Chromium",
        "run_command": RUN_COMMAND,
        "test_file": TEST_FILE_PATH,
        "comment_body": comment_body,
        "attachment_name": attachment_name,
        "expected_download_label": expected_download_label,
        "upload_control_fragments": list(UPLOAD_CONTROL_FRAGMENTS),
        "steps": [],
        "human_verification": [],
        "tab_counts": {},
        "tab_observations": {},
    }
    failures: list[str] = []

    try:
        with create_live_tracker_app_with_stored_token(
            config,
            token=token,
        ) as tracker_page:
            live_issue_page = LiveIssueDetailCollaborationPage(tracker_page)
            try:
                runtime = tracker_page.open()
                result["runtime_state"] = runtime.kind
                result["runtime_body_text"] = runtime.body_text
                if runtime.kind != "ready":
                    raise AssertionError(
                        "Step 1 failed: the deployed app did not reach the hosted tracker "
                        "shell before the collaboration-tab scenario began.\n"
                        f"Observed body text:\n{runtime.body_text}",
                    )
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action="Open the live app and reach the hosted tracker shell.",
                    observed=runtime.body_text,
                )
                _record_human_verification(
                    result,
                    check=(
                        "Opened the deployed hosted TrackState app in Chromium and "
                        "verified the tracker shell was visibly ready before starting "
                        "the collaboration-tab scenario."
                    ),
                    observed=runtime.body_text,
                )

                live_issue_page.ensure_connected(
                    token=token,
                    repository=repository_service.repository,
                    user_login=user.login,
                )
                live_issue_page.open_issue(
                    issue_key=issue_fixture.key,
                    issue_summary=issue_fixture.summary,
                )
                issue_detail_text = live_issue_page.current_body_text()
                result["initial_issue_detail_text"] = issue_detail_text
                if live_issue_page.issue_detail_count(issue_fixture.key) <= 0:
                    raise AssertionError(
                        "Step 1 failed: the hosted app did not open the requested issue "
                        f"detail for {issue_fixture.key}.\n"
                        f"Observed body text:\n{issue_detail_text}",
                    )

                tab_counts = {
                    "Detail": live_issue_page.tab_button_count("Detail"),
                    "Comments": live_issue_page.tab_button_count("Comments"),
                    "Attachments": live_issue_page.tab_button_count("Attachments"),
                    "History": live_issue_page.tab_button_count("History"),
                }
                result["tab_counts"] = tab_counts

                if live_issue_page.selected_tab_count("Detail") <= 0:
                    failures.append(
                        "Step 2 failed: the issue detail did not open on the dedicated "
                        '"Detail" tab before collaboration navigation began.\n'
                        f"Observed body text:\n{issue_detail_text}",
                    )
                for label, count in tab_counts.items():
                    if count <= 0:
                        failures.append(
                            f'Step 2 failed: the issue detail did not expose a dedicated "{label}" '
                            "tab button in the hosted session.\n"
                            f"Observed body text:\n{issue_detail_text}",
                        )
                if comment_body in issue_detail_text:
                    failures.append(
                        "Step 2 failed: the seeded comment body was already visible on the "
                        'initial issue-detail surface instead of being gated by the "Comments" tab.\n'
                        f"Unexpected text: {comment_body}\n"
                        f"Observed body text:\n{issue_detail_text}",
                    )
                if attachment_name in issue_detail_text:
                    failures.append(
                        "Step 2 failed: the seeded attachment name was already visible on the "
                        'initial issue-detail surface instead of being gated by the "Attachments" tab.\n'
                        f"Unexpected text: {attachment_name}\n"
                        f"Observed body text:\n{issue_detail_text}",
                    )
                if DOWNLOAD_ONLY_MESSAGE in issue_detail_text:
                    failures.append(
                        "Step 2 failed: the attachment read-only guidance was already visible "
                        'before the "Attachments" tab was opened.\n'
                        f"Unexpected text: {DOWNLOAD_ONLY_MESSAGE}\n"
                        f"Observed body text:\n{issue_detail_text}",
                    )
                _record_step(
                    result,
                    step=2,
                    status="passed" if not failures else "failed",
                    action=(
                        "Open the seeded issue detail and verify collaboration data stays "
                        "behind dedicated tabs before navigation."
                    ),
                    observed=issue_detail_text,
                )
                _record_human_verification(
                    result,
                    check=(
                        "Opened DEMO-2 from the hosted session and checked the visible "
                        "issue-detail surface before switching tabs."
                    ),
                    observed=issue_detail_text,
                )

                if tab_counts["Comments"] > 0:
                    _exercise_comments_tab(
                        live_issue_page=live_issue_page,
                        comment_body=comment_body,
                        attachment_name=attachment_name,
                        result=result,
                        failures=failures,
                    )
                if tab_counts["History"] > 0:
                    _exercise_history_tab(
                        live_issue_page=live_issue_page,
                        comment_body=comment_body,
                        attachment_name=attachment_name,
                        result=result,
                        failures=failures,
                    )
                if tab_counts["Attachments"] > 0:
                    _exercise_attachments_tab(
                        live_issue_page=live_issue_page,
                        attachment_name=attachment_name,
                        expected_download_label=expected_download_label,
                        result=result,
                        failures=failures,
                    )

                screenshot_path = SUCCESS_SCREENSHOT_PATH if not failures else FAILURE_SCREENSHOT_PATH
                live_issue_page.screenshot(str(screenshot_path))
                result["screenshot"] = str(screenshot_path)
            except Exception:
                live_issue_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                raise
    except AssertionError as error:
        result["error"] = str(error)
        result["traceback"] = traceback.format_exc()
        _write_failure_outputs(result, product_failure=True)
        print(json.dumps(result, indent=2))
        raise
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        _write_failure_outputs(result, product_failure=False)
        print(json.dumps(result, indent=2))
        raise
    else:
        if failures:
            error_message = "\n\n".join(failures)
            result["error"] = error_message
            result["traceback"] = "".join(
                traceback.format_exception(
                    AssertionError,
                    AssertionError(error_message),
                    None,
                )
            )
            result["summary"] = (
                "Observed the live hosted collaboration-tab flow, but at least one "
                "tab-gating or attachment-capability expectation did not match TS-311."
            )
            _write_failure_outputs(result, product_failure=True)
            print(json.dumps(result, indent=2))
            raise AssertionError(error_message)

        result["status"] = "passed"
        result["summary"] = (
            "Verified in the live hosted tracker that issue-detail collaboration data "
            "is tab-gated and the Attachments tab is download-only for the seeded "
            "Git LFS attachment."
        )
        _write_pass_outputs(result)
        print(json.dumps(result, indent=2))


def _exercise_comments_tab(
    *,
    live_issue_page: LiveIssueDetailCollaborationPage,
    comment_body: str,
    attachment_name: str,
    result: dict[str, object],
    failures: list[str],
) -> None:
    starting_failures = len(failures)
    try:
        live_issue_page.open_collaboration_tab("Comments")
        live_issue_page.wait_for_selected_tab("Comments", timeout_ms=30_000)
        live_issue_page.wait_for_text(comment_body, timeout_ms=30_000)
    except WebAppTimeoutError as error:
        failures.append(
            "Step 3 failed: the visible Comments tab did not become the active "
            "collaboration view with the seeded comment content.\n"
            f"Observed body text:\n{live_issue_page.current_body_text()}",
        )
        result["tab_observations"] = {
            **_tab_observations(result),
            "Comments": {
                "selected": live_issue_page.selected_tab_count("Comments"),
                "body_text": live_issue_page.current_body_text(),
            },
        }
        return

    comments_text = live_issue_page.current_body_text()
    _tab_observations(result)["Comments"] = {
        "selected": live_issue_page.selected_tab_count("Comments"),
        "body_text": comments_text,
    }
    if live_issue_page.selected_tab_count("Comments") <= 0:
        failures.append(
            "Step 3 failed: the Comments tab was visible but did not stay selected "
            "after it was opened.\n"
            f"Observed body text:\n{comments_text}",
        )
    if comment_body not in comments_text:
        failures.append(
            "Step 3 failed: opening the Comments tab did not render the seeded "
            "comment body for the user.\n"
            f"Expected comment text: {comment_body}\n"
            f"Observed body text:\n{comments_text}",
        )
    if attachment_name in comments_text:
        failures.append(
            "Step 3 failed: the seeded attachment content became visible in the "
            '"Comments" tab before the user opened "Attachments".\n'
            f"Unexpected text: {attachment_name}\n"
            f"Observed body text:\n{comments_text}",
        )
    _record_step(
        result,
        step=3,
        status="passed" if len(failures) == starting_failures else "failed",
        action="Open the Comments tab and verify the seeded comment becomes visible.",
        observed=comments_text,
    )
    _record_human_verification(
        result,
        check=(
            "Switched to the Comments tab and verified the seeded comment became "
            "visible there rather than on the default detail surface."
        ),
        observed=comments_text,
    )


def _exercise_history_tab(
    *,
    live_issue_page: LiveIssueDetailCollaborationPage,
    comment_body: str,
    attachment_name: str,
    result: dict[str, object],
    failures: list[str],
) -> None:
    starting_failures = len(failures)
    try:
        live_issue_page.open_collaboration_tab("History")
        live_issue_page.wait_for_selected_tab("History", timeout_ms=30_000)
    except WebAppTimeoutError:
        failures.append(
            "Step 4 failed: the visible History tab did not become the active "
            "collaboration view after it was opened.\n"
            f"Observed body text:\n{live_issue_page.current_body_text()}",
        )
        _tab_observations(result)["History"] = {
            "selected": live_issue_page.selected_tab_count("History"),
            "body_text": live_issue_page.current_body_text(),
        }
        return

    history_text = live_issue_page.current_body_text()
    _tab_observations(result)["History"] = {
        "selected": live_issue_page.selected_tab_count("History"),
        "body_text": history_text,
    }
    if live_issue_page.selected_tab_count("History") <= 0:
        failures.append(
            "Step 4 failed: the History tab was visible but did not stay selected "
            "after it was opened.\n"
            f"Observed body text:\n{history_text}",
        )
    if comment_body in history_text:
        failures.append(
            "Step 4 failed: the seeded comment body was still visible after switching "
            'away from "Comments" to "History", so tab navigation did not fully gate '
            "the collaboration panels.\n"
            f"Unexpected text: {comment_body}\n"
            f"Observed body text:\n{history_text}",
        )
    if attachment_name in history_text:
        failures.append(
            "Step 4 failed: the seeded attachment content became visible before the "
            '"Attachments" tab was opened.\n'
            f"Unexpected text: {attachment_name}\n"
            f"Observed body text:\n{history_text}",
        )
    _record_step(
        result,
        step=4,
        status="passed" if len(failures) == starting_failures else "failed",
        action=(
            "Open the History tab and verify the issue detail switches away from "
            "Comments without revealing attachment content."
        ),
        observed=history_text,
    )
    _record_human_verification(
        result,
        check=(
            "Switched to the History tab and confirmed the visible surface changed "
            "away from Comments without exposing attachment content early."
        ),
        observed=history_text,
    )


def _exercise_attachments_tab(
    *,
    live_issue_page: LiveIssueDetailCollaborationPage,
    attachment_name: str,
    expected_download_label: str,
    result: dict[str, object],
    failures: list[str],
) -> None:
    starting_failures = len(failures)
    try:
        live_issue_page.open_collaboration_tab("Attachments")
        live_issue_page.wait_for_selected_tab("Attachments", timeout_ms=30_000)
        live_issue_page.wait_for_text(attachment_name, timeout_ms=30_000)
    except WebAppTimeoutError:
        failures.append(
            "Step 5 failed: the visible Attachments tab did not become the active "
            "collaboration view with the seeded attachment row.\n"
            f"Observed body text:\n{live_issue_page.current_body_text()}",
        )
        _tab_observations(result)["Attachments"] = {
            "selected": live_issue_page.selected_tab_count("Attachments"),
            "body_text": live_issue_page.current_body_text(),
        }
        return

    attachments_text = live_issue_page.current_body_text()
    upload_controls = live_issue_page.observe_attachment_upload_controls()
    upload_button_counts = {
        fragment: live_issue_page.visible_button_label_fragment_count(fragment)
        for fragment in UPLOAD_CONTROL_FRAGMENTS
    }
    upload_button_disabled_counts = {
        fragment: live_issue_page.button_label_fragment_disabled_count(fragment)
        for fragment in UPLOAD_CONTROL_FRAGMENTS
    }
    upload_button_enabled_counts = {
        fragment: max(
            0,
            upload_button_counts[fragment] - upload_button_disabled_counts[fragment],
        )
        for fragment in UPLOAD_CONTROL_FRAGMENTS
    }
    attachments_observation = {
        "selected": live_issue_page.selected_tab_count("Attachments"),
        "body_text": attachments_text,
        "download_only_message_count": live_issue_page.text_fragment_count(
            DOWNLOAD_ONLY_MESSAGE,
        ),
        "download_button_count": live_issue_page.attachment_download_button_count(
            attachment_name,
        ),
        "download_button_disabled_count": live_issue_page.button_label_fragment_disabled_count(
            "Download",
        ),
        "upload_controls": {
            "choose_button_count": upload_controls.choose_button_count,
            "choose_button_enabled": upload_controls.choose_button_enabled,
            "upload_button_count": upload_controls.upload_button_count,
            "upload_button_enabled": upload_controls.upload_button_enabled,
        },
        "upload_button_counts": upload_button_counts,
        "upload_button_disabled_counts": upload_button_disabled_counts,
        "upload_button_enabled_counts": upload_button_enabled_counts,
        "visible_file_input_count": live_issue_page.visible_file_input_count(),
    }
    _tab_observations(result)["Attachments"] = attachments_observation

    if attachments_observation["selected"] <= 0:
        failures.append(
            "Step 5 failed: the Attachments tab was visible but did not stay selected "
            "after it was opened.\n"
            f"Observed body text:\n{attachments_text}",
        )
    if attachment_name not in attachments_text:
        failures.append(
            "Step 5 failed: opening the Attachments tab did not render the seeded "
            "attachment row for the user.\n"
            f"Expected attachment: {attachment_name}\n"
            f"Observed body text:\n{attachments_text}",
        )
    if DOWNLOAD_ONLY_MESSAGE not in attachments_text:
        failures.append(
            "Step 5 failed: the hosted Attachments tab did not show the explicit "
            "download-only guidance for Git LFS attachments.\n"
            f"Expected message: {DOWNLOAD_ONLY_MESSAGE}\n"
            f"Observed body text:\n{attachments_text}",
        )
    if attachments_observation["download_button_count"] <= 0:
        failures.append(
            "Step 5 failed: the hosted Attachments tab did not keep a visible "
            "download action for the seeded attachment.\n"
            f"Expected label: {expected_download_label}\n"
            f"Observed body text:\n{attachments_text}",
        )
    else:
        visible_download_label = live_issue_page.attachment_download_button_label(
            attachment_name,
        )
        attachments_observation["visible_download_label"] = visible_download_label
        if visible_download_label != expected_download_label:
            failures.append(
                "Step 5 failed: the attachment download action did not expose the "
                "expected user-facing label.\n"
                f"Expected label: {expected_download_label}\n"
                f"Observed label: {visible_download_label}",
            )
    if attachments_observation["download_button_disabled_count"] > 0:
        failures.append(
            "Step 5 failed: the download action appeared disabled even though TS-311 "
            "requires download to remain available for LFS-backed attachments.\n"
            f"Observed body text:\n{attachments_text}",
        )
    upload_controls_usable = (
        upload_controls.choose_button_enabled or upload_controls.upload_button_enabled
    )
    if (
        attachments_observation["visible_file_input_count"] > 0
        or upload_controls_usable
        or any(count > 0 for count in upload_button_enabled_counts.values())
    ):
        failures.append(
            "Step 5 failed: the hosted Attachments tab still exposed a usable upload "
            "path instead of a download-only experience for Git LFS attachments.\n"
            f"Observed upload controls: {attachments_observation['upload_controls']}\n"
            f"Visible upload button counts: {upload_button_counts}\n"
            f"Disabled upload button counts: {upload_button_disabled_counts}\n"
            f"Enabled upload button counts: {upload_button_enabled_counts}\n"
            f"Visible file input count: {attachments_observation['visible_file_input_count']}\n"
            f"Observed body text:\n{attachments_text}",
        )
    _record_step(
        result,
        step=5,
        status="passed" if len(failures) == starting_failures else "failed",
        action=(
            "Open the Attachments tab and verify download-only guidance, no usable "
            "upload path, and an available download action for the seeded attachment."
        ),
        observed=attachments_text,
    )
    _record_human_verification(
        result,
        check=(
            "Viewed the Attachments tab as a user and checked the visible upload and "
            "download actions plus the download-only guidance."
        ),
        observed=attachments_text,
    )


def _assert_preconditions(issue_fixture) -> None:
    if issue_fixture.key != "DEMO-2":
        raise AssertionError(
            "Precondition failed: TS-311 expected the seeded DEMO-2 fixture.\n"
            f"Observed issue key: {issue_fixture.key}",
        )
    if not issue_fixture.attachment_paths:
        raise AssertionError(
            "Precondition failed: DEMO-2 does not contain any seeded attachments in "
            f"{issue_fixture.path}.",
        )
    if not issue_fixture.comment_bodies:
        raise AssertionError(
            "Precondition failed: DEMO-2 does not contain any seeded comments in "
            f"{issue_fixture.path}.",
        )


def _tab_observations(result: dict[str, object]) -> dict[str, object]:
    tab_observations = result.setdefault("tab_observations", {})
    assert isinstance(tab_observations, dict)
    return tab_observations


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
    human_verification = result.setdefault("human_verification", [])
    assert isinstance(human_verification, list)
    human_verification.append(
        {
            "check": check,
            "observed": observed,
        },
    )


def _write_pass_outputs(result: dict[str, object]) -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    if BUG_DESCRIPTION_PATH.exists():
        BUG_DESCRIPTION_PATH.unlink()

    RESULT_PATH.write_text(
        json.dumps(
            {
                "status": "passed",
                "passed": 1,
                "failed": 0,
                "skipped": 0,
                "summary": "1 passed, 0 failed",
            }
        ),
        encoding="utf-8",
    )
    jira_lines = _jira_comment_lines(result, passed=True)
    markdown_lines = _markdown_result_lines(result, passed=True)
    JIRA_COMMENT_PATH.write_text("\n".join(jira_lines) + "\n", encoding="utf-8")
    PR_BODY_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    RESPONSE_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")


def _write_failure_outputs(
    result: dict[str, object],
    *,
    product_failure: bool,
) -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    error_message = _as_text(result.get("error"))
    RESULT_PATH.write_text(
        json.dumps(
            {
                "status": "failed",
                "passed": 0,
                "failed": 1,
                "skipped": 0,
                "summary": "0 passed, 1 failed",
                "error": error_message,
            }
        ),
        encoding="utf-8",
    )
    jira_lines = _jira_comment_lines(result, passed=False)
    markdown_lines = _markdown_result_lines(result, passed=False)
    JIRA_COMMENT_PATH.write_text("\n".join(jira_lines) + "\n", encoding="utf-8")
    PR_BODY_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    RESPONSE_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    if product_failure:
        BUG_DESCRIPTION_PATH.write_text(
            "\n".join(_bug_description_lines(result)) + "\n",
            encoding="utf-8",
        )
    elif BUG_DESCRIPTION_PATH.exists():
        BUG_DESCRIPTION_PATH.unlink()


def _jira_comment_lines(result: dict[str, object], *, passed: bool) -> list[str]:
    screenshot = _as_text(result.get("screenshot"))
    lines = [
        "h2. TS-311 — " + ("PASSED" if passed else "FAILED"),
        "",
        "*Automation*",
        f"* Updated or reused live hosted regression coverage in {_jira_code(TEST_FILE_PATH)}",
        "* Reused the existing hosted Playwright harness, live setup repository service, and issue-detail page object.",
        (
            "* Verified the deployed hosted session opens the issue detail, keeps collaboration content behind tabs, and enforces the download-only LFS attachment state."
            if passed
            else "* Exercised the deployed hosted session and captured the exact step where the user-visible collaboration-tab or attachment-capability behavior diverged from TS-311."
        ),
        "",
        "*Real user-style verification*",
        f"* Opened {_jira_code(_as_text(result.get('app_url')))} in Chromium on {platform.system()}.",
        f"* Connected the hosted GitHub session to {_jira_code(_as_text(result.get('repository')))} @ {_jira_code(_as_text(result.get('repository_ref')))}.",
        f"* Opened issue {_jira_code(_as_text(result.get('issue_key')))} — {_jira_inline(_as_text(result.get('issue_summary')))}.",
        "* Checked the visible tab labels, collaboration content placement, upload/download controls, and read-only guidance as they appeared in the live UI.",
        "",
        "*Observed result*",
        *_jira_step_lines(result),
        *[
            f"* Human verification: {_jira_inline(_as_text(entry.get('check')))} — observed {_jira_inline(_single_line(_as_text(entry.get('observed'))))}"
            for entry in _human_entries(result)
        ],
        "",
        "*Artifacts*",
        f"* Screenshot: {_jira_code(screenshot) if screenshot else 'not captured'}",
        "* Run command:",
        "{code:bash}",
        RUN_COMMAND,
        "{code}",
    ]
    if not passed:
        lines.extend(
            [
                "",
                "*Exact assertion / error*",
                "{code}",
                _as_text(result.get("traceback")).rstrip() or _as_text(result.get("error")),
                "{code}",
            ]
        )
    return lines


def _markdown_result_lines(result: dict[str, object], *, passed: bool) -> list[str]:
    screenshot = _as_text(result.get("screenshot"))
    lines = [
        "## Test Automation Result",
        "",
        f"**Status:** {'✅ PASSED' if passed else '❌ FAILED'}",
        f"**Test Case:** {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "## What was automated",
        f"- Reused `{TEST_FILE_PATH}` to exercise the deployed hosted TrackState app via Playwright.",
        "- Opened the seeded hosted issue `DEMO-2`, navigated the collaboration tabs, and validated the visible attachment controls and guidance in the live UI.",
        "- Verified the scenario from a user-facing perspective using visible text, selected tabs, and the rendered upload/download actions rather than repository internals alone.",
        "",
        "## Result",
        *_markdown_step_lines(result),
        *[
            f"- Human verification: `{_as_text(entry.get('check'))}` — observed `{_single_line(_as_text(entry.get('observed')))}`"
            for entry in _human_entries(result)
        ],
        "",
        "## Environment",
        f"- URL: `{_as_text(result.get('app_url'))}`",
        f"- Repository: `{_as_text(result.get('repository'))}` @ `{_as_text(result.get('repository_ref'))}`",
        f"- Browser / OS: `{_as_text(result.get('browser'))}` / `{_as_text(result.get('os'))}`",
        f"- Screenshot: `{screenshot}`" if screenshot else "- Screenshot: not captured",
        "",
        "## How to run",
        "```bash",
        RUN_COMMAND,
        "```",
    ]
    if not passed:
        lines.extend(
            [
                "",
                "## Exact assertion / error",
                "```text",
                _as_text(result.get("traceback")).rstrip() or _as_text(result.get("error")),
                "```",
            ]
        )
    return lines


def _bug_description_lines(result: dict[str, object]) -> list[str]:
    screenshot = _as_text(result.get("screenshot"))
    step_statuses = _ticket_step_statuses(result)
    observed_issue_text = _single_line(_as_text(result.get("initial_issue_detail_text")))
    attachments_text = _single_line(
        _as_text(_attachments_observation(result).get("body_text"))
    )
    return [
        "h3. Bug Summary",
        (
            f"TS-311 failed in the deployed hosted TrackState app for {_jira_code(_as_text(result.get('issue_key')))}. "
            "The live collaboration-tab or attachment-capability behavior did not match the expected hosted download-only LFS experience."
        ),
        "",
        "h4. Environment",
        f"* URL: {_jira_code(_as_text(result.get('app_url')))}",
        f"* Repository: {_jira_code(_as_text(result.get('repository')))} @ {_jira_code(_as_text(result.get('repository_ref')))}",
        f"* Browser: {_jira_code(_as_text(result.get('browser')))}",
        f"* OS: {_jira_code(_as_text(result.get('os')))}",
        f"* Issue: {_jira_code(_as_text(result.get('issue_key')))} — {_jira_inline(_as_text(result.get('issue_summary')))}",
        "",
        "h4. Steps to Reproduce",
        (
            "# "
            + ("✅" if step_statuses[0]["passed"] else "❌")
            + " Open the Issue Detail screen for an issue with existing attachments. "
            + step_statuses[0]["details"]
        ),
        (
            "# "
            + ("✅" if step_statuses[1]["passed"] else "❌")
            + " Navigate through 'Comments', 'Attachments', and 'History' tabs. "
            + step_statuses[1]["details"]
        ),
        (
            "# "
            + ("✅" if step_statuses[2]["passed"] else "❌")
            + " In the 'Attachments' tab, verify the state of the upload and download actions. "
            + step_statuses[2]["details"]
        ),
        "",
        "h4. Expected Result",
        "* Collaboration data is reachable through dedicated tabs inside the issue detail route.",
        "* In the hosted GitHub session, upload is hidden or disabled with the explicit read-only message.",
        "* Download remains visible and enabled for the LFS-backed attachment.",
        "",
        "h4. Actual Result",
        f"* Step 1 visible issue-detail snapshot: {_jira_inline(observed_issue_text)}",
        f"* Attachments-tab snapshot: {_jira_inline(attachments_text or 'Not reached.')}",
        f"* Assertion summary: {_jira_inline(_as_text(result.get('error')))}",
        "",
        "h4. Exact Error Message / Assertion Failure",
        "{code}",
        _as_text(result.get("traceback")).rstrip() or _as_text(result.get("error")),
        "{code}",
        "",
        "h4. Screenshots / Logs",
        f"* Screenshot: {_jira_code(screenshot) if screenshot else 'not captured'}",
        "* Observed steps:",
        "{code:json}",
        json.dumps(result.get("steps"), indent=2, sort_keys=True),
        "{code}",
    ]


def _ticket_step_statuses(result: dict[str, object]) -> list[dict[str, object]]:
    steps = _steps(result)
    issue_opened = any(
        step.get("step") == 1 and step.get("status") == "passed" for step in steps
    ) and any(step.get("step") == 2 for step in steps)
    tab_navigation_passed = all(
        step.get("status") == "passed"
        for step in steps
        if step.get("step") in {2, 3, 4, 5}
    ) and any(step.get("step") == 5 for step in steps)
    attachments_step = next(
        (step for step in steps if step.get("step") == 5),
        None,
    )
    attachments_observation = _attachments_observation(result)
    return [
        {
            "passed": issue_opened,
            "details": (
                "Observed: the hosted issue detail for "
                f"{_jira_code(_as_text(result.get('issue_key')))} opened and the page "
                f"text was {_jira_inline(_single_line(_as_text(result.get('initial_issue_detail_text'))))}."
                if issue_opened
                else "Observed: the hosted issue detail did not open successfully before the scenario failed."
            ),
        },
        {
            "passed": tab_navigation_passed,
            "details": (
                "Observed: the Comments, History, and Attachments tabs were reachable and switched the visible issue surface as expected."
                if tab_navigation_passed
                else f"Observed: {_jira_inline(_first_failure_message(result, step_numbers=(2, 3, 4, 5)))}"
            ),
        },
        {
            "passed": bool(attachments_step) and attachments_step.get("status") == "passed",
            "details": (
                "Observed: the Attachments tab showed the seeded file, the download action stayed enabled, upload stayed unavailable, and the read-only guidance was visible."
                if attachments_step and attachments_step.get("status") == "passed"
                else (
                    "Observed: the Attachments step was not reached because tab navigation failed earlier."
                    if attachments_step is None
                    else (
                        "Observed: "
                        + _jira_inline(
                            _single_line(
                                _as_text(attachments_observation.get("body_text"))
                                or _first_failure_message(result, step_numbers=(5,))
                            )
                        )
                    )
                )
            ),
        },
    ]


def _jira_step_lines(result: dict[str, object]) -> list[str]:
    lines: list[str] = []
    for step in _steps(result):
        status = _as_text(step.get("status")).upper()
        action = _as_text(step.get("action"))
        observed = _single_line(_as_text(step.get("observed")))
        icon = "✅" if status == "PASSED" else "❌"
        lines.append(f"* {icon} Step {step.get('step')} {status}: {action}")
        lines.append(f"* Observed: {_jira_inline(observed)}")
    if not lines:
        lines.append(f"* ❌ No step results were recorded. Observed error: {_jira_inline(_as_text(result.get('error')))}")
    return lines


def _markdown_step_lines(result: dict[str, object]) -> list[str]:
    lines: list[str] = []
    for step in _steps(result):
        status = _as_text(step.get("status")).upper()
        action = _as_text(step.get("action"))
        observed = _single_line(_as_text(step.get("observed")))
        icon = "✅" if status == "PASSED" else "❌"
        lines.append(f"- {icon} Step {step.get('step')} {status}: {action}")
        lines.append(f"  - Observed: `{observed}`")
    if not lines:
        lines.append(f"- ❌ No step results were recorded. Observed error: `{_as_text(result.get('error'))}`")
    return lines


def _steps(result: dict[str, object]) -> list[dict[str, object]]:
    payload = result.get("steps")
    return payload if isinstance(payload, list) else []


def _human_entries(result: dict[str, object]) -> list[dict[str, object]]:
    payload = result.get("human_verification")
    return payload if isinstance(payload, list) else []


def _attachments_observation(result: dict[str, object]) -> dict[str, object]:
    tab_observations = result.get("tab_observations")
    if not isinstance(tab_observations, dict):
        return {}
    attachments = tab_observations.get("Attachments")
    return attachments if isinstance(attachments, dict) else {}


def _first_failure_message(
    result: dict[str, object],
    *,
    step_numbers: tuple[int, ...],
) -> str:
    error_text = _as_text(result.get("error"))
    if error_text:
        for paragraph in error_text.split("\n\n"):
            if any(paragraph.startswith(f"Step {step_number} failed") for step_number in step_numbers):
                return paragraph
    for step in _steps(result):
        if step.get("step") in step_numbers and step.get("status") == "failed":
            return _as_text(step.get("action")) or _as_text(step.get("observed"))
    return _as_text(result.get("error"))


def _as_text(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def _single_line(value: str) -> str:
    return " ".join(value.split())


def _jira_inline(value: str) -> str:
    return "{{" + value.replace("}", "\\}") + "}}"


def _jira_code(value: str) -> str:
    return "{{" + value.replace("}", "\\}") + "}}"


if __name__ == "__main__":
    main()
