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
    WorkspaceSwitcherObservation,
    WorkspaceSwitcherPanelObservation,
    WorkspaceSwitcherRowFocusObservation,
    WorkspaceSwitcherSavedWorkspaceRowObservation,
    WorkspaceSwitcherSurfaceObservation,
    WorkspaceSwitcherTabStopObservation,
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

TICKET_KEY = "TS-1007"
TEST_CASE_TITLE = (
    "Press Shift+Tab in pristine state - focus wraps to the disabled "
    "'Save and switch' button"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-1007/test_ts_1007.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
FOCUS_TIMEOUT_MS = 4_000
FOCUS_SETTLE_MS = 300
DEFAULT_BRANCH = "main"
FIRST_WORKSPACE_DISPLAY_NAME = "Hosted main workspace"
SECOND_WORKSPACE_DISPLAY_NAME = "Hosted alt workspace"
THIRD_WORKSPACE_DISPLAY_NAME = "Hosted third workspace"
SECOND_WORKSPACE_WRITE_BRANCH = "ts-1007-alt"
THIRD_WORKSPACE_WRITE_BRANCH = "ts-1007-third"
LAST_INTERNAL_CONTROL_LABEL = "Save and switch"
LINKED_BUGS = ["TS-997"]

PRECONDITIONS = [
    "The TrackState application is opened.",
    "The workspace switcher panel is open in a pristine state (no changes made).",
    "Keyboard focus is on the first interactive element in the panel.",
]
REQUEST_STEPS = [
    "Press the 'Shift + Tab' keys on the keyboard.",
]
AUTOMATION_STEPS = [
    (
        "Open the deployed desktop workspace switcher in pristine state and confirm "
        "the visible footer still exposes a disabled Save and switch boundary."
    ),
    (
        "Establish focus on the first internal panel target, press Shift+Tab once, "
        "and verify focus wraps to the disabled Save and switch footer button while "
        "the panel stays open."
    ),
]
EXPECTED_RESULT = (
    "Keyboard focus wraps to the 'Save and switch' button in the footer. The panel "
    "remains open, and the button is correctly identified as a valid tab-stop "
    "boundary despite being disabled, confirming the focus-trap fix."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1007_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1007_failure.png"

WORKSPACE_NAMES = (
    FIRST_WORKSPACE_DISPLAY_NAME,
    SECOND_WORKSPACE_DISPLAY_NAME,
    THIRD_WORKSPACE_DISPLAY_NAME,
)


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-1007 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
        )
    user = service.fetch_authenticated_user()
    workspace_state = _workspace_state(service.repository)

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
        "preconditions": PRECONDITIONS,
        "preloaded_workspace_state": workspace_state,
        "user_login": user.login,
        "steps": [],
        "human_verification": [],
        "product_defect": False,
    }
    current_step = 1
    current_action = AUTOMATION_STEPS[0]
    page: LiveWorkspaceSwitcherPage | None = None
    try:
        with create_live_tracker_app(
            config,
            runtime_factory=lambda: StoredWorkspaceProfilesRuntime(
                repository=service.repository,
                token=token,
                workspace_state=workspace_state,
            ),
        ) as tracker_page:
            page = LiveWorkspaceSwitcherPage(tracker_page)
            try:
                try:
                    runtime = tracker_page.open()
                except AssertionError as error:
                    visible_body_text = _visible_body_text_from_text(str(error))
                    result["runtime_state"] = "not-interactive"
                    result["runtime_body_text"] = visible_body_text
                    result["product_defect"] = True
                    _record_human_verification(
                        result,
                        check=(
                            "Opened the live URL in Chromium and observed the first rendered "
                            "screen exactly as a user would before opening the workspace switcher."
                        ),
                        observed=(
                            "After waiting for the initial page load, the app remained almost "
                            f"blank and exposed only {visible_body_text!r}; no workspace "
                            "switcher trigger, dashboard, or other interactive app-shell "
                            "controls became visible."
                        ),
                    )
                    raise
                result["runtime_state"] = runtime.kind
                result["runtime_body_text"] = runtime.body_text
                if runtime.kind != "ready":
                    result["product_defect"] = True
                    raise AssertionError(
                        "Step 1 failed: the deployed app did not reach an interactive "
                        "desktop state before the TS-1007 reverse-wrap scenario began.\n"
                        f"Observed runtime state: {runtime.kind}\n"
                        f"Observed body text:\n{runtime.body_text}",
                    )

                page.dismiss_connection_banner()
                page.navigate_to_section("Dashboard")
                page.set_viewport(**DESKTOP_VIEWPORT)

                current_step = 1
                current_action = AUTOMATION_STEPS[0]
                initial_state = _open_switcher_and_capture(page)
                result["initial_state"] = initial_state
                _assert_initial_state(initial_state)
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=AUTOMATION_STEPS[0],
                    observed=(
                        f"Opened {config.app_url} in Chromium at "
                        f"{DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}; "
                        f"first_internal_target={_first_internal_label(initial_state)!r}; "
                        f"footer_label={_button_state_from_state(initial_state).get('label')!r}; "
                        f"footer_disabled={_button_state_from_state(initial_state).get('disabled')}; "
                        f"footer_aria_disabled={_button_state_from_state(initial_state).get('aria_disabled')!r}."
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Opened the desktop workspace switcher in pristine state and visually "
                        "confirmed the footer still showed Save and switch before any edits."
                    ),
                    observed=(
                        f"visible_panel_labels={_interactive_label_summary(initial_state)!r}; "
                        f"footer_state={json.dumps(_button_state_from_state(initial_state), ensure_ascii=True)}"
                    ),
                )

                current_step = 2
                current_action = AUTOMATION_STEPS[1]
                first_keyboard_target_state = _reach_first_keyboard_target(
                    page=page,
                    state=initial_state,
                )
                result["first_keyboard_target_state"] = first_keyboard_target_state
                _record_human_verification(
                    result,
                    check=(
                        "Re-established focus on the first interactive control inside the open "
                        "panel immediately before the Shift+Tab action."
                    ),
                    observed=(
                        f"focused_before_shift_tab={_active_label_for_summary(first_keyboard_target_state)!r}; "
                        f"source={first_keyboard_target_state.get('precondition_source')!r}; "
                        f"expected_wrap_target={_expected_target_label(first_keyboard_target_state)!r}"
                    ),
                )
                after_shift_tab_state = _press_key_and_capture(
                    page=page,
                    state=first_keyboard_target_state,
                    key="Shift+Tab",
                    before_override=_focused_element_observation_from_state(
                        first_keyboard_target_state,
                    ),
                )
                result["after_shift_tab_state"] = after_shift_tab_state
                _record_human_verification(
                    result,
                    check=(
                        "Pressed Shift+Tab once like a real keyboard user and observed which "
                        "visible control actually received focus."
                    ),
                    observed=(
                        f"expected_wrap_target={_expected_target_label(after_shift_tab_state)!r}; "
                        f"actual_focus={_active_label_for_summary(after_shift_tab_state)!r}; "
                        f"focus_within_switcher={_focus_from_state(after_shift_tab_state).get('active_within_switcher')}; "
                        f"focus_on_trigger={_focus_from_state(after_shift_tab_state).get('active_on_trigger')}; "
                        f"footer_state={json.dumps(_button_state_from_state(after_shift_tab_state), ensure_ascii=True)}"
                    ),
                )
                _assert_reverse_wrap_to_disabled_footer(after_shift_tab_state)
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=AUTOMATION_STEPS[1],
                    observed=(
                        f"Shift+Tab started from {_before_label_for_summary(after_shift_tab_state)!r} "
                        f"and moved focus to {_active_label_for_summary(after_shift_tab_state)!r}; "
                        f"footer_disabled={_button_state_from_state(after_shift_tab_state).get('disabled')}; "
                        f"footer_aria_disabled={_button_state_from_state(after_shift_tab_state).get('aria_disabled')!r}; "
                        f"panel_hidden_during_key={_monitor_from_state(after_shift_tab_state).get('ever_hidden_after_visible')}."
                    ),
                )
            except AssertionError:
                result["product_defect"] = True
                _capture_failure_screenshot(page, result)
                raise
            except Exception:
                _capture_failure_screenshot(page, result)
                raise
            page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
            result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
    except AssertionError as error:
        _capture_failure_screenshot(page, result)
        if not _has_failed_step(result):
            _record_step(
                result,
                step=current_step,
                status="failed",
                action=current_action,
                observed=str(error),
            )
        result["error"] = str(error)
        result["traceback"] = traceback.format_exc()
        _write_failure_outputs(result)
        raise
    except Exception as error:
        _capture_failure_screenshot(page, result)
        if not _has_failed_step(result):
            _record_step(
                result,
                step=current_step,
                status="failed",
                action=current_action,
                observed=f"{type(error).__name__}: {error}",
            )
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        _write_failure_outputs(result)
        raise

    _write_pass_outputs(result)
    print(f"{TICKET_KEY} passed")


def _open_switcher_and_capture(page: LiveWorkspaceSwitcherPage) -> dict[str, object]:
    trigger = page.observe_trigger(timeout_ms=30_000)
    page.focus_workspace_trigger(timeout_ms=FOCUS_TIMEOUT_MS)
    before = page.active_element()
    page.press_enter_on_active_element_and_wait_for_surface(timeout_ms=FOCUS_TIMEOUT_MS)
    switcher = page.observe_open_switcher(timeout_ms=FOCUS_TIMEOUT_MS)
    panel = page.observe_open_panel(
        expected_container_kinds=("anchored-panel", "surface"),
        timeout_ms=FOCUS_TIMEOUT_MS,
    )
    surface = page.observe_surface(timeout_ms=FOCUS_TIMEOUT_MS)
    rows = page.observe_saved_workspace_rows(timeout_ms=FOCUS_TIMEOUT_MS)
    active = page.active_element()
    focus = page.observe_focus_ownership(panel=panel)
    internal_tab_stops = page.observe_internal_tab_stops(
        panel=panel,
        timeout_ms=FOCUS_TIMEOUT_MS,
    )
    save_button_state = page.observe_switcher_button_state(
        LAST_INTERNAL_CONTROL_LABEL,
        timeout_ms=FOCUS_TIMEOUT_MS,
    )
    first_row = _selected_saved_workspace(rows)
    if first_row is None:
        raise AssertionError(
            "Step 1 failed: the open workspace switcher did not expose a selected saved "
            "workspace row in pristine state.\n"
            f"Observed rows: {json.dumps(_saved_workspace_rows_payload(rows), indent=2)}",
        )
    first_row_label = _saved_workspace_row_focus_label(first_row)
    row_focus = {
        name: _row_focus_payload(
            page.observe_saved_workspace_row_focus(display_name=name, panel=panel),
        )
        for name in WORKSPACE_NAMES
    }
    return {
        "before": _focused_element_payload(before),
        "trigger": _trigger_payload(trigger),
        "switcher": _switcher_payload(switcher),
        "panel": asdict(panel),
        "surface": _surface_payload(surface),
        "saved_workspace_rows": _saved_workspace_rows_payload(rows),
        "active": _focused_element_payload(active),
        "focus": _focus_ownership_payload(focus),
        "row_focus": row_focus,
        "internal_tab_stops": _tab_stops_payload(internal_tab_stops),
        "first_row_display_name": first_row.display_name,
        "first_row_label": first_row_label,
        "first_internal_target": _resolve_first_internal_focus_target(
            active=active,
            focus=focus,
            first_row_label=first_row_label,
            tab_stops=internal_tab_stops,
        ),
        "expected_target": _expected_footer_target(save_button_state),
        "button_state": _button_state_payload(save_button_state),
        "precondition_source": None,
        "monitor": {},
    }


def _reach_first_keyboard_target(
    *,
    page: LiveWorkspaceSwitcherPage,
    state: dict[str, object],
) -> dict[str, object]:
    current_state = _capture_current_state(page=page, state=state)
    if _is_switcher_internal_focus_state(current_state) and (
        _active_label_for_summary(current_state) == _first_internal_label(current_state)
    ):
        current_state["precondition_source"] = "initial-focus"
        _assert_first_keyboard_target(current_state)
        return current_state

    first_internal_label = _first_internal_label(current_state)
    if not first_internal_label:
        raise AssertionError(
            "Step 2 failed: the open workspace switcher did not expose a readable first "
            "internal keyboard target before the Shift+Tab check.\n"
            f"Observed active element: {json.dumps(_active_from_state(current_state), indent=2)}\n"
            f"Observed focus ownership: {json.dumps(_focus_from_state(current_state), indent=2)}\n"
            f"Observed internal tab stops: {json.dumps(_tab_stops_from_state(current_state), indent=2)}",
        )

    panel = WorkspaceSwitcherPanelObservation(**_panel_from_state(current_state))
    before = page.active_element()
    try:
        page.focus_internal_tab_stop(
            str(first_internal_label),
            panel=panel,
            timeout_ms=FOCUS_TIMEOUT_MS,
        )
    except AssertionError as error:
        failed_state = _capture_current_state(
            page=page,
            state=current_state,
            before=before,
        )
        raise AssertionError(
            "Step 2 failed: focusing the first internal keyboard target did not "
            "establish the TS-1007 precondition before Shift+Tab.\n"
            f"Focus target error: {error}\n"
            f"Observed before element: {json.dumps(_before_from_state(failed_state), indent=2)}\n"
            f"Observed active element: {json.dumps(_active_from_state(failed_state), indent=2)}\n"
            f"Observed focus ownership: {json.dumps(_focus_from_state(failed_state), indent=2)}\n"
            f"Observed internal target: {json.dumps(_first_internal_target_from_state(failed_state), indent=2)}\n"
            f"Observed internal tab stops: {json.dumps(_tab_stops_from_state(failed_state), indent=2)}",
        ) from error
    reached_state = _capture_current_state(
        page=page,
        state=current_state,
        before=before,
    )
    reached_state["precondition_source"] = "page-object-focus"
    _assert_first_keyboard_target(reached_state)
    return reached_state


def _capture_current_state(
    *,
    page: LiveWorkspaceSwitcherPage,
    state: dict[str, object],
    before: FocusedElementObservation | None = None,
    monitor: WorkspaceSwitcherTransitionMonitorObservation | None = None,
    surface_stability_error: str | None = None,
) -> dict[str, object]:
    panel_payload = _panel_from_state(state)
    current_panel = WorkspaceSwitcherPanelObservation(**panel_payload)
    panel_error: str | None = None
    try:
        current_panel = page.observe_open_panel(
            expected_container_kinds=("anchored-panel", "surface"),
            timeout_ms=1_000,
        )
    except Exception as error:
        panel_error = f"{type(error).__name__}: {error}"
    active = page.active_element()
    focus = page.observe_focus_ownership(panel=current_panel)

    row_focus = {
        name: _row_focus_payload(
            page.observe_saved_workspace_row_focus(display_name=name, panel=current_panel),
        )
        for name in WORKSPACE_NAMES
    }

    switcher: WorkspaceSwitcherObservation | None = None
    switcher_error: str | None = None
    try:
        switcher = page.observe_open_switcher(timeout_ms=1_000)
    except Exception as error:
        switcher_error = f"{type(error).__name__}: {error}"

    rows: tuple[WorkspaceSwitcherSavedWorkspaceRowObservation, ...] = ()
    rows_error: str | None = None
    try:
        rows = page.observe_saved_workspace_rows(timeout_ms=1_000)
    except Exception as error:
        rows_error = f"{type(error).__name__}: {error}"

    surface: WorkspaceSwitcherSurfaceObservation | None = None
    surface_error: str | None = None
    try:
        surface = page.observe_surface(timeout_ms=1_000)
    except Exception as error:
        surface_error = f"{type(error).__name__}: {error}"

    internal_tab_stops = state.get("internal_tab_stops")
    internal_tab_stops_error: str | None = None
    try:
        internal_tab_stops = _tab_stops_payload(
            page.observe_internal_tab_stops(panel=current_panel, timeout_ms=1_000),
        )
    except Exception as error:
        internal_tab_stops_error = f"{type(error).__name__}: {error}"

    button_state = state.get("button_state")
    button_state_error: str | None = None
    try:
        button_state = _button_state_payload(
            page.observe_switcher_button_state(
                LAST_INTERNAL_CONTROL_LABEL,
                timeout_ms=1_000,
            ),
        )
    except Exception as error:
        button_state_error = f"{type(error).__name__}: {error}"

    payload: dict[str, object] = {
        "panel": asdict(current_panel),
        "active": _focused_element_payload(active),
        "focus": _focus_ownership_payload(focus),
        "row_focus": row_focus,
        "saved_workspace_rows": _saved_workspace_rows_payload(rows),
        "expected_target": state.get("expected_target"),
        "first_internal_target": state.get("first_internal_target"),
        "first_row_display_name": state.get("first_row_display_name"),
        "first_row_label": state.get("first_row_label"),
        "internal_tab_stops": internal_tab_stops if isinstance(internal_tab_stops, list) else [],
        "button_state": button_state if isinstance(button_state, dict) else {},
        "precondition_source": state.get("precondition_source"),
        "monitor": _transition_monitor_payload(monitor) if monitor is not None else {},
    }
    if before is not None:
        payload["before"] = _focused_element_payload(before)
    elif isinstance(state.get("before"), dict):
        payload["before"] = state["before"]
    if switcher is not None:
        payload["switcher"] = _switcher_payload(switcher)
    if switcher_error is not None:
        payload["switcher_error"] = switcher_error
    if panel_error is not None:
        payload["panel_error"] = panel_error
    if surface is not None:
        payload["surface"] = _surface_payload(surface)
    if surface_error is not None:
        payload["surface_error"] = surface_error
    if surface_stability_error is not None:
        payload["surface_stability_error"] = surface_stability_error
    if rows_error is not None:
        payload["rows_error"] = rows_error
    if internal_tab_stops_error is not None:
        payload["internal_tab_stops_error"] = internal_tab_stops_error
    if button_state_error is not None:
        payload["button_state_error"] = button_state_error
    return payload


def _press_key_and_capture(
    *,
    page: LiveWorkspaceSwitcherPage,
    state: dict[str, object],
    key: str,
    before_override: FocusedElementObservation | None = None,
) -> dict[str, object]:
    before = before_override or page.active_element()
    page.start_transition_monitor()
    page.press_key(key, timeout_ms=FOCUS_TIMEOUT_MS)
    surface_stability_error: str | None = None
    try:
        page.wait_for_surface_to_remain_open(
            stability_ms=FOCUS_SETTLE_MS,
            timeout_ms=FOCUS_TIMEOUT_MS,
        )
    except Exception as error:
        surface_stability_error = f"{type(error).__name__}: {error}"
    monitor = page.read_transition_monitor(clear=True)
    payload = _capture_current_state(
        page=page,
        state=state,
        before=before,
        monitor=monitor,
        surface_stability_error=surface_stability_error,
    )
    payload["key"] = key
    return payload


def _assert_initial_state(state: dict[str, object]) -> None:
    switcher = _switcher_from_state(state)
    surface_labels = _interactive_label_summary(state)
    button_state = _button_state_from_state(state)
    failures: list[str] = []

    if FIRST_WORKSPACE_DISPLAY_NAME not in str(state.get("first_row_display_name")):
        failures.append(
            f"the selected saved workspace row was {state.get('first_row_display_name')!r} "
            f"instead of {FIRST_WORKSPACE_DISPLAY_NAME!r}",
        )
    if "Workspace switcher" not in str(switcher.get("switcher_text", "")):
        failures.append("the workspace switcher panel text was not visible")
    if _expected_target_label(state) != LAST_INTERNAL_CONTROL_LABEL:
        failures.append(
            f"the reverse-wrap boundary was {_expected_target_label(state)!r} instead of "
            f"{LAST_INTERNAL_CONTROL_LABEL!r}",
        )
    for label in ("Repository", "Branch", LAST_INTERNAL_CONTROL_LABEL):
        if label not in surface_labels:
            failures.append(f"the visible panel did not expose the expected {label!r} control")
    if not _button_represents_save_and_switch(button_state):
        failures.append(
            "the visible footer button state could not be read as the Save and switch control",
        )
    if not _button_reports_disabled(button_state):
        failures.append(
            "the visible Save and switch footer control was not marked disabled in pristine state",
        )
    if failures:
        raise AssertionError(
            "Step 1 failed: the open workspace switcher did not satisfy the TS-1007 "
            "preconditions before the reverse-wrap assertion.\n"
            + "\n".join(f"- {item}" for item in failures)
            + "\n"
            + f"Observed switcher: {json.dumps(switcher, indent=2)}\n"
            + f"Observed rows: {json.dumps(_saved_workspace_rows_from_state(state), indent=2)}\n"
            + f"Observed surface labels: {json.dumps(surface_labels, indent=2)}\n"
            + f"Observed footer state: {json.dumps(button_state, indent=2)}"
        )


def _assert_first_keyboard_target(state: dict[str, object]) -> None:
    active = _active_from_state(state)
    focus = _focus_from_state(state)
    first_internal_label = _first_internal_label(state)
    failures: list[str] = []

    if not bool(focus.get("focus_owned_by_switcher")):
        failures.append("keyboard focus was not owned by the workspace switcher before Shift+Tab")
    if not bool(focus.get("active_within_switcher")):
        failures.append("focus escaped the workspace switcher before Shift+Tab")
    if active.get("accessible_name") != first_internal_label:
        failures.append(
            f"focus landed on {active.get('accessible_name')!r} instead of the first internal "
            f"target {first_internal_label!r}",
        )
    if str(active.get("accessible_name") or "").startswith("Workspace switcher:"):
        failures.append(
            "focus stayed on the workspace-switcher trigger instead of the first internal target",
        )
    if failures:
        raise AssertionError(
            "Step 2 failed: focusing the first internal keyboard target did not establish "
            "the ticket precondition before Shift+Tab.\n"
            + "\n".join(f"- {item}" for item in failures)
            + "\n"
            + f"Observed before element: {json.dumps(_before_from_state(state), indent=2)}\n"
            + f"Observed active element: {json.dumps(active, indent=2)}\n"
            + f"Observed focus ownership: {json.dumps(focus, indent=2)}\n"
            + f"Observed internal target: {json.dumps(_first_internal_target_from_state(state), indent=2)}\n"
            + f"Observed internal tab stops: {json.dumps(_tab_stops_from_state(state), indent=2)}"
        )


def _assert_reverse_wrap_to_disabled_footer(state: dict[str, object]) -> None:
    active = _active_from_state(state)
    focus = _focus_from_state(state)
    button_state = _button_state_from_state(state)
    expected_target = _expected_target_from_state(state)
    row_focus = {name: _row_focus_from_state(state, name) for name in WORKSPACE_NAMES}
    monitor = _monitor_from_state(state)
    active_label = str(active.get("accessible_name") or "")
    failures: list[str] = []

    if _before_label_for_summary(state) != _first_internal_label(state):
        failures.append(
            f"Shift+Tab started from {_before_label_for_summary(state)!r} instead of the proven "
            f"first internal target {_first_internal_label(state)!r}",
        )
    if not bool(focus.get("focus_owned_by_switcher")):
        failures.append("keyboard focus was not owned by the workspace switcher after Shift+Tab")
    if not bool(focus.get("active_within_switcher")):
        failures.append("focus escaped the workspace switcher after Shift+Tab")
    if bool(focus.get("active_on_trigger")) or active_label.startswith("Workspace switcher:"):
        failures.append(
            "focus moved to the workspace-switcher trigger instead of wrapping to the footer boundary",
        )
    if bool(monitor.get("ever_hidden_after_visible")):
        failures.append("the workspace switcher panel became hidden during the Shift+Tab action")
    if active_label != LAST_INTERNAL_CONTROL_LABEL:
        failures.append(
            f"focus landed on {active_label!r} instead of {LAST_INTERNAL_CONTROL_LABEL!r}",
        )
    if expected_target.get("label") != LAST_INTERNAL_CONTROL_LABEL:
        failures.append(
            f"the expected reverse-wrap target was {expected_target.get('label')!r} instead of "
            f"{LAST_INTERNAL_CONTROL_LABEL!r}",
        )
    if not _button_represents_save_and_switch(button_state):
        failures.append("the focused footer control did not resolve to Save and switch")
    if not bool(button_state.get("active_within")):
        failures.append("the Save and switch footer button did not report active focus after Shift+Tab")
    if not _button_reports_disabled(button_state):
        failures.append(
            "the Save and switch footer button stopped reporting a disabled state when it received focus",
        )
    if failures:
        raise AssertionError(
            "Step 2 failed: pressing Shift+Tab from the first internal workspace-switcher "
            "target did not wrap focus to the disabled Save and switch footer boundary.\n"
            + "\n".join(f"- {item}" for item in failures)
            + "\n"
            + f"Observed before element: {json.dumps(_before_from_state(state), indent=2)}\n"
            + f"Observed active element: {json.dumps(active, indent=2)}\n"
            + f"Observed focus ownership: {json.dumps(focus, indent=2)}\n"
            + f"Observed footer state: {json.dumps(button_state, indent=2)}\n"
            + f"Expected wrap target: {json.dumps(expected_target, indent=2)}\n"
            + f"Observed row focus: {json.dumps(row_focus, indent=2)}\n"
            + f"Observed transition monitor: {json.dumps(monitor, indent=2)}\n"
            + f"Observed switcher: {json.dumps(_switcher_from_state(state), indent=2)}"
        )


def _resolve_first_internal_focus_target(
    *,
    active: FocusedElementObservation,
    focus: WorkspaceSwitcherFocusOwnershipObservation,
    first_row_label: str,
    tab_stops: tuple[WorkspaceSwitcherTabStopObservation, ...] | list[object],
) -> dict[str, object]:
    active_label = str(active.accessible_name or active.text or "")
    if (
        active_label
        and active_label == first_row_label
        and bool(focus.focus_owned_by_switcher)
        and bool(focus.active_within_switcher)
        and not bool(focus.active_on_trigger)
    ):
        return {
            "label": active_label,
            "visible_text": str(active.text or ""),
            "role": active.role,
            "tag_name": active.tag_name,
            "tabindex": active.tabindex,
            "tab_index_value": None,
            "dom_index": None,
            "keyboard_focusable": True,
            "disabled": False,
            "outer_html": active.outer_html,
        }
    payload = _tab_stops_payload(tab_stops)
    if not payload:
        raise AssertionError(
            "Step 1 failed: the open workspace switcher did not expose a readable first "
            "internal keyboard target.\n"
            f"Observed internal tab stops: {json.dumps(payload, indent=2)}",
        )
    return payload[0]


def _expected_footer_target(
    observation: WorkspaceSwitcherButtonStateObservation,
) -> dict[str, object]:
    payload = _button_state_payload(observation)
    return {
        "label": payload.get("label") or payload.get("visible_text") or "",
        "visible_text": payload.get("visible_text"),
        "role": payload.get("role"),
        "tag_name": payload.get("tag_name"),
        "tabindex": payload.get("tabindex"),
        "tab_index_value": payload.get("tab_index_value"),
        "dom_index": None,
        "keyboard_focusable": payload.get("keyboard_focusable"),
        "disabled": payload.get("disabled"),
        "outer_html": payload.get("outer_html"),
    }


def _is_switcher_internal_focus_state(state: dict[str, object]) -> bool:
    focus = _focus_from_state(state)
    active = _active_from_state(state)
    active_label = str(active.get("accessible_name") or active.get("text") or "")
    return (
        bool(focus.get("focus_owned_by_switcher"))
        and bool(focus.get("active_within_switcher"))
        and not bool(focus.get("active_on_trigger"))
        and not active_label.startswith("Workspace switcher:")
        and bool(active.get("accessible_name") or active.get("text"))
    )


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
                "lastOpenedAt": "2026-05-23T14:00:00.000Z",
            },
            {
                "id": second_id,
                "displayName": SECOND_WORKSPACE_DISPLAY_NAME,
                "customDisplayName": SECOND_WORKSPACE_DISPLAY_NAME,
                "targetType": "hosted",
                "target": repository,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": SECOND_WORKSPACE_WRITE_BRANCH,
                "lastOpenedAt": "2026-05-23T13:50:00.000Z",
            },
            {
                "id": third_id,
                "displayName": THIRD_WORKSPACE_DISPLAY_NAME,
                "customDisplayName": THIRD_WORKSPACE_DISPLAY_NAME,
                "targetType": "hosted",
                "target": repository,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": THIRD_WORKSPACE_WRITE_BRANCH,
                "lastOpenedAt": "2026-05-23T13:40:00.000Z",
            },
        ],
    }


def _selected_saved_workspace(
    rows: tuple[WorkspaceSwitcherSavedWorkspaceRowObservation, ...],
) -> WorkspaceSwitcherSavedWorkspaceRowObservation | None:
    return next((row for row in rows if row.selected), None)


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
    observations: tuple[WorkspaceSwitcherTabStopObservation, ...] | list[object],
) -> list[dict[str, object]]:
    payload: list[dict[str, object]] = []
    for observation in observations:
        if not isinstance(observation, WorkspaceSwitcherTabStopObservation):
            continue
        payload.append(
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
                "outer_html": observation.outer_html,
            },
        )
    return payload


def _transition_monitor_payload(
    observation: WorkspaceSwitcherTransitionMonitorObservation | None,
) -> dict[str, object]:
    if observation is None:
        return {}
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


def _focused_element_payload(observation: FocusedElementObservation) -> dict[str, object]:
    return {
        "accessible_name": observation.accessible_name,
        "role": observation.role,
        "tag_name": observation.tag_name,
        "text": observation.text,
        "tabindex": observation.tabindex,
        "outer_html": observation.outer_html,
    }


def _focused_element_observation_from_state(
    state: dict[str, object],
) -> FocusedElementObservation:
    active = _active_from_state(state)
    return FocusedElementObservation(
        accessible_name=(
            str(active.get("accessible_name"))
            if active.get("accessible_name") is not None
            else None
        ),
        role=str(active.get("role")) if active.get("role") is not None else None,
        tag_name=str(active.get("tag_name", "")),
        text=str(active.get("text", "")),
        tabindex=str(active.get("tabindex")) if active.get("tabindex") is not None else None,
        outer_html=str(active.get("outer_html", "")),
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
        raise TypeError("result['steps'] must be a list")
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
        raise TypeError("result['human_verification'] must be a list")
    items.append({"check": check, "observed": observed})


def _steps(result: dict[str, object]) -> list[dict[str, object]]:
    steps = result.get("steps")
    return steps if isinstance(steps, list) else []


def _has_failed_step(result: dict[str, object]) -> bool:
    return any(step.get("status") == "failed" for step in _steps(result))


def _step_status(result: dict[str, object], step_number: int) -> str:
    for step in _steps(result):
        if int(step.get("step", -1)) == step_number:
            return str(step.get("status", "not-run"))
    return "not-run"


def _step_observation(result: dict[str, object], step_number: int) -> str:
    for step in _steps(result):
        if int(step.get("step", -1)) == step_number:
            return str(step.get("observed", ""))
    return "Not reached."


def _step_passed(result: dict[str, object], step_number: int) -> bool:
    return _step_status(result, step_number) == "passed"


def _human_verification(result: dict[str, object]) -> list[dict[str, object]]:
    items = result.get("human_verification")
    return items if isinstance(items, list) else []


def _failed_step(result: dict[str, object]) -> dict[str, object] | None:
    return next((step for step in _steps(result) if step.get("status") == "failed"), None)


def _failed_step_label(result: dict[str, object]) -> str:
    failed = _failed_step(result)
    if failed is None:
        return "No failed automation step recorded"
    return f"Step {failed['step']} - {failed['action']}"


def _failed_step_summary(result: dict[str, object]) -> str:
    failed = _failed_step(result)
    if failed is None:
        return f"{TICKET_KEY} failed."
    return str(failed.get("observed", f"{TICKET_KEY} failed."))


def _surface_labels(surface: dict[str, object]) -> set[str]:
    elements = surface.get("interactive_elements")
    if not isinstance(elements, list):
        return set()
    return {
        str(item.get("label"))
        for item in elements
        if isinstance(item, dict) and str(item.get("label") or "")
    }


def _interactive_label_summary(state: object) -> list[str]:
    surface = _surface_from_state(state)
    return sorted(_surface_labels(surface))


def _saved_workspace_rows_from_state(state: object) -> list[dict[str, object]]:
    if not isinstance(state, dict):
        return []
    rows = state.get("saved_workspace_rows")
    return rows if isinstance(rows, list) else []


def _switcher_from_state(state: object) -> dict[str, object]:
    if not isinstance(state, dict):
        return {}
    switcher = state.get("switcher")
    return switcher if isinstance(switcher, dict) else {}


def _surface_from_state(state: object) -> dict[str, object]:
    if not isinstance(state, dict):
        return {}
    surface = state.get("surface")
    return surface if isinstance(surface, dict) else {}


def _panel_from_state(state: object) -> dict[str, object]:
    if not isinstance(state, dict):
        return {}
    panel = state.get("panel")
    return panel if isinstance(panel, dict) else {}


def _active_from_state(state: object) -> dict[str, object]:
    if not isinstance(state, dict):
        return {}
    active = state.get("active")
    return active if isinstance(active, dict) else {}


def _before_from_state(state: object) -> dict[str, object]:
    if not isinstance(state, dict):
        return {}
    before = state.get("before")
    return before if isinstance(before, dict) else {}


def _focus_from_state(state: object) -> dict[str, object]:
    if not isinstance(state, dict):
        return {}
    focus = state.get("focus")
    return focus if isinstance(focus, dict) else {}


def _row_focus_from_state(state: object, display_name: str) -> dict[str, object]:
    if not isinstance(state, dict):
        return {}
    row_focus = state.get("row_focus")
    if not isinstance(row_focus, dict):
        return {}
    target = row_focus.get(display_name)
    return target if isinstance(target, dict) else {}


def _expected_target_from_state(state: object) -> dict[str, object]:
    if not isinstance(state, dict):
        return {}
    target = state.get("expected_target")
    return target if isinstance(target, dict) else {}


def _first_internal_target_from_state(state: object) -> dict[str, object]:
    if not isinstance(state, dict):
        return {}
    target = state.get("first_internal_target")
    return target if isinstance(target, dict) else {}


def _button_state_from_state(state: object) -> dict[str, object]:
    if not isinstance(state, dict):
        return {}
    button = state.get("button_state")
    return button if isinstance(button, dict) else {}


def _tab_stops_from_state(state: object) -> list[dict[str, object]]:
    if not isinstance(state, dict):
        return []
    stops = state.get("internal_tab_stops")
    return stops if isinstance(stops, list) else []


def _monitor_from_state(state: object) -> dict[str, object]:
    if not isinstance(state, dict):
        return {}
    monitor = state.get("monitor")
    return monitor if isinstance(monitor, dict) else {}


def _active_label_for_summary(state: object) -> object:
    return _active_from_state(state).get("accessible_name")


def _before_label_for_summary(state: object) -> object:
    return _before_from_state(state).get("accessible_name")


def _first_internal_label(state: object) -> object:
    return _first_internal_target_from_state(state).get("label")


def _expected_target_label(state: object) -> object:
    return _expected_target_from_state(state).get("label")


def _button_represents_save_and_switch(button_state: dict[str, object]) -> bool:
    label = str(button_state.get("label") or "")
    visible_text = str(button_state.get("visible_text") or "")
    return label == LAST_INTERNAL_CONTROL_LABEL or visible_text == LAST_INTERNAL_CONTROL_LABEL


def _button_reports_disabled(button_state: dict[str, object]) -> bool:
    return button_state.get("aria_disabled") == "true" or bool(button_state.get("disabled"))


def _capture_failure_screenshot(
    page: LiveWorkspaceSwitcherPage | None,
    result: dict[str, object],
) -> None:
    if page is None or result.get("screenshot"):
        return
    try:
        page.screenshot(str(FAILURE_SCREENSHOT_PATH))
        result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
    except Exception as screenshot_error:
        result["screenshot_error"] = (
            f"{type(screenshot_error).__name__}: {screenshot_error}"
        )


def _write_pass_outputs(result: dict[str, object]) -> None:
    JIRA_COMMENT_PATH.write_text(_jira_comment(result, passed=True), encoding="utf-8")
    PR_BODY_PATH.write_text(_markdown_summary(result, passed=True), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_summary(result, passed=True), encoding="utf-8")
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
    BUG_DESCRIPTION_PATH.unlink(missing_ok=True)


def _write_failure_outputs(result: dict[str, object]) -> None:
    JIRA_COMMENT_PATH.write_text(_jira_comment(result, passed=False), encoding="utf-8")
    PR_BODY_PATH.write_text(_markdown_summary(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_summary(result, passed=False), encoding="utf-8")
    error_text = str(result.get("error", "AssertionError"))
    RESULT_PATH.write_text(
        json.dumps(
            {
                "status": "failed",
                "passed": 0,
                "failed": 1,
                "skipped": 0,
                "summary": "0 passed, 1 failed",
                "error": error_text,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    if bool(result.get("product_defect")):
        BUG_DESCRIPTION_PATH.write_text(_bug_description(result), encoding="utf-8")
    else:
        BUG_DESCRIPTION_PATH.unlink(missing_ok=True)


def _jira_comment(result: dict[str, object], *, passed: bool) -> str:
    status = "PASSED" if passed else "FAILED"
    lines = [
        "h3. Test Automation Result",
        "",
        f"*Status:* {status}",
        f"*Test Case:* {TICKET_KEY} - {TEST_CASE_TITLE}",
        (
            f"*Environment:* URL {{{{{result['app_url']}}}}}, repository "
            f"{{{{{result['repository']}}}}} @ {{{{{result['repository_ref']}}}}}, "
            f"browser {{Chromium (Playwright)}}, OS {{{{{result['os']}}}}}, "
            f"viewport {{{{{DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}}}}}"
        ),
        f"*Run command:* {{code}}{RUN_COMMAND}{{code}}",
        "",
        "h4. What automation checked",
        f"# {AUTOMATION_STEPS[0]} - *{_step_status(result, 1).upper()}*: {_step_observation(result, 1)}",
        f"# {AUTOMATION_STEPS[1]} - *{_step_status(result, 2).upper()}*: {_step_observation(result, 2)}",
        "",
        "h4. Human-style verification",
        *[
            f"# {item['check']} - {item['observed']}"
            for item in _human_verification(result)
        ],
        "",
        "h4. Expected result",
        EXPECTED_RESULT,
        "",
        "h4. Observed outcome",
        _actual_vs_expected_summary(result),
    ]
    if not passed:
        lines.extend(
            [
                "",
                "h4. Failure details",
                f"*Failed step:* {_failed_step_label(result)}",
                f"*Error:* {{code}}{result.get('error')}{{code}}",
                "",
                "h4. Exact error",
                "{code}",
                str(result.get("traceback", result.get("error", ""))),
                "{code}",
            ],
        )
    screenshot = result.get("screenshot")
    if screenshot:
        lines.extend(["", f"*Screenshot:* {{{{{screenshot}}}}}"])
    return "\n".join(lines) + "\n"


def _markdown_summary(result: dict[str, object], *, passed: bool) -> str:
    status = "PASSED" if passed else "FAILED"
    lines = [
        f"# {TICKET_KEY} - {status}",
        "",
        f"**Test case:** {TEST_CASE_TITLE}",
        f"**Result:** {status}",
        (
            f"**Environment:** `{result['app_url']}` · `{result['repository']}` @ "
            f"`{result['repository_ref']}` · `Chromium (Playwright)` · `{result['os']}` · "
            f"`{DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}`"
        ),
        f"**Run command:** `{RUN_COMMAND}`",
        "",
        "## What automation checked",
        f"1. {AUTOMATION_STEPS[0]} - **{_step_status(result, 1).upper()}**: {_step_observation(result, 1)}",
        f"2. {AUTOMATION_STEPS[1]} - **{_step_status(result, 2).upper()}**: {_step_observation(result, 2)}",
        "",
        "## Human-style verification",
        *[
            f"1. {item['check']} - {item['observed']}"
            for item in _human_verification(result)
        ],
        "",
        "## Expected result",
        EXPECTED_RESULT,
        "",
        "## Observed outcome",
        _actual_vs_expected_summary(result),
    ]
    if not passed:
        lines.extend(
            [
                "",
                "## Failure details",
                f"- **Failed step:** {_failed_step_label(result)}",
                f"- **Error:** `{result.get('error')}`",
                (
                    f"- **Screenshot:** `{result.get('screenshot')}`"
                    if result.get("screenshot")
                    else "- **Screenshot:** not captured"
                ),
                "",
                "## Exact error",
                "```text",
                str(result.get("traceback", result.get("error", ""))),
                "```",
            ],
        )
    elif result.get("screenshot"):
        lines.extend(["", f"**Screenshot:** `{result['screenshot']}`"])
    return "\n".join(lines) + "\n"


def _response_summary(result: dict[str, object], *, passed: bool) -> str:
    status = "PASSED" if passed else "FAILED"
    lines = [
        "# Test Automation Summary",
        "",
        f"- Test case: **{TICKET_KEY} - {TEST_CASE_TITLE}**",
        f"- Result: **{status}**",
        f"- Command: `{RUN_COMMAND}`",
        (
            f"- Environment: `{result['app_url']}` on Chromium/Playwright "
            f"({result['os']}) against `{result['repository']}` @ "
            f"`{result['repository_ref']}` with viewport "
            f"`{DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}`."
        ),
        f"- Expected result: {EXPECTED_RESULT}",
        f"- Observed outcome: {_actual_vs_expected_summary(result)}",
    ]
    if result.get("screenshot"):
        lines.append(f"- Screenshot: `{result['screenshot']}`")
    return "\n".join(lines) + "\n"


def _visible_body_text_from_text(text: str) -> str:
    marker = "Visible body text:"
    if marker in text:
        return text.split(marker, 1)[1].strip()
    return "<unknown>"


def _actual_vs_expected_summary(result: dict[str, object]) -> str:
    runtime_state = str(result.get("runtime_state") or "")
    if runtime_state == "not-interactive":
        visible_body_text = str(result.get("runtime_body_text") or "<unknown>")
        return (
            "The deployed app never rendered an interactive TrackState shell. Chromium "
            f"showed {visible_body_text!r} on an otherwise blank page, so the workspace "
            "switcher could not be opened and the Shift+Tab scenario never became reachable."
        )
    after_state = result.get("after_shift_tab_state")
    if not isinstance(after_state, dict):
        return _failed_step_summary(result)
    expected = _expected_target_label(after_state)
    actual = _active_label_for_summary(after_state)
    button_state = _button_state_from_state(after_state)
    focus = _focus_from_state(after_state)
    if _step_passed(result, 2):
        return (
            f"Shift+Tab wrapped focus from the first internal panel target to {expected!r}, "
            "the workspace switcher stayed open, and the focused footer control still "
            f"reported disabled={button_state.get('disabled')} and "
            f"aria-disabled={button_state.get('aria_disabled')!r}."
        )
    return (
        f"Shift+Tab should have wrapped focus to the disabled footer control {expected!r}, "
        f"but the live app moved focus to {actual!r}. "
        f"focus_within_switcher={focus.get('active_within_switcher')}, "
        f"focus_on_trigger={focus.get('active_on_trigger')}, "
        f"footer_state={json.dumps(button_state, ensure_ascii=True)}."
    )


def _bug_description(result: dict[str, object]) -> str:
    runtime_state = str(result.get("runtime_state") or "")
    if runtime_state == "not-interactive":
        visible_body_text = str(result.get("runtime_body_text") or "<unknown>")
        return "\n".join(
            [
                f"# {TICKET_KEY} - Deployed TrackState app never reaches an interactive state",
                "",
                "## Summary",
                _actual_vs_expected_summary(result),
                "",
                "## Exact steps to reproduce",
                "1. Open the TrackState application in a desktop browser at `https://istin.github.io/trackstate-setup/`.",
                "2. Wait for the initial TrackState UI to finish loading.",
                "3. Look for the top-bar workspace switcher trigger and the rest of the interactive app shell.",
                "4. Attempt to open the workspace switcher panel.",
                "5. Observe the rendered page state.",
                "",
                "## Exact steps from the test case with observations",
                _annotated_request_steps(result),
                "",
                "## Exact error message or assertion failure",
                "```text",
                str(result.get("traceback", result.get("error", ""))),
                "```",
                "",
                "## Actual vs Expected",
                f"- **Expected:** {EXPECTED_RESULT}",
                (
                    "- **Actual:** The deployed app never rendered the interactive "
                    f"workspace-switcher flow. Chromium showed {visible_body_text!r} on "
                    "an otherwise blank page, so the workspace switcher trigger and "
                    "panel never became available."
                ),
                "",
                "## Environment details",
                f"- URL: `{result.get('app_url')}`",
                f"- Repository: `{result.get('repository')}` @ `{result.get('repository_ref')}`",
                f"- Browser: `{result.get('browser')}`",
                f"- OS: `{result.get('os')}`",
                f"- Viewport: `{DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}`",
                f"- Run command: `{RUN_COMMAND}`",
                "",
                "## Screenshots or logs",
                f"- Screenshot: `{result.get('screenshot', 'not captured')}`",
                f"- Visible body text: `{visible_body_text}`",
                "- Step log:",
                "```json",
                json.dumps(
                    {
                        "steps": _steps(result),
                        "runtime_state": result.get("runtime_state"),
                        "runtime_body_text": result.get("runtime_body_text"),
                    },
                    indent=2,
                ),
                "```",
            ],
        ) + "\n"

    return "\n".join(
        [
            f"# {TICKET_KEY} - Shift+Tab does not wrap to the disabled Save and switch footer boundary",
            "",
            "## Summary",
            _actual_vs_expected_summary(result),
            "",
            "## Exact steps to reproduce",
            "1. Open the TrackState application in a desktop browser.",
            "2. Open the workspace switcher panel from Dashboard.",
            "3. Leave the workspace switcher in pristine state without changing repository or branch values.",
            "4. Ensure keyboard focus is on the first interactive element inside the panel.",
            "5. Press `Shift+Tab` once.",
            "6. Observe which control receives focus and whether the panel stays open.",
            "",
            "## Exact steps from the test case with observations",
            _annotated_request_steps(result),
            "",
            "## Exact error message or assertion failure",
            "```text",
            str(result.get("traceback", result.get("error", ""))),
            "```",
            "",
            "## Actual vs Expected",
            f"- **Expected:** {EXPECTED_RESULT}",
            f"- **Actual:** {_actual_vs_expected_summary(result)}",
            "",
            "## Environment details",
            f"- URL: `{result.get('app_url')}`",
            f"- Repository: `{result.get('repository')}` @ `{result.get('repository_ref')}`",
            f"- Browser: `{result.get('browser')}`",
            f"- OS: `{result.get('os')}`",
            f"- Viewport: `{DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}`",
            f"- Run command: `{RUN_COMMAND}`",
            "",
            "## Screenshots or logs",
            f"- Screenshot: `{result.get('screenshot', 'not captured')}`",
            "- Step log:",
            "```json",
            json.dumps(
                {
                    "steps": _steps(result),
                    "initial_state": result.get("initial_state"),
                    "first_keyboard_target_state": result.get("first_keyboard_target_state"),
                    "after_shift_tab_state": result.get("after_shift_tab_state"),
                },
                indent=2,
            ),
            "```",
        ],
    ) + "\n"


def _annotated_request_steps(result: dict[str, object]) -> str:
    runtime_state = str(result.get("runtime_state") or "")
    if runtime_state == "not-interactive":
        visible_body_text = str(result.get("runtime_body_text") or "<unknown>")
        return "\n".join(
            [
                (
                    "1. The TrackState application is opened.\n"
                    "   ❌ The URL opened in Chromium, but the page never rendered the "
                    f"interactive app shell; the visible body text was {visible_body_text!r}."
                ),
                (
                    "2. The workspace switcher panel is open in a pristine state.\n"
                    "   ❌ Not possible because no workspace switcher trigger became visible."
                ),
                (
                    "3. Keyboard focus is on the first interactive element in the panel.\n"
                    "   ❌ Not reached because the workspace switcher panel never rendered."
                ),
                (
                    "4. Press the 'Shift + Tab' keys on the keyboard.\n"
                    "   ❌ Not reached because the app never advanced past the blank startup state."
                ),
            ],
        )

    before_state = result.get("first_keyboard_target_state")
    after_state = result.get("after_shift_tab_state")
    return "\n".join(
        [
            (
                "1. Open the TrackState application and the workspace switcher panel in pristine state.\n"
                f"   {'✅' if _step_passed(result, 1) else '❌'} {_step_observation(result, 1)}"
            ),
            (
                "2. Ensure keyboard focus is on the first interactive element in the panel.\n"
                f"   {'✅' if isinstance(before_state, dict) and _active_label_for_summary(before_state) == _first_internal_label(before_state) else '❌'} "
                f"Focused before Shift+Tab: {_active_label_for_summary(before_state)!r}; "
                f"source={before_state.get('precondition_source') if isinstance(before_state, dict) else None!r}"
            ),
            (
                "3. Press the 'Shift + Tab' keys on the keyboard.\n"
                f"   {'✅' if _step_passed(result, 2) else '❌'} "
                + (
                    f"Expected focus: {_expected_target_label(after_state)!r}; actual focus: "
                    f"{_active_label_for_summary(after_state)!r}; footer state: "
                    f"{json.dumps(_button_state_from_state(after_state), ensure_ascii=True)}"
                    if isinstance(after_state, dict)
                    else "Not reached because the precondition failed before the Shift+Tab step."
                )
            ),
        ],
    )


if __name__ == "__main__":
    main()
