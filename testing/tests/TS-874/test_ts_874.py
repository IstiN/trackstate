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
    WorkspaceSwitcherButtonFocusabilityObservation,
    WorkspaceSwitcherEscapeDismissObservation,
    WorkspaceSwitcherFocusOwnershipObservation,
    WorkspaceSwitcherObservation,
    WorkspaceSwitcherPanelObservation,
    WorkspaceSwitcherRowFocusObservation,
    WorkspaceSwitcherSavedWorkspaceRowObservation,
    WorkspaceSwitcherTransitionMonitorObservation,
    WorkspaceSwitcherTriggerObservation,
    WorkspaceTriggerFocusStateObservation,
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

TICKET_KEY = "TS-874"
TEST_CASE_TITLE = (
    "Press Escape key while workspace switcher is open — panel closes and focus returns to trigger"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-874/test_ts_874.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 960}
ROW_FOCUS_STABILITY_MS = 500
ESCAPE_DISMISS_TIMEOUT_MS = 4_000
DEFAULT_BRANCH = "main"
FIRST_WORKSPACE_DISPLAY_NAME = "Hosted main workspace"
SECOND_WORKSPACE_DISPLAY_NAME = "Hosted alt workspace"
THIRD_WORKSPACE_DISPLAY_NAME = "Hosted third workspace"
SECOND_WORKSPACE_WRITE_BRANCH = "ts-874-alt"
THIRD_WORKSPACE_WRITE_BRANCH = "ts-874-third"
LINKED_BUGS = ["TS-872"]

PRECONDITIONS = [
    "The workspace switcher panel is open.",
    "Focus is currently on a workspace row.",
]
REQUEST_STEPS = [
    "Press the 'Escape' key on the keyboard.",
    "Observe the visibility of the workspace switcher panel.",
    "Observe the location of the keyboard focus.",
]
AUTOMATION_STEPS = [
    "Open the deployed desktop workspace switcher, confirm saved workspace rows are visible, and capture the trigger's unfocused baseline state.",
    "Move keyboard focus onto the selected saved workspace row and verify the row owns focus while the panel remains open.",
    "Press Escape and verify the visible workspace switcher panel dismisses immediately.",
    "Verify focus returns to the workspace switcher trigger, the trigger shows a visible focus indicator, and pressing Enter reopens the switcher without clicking.",
]
EXPECTED_RESULT = (
    "The workspace switcher panel closes immediately and is no longer visible. "
    "Keyboard focus is successfully restored to the workspace switcher trigger "
    "element, which displays a visible focus indicator."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts874_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts874_failure.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-874 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
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
        "row_focus_stability_ms": ROW_FOCUS_STABILITY_MS,
        "escape_dismiss_timeout_ms": ESCAPE_DISMISS_TIMEOUT_MS,
        "linked_bugs": LINKED_BUGS,
        "preconditions": PRECONDITIONS,
        "preloaded_workspace_state": workspace_state,
        "user_login": user.login,
        "steps": [],
        "human_verification": [],
    }

    page: LiveWorkspaceSwitcherPage | None = None
    current_step = 1
    current_action = AUTOMATION_STEPS[0]
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
                runtime = tracker_page.open()
                result["runtime_state"] = runtime.kind
                result["runtime_body_text"] = runtime.body_text
                if runtime.kind != "ready":
                    raise AssertionError(
                        "Step 1 failed: the deployed app did not reach an interactive "
                        "desktop state before the Escape dismissal scenario began.\n"
                        f"Observed runtime state: {runtime.kind}\n"
                        f"Observed body text:\n{runtime.body_text}",
                    )

                page.dismiss_connection_banner()
                page.navigate_to_section("Dashboard")
                page.set_viewport(**DESKTOP_VIEWPORT)

                current_step = 1
                current_action = AUTOMATION_STEPS[0]
                trigger_before = page.observe_trigger()
                trigger_focus_before = page.observe_desktop_trigger_focus_state()
                switcher = page.open_and_observe()
                panel = page.observe_open_panel(
                    expected_container_kinds=("anchored-panel", "surface"),
                )
                rows = page.observe_saved_workspace_rows()
                result["trigger_before"] = _trigger_payload(trigger_before)
                result["trigger_focus_before"] = _trigger_focus_state_payload(
                    trigger_focus_before,
                )
                result["open_switcher_observation"] = _switcher_payload(switcher)
                result["open_panel_observation"] = asdict(panel)
                result["saved_workspace_rows_before_focus"] = _saved_workspace_rows_payload(
                    rows,
                )
                _assert_initial_switcher_state(
                    trigger=trigger_before,
                    trigger_focus=trigger_focus_before,
                    switcher=switcher,
                    panel=panel,
                    rows=rows,
                )
                active_workspace = _selected_saved_workspace(rows)
                assert active_workspace is not None
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=AUTOMATION_STEPS[0],
                    observed=(
                        f"Opened {config.app_url} in Chromium at "
                        f"{DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}; "
                        f"row_count={len(rows)}; "
                        f"active_workspace={active_workspace.display_name!r}; "
                        f"trigger_label={trigger_before.semantic_label!r}; "
                        f"trigger_focused_before_open={trigger_focus_before.is_focused}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Opened the desktop Dashboard, opened the workspace switcher, and "
                        "visually confirmed the Workspace switcher title and saved "
                        "workspace rows were visible before pressing Escape."
                    ),
                    observed=(
                        "title='Workspace switcher'; "
                        f"saved_workspace_row_count={len(rows)}; "
                        f"active_workspace={active_workspace.display_name!r}; "
                        f"text_excerpt={_snippet(switcher.switcher_text)!r}"
                    ),
                )

                current_step = 2
                current_action = AUTOMATION_STEPS[1]
                focused_row_state = _focus_selected_workspace_row(
                    page=page,
                    expected_selected=FIRST_WORKSPACE_DISPLAY_NAME,
                )
                result["focused_row_state"] = focused_row_state
                _assert_row_focus_precondition(
                    state=focused_row_state,
                    expected_selected=FIRST_WORKSPACE_DISPLAY_NAME,
                )
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=AUTOMATION_STEPS[1],
                    observed=(
                        f"focused_label={_active_from_state(focused_row_state).get('accessible_name')!r}; "
                        f"row_contains_active={_row_focus_from_state(focused_row_state).get('row_contains_active')}; "
                        f"button_active_within={_row_button_from_state(focused_row_state).get('active_within')}; "
                        f"focus_on_trigger={_focus_from_state(focused_row_state).get('active_on_trigger')}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Moved focus onto the selected saved workspace row and confirmed the "
                        "user-visible focus stayed inside the open switcher on that row."
                    ),
                    observed=(
                        f"focused_label={_active_from_state(focused_row_state).get('accessible_name')!r}; "
                        f"row_text={_row_focus_from_state(focused_row_state).get('row_text')!r}; "
                        f"button_tabindex={_row_button_from_state(focused_row_state).get('tabindex')!r}"
                    ),
                )

                current_step = 3
                current_action = AUTOMATION_STEPS[2]
                page.start_transition_monitor()
                dismissal = page.wait_for_escape_dismissal(
                    timeout_ms=ESCAPE_DISMISS_TIMEOUT_MS,
                )
                escape_monitor = page.read_transition_monitor(clear=True)
                result["escape_dismissal_observation"] = _escape_dismissal_payload(
                    dismissal,
                )
                result["escape_transition_monitor"] = _transition_monitor_payload(
                    escape_monitor,
                )
                _assert_escape_surface_dismissal(
                    dismissal=dismissal,
                    monitor=escape_monitor,
                )
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action=AUTOMATION_STEPS[2],
                    observed=(
                        "Pressed Escape while the focused saved workspace row was inside "
                        "the open panel, and the transition monitor observed the panel "
                        f"disappear within {ESCAPE_DISMISS_TIMEOUT_MS} ms."
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Pressed Escape like a keyboard user from the focused workspace "
                        "row and confirmed the workspace switcher panel disappeared."
                    ),
                    observed=(
                        f"dashboard_visible={dismissal.dashboard_visible}; "
                        f"trigger_visible={dismissal.trigger_visible}; "
                        f"panel_hidden_after_visible={escape_monitor.ever_hidden_after_visible}"
                    ),
                )

                current_step = 4
                current_action = AUTOMATION_STEPS[3]
                trigger_after = page.observe_trigger()
                focused_after_escape = page.active_element()
                trigger_focus_after = page.observe_desktop_trigger_focus_state(
                    timeout_ms=ESCAPE_DISMISS_TIMEOUT_MS,
                )
                result["trigger_after"] = _trigger_payload(trigger_after)
                result["focused_after_escape"] = _focused_element_payload(
                    focused_after_escape,
                )
                result["trigger_focus_after"] = _trigger_focus_state_payload(
                    trigger_focus_after,
                )
                _assert_escape_focus_restored_to_trigger(
                    trigger_before=trigger_before,
                    trigger_after=trigger_after,
                    focused_after_escape=focused_after_escape,
                    trigger_focus_before=trigger_focus_before,
                    trigger_focus_after=trigger_focus_after,
                )
                page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
                page.press_enter_on_active_element_and_wait_for_surface(
                    timeout_ms=ESCAPE_DISMISS_TIMEOUT_MS,
                )
                keyboard_reopen_switcher = page.observe_open_switcher(
                    timeout_ms=ESCAPE_DISMISS_TIMEOUT_MS,
                )
                keyboard_reopen_panel = page.observe_open_panel(
                    expected_container_kinds=("anchored-panel", "surface"),
                    timeout_ms=ESCAPE_DISMISS_TIMEOUT_MS,
                )
                result["keyboard_reopen_switcher_observation"] = _switcher_payload(
                    keyboard_reopen_switcher,
                )
                result["keyboard_reopen_panel_observation"] = asdict(
                    keyboard_reopen_panel,
                )
                _assert_keyboard_reopen_after_escape(
                    trigger_after=trigger_after,
                    keyboard_reopen_switcher=keyboard_reopen_switcher,
                    keyboard_reopen_panel=keyboard_reopen_panel,
                )
                _record_step(
                    result,
                    step=4,
                    status="passed",
                    action=AUTOMATION_STEPS[3],
                    observed=(
                        f"focused_after_escape={focused_after_escape.accessible_name!r}; "
                        f"trigger_focus_visible={trigger_focus_after.focus_visible}; "
                        f"trigger_outline_width={trigger_focus_after.outline_width!r}; "
                        f"trigger_box_shadow={trigger_focus_after.box_shadow!r}; "
                        f"keyboard_reopen_rows={keyboard_reopen_switcher.row_count}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "After the panel closed, confirmed focus was back on the visible "
                        "workspace switcher trigger, a focus indicator was shown on that "
                        "trigger, and pressing Enter reopened the switcher without clicking."
                    ),
                    observed=(
                        f"focused_after_escape={focused_after_escape.accessible_name!r}; "
                        f"trigger_is_focused={trigger_focus_after.is_focused}; "
                        f"trigger_focus_visible={trigger_focus_after.focus_visible}; "
                        f"keyboard_reopen_kind={keyboard_reopen_panel.container_kind!r}"
                    ),
                )
            except Exception:
                try:
                    page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                    result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                except Exception as screenshot_error:
                    result["screenshot_error"] = (
                        f"{type(screenshot_error).__name__}: {screenshot_error}"
                    )
                raise
    except AssertionError as error:
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


def _focus_selected_workspace_row(
    *,
    page: LiveWorkspaceSwitcherPage,
    expected_selected: str,
) -> dict[str, object]:
    panel = page.observe_open_panel(
        expected_container_kinds=("anchored-panel", "surface"),
        timeout_ms=4_000,
    )
    switcher = page.observe_open_switcher(timeout_ms=4_000)
    rows = page.observe_saved_workspace_rows(timeout_ms=4_000)
    active_workspace = _selected_saved_workspace(rows)
    if active_workspace is None:
        raise AssertionError(
            "Step 2 failed: the open workspace switcher did not expose any selected "
            "saved workspace row before the Escape-key precondition was established.\n"
            f"Observed rows: {json.dumps(_saved_workspace_rows_payload(rows), indent=2)}",
        )
    if active_workspace.display_name != expected_selected:
        raise AssertionError(
            "Step 2 failed: the initially selected saved workspace did not match the "
            "expected row before keyboard focus was moved onto it.\n"
            f"Expected selected row: {expected_selected!r}\n"
            f"Observed selected row: {active_workspace.display_name!r}\n"
            f"Observed rows: {json.dumps(_saved_workspace_rows_payload(rows), indent=2)}",
        )

    row_label = _saved_workspace_row_focus_label(active_workspace)
    page.focus_switcher_button(
        row_label,
        panel=panel,
        timeout_ms=4_000,
    )
    page.wait_for_surface_to_remain_open(
        stability_ms=ROW_FOCUS_STABILITY_MS,
        timeout_ms=4_000,
    )

    panel = page.observe_open_panel(
        expected_container_kinds=("anchored-panel", "surface"),
        timeout_ms=4_000,
    )
    switcher = page.observe_open_switcher(timeout_ms=4_000)
    rows = page.observe_saved_workspace_rows(timeout_ms=4_000)
    active = page.active_element()
    focus = page.observe_focus_ownership(panel=panel)
    row_focus = page.observe_saved_workspace_row_focus(
        display_name=expected_selected,
        panel=panel,
    )
    row_button = page.observe_switcher_button_focusability(
        row_label,
        timeout_ms=4_000,
    )
    return {
        "active_workspace_name": expected_selected,
        "switcher": _switcher_payload(switcher),
        "panel": asdict(panel),
        "saved_workspace_rows": _saved_workspace_rows_payload(rows),
        "active": _focused_element_payload(active),
        "focus": _focus_ownership_payload(focus),
        "row_focus": _row_focus_payload(row_focus),
        "row_button": _button_focusability_payload(row_button),
        "row_label": row_label,
    }


def _assert_initial_switcher_state(
    *,
    trigger: WorkspaceSwitcherTriggerObservation,
    trigger_focus: WorkspaceTriggerFocusStateObservation,
    switcher: WorkspaceSwitcherObservation,
    panel: WorkspaceSwitcherPanelObservation,
    rows: tuple[WorkspaceSwitcherSavedWorkspaceRowObservation, ...],
) -> None:
    failures: list[str] = []
    if not trigger.semantic_label.startswith("Workspace switcher:"):
        failures.append(
            f"the visible trigger label did not describe a workspace switcher ({trigger.semantic_label!r})",
        )
    if trigger_focus.is_focused:
        failures.append("the trigger unexpectedly appeared focused before the panel was opened")
    if "Workspace switcher" not in switcher.switcher_text:
        failures.append("the visible Workspace switcher title was not present")
    if len(rows) < 3:
        failures.append("fewer than three saved workspace rows were visible")
    if panel.container_kind not in {"anchored-panel", "surface"}:
        failures.append(
            f"the panel kind was {panel.container_kind!r} instead of an anchored desktop surface",
        )
    active_workspace = _selected_saved_workspace(rows)
    if active_workspace is None or active_workspace.display_name != FIRST_WORKSPACE_DISPLAY_NAME:
        failures.append(
            "the expected first saved workspace row was not the selected row before row focus was applied",
        )
    if failures:
        raise AssertionError(
            "Step 1 failed: the workspace switcher did not reach the expected visible "
            "desktop state before the Escape-key interaction began.\n"
            + "\n".join(f"- {item}" for item in failures)
            + "\n"
            + f"Observed trigger: {json.dumps(_trigger_payload(trigger), indent=2)}\n"
            + f"Observed trigger focus: {json.dumps(_trigger_focus_state_payload(trigger_focus), indent=2)}\n"
            + f"Observed panel: {json.dumps(asdict(panel), indent=2)}\n"
            + f"Observed rows: {json.dumps(_saved_workspace_rows_payload(rows), indent=2)}"
        )


def _assert_row_focus_precondition(
    *,
    state: dict[str, object],
    expected_selected: str,
) -> None:
    active = _active_from_state(state)
    focus = _focus_from_state(state)
    row_focus = _row_focus_from_state(state)
    row_button = _row_button_from_state(state)

    failures: list[str] = []
    if _active_workspace_name_from_state(state) != expected_selected:
        failures.append(
            f"the selected workspace row was {_active_workspace_name_from_state(state)!r} instead of {expected_selected!r}",
        )
    if not bool(focus.get("focus_owned_by_switcher")):
        failures.append("keyboard focus was not owned by the workspace switcher")
    if not bool(focus.get("active_within_switcher")):
        failures.append("the active element was not inside the open workspace switcher")
    if bool(focus.get("active_on_trigger")):
        failures.append("keyboard focus remained on the trigger instead of the saved workspace row")
    if not bool(row_focus.get("row_found")):
        failures.append(f"the saved workspace row {expected_selected!r} could not be located")
    if not bool(row_focus.get("row_contains_active")):
        failures.append(f"the saved workspace row {expected_selected!r} did not contain the active element")
    if not bool(row_button.get("active_within")):
        failures.append(f"the row button for {expected_selected!r} was not the active focused control")
    if not bool(row_button.get("keyboard_focusable")):
        failures.append(f"the row button for {expected_selected!r} was not keyboard focusable")
    if failures:
        raise AssertionError(
            "Step 2 failed: keyboard focus did not move onto the selected saved "
            "workspace row before Escape was pressed.\n"
            + "\n".join(f"- {item}" for item in failures)
            + "\n"
            + f"Observed active element: {json.dumps(active, indent=2)}\n"
            + f"Observed focus ownership: {json.dumps(focus, indent=2)}\n"
            + f"Observed row focus: {json.dumps(row_focus, indent=2)}\n"
            + f"Observed row button: {json.dumps(row_button, indent=2)}"
        )


def _assert_escape_surface_dismissal(
    *,
    dismissal: WorkspaceSwitcherEscapeDismissObservation,
    monitor: WorkspaceSwitcherTransitionMonitorObservation,
) -> None:
    failures: list[str] = []
    if not dismissal.dashboard_visible:
        failures.append("the main Dashboard shell was not visible after Escape")
    if not dismissal.trigger_visible:
        failures.append("the workspace switcher trigger was not visible after Escape")
    if monitor.sample_count <= 0 or monitor.visible_sample_count <= 0:
        failures.append(
            "the transition monitor did not capture the visible workspace switcher surface before Escape",
        )
    if (
        not monitor.ever_hidden_after_visible
        and monitor.latest_visible_row_count not in {0, None}
    ):
        failures.append(
            "the transition monitor still observed a visible workspace switcher surface with rows after Escape",
        )
    if failures:
        raise AssertionError(
            "Step 3 failed: pressing Escape did not dismiss the user-visible workspace "
            "switcher panel reliably.\n"
            + "\n".join(f"- {item}" for item in failures)
            + "\n"
            + f"Observed dismissal: {json.dumps(_escape_dismissal_payload(dismissal), indent=2)}\n"
            + f"Observed monitor: {json.dumps(_transition_monitor_payload(monitor), indent=2)}"
        )


def _assert_escape_focus_restored_to_trigger(
    *,
    trigger_before: WorkspaceSwitcherTriggerObservation,
    trigger_after: WorkspaceSwitcherTriggerObservation,
    focused_after_escape: FocusedElementObservation,
    trigger_focus_before: WorkspaceTriggerFocusStateObservation,
    trigger_focus_after: WorkspaceTriggerFocusStateObservation,
) -> None:
    failures: list[str] = []

    if trigger_after.semantic_label != trigger_before.semantic_label:
        failures.append(
            "the workspace switcher trigger no longer reflected the same active "
            f"workspace state (before={trigger_before.semantic_label!r}, "
            f"after={trigger_after.semantic_label!r})",
        )
    if not _is_workspace_trigger_focus(
        focused_after_escape.accessible_name,
        fallback_text=focused_after_escape.text,
    ):
        failures.append(
            "keyboard focus after Escape was not restored to the workspace switcher trigger",
        )
    if not trigger_focus_after.is_focused:
        failures.append("the trigger itself was not the focused element after Escape")

    indicator_changed = any(
        before != after
        for before, after in (
            (trigger_focus_before.outline, trigger_focus_after.outline),
            (trigger_focus_before.outline_color, trigger_focus_after.outline_color),
            (trigger_focus_before.outline_width, trigger_focus_after.outline_width),
            (trigger_focus_before.box_shadow, trigger_focus_after.box_shadow),
        )
    )
    has_outline = _has_nonzero_outline(
        trigger_focus_after.outline,
        trigger_focus_after.outline_width,
    )
    has_box_shadow = _has_box_shadow(trigger_focus_after.box_shadow)
    if not (
        trigger_focus_after.focus_visible
        and (indicator_changed or has_outline or has_box_shadow)
    ):
        failures.append(
            "the restored workspace switcher trigger did not expose a visible keyboard focus indicator",
        )

    if failures:
        raise AssertionError(
            "Step 4 failed: after Escape, focus was not fully restored to the "
            "workspace switcher trigger with a visible focus indicator.\n"
            + "\n".join(f"- {item}" for item in failures)
            + "\n"
            + "Observed focused element after Escape: "
            + f"label={focused_after_escape.accessible_name!r}, "
            + f"role={focused_after_escape.role!r}, tag={focused_after_escape.tag_name!r}, "
            + f"text={focused_after_escape.text!r}\n"
            + "Observed trigger focus before opening: "
            + json.dumps(_trigger_focus_state_payload(trigger_focus_before), indent=2)
            + "\nObserved trigger focus after Escape: "
            + json.dumps(_trigger_focus_state_payload(trigger_focus_after), indent=2)
        )


def _assert_keyboard_reopen_after_escape(
    *,
    trigger_after: WorkspaceSwitcherTriggerObservation,
    keyboard_reopen_switcher: WorkspaceSwitcherObservation,
    keyboard_reopen_panel: WorkspaceSwitcherPanelObservation,
) -> None:
    try:
        _assert_desktop_panel_open(
            trigger=trigger_after,
            switcher=keyboard_reopen_switcher,
            panel=keyboard_reopen_panel,
        )
    except AssertionError as error:
        raise AssertionError(
            "Step 4 failed: pressing Enter immediately after Escape did not reopen the "
            f"visible workspace switcher from the restored trigger focus ({error})",
        ) from error


def _assert_desktop_panel_open(
    *,
    trigger: WorkspaceSwitcherTriggerObservation,
    switcher: WorkspaceSwitcherObservation,
    panel: WorkspaceSwitcherPanelObservation,
) -> None:
    failures: list[str] = []
    if not trigger.semantic_label.startswith("Workspace switcher:"):
        failures.append("the visible trigger was no longer a workspace switcher control")
    if switcher.row_count <= 0:
        failures.append("opening the workspace switcher did not expose any visible workspace rows")
    if panel.container_kind not in {"anchored-panel", "surface"}:
        failures.append(
            f"the visible surface kind was {panel.container_kind!r} instead of a desktop workspace-switcher panel",
        )
    if panel.width <= 0 or panel.height <= 0:
        failures.append("the visible panel bounds were not readable")
    if failures:
        raise AssertionError(
            "The visible workspace switcher panel was not present in the expected desktop form.\n"
            + "\n".join(f"- {item}" for item in failures)
            + "\n"
            + f"Observed trigger: {json.dumps(_trigger_payload(trigger), indent=2)}\n"
            + f"Observed switcher: {json.dumps(_switcher_payload(switcher), indent=2)}\n"
            + f"Observed panel: {json.dumps(asdict(panel), indent=2)}"
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
    error = str(result.get("error", "AssertionError: TS-874 failed"))
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
        "* Opened the deployed TrackState app in Chromium with a stored hosted token and preloaded saved workspace profiles.",
        "* Opened the desktop workspace switcher and moved keyboard focus onto a saved workspace row.",
        "* Pressed the Escape key while the workspace row had focus inside the open panel.",
        "* Verified the panel disappeared, focus returned to the workspace switcher trigger, and the trigger showed a visible focus indicator.",
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
        "- Opened the deployed TrackState app in Chromium with a stored hosted token and preloaded saved workspace profiles.",
        "- Opened the desktop workspace switcher and moved keyboard focus onto a saved workspace row.",
        "- Pressed Escape while the row was focused inside the visible panel.",
        "- Verified the panel disappeared, focus returned to the workspace switcher trigger, the trigger showed a visible focus indicator, and Enter reopened the switcher without clicking.",
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
        "- Added TS-874 live desktop coverage for Escape-key dismissal from a focused saved-workspace row in the workspace switcher.",
        f"- Test case: **{TICKET_KEY} - {TEST_CASE_TITLE}**",
        f"- Result: **{status}**",
        f"- Command: `{RUN_COMMAND}`",
        (
            f"- Environment: `{result['app_url']}` on Chromium/Playwright "
            f"({result['os']}) against `{result['repository']}` @ "
            f"`{result['repository_ref']}`."
        ),
        (
            f"- Outcome: {_failed_step_summary(result)}"
            if not passed
            else "- Outcome: Escape closed the panel, focus returned to the trigger, a visible focus indicator was present, and Enter reopened the switcher without clicking."
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
    return "\n".join(
        [
            f"# {TICKET_KEY} - Escape from focused workspace row does not fully restore trigger state",
            "",
            "## Steps to reproduce",
            "1. Open the deployed TrackState desktop app.",
            "2. Open the workspace switcher from Dashboard.",
            "3. Move keyboard focus onto the selected saved workspace row.",
            "4. Press Escape.",
            "5. Observe whether the panel closes and whether focus returns to the workspace switcher trigger with a visible focus indicator.",
            "",
            "## Exact steps from the test case with observations",
            *_annotated_request_steps(result),
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
            "## Screenshots or logs",
            f"- Screenshot: {result.get('screenshot', '<no screenshot recorded>')}",
            "```json",
            json.dumps(
                {
                    "trigger_before": result.get("trigger_before"),
                    "trigger_focus_before": result.get("trigger_focus_before"),
                    "open_switcher_observation": result.get("open_switcher_observation"),
                    "open_panel_observation": result.get("open_panel_observation"),
                    "saved_workspace_rows_before_focus": result.get(
                        "saved_workspace_rows_before_focus",
                    ),
                    "focused_row_state": result.get("focused_row_state"),
                    "escape_dismissal_observation": result.get("escape_dismissal_observation"),
                    "escape_transition_monitor": result.get("escape_transition_monitor"),
                    "trigger_after": result.get("trigger_after"),
                    "focused_after_escape": result.get("focused_after_escape"),
                    "trigger_focus_after": result.get("trigger_focus_after"),
                },
                indent=2,
            ),
            "```",
        ],
    ) + "\n"


def _annotated_request_steps(result: dict[str, object]) -> list[str]:
    failed_step = _first_failed_step_number(result)
    failed_summary = _failed_step_summary(result)
    if failed_step is None:
        return [
            f"1. ✅ {REQUEST_STEPS[0]} — Escape was sent from the focused saved workspace row.",
            "2. ✅ Observe the visibility of the workspace switcher panel. — The panel disappeared and was no longer visible.",
            "3. ✅ Observe the location of the keyboard focus. — Focus was restored to the workspace switcher trigger and Enter reopened the switcher without any click.",
        ]
    if failed_step <= 2:
        return [
            f"1. ❌ {REQUEST_STEPS[0]} — Not reached because the row-focus precondition failed before Escape could be pressed. {failed_summary}",
            f"2. ❌ {REQUEST_STEPS[1]} — Not reached because Escape was not pressed. {failed_summary}",
            f"3. ❌ {REQUEST_STEPS[2]} — Not reached because Escape was not pressed. {failed_summary}",
        ]
    if failed_step == 3:
        return [
            f"1. ✅ {REQUEST_STEPS[0]} — Escape was sent from the focused saved workspace row.",
            f"2. ❌ {REQUEST_STEPS[1]} — {failed_summary}",
            f"3. ❌ {REQUEST_STEPS[2]} — Not reached because the panel dismissal check already failed. {failed_summary}",
        ]
    return [
        f"1. ✅ {REQUEST_STEPS[0]} — Escape was sent from the focused saved workspace row.",
        "2. ✅ Observe the visibility of the workspace switcher panel. — The panel dismissed and the dashboard shell became visible again.",
        f"3. ❌ {REQUEST_STEPS[2]} — {failed_summary}",
    ]


def _steps(result: dict[str, object]) -> list[dict[str, object]]:
    items = result.get("steps", [])
    return items if isinstance(items, list) else []


def _human_verification(result: dict[str, object]) -> list[dict[str, object]]:
    items = result.get("human_verification", [])
    return items if isinstance(items, list) else []


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for step in _steps(result):
        prefix = "#" if jira else "1."
        lines.append(
            f"{prefix} Step {step['step']} — *{step['status'].upper()}*: {step['action']} — {step['observed']}"
            if jira
            else f"{prefix} Step {step['step']} — **{step['status'].upper()}**: {step['action']} — {step['observed']}"
        )
    return lines


def _human_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for item in _human_verification(result):
        prefix = "#" if jira else "1."
        lines.append(
            f"{prefix} {item['check']} — {item['observed']}"
        )
    return lines


def _artifact_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    screenshot = result.get("screenshot")
    if not screenshot:
        return []
    if jira:
        return ["", f"*Screenshot:* {{{{{screenshot}}}}}"]
    return ["", f"**Screenshot:** `{screenshot}`"]


def _failed_step_summary(result: dict[str, object]) -> str:
    failed = next((step for step in _steps(result) if step.get("status") == "failed"), None)
    if failed is None:
        return "No failed step was recorded."
    return (
        f"Step {failed.get('step')} failed while {failed.get('action')}: "
        f"{failed.get('observed')}"
    )


def _first_failed_step_number(result: dict[str, object]) -> int | None:
    failed = next((step for step in _steps(result) if step.get("status") == "failed"), None)
    if failed is None:
        return None
    step = failed.get("step")
    return int(step) if isinstance(step, int) else None


def _has_failed_step(result: dict[str, object]) -> bool:
    return any(step.get("status") == "failed" for step in _steps(result))


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
                "lastOpenedAt": "2026-05-18T03:30:00.000Z",
            },
            {
                "id": second_id,
                "displayName": SECOND_WORKSPACE_DISPLAY_NAME,
                "customDisplayName": SECOND_WORKSPACE_DISPLAY_NAME,
                "targetType": "hosted",
                "target": repository,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": SECOND_WORKSPACE_WRITE_BRANCH,
                "lastOpenedAt": "2026-05-18T03:20:00.000Z",
            },
            {
                "id": third_id,
                "displayName": THIRD_WORKSPACE_DISPLAY_NAME,
                "customDisplayName": THIRD_WORKSPACE_DISPLAY_NAME,
                "targetType": "hosted",
                "target": repository,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": THIRD_WORKSPACE_WRITE_BRANCH,
                "lastOpenedAt": "2026-05-18T03:10:00.000Z",
            },
        ],
    }


def _is_workspace_trigger_focus(label: str | None, *, fallback_text: str | None) -> bool:
    return any(
        value is not None and value.startswith("Workspace switcher:")
        for value in (label, fallback_text)
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


def _snippet(value: str, *, limit: int = 220) -> str:
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1] + "…"


def _active_workspace_name_from_state(state: dict[str, object]) -> str | None:
    value = state.get("active_workspace_name")
    return str(value) if value is not None else None


def _active_from_state(state: dict[str, object]) -> dict[str, object]:
    value = state.get("active")
    return value if isinstance(value, dict) else {}


def _focus_from_state(state: dict[str, object]) -> dict[str, object]:
    value = state.get("focus")
    return value if isinstance(value, dict) else {}


def _row_focus_from_state(state: dict[str, object]) -> dict[str, object]:
    value = state.get("row_focus")
    return value if isinstance(value, dict) else {}


def _row_button_from_state(state: dict[str, object]) -> dict[str, object]:
    value = state.get("row_button")
    return value if isinstance(value, dict) else {}


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


def _button_focusability_payload(
    observation: WorkspaceSwitcherButtonFocusabilityObservation,
) -> dict[str, object]:
    return {
        "label": observation.label,
        "visible_text": observation.visible_text,
        "role": observation.role,
        "tag_name": observation.tag_name,
        "tabindex": observation.tabindex,
        "keyboard_focusable": observation.keyboard_focusable,
        "active_within": observation.active_within,
        "outer_html": observation.outer_html,
    }


def _trigger_payload(trigger: WorkspaceSwitcherTriggerObservation) -> dict[str, object]:
    return {
        "viewport_width": trigger.viewport_width,
        "viewport_height": trigger.viewport_height,
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


def _trigger_focus_state_payload(
    observation: WorkspaceTriggerFocusStateObservation,
) -> dict[str, object]:
    return {
        "trigger_label": observation.trigger_label,
        "trigger_text": observation.trigger_text,
        "outline": observation.outline,
        "outline_color": observation.outline_color,
        "outline_width": observation.outline_width,
        "box_shadow": observation.box_shadow,
        "focus_visible": observation.focus_visible,
        "is_focused": observation.is_focused,
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


def _escape_dismissal_payload(
    dismissal: WorkspaceSwitcherEscapeDismissObservation,
) -> dict[str, object]:
    return {
        "body_text": dismissal.body_text,
        "dashboard_visible": dismissal.dashboard_visible,
        "trigger_visible": dismissal.trigger_visible,
    }


def _transition_monitor_payload(
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


def _focused_element_payload(observation: FocusedElementObservation) -> dict[str, object]:
    return {
        "accessible_name": observation.accessible_name,
        "role": observation.role,
        "tag_name": observation.tag_name,
        "text": observation.text,
        "outer_html": observation.outer_html,
    }


if __name__ == "__main__":
    main()
