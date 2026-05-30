from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import platform
import sys
import tempfile
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
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.components.services.live_workspace_switcher_visual_probe import (  # noqa: E402
    LiveWorkspaceSwitcherVisualProbe,
    WorkspaceSwitcherTriggerVisualObservation,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.interfaces.web_app_session import FocusedElementObservation  # noqa: E402
from testing.tests.support.live_tracker_app_factory import (  # noqa: E402
    create_live_tracker_app_with_stored_token,
)

TICKET_KEY = "TS-846"
TEST_CASE_TITLE = (
    "Condensed workspace switcher trigger activation - surface opens using Space key in mobile layout"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-846/test_ts_846.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 960}
MOBILE_VIEWPORT = {"width": 375, "height": 812}
TRIGGER_FOCUS_TIMEOUT_MS = 6_000
SURFACE_OPEN_TIMEOUT_MS = 6_000
LINKED_BUGS = ["TS-843"]
PRECONDITIONS = [
    "The deployed app is loaded in a compact/mobile viewport.",
    "Keyboard focus can move through the visible app shell until the condensed workspace switcher trigger is focused.",
]
REQUEST_STEPS = [
    "Open the application in a browser and resize the viewport to a mobile width (e.g., 375px).",
    "Navigate with the keyboard until focus is on the condensed (icon-led) workspace switcher trigger.",
    "Press the 'Space' key.",
    "Observe whether the workspace switcher surface opens successfully.",
]
EXPECTED_RESULT = (
    "The workspace switcher surface (for example a bottom sheet or full-screen overlay) "
    "opens successfully."
)
DESKTOP_SECTION_LABELS = {"Dashboard", "Board", "JQL Search", "Settings"}

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts846_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts846_failure.png"


@dataclass(frozen=True)
class TriggerKeyboardReachObservation:
    method: str
    focus_sequence: tuple[FocusNavigationStep, ...]


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    visual_probe = LiveWorkspaceSwitcherVisualProbe()
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-846 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
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
        "mobile_viewport": MOBILE_VIEWPORT,
        "trigger_focus_timeout_ms": TRIGGER_FOCUS_TIMEOUT_MS,
        "surface_open_timeout_ms": SURFACE_OPEN_TIMEOUT_MS,
        "linked_bugs": LINKED_BUGS,
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
                desktop_trigger: WorkspaceSwitcherTriggerObservation | None = None
                desktop_trigger_visual: WorkspaceSwitcherTriggerVisualObservation | None = None
                trigger: WorkspaceSwitcherTriggerObservation | None = None
                trigger_visual: WorkspaceSwitcherTriggerVisualObservation | None = None
                try:
                    runtime = tracker_page.open()
                    result["runtime_state"] = runtime.kind
                    result["runtime_body_text"] = runtime.body_text
                    if runtime.kind != "ready":
                        raise AssertionError(
                            "Step 1 failed: the deployed app did not reach an interactive "
                            "state before the compact Space-key activation scenario began.\n"
                            f"Observed runtime state: {runtime.kind}\n"
                            f"Observed body text:\n{runtime.body_text}",
                        )

                    page.dismiss_connection_banner()
                    page.navigate_to_section("Dashboard")
                    page.set_viewport(**DESKTOP_VIEWPORT)
                    desktop_trigger = page.observe_trigger()
                    desktop_trigger_visual = _observe_trigger_visual(
                        page=page,
                        visual_probe=visual_probe,
                        trigger=desktop_trigger,
                    )
                    result["desktop_trigger_observation"] = {
                        **_trigger_payload(desktop_trigger),
                        "visual_observation": asdict(desktop_trigger_visual),
                    }
                    page.set_viewport(**MOBILE_VIEWPORT)
                    trigger = page.observe_trigger()
                    trigger_visual = _observe_trigger_visual(
                        page=page,
                        visual_probe=visual_probe,
                        trigger=trigger,
                    )
                    result["trigger_observation"] = {
                        **_trigger_payload(trigger),
                        "visual_observation": asdict(trigger_visual),
                    }
                    _assert_mobile_trigger(
                        trigger,
                        desktop_trigger=desktop_trigger,
                        desktop_trigger_visual=desktop_trigger_visual,
                        trigger_visual=trigger_visual,
                    )
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
                        f"{DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']} then "
                        f"{MOBILE_VIEWPORT['width']}x{MOBILE_VIEWPORT['height']}; "
                        f"trigger_label={trigger.semantic_label!r}; "
                        f"trigger_text={trigger.visible_text!r}; "
                        f"trigger_bounds=({trigger.left:.1f}, {trigger.top:.1f}, "
                        f"{trigger.width:.1f}, {trigger.height:.1f}); "
                        f"desktop_height={desktop_trigger.height:.1f}; "
                        f"mobile_visual_icon_visible={trigger_visual.icon_visible}; "
                        f"mobile_text_band_count={trigger_visual.text_band_count}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Viewed the compact/mobile app shell and confirmed the condensed "
                        "icon-led workspace switcher trigger was visibly present before starting "
                        "keyboard navigation."
                    ),
                    observed=(
                        f"trigger_text={trigger.visible_text!r}; "
                        f"raw_text_lines={list(trigger.raw_text_lines)!r}; "
                        f"icon_count={trigger.icon_count}; "
                        f"visual_icon_visible={trigger_visual.icon_visible}; "
                        f"text_band_count={trigger_visual.text_band_count}; "
                        f"desktop_text_band_count={desktop_trigger_visual.text_band_count}; "
                        f"top_buttons={list(trigger.top_button_labels)!r}"
                    ),
                )

                focus_reach: TriggerKeyboardReachObservation | None = None
                focused_trigger: FocusedElementObservation | None = None
                try:
                    focus_reach = _reach_workspace_trigger_via_keyboard(
                        page=page,
                        timeout_ms=TRIGGER_FOCUS_TIMEOUT_MS,
                    )
                    focused_trigger = page.active_element()
                    result["trigger_focus_reach_observation"] = {
                        "method": focus_reach.method,
                    }
                    result["trigger_focus_sequence"] = [
                        asdict(step) for step in focus_reach.focus_sequence
                    ]
                    result["focused_trigger"] = _focused_element_payload(focused_trigger)
                    _assert_workspace_trigger_focused(
                        focused=focused_trigger,
                        focus_steps=focus_reach.focus_sequence,
                    )
                except Exception as error:
                    _record_step(
                        result,
                        step=2,
                        status="failed",
                        action=REQUEST_STEPS[1],
                        observed=str(error),
                    )
                    raise
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=REQUEST_STEPS[1],
                    observed=(
                        f"reach_method={focus_reach.method}; "
                        f"tab_steps_to_trigger={len(focus_reach.focus_sequence)}; "
                        f"focused_trigger={focused_trigger.accessible_name!r}; "
                        f"focused_role={focused_trigger.role!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Reached the condensed workspace switcher trigger through real "
                        "keyboard Tab navigation and confirmed it owned focus before "
                        "pressing Space."
                    ),
                    observed=(
                        f"focus_sequence={_focus_sequence_summary(focus_reach.focus_sequence)}; "
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
                        expected_container_kinds=("bottom-sheet", "full-screen-sheet"),
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
                        "Pressed Space from the focused condensed workspace switcher "
                        "trigger and the surface became visible within the expected wait window."
                    ),
                )

                try:
                    _assert_mobile_surface_opened(
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
                        f"panel_kind={panel.container_kind!r}; "
                        f"bottom_aligned={panel.bottom_aligned}; "
                        f"full_screen_like={panel.full_screen_like}; "
                        f"background_dimmed={panel.background_dimmed}; "
                        f"row_count={switcher.row_count}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Pressed Space like a keyboard user in the compact layout and "
                        "visually confirmed the mobile switcher surface opened on screen "
                        "with its title and visible workspace content."
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


def _assert_mobile_trigger(
    trigger: WorkspaceSwitcherTriggerObservation,
    *,
    desktop_trigger: WorkspaceSwitcherTriggerObservation,
    desktop_trigger_visual: WorkspaceSwitcherTriggerVisualObservation,
    trigger_visual: WorkspaceSwitcherTriggerVisualObservation,
) -> None:
    if not trigger.semantic_label.startswith("Workspace switcher:"):
        raise AssertionError(
            "Step 1 failed: the compact layout did not expose a visible workspace "
            "switcher trigger.\n"
            f"Observed trigger label: {trigger.semantic_label!r}\n"
            f"Observed body text excerpt: {_snippet(trigger.visible_text)!r}",
        )
    if trigger.height < 44:
        raise AssertionError(
            "Step 1 failed: the compact workspace switcher did not expose a touch-"
            "friendly mobile trigger height.\n"
            f"Observed height: {trigger.height}",
        )
    if trigger.width < trigger.viewport_width * 0.55:
        raise AssertionError(
            "Step 1 failed: the compact workspace switcher did not render in a visible "
            "condensed/mobile-width presentation.\n"
            f"Observed width: {trigger.width}\n"
            f"Viewport width: {trigger.viewport_width}",
        )
    if trigger.top < 40:
        raise AssertionError(
            "Step 1 failed: the trigger did not appear in the stacked mobile header area.\n"
            f"Observed top offset: {trigger.top}",
        )
    if trigger.height <= desktop_trigger.height:
        raise AssertionError(
            "Step 1 failed: the compact workspace switcher did not visibly change from "
            "the desktop trigger height.\n"
            f"Desktop height: {desktop_trigger.height}\n"
            f"Compact height: {trigger.height}",
        )
    if trigger.icon_count <= 0 and not trigger_visual.icon_visible:
        raise AssertionError(
            "Step 1 failed: the compact workspace switcher did not keep a visible "
            "leading icon for the required icon-led mobile presentation.\n"
            f"Observed semantic icon_count: {trigger.icon_count}\n"
            f"Observed visual icon: {trigger_visual.icon_visible}",
        )
    if trigger_visual.text_band_count < 2:
        raise AssertionError(
            "Step 1 failed: the compact workspace switcher did not render the expected "
            "stacked mobile text treatment.\n"
            f"Observed text bands: {trigger_visual.text_band_count}\n"
            f"Observed band boxes: {list(trigger_visual.text_band_boxes)!r}",
        )
    if trigger_visual.text_band_count <= desktop_trigger_visual.text_band_count:
        raise AssertionError(
            "Step 1 failed: the compact workspace switcher did not visibly condense "
            "the text structure relative to desktop.\n"
            f"Desktop text bands: {desktop_trigger_visual.text_band_count}\n"
            f"Compact text bands: {trigger_visual.text_band_count}",
        )
    if any(label in DESKTOP_SECTION_LABELS for label in trigger.top_button_labels):
        raise AssertionError(
            "Step 1 failed: the viewport still exposed the desktop top-row navigation "
            "layout instead of the compact/mobile header.\n"
            f"Observed top buttons: {list(trigger.top_button_labels)!r}",
        )


def _reach_workspace_trigger_via_keyboard(
    *,
    page: LiveWorkspaceSwitcherPage,
    timeout_ms: int,
) -> TriggerKeyboardReachObservation:
    focus_observation = page.observe_mobile_trigger_focus(
        tab_count=32,
        timeout_ms=timeout_ms,
    )
    return TriggerKeyboardReachObservation(
        method="forward-tab-from-current-focus",
        focus_sequence=focus_observation.focus_sequence,
    )


def _assert_workspace_trigger_focused(
    *,
    focused: FocusedElementObservation,
    focus_steps: tuple[FocusNavigationStep, ...],
) -> None:
    if _is_workspace_trigger_focus(focused.accessible_name, fallback_text=focused.text):
        return
    raise AssertionError(
        "Step 2 failed: keyboard navigation did not land on the condensed workspace "
        "switcher trigger before the Space-key activation scenario.\n"
        f"Observed focused element: label={focused.accessible_name!r}, "
        f"role={focused.role!r}, tag={focused.tag_name!r}, text={focused.text!r}\n"
        f"Observed focus sequence: {_focus_sequence_summary(focus_steps)}",
    )


def _assert_mobile_surface_opened(
    *,
    switcher: WorkspaceSwitcherObservation,
    panel: WorkspaceSwitcherPanelObservation,
    surface: WorkspaceSwitcherSurfaceObservation,
) -> None:
    failures: list[str] = []
    if "Workspace switcher" not in switcher.switcher_text:
        failures.append(
            "the visible switcher text did not include the 'Workspace switcher' title",
        )
    if panel.container_kind not in {"bottom-sheet", "full-screen-sheet"}:
        failures.append(f"the opened container kind was {panel.container_kind!r}")
    if not (panel.bottom_aligned or panel.full_screen_like):
        failures.append(
            "the opened container did not behave like a bottom sheet or full-screen overlay",
        )
    if not panel.background_dimmed:
        failures.append("the opened mobile surface did not dim the background")
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
            "Step 4 failed: pressing Space on the focused condensed workspace switcher "
            "trigger did not open the expected mobile workspace switcher surface.\n"
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
    error = str(result.get("error", "AssertionError: TS-846 failed"))
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
        "h4. Linked bug context",
        "* TS-843 is marked *Done*; this test verifies the deployed Space-key fix also works for the condensed/mobile trigger variation.",
        "",
        "h4. Rework changes",
        "* Added compact-trigger proof that compares desktop and mobile presentations before the Space-key action.",
        "* Added visual icon detection and condensed text-band checks so TS-846 only passes on the icon-led mobile trigger variant.",
        "",
        "h4. What was tested",
        "* Opened the deployed TrackState app in Chromium with a stored hosted token.",
        "* Compared the desktop and mobile trigger presentations, then confirmed the compact trigger stayed icon-led and visually condensed.",
        "* Reached the condensed trigger through real keyboard Tab navigation.",
        "* Pressed the Space key on the focused trigger.",
        "* Verified that the visible mobile switcher surface opened with its title and workspace content.",
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
            f"browser {{Chromium (Playwright)}}, OS {{{{{result['os']}}}}}, "
            f"viewport {{{MOBILE_VIEWPORT['width']}x{MOBILE_VIEWPORT['height']}}}."
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
        "## Linked bug context",
        "- TS-843 is already marked **Done**; this automation verifies the same Space-key fix on the condensed/mobile trigger path.",
        "",
        "## Rework changes",
        "- Added desktop-vs-mobile trigger comparison before the keyboard flow.",
        "- Added visual icon detection and condensed text-band assertions so the test only passes on the icon-led mobile trigger variation.",
        "",
        "## What was automated",
        "- Opened the deployed TrackState app in Chromium with a stored hosted token.",
        "- Compared the desktop and compact trigger presentations and verified the compact trigger remained icon-led and visually condensed.",
        "- Reached the trigger through a real keyboard Tab path.",
        "- Pressed `Space` on the focused trigger.",
        "- Verified the visible mobile switcher surface opened with the expected title and workspace content.",
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
            f"`Chromium (Playwright)`, OS `{result['os']}`, viewport "
            f"`{MOBILE_VIEWPORT['width']}x{MOBILE_VIEWPORT['height']}`."
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
            "- Strengthened TS-846 so it proves the condensed/icon-led mobile trigger "
            "before exercising Space-key activation."
        ),
        f"- Test case: **{TICKET_KEY} - {TEST_CASE_TITLE}**",
        f"- Result: **{status}**",
        f"- Command: `{RUN_COMMAND}`",
        (
            f"- Environment: `{result['app_url']}` on Chromium/Playwright "
            f"({result['os']}) against `{result['repository']}` @ "
            f"`{result['repository_ref']}` with viewport "
            f"`{MOBILE_VIEWPORT['width']}x{MOBILE_VIEWPORT['height']}`."
        ),
        (
            "- Outcome: pressing Space on the focused condensed/mobile workspace "
            "switcher trigger opened the visible mobile workspace switcher surface."
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
            f"- Viewport: {MOBILE_VIEWPORT['width']}x{MOBILE_VIEWPORT['height']}",
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
                    "desktop_trigger_observation": result.get("desktop_trigger_observation"),
                    "trigger_observation": result.get("trigger_observation"),
                    "trigger_focus_reach_observation": result.get(
                        "trigger_focus_reach_observation",
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
    if failed_step == 1:
        return (
            f"{TICKET_KEY} - Condensed mobile workspace switcher trigger is not exposed correctly",
            [
                "1. Open the deployed TrackState app in a browser.",
                "2. Resize the viewport to a compact/mobile width such as 375px.",
                "3. Navigate to Dashboard.",
                "4. Observe the workspace switcher trigger in the compact header.",
            ],
            (
                "The production compact/mobile layout does not expose the expected "
                "condensed/icon-led workspace switcher trigger presentation needed for "
                "the Space-key scenario."
            ),
        )
    if failed_step == 2:
        return (
            f"{TICKET_KEY} - Condensed mobile workspace switcher trigger is not reachable by keyboard",
            [
                "1. Open the deployed TrackState app in a browser and resize to a mobile width.",
                "2. Navigate to Dashboard in the compact/mobile layout.",
                "3. Use real keyboard Tab navigation through the visible controls.",
                "4. Observe whether focus lands on the condensed workspace switcher trigger.",
            ],
            (
                "The production compact/mobile UI does not expose the condensed workspace "
                "switcher trigger as a reachable keyboard focus target, so the Space-key "
                "activation scenario cannot begin from a real focused trigger state."
            ),
        )
    if failed_step in {3, 4}:
        return (
            f"{TICKET_KEY} - Pressing Space on the focused condensed workspace switcher trigger does not open the mobile surface",
            [
                "1. Open the deployed TrackState app in a browser and resize to a mobile width.",
                "2. Reach the condensed workspace switcher trigger by keyboard.",
                "3. Press the `Space` key.",
                "4. Observe whether the workspace switcher mobile surface opens.",
            ],
            (
                "After the condensed workspace switcher trigger receives real keyboard "
                "focus in the mobile layout, the production UI does not open the expected "
                "bottom-sheet/full-screen workspace switcher surface in response to Space."
            ),
        )
    return (
        f"{TICKET_KEY} - Condensed workspace switcher Space-key activation is broken",
        [
            "1. Open the deployed TrackState app in a browser.",
            "2. Resize to a mobile width and attempt the TS-846 scenario.",
            "3. Observe the first failing boundary.",
        ],
        (
            "The production compact/mobile workspace switcher does not satisfy the TS-846 "
            "keyboard Space activation requirement."
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


def _observe_trigger_visual(
    *,
    page: LiveWorkspaceSwitcherPage,
    visual_probe: LiveWorkspaceSwitcherVisualProbe,
    trigger: WorkspaceSwitcherTriggerObservation,
) -> WorkspaceSwitcherTriggerVisualObservation:
    with tempfile.NamedTemporaryFile(
        dir=OUTPUTS_DIR,
        prefix="ts846_trigger_",
        suffix=".png",
        delete=False,
    ) as handle:
        screenshot_path = Path(handle.name)
    try:
        page.screenshot(str(screenshot_path))
        return visual_probe.observe_trigger(
            screenshot_path=screenshot_path,
            trigger=trigger,
        )
    finally:
        screenshot_path.unlink(missing_ok=True)


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


def _is_workspace_trigger_focus(
    label: str | None,
    *,
    fallback_text: str | None = None,
) -> bool:
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
