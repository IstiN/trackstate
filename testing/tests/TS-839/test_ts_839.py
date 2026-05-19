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
    FocusNavigationStep,
    LiveWorkspaceSwitcherPage,
    WorkspaceSwitcherObservation,
    WorkspaceSwitcherPanelObservation,
    WorkspaceSwitcherSurfaceObservation,
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

TICKET_KEY = "TS-839"
TEST_CASE_TITLE = "Workspace switcher trigger keyboard activation — surface opens using Space key"
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-839/test_ts_839.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 960}
TRIGGER_FOCUS_TIMEOUT_MS = 4_000
SURFACE_OPEN_TIMEOUT_MS = 4_000

PRECONDITIONS = [
    "Keyboard focus is currently on the workspace switcher trigger.",
]
REQUEST_STEPS = [
    "Launch the application on a desktop browser.",
    "Use real keyboard navigation to move focus to the workspace switcher trigger.",
    "Press the 'Space' key on the keyboard.",
    "Observe whether the workspace switcher surface opens.",
]
EXPECTED_RESULT = (
    "The workspace switcher surface opens, confirming standard keyboard activation "
    "works when the trigger is focused."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts839_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts839_failure.png"


@dataclass(frozen=True)
class TriggerKeyboardReachObservation:
    method: str
    focus_sequence: tuple[FocusNavigationStep, ...]
    forward_error: str | None = None


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-839 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
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
        "surface_open_timeout_ms": SURFACE_OPEN_TIMEOUT_MS,
        "preconditions": PRECONDITIONS,
        "user_login": user.login,
        "steps": [],
        "human_verification": [],
    }

    page: LiveWorkspaceSwitcherPage | None = None
    try:
        with create_live_tracker_app_with_stored_token(config, token=token) as tracker_page:
            page = LiveWorkspaceSwitcherPage(tracker_page)
            try:
                trigger: WorkspaceSwitcherTriggerObservation | None = None
                try:
                    runtime = tracker_page.open()
                    result["runtime_state"] = runtime.kind
                    result["runtime_body_text"] = runtime.body_text
                    if runtime.kind != "ready":
                        raise AssertionError(
                            "Step 1 failed: the deployed app did not reach an interactive "
                            "desktop state before the Space-key activation scenario began.\n"
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
                        "Viewed the desktop app shell before the keypress and confirmed "
                        "Dashboard plus the visible workspace switcher trigger were rendered."
                    ),
                    observed=(
                        f"trigger_text={trigger.visible_text!r}; "
                        f"display_name={trigger.display_name!r}; "
                        f"top_buttons={list(trigger.top_button_labels)!r}"
                    ),
                )

                trigger_focusability: WorkspaceTriggerFocusabilityObservation | None = None
                focus_reach: TriggerKeyboardReachObservation | None = None
                focus_steps: tuple[FocusNavigationStep, ...] = ()
                focused_trigger: FocusedElementObservation | None = None
                try:
                    trigger_focusability = page.observe_trigger_focusability()
                    result["trigger_focusability_observation"] = _trigger_focusability_payload(
                        trigger_focusability,
                    )
                    focus_reach = _reach_workspace_trigger_via_keyboard(
                        page=page,
                        timeout_ms=TRIGGER_FOCUS_TIMEOUT_MS,
                    )
                    focus_steps = focus_reach.focus_sequence
                    focused_trigger = page.active_element()
                    result["trigger_focus_reach_observation"] = {
                        "method": focus_reach.method,
                        "forward_error": focus_reach.forward_error,
                    }
                    result["trigger_focus_sequence"] = [asdict(step) for step in focus_steps]
                    result["focused_trigger"] = _focused_element_payload(focused_trigger)
                    _assert_workspace_trigger_focused(
                        focused=focused_trigger,
                        focus_steps=focus_steps,
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
                        f"reach_method={focus_reach.method}; "
                        f"tab_steps_to_trigger={len(focus_steps)}; "
                        f"focused_trigger={focused_trigger.accessible_name!r}; "
                        f"keyboard_focusable={trigger_focusability.keyboard_focusable}; "
                        f"tabindex={trigger_focusability.tabindex!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Reached the workspace switcher trigger using a real keyboard "
                        "navigation path and confirmed the trigger, not a scripted "
                        "fallback, owned keyboard focus before pressing Space."
                    ),
                    observed=(
                        f"reach_method={focus_reach.method}; "
                        f"focus_sequence={_focus_sequence_summary(focus_steps)}; "
                        f"focused_trigger={focused_trigger.accessible_name!r}; "
                        f"focused_role={focused_trigger.role!r}"
                    ),
                )

                switcher: WorkspaceSwitcherObservation | None = None
                panel: WorkspaceSwitcherPanelObservation | None = None
                surface: WorkspaceSwitcherSurfaceObservation | None = None
                try:
                    page.press_space_on_active_element_and_wait_for_surface(
                        timeout_ms=SURFACE_OPEN_TIMEOUT_MS,
                    )
                    switcher = page.observe_open_switcher(
                        timeout_ms=SURFACE_OPEN_TIMEOUT_MS,
                    )
                    panel = page.observe_open_panel(
                        expected_container_kinds=("anchored-panel", "surface"),
                        timeout_ms=SURFACE_OPEN_TIMEOUT_MS,
                    )
                    surface = page.observe_surface(timeout_ms=SURFACE_OPEN_TIMEOUT_MS)
                    result["open_switcher_observation"] = _switcher_payload(switcher)
                    result["open_panel_observation"] = asdict(panel)
                    result["surface_observation"] = asdict(surface)
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
                        "Pressed Space from the focused workspace switcher trigger and "
                        "the surface became visible within the expected wait window."
                    ),
                )

                try:
                    _assert_surface_opened(
                        switcher=switcher,
                        panel=panel,
                        surface=surface,
                    )
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
                        f"heading={surface.heading_text!r}; "
                        f"dialog_visible={surface.dialog_visible}; "
                        f"panel_kind={panel.container_kind!r}; "
                        f"row_count={switcher.row_count}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Pressed Space like a keyboard user and visually confirmed the "
                        "workspace switcher surface opened on screen with its expected "
                        "title and visible content."
                    ),
                    observed=(
                        f"heading={surface.heading_text!r}; "
                        f"switcher_text_excerpt={_snippet(switcher.switcher_text)!r}; "
                        f"interactive_labels={_interactive_label_summary(surface)!r}"
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
        "trigger before the Space-key activation scenario.\n"
        f"Observed focused element: label={focused.accessible_name!r}, "
        f"role={focused.role!r}, tag={focused.tag_name!r}, text={focused.text!r}\n"
        f"Observed focus sequence: {_focus_sequence_summary(focus_steps)}",
    )


def _reach_workspace_trigger_via_keyboard(
    *,
    page: LiveWorkspaceSwitcherPage,
    timeout_ms: int,
) -> TriggerKeyboardReachObservation:
    try:
        return TriggerKeyboardReachObservation(
            method="forward-tab",
            focus_sequence=page.focus_trigger_via_keyboard(
                max_tabs=24,
                timeout_ms=timeout_ms,
            ),
        )
    except AssertionError as forward_error:
        candidate_summaries: list[str] = []
        for seed_tabs in range(1, 25):
            page.focus_search_field(timeout_ms=timeout_ms)
            steps: list[FocusNavigationStep] = []
            for step_index in range(1, seed_tabs + 1):
                before = page.active_element()
                page.press_key("Tab", timeout_ms=timeout_ms)
                after = page.active_element()
                steps.append(
                    FocusNavigationStep(
                        step=step_index,
                        before_label=before.accessible_name,
                        before_role=before.role,
                        after_label=after.accessible_name,
                        after_role=after.role,
                        after_tag_name=after.tag_name,
                        after_outer_html=after.outer_html,
                    ),
                )
                if _is_workspace_trigger_focus(
                    after.accessible_name,
                    fallback_text=after.text,
                ):
                    return TriggerKeyboardReachObservation(
                        method=f"{seed_tabs}x-tab",
                        focus_sequence=tuple(steps),
                        forward_error=str(forward_error),
                    )
            for reverse_index in range(1, 19):
                before = page.active_element()
                page.press_key("Shift+Tab", timeout_ms=timeout_ms)
                after = page.active_element()
                steps.append(
                    FocusNavigationStep(
                        step=seed_tabs + reverse_index,
                        before_label=before.accessible_name,
                        before_role=before.role,
                        after_label=after.accessible_name,
                        after_role=after.role,
                        after_tag_name=after.tag_name,
                        after_outer_html=after.outer_html,
                    ),
                )
                if _is_workspace_trigger_focus(
                    after.accessible_name,
                    fallback_text=after.text,
                ):
                    return TriggerKeyboardReachObservation(
                        method=f"{seed_tabs}x-tab-then-{reverse_index}x-shift-tab",
                        focus_sequence=tuple(steps),
                        forward_error=str(forward_error),
                    )
            candidate_summaries.append(
                f"{seed_tabs} tab(s): {_focus_sequence_summary(tuple(steps[-8:]))}",
            )
        raise AssertionError(
            "Keyboard navigation never reached the workspace switcher trigger.\n"
            f"Forward navigation failure: {forward_error}\n"
            "Observed fallback focus attempts:\n"
            + "\n".join(candidate_summaries),
        ) from forward_error


def _assert_surface_opened(
    *,
    switcher: WorkspaceSwitcherObservation,
    panel: WorkspaceSwitcherPanelObservation,
    surface: WorkspaceSwitcherSurfaceObservation,
) -> None:
    failures: list[str] = []
    if "Workspace switcher" not in switcher.switcher_text:
        failures.append("the visible switcher text did not include the 'Workspace switcher' title")
    if panel.container_kind not in {"anchored-panel", "surface"}:
        failures.append(f"the opened container kind was {panel.container_kind!r}")
    if panel.width <= 0 or panel.height <= 0:
        failures.append(
            f"the opened panel bounds were width={panel.width:.1f}, height={panel.height:.1f}",
        )
    if not surface.dialog_visible:
        failures.append("the opened switcher surface was not reported as visible")
    if surface.heading_text.strip() != "Workspace switcher":
        failures.append(
            f"the visible heading was {surface.heading_text!r} instead of 'Workspace switcher'",
        )
    if switcher.row_count <= 0:
        failures.append("the opened surface did not expose any visible workspace rows")
    if failures:
        raise AssertionError(
            "Step 4 failed: pressing Space on the focused workspace switcher trigger "
            "did not open the expected visible workspace switcher surface.\n"
            + "\n".join(f"- {item}" for item in failures)
            + "\n"
            + f"Observed switcher text:\n{switcher.switcher_text}\n"
            + f"Observed panel bounds: left={panel.left:.1f}, top={panel.top:.1f}, "
            + f"width={panel.width:.1f}, height={panel.height:.1f}",
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
            },
        )
        + "\n",
        encoding="utf-8",
    )
    JIRA_COMMENT_PATH.write_text(_jira_comment(result, passed=True), encoding="utf-8")
    PR_BODY_PATH.write_text(_markdown_summary(result, passed=True), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_summary(result, passed=True), encoding="utf-8")


def _write_failure_outputs(result: dict[str, object]) -> None:
    error = str(result.get("error", "AssertionError: TS-839 failed"))
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
        "h4. Preconditions checked",
        *[f"* {item}" for item in PRECONDITIONS],
        "",
        "h4. What was tested",
        "* Opened the deployed TrackState app in Chromium with a stored hosted token.",
        "* Reached the desktop workspace switcher trigger through a real keyboard navigation path.",
        "* Pressed the Space key on the focused workspace switcher trigger.",
        "* Verified that the visible workspace switcher surface opened with its title and panel content.",
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
        "## Preconditions checked",
        *[f"- {item}" for item in PRECONDITIONS],
        "",
        "## What was automated",
        "- Opened the deployed TrackState app in Chromium with a stored hosted token.",
        "- Reached the desktop workspace switcher trigger through a real keyboard navigation path.",
        "- Pressed `Space` on the focused trigger.",
        "- Verified that the visible workspace switcher surface opened with the expected title and panel content.",
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
        (
            "- Added TS-839 live desktop coverage for keyboard Space activation of the "
            "workspace switcher trigger."
        ),
        f"- Test case: **{TICKET_KEY} - {TEST_CASE_TITLE}**",
        f"- Result: **{status}**",
        f"- Command: `{RUN_COMMAND}`",
        (
            f"- Environment: `{result['app_url']}` on Chromium/Playwright "
            f"({result['os']}) against `{result['repository']}` @ "
            f"`{result['repository_ref']}`."
        ),
        (
            "- Outcome: pressing Space on the focused workspace switcher trigger opened "
            "the visible workspace switcher surface."
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
            _annotated_step_line(result, 1, REQUEST_STEPS[0]),
            _annotated_step_line(result, 2, REQUEST_STEPS[1]),
            _annotated_step_line(result, 3, REQUEST_STEPS[2]),
            _annotated_step_line(result, 4, REQUEST_STEPS[3]),
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
                    "focused_trigger": result.get("focused_trigger"),
                    "open_switcher_observation": result.get("open_switcher_observation"),
                    "open_panel_observation": result.get("open_panel_observation"),
                    "surface_observation": result.get("surface_observation"),
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
            f"{TICKET_KEY} - Workspace switcher trigger is not reachable by desktop keyboard focus",
            [
                "1. Launch the application on a desktop browser.",
                "2. Navigate to Dashboard in the desktop web app.",
                "3. Use real keyboard Tab navigation through the visible shell controls.",
                "4. Observe whether focus lands on the workspace switcher trigger.",
            ],
            (
                "The production desktop UI does not expose the workspace switcher trigger "
                "as a reachable keyboard focus target, so the Space-key activation scenario "
                "cannot begin from a real focused trigger state."
            ),
        )
    if failed_step in {3, 4}:
        return (
            f"{TICKET_KEY} - Pressing Space on the focused workspace switcher trigger does not open the surface",
            [
                "1. Launch the application on a desktop browser.",
                "2. Reach the workspace switcher trigger by keyboard.",
                "3. Press the `Space` key.",
                "4. Observe whether the workspace switcher surface opens.",
            ],
            (
                "After the workspace switcher trigger receives real keyboard focus, the "
                "production desktop UI does not open the expected workspace switcher surface "
                "in response to the Space key."
            ),
        )
    return (
        f"{TICKET_KEY} - Workspace switcher Space-key activation is broken",
        [
            "1. Launch the application on a desktop browser.",
            "2. Attempt the TS-839 Space-key activation scenario.",
            "3. Observe the first failing boundary.",
        ],
        (
            "The production desktop workspace switcher does not satisfy the TS-839 "
            "keyboard activation requirement."
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
    for step in steps:
        if isinstance(step, dict) and int(step.get("step", -1)) == step_number:
            return str(step.get("observed", "<no observation recorded>"))
    first_failed = _first_failed_step_number(result)
    if first_failed is not None and step_number > first_failed:
        return f"Not reached because Step {first_failed} failed."
    return "<no observation recorded>"


def _trigger_payload(observation: WorkspaceSwitcherTriggerObservation) -> dict[str, object]:
    return {
        "viewport_width": observation.viewport_width,
        "viewport_height": observation.viewport_height,
        "semantic_label": observation.semantic_label,
        "visible_text": observation.visible_text,
        "raw_text_lines": list(observation.raw_text_lines),
        "display_name": observation.display_name,
        "workspace_type": observation.workspace_type,
        "state_label": observation.state_label,
        "icon_count": observation.icon_count,
        "left": observation.left,
        "top": observation.top,
        "width": observation.width,
        "height": observation.height,
        "top_button_labels": list(observation.top_button_labels),
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


def _focused_element_payload(observation: FocusedElementObservation) -> dict[str, object]:
    return {
        "tag_name": observation.tag_name,
        "role": observation.role,
        "accessible_name": observation.accessible_name,
        "text": observation.text,
        "tabindex": observation.tabindex,
        "outer_html": observation.outer_html,
    }


def _switcher_payload(observation: WorkspaceSwitcherObservation) -> dict[str, object]:
    return {
        "body_text": observation.body_text,
        "switcher_text": observation.switcher_text,
        "row_count": observation.row_count,
        "rows": [asdict(row) for row in observation.rows],
    }


def _focus_sequence_summary(sequence: tuple[FocusNavigationStep, ...]) -> str:
    if not sequence:
        return "<no focus steps recorded>"
    return " -> ".join(
        _describe_focus_target(step.after_label, step.after_tag_name) for step in sequence
    )


def _describe_focus_target(label: str | None, tag_name: str | None) -> str:
    normalized = " ".join((label or "").split())
    if not normalized:
        return f"<{tag_name or 'unknown'}>"
    if len(normalized) > 96:
        return normalized[:93] + "..."
    return normalized


def _is_workspace_trigger_focus(label: str | None, *, fallback_text: str | None = None) -> bool:
    for candidate in (label, fallback_text):
        normalized = " ".join((candidate or "").split()).lower()
        if normalized.startswith("workspace switcher:"):
            return True
    return False


def _interactive_label_summary(surface: WorkspaceSwitcherSurfaceObservation) -> list[str]:
    labels: list[str] = []
    for item in surface.interactive_elements:
        label = " ".join(item.label.split())
        if label and label not in labels:
            labels.append(label)
        if len(labels) >= 5:
            break
    return labels


def _snippet(text: str, *, max_length: int = 160) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= max_length:
        return normalized
    return normalized[: max_length - 3] + "..."


if __name__ == "__main__":
    main()
