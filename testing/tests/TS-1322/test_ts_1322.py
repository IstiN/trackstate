from __future__ import annotations

import hashlib
import json
import os
import platform
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
    LiveHostedRepositoryFile,
    LiveSetupRepositoryService,
)
import urllib.error  # noqa: E402
from testing.core.config.live_setup_test_config import (  # noqa: E402
    load_live_setup_test_config,
)
from testing.tests.support.live_tracker_app_factory import (  # noqa: E402
    create_live_tracker_app_with_stored_token,
)


TICKET_KEY = "TS-1322"
ISSUE_PATH = "DEMO/DEMO-1/DEMO-2"
ATTACHMENT_NAME = "design_doc.pdf"
MANIFEST_PATH = f"{ISSUE_PATH}/attachments.json"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"

INITIAL_ATTACHMENT_BYTES = (
    b"TS-1322 initial hosted attachment content.\n"
    b"Initial Content.\n"
)
REPLACEMENT_ATTACHMENT_BYTES = (
    b"TS-1322 replacement hosted attachment content.\n"
    b"New Content.\n"
    b"The cache should be invalidated after replacement.\n"
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


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_live_setup_test_config()
    repository_service = LiveSetupRepositoryService(config=config)
    token = repository_service.token
    if not token:
        _write_blocked_outputs(
            blocked_reason=(
                "TS-1322 requires GH_TOKEN or GITHUB_TOKEN to seed and verify the "
                "hosted repository-backed attachment."
            ),
            missing_name="GH_TOKEN or GITHUB_TOKEN",
            missing_description="GitHub token with write access to IstiN/trackstate-setup",
            missing_how_to_add="Add the token using the CI secret-management process.",
        )
        return

    user = repository_service.fetch_authenticated_user()
    seed_path = (
        ISSUE_PATH
        + "/attachments/"
        + ATTACHMENT_NAME
    )
    original_manifest = _fetch_repo_file_if_exists(repository_service, MANIFEST_PATH)
    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "repository": repository_service.repository,
        "repository_ref": repository_service.ref,
        "issue_path": ISSUE_PATH,
        "issue_key": ISSUE_PATH.split("/")[-1],
        "attachment_name": ATTACHMENT_NAME,
        "app_url": config.app_url,
        "os": platform.system(),
        "steps": [],
        "human_verification": [],
        "seed_path": seed_path,
    }

    with tempfile.TemporaryDirectory(prefix="ts1322-") as temp_dir:
        temp_dir_path = Path(temp_dir)
        replacement_file = temp_dir_path / ATTACHMENT_NAME
        replacement_file.write_bytes(REPLACEMENT_ATTACHMENT_BYTES)

        cleanup_error: Exception | None = None
        cleanup_traceback: str = ""
        failure_error: Exception | None = None
        failure_traceback: str = ""
        seeded = False
        try:
            _seed_attachment(
                repository_service=repository_service,
                path=seed_path,
                content=INITIAL_ATTACHMENT_BYTES,
            )
            seeded = True
            issue_fixture = repository_service.fetch_issue_fixture(ISSUE_PATH)
            _assert_preconditions(issue_fixture=issue_fixture, result=result)
            _run_live_ui_flow(
                config=config,
                repository_service=repository_service,
                user_login=user.login,
                issue_fixture=issue_fixture,
                replacement_file=replacement_file,
                result=result,
            )
        except Exception as error:
            failure_error = error
            failure_traceback = traceback.format_exc()
        finally:
            if seeded:
                try:
                    repository_service.delete_repo_file(
                        seed_path,
                        message=f"Remove TS-1322 seeded attachment {ATTACHMENT_NAME}",
                    )
                except Exception as error:  # pragma: no cover - cleanup failure is rare
                    cleanup_error = error
                    cleanup_traceback = traceback.format_exc()
            if original_manifest is not None:
                try:
                    current_manifest = _fetch_repo_file_if_exists(
                        repository_service, MANIFEST_PATH
                    )
                    if current_manifest is None or current_manifest.content != original_manifest.content:
                        repository_service.write_repo_text(
                            MANIFEST_PATH,
                            content=original_manifest.content,
                            message=f"{TICKET_KEY}: restore original attachments manifest",
                        )
                except Exception as error:  # pragma: no cover - cleanup failure is rare
                    if cleanup_error is None:
                        cleanup_error = error
                        cleanup_traceback = traceback.format_exc()

        if failure_error is None and cleanup_error is None:
            _write_pass_outputs(result)
            return

        if failure_error is not None:
            result["error"] = f"{type(failure_error).__name__}: {failure_error}"
            result["traceback"] = failure_traceback
            result["failed_step"] = _extract_failed_step(str(failure_error))
            if cleanup_error is not None:
                result["cleanup_error"] = f"{type(cleanup_error).__name__}: {cleanup_error}"
                result["cleanup_traceback"] = cleanup_traceback
            _write_failure_outputs(result, str(failure_error), write_bug_description=True)
            raise failure_error

        result["error"] = f"{type(cleanup_error).__name__}: {cleanup_error}"
        result["traceback"] = cleanup_traceback
        _write_failure_outputs(result, str(cleanup_error), write_bug_description=False)
        raise cleanup_error


def _run_live_ui_flow(
    *,
    config,
    repository_service: LiveSetupRepositoryService,
    user_login: str,
    issue_fixture: LiveHostedIssueFixture,
    replacement_file: Path,
    result: dict[str, object],
) -> None:
    with create_live_tracker_app_with_stored_token(
        config,
        token=repository_service.token or "",
    ) as tracker_page:
        page = LiveIssueDetailCollaborationPage(tracker_page)

        runtime = tracker_page.open()
        if runtime.kind != "ready":
            raise AssertionError(
                "Step 1 failed: the deployed hosted app did not reach the tracker shell.\n"
                f"Observed body text:\n{runtime.body_text}",
            )
        _record_step(
            result,
            step=1,
            action="Open the hosted app and reach the tracker shell.",
            observed=runtime.body_text,
        )

        page.ensure_connected(
            token=repository_service.token or "",
            repository=repository_service.repository,
            user_login=user_login,
        )
        page.dismiss_connection_banner()
        page.open_issue(
            issue_key=issue_fixture.key,
            issue_summary=issue_fixture.summary,
        )
        detail_label = page.issue_detail_accessible_label(
            issue_fixture.key,
            expected_fragment=issue_fixture.summary,
        )
        if issue_fixture.summary not in detail_label:
            raise AssertionError(
                "Step 2 failed: the selected issue detail did not stay visible.\n"
                f"Observed detail label:\n{detail_label}",
            )
        _record_step(
            result,
            step=2,
            action="Open the seeded issue detail from JQL Search.",
            observed=detail_label,
        )

        page.open_collaboration_tab("Attachments")
        controls = page.observe_attachment_upload_controls()
        if controls.choose_button_count < 1 or not controls.choose_button_enabled:
            raise AssertionError(
                "Step 3 failed: the Attachments tab did not expose an enabled Choose "
                "attachment control.\n"
                f"Observed controls: {controls}",
            )
        if controls.upload_button_count < 1 or not controls.upload_button_enabled:
            raise AssertionError(
                "Step 3 failed: the Attachments tab did not expose an enabled Upload "
                "attachment control.\n"
                f"Observed controls: {controls}",
            )
        initial_row_text = page.attachment_row_text(ATTACHMENT_NAME)
        _scroll_download_button_into_view(tracker_page.session, ATTACHMENT_NAME)
        initial_download_path = page.download_attachment(ATTACHMENT_NAME)
        initial_download_bytes = Path(initial_download_path).read_bytes()
        if initial_download_bytes != INITIAL_ATTACHMENT_BYTES:
            raise AssertionError(
                "Step 3 failed: the pre-existing hosted attachment did not download the "
                "expected initial bytes.\n"
                f"Observed checksum: {_sha256(initial_download_bytes)}\n"
                f"Expected checksum: {_sha256(INITIAL_ATTACHMENT_BYTES)}\n"
                f"Visible row text:\n{initial_row_text}",
            )
        _record_step(
            result,
            step=3,
            action="Verify the seeded attachment is visible and downloads the initial bytes.",
            observed=(
                f"row_text={initial_row_text}\n"
                f"sha256={_sha256(initial_download_bytes)}"
            ),
        )

        page.choose_attachment_file(str(replacement_file))
        selected = page.wait_for_attachment_selection_summary(file_name=ATTACHMENT_NAME)
        if not selected.file_name_visible or not selected.upload_enabled:
            raise AssertionError(
                "Step 4 failed: the selected replacement file was not acknowledged in the "
                "Attachments tab before upload.\n"
                f"Observed summary: {selected}",
            )
        _record_step(
            result,
            step=4,
            action="Select the replacement file with the same attachment name.",
            observed=selected.summary_text,
        )

        page.click_upload_attachment()
        dialog_text = page.wait_for_replace_attachment_dialog(ATTACHMENT_NAME)
        if "Replace attachment?" not in dialog_text:
            raise AssertionError(
                "Step 5 failed: the replacement confirmation dialog did not appear.\n"
                f"Observed dialog text:\n{dialog_text}",
            )
        page.confirm_replace_attachment()
        page.wait_for_replace_attachment_dialog_to_close()
        _record_step(
            result,
            step=5,
            action="Confirm the replacement dialog and complete the overwrite.",
            observed=dialog_text,
        )
        page.wait_for_attachment_upload_completion(
            ATTACHMENT_NAME,
            expected_size_label=f"{len(REPLACEMENT_ATTACHMENT_BYTES)} B",
        )

        updated_row_text = page.attachment_row_text(ATTACHMENT_NAME)
        _scroll_download_button_into_view(tracker_page.session, ATTACHMENT_NAME)
        updated_download_path = page.download_attachment(ATTACHMENT_NAME)
        updated_download_bytes = Path(updated_download_path).read_bytes()
        if updated_download_bytes != REPLACEMENT_ATTACHMENT_BYTES:
            raise AssertionError(
                "Step 6 failed: the hosted attachment download still returned stale bytes "
                "after confirming the overwrite.\n"
                f"Initial checksum: {_sha256(initial_download_bytes)}\n"
                f"Updated checksum: {_sha256(updated_download_bytes)}\n"
                f"Expected checksum: {_sha256(REPLACEMENT_ATTACHMENT_BYTES)}\n"
                f"Initial row text:\n{initial_row_text}\n"
                f"Updated row text:\n{updated_row_text}",
            )
        if updated_row_text == initial_row_text:
            raise AssertionError(
                "Step 6 failed: the visible attachment row did not change after the "
                "replacement was confirmed.\n"
                f"Row text before:\n{initial_row_text}\n"
                f"Row text after:\n{updated_row_text}",
            )
        _record_step(
            result,
            step=6,
            action="Verify the attachment row and downloaded bytes reflect the new content.",
            observed=(
                f"row_text={updated_row_text}\n"
                f"sha256={_sha256(updated_download_bytes)}"
            ),
        )
        _record_human_verification(
            result,
            check=(
                "Confirmed from the user-facing Attachments tab that the visible row "
                "updated after overwrite and the downloaded file matched the new bytes."
            ),
            observed=(
                f"before={initial_row_text}\n"
                f"after={updated_row_text}\n"
                f"download_sha256={_sha256(updated_download_bytes)}"
            ),
        )


def _assert_preconditions(
    *,
    issue_fixture: LiveHostedIssueFixture,
    result: dict[str, object],
) -> None:
    if not any(path.endswith(f"/{ATTACHMENT_NAME}") for path in issue_fixture.attachment_paths):
        raise AssertionError(
            "Precondition failed: the seeded hosted issue did not expose the temporary "
            f"attachment {ATTACHMENT_NAME!r}.\n"
            f"Observed attachment paths: {issue_fixture.attachment_paths}",
        )
    _record_step(
        result,
        step=0,
        action="Seed the hosted repository with the initial attachment bytes.",
        observed=(
            f"issue={issue_fixture.key}; attachment_paths={issue_fixture.attachment_paths}"
        ),
    )


def _seed_attachment(
    *,
    repository_service: LiveSetupRepositoryService,
    path: str,
    content: bytes,
) -> None:
    repository_service.write_repo_text(
        path,
        content=content.decode("utf-8"),
        message=f"Seed TS-1322 hosted attachment {ATTACHMENT_NAME}",
    )


def _record_step(
    result: dict[str, object],
    *,
    step: int,
    action: str,
    observed: str,
) -> None:
    steps = result.setdefault("steps", [])
    assert isinstance(steps, list)
    steps.append(
        {
            "step": step,
            "status": "passed",
            "action": action,
            "observed": observed,
        }
    )


def _record_human_verification(
    result: dict[str, object],
    *,
    check: str,
    observed: str,
) -> None:
    checks = result.setdefault("human_verification", [])
    assert isinstance(checks, list)
    checks.append(
        {
            "check": check,
            "observed": observed,
        }
    )


def _write_pass_outputs(result: dict[str, object]) -> None:
    _write_text(
        JIRA_COMMENT_PATH,
        _jira_comment(result, status="PASSED"),
    )
    _write_text(
        PR_BODY_PATH,
        _markdown_summary(result, status="PASSED"),
    )
    _write_text(
        RESPONSE_PATH,
        _markdown_summary(result, status="PASSED"),
    )
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
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_failure_outputs(
    result: dict[str, object],
    error: str,
    *,
    write_bug_description: bool,
) -> None:
    _write_text(
        JIRA_COMMENT_PATH,
        _jira_comment(result, status="FAILED"),
    )
    _write_text(
        PR_BODY_PATH,
        _markdown_summary(result, status="FAILED"),
    )
    _write_text(
        RESPONSE_PATH,
        _markdown_summary(result, status="FAILED"),
    )
    if write_bug_description:
        _write_text(BUG_DESCRIPTION_PATH, _bug_description(result, error))
    else:
        BUG_DESCRIPTION_PATH.unlink(missing_ok=True)
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
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_blocked_outputs(
    *,
    blocked_reason: str,
    missing_name: str,
    missing_description: str,
    missing_how_to_add: str,
) -> None:
    payload = {
        "status": "blocked_by_human",
        "passed": 0,
        "failed": 0,
        "skipped": 1,
        "summary": "0 passed, 0 failed, 1 skipped",
        "blocked_reason": blocked_reason,
        "missing": [
            {
                "type": "secret",
                "name": missing_name,
                "description": missing_description,
                "how_to_add": missing_how_to_add,
            }
        ],
    }
    RESULT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    _write_text(
        JIRA_COMMENT_PATH,
        "h3. Test Automation Result\n\n"
        "*Status:* 🚫 BLOCKED\n"
        f"*Test Case:* {TICKET_KEY} — Replace hosted attachment\n\n"
        "h4. What was tested\n"
        "* Hosted attachment replacement through the live TrackState setup\n\n"
        "h4. Result\n"
        f"* Blocked: {blocked_reason}\n\n"
        "h4. Test file\n"
        "{code}\n"
        f"testing/tests/{TICKET_KEY}/test_ts_1322.py\n"
        "{code}\n\n"
        "h4. Run command\n"
        "{code:bash}\n"
        f"python3 testing/tests/{TICKET_KEY}/test_ts_1322.py\n"
        "{code}\n",
    )
    _write_text(
        PR_BODY_PATH,
        "# Test Automation Result\n\n"
        "**Status:** 🚫 BLOCKED\n"
        f"**Test Case:** {TICKET_KEY} — Replace hosted attachment\n\n"
        "## What was automated\n"
        "- Hosted attachment replacement through the live TrackState setup\n\n"
        "## Result\n"
        f"- Blocked: {blocked_reason}\n\n"
        "## How to run\n"
        "```bash\n"
        f"python3 testing/tests/{TICKET_KEY}/test_ts_1322.py\n"
        "```\n",
    )
    _write_text(
        RESPONSE_PATH,
        f"# {TICKET_KEY} BLOCKED\n\n- {blocked_reason}\n",
    )


def _jira_comment(result: dict[str, object], *, status: str) -> str:
    steps = result.get("steps", [])
    human = result.get("human_verification", [])
    lines = [
        "h3. Test Automation Result",
        "",
        f"*Status:* {'✅ PASSED' if status == 'PASSED' else '❌ FAILED'}",
        f"*Test Case:* {TICKET_KEY} — Replace hosted attachment",
        "",
        "h4. What was tested",
        "* Replaced a hosted attachment in the live TrackState setup",
        "* Verified the attachment row updated and the downloaded bytes matched the new content",
        "",
        "h4. Result",
    ]
    if isinstance(steps, list):
        for step in steps:
            if isinstance(step, dict):
                lines.append(
                    f"* Step {step.get('step')}: {step.get('action')} — {step.get('observed')}",
                )
    lines.extend(
        [
            "",
            "h4. Human-style verification",
        ],
    )
    if isinstance(human, list):
        for check in human:
            if isinstance(check, dict):
                lines.append(
                    f"* {check.get('check')} Observed: {check.get('observed')}",
                )
    lines.extend(
        [
            "",
            "h4. Test file",
            "{code}",
            f"testing/tests/{TICKET_KEY}/test_ts_1322.py",
            "{code}",
            "",
            "h4. Run command",
            "{code:bash}",
            f"python3 testing/tests/{TICKET_KEY}/test_ts_1322.py",
            "{code}",
        ],
    )
    if status == "FAILED":
        lines.extend(
            [
                "",
                "h4. Failure",
                f"*Error:* {result.get('error')}",
            ],
        )
    return "\n".join(lines) + "\n"


def _markdown_summary(result: dict[str, object], *, status: str) -> str:
    steps = result.get("steps", [])
    human = result.get("human_verification", [])
    lines = [
        "## Test Automation Result",
        "",
        f"**Status:** {'✅ PASSED' if status == 'PASSED' else '❌ FAILED'}",
        f"**Test Case:** {TICKET_KEY} — Replace hosted attachment",
        "",
        "## What was automated",
        "- Replaced a hosted attachment in the live TrackState setup",
        "- Verified the attachment row updated and the downloaded bytes matched the new content",
        "",
        "## Result",
    ]
    if isinstance(steps, list):
        for step in steps:
            if isinstance(step, dict):
                lines.append(
                    f"- Step {step.get('step')}: {step.get('action')} — {step.get('observed')}",
                )
    lines.extend(["", "## Human-style verification"])
    if isinstance(human, list):
        for check in human:
            if isinstance(check, dict):
                lines.append(
                    f"- {check.get('check')} Observed: {check.get('observed')}",
                )
    if status == "FAILED":
        lines.extend(["", "## Failure", f"`{result.get('error')}`"])
    return "\n".join(lines) + "\n"


def _bug_description(result: dict[str, object], error: str) -> str:
    step_lines = [
        "1. ✅ Seed `DEMO/DEMO-1/DEMO-2/attachments/design_doc.pdf` with the initial bytes.",
        "2. ✅ Open the hosted TrackState setup, connect to the repository, and open `DEMO-2`.",
        "3. ✅ Switch to the `Attachments` tab, select the replacement `design_doc.pdf`, and confirm the overwrite dialog.",
        "4. ❌ Verify the attachment row and downloaded bytes reflect the replacement content.",
        f"   - Actual error: {error}",
    ]
    return "\n".join(
        [
            f"h4. Environment",
            f"* Repository: `{result.get('repository')}`",
            f"* Branch: `{result.get('repository_ref')}`",
            f"* App URL: `{result.get('app_url')}`",
            f"* OS: `{result.get('os')}`",
            "",
            "h4. Steps to Reproduce",
            *step_lines,
            "",
            "h4. Expected Result",
            "The replacement dialog should complete successfully, the visible attachment row should update, "
            "and downloading `design_doc.pdf` should return the new bytes.",
            "",
            "h4. Actual Result",
            f"The test failed with `{error}` before the overwrite could be verified.",
            "",
            "h4. Logs / Error Output",
            "{code}",
            str(result.get("traceback", "")),
            "{code}",
        ]
    ) + "\n"


def _write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _scroll_download_button_into_view(session, attachment_name: str) -> None:
    selector = f'flt-semantics[aria-label="Download {attachment_name}"]'
    session.evaluate(
        """
        ({ selector }) => {
          const element = document.querySelector(selector);
          if (!element) {
            return false;
          }
          element.scrollIntoView({ block: 'center', inline: 'center' });
          return true;
        }
        """,
        arg={"selector": selector},
    )
    session.wait_for_function(
        """
        ({ selector }) => {
          const element = document.querySelector(selector);
          if (!element) {
            return false;
          }
          const rect = element.getBoundingClientRect();
          return rect.width > 0
            && rect.height > 0
            && rect.top >= 0
            && rect.left >= 0
            && rect.bottom <= window.innerHeight
            && rect.right <= window.innerWidth;
        }
        """,
        arg={"selector": selector},
        timeout_ms=30_000,
    )


def _extract_failed_step(message: str) -> int:
    for token in ("Step 6 failed", "Step 5 failed", "Step 4 failed", "Step 3 failed", "Step 2 failed", "Step 1 failed"):
        if token in message:
            try:
                return int(token.split()[1])
            except (IndexError, ValueError):
                continue
    return 0


if __name__ == "__main__":
    main()
