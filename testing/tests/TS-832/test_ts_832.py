from __future__ import annotations

from dataclasses import asdict
import json
import platform
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_workspace_switcher_page import (  # noqa: E402
    FocusNavigationStep,
    LiveWorkspaceSwitcherPage,
    WorkspaceSwitcherTriggerObservation,
    WorkspaceTriggerForwardFocusObservation,
    WorkspaceTriggerFocusabilityObservation,
    WorkspaceTriggerReverseFocusObservation,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.interfaces.web_app_session import FocusedElementObservation  # noqa: E402
from testing.tests.support.live_tracker_app_factory import (  # noqa: E402
    create_live_tracker_app_with_stored_token,
)

TICKET_KEY = "TS-832"
TEST_CASE_TITLE = (
    "Reverse keyboard navigation (Shift+Tab) — focus returns to workspace "
    "switcher trigger"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-832/test_ts_832.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 960}
TRIGGER_FOCUS_TIMEOUT_MS = 4_000
REVERSE_FOCUS_TIMEOUT_MS = 4_000

REQUEST_STEPS = [
    "Launch the application on a desktop browser.",
    "Use keyboard Tab navigation to move focus to the workspace switcher trigger.",
    (
        "Use the 'Tab' key to navigate to the interactive element immediately "
        "following the workspace switcher trigger."
    ),
    "Press 'Shift + Tab' on the keyboard.",
    (
        "Observe whether keyboard focus returns to the workspace switcher trigger "
        "and whether the trigger shows a visible focus indicator."
    ),
]
TICKET_REQUEST_STEPS = [
    (
        "Use the 'Tab' key to navigate to the interactive element immediately "
        "following the workspace switcher trigger (e.g., the 'Search' field)."
    ),
    "Press 'Shift + Tab' on the keyboard.",
]
EXPECTED_RESULT = (
    "Keyboard focus moves backward from the subsequent element to the workspace "
    "switcher trigger, which displays a visible focus indicator."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts832_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts832_failure.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-832 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
        )
    user = service.fetch_authenticated_user()

    result: dict[str, object] = {
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
        "trigger_focus_timeout_ms": TRIGGER_FOCUS_TIMEOUT_MS,
        "reverse_focus_timeout_ms": REVERSE_FOCUS_TIMEOUT_MS,
        "user_login": user.login,
        "steps": [],
        "human_verification": [],
    }

    page: LiveWorkspaceSwitcherPage | None = None
    try:
        with create_live_tracker_app_with_stored_token(config, token=token) as tracker_page:
            page = LiveWorkspaceSwitcherPage(tracker_page)
            try:
                try:
                    runtime = tracker_page.open()
                    result["runtime_state"] = runtime.kind
                    result["runtime_body_text"] = runtime.body_text
                    if runtime.kind != "ready":
                        raise AssertionError(
                            "Step 1 failed: the deployed app did not reach an interactive "
                            "desktop state before the reverse keyboard navigation scenario "
                            "began.\n"
                            f"Observed runtime state: {runtime.kind}\n"
                            f"Observed body text:\n{runtime.body_text}",
                        )

                    page.dismiss_connection_banner()
                    page.navigate_to_section("Dashboard")
                    page.set_viewport(**DESKTOP_VIEWPORT)
                    trigger = page.observe_trigger()
                    result["trigger_observation"] = _trigger_payload(trigger)
                except AssertionError as error:
                    _record_step(
                        result,
                        step=1,
                        status="failed",
                        action=REQUEST_STEPS[0],
                        observed=str(error),
                    )
                    raise
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=REQUEST_STEPS[0],
                    observed=(
                        f"Opened {config.app_url} in Chromium at "
                        f"{DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}; "
                        f"trigger_label={trigger.semantic_label!r}; "
                        f"trigger_text={trigger.visible_text!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Viewed the desktop app shell before the keyboard scenario and "
                        "confirmed Dashboard plus the visible workspace switcher trigger "
                        "were rendered."
                    ),
                    observed=(
                        f"trigger_text={trigger.visible_text!r}; "
                        f"top_buttons={list(trigger.top_button_labels)!r}"
                    ),
                )

                trigger_focusability: WorkspaceTriggerFocusabilityObservation | None = None
                try:
                    trigger_focusability = page.observe_trigger_focusability()
                    result["trigger_focusability_observation"] = _trigger_focusability_payload(
                        trigger_focusability,
                    )
                    trigger_focus_steps = page.focus_trigger_via_keyboard(max_tabs=24)
                    focused_trigger = page.active_element()
                    result["trigger_focus_sequence"] = [
                        asdict(step) for step in trigger_focus_steps
                    ]
                    result["focused_trigger_before_reverse"] = _focused_element_payload(
                        focused_trigger,
                    )
                    _assert_workspace_trigger_focused(
                        focused=focused_trigger,
                        focus_steps=trigger_focus_steps,
                    )
                except Exception as error:
                    observed = str(error)
                    if trigger_focusability is not None:
                        observed = (
                            f"{observed}\n"
                            "Observed trigger focusability: "
                            f"label={trigger_focusability.label!r}, "
                            f"role={trigger_focusability.role!r}, "
                            f"tag={trigger_focusability.tag_name!r}, "
                            f"tabindex={trigger_focusability.tabindex!r}, "
                            f"keyboard_focusable={trigger_focusability.keyboard_focusable}\n"
                            f"Observed trigger HTML: {trigger_focusability.outer_html}"
                        )
                    _record_step(
                        result,
                        step=2,
                        status="failed",
                        action=REQUEST_STEPS[1],
                        observed=observed,
                    )
                    raise
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=REQUEST_STEPS[1],
                    observed=(
                        f"tab_steps_to_trigger={len(trigger_focus_steps)}; "
                        f"focused_trigger={focused_trigger.accessible_name!r}; "
                        f"keyboard_focusable={trigger_focusability.keyboard_focusable}; "
                        f"tabindex={trigger_focusability.tabindex!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Reached the workspace switcher trigger using real keyboard Tab "
                        "navigation instead of script-forcing focus."
                    ),
                    observed=(
                        f"focus_sequence={_focus_sequence_summary(trigger_focus_steps)}; "
                        f"focused_trigger={focused_trigger.accessible_name!r}"
                    ),
                )

                forward_focus: WorkspaceTriggerForwardFocusObservation | None = None
                try:
                    forward_focus = page.observe_forward_focus_from_trigger(
                        timeout_ms=REVERSE_FOCUS_TIMEOUT_MS,
                    )
                    result["forward_focus_observation"] = _forward_focus_payload(forward_focus)
                    _assert_forward_focus_target(forward_focus)
                except Exception as error:
                    _record_step(
                        result,
                        step=3,
                        status="failed",
                        action=REQUEST_STEPS[2],
                        observed=str(error),
                    )
                    raise
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action=REQUEST_STEPS[2],
                    observed=(
                        "Pressed Tab once from the focused workspace switcher trigger and "
                        f"moved focus to {forward_focus.next_focus_label!r} "
                        f"(role={forward_focus.next_focus_role!r}, "
                        f"tag={forward_focus.next_focus_tag_name!r})."
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Used Tab from the real focused trigger and watched which visible "
                        "control received focus next."
                    ),
                    observed=(
                        f"next_focus={forward_focus.next_focus_label!r}; "
                        f"role={forward_focus.next_focus_role!r}; "
                        f"tag={forward_focus.next_focus_tag_name!r}; "
                        f"visible={forward_focus.next_focus_visible}; "
                        f"in_viewport={forward_focus.next_focus_in_viewport}"
                    ),
                )

                reverse_focus: WorkspaceTriggerReverseFocusObservation | None = None
                try:
                    reverse_focus = page.observe_reverse_focus_return_to_trigger(
                        timeout_ms=REVERSE_FOCUS_TIMEOUT_MS,
                    )
                    result["reverse_focus_observation"] = _reverse_focus_payload(reverse_focus)
                    _assert_reverse_focus_returned_to_trigger(reverse_focus)
                except Exception as error:
                    _record_step(
                        result,
                        step=4,
                        status="failed",
                        action=REQUEST_STEPS[3],
                        observed=str(error),
                    )
                    raise
                _record_step(
                    result,
                    step=4,
                    status="passed",
                    action=REQUEST_STEPS[3],
                    observed=(
                        "Pressed Shift+Tab from the subsequent focused element and "
                        f"restored focus to {reverse_focus.restored_focus_label!r}."
                    ),
                )

                try:
                    _assert_visible_focus_indicator(reverse_focus)
                except Exception as error:
                    _record_step(
                        result,
                        step=5,
                        status="failed",
                        action=REQUEST_STEPS[4],
                        observed=str(error),
                    )
                    raise
                _record_step(
                    result,
                    step=5,
                    status="passed",
                    action=REQUEST_STEPS[4],
                    observed=(
                        "The workspace switcher trigger regained keyboard focus and exposed "
                        "a visible focus indicator after Shift+Tab."
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Pressed Shift+Tab like a keyboard user and confirmed the visible "
                        "focus ring returned to the workspace switcher trigger rather than "
                        "landing somewhere else."
                    ),
                    observed=(
                        f"restored_focus={reverse_focus.restored_focus_label!r}; "
                        f"focus_visible={reverse_focus.after_reverse_focus_visible}; "
                        f"outline={reverse_focus.after_reverse_outline!r}; "
                        f"outline_width={reverse_focus.after_reverse_outline_width!r}; "
                        f"box_shadow={reverse_focus.after_reverse_box_shadow!r}"
                    ),
                )
            except Exception:
                if page is not None:
                    try:
                        page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                        result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                    except Exception as screenshot_error:
                        result["screenshot_error"] = (
                            f"{type(screenshot_error).__name__}: {screenshot_error}"
                        )
                raise
            page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
            result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
    except AssertionError as error:
        result["error"] = str(error)
        result["traceback"] = traceback.format_exc()
        _write_failure_outputs(result)
        raise
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        _write_failure_outputs(result)
        raise

    _write_pass_outputs(result)
    print(f"{TICKET_KEY} passed")


def _assert_workspace_trigger_focused(
    *,
    focused: FocusedElementObservation,
    focus_steps: tuple[FocusNavigationStep, ...],
) -> None:
    if _is_workspace_trigger_focus(focused.accessible_name, fallback_text=focused.text):
        return
    raise AssertionError(
        "Step 2 failed: keyboard navigation did not land on the workspace switcher "
        "trigger before the reverse navigation scenario.\n"
        f"Observed focused element: label={focused.accessible_name!r}, "
        f"role={focused.role!r}, tag={focused.tag_name!r}, text={focused.text!r}\n"
        f"Observed focus sequence: {_focus_sequence_summary(focus_steps)}",
    )


def _assert_forward_focus_target(observation: WorkspaceTriggerForwardFocusObservation) -> None:
    failures: list[str] = []
    if not _is_workspace_trigger_focus(
        observation.starting_focus_label,
        fallback_text=observation.trigger_text,
    ):
        failures.append("the scenario did not start from a trigger-focused state")
    if not observation.next_focus_visible:
        failures.append("the next focused element after Tab was not visible")
    if not observation.next_focus_in_viewport:
        failures.append("the next focused element after Tab was outside the viewport")
    if _is_workspace_trigger_focus(
        observation.next_focus_label,
        fallback_text=observation.next_focus_outer_html,
    ):
        failures.append("focus did not move away from the workspace switcher trigger")
    if observation.next_focus_tag_name in {"BODY", "HTML", "FLUTTER-VIEW"}:
        failures.append(
            "focus landed on a non-interactive root element instead of the next user-visible control"
        )
    if failures:
        raise AssertionError(
            "Step 3 failed: pressing Tab from the workspace switcher trigger did not "
            "move focus to the next visible interactive element.\n"
            + "\n".join(f"- {item}" for item in failures)
            + "\n"
            + f"Observed next focus: label={observation.next_focus_label!r}, "
            + f"role={observation.next_focus_role!r}, tag={observation.next_focus_tag_name!r}\n"
            + f"Observed next focus HTML: {observation.next_focus_outer_html}",
        )


def _assert_reverse_focus_returned_to_trigger(
    observation: WorkspaceTriggerReverseFocusObservation,
) -> None:
    failures: list[str] = []
    if not observation.after_reverse_trigger_focused:
        failures.append("the trigger was not the active keyboard-focused control after Shift+Tab")
    if not _is_workspace_trigger_focus(
        observation.restored_focus_label,
        fallback_text=observation.trigger_text,
    ):
        failures.append("the active element after Shift+Tab was not labelled as the workspace switcher trigger")
    if failures:
        raise AssertionError(
            "Step 4 failed: pressing Shift+Tab from the subsequent element did not "
            "return keyboard focus to the workspace switcher trigger.\n"
            + "\n".join(f"- {item}" for item in failures)
            + "\n"
            + f"Observed restored focus: label={observation.restored_focus_label!r}, "
            + f"role={observation.restored_focus_role!r}, tag={observation.restored_focus_tag_name!r}\n"
            + f"Observed restored focus HTML: {observation.restored_focus_outer_html}",
        )


def _assert_visible_focus_indicator(
    observation: WorkspaceTriggerReverseFocusObservation,
) -> None:
    indicator_changed = any(
        before != after
        for before, after in (
            (observation.before_reverse_outline, observation.after_reverse_outline),
            (
                observation.before_reverse_outline_color,
                observation.after_reverse_outline_color,
            ),
            (
                observation.before_reverse_outline_width,
                observation.after_reverse_outline_width,
            ),
            (
                observation.before_reverse_box_shadow,
                observation.after_reverse_box_shadow,
            ),
        )
    )
    has_outline = _has_nonzero_outline(
        observation.after_reverse_outline,
        observation.after_reverse_outline_width,
    )
    has_box_shadow = _has_box_shadow(observation.after_reverse_box_shadow)
    if observation.after_reverse_focus_visible and (indicator_changed or has_outline or has_box_shadow):
        return
    raise AssertionError(
        "Step 5 failed: the workspace switcher trigger did not expose a visible "
        "keyboard focus indicator after Shift+Tab restored focus.\n"
        f"Observed before-reverse outline={observation.before_reverse_outline!r}, "
        f"outline_width={observation.before_reverse_outline_width!r}, "
        f"box_shadow={observation.before_reverse_box_shadow!r}, "
        f"focus_visible={observation.before_reverse_focus_visible}\n"
        f"Observed after-reverse outline={observation.after_reverse_outline!r}, "
        f"outline_width={observation.after_reverse_outline_width!r}, "
        f"box_shadow={observation.after_reverse_box_shadow!r}, "
        f"focus_visible={observation.after_reverse_focus_visible}",
    )


def _has_nonzero_outline(outline: str, outline_width: str) -> bool:
    outline_normalized = outline.strip().lower()
    if not outline_normalized or outline_normalized == "none":
        return False
    width_normalized = outline_width.strip().lower()
    if width_normalized in {"0", "0px", "0px none rgb(0, 0, 0)"}:
        return False
    return "0px" not in width_normalized


def _has_box_shadow(box_shadow: str) -> bool:
    normalized = box_shadow.strip().lower()
    return bool(normalized) and normalized != "none"


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
    PR_BODY_PATH.write_text(_markdown_summary(result, passed=True), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_summary(result, passed=True), encoding="utf-8")


def _write_failure_outputs(result: dict[str, object]) -> None:
    error = str(result.get("error", "AssertionError: TS-832 failed"))
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
    PR_BODY_PATH.write_text(_markdown_summary(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_summary(result, passed=False), encoding="utf-8")
    BUG_DESCRIPTION_PATH.write_text(_bug_description(result), encoding="utf-8")


def _jira_comment(result: dict[str, object], *, passed: bool) -> str:
    status = "✅ PASSED" if passed else "❌ FAILED"
    lines = [
        "h3. Test Automation Result",
        "",
        f"*Status:* {status}",
        f"*Test Case:* {TICKET_KEY} - {TEST_CASE_TITLE}",
        "",
        "h4. What was tested",
        "* Opened the deployed TrackState app in Chromium with a stored hosted token.",
        "* Reached the desktop workspace switcher trigger through real keyboard Tab navigation.",
        "* Pressed Tab once from the focused trigger and captured the next visible focused control.",
        "* Pressed Shift + Tab and verified whether focus returned to the workspace switcher trigger.",
        "* Checked whether the restored trigger showed a visible keyboard focus indicator.",
        "",
        "h4. Result",
        (
            "* Matched the expected result."
            if passed
            else f"* Did not match the expected result. {_failed_step_summary(result)}"
        ),
        (
            f"* Environment: URL {{{{{result['app_url']}}}}}, repository "
            f"{{{{{result['repository']}}}}} @ {{{{{result['repository_ref']}}}}}, "
            f"browser {{Chromium (Playwright)}}, OS {{{{{result['os']}}}}}."
        ),
        "",
        "h4. Step results",
        *_step_lines(result, jira=True),
        "",
        "h4. Ticket step verification",
        *_ticket_step_lines(result, jira=True),
        "",
        "h4. Human-style verification",
        *_human_lines(result, jira=True),
    ]
    if not passed:
        lines.extend(
            [
                "",
                "h4. Exact error",
                "{code}",
                str(result.get("traceback", result.get("error", ""))),
                "{code}",
            ],
        )
    lines.extend(_artifact_lines(result, jira=True))
    return "\n".join(lines) + "\n"


def _markdown_summary(result: dict[str, object], *, passed: bool) -> str:
    status = "✅ PASSED" if passed else "❌ FAILED"
    lines = [
        "## Test Automation Result",
        "",
        f"**Status:** {status}",
        f"**Test Case:** {TICKET_KEY} - {TEST_CASE_TITLE}",
        "",
        "## What was automated",
        "- Opened the deployed TrackState app in Chromium with a stored hosted token.",
        "- Reached the desktop workspace switcher trigger through real keyboard Tab navigation.",
        "- Pressed Tab once to move to the subsequent visible interactive element.",
        "- Pressed Shift+Tab and checked that focus returned to the workspace switcher trigger.",
        "- Verified that the restored trigger exposed a visible keyboard focus indicator.",
        "",
        "## Result",
        (
            "- Matched the expected result."
            if passed
            else f"- Did not match the expected result. {_failed_step_summary(result)}"
        ),
        (
            f"- Environment: URL `{result['app_url']}`, repository "
            f"`{result['repository']}` @ `{result['repository_ref']}`, browser "
            f"`Chromium (Playwright)`, OS `{result['os']}`."
        ),
        "",
        "## Step results",
        *_step_lines(result, jira=False),
        "",
        "## Ticket step verification",
        *_ticket_step_lines(result, jira=False),
        "",
        "## Human-style verification",
        *_human_lines(result, jira=False),
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
                "## Exact error",
                "```text",
                str(result.get("traceback", result.get("error", ""))),
                "```",
            ],
        )
    lines.extend(_artifact_lines(result, jira=False))
    return "\n".join(lines) + "\n"


def _response_summary(result: dict[str, object], *, passed: bool) -> str:
    status = "PASSED" if passed else "FAILED"
    lines = [
        "## Test Automation Summary",
        "",
        f"- Test case: **{TICKET_KEY} - {TEST_CASE_TITLE}**",
        f"- Result: **{status}**",
        f"- Command: `{RUN_COMMAND}`",
        (
            f"- Environment: `{result['app_url']}` on Chromium/Playwright "
            f"({result['os']}) against `{result['repository']}` @ "
            f"`{result['repository_ref']}`."
        ),
        (
            "- Outcome: Shift+Tab returned focus from the next visible control to the "
            "workspace switcher trigger, and the trigger showed a visible focus indicator."
            if passed
            else f"- Outcome: {_failed_step_summary(result)}"
        ),
    ]
    lines.extend(_artifact_lines(result, jira=False))
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
    title, reproduction_steps, missing_capability = _bug_context(result)
    return "\n".join(
        [
            f"# {title}",
            "",
            "## Steps to reproduce",
            *reproduction_steps,
            "",
            "## Exact steps from the test case with observations",
            *_ticket_bug_step_lines(result),
            "",
            "## Detailed automation step results",
            _annotated_step_line(result, 1, REQUEST_STEPS[0]),
            _annotated_step_line(result, 2, REQUEST_STEPS[1]),
            _annotated_step_line(result, 3, REQUEST_STEPS[2]),
            _annotated_step_line(result, 4, REQUEST_STEPS[3]),
            _annotated_step_line(result, 5, REQUEST_STEPS[4]),
            "",
            "## Exact error message or assertion failure",
            "```text",
            str(result.get("traceback", result.get("error", ""))),
            "```",
            "",
            "## Actual vs Expected",
            f"- Expected: {EXPECTED_RESULT}",
            f"- Actual: {_failed_step_summary(result)}",
            "",
            "## Environment details",
            f"- URL: {result.get('app_url')}",
            f"- Repository: {result.get('repository')} @ {result.get('repository_ref')}",
            f"- Browser: {result.get('browser')}",
            f"- OS: {result.get('os')}",
            f"- Viewport: {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
            f"- Run command: {RUN_COMMAND}",
            "",
            "## Missing or broken production capability",
            missing_capability,
            "",
            "## Failing command",
            "```bash",
            RUN_COMMAND,
            "```",
            "",
            "## Failing command output",
            "```text",
            str(result.get("traceback", result.get("error", "<missing error>"))),
            "```",
            "",
            "## Screenshots or logs",
            f"- Screenshot: {result.get('screenshot', '<no screenshot recorded>')}",
            "```json",
            json.dumps(
                {
                    "trigger_observation": result.get("trigger_observation"),
                    "trigger_focusability_observation": result.get(
                        "trigger_focusability_observation",
                    ),
                    "trigger_focus_sequence": result.get("trigger_focus_sequence"),
                    "focused_trigger_before_reverse": result.get(
                        "focused_trigger_before_reverse",
                    ),
                    "forward_focus_observation": result.get("forward_focus_observation"),
                    "reverse_focus_observation": result.get("reverse_focus_observation"),
                },
                indent=2,
            ),
            "```",
        ],
    ) + "\n"


def _bug_context(result: dict[str, object]) -> tuple[str, list[str], str]:
    failed_step = _first_failed_step_number(result)
    if failed_step == 2:
        return (
            f"{TICKET_KEY} - Workspace switcher trigger is missing from desktop keyboard tab order",
            [
                "1. Launch the application on a desktop browser.",
                "2. Navigate to Dashboard in the desktop web app.",
                "3. Use real keyboard Tab navigation from the visible desktop shell.",
                "4. Observe that focus does not land on the visible workspace switcher trigger.",
            ],
            (
                "The production desktop UI does not expose the workspace switcher trigger "
                "as a reachable keyboard focus target, so the reverse Shift+Tab scenario "
                "cannot start from a real trigger-focused state."
            ),
        )
    if failed_step == 3:
        return (
            f"{TICKET_KEY} - Tab from workspace switcher trigger does not reach the next visible control",
            [
                "1. Launch the application on a desktop browser.",
                "2. Reach the workspace switcher trigger by keyboard.",
                "3. Press `Tab` once from the focused trigger.",
                "4. Observe the active element after that keypress.",
            ],
            (
                "After the workspace switcher trigger receives real keyboard focus, the "
                "next Tab press does not move focus to the following visible interactive "
                "control in the desktop shell."
            ),
        )
    if failed_step == 4:
        return (
            f"{TICKET_KEY} - Shift+Tab from the next control does not return focus to the workspace switcher trigger",
            [
                "1. Launch the application on a desktop browser.",
                "2. Reach the workspace switcher trigger by keyboard.",
                "3. Press `Tab` once to focus the next visible interactive element.",
                "4. Press `Shift+Tab`.",
                "5. Observe the active element after reverse navigation.",
            ],
            (
                "Reverse sequential keyboard navigation does not return focus from the "
                "subsequent desktop control back to the workspace switcher trigger."
            ),
        )
    if failed_step == 5:
        return (
            f"{TICKET_KEY} - Workspace switcher trigger regains focus without a visible focus indicator",
            [
                "1. Launch the application on a desktop browser.",
                "2. Reach the workspace switcher trigger by keyboard.",
                "3. Press `Tab` once to focus the next visible interactive element.",
                "4. Press `Shift+Tab` to move focus back to the trigger.",
                "5. Observe the trigger styling after focus is restored.",
            ],
            (
                "The workspace switcher trigger regains focus, but the production desktop "
                "UI does not expose a visible keyboard focus indicator for that restored "
                "state."
            ),
        )
    return (
        f"{TICKET_KEY} - Reverse keyboard navigation around the workspace switcher is broken",
        [
            "1. Launch the application on a desktop browser.",
            "2. Attempt the TS-832 reverse keyboard navigation scenario.",
            "3. Observe the first failing boundary.",
        ],
        (
            "The production desktop workspace switcher does not satisfy the TS-832 "
            "reverse keyboard navigation requirement."
        ),
    )


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


def _annotated_step_line(
    result: dict[str, object],
    step_number: int,
    action: str,
) -> str:
    marker = "✅" if _step_status(result, step_number) == "passed" else "❌"
    return (
        f"{step_number}. {marker} {action}\n"
        f"   Actual: {_step_observation(result, step_number)}"
    )


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    prefix = "*" if jira else "-"
    steps = result.get("steps", [])
    if not isinstance(steps, list):
        return [f"{prefix} <no step data recorded>"]
    lines: list[str] = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        marker = "✅" if step.get("status") == "passed" else "❌"
        lines.append(
            f"{prefix} {marker} Step {step.get('step')}: {step.get('action')} "
            f"Observed: {step.get('observed')}"
        )
    return lines or [f"{prefix} <no step data recorded>"]


def _human_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    prefix = "*" if jira else "-"
    checks = result.get("human_verification", [])
    if not isinstance(checks, list):
        return [f"{prefix} <no human-style verification recorded>"]
    lines: list[str] = []
    for check in checks:
        if not isinstance(check, dict):
            continue
        lines.append(f"{prefix} {check.get('check')}: {check.get('observed')}")
    return lines or [f"{prefix} <no human-style verification recorded>"]


def _ticket_bug_step_lines(result: dict[str, object]) -> list[str]:
    return [
        _annotated_ticket_step_line(result, 1, TICKET_REQUEST_STEPS[0]),
        _annotated_ticket_step_line(result, 2, TICKET_REQUEST_STEPS[1]),
    ]


def _ticket_step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    prefix = "*" if jira else "-"
    return [
        f"{prefix} {_annotated_ticket_step_line(result, 1, TICKET_REQUEST_STEPS[0])}",
        f"{prefix} {_annotated_ticket_step_line(result, 2, TICKET_REQUEST_STEPS[1])}",
    ]


def _annotated_ticket_step_line(
    result: dict[str, object],
    step_number: int,
    action: str,
) -> str:
    marker = "✅" if _ticket_step_status(result, step_number) == "passed" else "❌"
    return (
        f"{step_number}. {marker} {action}\n"
        f"   Actual: {_ticket_step_observation(result, step_number)}"
    )


def _ticket_step_status(result: dict[str, object], step_number: int) -> str:
    if step_number == 1:
        return "passed" if _step_status(result, 3) == "passed" else "failed"
    if step_number == 2:
        return (
            "passed"
            if _step_status(result, 4) == "passed" and _step_status(result, 5) == "passed"
            else "failed"
        )
    return "failed"


def _ticket_step_observation(result: dict[str, object], step_number: int) -> str:
    if step_number == 1:
        if _step_status(result, 1) != "passed":
            return _step_observation(result, 1)
        if _step_status(result, 2) != "passed":
            return (
                "The desktop app opened, but the scenario could not reach the workspace "
                f"switcher trigger by keyboard. {_step_observation(result, 2)}"
            )
        if _step_status(result, 3) == "passed":
            return (
                "Real keyboard navigation reached the workspace switcher trigger, and "
                f"pressing Tab moved focus to the next visible interactive control. "
                f"{_step_observation(result, 3)}"
            )
        return (
            "Real keyboard navigation reached the workspace switcher trigger, but "
            f"pressing Tab from the focused trigger failed. {_step_observation(result, 3)}"
        )
    if _step_status(result, 3) != "passed":
        return "Not reached because request step 1 failed."
    if _step_status(result, 4) != "passed":
        return _step_observation(result, 4)
    if _step_status(result, 5) != "passed":
        return (
            "Shift+Tab restored focus to the workspace switcher trigger, but the "
            f"visible focus-indicator check failed. {_step_observation(result, 5)}"
        )
    return (
        "Shift+Tab returned focus to the workspace switcher trigger, and the trigger "
        "showed a visible keyboard focus indicator."
    )


def _artifact_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    prefix = "*" if jira else "-"
    screenshot = result.get("screenshot")
    if not screenshot:
        return []
    if jira:
        return [f"{prefix} Screenshot: {{{{{screenshot}}}}}"]
    return [f"{prefix} Screenshot: `{screenshot}`"]


def _failed_step_summary(result: dict[str, object]) -> str:
    steps = result.get("steps", [])
    if isinstance(steps, list):
        for step in steps:
            if isinstance(step, dict) and step.get("status") != "passed":
                return f"Step {step.get('step')}: {step.get('observed')}"
    return str(result.get("error", "No failed step recorded."))


def _first_failed_step_number(result: dict[str, object]) -> int | None:
    steps = result.get("steps", [])
    if not isinstance(steps, list):
        return None
    for step in steps:
        if isinstance(step, dict) and step.get("status") != "passed":
            return int(step.get("step", -1))
    return None


def _step_status(result: dict[str, object], step_number: int) -> str:
    steps = result.get("steps", [])
    if not isinstance(steps, list):
        return "failed"
    for step in steps:
        if isinstance(step, dict) and int(step.get("step", -1)) == step_number:
            return str(step.get("status", "failed"))
    return "failed"


def _step_observation(result: dict[str, object], step_number: int) -> str:
    steps = result.get("steps", [])
    if not isinstance(steps, list):
        return "<no observation recorded>"
    last_failed_step: int | None = None
    for step in steps:
        if not isinstance(step, dict):
            continue
        current_step = int(step.get("step", -1))
        if current_step == step_number:
            return str(step.get("observed", "<no observation recorded>"))
        if step.get("status") != "passed":
            last_failed_step = current_step
    if last_failed_step is not None and step_number > last_failed_step:
        return f"Not reached because step {last_failed_step} failed."
    return "<no observation recorded>"


def _focus_sequence_summary(steps: tuple[FocusNavigationStep, ...]) -> str:
    return " -> ".join(
        str(step.after_label or f"<{step.after_tag_name}>")
        for step in steps
    )


def _trigger_payload(trigger: WorkspaceSwitcherTriggerObservation) -> dict[str, object]:
    return {
        "semantic_label": trigger.semantic_label,
        "visible_text": trigger.visible_text,
        "raw_text_lines": list(trigger.raw_text_lines),
        "display_name": trigger.display_name,
        "workspace_type": trigger.workspace_type,
        "state_label": trigger.state_label,
        "icon_count": trigger.icon_count,
        "left": trigger.left,
        "top": trigger.top,
        "width": trigger.width,
        "height": trigger.height,
        "top_button_labels": list(trigger.top_button_labels),
    }


def _trigger_focusability_payload(
    observation: WorkspaceTriggerFocusabilityObservation,
) -> dict[str, object]:
    return {
        "label": observation.label,
        "role": observation.role,
        "tag_name": observation.tag_name,
        "tabindex": observation.tabindex,
        "keyboard_focusable": observation.keyboard_focusable,
        "outer_html": observation.outer_html,
    }


def _focused_element_payload(focused: FocusedElementObservation) -> dict[str, object]:
    return {
        "accessible_name": focused.accessible_name,
        "role": focused.role,
        "tag_name": focused.tag_name,
        "text": focused.text,
        "tabindex": focused.tabindex,
        "outer_html": focused.outer_html,
    }


def _forward_focus_payload(
    observation: WorkspaceTriggerForwardFocusObservation,
) -> dict[str, object]:
    return {
        "trigger_label": observation.trigger_label,
        "trigger_text": observation.trigger_text,
        "starting_focus_label": observation.starting_focus_label,
        "starting_focus_role": observation.starting_focus_role,
        "starting_focus_tag_name": observation.starting_focus_tag_name,
        "next_focus_label": observation.next_focus_label,
        "next_focus_role": observation.next_focus_role,
        "next_focus_tag_name": observation.next_focus_tag_name,
        "next_focus_outer_html": observation.next_focus_outer_html,
        "next_focus_visible": observation.next_focus_visible,
        "next_focus_in_viewport": observation.next_focus_in_viewport,
    }


def _reverse_focus_payload(
    observation: WorkspaceTriggerReverseFocusObservation,
) -> dict[str, object]:
    return {
        "trigger_label": observation.trigger_label,
        "trigger_text": observation.trigger_text,
        "starting_focus_label": observation.starting_focus_label,
        "starting_focus_role": observation.starting_focus_role,
        "starting_focus_tag_name": observation.starting_focus_tag_name,
        "starting_focus_outer_html": observation.starting_focus_outer_html,
        "before_reverse_outline": observation.before_reverse_outline,
        "before_reverse_outline_color": observation.before_reverse_outline_color,
        "before_reverse_outline_width": observation.before_reverse_outline_width,
        "before_reverse_box_shadow": observation.before_reverse_box_shadow,
        "before_reverse_focus_visible": observation.before_reverse_focus_visible,
        "before_reverse_trigger_focused": observation.before_reverse_trigger_focused,
        "after_reverse_outline": observation.after_reverse_outline,
        "after_reverse_outline_color": observation.after_reverse_outline_color,
        "after_reverse_outline_width": observation.after_reverse_outline_width,
        "after_reverse_box_shadow": observation.after_reverse_box_shadow,
        "after_reverse_focus_visible": observation.after_reverse_focus_visible,
        "after_reverse_trigger_focused": observation.after_reverse_trigger_focused,
        "restored_focus_label": observation.restored_focus_label,
        "restored_focus_role": observation.restored_focus_role,
        "restored_focus_tag_name": observation.restored_focus_tag_name,
        "restored_focus_outer_html": observation.restored_focus_outer_html,
    }


def _is_workspace_trigger_focus(
    accessible_name: str | None,
    *,
    fallback_text: str | None = None,
) -> bool:
    candidates = (accessible_name or "", fallback_text or "")
    return any(candidate.startswith("Workspace switcher:") for candidate in candidates)


if __name__ == "__main__":
    main()
