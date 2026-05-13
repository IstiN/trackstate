from __future__ import annotations

import json
import platform
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_issue_detail_collaboration_page import (  # noqa: E402
    AttachmentSelectionSummaryObservation,
    AttachmentUploadControlsObservation,
    LiveIssueDetailCollaborationPage,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveHostedIssueFixture,
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.utils.polling import poll_until  # noqa: E402
from testing.tests.support.live_tracker_app_factory import (  # noqa: E402
    create_live_tracker_app,
)
from testing.tests.support.ts567_uninitialized_attachment_provider_runtime import (  # noqa: E402
    Ts567UninitializedAttachmentProviderObservation,
    Ts567UninitializedAttachmentProviderRuntime,
)

TICKET_KEY = "TS-567"
ISSUE_PATH = "DEMO/DEMO-1/DEMO-2"
EXPECTED_ISSUE_KEY = "DEMO-2"
ATTACHMENTS_TAB_LABEL = "Attachments"
UPLOAD_FILE_NAME = "ts567-provider-unavailable.txt"
UPLOAD_FILE_TEXT = (
    "TS-567 hosted upload probe.\n"
    "This file verifies the visible runtime error when the active attachment "
    "provider becomes unavailable before the upload is committed.\n"
)

EXPECTED_ERROR_MESSAGE = (
    "Save failed: GitHub Releases attachment storage requires GitHub "
    "authentication/configuration that supports release uploads. This "
    "repository session cannot upload release-backed attachments."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts567_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts567_failure.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-567 requires GH_TOKEN or GITHUB_TOKEN to open the hosted live app.",
        )

    issue_fixture = service.fetch_issue_fixture(ISSUE_PATH)
    _assert_preconditions(issue_fixture)
    user = service.fetch_authenticated_user()
    observation = Ts567UninitializedAttachmentProviderObservation(
        repository=service.repository,
    )
    runtime = Ts567UninitializedAttachmentProviderRuntime(
        repository=service.repository,
        token=token,
        observation=observation,
    )

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
        with tempfile.TemporaryDirectory(prefix="ts567-", dir=OUTPUTS_DIR) as temp_dir:
            upload_path = Path(temp_dir) / UPLOAD_FILE_NAME
            upload_path.write_text(UPLOAD_FILE_TEXT, encoding="utf-8")
            result["upload_file_path"] = str(upload_path)
            result["upload_size_bytes"] = upload_path.stat().st_size
            result["upload_size_label"] = f"{upload_path.stat().st_size} B"

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
                            "Precondition failed: the deployed app did not reach the "
                            "hosted tracker shell before the TS-567 scenario began.\n"
                            f"Observed body text:\n{runtime_state.body_text}",
                        )

                    page.ensure_connected(
                        token=token,
                        repository=service.repository,
                        user_login=user.login,
                    )
                    page.dismiss_connection_banner()
                    page.search_and_select_issue(
                        issue_key=issue_fixture.key,
                        issue_summary=issue_fixture.summary,
                        query=issue_fixture.key,
                    )
                    if page.issue_detail_count(issue_fixture.key) == 0:
                        raise AssertionError(
                            "Precondition failed: selecting the seeded issue did not open "
                            "the hosted issue detail view.\n"
                            f"Observed body text:\n{page.current_body_text()}",
                        )

                    page.open_collaboration_tab(ATTACHMENTS_TAB_LABEL)
                    page.wait_for_selected_tab(ATTACHMENTS_TAB_LABEL, timeout_ms=30_000)
                    attachments_before = page.wait_for_collaboration_section_to_settle(
                        ATTACHMENTS_TAB_LABEL,
                        timeout_ms=60_000,
                    )
                    result["attachments_body_text_before_selection"] = attachments_before
                    try:
                        controls_before = _wait_for_enabled_upload_controls(page)
                    except AssertionError:
                        preliminary_controls = page.observe_attachment_upload_controls()
                        result["controls_before_selection"] = _controls_payload(
                            preliminary_controls,
                        )
                        _record_human_verification(
                            result,
                            check=(
                                "Verified the visible Attachments panel showed an "
                                "`Open settings` recovery action plus existing download "
                                "rows, but no visible upload controls."
                            ),
                            observed=_normalize_whitespace(attachments_before),
                        )
                        raise
                    result["controls_before_selection"] = _controls_payload(
                        controls_before,
                    )
                    _record_step(
                        result,
                        step=1,
                        status="passed",
                        action="Navigate to the Attachments tab of the hosted issue.",
                        observed=(
                            f"selected_tab={ATTACHMENTS_TAB_LABEL!r}; "
                            f"choose_button_enabled={controls_before.choose_button_enabled}; "
                            f"upload_button_enabled={controls_before.upload_button_enabled}"
                        ),
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Verified the visible Attachments panel showed the hosted upload "
                            "actions before the runtime provider fault was injected."
                        ),
                        observed=_normalize_whitespace(attachments_before),
                    )

                    page.choose_attachment(str(upload_path), timeout_ms=30_000)
                    selection = page.wait_for_attachment_selection_summary(
                        file_name=UPLOAD_FILE_NAME,
                        timeout_ms=60_000,
                    )
                    attachments_after_selection = page.current_body_text()
                    result["selection_summary"] = _selection_payload(selection)
                    result["attachments_body_text_after_selection"] = (
                        attachments_after_selection
                    )
                    if not selection.file_name_visible or not selection.upload_enabled:
                        raise AssertionError(
                            "Step 2 failed: selecting the upload file did not surface the "
                            "expected hosted selected-file state with an enabled Upload "
                            "attachment action.\n"
                            f"Observed selection summary: {selection}\n"
                            f"Observed body text:\n{attachments_after_selection}",
                        )
                    _record_step(
                        result,
                        step=2,
                        status="passed",
                        action=(
                            "Select a file in the hosted Attachments tab and prepare the "
                            "upload."
                        ),
                        observed=_selection_text(selection),
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Verified the selected file name and size appeared in the same "
                            "Attachments panel a user uses before clicking Upload attachment."
                        ),
                        observed=_selection_text(selection),
                    )

                    observation.enable_permission_fault()
                    result["permission_fault_enabled"] = True
                    page.upload_attachment()
                    visible_error = page.wait_for_text(
                        EXPECTED_ERROR_MESSAGE,
                        timeout_ms=60_000,
                    )
                    final_body_text = page.current_body_text()
                    result["visible_error"] = visible_error
                    result["final_body_text"] = final_body_text
                    result["permission_patch_observation"] = {
                        "intercepted_repo_urls": list(observation.intercepted_repo_urls),
                        "observed_permissions": list(observation.observed_permissions),
                        "blocked_mutation_urls": list(observation.blocked_mutation_urls),
                    }
                    result["new_attachment_download_count"] = (
                        page.attachment_download_button_count(UPLOAD_FILE_NAME)
                    )
                    if EXPECTED_ERROR_MESSAGE not in final_body_text:
                        raise AssertionError(
                            "Step 3 failed: the hosted UI did not show the exact visible "
                            "runtime error after the attachment provider was forced into an "
                            "unsupported/uninitialized state.\n"
                            f"Observed body text:\n{final_body_text}",
                        )
                    if not observation.intercepted_repo_urls:
                        raise AssertionError(
                            "Step 3 failed: the synthetic provider fault was never exercised "
                            "during the upload attempt, so the runtime check was not proven.\n"
                            f"Observed permission patch data: "
                            f"{result['permission_patch_observation']}",
                        )
                    if observation.blocked_mutation_urls:
                        raise AssertionError(
                            "Step 3 failed: the hosted UI bypassed the runtime check and "
                            "still attempted a live repository mutation after the provider "
                            "was forced unavailable.\n"
                            f"Observed blocked mutation URLs: "
                            f"{observation.blocked_mutation_urls}\n"
                            f"Observed body text:\n{final_body_text}",
                        )
                    if page.attachment_download_button_count(UPLOAD_FILE_NAME) != 0:
                        raise AssertionError(
                            "Step 3 failed: the hosted UI showed the upload file as a "
                            "completed attachment row even though the provider was forced "
                            "unavailable.\n"
                            f"Observed body text:\n{final_body_text}",
                        )
                    _record_step(
                        result,
                        step=3,
                        status="passed",
                        action=(
                            "Attempt the upload after the active attachment provider is "
                            "forced unavailable."
                        ),
                        observed=EXPECTED_ERROR_MESSAGE,
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Verified as a user that the page showed a visible Save failed "
                            "banner, kept the selected-file state, and did not show the file "
                            "as a completed attachment."
                        ),
                        observed=_normalize_whitespace(final_body_text),
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
        result["permission_patch_observation"] = {
            "intercepted_repo_urls": list(observation.intercepted_repo_urls),
            "observed_permissions": list(observation.observed_permissions),
            "blocked_mutation_urls": list(observation.blocked_mutation_urls),
        }
        _record_failed_step_from_error(result, str(error))
        _write_failure_outputs(result)
        raise


def _assert_preconditions(issue_fixture: LiveHostedIssueFixture) -> None:
    if issue_fixture.key != EXPECTED_ISSUE_KEY:
        raise AssertionError(
            "Precondition failed: TS-567 expected the seeded DEMO-2 issue fixture.\n"
            f"Observed issue key: {issue_fixture.key}",
        )


def _wait_for_enabled_upload_controls(
    page: LiveIssueDetailCollaborationPage,
) -> AttachmentUploadControlsObservation:
    matched, observation = poll_until(
        probe=page.observe_attachment_upload_controls,
        is_satisfied=lambda current: (
            current.choose_button_count == 1
            and current.choose_button_enabled
            and current.upload_button_count == 1
        ),
        timeout_seconds=30,
        interval_seconds=2,
    )
    latest = observation or page.observe_attachment_upload_controls()
    if not matched:
        raise AssertionError(
            "Step 1 failed: the hosted Attachments tab did not expose the visible upload "
            "controls needed to attempt the TS-567 scenario.\n"
            f"Observed controls: {latest}\n"
            f"Observed body text:\n{page.current_body_text()}",
        )
    return latest


def _controls_payload(
    observation: AttachmentUploadControlsObservation,
) -> dict[str, object]:
    return {
        "choose_button_count": observation.choose_button_count,
        "choose_button_enabled": observation.choose_button_enabled,
        "upload_button_count": observation.upload_button_count,
        "upload_button_enabled": observation.upload_button_enabled,
    }


def _selection_payload(
    selection: AttachmentSelectionSummaryObservation,
) -> dict[str, object]:
    return {
        "summary_text": selection.summary_text,
        "file_name_visible": selection.file_name_visible,
        "size_label": selection.size_label,
        "upload_enabled": selection.upload_enabled,
        "summary_top": selection.summary_top,
        "first_attachment_top": selection.first_attachment_top,
    }


def _selection_text(selection: AttachmentSelectionSummaryObservation) -> str:
    return (
        f"summary={selection.summary_text!r}; "
        f"file_name_visible={selection.file_name_visible}; "
        f"size_label={selection.size_label!r}; "
        f"upload_enabled={selection.upload_enabled}"
    )


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


def _record_failed_step_from_error(result: dict[str, object], error_text: str) -> None:
    failed_step = _extract_failed_step_number(error_text)
    if failed_step is None or _find_step(result, failed_step) is not None:
        return
    _record_step(
        result,
        step=failed_step,
        status="failed",
        action=_ticket_step_action(failed_step),
        observed=error_text,
    )


def _extract_failed_step_number(error_text: str) -> int | None:
    marker = "Step "
    if marker not in error_text:
        return None
    after = error_text.split(marker, 1)[1]
    digits = []
    for char in after:
        if char.isdigit():
            digits.append(char)
            continue
        break
    if not digits:
        return None
    return int("".join(digits))


def _ticket_step_action(step_number: int) -> str:
    return {
        1: "Navigate to the Attachments tab of the hosted issue.",
        2: "Select a file in the hosted Attachments tab and prepare the upload.",
        3: "Attempt the upload after the active attachment provider is forced unavailable.",
    }.get(step_number, "Execute the TS-567 hosted upload scenario.")


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
        (
            "* Connected the hosted GitHub session and opened the seeded issue "
            f"{{{{{result['issue_key']}}}}}."
        ),
        (
            "* Reached the file-selection state, injected the provider fault, and "
            "attempted the upload."
            if _step_status(result, 2) == "passed"
            else "* The run stopped before file selection because the hosted Attachments "
            "tab did not expose upload controls."
        ),
        "",
        "*Observed result*",
        (
            "* Matched the expected result: the hosted UI showed a clear visible error "
            "instead of a success state when the provider could no longer handle the upload."
            if passed
            else "* Did not match the expected result: the hosted Attachments tab only "
            "showed {{Open settings}} plus existing download rows, with no visible "
            "{{Choose attachment}} or {{Upload attachment}} controls."
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
        f"- Connected the hosted GitHub session and opened the seeded issue `{result['issue_key']}`.",
        (
            "- Reached the file-selection state, injected the provider fault, and "
            "attempted the upload."
            if _step_status(result, 2) == "passed"
            else "- The run stopped before file selection because the hosted Attachments "
            "tab did not expose upload controls."
        ),
        "",
        "### Observed result",
        (
            "- Matched the expected result: the hosted UI showed a clear visible error "
            "instead of a success state when the provider could no longer handle the upload."
            if passed
            else "- Did not match the expected result: the hosted Attachments tab only "
            "showed `Open settings` plus existing download rows, with no visible "
            "`Choose attachment` or `Upload attachment` controls."
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
            "Ran the hosted upload error-state scenario by selecting a real file and "
            "forcing the attachment provider into an unavailable state immediately "
            "before the upload attempt."
            if _step_status(result, 2) == "passed"
            else "Ran the hosted Attachments-tab verification and found that the live "
            "UI stopped the scenario before file selection because upload controls were "
            "not exposed."
        ),
        "",
        "## Observed",
        f"- Screenshot: `{screenshot_path}`",
        f"- Environment: `{result['app_url']}` on Chromium/Playwright ({platform.system()})",
        (
            "- Permission patch observation: "
            f"`{result.get('permission_patch_observation')}`"
        ),
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
    return "\n".join(
        [
            "# TS-567 - Upload attempt while storage provider is uninitialized does not surface the expected visible error",
            "",
            "## Steps to reproduce",
            "1. Navigate to the 'Attachments' tab of any issue.",
            f"   - {'✅' if _step_status(result, 1) == 'passed' else '❌'} {_step_observation(result, 1)}",
            "2. Select a file and attempt to trigger an upload.",
            f"   - {'✅' if _step_status(result, 2) == 'passed' else '❌'} {_step_observation(result, 2)}",
            "",
            "## Exact error message or assertion failure",
            "```text",
            str(result.get("traceback", result.get("error", ""))),
            "```",
            "",
            "## Actual vs Expected",
            (
                "- **Expected:** after the upload is triggered while the active storage "
                "provider cannot handle the request, the hosted UI should display a clear "
                f"visible error such as `{EXPECTED_ERROR_MESSAGE}` and should not show a "
                "successful completion state."
            ),
            (
                "- **Actual:** "
                + str(
                    result.get("error")
                    or "the hosted UI did not show the expected visible error state."
                )
            ),
            "",
            "## Environment details",
            f"- URL: `{result.get('app_url')}`",
            f"- Repository: `{result.get('repository')}` @ `{result.get('repository_ref')}`",
            f"- Issue: `{result.get('issue_key')}` (`{result.get('issue_summary')}`)",
            f"- Browser: `Chromium (Playwright)`",
            f"- OS: `{platform.platform()}`",
            f"- Selected file: `{result.get('upload_file_path')}`",
            "",
            "## Screenshots or logs",
            f"- Screenshot: `{result.get('screenshot', FAILURE_SCREENSHOT_PATH)}`",
            "### Attachments tab before file selection",
            "```text",
            str(result.get("attachments_body_text_before_selection", "")),
            "```",
            "### Attachments tab after file selection",
            "```text",
            str(result.get("attachments_body_text_after_selection", "")),
            "```",
            "### Final body text after upload attempt",
            "```text",
            str(result.get("final_body_text", "")),
            "```",
            "### Permission patch observation",
            "```json",
            json.dumps(
                result.get("permission_patch_observation", {}),
                indent=2,
                sort_keys=True,
            ),
            "```",
        ],
    ) + "\n"


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for step in result.get("steps", []):
        if not isinstance(step, dict):
            continue
        prefix = "#" if jira else "1."
        status = str(step.get("status", "failed"))
        lines.append(
            f"{prefix} Step {step['step']} — {step['action']} — "
            f"{status.upper() if jira else status}: {step['observed']}"
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
    step = _find_step(result, step_number)
    if step is not None:
        return str(step.get("status", "failed"))
    return "failed"


def _step_observation(result: dict[str, object], step_number: int) -> str:
    step = _find_step(result, step_number)
    if step is not None:
        return str(step.get("observed", "No observation recorded."))
    previous_step = step_number - 1
    if previous_step >= 1 and _step_status(result, previous_step) != "passed":
        return (
            f"Not reached because Step {previous_step} failed: "
            f"{_step_observation(result, previous_step)}"
        )
    return str(result.get("error", "No observation recorded."))


def _find_step(result: dict[str, object], step_number: int) -> dict[str, object] | None:
    for step in result.get("steps", []):
        if isinstance(step, dict) and int(step.get("step", -1)) == step_number:
            return step
    return None


if __name__ == "__main__":
    main()
