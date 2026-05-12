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
    AttachmentSelectionSummaryObservation,
    LiveIssueDetailCollaborationPage,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.tests.support.live_tracker_app_factory import (  # noqa: E402
    create_live_tracker_app_with_stored_token,
)

TICKET_KEY = "TS-392"
ISSUE_PATH = "DEMO/DEMO-1/DEMO-2"
SELECTED_FILE_NAME = "ts392-preupload-size-2_5mb.txt"
SELECTED_FILE_SIZE_BYTES = 2_500_000
EXPECTED_SIZE_MB = 2.5
SIZE_TOLERANCE_MB = 0.15

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts392_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts392_failure.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    fixture_dir = Path(tempfile.mkdtemp(prefix="ts392-"))
    fixture_path = fixture_dir / SELECTED_FILE_NAME
    fixture_path.write_bytes(b"a" * SELECTED_FILE_SIZE_BYTES)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-392 requires GH_TOKEN or GITHUB_TOKEN to open the hosted live app.",
        )

    user = service.fetch_authenticated_user()
    issue_fixture = service.fetch_issue_fixture(ISSUE_PATH)
    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "app_url": config.app_url,
        "repository": service.repository,
        "repository_ref": service.ref,
        "issue_key": issue_fixture.key,
        "issue_summary": issue_fixture.summary,
        "selected_file_name": SELECTED_FILE_NAME,
        "selected_file_size_bytes": SELECTED_FILE_SIZE_BYTES,
        "expected_size_mb": EXPECTED_SIZE_MB,
        "steps": [],
        "human_verification": [],
    }

    try:
        _assert_preconditions(issue_fixture)
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
                        "Precondition failed: the deployed app never reached the hosted "
                        "tracker shell before the TS-392 attachment validation scenario ran.\n"
                        f"Observed body text:\n{runtime.body_text}",
                    )

                page.ensure_connected(
                    token=token,
                    repository=service.repository,
                    user_login=user.login,
                )
                page.open_issue(
                    issue_key=issue_fixture.key,
                    issue_summary=issue_fixture.summary,
                )
                issue_detail_text = page.current_body_text()
                if page.issue_detail_count(issue_fixture.key) <= 0:
                    raise AssertionError(
                        "Step 1 failed: the hosted app did not open the requested issue "
                        f"detail for {issue_fixture.key}.\n"
                        f"Observed body text:\n{issue_detail_text}",
                    )
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action="Open the seeded issue detail and switch to the Attachments tab.",
                    observed=issue_detail_text,
                )

                page.open_collaboration_tab("Attachments")
                page.wait_for_attachment_picker_ready(timeout_ms=60_000)
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=(
                        f"Click the upload trigger and select `{SELECTED_FILE_NAME}` "
                        f"({EXPECTED_SIZE_MB:.1f} MB)."
                    ),
                    observed=(
                        "Attachments tab opened and the Choose attachment control became "
                        "interactive before file selection."
                    ),
                )

                page.choose_attachment(str(fixture_path), timeout_ms=30_000)
                summary = page.wait_for_attachment_selection_summary(
                    file_name=SELECTED_FILE_NAME,
                    timeout_ms=60_000,
                )
                result["selection_summary"] = _selection_summary_payload(summary)

                _assert_selected_file_summary(summary)
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action=(
                        "Observe the selected-file summary area above the attachment list "
                        "before submitting upload."
                    ),
                    observed=_selection_summary_text(summary),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Verified the action area showed the newly selected file name and "
                        "a visible MB-sized label before upload submission."
                    ),
                    observed=_selection_summary_text(summary),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Verified the selected-file summary stayed above the existing "
                        "attachment list, so the user could review the pending upload "
                        "before committing it."
                    ),
                    observed=_placement_text(summary),
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
        _write_failure_outputs(result)
        raise


def _assert_preconditions(issue_fixture) -> None:
    if issue_fixture.key != "DEMO-2":
        raise AssertionError(
            "Precondition failed: TS-392 expected the seeded DEMO-2 issue fixture.\n"
            f"Observed issue key: {issue_fixture.key}",
        )
    if not issue_fixture.attachment_paths:
        raise AssertionError(
            "Precondition failed: DEMO-2 does not contain any seeded attachments in "
            f"{issue_fixture.path}.",
        )


def _assert_selected_file_summary(summary: AttachmentSelectionSummaryObservation) -> None:
    if not summary.file_name_visible:
        raise AssertionError(
            "Step 3 failed: the selected-file summary did not show the chosen file name "
            "before upload submission.\n"
            f"Observed summary text: {summary.summary_text}",
        )
    if not summary.size_label:
        raise AssertionError(
            "Step 3 failed: the selected-file summary did not show a visible file size "
            "before upload submission.\n"
            f"Observed summary text: {summary.summary_text}",
        )

    size_match = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(KB|MB|bytes?)", summary.size_label, re.I)
    if size_match is None:
        raise AssertionError(
            "Step 3 failed: the selected-file summary showed an unexpected size format.\n"
            f"Observed size label: {summary.size_label}\n"
            f"Observed summary text: {summary.summary_text}",
        )
    size_value = float(size_match.group(1))
    size_unit = size_match.group(2).upper()
    if size_unit != "MB":
        raise AssertionError(
            "Step 3 failed: the selected-file summary did not surface the expected MB-sized "
            "user-facing label for the 2.5 MB file.\n"
            f"Observed size label: {summary.size_label}\n"
            f"Observed summary text: {summary.summary_text}",
        )
    if abs(size_value - EXPECTED_SIZE_MB) > SIZE_TOLERANCE_MB:
        raise AssertionError(
            "Step 3 failed: the selected-file summary showed the wrong file size before "
            "upload submission.\n"
            f"Expected approximately: {EXPECTED_SIZE_MB:.1f} MB\n"
            f"Observed size label: {summary.size_label}\n"
            f"Observed summary text: {summary.summary_text}",
        )
    if not summary.upload_enabled:
        raise AssertionError(
            "Step 3 failed: after file selection, the Upload attachment action stayed "
            "disabled instead of reflecting a pending upload state.\n"
            f"Observed summary text: {summary.summary_text}",
        )
    if (
        summary.first_attachment_top is not None
        and summary.summary_top >= summary.first_attachment_top
    ):
        raise AssertionError(
            "Step 3 failed: the selected-file summary did not stay in the action area "
            "above the attachment list.\n"
            f"Observed summary top: {summary.summary_top}\n"
            f"Observed first attachment top: {summary.first_attachment_top}\n"
            f"Observed summary text: {summary.summary_text}",
        )


def _selection_summary_payload(
    summary: AttachmentSelectionSummaryObservation,
) -> dict[str, object]:
    return {
        "summary_text": summary.summary_text,
        "file_name_visible": summary.file_name_visible,
        "size_label": summary.size_label,
        "upload_enabled": summary.upload_enabled,
        "summary_top": summary.summary_top,
        "first_attachment_top": summary.first_attachment_top,
    }


def _selection_summary_text(summary: AttachmentSelectionSummaryObservation) -> str:
    return (
        f"summary_text={summary.summary_text!r}; size_label={summary.size_label!r}; "
        f"upload_enabled={summary.upload_enabled}"
    )


def _placement_text(summary: AttachmentSelectionSummaryObservation) -> str:
    return (
        f"summary_top={summary.summary_top}; "
        f"first_attachment_top={summary.first_attachment_top}"
    )


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
    screenshot_path = result.get("screenshot", FAILURE_SCREENSHOT_PATH)
    lines = [
        f"h3. {TICKET_KEY} {'PASSED' if passed else 'FAILED'}",
        "",
        "*Automation coverage*",
        (
            f"* Opened {{{{{result['issue_key']}}}}} in the deployed hosted app and switched "
            "to the Attachments tab."
        ),
        (
            f"* Selected {{{{{result['selected_file_name']}}}}} "
            f"({SELECTED_FILE_SIZE_BYTES} bytes) through the real browser file picker."
        ),
        (
            "* Verified the pre-upload action area exposed the selected file name and "
            "size before submitting upload."
        ),
        "",
        "*Observed result*",
        (
            "* Matched the expected result."
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
    screenshot_path = result.get("screenshot", FAILURE_SCREENSHOT_PATH)
    lines = [
        f"## {TICKET_KEY} {'Passed' if passed else 'Failed'}",
        "",
        "### Automation",
        f"- Opened `{result['issue_key']}` in the deployed hosted app and switched to `Attachments`.",
        (
            f"- Selected `{result['selected_file_name']}` "
            f"({SELECTED_FILE_SIZE_BYTES} bytes) through the real browser file picker."
        ),
        (
            "- Verified the pre-upload action area showed the chosen file name and size "
            "before upload submission."
        ),
        "",
        "### Observed result",
        (
            "- Matched the expected result."
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
    screenshot_path = result.get("screenshot", FAILURE_SCREENSHOT_PATH)
    lines = [
        f"# {TICKET_KEY} {'passed' if passed else 'failed'}",
        "",
        (
            f"Ran the deployed hosted Attachments flow for `{result['issue_key']}` and "
            f"selected `{result['selected_file_name']}` before upload submission."
        ),
        "",
        "## Observed",
        (
            f"- Selection summary: `{result.get('selection_summary', {}).get('summary_text', '')}`"
            if isinstance(result.get("selection_summary"), dict)
            else ""
        ),
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
            ]
        )
    return "\n".join(line for line in lines if line) + "\n"


def _bug_description(result: dict[str, object]) -> str:
    selection_summary = result.get("selection_summary")
    lines = [
        f"# {TICKET_KEY} - Pre-upload attachment size visibility regression",
        "",
        "## Steps to reproduce",
        "1. Open the `Attachments` tab.",
        f"   - {'✅' if _step_status(result, 1) == 'passed' else '❌'} {_step_observation(result, 1)}",
        (
            f"2. Click the upload trigger and select `{result['selected_file_name']}` "
            f"({EXPECTED_SIZE_MB:.1f} MB)."
        ),
        f"   - {'✅' if _step_status(result, 2) == 'passed' else '❌'} {_step_observation(result, 2)}",
        "3. Observe the `selected-file summary` area above the list before upload is submitted.",
        f"   - {'✅' if _step_status(result, 3) == 'passed' else '❌'} {_step_observation(result, 3)}",
        "",
        "## Actual vs Expected",
        (
            f"- Expected: before upload submission, the action area clearly shows "
            f"`{result['selected_file_name']}` with an approximately `{EXPECTED_SIZE_MB:.1f} MB` "
            "size label above the existing attachment list."
        ),
        (
            "- Actual: "
            + str(
                result.get("error")
                or "the deployed app did not keep the selected file name and size visible in the pre-upload action area."
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
        f"- Issue: `{result['issue_key']} - {result['issue_summary']}`",
        "- Browser: `Chromium (Playwright)`",
        f"- OS: `{platform.platform()}`",
        (
            f"- Selected file fixture: `{result['selected_file_name']}` "
            f"({SELECTED_FILE_SIZE_BYTES} bytes)"
        ),
        "",
        "## Evidence",
        f"- Screenshot: `{result.get('screenshot', FAILURE_SCREENSHOT_PATH)}`",
    ]
    if isinstance(selection_summary, dict):
        lines.extend(
            [
                f"- Observed summary text: `{selection_summary.get('summary_text', '')}`",
                f"- Observed size label: `{selection_summary.get('size_label', '')}`",
                (
                    "- Observed placement: "
                    f"`summary_top={selection_summary.get('summary_top')}, "
                    f"first_attachment_top={selection_summary.get('first_attachment_top')}`"
                ),
            ]
        )
    return "\n".join(lines) + "\n"


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
    checks.append({"check": check, "observed": observed})


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for step in result.get("steps", []):
        if not isinstance(step, dict):
            continue
        prefix = "#" if jira else "1."
        lines.append(
            f"{prefix} Step {step['step']} — {step['action']} — "
            f"{step['status'].upper() if jira else step['status']}: {step['observed']}"
        )
    if not lines:
        lines.append("# No step details were recorded." if jira else "1. No step details were recorded.")
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
