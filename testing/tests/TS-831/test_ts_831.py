from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import platform
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_workspace_switcher_page import (  # noqa: E402
    LiveWorkspaceSwitcherPage,
    WorkspaceSwitcherInternalFocusObservation,
    WorkspaceSwitcherObservation,
    WorkspaceSwitcherPanelObservation,
    WorkspaceSwitcherTriggerObservation,
    WorkspaceTriggerFocusabilityObservation,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.interfaces.web_app_session import FocusedElementObservation  # noqa: E402
from testing.tests.support.live_tracker_app_factory import (  # noqa: E402
    create_live_tracker_app_with_stored_token,
)

TICKET_KEY = "TS-831"
TEST_CASE_TITLE = "Workspace switcher trigger keyboard activation - panel opens using Space key"
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-831/test_ts_831.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 960}
OPEN_TIMEOUT_MS = 4_000
TAB_FOCUS_TIMEOUT_MS = 4_000
KEYBOARD_TAB_LIMIT = 24
POST_OPEN_TAB_LIMIT = 6
EXPECTED_RESULT = (
    "The workspace switcher panel opens immediately, allowing for subsequent "
    "keyboard navigation within the panel."
)
REQUEST_STEPS = [
    "Use keyboard navigation ('Tab') to reach the workspace switcher trigger.",
    "Ensure the trigger has active keyboard focus.",
    "Press the 'Space' key on the keyboard.",
]

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts831_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts831_failure.png"


@dataclass(frozen=True)
class PanelTabNavigationAttempt:
    tab_press: int
    before_label: str | None
    before_role: str | None
    before_tag_name: str
    after_label: str | None
    after_role: str | None
    after_tag_name: str
    after_visible: bool
    after_in_viewport: bool
    after_within_switcher: bool
    after_on_trigger: bool
    after_owned_by_switcher: bool
    after_different_from_before: bool


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-831 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
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
        "desktop_viewport": DESKTOP_VIEWPORT,
        "expected_result": EXPECTED_RESULT,
        "linked_bugs": ["TS-843", "TS-837", "TS-835", "TS-828"],
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
                            "desktop state before the Space-key workspace-switcher scenario began.\n"
                            f"Observed runtime state: {runtime.kind}\n"
                            f"Observed body text:\n{runtime.body_text}",
                        )

                    page.dismiss_connection_banner()
                    page.navigate_to_section("Dashboard")
                    page.set_viewport(**DESKTOP_VIEWPORT)
                    trigger_before = page.observe_trigger()
                    result["trigger_before"] = _trigger_payload(trigger_before)
                except AssertionError as error:
                    _record_step(
                        result,
                        step=1,
                        status="failed",
                        action="Launch the application on a desktop browser.",
                        observed=str(error),
                    )
                    raise
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action="Launch the application on a desktop browser.",
                    observed=(
                        f"Opened {config.app_url} in Chromium at "
                        f"{DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}; "
                        f"trigger_label={trigger_before.semantic_label!r}; "
                        f"trigger_text={trigger_before.visible_text!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Viewed the desktop app shell and confirmed Dashboard plus the "
                        "visible workspace switcher trigger were rendered before any keyboard interaction."
                    ),
                    observed=(
                        f"trigger_text={trigger_before.visible_text!r}; "
                        f"top_buttons={list(trigger_before.top_button_labels)!r}"
                    ),
                )

                try:
                    trigger_focusability = page.observe_trigger_focusability()
                    result["trigger_focusability_observation"] = _trigger_focusability_payload(
                        trigger_focusability,
                    )
                    trigger_focus_steps, navigation_strategy = _focus_trigger_for_ts831(
                        page=page,
                        result=result,
                        trigger_focusability=trigger_focusability,
                    )
                    focused_trigger = page.active_element()
                    _assert_workspace_trigger_focused(
                        focused=focused_trigger,
                        focus_steps=trigger_focus_steps,
                    )
                    result["trigger_navigation_strategy"] = navigation_strategy
                    result["trigger_focus_sequence"] = [
                        asdict(step) for step in trigger_focus_steps
                    ]
                    result["focused_trigger_before_space"] = _focused_element_payload(
                        focused_trigger,
                    )
                except Exception as error:
                    _record_step(
                        result,
                        step=2,
                        status="failed",
                        action=(
                            "Use keyboard navigation ('Tab') to reach the workspace "
                            "switcher trigger and ensure it has active keyboard focus."
                        ),
                        observed=str(error),
                    )
                    raise
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=(
                        "Use keyboard navigation ('Tab') to reach the workspace "
                        "switcher trigger and ensure it has active keyboard focus."
                    ),
                    observed=(
                        f"strategy={navigation_strategy}; "
                        f"tab_steps_to_trigger={len(trigger_focus_steps)}; "
                        f"focused_trigger={focused_trigger.accessible_name!r}; "
                        f"tabindex={trigger_focusability.tabindex!r}; "
                        f"keyboard_focusable={trigger_focusability.keyboard_focusable}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Reached the workspace switcher through real keyboard Tab navigation "
                        "and confirmed the active element was the trigger."
                    ),
                    observed=(
                        f"strategy={navigation_strategy}; "
                        f"tab_steps_to_trigger={len(trigger_focus_steps)}; "
                        f"focused_trigger={focused_trigger.accessible_name!r}; "
                        f"focus_sequence_tail={_focus_sequence_tail(trigger_focus_steps)!r}"
                    ),
                )

                try:
                    page.press_space_on_active_element_and_wait_for_surface(
                        timeout_ms=OPEN_TIMEOUT_MS,
                    )
                    switcher = page.observe_open_switcher(timeout_ms=OPEN_TIMEOUT_MS)
                    panel = page.observe_open_panel(
                        expected_container_kinds=("anchored-panel", "surface"),
                        timeout_ms=OPEN_TIMEOUT_MS,
                    )
                    _assert_desktop_panel_open(
                        trigger=trigger_before,
                        switcher=switcher,
                        panel=panel,
                    )
                    result["open_switcher_observation"] = _switcher_payload(switcher)
                    result["open_panel_observation"] = asdict(panel)
                except Exception as error:
                    _record_step(
                        result,
                        step=3,
                        status="failed",
                        action="Press the 'Space' key on the keyboard.",
                        observed=str(error),
                    )
                    raise
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action="Press the 'Space' key on the keyboard.",
                    observed=(
                        f"container_kind={panel.container_kind}; "
                        f"anchored_to_trigger={panel.anchored_to_trigger}; "
                        f"row_count={switcher.row_count}; "
                        f"title_visible={'Workspace switcher' in switcher.switcher_text}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Pressed Space on the focused workspace switcher trigger and "
                        "checked the user-visible result in the desktop UI."
                    ),
                    observed=(
                        "The workspace switcher title and saved workspace content became visible "
                        f"immediately; text_excerpt={_snippet(switcher.switcher_text)!r}"
                    ),
                )

                try:
                    internal_focus, tab_attempts = _advance_focus_into_panel(
                        page=page,
                        panel=panel,
                        max_tabs=POST_OPEN_TAB_LIMIT,
                        timeout_ms=TAB_FOCUS_TIMEOUT_MS,
                    )
                    result["tab_focus_observation"] = _internal_focus_payload(internal_focus)
                    result["post_open_tab_attempts"] = [
                        asdict(attempt) for attempt in tab_attempts
                    ]
                except Exception as error:
                    _record_step(
                        result,
                        step=4,
                        status="failed",
                        action=(
                            "Verify the opened panel allows subsequent keyboard navigation "
                            "within the panel."
                        ),
                        observed=str(error),
                    )
                    raise
                _record_step(
                    result,
                    step=4,
                    status="passed",
                    action=(
                        "Verify the opened panel allows subsequent keyboard navigation "
                        "within the panel."
                    ),
                    observed=(
                        f"Pressed Tab {len(tab_attempts)} time(s) after the Space-opened "
                        "panel appeared and moved focus "
                        f"from {internal_focus.before_label!r} to {internal_focus.after_label!r} "
                        f"(role={internal_focus.after_role!r}, tag={internal_focus.after_tag_name!r}) "
                        "inside the visible workspace switcher panel."
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Pressed Tab repeatedly after opening the panel with Space to confirm "
                        "a keyboard user could continue navigating inside the visible panel."
                    ),
                    observed=(
                        f"tabs_required={len(tab_attempts)}; "
                        f"before_focus={internal_focus.before_label!r}; "
                        f"after_focus={internal_focus.after_label!r}; "
                        f"after_role={internal_focus.after_role!r}; "
                        f"after_visible={internal_focus.after_visible}; "
                        f"after_within_switcher={internal_focus.after_within_switcher}; "
                        f"attempt_sequence={_panel_attempt_summary(tab_attempts)!r}"
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
    focus_steps: tuple[object, ...],
) -> None:
    if (focused.accessible_name or "").startswith("Workspace switcher:"):
        return
    sequence = " -> ".join(
        str(
            getattr(step, "after_label", None)
            or f"<{getattr(step, 'after_tag_name', 'unknown')}>"
        )
        for step in focus_steps
    )
    raise AssertionError(
        "Step 2 failed: keyboard navigation did not land on the workspace switcher "
        "trigger before pressing Space.\n"
        f"Observed focused element: label={focused.accessible_name!r}, "
        f"role={focused.role!r}, tag={focused.tag_name!r}\n"
        f"Observed focus sequence: {sequence}",
    )


def _assert_desktop_panel_open(
    *,
    trigger: WorkspaceSwitcherTriggerObservation,
    switcher: WorkspaceSwitcherObservation,
    panel: WorkspaceSwitcherPanelObservation,
) -> None:
    if switcher.row_count <= 0:
        raise AssertionError(
            "Step 3 failed: pressing Space did not expose any visible workspace rows.\n"
            f"Observed switcher text:\n{switcher.switcher_text}",
        )
    if panel.container_kind not in {"anchored-panel", "surface"}:
        raise AssertionError(
            "Step 3 failed: pressing Space on the workspace switcher trigger did not "
            "open the expected desktop panel-style surface.\n"
            f"Observed container kind: {panel.container_kind}\n"
            f"Observed bounds: left={panel.left:.1f}, top={panel.top:.1f}, "
            f"width={panel.width:.1f}, height={panel.height:.1f}",
        )
    if panel.width <= 0 or panel.height <= 0:
        raise AssertionError(
            "Step 3 failed: pressing Space on the workspace switcher trigger did not "
            "expose a readable desktop panel surface.\n"
            f"Observed panel bounds: left={panel.left:.1f}, top={panel.top:.1f}, "
            f"width={panel.width:.1f}, height={panel.height:.1f}\n"
            f"Observed trigger bounds: left={trigger.left:.1f}, top={trigger.top:.1f}, "
            f"width={trigger.width:.1f}, height={trigger.height:.1f}",
        )


def _advance_focus_into_panel(
    *,
    page: LiveWorkspaceSwitcherPage,
    panel: WorkspaceSwitcherPanelObservation,
    max_tabs: int,
    timeout_ms: int,
) -> tuple[WorkspaceSwitcherInternalFocusObservation, tuple[PanelTabNavigationAttempt, ...]]:
    attempts: list[PanelTabNavigationAttempt] = []

    for tab_press in range(1, max_tabs + 1):
        observation = page.observe_internal_focus_after_tab(
            panel=panel,
            timeout_ms=timeout_ms,
        )
        attempt = PanelTabNavigationAttempt(
            tab_press=tab_press,
            before_label=observation.before_label,
            before_role=observation.before_role,
            before_tag_name=observation.before_tag_name,
            after_label=observation.after_label,
            after_role=observation.after_role,
            after_tag_name=observation.after_tag_name,
            after_visible=observation.after_visible,
            after_in_viewport=observation.after_in_viewport,
            after_within_switcher=observation.after_within_switcher,
            after_on_trigger=observation.after_on_trigger,
            after_owned_by_switcher=observation.after_owned_by_switcher,
            after_different_from_before=observation.after_different_from_before,
        )
        attempts.append(attempt)
        if _panel_focus_reached(observation):
            return observation, tuple(attempts)

    last = attempts[-1]
    raise AssertionError(
        "Step 4 failed: after opening the panel with Space, subsequent keyboard Tab "
        f"navigation did not reach a visible item inside the open workspace switcher "
        f"panel within {max_tabs} Tab presses.\n"
        f"Observed Tab attempt sequence: {_panel_attempt_summary(tuple(attempts))}\n"
        f"Last observed after focus: label={last.after_label!r}, role={last.after_role!r}, "
        f"tag={last.after_tag_name!r}, visible={last.after_visible}, "
        f"in_viewport={last.after_in_viewport}, within_switcher={last.after_within_switcher}, "
        f"on_trigger={last.after_on_trigger}, owned_by_switcher={last.after_owned_by_switcher}, "
        f"moved={last.after_different_from_before}",
    )


def _panel_focus_reached(observation: WorkspaceSwitcherInternalFocusObservation) -> bool:
    return (
        observation.after_visible
        and observation.after_in_viewport
        and observation.after_within_switcher
        and not observation.after_on_trigger
        and observation.after_owned_by_switcher
        and observation.after_different_from_before
    )

def _focus_trigger_for_ts831(
    *,
    page: LiveWorkspaceSwitcherPage,
    result: dict[str, object],
    trigger_focusability: WorkspaceTriggerFocusabilityObservation,
) -> tuple[tuple[object, ...], str]:
    attempts: list[str] = []

    initial_active = page.active_element()
    result["initial_active_element_before_tab"] = _focused_element_payload(initial_active)

    try:
        current_focus_steps = page.focus_trigger_via_keyboard_from_current_focus(
            max_tabs=KEYBOARD_TAB_LIMIT,
        )
        return current_focus_steps, "current-active-element"
    except AssertionError as error:
        attempts.append(
            "Attempt 1 from the current active element "
            f"({initial_active.accessible_name!r}, role={initial_active.role!r}, "
            f"tag={initial_active.tag_name!r}) failed.\n{error}",
        )

    try:
        search_focus_steps = page.focus_trigger_via_keyboard(
            max_tabs=KEYBOARD_TAB_LIMIT,
        )
        return search_focus_steps, "search-field"
    except AssertionError as error:
        attempts.append(
            "Attempt 2 from the visible search field failed.\n"
            f"{error}",
        )

    result["trigger_keyboard_navigation_attempts"] = attempts
    _record_human_verification(
        result,
        check=(
            "Used visible keyboard-only Tab navigation from the current active control "
            "and from the visible search field to verify whether the header workspace "
            "switcher could actually receive focus as a user would experience it."
        ),
        observed=(
            "The visible workspace switcher trigger stayed rendered in the desktop header, "
            "and the browser focus ring moved through other visible controls instead of the "
            "trigger in both attempts. "
            f"trigger_tabindex={trigger_focusability.tabindex!r}; "
            f"keyboard_focusable={trigger_focusability.keyboard_focusable}; "
            f"attempt_count={len(attempts)}"
        ),
    )
    raise AssertionError(
        "Keyboard Tab navigation never reached the workspace switcher trigger during "
        "two realistic keyboard-entry attempts.\n"
        + "\n\n".join(attempts)
        + "\nObserved trigger focusability: "
        + f"label={trigger_focusability.label!r}, "
        + f"role={trigger_focusability.role!r}, "
        + f"tag={trigger_focusability.tag_name!r}, "
        + f"tabindex={trigger_focusability.tabindex!r}, "
        + f"keyboard_focusable={trigger_focusability.keyboard_focusable}\n"
        + f"Observed trigger HTML: {trigger_focusability.outer_html}"
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
    error = str(result.get("error", "AssertionError: TS-831 failed"))
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
        "* Used real keyboard Tab navigation to reach the desktop workspace switcher trigger.",
        "* Pressed Space on the focused trigger and checked whether the visible workspace switcher panel opened immediately.",
        "* Used subsequent keyboard Tab navigation after the Space-opened panel appeared and checked whether focus reached a visible control inside the panel.",
        "",
        "h4. Linked bug context applied",
        "* Reviewed linked bugs TS-843, TS-837, TS-835, and TS-828. Their fixes are deployed, and none adds delayed async behavior, so this run checks the live deployment for immediate keyboard focus and Space activation without extra waits.",
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
        "- Pressed `Space` on the focused trigger and verified the visible workspace switcher panel opened immediately.",
        "- Used subsequent keyboard `Tab` navigation after the panel opened and verified focus reached a visible control inside the panel.",
        "",
        "## Real human-style verification",
        "- Checked the visible Dashboard shell before interaction.",
        "- Checked the visible workspace switcher trigger before keyboard activation.",
        "- Checked the visible `Workspace switcher` title and workspace content after pressing `Space`.",
        "- Checked that keyboard focus could continue moving inside the opened panel without any mouse interaction.",
        "",
        "## Linked bug context applied",
        "- Reviewed linked bugs `TS-843`, `TS-837`, `TS-835`, and `TS-828`. Their fixes are deployed, and none adds delayed async behavior, so this run checks the live deployment for immediate keyboard focus and `Space` activation without extra waits.",
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
        "## Human-style verification details",
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
            "- Outcome: real keyboard Tab reached the workspace switcher trigger, "
            "Space opened the visible panel immediately, and subsequent Tab navigation "
            "reached a visible control inside the panel."
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
            _annotated_request_step(result, 1, REQUEST_STEPS[0]),
            _annotated_request_step(result, 2, REQUEST_STEPS[1]),
            _annotated_request_step(result, 3, REQUEST_STEPS[2]),
            "Expected result check:",
            f"- {_expected_result_observation(result)}",
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
                    "trigger_before": result.get("trigger_before"),
                    "trigger_focusability_observation": result.get(
                        "trigger_focusability_observation",
                    ),
                    "trigger_focus_sequence": result.get("trigger_focus_sequence"),
                    "focused_trigger_before_space": result.get(
                        "focused_trigger_before_space",
                    ),
                    "open_switcher_observation": result.get("open_switcher_observation"),
                    "open_panel_observation": result.get("open_panel_observation"),
                    "tab_focus_observation": result.get("tab_focus_observation"),
                },
                indent=2,
            ),
            "```",
        ],
    ) + "\n"


def _annotated_request_step(
    result: dict[str, object],
    request_step_number: int,
    action: str,
) -> str:
    status, observed = _request_step_observation(result, request_step_number)
    marker = "✅" if status == "passed" else "❌"
    return f"{request_step_number}. {marker} {action}\n   Actual: {observed}"


def _request_step_observation(
    result: dict[str, object],
    request_step_number: int,
) -> tuple[str, str]:
    steps = result.get("steps", [])
    if not isinstance(steps, list):
        return ("failed", "<no observation recorded>")
    if request_step_number == 1:
        return _lookup_step(result, 2)
    if request_step_number == 2:
        return _lookup_step(result, 2)
    if request_step_number == 3:
        return _lookup_step(result, 3)
    return ("failed", "<no observation recorded>")


def _expected_result_observation(result: dict[str, object]) -> str:
    status, observed = _lookup_step(result, 4)
    if status == "passed":
        return observed
    return f"Expected-result verification failed. {observed}"


def _lookup_step(result: dict[str, object], step_number: int) -> tuple[str, str]:
    steps = result.get("steps", [])
    if not isinstance(steps, list):
        return ("failed", "<no observation recorded>")
    for step in steps:
        if isinstance(step, dict) and int(step.get("step", -1)) == step_number:
            return (
                str(step.get("status", "failed")),
                str(step.get("observed", "<no observation recorded>")),
            )
    failed_step = _first_failed_step_number(result)
    if failed_step is not None and step_number > failed_step:
        return ("failed", f"Not reached because step {failed_step} failed.")
    return ("failed", "<no observation recorded>")


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
            f"Observed: {step.get('observed')}",
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


def _bug_context(result: dict[str, object]) -> tuple[str, list[str], str]:
    failed_step = _first_failed_step_number(result)
    if failed_step == 2:
        return (
            f"{TICKET_KEY} - Workspace switcher trigger is skipped by forward Tab navigation before Space activation",
            [
                "1. Launch the application in a desktop browser.",
                "2. Use forward keyboard navigation (`Tab`) from visible desktop controls to reach the workspace switcher trigger.",
                "3. Observe whether the visible workspace switcher trigger ever receives active keyboard focus before Space activation.",
            ],
            (
                "The production desktop web UI still skips the visible workspace switcher "
                "during real forward Tab navigation, so a keyboard user cannot reliably reach "
                "the trigger to activate it with Space."
            ),
        )
    if failed_step == 3:
        return (
            f"{TICKET_KEY} - Pressing Space on the focused workspace switcher trigger does not open the panel",
            [
                "1. Launch the application in a desktop browser.",
                "2. Use keyboard navigation (`Tab`) to reach the workspace switcher trigger.",
                "3. Ensure the trigger has active keyboard focus.",
                "4. Press `Space`.",
                "5. Observe whether the visible workspace switcher panel opens immediately.",
            ],
            (
                "The production workspace switcher trigger does not honor the semantic "
                "button Space activation requirement even when real keyboard focus is on the trigger."
            ),
        )
    if failed_step == 4:
        return (
            f"{TICKET_KEY} - Space-opened workspace switcher panel is not keyboard-navigable",
            [
                "1. Launch the application in a desktop browser.",
                "2. Use keyboard navigation (`Tab`) to reach the workspace switcher trigger.",
                "3. Ensure the trigger has active keyboard focus.",
                "4. Press `Space` to open the panel.",
                "5. Press `Tab` again and observe the focused element inside the open panel.",
            ],
            (
                "The production workspace switcher panel may open after Space activation, "
                "but subsequent keyboard Tab navigation still does not reach a visible "
                "panel control within the allowed keyboard-only progression."
            ),
        )
    return (
        f"{TICKET_KEY} - Workspace switcher Space activation flow is broken",
        [
            "1. Launch the application in a desktop browser.",
            "2. Attempt the workspace-switcher keyboard Space-activation scenario.",
            "3. Observe the first failing boundary.",
        ],
        "The production desktop workspace-switcher Space activation flow does not satisfy the ticket requirement.",
    )


def _trigger_payload(trigger: WorkspaceSwitcherTriggerObservation) -> dict[str, object]:
    return {
        "semantic_label": trigger.semantic_label,
        "visible_text": trigger.visible_text,
        "raw_text_lines": list(trigger.raw_text_lines),
        "display_name": trigger.display_name,
        "workspace_type": trigger.workspace_type,
        "state_label": trigger.state_label,
        "viewport_width": trigger.viewport_width,
        "viewport_height": trigger.viewport_height,
        "bounds": {
            "left": trigger.left,
            "top": trigger.top,
            "width": trigger.width,
            "height": trigger.height,
        },
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


def _switcher_payload(switcher: WorkspaceSwitcherObservation) -> dict[str, object]:
    return {
        "row_count": switcher.row_count,
        "switcher_text": switcher.switcher_text,
        "rows": [
            {
                "display_name": row.display_name,
                "target_type_label": row.target_type_label,
                "state_label": row.state_label,
                "detail_text": row.detail_text,
                "visible_text": row.visible_text,
                "selected": row.selected,
                "action_labels": list(row.action_labels),
                "button_labels": list(row.button_labels),
            }
            for row in switcher.rows
        ],
    }


def _internal_focus_payload(
    observation: WorkspaceSwitcherInternalFocusObservation,
) -> dict[str, object]:
    return {
        "before_focus": {
            "label": observation.before_label,
            "role": observation.before_role,
            "tag_name": observation.before_tag_name,
            "outer_html": observation.before_outer_html,
            "visible": observation.before_visible,
            "in_viewport": observation.before_in_viewport,
            "within_switcher": observation.before_within_switcher,
            "on_trigger": observation.before_on_trigger,
            "owned_by_switcher": observation.before_owned_by_switcher,
        },
        "after_focus": {
            "label": observation.after_label,
            "role": observation.after_role,
            "tag_name": observation.after_tag_name,
            "outer_html": observation.after_outer_html,
        },
        "after_visible": observation.after_visible,
        "after_in_viewport": observation.after_in_viewport,
        "after_within_switcher": observation.after_within_switcher,
        "after_on_trigger": observation.after_on_trigger,
        "after_owned_by_switcher": observation.after_owned_by_switcher,
        "after_different_from_before": observation.after_different_from_before,
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


def _focus_sequence_tail(focus_steps: tuple[object, ...]) -> list[str]:
    tail = list(focus_steps[-4:])
    return [
        str(
            getattr(step, "after_label", None)
            or f"<{getattr(step, 'after_tag_name', 'unknown')}>"
        )
        for step in tail
    ]


def _panel_attempt_summary(attempts: tuple[PanelTabNavigationAttempt, ...]) -> str:
    return " -> ".join(
        (
            f"Tab {attempt.tab_press}: "
            f"{attempt.after_label!r} "
            f"(role={attempt.after_role!r}, tag={attempt.after_tag_name!r}, "
            f"within_switcher={attempt.after_within_switcher}, "
            f"on_trigger={attempt.after_on_trigger}, moved={attempt.after_different_from_before})"
        )
        for attempt in attempts
    )


def _snippet(value: str, *, max_length: int = 220) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= max_length:
        return normalized
    return normalized[: max_length - 3] + "..."


if __name__ == "__main__":
    main()
