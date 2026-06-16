from __future__ import annotations

import json
import platform
import sys
import traceback
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_create_issue_gate_page import (  # noqa: E402
    CreateIssueGateObservation,
    LiveCreateIssueGatePage,
)
from testing.components.pages.live_issue_detail_collaboration_page import (  # noqa: E402
    LiveIssueDetailCollaborationPage,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
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
    create_live_tracker_app,
)
from testing.tests.support.read_only_hosted_session_runtime import (  # noqa: E402
    ReadOnlyHostedSessionObservation,
    ReadOnlyHostedSessionRuntime,
)

TICKET_KEY = "TS-1288"
TEST_CASE_TITLE = (
    "Create Issue dialog in read-only session — editable form controls are hidden "
    "when recovery gate is active"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-1288/test_ts_1288.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
EXPECTED_CTA = "Open settings"
LINKED_BUGS = ["TS-1270"]
LINKED_BUG_NOTES = (
    "Reviewed linked bug TS-1270 before writing this test. The fix is marked Done, so "
    "the automation runs against the deployed live implementation and inspects the "
    "read-only Create issue dialog itself instead of relying on page-wide button counts."
)
REQUEST_STEPS = [
    "Open the 'Create issue' dialog from the top-bar shell.",
    "Confirm that the 'GuidedRecoveryGate' panel is displayed.",
    "Inspect the dialog for standard input fields (e.g., Summary, Description).",
    "Count the number of 'Save' and 'Create' buttons visible in the dialog footer.",
]
EXPECTED_RESULT = (
    "The UI displays only the guided recovery gate with its explanation and CTA. "
    "All standard editable form controls are hidden and the action button count is "
    "zero (specifically save_button_count=0 and create_button_count=0), ensuring the "
    "gate and form are mutually exclusive."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1288_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1288_failure.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-1288 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
        )

    user = service.fetch_authenticated_user()
    observation = ReadOnlyHostedSessionObservation(repository=service.repository)
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
        "steps": [],
        "human_verification": [],
        "is_product_failure": False,
    }

    tracker_page = None
    try:
        with create_live_tracker_app(
            config,
            runtime_factory=lambda: ReadOnlyHostedSessionRuntime(
                repository=service.repository,
                token=token,
                observation=observation,
            ),
        ) as tracker_page:
            tracker_page.session.set_viewport_size(**DESKTOP_VIEWPORT)
            access_page = LiveIssueDetailCollaborationPage(tracker_page)
            create_page = LiveCreateIssueGatePage(tracker_page)

            runtime = tracker_page.open()
            result["runtime_state"] = runtime.kind
            result["runtime_body_text"] = runtime.body_text
            if runtime.kind != "ready":
                message = (
                    "Step 1 failed: the deployed app did not reach the hosted tracker "
                    "shell before the read-only Create issue dialog scenario started.\n"
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

            access_page.ensure_connected(
                token=token,
                repository=service.repository,
                user_login=user.login,
            )
            access_page.dismiss_connection_banner()
            if not observation.was_exercised:
                message = (
                    "Precondition failed: the read-only hosted-session runtime never "
                    "intercepted the repository permission request, so the scenario was "
                    "not proven to be running with write access disabled."
                )
                record_step(
                    result,
                    step=1,
                    status="failed",
                    action=REQUEST_STEPS[0],
                    observed=message,
                )
                record_not_reached_steps(result, starting_step=2, request_steps=REQUEST_STEPS)
                raise AssertionError(message)

            result["permission_patch_observation"] = {
                "intercepted_urls": list(observation.intercepted_urls),
                "observed_permissions": list(observation.observed_permissions),
            }

            create_trigger_body = create_page.wait_for_create_trigger()
            if "Create issue" not in create_trigger_body:
                message = (
                    "Step 1 failed: the top-bar shell did not expose the visible "
                    "`Create issue` action required by the test case.\n"
                    f"Observed body text:\n{create_trigger_body}"
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

            create_page.open_create_issue()
            gate = create_page.wait_for_access_gate(primary_action_label=EXPECTED_CTA)
            result["gate_observation"] = _gate_payload(gate)

            record_step(
                result,
                step=1,
                status="passed",
                action=REQUEST_STEPS[0],
                observed=(
                    "Opened the visible top-bar Create issue action in a connected read-only "
                    f"hosted session at viewport {DESKTOP_VIEWPORT!r}."
                ),
            )

            validation_errors: list[str] = []

            gate_error = _gate_panel_error(gate)
            record_step(
                result,
                step=2,
                status="failed" if gate_error else "passed",
                action=REQUEST_STEPS[1],
                observed=(
                    gate_error
                    or (
                        "The gate panel kept the read-only explanation and the visible "
                        f"`{EXPECTED_CTA}` CTA together in the same create surface. "
                        f"Observed gate text={snippet(gate.gate_panel_text)!r}; "
                        f"gate_open_settings_button_count={gate.gate_open_settings_button_count!r}."
                    )
                ),
            )
            if gate_error:
                validation_errors.append(gate_error)

            fields_error = _field_visibility_error(gate)
            record_step(
                result,
                step=3,
                status="failed" if fields_error else "passed",
                action=REQUEST_STEPS[2],
                observed=(
                    fields_error
                    or (
                        "No editable Create issue form fields remained in the live dialog DOM. "
                        f"Observed summary_field_count={gate.summary_field_count!r}; "
                        f"description_field_count={gate.description_field_count!r}."
                    )
                ),
            )
            if fields_error:
                validation_errors.append(fields_error)

            actions_error = _action_button_error(gate)
            record_step(
                result,
                step=4,
                status="failed" if actions_error else "passed",
                action=REQUEST_STEPS[3],
                observed=(
                    actions_error
                    or (
                        "The live create dialog footer exposed no visible Save or Create "
                        "actions while the recovery gate was active. "
                        f"Observed save_button_count={gate.save_button_count!r}; "
                        f"create_button_count={gate.create_button_count!r}; "
                        f"gate_open_settings_button_count={gate.gate_open_settings_button_count!r}."
                    )
                ),
            )
            if actions_error:
                validation_errors.append(actions_error)

            record_human_verification(
                result,
                check=(
                    "Viewed the live Create issue dialog as a user and confirmed the "
                    "only visible dialog content was the read-only recovery explanation "
                    "plus the Open settings CTA."
                ),
                observed=(
                    f"gate_panel_text={snippet(gate.gate_panel_text, limit=320)!r}; "
                    f"gate_open_settings_button_count={gate.gate_open_settings_button_count!r}"
                ),
            )
            record_human_verification(
                result,
                check=(
                    "Checked the same live dialog for user-visible editing controls rather "
                    "than hidden implementation details."
                ),
                observed=(
                    f"summary_field_count={gate.summary_field_count!r}; "
                    f"description_field_count={gate.description_field_count!r}; "
                    f"save_button_count={gate.save_button_count!r}; "
                    f"create_button_count={gate.create_button_count!r}"
                ),
            )

            if validation_errors:
                result["is_product_failure"] = True
                raise AssertionError("\n\n".join(validation_errors))

            create_page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
            result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
            _write_pass_outputs(result)
            return
    except Exception as error:
        if tracker_page is not None:
            try:
                tracker_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
            except Exception:
                pass
        if isinstance(error, AssertionError) and not str(error).startswith("Precondition failed:"):
            result["is_product_failure"] = True
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        _write_failure_outputs(result)
        raise


def _gate_panel_error(gate: CreateIssueGateObservation) -> str | None:
    if not gate.create_heading_visible:
        return (
            "Step 2 failed: the Create issue heading did not remain visible when the "
            "read-only recovery surface rendered.\n"
            f"Observed body text:\n{gate.body_text}"
        )
    if gate.gate_open_settings_button_count < 1:
        return (
            "Step 2 failed: the guided recovery gate did not expose the expected "
            f"`{EXPECTED_CTA}` CTA inside the visible create surface.\n"
            f"Observed gate text:\n{gate.gate_panel_text}\n\n"
            f"Observed body text:\n{gate.body_text}"
        )
    if "This repository session is read-only" not in gate.gate_panel_text:
        return (
            "Step 2 failed: the visible create surface did not show the expected "
            "read-only explanation alongside the recovery CTA.\n"
            f"Observed gate text:\n{gate.gate_panel_text}\n\n"
            f"Observed body text:\n{gate.body_text}"
        )
    return None


def _field_visibility_error(gate: CreateIssueGateObservation) -> str | None:
    if gate.summary_field_count == 0 and gate.description_field_count == 0:
        return None
    return (
        "Step 3 failed: the read-only Create issue dialog still exposed editable form "
        "fields instead of showing only the guided recovery gate.\n"
        f"Observed summary_field_count={gate.summary_field_count!r}; "
        f"description_field_count={gate.description_field_count!r}\n"
        f"Observed gate text:\n{gate.gate_panel_text}\n\n"
        f"Observed body text:\n{gate.body_text}"
    )


def _action_button_error(gate: CreateIssueGateObservation) -> str | None:
    if gate.save_button_count == 0 and gate.create_button_count == 0:
        return None
    return (
        "Step 4 failed: the read-only Create issue dialog still exposed Save or Create "
        "actions even though the guided recovery gate was active.\n"
        f"Observed save_button_count={gate.save_button_count!r}; "
        f"create_button_count={gate.create_button_count!r}\n"
        f"Observed gate text:\n{gate.gate_panel_text}\n\n"
        f"Observed body text:\n{gate.body_text}"
    )


def _gate_payload(gate: CreateIssueGateObservation) -> dict[str, Any]:
    return {
        "body_text": gate.body_text,
        "gate_panel_text": gate.gate_panel_text,
        "callout_semantics_label": gate.callout_semantics_label,
        "create_heading_visible": gate.create_heading_visible,
        "summary_field_count": gate.summary_field_count,
        "description_field_count": gate.description_field_count,
        "create_button_count": gate.create_button_count,
        "save_button_count": gate.save_button_count,
        "open_settings_button_count": gate.open_settings_button_count,
        "gate_open_settings_button_count": gate.gate_open_settings_button_count,
        "gate_cta_center_x": gate.gate_cta_center_x,
        "gate_cta_center_y": gate.gate_cta_center_y,
    }


def _write_pass_outputs(result: dict[str, Any]) -> None:
    BUG_DESCRIPTION_PATH.unlink(missing_ok=True)
    write_test_automation_result(RESULT_PATH, passed=True)
    JIRA_COMMENT_PATH.write_text(_build_jira_comment(result, passed=True), encoding="utf-8")
    PR_BODY_PATH.write_text(_build_pr_body(result, passed=True), encoding="utf-8")
    RESPONSE_PATH.write_text(_build_response_summary(result, passed=True), encoding="utf-8")


def _write_failure_outputs(result: dict[str, Any]) -> None:
    error = str(result.get("error", f"AssertionError: {TICKET_KEY} failed"))
    write_test_automation_result(RESULT_PATH, passed=False, error=error)
    JIRA_COMMENT_PATH.write_text(_build_jira_comment(result, passed=False), encoding="utf-8")
    PR_BODY_PATH.write_text(_build_pr_body(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_build_response_summary(result, passed=False), encoding="utf-8")
    if _should_write_bug_description(result):
        BUG_DESCRIPTION_PATH.write_text(_build_bug_description(result), encoding="utf-8")
    else:
        BUG_DESCRIPTION_PATH.unlink(missing_ok=True)


def _build_jira_comment(result: dict[str, Any], *, passed: bool) -> str:
    status_text = "✅ PASSED" if passed else "❌ FAILED"
    lines = [
        "h3. Test Automation Result",
        "",
        f"*Status:* {status_text}",
        f"*Test Case:* {TICKET_KEY} — {TEST_CASE_TITLE}",
        f"*Environment:* URL={result.get('app_url')} | Browser={result.get('browser')} | OS={result.get('os')}",
        f"*Viewport:* {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
        f"*Linked Bugs Considered:* {', '.join(LINKED_BUGS)}",
        "",
        "h4. What was tested",
        "* Opened the deployed hosted app in a connected read-only hosted session using the live GitHub-backed repository.",
        "* Opened the visible Create issue action from the top-bar shell and waited for the same live create surface to render the recovery gate.",
        "* Checked the gate explanation, the visible Open settings CTA, the Summary/Description field DOM counts, and the dialog-scoped Save/Create button counts.",
        "",
        "h4. Linked bug handling",
        f"* {LINKED_BUG_NOTES}",
        "",
        "h4. Result",
        f"* {_actual_result_summary(result, passed=passed)}",
        *format_step_lines(result, jira=True),
        "",
        "h4. Real user-style verification",
        *format_human_lines(result, jira=True),
        "",
        "h4. Test file",
        "{code}",
        "testing/tests/TS-1288/test_ts_1288.py",
        "{code}",
        "",
        "h4. Run command",
        "{code:bash}",
        RUN_COMMAND,
        "{code}",
    ]
    if result.get("screenshot"):
        lines.extend(["", f"*Screenshot:* {result['screenshot']}"])
    if not passed:
        lines.extend(
            [
                "",
                "h4. Assertion / error",
                "{code}",
                str(result.get("traceback", result.get("error", ""))),
                "{code}",
            ],
        )
    return "\n".join(lines) + "\n"


def _build_pr_body(result: dict[str, Any], *, passed: bool) -> str:
    status_text = "✅ PASSED" if passed else "❌ FAILED"
    lines = [
        "## Test Automation Result",
        "",
        f"**Status:** {status_text}",
        f"**Test Case:** {TICKET_KEY} — {TEST_CASE_TITLE}",
        f"**Environment:** `{result.get('app_url')}` · {result.get('browser')} · {result.get('os')}",
        f"**Viewport:** `{DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}`",
        f"**Linked Bugs Considered:** {', '.join(LINKED_BUGS)}",
        "",
        "## What was automated",
        "- Drove the live hosted app with a read-only repository-permission patch so the deployed Create issue recovery gate was exercised as a user sees it.",
        "- Scoped the Save/Create button counts to the active create dialog instead of unrelated page-level actions behind the modal.",
        "- Verified the read-only gate text, the visible Open settings CTA, and that Summary/Description controls were absent from the dialog DOM.",
        "",
        "## Linked bug handling",
        f"- {LINKED_BUG_NOTES}",
        "",
        "## Result",
        f"- {_actual_result_summary(result, passed=passed)}",
        *format_step_lines(result, jira=False),
        "",
        "## Real user-style verification",
        *format_human_lines(result, jira=False),
        "",
        "## How to run",
        "```bash",
        RUN_COMMAND,
        "```",
    ]
    if result.get("screenshot"):
        lines.extend(["", f"**Screenshot:** `{result['screenshot']}`"])
    if not passed:
        lines.extend(
            [
                "",
                "## Assertion / error",
                "```text",
                str(result.get("traceback", result.get("error", ""))),
                "```",
            ],
        )
    return "\n".join(lines) + "\n"


def _build_response_summary(result: dict[str, Any], *, passed: bool) -> str:
    lines = [
        f"# {TICKET_KEY} {'passed' if passed else 'failed'}",
        "",
        f"- Test case: {TEST_CASE_TITLE}",
        f"- Run command: `{RUN_COMMAND}`",
        f"- Summary: {'1 passed, 0 failed' if passed else '0 passed, 1 failed'}",
        f"- Observed: {_actual_result_summary(result, passed=passed)}",
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


def _should_write_bug_description(result: dict[str, Any]) -> bool:
    error = str(result.get("error", ""))
    if error.startswith("RuntimeError: TS-1288 requires GH_TOKEN or GITHUB_TOKEN"):
        return False
    if error.startswith("ModuleNotFoundError:"):
        return False
    return bool(result.get("is_product_failure"))


def _build_bug_description(result: dict[str, Any]) -> str:
    lines = [
        f"# {TICKET_KEY} bug report",
        "",
        "## Steps to reproduce",
        *build_annotated_steps(result, request_steps=REQUEST_STEPS),
        "",
        "## Exact error message or assertion failure",
        "```text",
        str(result.get("traceback", result.get("error", ""))),
        "```",
        "",
        "## Actual vs Expected",
        f"- **Expected:** {EXPECTED_RESULT}",
        f"- **Actual:** {_actual_result_summary(result, passed=False)}",
        "",
        "## Environment details",
        f"- URL: {result.get('app_url')}",
        f"- Browser: {result.get('browser')}",
        f"- OS: {result.get('os')}",
        f"- Viewport: {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
        f"- Repository: {result.get('repository')} @ {result.get('repository_ref')}",
        f"- Run command: `{RUN_COMMAND}`",
        "",
        "## Screenshots or logs",
        f"- Screenshot: `{result.get('screenshot')}`",
        f"- Gate observation: `{json.dumps(result.get('gate_observation', {}), ensure_ascii=True)}`",
        f"- Permission patch observation: `{json.dumps(result.get('permission_patch_observation', {}), ensure_ascii=True)}`",
        f"- Runtime state: `{result.get('runtime_state')}`",
        f"- Runtime body text: `{snippet(str(result.get('runtime_body_text', '')), limit=320)}`",
    ]
    return "\n".join(lines) + "\n"


def _actual_result_summary(result: dict[str, Any], *, passed: bool) -> str:
    gate = result.get("gate_observation", {})
    if passed:
        return (
            "The live read-only Create issue dialog showed only the guided recovery "
            "gate, kept the visible Open settings CTA in that same surface, removed "
            "Summary and Description from the dialog DOM, and exposed "
            f"save_button_count={gate.get('save_button_count', 0)} / "
            f"create_button_count={gate.get('create_button_count', 0)}."
        )
    if gate:
        return (
            "The live read-only Create issue dialog did not keep the recovery gate and "
            "editable form mutually exclusive. Observed "
            f"summary_field_count={gate.get('summary_field_count')!r}, "
            f"description_field_count={gate.get('description_field_count')!r}, "
            f"save_button_count={gate.get('save_button_count')!r}, and "
            f"create_button_count={gate.get('create_button_count')!r}."
        )
    return str(
        result.get(
            "error",
            "The deployed app did not expose the expected read-only Create issue gate.",
        ),
    )


if __name__ == "__main__":
    main()
