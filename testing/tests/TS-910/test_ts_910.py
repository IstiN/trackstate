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
    LiveWorkspaceSwitcherPage,
    WorkspaceSwitcherButtonStateObservation,
    WorkspaceSwitcherFocusOwnershipObservation,
    WorkspaceSwitcherTabStopObservation,
    WorkspaceSwitcherObservation,
    WorkspaceSwitcherPanelObservation,
    WorkspaceSwitcherRowFocusObservation,
    WorkspaceSwitcherSavedWorkspaceRowObservation,
    WorkspaceSwitcherSurfaceObservation,
    WorkspaceSwitcherTransitionMonitorObservation,
    WorkspaceSwitcherTriggerObservation,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.interfaces.web_app_session import FocusedElementObservation  # noqa: E402
from testing.tests.support.live_tracker_app_factory import (  # noqa: E402
    create_live_tracker_app,
)
from testing.tests.support.stored_workspace_profiles_runtime import (  # noqa: E402
    StoredWorkspaceProfilesRuntime,
)

TICKET_KEY = "TS-910"
TEST_CASE_TITLE = (
    "Press Tab repeatedly in open workspace switcher — focus loops within panel "
    "elements"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-910/test_ts_910.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
DEFAULT_BRANCH = "main"
FIRST_WORKSPACE_DISPLAY_NAME = "Hosted main workspace"
SECOND_WORKSPACE_DISPLAY_NAME = "Hosted alt workspace"
THIRD_WORKSPACE_DISPLAY_NAME = "Hosted third workspace"
SECOND_WORKSPACE_WRITE_BRANCH = "ts-910-alt"
THIRD_WORKSPACE_WRITE_BRANCH = "ts-910-third"
LINKED_BUGS = ["TS-916", "TS-900"]
FOCUS_SETTLE_MS = 300
MAX_TABS_TO_REACH_FOOTER = 16
LAST_INTERNAL_CONTROL_LABEL = "Save and switch"
FIELD_LABELS = ("Repository", "Branch")
PANEL_OBSERVE_TIMEOUT_MS = 4_000

REQUEST_STEPS = [
    "Press the 'Tab' key to navigate through all interactive elements within the panel (e.g., workspace list items, footer buttons).",
    "Continue pressing 'Tab' after reaching the final interactive element in the panel.",
]
AUTOMATION_STEPS = [
    "Open the deployed desktop workspace switcher and confirm the visible panel exposes the saved workspace rows and footer controls.",
    "Move keyboard focus to the selected first saved workspace row inside the open switcher panel.",
    "Press Tab repeatedly until the visible Save and switch footer button is reached, confirming focus remains trapped inside the switcher panel during traversal.",
    "Press Tab once more from the Save and switch footer button and verify focus wraps back to the first saved workspace row instead of staying on the footer button or escaping outside the panel.",
]
EXPECTED_RESULT = (
    "Keyboard focus remains inside the workspace switcher panel. After the last "
    "interactive panel control, pressing Tab wraps focus back to the first saved "
    "workspace row instead of escaping to external controls such as Search issues."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
REVIEW_REPLIES_PATH = OUTPUTS_DIR / "review_replies.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts910_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts910_failure.png"
DISCUSSIONS_RAW_PATH = REPO_ROOT / "input" / TICKET_KEY / "pr_discussions_raw.json"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-910 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
        )
    user = service.fetch_authenticated_user()
    workspace_repository = service.repository
    workspace_state = _workspace_state(workspace_repository)

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
        "linked_bugs": LINKED_BUGS,
        "focus_settle_ms": FOCUS_SETTLE_MS,
        "max_tabs_to_reach_footer": MAX_TABS_TO_REACH_FOOTER,
        "last_internal_control_label": LAST_INTERNAL_CONTROL_LABEL,
        "preloaded_workspace_state": workspace_state,
        "user_login": user.login,
        "steps": [],
        "human_verification": [],
    }

    page: LiveWorkspaceSwitcherPage | None = None
    try:
        with create_live_tracker_app(
            config,
            runtime_factory=lambda: StoredWorkspaceProfilesRuntime(
                repository=workspace_repository,
                token=token,
                workspace_state=workspace_state,
            ),
        ) as tracker_page:
            page = LiveWorkspaceSwitcherPage(tracker_page)
            try:
                page.set_viewport(**DESKTOP_VIEWPORT)
                try:
                    runtime = tracker_page.open()
                except AssertionError as error:
                    body_text = tracker_page.body_text()
                    result["runtime_state"] = "startup-failed"
                    result["runtime_body_text"] = body_text
                    _record_step(
                        result,
                        step=1,
                        status="failed",
                        action=AUTOMATION_STEPS[0],
                        observed=str(error),
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Opened the deployed desktop app and visually checked whether "
                            "the dashboard and workspace switcher were available before "
                            "starting the keyboard scenario."
                        ),
                        observed=(
                            f"viewport={DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}; "
                            f"body_text={body_text!r}"
                        ),
                    )
                    raise
                result["runtime_state"] = runtime.kind
                result["runtime_body_text"] = runtime.body_text
                if runtime.kind != "ready":
                    startup_error = (
                        "Step 1 failed: the deployed app did not reach an interactive "
                        "desktop state before the workspace-switcher focus-loop scenario began.\n"
                        f"Observed runtime state: {runtime.kind}\n"
                        f"Observed body text:\n{runtime.body_text}"
                    )
                    _record_step(
                        result,
                        step=1,
                        status="failed",
                        action=AUTOMATION_STEPS[0],
                        observed=startup_error,
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Opened the deployed desktop app and visually checked whether "
                            "the dashboard and workspace switcher were available before "
                            "starting the keyboard scenario."
                        ),
                        observed=(
                            f"viewport={DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}; "
                            f"runtime_state={runtime.kind!r}; "
                            f"body_text={runtime.body_text!r}"
                        ),
                    )
                    raise AssertionError(startup_error)

                page.dismiss_connection_banner()
                page.navigate_to_section("Dashboard")
                page.set_viewport(**DESKTOP_VIEWPORT)

                trigger: WorkspaceSwitcherTriggerObservation | None = None
                switcher: WorkspaceSwitcherObservation | None = None
                panel: WorkspaceSwitcherPanelObservation | None = None
                rows: tuple[WorkspaceSwitcherSavedWorkspaceRowObservation, ...] = ()
                surface: WorkspaceSwitcherSurfaceObservation | None = None
                internal_tab_stops: tuple[WorkspaceSwitcherTabStopObservation, ...] = ()
                try:
                    trigger = page.observe_trigger()
                    switcher = page.open_and_observe()
                    panel = page.observe_open_panel(
                        expected_container_kinds=("anchored-panel", "surface"),
                        timeout_ms=4_000,
                    )
                    result["trigger_observation"] = _trigger_payload(trigger)
                    result["open_switcher_observation"] = _switcher_payload(switcher)
                    result["open_panel_observation"] = asdict(panel)
                    rows = page.observe_saved_workspace_rows(timeout_ms=4_000)
                    surface = page.observe_surface(timeout_ms=4_000)
                    internal_tab_stops = page.observe_internal_tab_stops(
                        panel=panel,
                        timeout_ms=4_000,
                    )
                    result["saved_workspace_rows_before_focus"] = _saved_workspace_rows_payload(
                        rows,
                    )
                    result["surface_observation"] = _surface_payload(surface)
                    result["internal_tab_stops_before_focus"] = _tab_stops_payload(
                        internal_tab_stops,
                    )
                    first_row = _assert_initial_panel_state(
                        switcher=switcher,
                        panel=panel,
                        rows=rows,
                        surface=surface,
                    )
                    result["first_row_display_name"] = first_row.display_name
                    result["first_row_detail_text"] = first_row.detail_text
                except Exception as error:
                    _record_step(
                        result,
                        step=1,
                        status="failed",
                        action=AUTOMATION_STEPS[0],
                        observed=str(error),
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Opened the desktop workspace switcher and visually checked the "
                            "visible panel state before starting keyboard traversal."
                        ),
                        observed=(
                            f"trigger_label={trigger.semantic_label!r}; "
                            f"switcher_text={switcher.switcher_text!r}; "
                            f"panel_kind={panel.container_kind if panel is not None else None!r}; "
                            f"saved_workspace_row_count={len(rows)}; "
                            f"surface_labels={_surface_label_summary(surface)!r}"
                            if trigger is not None and switcher is not None and panel is not None and surface is not None
                            else f"body_text={page.current_body_text()!r}"
                        ),
                    )
                    raise
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=AUTOMATION_STEPS[0],
                    observed=(
                        f"Opened {config.app_url} in Chromium at "
                        f"{DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}; "
                        f"saved_workspace_row_count={len(rows)}; "
                        f"surface_labels={_surface_label_summary(surface)!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Opened the desktop workspace switcher and visually confirmed the "
                        "Workspace switcher title, the saved workspace rows, the Repository "
                        "and Branch fields, and the Save and switch footer button were visible."
                    ),
                        observed=(
                            f"row_names={[row.display_name for row in rows]!r}; "
                            f"surface_labels={_surface_label_summary(surface)!r}; "
                            f"internal_tab_stops={_tab_stop_label_summary(internal_tab_stops)!r}"
                        ),
                    )

                page.focus_saved_workspace_row(
                    first_row.display_name,
                    panel=panel,
                    timeout_ms=4_000,
                )
                panel, surface_stability_error = _observe_panel_after_key_press(
                    page=page,
                    timeout_ms=PANEL_OBSERVE_TIMEOUT_MS,
                )
                focused_row_state = _capture_tab_state(
                    page=page,
                    panel=panel,
                    first_row_display_name=first_row.display_name,
                    press_index=0,
                    before=None,
                    key="Initial focus",
                    monitor=None,
                )
                if surface_stability_error is not None:
                    focused_row_state["surface_stability_error"] = surface_stability_error
                result["focused_first_row_state"] = focused_row_state
                first_row_label = _focus_label_for_summary(focused_row_state)
                result["first_row_label"] = first_row_label
                _assert_first_row_focus_ready(
                    state=focused_row_state,
                    expected_display_name=first_row.display_name,
                    expected_detail_text=first_row.detail_text,
                )
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=AUTOMATION_STEPS[1],
                    observed=(
                        f"focused_label={_active_from_state(focused_row_state).get('accessible_name')!r}; "
                        f"focus_owned_by_switcher={_focus_from_state(focused_row_state).get('focus_owned_by_switcher')}; "
                        f"first_row_contains_active={_first_row_focus_from_state(focused_row_state).get('row_contains_active')}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Moved keyboard focus onto the selected first saved workspace row "
                        "inside the open panel before starting repeated Tab navigation."
                    ),
                    observed=(
                        f"focused_label={_active_from_state(focused_row_state).get('accessible_name')!r}; "
                        f"first_row_contains_active={_first_row_focus_from_state(focused_row_state).get('row_contains_active')}"
                    ),
                )

                tab_trace: list[dict[str, object]] = []
                footer_state: dict[str, object] | None = None
                looped_before_footer_state: dict[str, object] | None = None
                try:
                    for press_index in range(1, MAX_TABS_TO_REACH_FOOTER + 1):
                        before = page.active_element()
                        page.start_transition_monitor()
                        page.press_key("Tab", timeout_ms=4_000)
                        panel, state = _capture_post_tab_state(
                            page=page,
                            first_row_display_name=first_row.display_name,
                            press_index=press_index,
                            before=before,
                            timeout_ms=PANEL_OBSERVE_TIMEOUT_MS,
                        )
                        tab_trace.append(state)
                        if _footer_control_reached(state):
                            footer_state = state
                            break
                        if _wrapped_to_first_row_before_footer(
                            state,
                            expected_display_name=first_row.display_name,
                            expected_detail_text=first_row.detail_text,
                        ):
                            looped_before_footer_state = state
                            break
                    result["tab_trace_to_footer"] = tab_trace
                    if looped_before_footer_state is not None:
                        result["looped_before_footer_state"] = looped_before_footer_state
                    _assert_traversal_reached_footer(
                        tab_trace=tab_trace,
                        footer_state=footer_state,
                        surface=surface,
                        looped_before_footer_state=looped_before_footer_state,
                        internal_tab_stops=internal_tab_stops,
                        expected_display_name=first_row.display_name,
                        expected_detail_text=first_row.detail_text,
                    )
                except Exception as error:
                    result["tab_trace_to_footer"] = tab_trace
                    if looped_before_footer_state is not None:
                        result["looped_before_footer_state"] = looped_before_footer_state
                    _record_step(
                        result,
                        step=3,
                        status="failed",
                        action=AUTOMATION_STEPS[2],
                        observed=_step3_failure_observed(tab_trace, error),
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Pressed Tab repeatedly through the visible panel controls and "
                            "watched whether focus stayed inside the switcher long enough to "
                            "reach the visible Save and switch footer button."
                        ),
                        observed=(
                            f"visited_labels={_visited_focus_labels(tab_trace)!r}; "
                            f"focus_escape={_focus_escape_summary(tab_trace)!r}; "
                            f"footer_reached={footer_state is not None}; "
                            f"looped_before_footer={looped_before_footer_state is not None}; "
                            f"internal_tab_stops={_tab_stop_label_summary(internal_tab_stops)!r}"
                        ),
                    )
                    raise
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action=AUTOMATION_STEPS[2],
                    observed=(
                        f"tab_count_to_footer={len(tab_trace)}; "
                        f"visited_labels={_visited_focus_labels(tab_trace)!r}; "
                        f"footer_state_label={_footer_focus_label_for_summary(footer_state)!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Pressed Tab repeatedly through the visible panel controls and "
                        "watched focus move through the internal switcher fields until the "
                        "Save and switch footer button visibly owned focus."
                    ),
                    observed=(
                        f"visited_labels={_visited_focus_labels(tab_trace)!r}; "
                        f"footer_visible_label={_footer_focus_label_for_summary(footer_state)!r}; "
                        f"search_issues_reached={_trace_reached_label(tab_trace, 'Search issues')}; "
                        f"internal_tab_stops={_tab_stop_label_summary(internal_tab_stops)!r}"
                    ),
                )

                try:
                    before_wrap = page.active_element()
                    page.start_transition_monitor()
                    page.press_key("Tab", timeout_ms=4_000)
                    panel, wrap_state = _capture_post_tab_state(
                        page=page,
                        first_row_display_name=first_row.display_name,
                        press_index=len(tab_trace) + 1,
                        before=before_wrap,
                        timeout_ms=PANEL_OBSERVE_TIMEOUT_MS,
                    )
                    result["wrap_state_after_footer"] = wrap_state
                    _record_human_verification(
                        result,
                        check=(
                            "Pressed Tab once more from the visible Save and switch footer "
                            "button and watched the focus destination a user would experience next."
                        ),
                        observed=(
                            f"focused_after_wrap={_focus_label_for_summary(wrap_state)!r}; "
                            f"first_row_contains_active={_first_row_focus_from_state(wrap_state).get('row_contains_active')}; "
                            f"focus_owned_by_switcher={_focus_from_state(wrap_state).get('focus_owned_by_switcher')}"
                        ),
                    )
                    _assert_wrap_to_first_row(
                        state=wrap_state,
                        expected_label=first_row_label,
                        expected_display_name=first_row.display_name,
                        expected_detail_text=first_row.detail_text,
                    )
                except Exception as error:
                    if "wrap_state_after_footer" not in result:
                        result["wrap_state_after_footer"] = {}
                    _record_step(
                        result,
                        step=4,
                        status="failed",
                        action=AUTOMATION_STEPS[3],
                        observed=str(error),
                    )
                    raise
                _record_step(
                    result,
                    step=4,
                    status="passed",
                    action=AUTOMATION_STEPS[3],
                    observed=(
                        f"wrapped_focus_label={_focus_label_for_summary(wrap_state)!r}; "
                        f"first_row_contains_active={_first_row_focus_from_state(wrap_state).get('row_contains_active')}; "
                        f"search_issues_reached={_focus_label_for_summary(wrap_state) == 'Search issues'}"
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


def _assert_initial_panel_state(
    *,
    switcher: WorkspaceSwitcherObservation,
    panel: WorkspaceSwitcherPanelObservation,
    rows: tuple[WorkspaceSwitcherSavedWorkspaceRowObservation, ...],
    surface: WorkspaceSwitcherSurfaceObservation,
) -> WorkspaceSwitcherSavedWorkspaceRowObservation:
    failures: list[str] = []
    if "Workspace switcher" not in switcher.switcher_text:
        failures.append("the visible Workspace switcher title was not present")
    if panel.container_kind not in {"anchored-panel", "surface"}:
        failures.append(
            f"the visible panel kind was {panel.container_kind!r} instead of a desktop switcher panel",
        )
    if len(rows) < 3:
        failures.append(
            f"only {len(rows)} saved workspace rows were visible instead of the expected 3+ rows",
        )
    first_row = _selected_saved_workspace(rows)
    if first_row is None:
        failures.append("no saved workspace row was marked selected when the panel opened")
    elif first_row.display_name != FIRST_WORKSPACE_DISPLAY_NAME:
        failures.append(
            f"the selected row was {first_row.display_name!r} instead of {FIRST_WORKSPACE_DISPLAY_NAME!r}",
        )
    labels = _surface_labels(surface)
    for label in (*FIELD_LABELS, LAST_INTERNAL_CONTROL_LABEL):
        if label not in labels:
            failures.append(f"the visible panel did not expose the expected {label!r} control")
    if failures:
        raise AssertionError(
            "Step 1 failed: the workspace switcher panel was not ready for the focus-loop scenario.\n"
            + "\n".join(f"- {item}" for item in failures)
            + "\n"
            + f"Observed panel: {json.dumps(asdict(panel), indent=2)}\n"
            + f"Observed rows: {json.dumps(_saved_workspace_rows_payload(rows), indent=2)}\n"
            + f"Observed surface: {json.dumps(_surface_payload(surface), indent=2)}"
        )
    return first_row


def _assert_first_row_focus_ready(
    *,
    state: dict[str, object],
    expected_display_name: str,
    expected_detail_text: str,
) -> None:
    active = _active_from_state(state)
    focus = _focus_from_state(state)
    first_row_focus = _first_row_focus_from_state(state)
    failures: list[str] = []
    if not _active_label_matches_saved_workspace(
        state,
        display_name=expected_display_name,
        detail_text=expected_detail_text,
    ):
        failures.append(
            "the active label did not match the selected first saved workspace row "
            f"{expected_display_name!r}",
        )
    if not bool(focus.get("focus_owned_by_switcher")):
        failures.append("keyboard focus was not owned by the open workspace switcher")
    if not bool(focus.get("active_within_switcher")):
        failures.append("the active element was not inside the open workspace switcher")
    if bool(focus.get("active_on_trigger")):
        failures.append("focus remained on the workspace-switcher trigger instead of the first row")
    if not bool(first_row_focus.get("row_contains_active")):
        failures.append("the selected first saved workspace row did not contain the active element")
    if failures:
        raise AssertionError(
            "Step 2 failed: the test could not establish focus on the first saved workspace row.\n"
            + "\n".join(f"- {item}" for item in failures)
            + "\n"
            + f"Observed state: {json.dumps(state, indent=2)}"
        )


def _assert_traversal_reached_footer(
    *,
    tab_trace: list[dict[str, object]],
    footer_state: dict[str, object] | None,
    surface: WorkspaceSwitcherSurfaceObservation,
    looped_before_footer_state: dict[str, object] | None,
    internal_tab_stops: tuple[WorkspaceSwitcherTabStopObservation, ...],
    expected_display_name: str,
    expected_detail_text: str,
) -> None:
    failures: list[str] = []
    if not tab_trace:
        failures.append("no Tab traversal states were captured")
    for state in tab_trace:
        label = _focus_label_for_summary(state)
        focus = _focus_from_state(state)
        monitor = _monitor_from_state(state)
        if not bool(focus.get("focus_owned_by_switcher")):
            failures.append(
                f"focus was no longer owned by the switcher after Tab {state.get('press_index')}; active={label!r}",
            )
        if not bool(focus.get("active_within_switcher")):
            failures.append(
                f"the active element left the switcher panel after Tab {state.get('press_index')}; active={label!r}",
            )
        if bool(focus.get("active_on_trigger")):
            failures.append(
                f"focus returned to the workspace-switcher trigger after Tab {state.get('press_index')}",
            )
        if label == "Search issues":
            failures.append("focus escaped to the external Search issues field before the footer button was reached")
        if label == "FLUTTER-VIEW root":
            failures.append(
                f"focus escaped to the application root view after Tab {state.get('press_index')} instead of continuing to the footer button",
            )
        if bool(monitor.get("ever_hidden_after_visible")):
            failures.append(
                f"the switcher panel became hidden after Tab {state.get('press_index')}",
            )
    if footer_state is None:
        if looped_before_footer_state is not None:
            failures.append(
                "focus looped back to the first saved workspace row before the visible "
                f"{LAST_INTERNAL_CONTROL_LABEL!r} footer button was reached",
            )
        else:
            failures.append(
                f"the visible {LAST_INTERNAL_CONTROL_LABEL!r} footer button was never reached within "
                f"{MAX_TABS_TO_REACH_FOOTER} Tab presses",
            )
    else:
        labels = _surface_labels(surface)
        for label in FIELD_LABELS:
            if label in labels and not _trace_reached_label(tab_trace, label):
                failures.append(
                    f"the visible internal {label!r} field was not reached during Tab traversal before the footer button",
                )
    if LAST_INTERNAL_CONTROL_LABEL in _surface_labels(surface):
        tab_stop_labels = {observation.label for observation in internal_tab_stops if observation.label}
        if LAST_INTERNAL_CONTROL_LABEL not in tab_stop_labels:
            failures.append(
                f"the visible {LAST_INTERNAL_CONTROL_LABEL!r} footer button was missing from the live internal tab-stop order",
            )
    if looped_before_footer_state is not None and not _active_label_matches_saved_workspace(
        looped_before_footer_state,
        display_name=expected_display_name,
        detail_text=expected_detail_text,
    ):
        failures.append(
            "the early loop state did not land on the first saved workspace row as expected",
        )
    if failures:
        internal_tab_stop_summary = _tab_stop_label_summary(internal_tab_stops)
        raise AssertionError(
            "Step 3 failed: repeated Tab navigation did not traverse the internal switcher controls as expected.\n"
            + "\n".join(f"- {item}" for item in failures)
            + "\n"
            + f"Observed internal tab stops: {json.dumps(internal_tab_stop_summary, indent=2)}\n"
            + f"Observed trace: {json.dumps(tab_trace, indent=2)}"
        )


def _assert_wrap_to_first_row(
    *,
    state: dict[str, object],
    expected_label: str,
    expected_display_name: str,
    expected_detail_text: str,
) -> None:
    active = _active_from_state(state)
    focus = _focus_from_state(state)
    first_row_focus = _first_row_focus_from_state(state)
    monitor = _monitor_from_state(state)

    failures: list[str] = []
    if not bool(focus.get("focus_owned_by_switcher")):
        failures.append("keyboard focus was not owned by the workspace switcher after the wrap attempt")
    if not bool(focus.get("active_within_switcher")):
        failures.append("keyboard focus left the workspace switcher after the wrap attempt")
    if bool(focus.get("active_on_trigger")):
        failures.append("keyboard focus returned to the workspace-switcher trigger instead of wrapping inside the panel")
    if _focus_label_for_summary(state) == "Search issues":
        failures.append("keyboard focus escaped to the external Search issues field instead of wrapping inside the panel")
    if bool(monitor.get("ever_hidden_after_visible")):
        failures.append("the workspace switcher panel became hidden during the wrap attempt")
    if not bool(first_row_focus.get("row_contains_active")):
        failures.append(
            f"the first saved workspace row did not receive focus after pressing Tab on {LAST_INTERNAL_CONTROL_LABEL!r}",
        )
    if not _active_label_matches_saved_workspace(
        state,
        display_name=expected_display_name,
        detail_text=expected_detail_text,
    ):
        failures.append(
            f"the active label {_focus_label_for_summary(state)!r} did not match the first "
            f"saved workspace row {expected_label!r} after the wrap attempt",
        )
    if failures:
        raise AssertionError(
            "Step 4 failed: pressing Tab on the final visible panel control did not wrap focus to the first saved workspace row.\n"
            + "\n".join(f"- {item}" for item in failures)
            + "\n"
            + f"Observed wrap state: {json.dumps(state, indent=2)}"
        )


def _capture_tab_state(
    *,
    page: LiveWorkspaceSwitcherPage,
    panel: WorkspaceSwitcherPanelObservation,
    first_row_display_name: str,
    press_index: int,
    before: FocusedElementObservation | None,
    key: str,
    monitor: WorkspaceSwitcherTransitionMonitorObservation | None,
) -> dict[str, object]:
    active = page.active_element()
    focus = page.observe_focus_ownership(panel=panel)
    first_row_focus = page.observe_saved_workspace_row_focus(
        display_name=first_row_display_name,
        panel=panel,
    )
    state: dict[str, object] = {
        "key": key,
        "press_index": press_index,
        "panel": asdict(panel),
        "active": _focused_element_payload(active),
        "focus": _focus_ownership_payload(focus),
        "first_row_focus": _row_focus_payload(first_row_focus),
    }
    if before is not None:
        state["before"] = _focused_element_payload(before)
    if monitor is not None:
        state["monitor"] = _monitor_payload(monitor)
    return state


def _capture_post_tab_state(
    *,
    page: LiveWorkspaceSwitcherPage,
    first_row_display_name: str,
    press_index: int,
    before: FocusedElementObservation,
    timeout_ms: int,
) -> tuple[WorkspaceSwitcherPanelObservation, dict[str, object]]:
    panel, surface_stability_error = _observe_panel_after_key_press(
        page=page,
        timeout_ms=timeout_ms,
    )
    monitor = page.read_transition_monitor(clear=True)
    state = _capture_tab_state(
        page=page,
        panel=panel,
        first_row_display_name=first_row_display_name,
        press_index=press_index,
        before=before,
        key="Tab",
        monitor=monitor,
    )
    _attach_footer_button_state_if_needed(
        page=page,
        panel=panel,
        state=state,
        timeout_ms=timeout_ms,
    )
    state["panel_detected_after_key"] = True
    if surface_stability_error is not None:
        state["surface_stability_error"] = surface_stability_error
    return panel, state


def _observe_panel_after_key_press(
    *,
    page: LiveWorkspaceSwitcherPage,
    timeout_ms: int,
) -> tuple[WorkspaceSwitcherPanelObservation, str | None]:
    surface_stability_error: str | None = None
    try:
        page.wait_for_surface_to_remain_open(
            stability_ms=FOCUS_SETTLE_MS,
            timeout_ms=timeout_ms,
        )
    except Exception as error:
        surface_stability_error = f"{type(error).__name__}: {error}"
    try:
        panel = page.observe_open_panel(
            expected_container_kinds=("anchored-panel", "surface", "dialog"),
            timeout_ms=timeout_ms,
        )
        return panel, surface_stability_error
    except Exception as error:
        raise AssertionError(
            "The test could not re-observe the visible workspace switcher panel after the "
            "keyboard interaction, so the next focus target could not be sampled reliably.\n"
            + (
                f"Observed stability wait error: {surface_stability_error}\n"
                if surface_stability_error is not None
                else ""
            )
            + f"Observed panel error: {type(error).__name__}: {error}"
        ) from error


def _attach_footer_button_state_if_needed(
    *,
    page: LiveWorkspaceSwitcherPage,
    panel: WorkspaceSwitcherPanelObservation,
    state: dict[str, object],
    timeout_ms: int,
) -> None:
    label = _focus_label_for_summary(state)
    if label not in {LAST_INTERNAL_CONTROL_LABEL, "anonymous FLT-SEMANTICS"}:
        return
    try:
        footer_button = page.observe_switcher_button_state(
            LAST_INTERNAL_CONTROL_LABEL,
            panel=panel,
            timeout_ms=timeout_ms,
        )
    except AssertionError as error:
        state["footer_button_error"] = str(error)
        return
    state["footer_button"] = _button_state_payload(footer_button)


def _workspace_state(repository: str) -> dict[str, object]:
    first_id = f"hosted:{repository.lower()}@{DEFAULT_BRANCH}"
    second_id = f"hosted:{repository.lower()}@{DEFAULT_BRANCH}:{SECOND_WORKSPACE_WRITE_BRANCH}"
    third_id = f"hosted:{repository.lower()}@{DEFAULT_BRANCH}:{THIRD_WORKSPACE_WRITE_BRANCH}"
    return {
        "activeWorkspaceId": first_id,
        "migrationComplete": True,
        "profiles": [
            {
                "id": first_id,
                "displayName": FIRST_WORKSPACE_DISPLAY_NAME,
                "customDisplayName": FIRST_WORKSPACE_DISPLAY_NAME,
                "targetType": "hosted",
                "target": repository,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": DEFAULT_BRANCH,
                "lastOpenedAt": "2026-05-21T23:30:00.000Z",
            },
            {
                "id": second_id,
                "displayName": SECOND_WORKSPACE_DISPLAY_NAME,
                "customDisplayName": SECOND_WORKSPACE_DISPLAY_NAME,
                "targetType": "hosted",
                "target": repository,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": SECOND_WORKSPACE_WRITE_BRANCH,
                "lastOpenedAt": "2026-05-21T23:20:00.000Z",
            },
            {
                "id": third_id,
                "displayName": THIRD_WORKSPACE_DISPLAY_NAME,
                "customDisplayName": THIRD_WORKSPACE_DISPLAY_NAME,
                "targetType": "hosted",
                "target": repository,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": THIRD_WORKSPACE_WRITE_BRANCH,
                "lastOpenedAt": "2026-05-21T23:10:00.000Z",
            },
        ],
    }


def _selected_saved_workspace(
    rows: tuple[WorkspaceSwitcherSavedWorkspaceRowObservation, ...],
) -> WorkspaceSwitcherSavedWorkspaceRowObservation | None:
    selected_row = next((row for row in rows if row.selected), None)
    if selected_row is not None:
        return selected_row
    expected_row = next(
        (row for row in rows if row.display_name == FIRST_WORKSPACE_DISPLAY_NAME),
        None,
    )
    if expected_row is not None:
        return expected_row
    return rows[0] if rows else None


def _saved_workspace_row_focus_label(
    row: WorkspaceSwitcherSavedWorkspaceRowObservation,
) -> str:
    segments = [row.display_name]
    if row.target_type_label:
        segments.append(row.target_type_label)
    if row.state_label:
        segments.append(row.state_label)
    return ", ".join(segments) + f", {row.detail_text}"


def _saved_workspace_rows_payload(
    rows: tuple[WorkspaceSwitcherSavedWorkspaceRowObservation, ...] | list[object],
) -> list[dict[str, object]]:
    payload: list[dict[str, object]] = []
    for row in rows:
        if not isinstance(row, WorkspaceSwitcherSavedWorkspaceRowObservation):
            continue
        payload.append(
            {
                "display_name": row.display_name,
                "target_type_label": row.target_type_label,
                "state_label": row.state_label,
                "detail_text": row.detail_text,
                "selected": row.selected,
                "action_labels": list(row.action_labels),
                "left": row.left,
                "top": row.top,
                "width": row.width,
                "height": row.height,
            },
        )
    return payload


def _focused_element_payload(observation: FocusedElementObservation) -> dict[str, object]:
    return {
        "accessible_name": observation.accessible_name,
        "role": observation.role,
        "tag_name": observation.tag_name,
        "text": observation.text,
        "outer_html": observation.outer_html,
    }


def _focus_ownership_payload(
    observation: WorkspaceSwitcherFocusOwnershipObservation,
) -> dict[str, object]:
    return {
        "active_label": observation.active_label,
        "active_role": observation.active_role,
        "active_tag_name": observation.active_tag_name,
        "active_outer_html": observation.active_outer_html,
        "active_visible": observation.active_visible,
        "active_in_viewport": observation.active_in_viewport,
        "switcher_focus_within": observation.switcher_focus_within,
        "active_within_switcher": observation.active_within_switcher,
        "active_on_trigger": observation.active_on_trigger,
        "focus_owned_by_switcher": observation.focus_owned_by_switcher,
    }


def _row_focus_payload(
    observation: WorkspaceSwitcherRowFocusObservation,
) -> dict[str, object]:
    return {
        "active_label": observation.active_label,
        "active_role": observation.active_role,
        "active_tag_name": observation.active_tag_name,
        "active_outer_html": observation.active_outer_html,
        "active_visible": observation.active_visible,
        "active_in_viewport": observation.active_in_viewport,
        "active_within_switcher": observation.active_within_switcher,
        "active_on_trigger": observation.active_on_trigger,
        "focus_owned_by_switcher": observation.focus_owned_by_switcher,
        "row_found": observation.row_found,
        "row_contains_active": observation.row_contains_active,
        "row_text": observation.row_text,
    }


def _trigger_payload(trigger: WorkspaceSwitcherTriggerObservation) -> dict[str, object]:
    return {
        "semantic_label": trigger.semantic_label,
        "visible_text": trigger.visible_text,
        "display_name": trigger.display_name,
        "workspace_type": trigger.workspace_type,
        "state_label": trigger.state_label,
        "raw_text_lines": list(trigger.raw_text_lines),
        "icon_count": trigger.icon_count,
        "left": trigger.left,
        "top": trigger.top,
        "width": trigger.width,
        "height": trigger.height,
        "top_button_labels": list(trigger.top_button_labels),
    }


def _switcher_payload(switcher: WorkspaceSwitcherObservation) -> dict[str, object]:
    return {
        "body_text": switcher.body_text,
        "switcher_text": switcher.switcher_text,
        "row_count": switcher.row_count,
        "rows": [
            {
                "display_name": row.display_name,
                "target_type_label": row.target_type_label,
                "state_label": row.state_label,
                "detail_text": row.detail_text,
                "visible_text": row.visible_text,
                "selected": row.selected,
                "semantics_label": row.semantics_label,
                "icon_accessibility_label": row.icon_accessibility_label,
                "action_labels": list(row.action_labels),
                "button_labels": list(row.button_labels),
            }
            for row in switcher.rows
        ],
    }


def _surface_payload(surface: WorkspaceSwitcherSurfaceObservation) -> dict[str, object]:
    return {
        "heading_text": surface.heading_text,
        "interactive_elements": [
            {
                "label": item.label,
                "accessible_label": item.accessible_label,
                "role": item.role,
                "tag_name": item.tag_name,
                "x": item.x,
                "y": item.y,
                "width": item.width,
                "height": item.height,
            }
            for item in surface.interactive_elements
        ],
        "missing_interactive_labels": list(surface.missing_interactive_labels),
        "missing_semantics_labels": list(surface.missing_semantics_labels),
    }


def _monitor_payload(
    observation: WorkspaceSwitcherTransitionMonitorObservation,
) -> dict[str, object]:
    return {
        "sample_count": observation.sample_count,
        "visible_sample_count": observation.visible_sample_count,
        "hidden_sample_count": observation.hidden_sample_count,
        "ever_hidden_after_visible": observation.ever_hidden_after_visible,
        "observed_container_kinds": list(observation.observed_container_kinds),
        "observed_row_counts": list(observation.observed_row_counts),
        "observed_active_workspace_names": list(observation.observed_active_workspace_names),
        "latest_visible_container_kind": observation.latest_visible_container_kind,
        "latest_visible_row_count": observation.latest_visible_row_count,
        "latest_visible_active_workspace_name": observation.latest_visible_active_workspace_name,
    }


def _button_state_payload(
    observation: WorkspaceSwitcherButtonStateObservation,
) -> dict[str, object]:
    return {
        "label": observation.label,
        "visible_text": observation.visible_text,
        "role": observation.role,
        "tag_name": observation.tag_name,
        "tabindex": observation.tabindex,
        "tab_index_value": observation.tab_index_value,
        "aria_disabled": observation.aria_disabled,
        "disabled": observation.disabled,
        "keyboard_focusable": observation.keyboard_focusable,
        "active_within": observation.active_within,
        "outer_html": observation.outer_html,
    }


def _tab_stops_payload(
    tab_stops: tuple[WorkspaceSwitcherTabStopObservation, ...],
) -> list[dict[str, object]]:
    return [
        {
            "label": observation.label,
            "visible_text": observation.visible_text,
            "role": observation.role,
            "tag_name": observation.tag_name,
            "tabindex": observation.tabindex,
            "tab_index_value": observation.tab_index_value,
            "dom_index": observation.dom_index,
            "keyboard_focusable": observation.keyboard_focusable,
            "disabled": observation.disabled,
        }
        for observation in tab_stops
    ]


def _surface_labels(surface: WorkspaceSwitcherSurfaceObservation) -> set[str]:
    return {item.label for item in surface.interactive_elements if item.label}


def _surface_label_summary(surface: WorkspaceSwitcherSurfaceObservation) -> list[str]:
    labels = sorted(_surface_labels(surface))
    return labels[:12]


def _tab_stop_label_summary(
    tab_stops: tuple[WorkspaceSwitcherTabStopObservation, ...],
) -> list[str]:
    return [
        observation.label or observation.visible_text or observation.tag_name
        for observation in tab_stops
    ]


def _visited_focus_labels(states: list[dict[str, object]]) -> list[str]:
    labels: list[str] = []
    for state in states:
        label = _footer_focus_label_for_summary(state)
        if not labels or labels[-1] != label:
            labels.append(label)
    return labels


def _trace_reached_label(states: list[dict[str, object]], label: str) -> bool:
    if label == LAST_INTERNAL_CONTROL_LABEL:
        return any(_footer_control_reached(state) for state in states)
    return any(_focus_label_for_summary(state) == label for state in states)


def _active_from_state(state: dict[str, object] | None) -> dict[str, object]:
    if not isinstance(state, dict):
        return {}
    active = state.get("active")
    return active if isinstance(active, dict) else {}


def _focus_from_state(state: dict[str, object] | None) -> dict[str, object]:
    if not isinstance(state, dict):
        return {}
    focus = state.get("focus")
    return focus if isinstance(focus, dict) else {}


def _first_row_focus_from_state(state: dict[str, object] | None) -> dict[str, object]:
    if not isinstance(state, dict):
        return {}
    row_focus = state.get("first_row_focus")
    return row_focus if isinstance(row_focus, dict) else {}


def _monitor_from_state(state: dict[str, object] | None) -> dict[str, object]:
    if not isinstance(state, dict):
        return {}
    monitor = state.get("monitor")
    return monitor if isinstance(monitor, dict) else {}


def _footer_button_from_state(state: dict[str, object] | None) -> dict[str, object]:
    if not isinstance(state, dict):
        return {}
    footer_button = state.get("footer_button")
    return footer_button if isinstance(footer_button, dict) else {}


def _footer_control_reached(state: dict[str, object] | None) -> bool:
    label = _focus_label_for_summary(state)
    footer_button = _footer_button_from_state(state)
    return label == LAST_INTERNAL_CONTROL_LABEL or bool(footer_button.get("active_within"))


def _footer_focus_label_for_summary(state: dict[str, object] | None) -> str:
    label = _focus_label_for_summary(state)
    if label != "anonymous FLT-SEMANTICS":
        return label
    footer_button = _footer_button_from_state(state)
    if bool(footer_button.get("active_within")):
        footer_label = str(footer_button.get("label") or "").strip()
        if footer_label:
            return footer_label
    return label


def _focus_label_for_summary(state: dict[str, object] | None) -> str:
    active = _active_from_state(state)
    accessible_name = str(active.get("accessible_name") or "").strip()
    tag_name = str(active.get("tag_name") or "").strip()
    role = str(active.get("role") or "").strip()
    if tag_name == "FLUTTER-VIEW":
        return "FLUTTER-VIEW root"
    if tag_name == "FLT-SEMANTICS" and not accessible_name:
        return "anonymous FLT-SEMANTICS"
    if accessible_name:
        return accessible_name
    if role or tag_name:
        return " ".join(part for part in (role, tag_name) if part)
    return "unknown focus target"


def _active_label_matches_saved_workspace(
    state: dict[str, object] | None,
    *,
    display_name: str,
    detail_text: str,
) -> bool:
    label = _focus_label_for_summary(state)
    return display_name in label and detail_text in label


def _wrapped_to_first_row_before_footer(
    state: dict[str, object] | None,
    *,
    expected_display_name: str,
    expected_detail_text: str,
) -> bool:
    if _footer_control_reached(state):
        return False
    return _active_label_matches_saved_workspace(
        state,
        display_name=expected_display_name,
        detail_text=expected_detail_text,
    )


def _first_focus_escape_index(states: list[dict[str, object]]) -> int | None:
    for index, state in enumerate(states):
        focus = _focus_from_state(state)
        if (
            _focus_label_for_summary(state) == "FLUTTER-VIEW root"
            or not bool(focus.get("focus_owned_by_switcher"))
            or not bool(focus.get("active_within_switcher"))
            or not bool(state.get("panel_detected_after_key", True))
        ):
            return index
    return None


def _focus_escape_summary(states: list[dict[str, object]]) -> str:
    escape_index = _first_focus_escape_index(states)
    if escape_index is None:
        return "none"
    escape_state = states[escape_index]
    return (
        f"Tab {escape_state.get('press_index')} -> {_focus_label_for_summary(escape_state)} "
        f"(focus_owned_by_switcher={_focus_from_state(escape_state).get('focus_owned_by_switcher')}, "
        f"active_within_switcher={_focus_from_state(escape_state).get('active_within_switcher')})"
    )


def _step3_failure_observed(
    states: list[dict[str, object]],
    error: Exception,
) -> str:
    error_summary = str(error).splitlines()[0]
    return (
        f"visited_labels={_visited_focus_labels(states)!r}; "
        f"focus_escape={_focus_escape_summary(states)!r}; "
        f"footer_reached={any(_footer_control_reached(state) for state in states)}; "
        f"error={error_summary}"
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
    if not isinstance(steps, list):
        raise AssertionError("Result steps store must be a list.")
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
    items = result.setdefault("human_verification", [])
    if not isinstance(items, list):
        raise AssertionError("Result human_verification store must be a list.")
    items.append(
        {
            "check": check,
            "observed": observed,
        },
    )


def _steps(result: dict[str, object]) -> list[dict[str, object]]:
    steps = result.get("steps")
    return steps if isinstance(steps, list) else []


def _human_verification(result: dict[str, object]) -> list[dict[str, object]]:
    items = result.get("human_verification")
    return items if isinstance(items, list) else []


def _failed_step(result: dict[str, object]) -> dict[str, object] | None:
    for step in _steps(result):
        if step.get("status") == "failed":
            return step
    return None


def _failed_step_label(result: dict[str, object]) -> str:
    failed = _failed_step(result)
    if failed is None:
        return "Unknown"
    return f"Step {failed.get('step')} — {failed.get('action')}"


def _failed_step_summary(result: dict[str, object]) -> str:
    failed = _failed_step(result)
    if failed is None:
        return str(result.get("error", "unknown failure"))
    return (
        f"{_failed_step_label(result)}: "
        f"{failed.get('observed') or result.get('error', 'unknown failure')}"
    )


def _review_replies_payload(result: dict[str, object], *, passed: bool) -> str:
    replies = [
        {
            "inReplyToId": thread.get("rootCommentId"),
            "threadId": thread.get("threadId"),
            "reply": _review_reply_text(result, passed=passed),
        }
        for thread in _discussion_threads()
    ]
    return json.dumps({"replies": replies}, indent=2) + "\n"


def _discussion_threads() -> list[dict[str, object]]:
    if not DISCUSSIONS_RAW_PATH.is_file():
        return []
    raw = json.loads(DISCUSSIONS_RAW_PATH.read_text(encoding="utf-8"))
    threads = raw.get("threads")
    if not isinstance(threads, list):
        return []
    return [
        thread
        for thread in threads
        if isinstance(thread, dict)
        and thread.get("resolved") is False
        and thread.get("rootCommentId") is not None
        and thread.get("threadId") is not None
    ]


def _review_reply_text(result: dict[str, object], *, passed: bool) -> str:
    rerun_summary = (
        f"Re-ran `{RUN_COMMAND}`: passed (`1 passed, 0 failed`)."
        if passed
        else f"Re-ran `{RUN_COMMAND}`: still failing. Current failure: {_failed_step_summary(result)}"
    )
    return (
        "Resolved the merge conflict in `testing/tests/TS-910/test_ts_910.py`, kept the "
        "diagnostics that capture the live internal tab-stop order and the loop-before-footer "
        "case, and regenerated the required `outputs/` artifacts. "
        f"{rerun_summary}"
    )


def _runtime_body_text(result: dict[str, object]) -> str:
    runtime_body_text = result.get("runtime_body_text")
    if isinstance(runtime_body_text, str) and runtime_body_text.strip():
        return runtime_body_text.strip()
    return str(result.get("error", "")).split("Visible body text:", 1)[-1].strip() or ""


def _actual_vs_expected_summary(result: dict[str, object]) -> str:
    failed = _failed_step(result)
    if failed is not None and failed.get("step") == 1:
        body_text = _runtime_body_text(result)
        return (
            "The deployed app never reached the ticket precondition for the workspace-switcher "
            "focus-loop scenario. Instead of the desktop tracker shell and workspace switcher, "
            f"the visible page content was {body_text!r}."
        )
    if failed is not None and failed.get("step") == 3:
        trace = result.get("tab_trace_to_footer")
        looped_before_footer_state = result.get("looped_before_footer_state")
        internal_tab_stops = result.get("internal_tab_stops_before_focus")
        if isinstance(trace, list) and trace:
            escape_index = _first_focus_escape_index(trace)
            visited_labels = _visited_focus_labels(trace)
            if escape_index is not None:
                escape_state = trace[escape_index]
                prior_label = (
                    _focus_label_for_summary(trace[escape_index - 1])
                    if escape_index > 0
                    else str(result.get("first_row_label", "the first saved workspace row"))
                )
                return (
                    f"After focus advanced to {prior_label!r}, pressing Tab moved focus to "
                    f"{_focus_label_for_summary(escape_state)!r} outside the expected in-panel "
                    f"loop before the visible {LAST_INTERNAL_CONTROL_LABEL!r} footer button was reached. "
                    f"visited_labels={visited_labels!r}."
                )
            if isinstance(looped_before_footer_state, dict):
                return (
                    f"Tab traversal stayed inside the workspace switcher, but it looped back to "
                    f"the first saved workspace row {_focus_label_for_summary(looped_before_footer_state)!r} "
                    f"before the visible {LAST_INTERNAL_CONTROL_LABEL!r} footer button became reachable. "
                    f"internal_tab_stops={internal_tab_stops!r}; visited_labels={visited_labels!r}."
                )
            return (
                f"The switcher never reached the visible {LAST_INTERNAL_CONTROL_LABEL!r} footer "
                f"button during Tab traversal. visited_labels={visited_labels!r}."
            )
    wrap_state = result.get("wrap_state_after_footer")
    if isinstance(wrap_state, dict):
        focus = _focus_from_state(wrap_state)
        return (
            f"After the final visible {LAST_INTERNAL_CONTROL_LABEL!r} footer button received focus, "
            f"pressing Tab left focus on {_focus_label_for_summary(wrap_state)!r} instead of wrapping "
            f"to the first saved workspace row. "
            f"focus_owned_by_switcher={focus.get('focus_owned_by_switcher')}."
        )
    trace = result.get("tab_trace_to_footer")
    if isinstance(trace, list) and trace:
        return (
            f"The switcher did not complete the expected internal Tab traversal before wrapping: "
            f"visited_labels={_visited_focus_labels(trace)!r}."
        )
    return str(result.get("error", "The focus loop did not match the expected result."))


def _annotated_request_steps(result: dict[str, object]) -> str:
    failed = _failed_step(result)
    if failed is not None and failed.get("step") == 1:
        body_text = _runtime_body_text(result)
        return "\n".join(
            [
                (
                    f"# ❌ {REQUEST_STEPS[0]} — Could not start the panel traversal because "
                    "the deployed desktop app never exposed the workspace switcher scenario. "
                    f"Visible page content: {body_text!r}."
                ),
                (
                    f"# ❌ {REQUEST_STEPS[1]} — The wrap verification could not run because "
                    "the final interactive panel control was never reachable after the failed "
                    f"startup state {body_text!r}."
                ),
            ],
        )
    if failed is not None and failed.get("step") == 3:
        trace = result.get("tab_trace_to_footer")
        visited_labels = _visited_focus_labels(trace) if isinstance(trace, list) else []
        escape_index = _first_focus_escape_index(trace if isinstance(trace, list) else [])
        looped_before_footer_state = result.get("looped_before_footer_state")
        internal_tab_stops = result.get("internal_tab_stops_before_focus")
        last_label = (
            _focus_label_for_summary(trace[-1])
            if isinstance(trace, list) and trace
            else "an unexpected focus target"
        )
        return "\n".join(
            [
                (
                    f"# ❌ {REQUEST_STEPS[0]} — Focus moved through {visited_labels!r} and then "
                    + (
                        f"escaped to {_focus_label_for_summary(trace[escape_index])!r} before the "
                        f"visible {LAST_INTERNAL_CONTROL_LABEL!r} footer control was reached."
                        if isinstance(trace, list) and escape_index is not None
                        else f"stalled on {last_label!r} instead of reaching the visible "
                        f"{LAST_INTERNAL_CONTROL_LABEL!r} footer control."
                    )
                ),
                (
                    f"# ❌ {REQUEST_STEPS[1]} — The wrap verification could not run because "
                    + (
                        "the workspace switcher lost the required in-panel focus loop before the "
                        f"final interactive control was reachable. focus_escape="
                        f"{_focus_label_for_summary(trace[escape_index])!r}."
                        if isinstance(trace, list) and escape_index is not None
                        else (
                            "focus looped back to the first saved workspace row before the "
                            f"visible {LAST_INTERNAL_CONTROL_LABEL!r} footer control became "
                            f"reachable. internal_tab_stops={internal_tab_stops!r}; "
                            f"last_focus={_focus_label_for_summary(looped_before_footer_state)!r}."
                            if isinstance(looped_before_footer_state, dict)
                            else "the visible footer control never became reachable within the "
                            f"captured in-panel tab order. internal_tab_stops={internal_tab_stops!r}; "
                            f"last_focus={last_label!r}."
                        )
                    )
                ),
            ],
        )
    trace = result.get("tab_trace_to_footer")
    wrap_state = result.get("wrap_state_after_footer")
    visited_labels = _visited_focus_labels(trace) if isinstance(trace, list) else []
    wrapped_correctly = False
    if isinstance(wrap_state, dict):
        wrapped_correctly = _active_label_matches_saved_workspace(
            wrap_state,
            display_name=str(result.get("first_row_display_name", "")),
            detail_text=str(result.get("first_row_detail_text", "")),
        )
    lines = [
        (
            f"# {'✅' if visited_labels else '❌'} {REQUEST_STEPS[0]} — "
            + (
                f"Observed internal focus labels: {visited_labels!r}."
                if visited_labels
                else "The test did not capture a valid internal Tab traversal."
            )
        ),
        (
            f"# {'✅' if wrapped_correctly else '❌'} "
            f"{REQUEST_STEPS[1]} — "
            + (
                f"After the footer control, focus landed on {_focus_label_for_summary(wrap_state)!r}; "
                f"expected_first_row={result.get('first_row_label')!r}."
                if isinstance(wrap_state, dict)
                else "The wrap attempt could not be captured."
            )
        ),
    ]
    return "\n".join(lines)


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
    REVIEW_REPLIES_PATH.write_text(
        _review_replies_payload(result, passed=True),
        encoding="utf-8",
    )


def _write_failure_outputs(result: dict[str, object]) -> None:
    error = str(result.get("error", "AssertionError: TS-910 failed"))
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
    REVIEW_REPLIES_PATH.write_text(
        _review_replies_payload(result, passed=False),
        encoding="utf-8",
    )
    BUG_DESCRIPTION_PATH.write_text(_bug_description(result), encoding="utf-8")


def _jira_comment(result: dict[str, object], *, passed: bool) -> str:
    status = "✅ PASSED" if passed else "❌ FAILED"
    lines = [
        "h3. Test Automation Result",
        "",
        f"*Status:* {status}",
        f"*Test Case:* {TICKET_KEY} — {TEST_CASE_TITLE}",
        "",
        "h4. What was tested",
    ]
    lines.extend(
        f"* Step {step['step']}: {step['action']} — {step['status'].upper()}: {step['observed']}"
        for step in _steps(result)
    )
    lines.extend(
        [
            "",
            "h4. Result",
            (
                f"* Matched expected focus-loop behavior. {_actual_vs_expected_summary(result) if not passed else 'Tab traversal stayed within the open panel and wrapped back to the first saved workspace row.'}"
                if passed
                else f"* {_actual_vs_expected_summary(result)}"
            ),
            "* Human-style verification confirmed the visible desktop panel labels and the observed keyboard focus destination matched the recorded result."
            if passed
            else f"* Human-style verification matched the failed step outcome: {_failed_step_label(result)}.",
            "",
            "h4. Human-style verification",
        ],
    )
    lines.extend(
        f"* {item['check']} — {item['observed']}" for item in _human_verification(result)
    )
    lines.extend(
        [
            "",
            "h4. Test file",
            "{code}",
            "testing/tests/TS-910/test_ts_910.py",
            "{code}",
            "",
            "h4. Run command",
            "{code:bash}",
            RUN_COMMAND,
            "{code}",
        ],
    )
    if not passed:
        lines.extend(
            [
                "",
                "h4. Failure details",
                f"* Failed step: {_failed_step_label(result)}",
                "{code}",
                str(result.get("error", "")),
                "{code}",
            ],
        )
    return "\n".join(lines) + "\n"


def _pr_body(result: dict[str, object], *, passed: bool) -> str:
    status = "✅ PASSED" if passed else "❌ FAILED"
    lines = [
        "## Test Automation Result",
        "",
        f"**Status:** {status}",
        f"**Test Case:** {TICKET_KEY} — {TEST_CASE_TITLE}",
        "",
        "## What was automated",
    ]
    lines.extend(
        f"- Step {step['step']}: {step['action']} — **{step['status'].upper()}**: {step['observed']}"
        for step in _steps(result)
    )
    lines.extend(
        [
            "",
            "## Result",
            (
                "- Tab traversal stayed inside the visible workspace switcher panel and wrapped back to the first saved workspace row after the footer button."
                if passed
                else f"- {_actual_vs_expected_summary(result)}"
            ),
            "",
            "## Human-style verification",
        ],
    )
    lines.extend(
        f"- {item['check']} — {item['observed']}" for item in _human_verification(result)
    )
    lines.extend(
        [
            "",
            "## How to run",
            "```bash",
            RUN_COMMAND,
            "```",
        ],
    )
    if not passed:
        lines.extend(
            [
                "",
                "## Failure details",
                f"- **Failed step:** {_failed_step_label(result)}",
                f"- **Error:** `{result.get('error')}`",
                f"- **Screenshot:** `{result.get('screenshot')}`"
                if result.get("screenshot")
                else "- **Screenshot:** not captured",
            ],
        )
    return "\n".join(lines) + "\n"


def _response_summary(result: dict[str, object], *, passed: bool) -> str:
    status = "PASSED" if passed else "FAILED"
    observed = (
        "Tab traversal stayed inside the visible workspace switcher panel and wrapped back to the first saved workspace row."
        if passed
        else _actual_vs_expected_summary(result)
    )
    return (
        f"# {TICKET_KEY} — {status}\n\n"
        f"- Test case: **{TEST_CASE_TITLE}**\n"
        f"- Environment: `{result['app_url']}` on Chromium/Playwright ({result['os']})\n"
        f"- Expected result: {EXPECTED_RESULT}\n"
        f"- Observed: {observed}\n"
        f"- Screenshot: `{result.get('screenshot')}`\n"
    )


def _bug_description(result: dict[str, object]) -> str:
    screenshot = result.get("screenshot", "not captured")
    failed_step = _failed_step(result)
    note = (
        "* The live desktop app never reached the workspace-switcher precondition, so the automation reported the earliest product-visible mismatch before any panel traversal could begin."
        if failed_step is not None and failed_step.get("step") == 1
        else "* The live panel did not reach the ticket's expected saved-workspace traversal state, so the automation reported the earliest product-visible mismatch."
        if failed_step is not None and failed_step.get("step") != 4
        else "* The regression reproduction stayed within the visible panel; the final Tab press failed because focus did not loop back to the first internal row."
    )
    return "\n".join(
        [
            f"h4. Summary",
            _actual_vs_expected_summary(result),
            "",
            "h4. Environment",
            f"* URL: {{{{{result.get('app_url')}}}}}",
            f"* Repository: {{{{{result.get('repository')}}}}} @ {{{{{result.get('repository_ref')}}}}}",
            f"* Browser: {{{{{result.get('browser')}}}}}",
            f"* OS: {{{{{result.get('os')}}}}}",
            f"* Viewport: {{{{{DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}}}}}",
            f"* Run command: {{code:bash}}{RUN_COMMAND}{{code}}",
            f"* Screenshot: {{{{{screenshot}}}}}",
            "",
            "h4. Steps to Reproduce",
            _annotated_request_steps(result),
            "",
            "h4. Expected Result",
            EXPECTED_RESULT,
            "",
            "h4. Actual Result",
            _actual_vs_expected_summary(result),
            "",
            "h4. Logs / Error Output",
            "{code}",
            str(result.get("error", "")),
            "",
            str(result.get("traceback", "")),
            "{code}",
            "",
            "h4. Notes",
            f"* Focus labels observed before the failure: {_visited_focus_labels(result.get('tab_trace_to_footer') if isinstance(result.get('tab_trace_to_footer'), list) else [])!r}",
            note,
        ],
    ) + "\n"


if __name__ == "__main__":
    main()
