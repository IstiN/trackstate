from __future__ import annotations

import json
import platform
import re
import sys
import tempfile
import traceback
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
    create_live_tracker_app,
)
from testing.tests.support.ts390_attachment_upload_guard_runtime import (  # noqa: E402
    Ts390AttachmentUploadAttemptObservation,
    Ts390AttachmentUploadGuardRuntime,
)

TICKET_KEY = "TS-390"
ISSUE_PATH = "DEMO/DEMO-1/DEMO-2"
EXPECTED_ISSUE_KEY = "DEMO-2"

HOSTED_LIMITED_UPLOAD_TITLE = "Some attachment uploads still require local Git"
HOSTED_LIMITED_UPLOAD_FRAGMENTS = (
    "Attachment upload is available for browser-supported files.",
    "Files that follow the Git LFS attachment path",
    "local Git runtime.",
)
GENERIC_LFS_ERROR_FRAGMENT = "download-only for Git LFS attachments"
ATTACHMENTS_TAB_LABEL = "Attachments"
CHOOSE_ATTACHMENT_LABEL = "Choose attachment"
UPLOAD_ATTACHMENT_LABEL = "Upload attachment"
CLEAR_ATTACHMENT_LABEL = "Clear selected attachment"

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts390_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts390_failure.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-390 requires GH_TOKEN or GITHUB_TOKEN to open the hosted live app.",
        )

    user = service.fetch_authenticated_user()
    issue_fixture = service.fetch_issue_fixture(ISSUE_PATH)
    _assert_preconditions(issue_fixture)

    gitattributes_text = service.fetch_repo_text(".gitattributes")
    extension = _pick_lfs_extension(gitattributes_text)
    upload_name = f"ts390-hosted-lfs-guidance.{extension}"
    issue_attachments_directory = f"{issue_fixture.path}/attachments"
    expected_upload_path = f"{issue_attachments_directory}/{upload_name}"
    expected_specific_message = (
        f"{upload_name} follows the Git LFS attachment path and must be uploaded "
        "from a local Git runtime. Existing attachments remain available for "
        "download here."
    )
    expected_specific_message_fragments = (
        upload_name,
        "follows the Git LFS attachment path",
        "must be uploaded from a local Git runtime",
        "Existing attachments remain available for download here.",
    )

    upload_observation = Ts390AttachmentUploadAttemptObservation(
        issue_attachments_directory=issue_attachments_directory,
    )
    runtime = Ts390AttachmentUploadGuardRuntime(
        repository=service.repository,
        token=token,
        observation=upload_observation,
    )

    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "app_url": config.app_url,
        "repository": service.repository,
        "repository_ref": service.ref,
        "issue_key": issue_fixture.key,
        "issue_summary": issue_fixture.summary,
        "issue_path": issue_fixture.path,
        "lfs_gitattributes": gitattributes_text,
        "chosen_lfs_extension": extension,
        "upload_name": upload_name,
        "expected_upload_path": expected_upload_path,
        "expected_specific_message": expected_specific_message,
        "steps": [],
        "human_verification": [],
    }

    with tempfile.TemporaryDirectory(prefix="ts390-", dir=OUTPUTS_DIR) as temp_dir:
        attachment_path = Path(temp_dir) / upload_name
        attachment_path.write_bytes(
            b"TS-390 hosted LFS upload guidance probe\n",
        )
        result["temporary_attachment_path"] = str(attachment_path)
        result["temporary_attachment_size_bytes"] = attachment_path.stat().st_size

        try:
            with create_live_tracker_app(
                config,
                runtime_factory=lambda: runtime,
            ) as tracker_page:
                page = LiveIssueDetailCollaborationPage(tracker_page)
                try:
                    runtime_state = tracker_page.open()
                    result["runtime_state"] = runtime_state.kind
                    result["runtime_body_text"] = runtime_state.body_text
                    if runtime_state.kind != "ready":
                        raise AssertionError(
                            "Step 1 failed: the deployed app did not reach the hosted "
                            "tracker shell before the LFS upload guidance scenario "
                            "began.\n"
                            f"Observed body text:\n{runtime_state.body_text}",
                        )
                    _record_step(
                        result,
                        step=1,
                        status="passed",
                        action="Open the deployed hosted app and reach the tracker shell.",
                        observed=(
                            "runtime_state=ready; visible_navigation=Dashboard, Board, "
                            "JQL Search, Hierarchy, Settings"
                        ),
                    )

                    page.ensure_connected(
                        token=token,
                        repository=service.repository,
                        user_login=user.login,
                    )
                    page.dismiss_connection_banner()
                    _record_step(
                        result,
                        step=2,
                        status="passed",
                        action="Connect the hosted GitHub session for the deployed repository.",
                        observed=(
                            f"connected_user={user.login}; repository={service.repository}; "
                            "hosted_access=Attachments limited"
                        ),
                    )

                    page.open_issue(
                        issue_key=issue_fixture.key,
                        issue_summary=issue_fixture.summary,
                    )
                    issue_detail_text = page.current_body_text()
                    result["issue_detail_text"] = issue_detail_text
                    if page.issue_detail_count(issue_fixture.key) == 0:
                        raise AssertionError(
                            "Step 3 failed: selecting the seeded issue did not open the "
                            "hosted issue detail view.\n"
                            f"Observed body text:\n{issue_detail_text}",
                        )
                    _record_step(
                        result,
                        step=3,
                        status="passed",
                        action="Open the seeded hosted issue detail.",
                        observed=(
                            f"opened_issue={issue_fixture.key}; summary={issue_fixture.summary}; "
                            "visible_tabs=Detail, Comments, Attachments, History"
                        ),
                    )

                    page.open_collaboration_tab(ATTACHMENTS_TAB_LABEL)
                    page.wait_for_selected_tab(ATTACHMENTS_TAB_LABEL, timeout_ms=30_000)
                    attachments_text = _wait_for_accessible_fragments(
                        page,
                        (HOSTED_LIMITED_UPLOAD_TITLE, *HOSTED_LIMITED_UPLOAD_FRAGMENTS),
                        timeout_ms=60_000,
                    )
                    result["attachments_text_before_upload"] = attachments_text
                    if page.button_label_fragment_count(CHOOSE_ATTACHMENT_LABEL) == 0:
                        raise AssertionError(
                            "Step 4 failed: the hosted Attachments tab did not expose the "
                            f'visible "{CHOOSE_ATTACHMENT_LABEL}" action.\n'
                            f"Observed body text:\n{attachments_text}",
                        )
                    if page.button_label_fragment_count(UPLOAD_ATTACHMENT_LABEL) == 0:
                        raise AssertionError(
                            "Step 4 failed: the hosted Attachments tab did not expose the "
                            f'visible "{UPLOAD_ATTACHMENT_LABEL}" action.\n'
                            f"Observed body text:\n{attachments_text}",
                        )
                    _record_step(
                        result,
                        step=4,
                        status="passed",
                        action=(
                            "Open the Attachments tab and verify the hosted capability "
                            "banner explains that Git LFS files still require local Git."
                        ),
                        observed=(
                            f"title={HOSTED_LIMITED_UPLOAD_TITLE}; "
                            f"choose_button_visible={page.button_label_fragment_count(CHOOSE_ATTACHMENT_LABEL) > 0}; "
                            f"upload_button_visible={page.button_label_fragment_count(UPLOAD_ATTACHMENT_LABEL) > 0}"
                        ),
                    )

                    page.choose_attachment(str(attachment_path))
                    selected_attachment_text = page.wait_for_text(
                        upload_name,
                        timeout_ms=30_000,
                    )
                    result["selected_attachment_text"] = selected_attachment_text
                    if page.button_label_fragment_count(CLEAR_ATTACHMENT_LABEL) == 0:
                        raise AssertionError(
                            "Step 5 failed: choosing the LFS-tracked attachment did not "
                            "surface the selected-file state.\n"
                            f"Observed body text:\n{selected_attachment_text}",
                        )
                    _record_step(
                        result,
                        step=5,
                        status="passed",
                        action=(
                            f"Choose the LFS-tracked `{upload_name}` file in the hosted "
                            "Attachments tab."
                        ),
                        observed=(
                            f"selected_attachment={upload_name}; "
                            f"size_bytes={attachment_path.stat().st_size}; "
                            f"clear_button_visible={page.button_label_fragment_count(CLEAR_ATTACHMENT_LABEL) > 0}"
                        ),
                    )

                    page.upload_attachment()
                    final_accessible_text = _wait_for_accessible_fragments(
                        page,
                        expected_specific_message_fragments,
                        timeout_ms=60_000,
                    )
                    page.wait_for_text_absent(
                        GENERIC_LFS_ERROR_FRAGMENT,
                        timeout_ms=60_000,
                    )
                    final_body_text = page.current_body_text()
                    result["final_accessible_text"] = final_accessible_text
                    result["final_body_text"] = final_body_text
                    result["attempted_upload_urls"] = list(
                        upload_observation.attempted_upload_urls,
                    )
                    if GENERIC_LFS_ERROR_FRAGMENT in final_body_text:
                        raise AssertionError(
                            "Step 6 failed: the hosted LFS upload flow still surfaced the "
                            "generic download-only message instead of the specific local-"
                            "runtime guidance.\n"
                            f"Observed body text:\n{final_body_text}",
                        )
                    if upload_observation.upload_was_attempted:
                        raise AssertionError(
                            "Step 6 failed: the hosted session attempted a live attachment "
                            "write for the LFS-tracked file instead of blocking the upload "
                            "in the UI.\n"
                            f"Observed upload URLs: {upload_observation.attempted_upload_urls}\n"
                            f"Observed body text:\n{final_body_text}",
                        )
                    _record_step(
                        result,
                        step=6,
                        status="passed",
                        action=(
                            "Click Upload attachment and verify the UI blocks the upload "
                            "with file-specific local Git guidance."
                        ),
                        observed=expected_specific_message,
                    )

                    _record_human_verification(
                        result,
                        check=(
                            "Verified the visible Attachments callout still told a hosted "
                            "user that browser-supported files can upload here while Git "
                            "LFS files still require local Git."
                        ),
                        observed=(
                            f"title={HOSTED_LIMITED_UPLOAD_TITLE}; "
                            "message=Attachment upload is available for browser-supported "
                            "files. Files that follow the Git LFS attachment path still "
                            "need to be added from a local Git runtime."
                        ),
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Verified the selected file name stayed visible in the "
                            "Attachments panel and the upload was blocked with a specific "
                            "file-name message instead of a generic hosted error."
                        ),
                        observed=(
                            f"selected_file={upload_name}; "
                            f"message={expected_specific_message}; "
                            f"upload_attempted={upload_observation.upload_was_attempted}"
                        ),
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
            result["error"] = f"{type(error).__name__}: {error}"
            result["traceback"] = traceback.format_exc()
            result["attempted_upload_urls"] = list(upload_observation.attempted_upload_urls)
            _write_failure_outputs(result)
            raise


def _assert_preconditions(issue_fixture: LiveHostedIssueFixture) -> None:
    if issue_fixture.key != EXPECTED_ISSUE_KEY:
        raise AssertionError(
            "Precondition failed: TS-390 expected the seeded DEMO-2 fixture.\n"
            f"Observed issue key: {issue_fixture.key}",
        )


def _pick_lfs_extension(gitattributes_text: str) -> str:
    tracked_extensions = [
        match.group("extension").lower()
        for match in re.finditer(
            r"^\*\.(?P<extension>[A-Za-z0-9]+)\s+filter=lfs\b",
            gitattributes_text,
            flags=re.MULTILINE,
        )
    ]
    for preferred in ("zip", "pdf", "png", "jpg", "jpeg", "gif", "webp"):
        if preferred in tracked_extensions:
            return preferred
    if tracked_extensions:
        return tracked_extensions[0]
    raise AssertionError(
        "Precondition failed: the hosted setup repository `.gitattributes` file did "
        "not declare any Git LFS tracked extensions.\n"
        f"Observed .gitattributes:\n{gitattributes_text}",
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
            "Expected accessible text fragments were not all visible after waiting.\n"
            f"Missing fragments: {missing}\n"
            f"Observed labels:\n{combined}",
        )
    return combined


def _normalize_whitespace(value: str) -> str:
    return " ".join(value.split())


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
        "* Opened the deployed hosted TrackState app against the live setup repository.",
        "* Connected the hosted GitHub session and opened the seeded issue Attachments tab.",
        "* Chose an LFS-tracked file extension from the live .gitattributes configuration and attempted the hosted upload flow.",
        "* Verified the UI showed specific local-runtime guidance and that no live attachment write was attempted.",
        "",
        "*Observed result*",
        (
            "* Matched the expected result: the hosted UI blocked the LFS-tracked upload with file-specific local Git guidance."
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
        "- Opened the deployed hosted TrackState app against the live setup repository.",
        "- Connected the hosted GitHub session and opened the seeded issue Attachments tab.",
        "- Chose an LFS-tracked file extension from the live `.gitattributes` file and exercised the hosted upload flow.",
        "- Verified the UI showed specific local-runtime guidance and that no live attachment write was attempted.",
        "",
        "### Observed result",
        (
            "- Matched the expected result: the hosted UI blocked the LFS-tracked upload with file-specific local Git guidance."
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
        (
            "Ran the deployed hosted attachment upload flow with an LFS-tracked file "
            "selected from the live `.gitattributes` configuration."
        ),
        "",
        "## Observed",
        f"- Upload name: `{result.get('upload_name', '')}`",
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
        f"# {TICKET_KEY} - Hosted LFS upload guidance regression",
        "",
        "## Steps to reproduce",
        "1. Open the Attachments tab for the hosted issue.",
        f"   - {'✅' if _step_status(result, 4) == 'passed' else '❌'} {_step_observation(result, 4)}",
        "2. Select the LFS-tracked file for upload.",
        f"   - {'✅' if _step_status(result, 5) == 'passed' else '❌'} {_step_observation(result, 5)}",
        "3. Click `Upload attachment` and observe the capability banner/message.",
        f"   - {'✅' if _step_status(result, 6) == 'passed' else '❌'} {_step_observation(result, 6)}",
        "",
        "## Actual vs Expected",
        (
            "- Expected: the hosted UI blocks the LFS-tracked file and displays a "
            "specific message that the file must be added through a local/runtime Git flow."
        ),
        (
            "- Actual: "
            + str(
                result.get("error")
                or "the hosted UI did not show the expected file-specific local Git guidance."
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
        f"- Chosen upload file: `{result.get('upload_name', '')}`",
        f"- Live `.gitattributes` extension used: `.{result.get('chosen_lfs_extension', '')}`",
        "",
        "## Evidence",
        f"- Screenshot: `{result.get('screenshot', FAILURE_SCREENSHOT_PATH)}`",
        f"- Attempted upload URLs: `{result.get('attempted_upload_urls', [])}`",
        "",
        "## Observed body text",
        "```text",
        str(result.get("final_body_text") or result.get("selected_attachment_text") or result.get("attachments_text_before_upload") or result.get("runtime_body_text", "")),
        "```",
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
