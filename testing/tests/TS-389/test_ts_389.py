from __future__ import annotations

import json
import platform
import sys
import tempfile
import traceback
import urllib.error
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_issue_detail_collaboration_page import (  # noqa: E402
    LiveIssueDetailCollaborationPage,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveHostedIssueFixture,
    LiveHostedRepositoryFile,
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.utils.polling import poll_until  # noqa: E402
from testing.tests.support.live_tracker_app_factory import (  # noqa: E402
    create_live_tracker_app_with_stored_token,
)

TICKET_KEY = "TS-389"
ISSUE_PATH = "DEMO/DEMO-1/DEMO-2"
ATTACHMENT_NAME = "design_doc.pdf"
ATTACHMENT_PATH_SUFFIX = f"attachments/{ATTACHMENT_NAME}"
INITIAL_ATTACHMENT_TEXT = "TS-389 original attachment baseline.\n"
REPLACEMENT_ATTACHMENT_TEXT = (
    "TS-389 replacement attachment content.\n"
    "This payload is intentionally longer to change the visible file size.\n"
)
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts389_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts389_failure.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-389 requires GH_TOKEN or GITHUB_TOKEN to open the hosted live app.",
        )

    user = service.fetch_authenticated_user()
    issue_fixture = service.fetch_issue_fixture(ISSUE_PATH)
    _assert_preconditions(issue_fixture)
    attachment_path = f"{issue_fixture.path}/{ATTACHMENT_PATH_SUFFIX}"
    original_attachment = _fetch_repo_file_if_exists(service, attachment_path)
    seeded_attachment_text = (
        original_attachment.content if original_attachment is not None else INITIAL_ATTACHMENT_TEXT
    )

    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "app_url": config.app_url,
        "repository": service.repository,
        "repository_ref": service.ref,
        "issue_key": issue_fixture.key,
        "issue_summary": issue_fixture.summary,
        "issue_path": issue_fixture.path,
        "attachment_name": ATTACHMENT_NAME,
        "attachment_path": attachment_path,
        "original_attachment_present": original_attachment is not None,
        "steps": [],
        "human_verification": [],
    }

    scenario_error: Exception | None = None
    cleanup_error: Exception | None = None
    try:
        _ensure_seed_attachment(
            service=service,
            issue_path=issue_fixture.path,
            attachment_path=attachment_path,
            original_attachment=original_attachment,
        )
        with tempfile.TemporaryDirectory(prefix="ts389-") as temp_dir:
            upload_path = Path(temp_dir) / ATTACHMENT_NAME
            upload_path.write_bytes(REPLACEMENT_ATTACHMENT_TEXT.encode("utf-8"))
            replacement_size_label = _attachment_size_label(
                REPLACEMENT_ATTACHMENT_TEXT.encode("utf-8"),
            )
            result["upload_file_path"] = str(upload_path)
            result["replacement_attachment_size"] = replacement_size_label

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
                            "Precondition failed: the deployed app did not reach the hosted "
                            "tracker shell before the attachment replacement scenario began.\n"
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
                    if page.issue_detail_count(issue_fixture.key) == 0:
                        raise AssertionError(
                            "Precondition failed: opening the seeded issue did not render the "
                            "requested issue detail view.\n"
                            f"Observed body text:\n{page.current_body_text()}",
                        )

                    page.open_collaboration_tab("Attachments")
                    page.wait_for_text(ATTACHMENT_NAME, timeout_ms=60_000)
                    attachments_body_text = page.current_body_text()
                    result["attachments_body_text_before_upload"] = attachments_body_text
                    visible_download_count = page.attachment_download_button_count(
                        ATTACHMENT_NAME,
                    )
                    if visible_download_count != 1:
                        raise AssertionError(
                            "Step 1 failed: the Attachments tab did not show exactly one "
                            "visible download control for the seeded `design_doc.pdf` "
                            "attachment.\n"
                            f"Observed download control count: {visible_download_count}\n"
                            f"Observed body text:\n{attachments_body_text}",
                        )
                    _record_step(
                        result,
                        step=1,
                        status="passed",
                        action="Open the Attachments tab in the issue detail view.",
                        observed=attachments_body_text,
                    )

                    upload_controls = page.observe_attachment_upload_controls()
                    result["choose_attachment_button_count"] = (
                        upload_controls.choose_button_count
                    )
                    result["choose_attachment_button_enabled"] = (
                        upload_controls.choose_button_enabled
                    )
                    result["upload_attachment_button_count"] = (
                        upload_controls.upload_button_count
                    )
                    result["upload_attachment_button_enabled"] = (
                        upload_controls.upload_button_enabled
                    )
                    if (
                        upload_controls.choose_button_count != 1
                        or upload_controls.upload_button_count != 1
                        or not upload_controls.choose_button_enabled
                    ):
                        raise AssertionError(
                            "Step 2 failed: the live Attachments tab stayed in a limited or "
                            "download-only state and did not expose the visible `Choose "
                            "attachment` and `Upload attachment` controls required for the "
                            "duplicate replacement flow.\n"
                            f"Observed choose button count: {upload_controls.choose_button_count}\n"
                            f"Observed choose button enabled: {upload_controls.choose_button_enabled}\n"
                            f"Observed upload button count: {upload_controls.upload_button_count}\n"
                            f"Observed upload button enabled: {upload_controls.upload_button_enabled}\n"
                            f"Observed body text:\n{attachments_body_text}",
                        )

                    page.choose_attachment_file(str(upload_path))
                    selected_summary = page.wait_for_selected_attachment_summary(
                        attachment_name=ATTACHMENT_NAME,
                        attachment_size_label=replacement_size_label,
                        timeout_ms=30_000,
                    )
                    result["selected_attachment_summary"] = selected_summary
                    _record_step(
                        result,
                        step=2,
                        status="passed",
                        action="Select a new file named `design_doc.pdf` for upload.",
                        observed=selected_summary,
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Verified the Attachments panel showed the selected-file summary "
                            "with the exact file name and visible file size before upload."
                        ),
                        observed=selected_summary,
                    )

                    page.click_upload_attachment()
                    dialog_text = page.wait_for_replace_attachment_dialog(
                        ATTACHMENT_NAME,
                        timeout_ms=60_000,
                    )
                    result["replace_dialog_text"] = dialog_text
                    repo_text_before_confirm = service.fetch_repo_text(attachment_path)
                    result["repo_text_before_confirm"] = repo_text_before_confirm
                    if repo_text_before_confirm != seeded_attachment_text:
                        raise AssertionError(
                            "Step 3 failed: the replacement preflight changed the repository "
                            "attachment before the user confirmed the dialog.\n"
                            f"Expected repository text before confirmation:\n{seeded_attachment_text}\n"
                            f"Observed repository text before confirmation:\n{repo_text_before_confirm}",
                        )
                    _record_step(
                        result,
                        step=3,
                        status="passed",
                        action="Observe the UI response after the repository preflight check.",
                        observed=dialog_text,
                    )

                    for expected_fragment in (
                        "Replace attachment?",
                        (
                            "Uploading this file will replace the existing attachment stored "
                            "as design_doc.pdf. Rename the new file first if you need to keep "
                            "both versions."
                        ),
                        "Keep current attachment",
                        "Replace attachment",
                    ):
                        if expected_fragment not in dialog_text:
                            raise AssertionError(
                                "Step 4 failed: the replace-confirmation dialog did not show "
                                "the expected user-facing copy.\n"
                                f"Missing fragment: {expected_fragment}\n"
                                f"Observed dialog text:\n{dialog_text}",
                            )
                    _record_step(
                        result,
                        step=4,
                        status="passed",
                        action=(
                            "Verify the replacement confirmation dialog explains that the "
                            "existing attachment will be replaced."
                        ),
                        observed=dialog_text,
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Verified the visible modal title, warning copy, and action "
                            "buttons clearly stated that `design_doc.pdf` would be replaced "
                            "only after explicit confirmation."
                        ),
                        observed=dialog_text,
                    )

                    page.confirm_replace_attachment()
                    page.wait_for_replace_attachment_dialog_to_close(timeout_ms=60_000)
                    page.wait_for_text(
                        "Choose a file to review its size before upload.",
                        timeout_ms=60_000,
                    )
                    matched, repo_text_after_confirm = poll_until(
                        probe=lambda: service.fetch_repo_text(attachment_path),
                        is_satisfied=lambda text: text == REPLACEMENT_ATTACHMENT_TEXT,
                        timeout_seconds=90,
                        interval_seconds=3,
                    )
                    result["repo_text_after_confirm"] = repo_text_after_confirm
                    if not matched:
                        raise AssertionError(
                            "Step 5 failed: confirming the replacement did not persist the new "
                            "attachment content within the timeout.\n"
                            f"Expected repository text after confirmation:\n{REPLACEMENT_ATTACHMENT_TEXT}\n"
                            f"Observed repository text after confirmation:\n{repo_text_after_confirm}",
                        )
                    attachments_body_text_after_upload = page.current_body_text()
                    result["attachments_body_text_after_upload"] = attachments_body_text_after_upload
                    visible_download_count_after_upload = page.attachment_download_button_count(
                        ATTACHMENT_NAME,
                    )
                    result["visible_download_count_after_upload"] = (
                        visible_download_count_after_upload
                    )
                    if visible_download_count_after_upload != 1:
                        raise AssertionError(
                            "Step 5 failed: confirming the replacement left the Attachments "
                            "tab without exactly one visible `Download design_doc.pdf` "
                            "control.\n"
                            f"Observed download control count: {visible_download_count_after_upload}\n"
                            f"Observed body text:\n{attachments_body_text_after_upload}",
                        )
                    _record_step(
                        result,
                        step=5,
                        status="passed",
                        action="Confirm the replacement and verify the upload completes.",
                        observed=attachments_body_text_after_upload,
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Verified the dialog closed, the selected-file summary reset to the "
                            "empty Attachments state, and the visible `Download "
                            "design_doc.pdf` control still remained available."
                        ),
                        observed=(
                            "empty_state=Choose a file to review its size before upload.; "
                            f"download_count={visible_download_count_after_upload}; "
                            f"body_text={attachments_body_text_after_upload}"
                        ),
                    )

                    page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                    result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
                except Exception:
                    page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                    result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                    raise
    except Exception as error:
        scenario_error = error
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
    finally:
        try:
            cleanup = _restore_attachment(
                service=service,
                attachment_path=attachment_path,
                original_attachment=original_attachment,
            )
            result["cleanup"] = cleanup
        except Exception as error:
            cleanup_error = error
            result["cleanup"] = {
                "status": "failed",
                "error": f"{type(error).__name__}: {error}",
            }
            if scenario_error is None:
                scenario_error = error
                result["error"] = f"{type(error).__name__}: {error}"
                result["traceback"] = traceback.format_exc()

    if scenario_error is not None:
        if cleanup_error is not None and cleanup_error is not scenario_error:
            result["traceback"] = (
                str(result.get("traceback", ""))
                + "\nCleanup error:\n"
                + "".join(
                    traceback.format_exception(
                        type(cleanup_error),
                        cleanup_error,
                        cleanup_error.__traceback__,
                    )
                )
            )
        _write_failure_outputs(result)
        raise scenario_error

    _write_pass_outputs(result)


def _assert_preconditions(issue_fixture: LiveHostedIssueFixture) -> None:
    if issue_fixture.key != "DEMO-2":
        raise AssertionError(
            "Precondition failed: TS-389 expected the seeded DEMO-2 fixture.\n"
            f"Observed issue key: {issue_fixture.key}",
        )


def _fetch_repo_file_if_exists(
    service: LiveSetupRepositoryService,
    path: str,
) -> LiveHostedRepositoryFile | None:
    try:
        return service.fetch_repo_file(path)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise


def _ensure_seed_attachment(
    *,
    service: LiveSetupRepositoryService,
    issue_path: str,
    attachment_path: str,
    original_attachment: LiveHostedRepositoryFile | None,
) -> None:
    expected_text = (
        original_attachment.content if original_attachment is not None else INITIAL_ATTACHMENT_TEXT
    )
    if original_attachment is None:
        service.write_repo_text(
            attachment_path,
            content=INITIAL_ATTACHMENT_TEXT,
            message=f"{TICKET_KEY}: seed duplicate attachment precondition",
        )
    matched, observation = poll_until(
        probe=lambda: service.fetch_issue_fixture(issue_path),
        is_satisfied=lambda fixture: ATTACHMENT_NAME
        in {Path(path).name for path in fixture.attachment_paths},
        timeout_seconds=90,
        interval_seconds=3,
    )
    if not matched:
        raise AssertionError(
            "Precondition failed: the hosted repository did not expose the seeded "
            f"`{ATTACHMENT_NAME}` attachment before the live test began.\n"
            f"Observed attachment paths: {observation.attachment_paths}",
        )
    matched, repo_text = poll_until(
        probe=lambda: service.fetch_repo_text(attachment_path),
        is_satisfied=lambda text: text == expected_text,
        timeout_seconds=90,
        interval_seconds=3,
    )
    if not matched:
        raise AssertionError(
            "Precondition failed: the hosted repository did not expose the expected seeded "
            "attachment content before the live test began.\n"
            f"Observed repository text:\n{repo_text}",
        )


def _restore_attachment(
    *,
    service: LiveSetupRepositoryService,
    attachment_path: str,
    original_attachment: LiveHostedRepositoryFile | None,
) -> dict[str, object]:
    if original_attachment is None:
        try:
            current_attachment = service.fetch_repo_file(attachment_path)
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return {"status": "absent"}
            raise
        service.delete_repo_file(
            attachment_path,
            message=f"{TICKET_KEY}: delete seeded duplicate attachment precondition",
        )
        matched, _ = poll_until(
            probe=lambda: _fetch_repo_file_if_exists(service, attachment_path),
            is_satisfied=lambda file: file is None,
            timeout_seconds=90,
            interval_seconds=3,
        )
        return {
            "status": "deleted" if matched else "delete-pending",
            "deleted_sha": current_attachment.sha,
        }

    current_text = service.fetch_repo_text(attachment_path)
    if current_text != original_attachment.content:
        service.write_repo_text(
            attachment_path,
            content=original_attachment.content,
            message=f"{TICKET_KEY}: restore original attachment content",
        )
    matched, repo_text = poll_until(
        probe=lambda: service.fetch_repo_text(attachment_path),
        is_satisfied=lambda text: text == original_attachment.content,
        timeout_seconds=90,
        interval_seconds=3,
    )
    return {
        "status": "restored" if matched else "restore-pending",
        "restored_sha": original_attachment.sha,
        "observed_text": repo_text,
    }


def _attachment_size_label(payload: bytes) -> str:
    return f"{len(payload)} B"


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
            }
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
            }
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
        (
            "* Opened the live hosted issue detail, switched to the Attachments tab, and "
            f"seeded {{{{{ATTACHMENT_NAME}}}}} in the demo repository when needed."
        ),
        (
            f"* Prepared a second local file named {{{{{ATTACHMENT_NAME}}}}} and attempted "
            "to start the duplicate attachment replacement flow from the live UI."
        ),
        (
            "* Verified whether the live Attachments tab exposed the upload controls and "
            "user-facing replacement confirmation path."
        ),
        "",
        "*Observed result*",
        (
            "* Matched the expected result: the UI blocked the duplicate upload until the "
            "user explicitly confirmed the replacement."
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
            ]
        )
    return "\n".join(lines) + "\n"


def _pr_body(result: dict[str, object], *, passed: bool) -> str:
    status = "Passed" if passed else "Failed"
    screenshot_path = result.get("screenshot", FAILURE_SCREENSHOT_PATH)
    lines = [
        f"## {TICKET_KEY} {status}",
        "",
        "### Automation",
        (
            f"- Opened the live hosted issue detail, switched to the Attachments tab, and "
            f"seeded `{ATTACHMENT_NAME}` in the demo repository when needed."
        ),
        (
            f"- Prepared a second local file named `{ATTACHMENT_NAME}` and attempted to "
            "start the duplicate attachment replacement flow from the live UI."
        ),
        (
            "- Verified whether the live Attachments tab exposed the upload controls and "
            "user-facing replacement confirmation path."
        ),
        "",
        "### Observed result",
        (
            "- Matched the expected result: the UI blocked the duplicate upload until the "
            "user explicitly confirmed the replacement."
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
            ]
        )
    return "\n".join(lines) + "\n"


def _response_summary(result: dict[str, object], *, passed: bool) -> str:
    status = "passed" if passed else "failed"
    screenshot_path = result.get("screenshot", FAILURE_SCREENSHOT_PATH)
    lines = [
        f"# {TICKET_KEY} {status}",
        "",
        (
            f"Ran the live hosted attachment replacement flow for `{ATTACHMENT_NAME}` and "
            "checked that duplicate uploads require explicit confirmation."
        ),
        "",
        "## Observed",
        f"- Screenshot: `{screenshot_path}`",
        f"- Environment: `{result['app_url']}` on Chromium/Playwright ({platform.system()})",
        f"- Cleanup: `{result.get('cleanup')}`",
    ]
    if not passed:
        lines.extend(
            [
                "",
                "## Error",
                "```text",
                str(result.get("traceback", result.get("error", ""))),
                "```",
            ]
        )
    return "\n".join(lines) + "\n"


def _bug_description(result: dict[str, object]) -> str:
    lines = [
        f"# {TICKET_KEY} - Duplicate attachment replacement confirmation regression",
        "",
        "## Steps to reproduce",
        "1. Open the `Attachments` tab in the issue detail view for the seeded demo issue.",
        f"   - {'✅' if _step_status(result, 1) == 'passed' else '❌'} {_step_observation(result, 1)}",
        "2. Select a new file named `design_doc.pdf` for upload.",
        f"   - {'✅' if _step_status(result, 2) == 'passed' else '❌'} {_step_observation(result, 2)}",
        "3. Observe the UI response after the repository preflight check.",
        f"   - {'✅' if _step_status(result, 3) == 'passed' else '❌'} {_step_observation(result, 3)}",
        "4. Verify a confirmation dialog appears explaining that the existing attachment will be replaced.",
        f"   - {'✅' if _step_status(result, 4) == 'passed' else '❌'} {_step_observation(result, 4)}",
        "5. Confirm the replacement and verify the upload completes.",
        f"   - {'✅' if _step_status(result, 5) == 'passed' else '❌'} {_step_observation(result, 5)}",
        "",
        "## Actual vs Expected",
        (
            "- Expected: selecting a duplicate `design_doc.pdf` upload shows the explicit "
            "replace-confirmation dialog, leaves the repository attachment unchanged until "
            "confirmation, and then completes the replacement after the user confirms."
        ),
        (
            "- Actual: "
            + str(
                result.get("error")
                or "the live Attachments tab did not require explicit confirmation before replacing the existing attachment."
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
        f"- Issue: `{result['issue_key']}` (`{result['issue_summary']}`)",
        f"- Attachment path: `{result['attachment_path']}`",
        "- Browser: `Chromium (Playwright)`",
        f"- OS: `{platform.platform()}`",
        "",
        "## Evidence",
        f"- Screenshot: `{result.get('screenshot', FAILURE_SCREENSHOT_PATH)}`",
        f"- Replace dialog text: `{result.get('replace_dialog_text', '')}`",
        f"- Repository text before confirmation: `{result.get('repo_text_before_confirm', '')}`",
        f"- Repository text after confirmation: `{result.get('repo_text_after_confirm', '')}`",
        f"- Attachments body text before upload: `{result.get('attachments_body_text_before_upload', '')}`",
        f"- Attachments body text after upload: `{result.get('attachments_body_text_after_upload', '')}`",
        f"- Cleanup: `{result.get('cleanup')}`",
    ]
    return "\n".join(lines) + "\n"


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for step in result.get("steps", []):
        if not isinstance(step, dict):
            continue
        prefix = "#" if jira else "1."
        lines.append(
            f"{prefix} Step {step['step']} — {step['action']} — {step['status'].upper() if jira else step['status']}: {step['observed']}"
        )
    if not lines:
        lines.append("# No step details were recorded." if jira else "1. No step details were recorded.")
    return lines


def _human_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for check in result.get("human_verification", []):
        if not isinstance(check, dict):
            continue
        prefix = "#" if jira else "1."
        lines.append(f"{prefix} {check.get('check')}: {check.get('observed')}")
    if not lines:
        lines.append(
            "# No human-style verification data was recorded."
            if jira
            else "1. No human-style verification data was recorded."
        )
    return lines


def _step_status(result: dict[str, object], step_number: int) -> str:
    for step in result.get("steps", []):
        if isinstance(step, dict) and int(step.get("step", -1)) == step_number:
            return str(step.get("status", "failed"))
    return "failed"


def _step_observation(result: dict[str, object], step_number: int) -> str:
    for step in result.get("steps", []):
        if isinstance(step, dict) and int(step.get("step", -1)) == step_number:
            return str(step.get("observed", "No observation recorded."))
    previous_step = step_number - 1
    if previous_step >= 1 and _step_status(result, previous_step) != "passed":
        return (
            f"Not reached because Step {previous_step} failed: "
            f"{_step_observation(result, previous_step)}"
        )
    return str(result.get("error", "No observation recorded."))


if __name__ == "__main__":
    main()
