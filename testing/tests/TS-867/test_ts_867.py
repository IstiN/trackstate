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
    WorkspaceSwitcherFocusOwnershipObservation,
    WorkspaceSwitcherObservation,
    WorkspaceSwitcherPanelObservation,
    WorkspaceSwitcherRowFocusObservation,
    WorkspaceSwitcherSavedWorkspaceRowObservation,
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

TICKET_KEY = "TS-867"
TEST_CASE_TITLE = (
    "Workspace list roving tabindex — only the selected item is focusable via Tab"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-867/test_ts_867.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 960}
KEY_STABILITY_MS = 1_000
TAB_STABILITY_MS = 500
DEFAULT_BRANCH = "main"
FIRST_WORKSPACE_DISPLAY_NAME = "Hosted main workspace"
SECOND_WORKSPACE_DISPLAY_NAME = "Hosted alt workspace"
THIRD_WORKSPACE_DISPLAY_NAME = "Hosted third workspace"
SECOND_WORKSPACE_WRITE_BRANCH = "ts-867-alt"
THIRD_WORKSPACE_WRITE_BRANCH = "ts-867-third"
LINKED_BUGS = ["TS-866", "TS-870"]

PRECONDITIONS = [
    "At least three saved workspaces exist.",
    "The workspace switcher panel is open.",
    "The second workspace row is currently highlighted/selected (for example via Arrow Down).",
]
REQUEST_STEPS = [
    "Press the Tab key to move focus out of the workspace row list toward the next interactive element (e.g., 'Add workspace' button).",
    "Press the Shift + Tab keys to return focus back into the workspace list.",
    "Observe which workspace row receives focus.",
    "Attempt to press the Tab key to move focus to the first workspace row while the second is selected.",
]
AUTOMATION_STEPS = [
    "Open the deployed desktop workspace switcher and confirm three saved workspace rows are visible with the first row selected.",
    "Explicitly move keyboard focus onto the active first saved workspace row and verify the row-list focus precondition is met before Arrow Down is used.",
    "Press Arrow Down once to move selection and keyboard focus from the first saved workspace row to the second row, leaving only the second row in the sequential Tab order.",
    "Press Tab from the selected second row and verify focus leaves the workspace row list without landing on the first or third saved workspace row while the second row remains the only focusable row.",
    "Press Shift+Tab and verify focus returns directly to the selected second saved workspace row, not to the first or third row, while the roving tabindex state stays intact.",
    "Press Tab again while the second row remains selected and verify sequential keyboard navigation still bypasses the inactive first and third rows.",
]
EXPECTED_RESULT = (
    "Sequential Tab navigation bypasses all non-selected workspace rows. When focus "
    "returns into the workspace list, it lands directly on the selected second row, "
    "and inactive rows stay out of the Tab order with tabindex='-1'."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
REVIEW_REPLIES_PATH = OUTPUTS_DIR / "review_replies.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts867_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts867_failure.png"
DISCUSSIONS_RAW_PATH = REPO_ROOT / "input" / TICKET_KEY / "pr_discussions_raw.json"

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
            "TS-867 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
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
        "key_stability_ms": KEY_STABILITY_MS,
        "tab_stability_ms": TAB_STABILITY_MS,
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
                        "desktop state before the workspace roving-tabindex scenario began.\n"
                        f"Observed runtime state: {runtime.kind}\n"
                        f"Observed body text:\n{runtime.body_text}",
                    )

                page.dismiss_connection_banner()
                page.navigate_to_section("Dashboard")
                page.set_viewport(**DESKTOP_VIEWPORT)

                current_step = 1
                current_action = AUTOMATION_STEPS[0]
                ready_state = _open_switcher_and_capture(page)
                result["initial_state"] = ready_state
                _assert_initial_switcher_state(ready_state)
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=AUTOMATION_STEPS[0],
                    observed=(
                        f"Opened {config.app_url} in Chromium at "
                        f"{DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}; "
                        f"saved_workspace_row_count={len(_saved_workspace_rows_from_state(ready_state))}; "
                        f"active_workspace={ready_state['active_workspace_name']!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Opened the desktop workspace switcher and visually confirmed the "
                        "Workspace switcher title plus all three saved workspace rows were "
                        "visible before keyboard navigation."
                    ),
                    observed=(
                        f"active_workspace={ready_state['active_workspace_name']!r}; "
                        f"text_excerpt={_snippet(str(_switcher_from_state(ready_state).get('switcher_text')))!r}"
                    ),
                )

                current_step = 2
                current_action = AUTOMATION_STEPS[1]
                focused_active_row_state = _focus_active_workspace_row_and_capture(
                    page=page,
                    expected_selected=FIRST_WORKSPACE_DISPLAY_NAME,
                )
                result["focused_active_row_state"] = focused_active_row_state
                _assert_row_focus_precondition(
                    state=focused_active_row_state,
                    expected_selected=FIRST_WORKSPACE_DISPLAY_NAME,
                    inactive_names=(
                        SECOND_WORKSPACE_DISPLAY_NAME,
                        THIRD_WORKSPACE_DISPLAY_NAME,
                    ),
                    step_prefix="Step 2 failed",
                )
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=AUTOMATION_STEPS[1],
                    observed=(
                        f"focused_label={_active_from_state(focused_active_row_state).get('accessible_name')!r}; "
                        f"first_row_contains_active={_row_focus_from_state(focused_active_row_state, FIRST_WORKSPACE_DISPLAY_NAME).get('row_contains_active')}; "
                        f"first_tabindex={_button_from_state(focused_active_row_state, FIRST_WORKSPACE_DISPLAY_NAME).get('tabindex')!r}; "
                        f"second_tabindex={_button_from_state(focused_active_row_state, SECOND_WORKSPACE_DISPLAY_NAME).get('tabindex')!r}; "
                        f"third_tabindex={_button_from_state(focused_active_row_state, THIRD_WORKSPACE_DISPLAY_NAME).get('tabindex')!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Moved focus into the saved-workspace row list before Arrow Down "
                        "and confirmed the first active row owned keyboard focus."
                    ),
                    observed=(
                        f"focused_label={_active_from_state(focused_active_row_state).get('accessible_name')!r}; "
                        f"row_focus_first={_row_focus_from_state(focused_active_row_state, FIRST_WORKSPACE_DISPLAY_NAME).get('row_contains_active')}; "
                        f"focus_on_trigger={_focus_from_state(focused_active_row_state).get('active_on_trigger')}"
                    ),
                )

                current_step = 3
                current_action = AUTOMATION_STEPS[2]
                arrow_state = _press_key_and_capture(
                    page=page,
                    key="ArrowDown",
                    stability_ms=KEY_STABILITY_MS,
                    expected_active_workspace=SECOND_WORKSPACE_DISPLAY_NAME,
                )
                result["arrow_down_state"] = arrow_state
                _assert_panel_open_after_key(
                    key="Arrow Down",
                    state=arrow_state,
                    step_prefix="Step 3 failed",
                )
                _assert_selected_row_roving_state(
                    state=arrow_state,
                    expected_selected=SECOND_WORKSPACE_DISPLAY_NAME,
                    inactive_names=(
                        FIRST_WORKSPACE_DISPLAY_NAME,
                        THIRD_WORKSPACE_DISPLAY_NAME,
                    ),
                    step_prefix="Step 3 failed",
                    require_row_focus=True,
                )
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action=AUTOMATION_STEPS[2],
                    observed=(
                        f"active_workspace={arrow_state['active_workspace_name']!r}; "
                        f"focused_label={_active_from_state(arrow_state).get('accessible_name')!r}; "
                        f"second_tabindex={_button_from_state(arrow_state, SECOND_WORKSPACE_DISPLAY_NAME).get('tabindex')!r}; "
                        f"first_tabindex={_button_from_state(arrow_state, FIRST_WORKSPACE_DISPLAY_NAME).get('tabindex')!r}; "
                        f"third_tabindex={_button_from_state(arrow_state, THIRD_WORKSPACE_DISPLAY_NAME).get('tabindex')!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Pressed Arrow Down once and watched the highlight and keyboard "
                        "focus move from the first saved workspace row to the second row."
                    ),
                    observed=(
                        f"active_after_arrow={arrow_state['active_workspace_name']!r}; "
                        f"focused_label_after_arrow={_active_from_state(arrow_state).get('accessible_name')!r}; "
                        f"row_focus_second={_row_focus_from_state(arrow_state, SECOND_WORKSPACE_DISPLAY_NAME).get('row_contains_active')}"
                    ),
                )

                current_step = 4
                current_action = AUTOMATION_STEPS[3]
                tab_out_state = _press_key_and_capture(
                    page=page,
                    key="Tab",
                    stability_ms=TAB_STABILITY_MS,
                )
                result["tab_out_state"] = tab_out_state
                _assert_panel_open_after_key(
                    key="Tab",
                    state=tab_out_state,
                    step_prefix="Step 4 failed",
                )
                _assert_tab_left_workspace_rows(
                    state=tab_out_state,
                    expected_selected=SECOND_WORKSPACE_DISPLAY_NAME,
                    inactive_names=(
                        FIRST_WORKSPACE_DISPLAY_NAME,
                        THIRD_WORKSPACE_DISPLAY_NAME,
                    ),
                    step_prefix="Step 4 failed",
                )
                _record_step(
                    result,
                    step=4,
                    status="passed",
                    action=AUTOMATION_STEPS[3],
                    observed=(
                        f"focused_after_tab={_active_from_state(tab_out_state).get('accessible_name')!r}; "
                        f"focused_role_after_tab={_active_from_state(tab_out_state).get('role')!r}; "
                        f"second_row_contains_active={_row_focus_from_state(tab_out_state, SECOND_WORKSPACE_DISPLAY_NAME).get('row_contains_active')}; "
                        f"first_tabindex={_button_from_state(tab_out_state, FIRST_WORKSPACE_DISPLAY_NAME).get('tabindex')!r}; "
                        f"third_tabindex={_button_from_state(tab_out_state, THIRD_WORKSPACE_DISPLAY_NAME).get('tabindex')!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Pressed Tab from the selected second row and watched focus move "
                        "away from the workspace row list without landing on either "
                        "inactive saved workspace row."
                    ),
                    observed=(
                        f"focused_after_tab={_active_from_state(tab_out_state).get('accessible_name')!r}; "
                        f"row_focus_first={_row_focus_from_state(tab_out_state, FIRST_WORKSPACE_DISPLAY_NAME).get('row_contains_active')}; "
                        f"row_focus_second={_row_focus_from_state(tab_out_state, SECOND_WORKSPACE_DISPLAY_NAME).get('row_contains_active')}; "
                        f"row_focus_third={_row_focus_from_state(tab_out_state, THIRD_WORKSPACE_DISPLAY_NAME).get('row_contains_active')}"
                    ),
                )

                current_step = 5
                current_action = AUTOMATION_STEPS[4]
                shift_tab_state = _press_key_and_capture(
                    page=page,
                    key="Shift+Tab",
                    stability_ms=TAB_STABILITY_MS,
                )
                result["shift_tab_state"] = shift_tab_state
                _assert_panel_open_after_key(
                    key="Shift+Tab",
                    state=shift_tab_state,
                    step_prefix="Step 5 failed",
                )
                _assert_selected_row_roving_state(
                    state=shift_tab_state,
                    expected_selected=SECOND_WORKSPACE_DISPLAY_NAME,
                    inactive_names=(
                        FIRST_WORKSPACE_DISPLAY_NAME,
                        THIRD_WORKSPACE_DISPLAY_NAME,
                    ),
                    step_prefix="Step 5 failed",
                    require_row_focus=True,
                )
                _record_step(
                    result,
                    step=5,
                    status="passed",
                    action=AUTOMATION_STEPS[4],
                    observed=(
                        f"focused_after_shift_tab={_active_from_state(shift_tab_state).get('accessible_name')!r}; "
                        f"second_row_contains_active={_row_focus_from_state(shift_tab_state, SECOND_WORKSPACE_DISPLAY_NAME).get('row_contains_active')}; "
                        f"second_tabindex={_button_from_state(shift_tab_state, SECOND_WORKSPACE_DISPLAY_NAME).get('tabindex')!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Pressed Shift+Tab like a desktop user and verified focus returned "
                        "directly to the selected second workspace row."
                    ),
                    observed=(
                        f"focused_after_shift_tab={_active_from_state(shift_tab_state).get('accessible_name')!r}; "
                        f"first_row_contains_active={_row_focus_from_state(shift_tab_state, FIRST_WORKSPACE_DISPLAY_NAME).get('row_contains_active')}; "
                        f"third_row_contains_active={_row_focus_from_state(shift_tab_state, THIRD_WORKSPACE_DISPLAY_NAME).get('row_contains_active')}"
                    ),
                )

                current_step = 6
                current_action = AUTOMATION_STEPS[5]
                second_tab_out_state = _press_key_and_capture(
                    page=page,
                    key="Tab",
                    stability_ms=TAB_STABILITY_MS,
                )
                result["second_tab_out_state"] = second_tab_out_state
                _assert_panel_open_after_key(
                    key="Tab",
                    state=second_tab_out_state,
                    step_prefix="Step 6 failed",
                )
                _assert_tab_left_workspace_rows(
                    state=second_tab_out_state,
                    expected_selected=SECOND_WORKSPACE_DISPLAY_NAME,
                    inactive_names=(
                        FIRST_WORKSPACE_DISPLAY_NAME,
                        THIRD_WORKSPACE_DISPLAY_NAME,
                    ),
                    step_prefix="Step 6 failed",
                )
                _record_step(
                    result,
                    step=6,
                    status="passed",
                    action=AUTOMATION_STEPS[5],
                    observed=(
                        f"focused_after_second_tab={_active_from_state(second_tab_out_state).get('accessible_name')!r}; "
                        f"focused_role_after_second_tab={_active_from_state(second_tab_out_state).get('role')!r}; "
                        f"first_row_contains_active={_row_focus_from_state(second_tab_out_state, FIRST_WORKSPACE_DISPLAY_NAME).get('row_contains_active')}; "
                        f"third_row_contains_active={_row_focus_from_state(second_tab_out_state, THIRD_WORKSPACE_DISPLAY_NAME).get('row_contains_active')}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Pressed Tab again while the second row stayed selected and "
                        "confirmed keyboard navigation still skipped the inactive first and third rows."
                    ),
                    observed=(
                        f"focused_after_second_tab={_active_from_state(second_tab_out_state).get('accessible_name')!r}; "
                        f"first_tabindex={_button_from_state(second_tab_out_state, FIRST_WORKSPACE_DISPLAY_NAME).get('tabindex')!r}; "
                        f"third_tabindex={_button_from_state(second_tab_out_state, THIRD_WORKSPACE_DISPLAY_NAME).get('tabindex')!r}"
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
            page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
            result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
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


def _open_switcher_and_capture(page: LiveWorkspaceSwitcherPage) -> dict[str, object]:
    trigger = page.observe_trigger()
    switcher = page.open_and_observe()
    panel = page.observe_open_panel(expected_container_kinds=("anchored-panel", "surface"))
    rows = page.observe_saved_workspace_rows()
    active = page.active_element()
    focus = page.observe_focus_ownership(panel=panel)
    return _state_payload(
        trigger=trigger,
        switcher=switcher,
        panel=panel,
        active=active,
        focus=focus,
        saved_workspace_rows=rows,
        row_focus={},
        row_buttons={},
        monitor=None,
    )


def _focus_active_workspace_row_and_capture(
    *,
    page: LiveWorkspaceSwitcherPage,
    expected_selected: str,
) -> dict[str, object]:
    panel = page.observe_open_panel(
        expected_container_kinds=("anchored-panel", "surface"),
        timeout_ms=4_000,
    )
    rows = page.observe_saved_workspace_rows(timeout_ms=4_000)
    active_workspace = _selected_saved_workspace(rows)
    if active_workspace is None:
        raise AssertionError(
            "Step 2 failed: the open workspace switcher did not expose any selected "
            "saved workspace row before Arrow Down.\n"
            f"Observed rows: {json.dumps(_saved_workspace_rows_payload(rows), indent=2)}",
        )
    if active_workspace.display_name != expected_selected:
        raise AssertionError(
            "Step 2 failed: the initial saved workspace selection changed before the "
            "row-list focus precondition was established.\n"
            f"Observed active workspace: {active_workspace.display_name!r}\n"
            f"Observed rows: {json.dumps(_saved_workspace_rows_payload(rows), indent=2)}",
        )
    page.focus_switcher_button(
        _saved_workspace_row_focus_label(active_workspace),
        panel=panel,
        timeout_ms=4_000,
    )
    page.wait_for_surface_to_remain_open(
        stability_ms=KEY_STABILITY_MS,
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
    row_labels = {
        row.display_name: _saved_workspace_row_focus_label(row)
        for row in rows
        if row.display_name in WORKSPACE_NAMES
    }
    row_focus = {
        name: _row_focus_payload(
            page.observe_saved_workspace_row_focus(display_name=name, panel=panel),
        )
        for name in WORKSPACE_NAMES
    }
    row_buttons = {
        name: _button_focusability_payload(
            page.observe_switcher_button_focusability(row_labels[name], timeout_ms=4_000),
        )
        for name in WORKSPACE_NAMES
        if name in row_labels
    }
    for name, button in row_buttons.items():
        if name in row_focus:
            row_focus[name]["row_contains_active"] = bool(button.get("active_within"))
    state = _state_payload(
        trigger=None,
        switcher=switcher,
        panel=panel,
        active=active,
        focus=focus,
        saved_workspace_rows=rows,
        row_focus=row_focus,
        row_buttons=row_buttons,
        monitor=None,
    )
    state["row_labels"] = row_labels
    return state


def _press_key_and_capture(
    *,
    page: LiveWorkspaceSwitcherPage,
    key: str,
    stability_ms: int,
    expected_active_workspace: str | None = None,
) -> dict[str, object]:
    page.start_transition_monitor()
    page.press_key(key)
    page.wait_for_surface_to_remain_open(
        stability_ms=stability_ms,
        timeout_ms=4_000,
    )
    if expected_active_workspace is not None:
        page.wait_for_active_saved_workspace(
            expected_active_workspace,
            timeout_ms=10_000,
        )
    panel = page.observe_open_panel(
        expected_container_kinds=("anchored-panel", "surface"),
        timeout_ms=4_000,
    )
    switcher = page.observe_open_switcher(timeout_ms=4_000)
    rows = page.observe_saved_workspace_rows(timeout_ms=4_000)
    active = page.active_element()
    focus = page.observe_focus_ownership(panel=panel)
    row_labels = {
        row.display_name: _saved_workspace_row_focus_label(row)
        for row in rows
        if row.display_name in WORKSPACE_NAMES
    }
    row_focus = {
        name: _row_focus_payload(
            page.observe_saved_workspace_row_focus(display_name=name, panel=panel),
        )
        for name in WORKSPACE_NAMES
    }
    row_buttons = {
        name: _button_focusability_payload(
            page.observe_switcher_button_focusability(row_labels[name], timeout_ms=4_000),
        )
        for name in WORKSPACE_NAMES
        if name in row_labels
    }
    for name, button in row_buttons.items():
        if name in row_focus:
            row_focus[name]["row_contains_active"] = bool(button.get("active_within"))
    monitor = page.read_transition_monitor(clear=True)
    state = _state_payload(
        trigger=None,
        switcher=switcher,
        panel=panel,
        active=active,
        focus=focus,
        saved_workspace_rows=rows,
        row_focus=row_focus,
        row_buttons=row_buttons,
        monitor=monitor,
    )
    state["key"] = key
    state["row_labels"] = row_labels
    return state


def _assert_initial_switcher_state(state: dict[str, object]) -> None:
    rows = _saved_workspace_rows_from_state(state)
    if len(rows) < 3:
        raise AssertionError(
            "Step 1 failed: the visible workspace switcher did not expose at least "
            "three saved workspace rows needed for the roving-tabindex scenario.\n"
            f"Observed rows: {json.dumps(rows, indent=2)}",
        )
    if _active_workspace_name_from_state(state) != FIRST_WORKSPACE_DISPLAY_NAME:
        raise AssertionError(
            "Step 1 failed: the preloaded active saved workspace was not the expected "
            "first row before Arrow Down established the ticket precondition.\n"
            f"Observed active workspace: {_active_workspace_name_from_state(state)!r}\n"
            f"Observed rows: {json.dumps(rows, indent=2)}",
        )
    switcher = _switcher_from_state(state)
    panel = _panel_from_state(state)
    if "Workspace switcher" not in str(switcher.get("switcher_text", "")):
        raise AssertionError(
            "Step 1 failed: opening the workspace switcher did not expose the visible "
            "Workspace switcher title.\n"
            f"Observed switcher text:\n{switcher.get('switcher_text')}",
        )
    if str(panel.get("container_kind")) not in {"anchored-panel", "surface"}:
        raise AssertionError(
            "Step 1 failed: clicking the workspace switcher trigger did not open the "
            "expected desktop panel-style surface.\n"
            f"Observed panel: {json.dumps(panel, indent=2)}",
        )


def _assert_panel_open_after_key(
    *,
    key: str,
    state: dict[str, object],
    step_prefix: str,
) -> None:
    switcher = _switcher_from_state(state)
    panel = _panel_from_state(state)
    monitor = _monitor_from_state(state)
    rows = _saved_workspace_rows_from_state(state)
    failures: list[str] = []
    if not rows:
        failures.append("no visible saved workspace rows remained in the open switcher")
    if "Workspace switcher" not in str(switcher.get("switcher_text", "")):
        failures.append("the visible Workspace switcher title was not present")
    if str(panel.get("container_kind")) not in {"anchored-panel", "surface"}:
        failures.append("the visible surface was no longer the expected desktop workspace switcher panel")
    if bool(monitor.get("ever_hidden_after_visible")):
        failures.append(f"the transition monitor observed the panel become hidden after pressing {key}")
    if int(monitor.get("visible_sample_count", 0)) <= 0:
        failures.append(f"the transition monitor captured no visible switcher samples after pressing {key}")
    if failures:
        raise AssertionError(
            f"{step_prefix}: pressing {key} did not leave the workspace switcher visibly open.\n"
            + "\n".join(f"- {item}" for item in failures)
            + "\n"
            + f"Observed panel: {json.dumps(panel, indent=2)}\n"
            + f"Observed monitor: {json.dumps(monitor, indent=2)}"
        )


def _assert_selected_row_roving_state(
    *,
    state: dict[str, object],
    expected_selected: str,
    inactive_names: tuple[str, str],
    step_prefix: str,
    require_row_focus: bool,
) -> None:
    rows = _saved_workspace_rows_from_state(state)
    focus = _focus_from_state(state)
    active = _active_from_state(state)
    row_focus = {name: _row_focus_from_state(state, name) for name in WORKSPACE_NAMES}
    row_buttons = {name: _button_from_state(state, name) for name in WORKSPACE_NAMES}

    failures: list[str] = []
    if _active_workspace_name_from_state(state) != expected_selected:
        failures.append(
            f"the active saved workspace was {_active_workspace_name_from_state(state)!r} instead of {expected_selected!r}",
        )
    if not bool(focus.get("focus_owned_by_switcher")):
        failures.append("keyboard focus was not owned by the workspace switcher")
    if not bool(focus.get("active_within_switcher")):
        failures.append("the active element was not inside the open workspace switcher")
    if bool(focus.get("active_on_trigger")):
        failures.append("keyboard focus fell back to the workspace-switcher trigger")
    if require_row_focus and not _row_contains_active(state, expected_selected):
        failures.append(f"the selected row {expected_selected!r} did not contain the active element")
    for inactive_name in inactive_names:
        if _row_contains_active(state, inactive_name):
            failures.append(f"the inactive row {inactive_name!r} contained the active element")
    if str(active.get("role")) != "button":
        failures.append(
            f"the active element role was {active.get('role')!r} instead of 'button'",
        )
    _extend_roving_tabindex_failures(
        failures=failures,
        row_buttons=row_buttons,
        selected_name=expected_selected,
        inactive_names=inactive_names,
    )
    if failures:
        raise AssertionError(
            f"{step_prefix}: the workspace switcher did not expose a valid roving-tabindex "
            "state for the selected row.\n"
            + "\n".join(f"- {item}" for item in failures)
            + "\n"
            + f"Observed active element: {json.dumps(active, indent=2)}\n"
            + f"Observed focus ownership: {json.dumps(focus, indent=2)}\n"
            + f"Observed row focus: {json.dumps(row_focus, indent=2)}\n"
            + f"Observed row button focusability: {json.dumps(row_buttons, indent=2)}\n"
            + f"Observed rows: {json.dumps(rows, indent=2)}"
        )


def _assert_row_focus_precondition(
    *,
    state: dict[str, object],
    expected_selected: str,
    inactive_names: tuple[str, str],
    step_prefix: str,
) -> None:
    rows = _saved_workspace_rows_from_state(state)
    focus = _focus_from_state(state)
    active = _active_from_state(state)
    row_focus = {name: _row_focus_from_state(state, name) for name in WORKSPACE_NAMES}
    row_buttons = {name: _button_from_state(state, name) for name in WORKSPACE_NAMES}

    failures: list[str] = []
    if _active_workspace_name_from_state(state) != expected_selected:
        failures.append(
            f"the active saved workspace was {_active_workspace_name_from_state(state)!r} instead of {expected_selected!r}",
        )
    if not bool(focus.get("focus_owned_by_switcher")):
        failures.append("keyboard focus was not owned by the workspace switcher")
    if not bool(focus.get("active_within_switcher")):
        failures.append("the active element was not inside the open workspace switcher")
    if bool(focus.get("active_on_trigger")):
        failures.append("keyboard focus fell back to the workspace-switcher trigger")
    if not _row_contains_active(state, expected_selected):
        failures.append(f"the selected row {expected_selected!r} did not contain the active element")
    for inactive_name in inactive_names:
        if _row_contains_active(state, inactive_name):
            failures.append(f"the inactive row {inactive_name!r} contained the active element")
    if str(active.get("role")) != "button":
        failures.append(
            f"the active element role was {active.get('role')!r} instead of 'button'",
        )
    if failures:
        raise AssertionError(
            f"{step_prefix}: keyboard focus was not on the selected saved-workspace row before Arrow Down.\n"
            + "\n".join(f"- {item}" for item in failures)
            + "\n"
            + f"Observed active element: {json.dumps(active, indent=2)}\n"
            + f"Observed focus ownership: {json.dumps(focus, indent=2)}\n"
            + f"Observed row focus: {json.dumps(row_focus, indent=2)}\n"
            + f"Observed row button focusability: {json.dumps(row_buttons, indent=2)}\n"
            + f"Observed rows: {json.dumps(rows, indent=2)}"
        )


def _assert_tab_left_workspace_rows(
    *,
    state: dict[str, object],
    expected_selected: str,
    inactive_names: tuple[str, str],
    step_prefix: str,
) -> None:
    rows = _saved_workspace_rows_from_state(state)
    focus = _focus_from_state(state)
    active = _active_from_state(state)
    row_focus = {name: _row_focus_from_state(state, name) for name in WORKSPACE_NAMES}
    row_buttons = {name: _button_from_state(state, name) for name in WORKSPACE_NAMES}

    failures: list[str] = []
    if _active_workspace_name_from_state(state) != expected_selected:
        failures.append(
            f"the active saved workspace changed to {_active_workspace_name_from_state(state)!r} instead of remaining on {expected_selected!r}",
        )
    if bool(focus.get("active_on_trigger")):
        failures.append("keyboard focus jumped back to the workspace-switcher trigger")
    if str(active.get("tag_name")) in {"BODY", "HTML", "FLUTTER-VIEW"}:
        failures.append(
            f"focus landed on a non-interactive root element ({active.get('tag_name')!r}) instead of a visible subsequent control",
        )
    for name in WORKSPACE_NAMES:
        if _row_contains_active(state, name):
            failures.append(f"focus remained inside saved workspace row {name!r} after pressing Tab")
    _extend_roving_tabindex_failures(
        failures=failures,
        row_buttons=row_buttons,
        selected_name=expected_selected,
        inactive_names=inactive_names,
    )
    if failures:
        raise AssertionError(
            f"{step_prefix}: pressing Tab from the selected second row did not bypass the "
            "inactive workspace rows.\n"
            + "\n".join(f"- {item}" for item in failures)
            + "\n"
            + f"Observed active element: {json.dumps(active, indent=2)}\n"
            + f"Observed focus ownership: {json.dumps(focus, indent=2)}\n"
            + f"Observed row focus: {json.dumps(row_focus, indent=2)}\n"
            + f"Observed row button focusability: {json.dumps(row_buttons, indent=2)}\n"
            + f"Observed rows: {json.dumps(rows, indent=2)}"
        )


def _extend_roving_tabindex_failures(
    *,
    failures: list[str],
    row_buttons: dict[str, dict[str, object]],
    selected_name: str,
    inactive_names: tuple[str, str],
) -> None:
    selected_button = row_buttons.get(selected_name, {})
    if not selected_button:
        failures.append(f"no focusability observation was captured for the selected row {selected_name!r}")
    else:
        if not bool(selected_button.get("keyboard_focusable")):
            failures.append(f"the selected row {selected_name!r} was not sequentially keyboard-focusable")
        if selected_button.get("tabindex") == "-1":
            failures.append(f"the selected row {selected_name!r} incorrectly kept tabindex='-1'")
    for inactive_name in inactive_names:
        inactive_button = row_buttons.get(inactive_name, {})
        if not inactive_button:
            failures.append(f"no focusability observation was captured for inactive row {inactive_name!r}")
            continue
        if inactive_button.get("tabindex") != "-1":
            failures.append(
                f"the inactive row {inactive_name!r} had tabindex={inactive_button.get('tabindex')!r} instead of '-1'",
            )
        if bool(inactive_button.get("keyboard_focusable")):
            failures.append(f"the inactive row {inactive_name!r} remained sequentially keyboard-focusable")


def _state_payload(
    *,
    trigger: WorkspaceSwitcherTriggerObservation | None,
    switcher: WorkspaceSwitcherObservation,
    panel: WorkspaceSwitcherPanelObservation,
    active: FocusedElementObservation,
    focus: WorkspaceSwitcherFocusOwnershipObservation,
    saved_workspace_rows: tuple[WorkspaceSwitcherSavedWorkspaceRowObservation, ...],
    row_focus: dict[str, dict[str, object]],
    row_buttons: dict[str, dict[str, object]],
    monitor: WorkspaceSwitcherTransitionMonitorObservation | None,
) -> dict[str, object]:
    active_workspace = _selected_saved_workspace(saved_workspace_rows)
    payload: dict[str, object] = {
        "switcher": _switcher_payload(switcher),
        "panel": asdict(panel),
        "active": _focused_element_payload(active),
        "focus": _focus_ownership_payload(focus),
        "saved_workspace_rows": _saved_workspace_rows_payload(saved_workspace_rows),
        "active_workspace_name": (
            active_workspace.display_name if active_workspace is not None else None
        ),
        "row_focus": row_focus,
        "row_buttons": row_buttons,
    }
    if trigger is not None:
        payload["trigger"] = _trigger_payload(trigger)
    if monitor is not None:
        payload["monitor"] = _monitor_payload(monitor)
    return payload


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
    REVIEW_REPLIES_PATH.write_text(
        _review_replies_payload(result, passed=True),
        encoding="utf-8",
    )


def _write_failure_outputs(result: dict[str, object]) -> None:
    error = str(result.get("error", "AssertionError: TS-867 failed"))
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
    jira_comment = _jira_comment(result, passed=False)
    markdown_summary = _markdown_summary(result, passed=False)
    JIRA_COMMENT_PATH.write_text(jira_comment, encoding="utf-8")
    PR_BODY_PATH.write_text(markdown_summary, encoding="utf-8")
    RESPONSE_PATH.write_text(_response_summary(result, passed=False), encoding="utf-8")
    REVIEW_REPLIES_PATH.write_text(
        _review_replies_payload(result, passed=False),
        encoding="utf-8",
    )
    BUG_DESCRIPTION_PATH.write_text(_bug_description(result), encoding="utf-8")


def _jira_comment(result: dict[str, object], *, passed: bool) -> str:
    status = "PASSED" if passed else "FAILED"
    lines = [
        f"h3. {status} — {TICKET_KEY} automation",
        "",
        f"*Test case*: *{TICKET_KEY} - {TEST_CASE_TITLE}*",
        f"*Result*: *{status}*",
        (
            f"*Environment*: URL {{{{{result['app_url']}}}}}, repository "
            f"{{{{{result['repository']}}}}} @ {{{{{result['repository_ref']}}}}}, "
            f"browser {{Chromium (Playwright)}}, OS {{{{{result['os']}}}}}"
        ),
        f"*Run command*: {{code}}{result['run_command']}{{code}}",
        "",
        "h4. What automation checked",
    ]
    lines.extend(f"# {step['action']} — *{step['status'].upper()}*: {step['observed']}" for step in _steps(result))
    lines.extend(
        [
            "",
            "h4. Human-style verification",
        ],
    )
    lines.extend(
        f"# {item['check']} — {item['observed']}" for item in _human_verification(result)
    )
    lines.extend(
        [
            "",
            "h4. Expected result",
            EXPECTED_RESULT,
            "",
            "h4. Observed outcome",
            (
                "Matched the expected roving-tabindex behavior: only the selected second "
                "workspace row stayed in the Tab order, Shift+Tab returned directly to it, "
                "and inactive rows remained bypassed."
                if passed
                else _actual_vs_expected_summary(result)
            ),
        ],
    )
    if not passed:
        lines.extend(
            [
                "",
                "h4. Failure details",
                f"*Failed step*: {_failed_step_label(result)}",
                f"*Error*: {{code}}{result.get('error')}{{code}}",
            ],
        )
    screenshot = result.get("screenshot")
    if screenshot:
        lines.extend(["", f"*Screenshot*: {{{{{screenshot}}}}}"])
    return "\n".join(lines) + "\n"


def _markdown_summary(result: dict[str, object], *, passed: bool) -> str:
    status = "PASSED" if passed else "FAILED"
    lines = [
        f"# {TICKET_KEY} — {status}",
        "",
        f"**Test case:** {TEST_CASE_TITLE}",
        f"**Result:** {status}",
        (
            f"**Environment:** `{result['app_url']}` · `{result['repository']}` @ "
            f"`{result['repository_ref']}` · `Chromium (Playwright)` · `{result['os']}`"
        ),
        f"**Run command:** `{result['run_command']}`",
        "",
        "## What automation checked",
    ]
    lines.extend(f"1. {step['action']} — **{step['status'].upper()}**: {step['observed']}" for step in _steps(result))
    lines.extend(["", "## Human-style verification"])
    lines.extend(f"1. {item['check']} — {item['observed']}" for item in _human_verification(result))
    lines.extend(
        [
            "",
            "## Expected result",
            EXPECTED_RESULT,
            "",
            "## Observed outcome",
            (
                "Matched the expected roving-tabindex behavior: the selected second row was "
                "the only saved-workspace row in the sequential Tab order, Shift+Tab re-entered "
                "the list on that same row, and repeated Tab navigation never reached the inactive rows."
                if passed
                else _actual_vs_expected_summary(result)
            ),
        ],
    )
    if not passed:
        lines.extend(
            [
                "",
                "## Failure details",
                f"- **Failed step:** {_failed_step_label(result)}",
                f"- **Error:** `{result.get('error')}`",
                f"- **Screenshot:** `{result.get('screenshot')}`" if result.get("screenshot") else "- **Screenshot:** not captured",
            ],
        )
    elif result.get("screenshot"):
        lines.extend(["", f"**Screenshot:** `{result['screenshot']}`"])
    return "\n".join(lines) + "\n"


def _response_summary(result: dict[str, object], *, passed: bool) -> str:
    status = "PASSED" if passed else "FAILED"
    return (
        f"# {TICKET_KEY} — {status}\n\n"
        f"- Test case: **{TEST_CASE_TITLE}**\n"
        f"- Environment: `{result['app_url']}` on Chromium/Playwright ({result['os']})\n"
        f"- Expected result: {EXPECTED_RESULT}\n"
        f"- Observed: {_actual_vs_expected_summary(result) if not passed else 'Matched the expected behavior.'}\n"
        f"- Screenshot: `{result.get('screenshot')}`\n"
    )


def _bug_description(result: dict[str, object]) -> str:
    screenshot = result.get("screenshot", "not captured")
    lines = [
        f"# {TICKET_KEY} — workspace switcher roving tabindex regression",
        "",
        "## Summary",
        _actual_vs_expected_summary(result),
        "",
        "## Exact steps to reproduce",
        _annotated_request_steps(result),
        "",
        "## Exact error message or assertion failure",
        "```text",
        str(result.get("error", "")),
        "",
        str(result.get("traceback", "")),
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
        f"- Run command: `{result.get('run_command')}`",
        "",
        "## Screenshots or logs",
        f"- Screenshot: `{screenshot}`",
        "- Step log:",
        "```json",
        json.dumps(_steps(result), indent=2),
        "```",
    ]
    return "\n".join(lines) + "\n"


def _annotated_request_steps(result: dict[str, object]) -> str:
    tab_out_state = result.get("tab_out_state")
    shift_tab_state = result.get("shift_tab_state")
    second_tab_out_state = result.get("second_tab_out_state")
    annotations = [
        (
            REQUEST_STEPS[0],
            _request_step_outcome(
                result=result,
                state=tab_out_state,
                success_step=4,
                success_observation=(
                    f"focus moved to {_active_label_for_summary(tab_out_state)!r}, outside the saved-workspace rows; "
                    f"row1_active={_row_focus_value(tab_out_state, FIRST_WORKSPACE_DISPLAY_NAME, 'row_contains_active')}; "
                    f"row2_active={_row_focus_value(tab_out_state, SECOND_WORKSPACE_DISPLAY_NAME, 'row_contains_active')}; "
                    f"row3_active={_row_focus_value(tab_out_state, THIRD_WORKSPACE_DISPLAY_NAME, 'row_contains_active')}"
                ),
            ),
        ),
        (
            REQUEST_STEPS[1],
            _request_step_outcome(
                result=result,
                state=shift_tab_state,
                success_step=5,
                success_observation=(
                    f"Shift+Tab restored focus to {_active_label_for_summary(shift_tab_state)!r}; "
                    f"second_row_contains_active={_row_focus_value(shift_tab_state, SECOND_WORKSPACE_DISPLAY_NAME, 'row_contains_active')}"
                ),
            ),
        ),
        (
            REQUEST_STEPS[2],
            _request_step_outcome(
                result=result,
                state=shift_tab_state,
                success_step=5,
                success_observation=(
                    f"focus returned to the selected second row {_active_label_for_summary(shift_tab_state)!r}, "
                    f"not to the first or third row"
                ),
            ),
        ),
        (
            REQUEST_STEPS[3],
            _request_step_outcome(
                result=result,
                state=second_tab_out_state,
                success_step=6,
                success_observation=(
                    f"pressing Tab again moved focus to {_active_label_for_summary(second_tab_out_state)!r}; "
                    f"row1_active={_row_focus_value(second_tab_out_state, FIRST_WORKSPACE_DISPLAY_NAME, 'row_contains_active')}; "
                    f"row3_active={_row_focus_value(second_tab_out_state, THIRD_WORKSPACE_DISPLAY_NAME, 'row_contains_active')}"
                ),
            ),
        ),
    ]
    return "\n".join(f"{index}. {step}\n   {annotation}" for index, (step, annotation) in enumerate(annotations, start=1))


def _request_step_outcome(
    *,
    result: dict[str, object],
    state: object,
    success_step: int,
    success_observation: str,
) -> str:
    if state is not None and _step_passed(result, success_step):
        return f"✅ {success_observation}"
    failed = next(
        (
            item
            for item in _steps(result)
            if item.get("step") == success_step and item.get("status") == "failed"
        ),
        None,
    )
    if isinstance(failed, dict):
        return f"❌ {failed.get('observed')}"
    if success_step > 1 and not _step_passed(result, success_step - 1):
        return "❌ Not reached because an earlier required automation step failed."
    return "❌ Not completed successfully in this run."


def _actual_vs_expected_summary(result: dict[str, object]) -> str:
    failed = next((step for step in _steps(result) if step["status"] == "failed"), None)
    if failed is None:
        return (
            "Only the selected second workspace row remained in the sequential Tab order, "
            "Shift+Tab returned directly to that row, and the inactive first and third "
            "rows stayed at tabindex='-1'."
        )
    return (
        f"{failed['action']} failed. {failed['observed']} "
        "As a result, the workspace switcher did not demonstrate the expected roving-tabindex behavior."
    )


def _failed_step_label(result: dict[str, object]) -> str:
    failed = next((step for step in _steps(result) if step["status"] == "failed"), None)
    if failed is None:
        return "No failed automation step recorded"
    return f"Step {failed['step']} — {failed['action']}"


def _review_replies_payload(result: dict[str, object], *, passed: bool) -> str:
    replies = [
        {
            "inReplyToId": thread.get("rootCommentId"),
            "threadId": thread.get("threadId"),
            "reply": _review_reply_text(passed=passed, result=result),
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


def _review_reply_text(*, passed: bool, result: dict[str, object]) -> str:
    rerun_summary = (
        f"Re-ran `{RUN_COMMAND}`: passed (`1 passed, 0 failed`)."
        if passed
        else (
            "Re-ran "
            f"`{RUN_COMMAND}`: still failing. Current failure: {_failed_step_summary(result)}"
        )
    )
    return (
        "Fixed: the test now adds an explicit row-list focus precondition before "
        "sending `ArrowDown`, asserts that the active first saved-workspace row owns "
        "keyboard focus before continuing, waits for the second row to become active "
        "after `ArrowDown`, and includes the missing `testing/tests/TS-867/README.md`. "
        f"{rerun_summary}"
    )


def _failed_step_summary(result: dict[str, object]) -> str:
    steps = result.get("steps", [])
    if isinstance(steps, list):
        for step in steps:
            if isinstance(step, dict) and step.get("status") != "passed":
                return f"Step {step.get('step')}: {step.get('observed')}"
    return str(result.get("error", "No failed step recorded."))


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


def _steps(result: dict[str, object]) -> list[dict[str, object]]:
    steps = result.get("steps", [])
    return steps if isinstance(steps, list) else []


def _step_passed(result: dict[str, object], step_number: int) -> bool:
    return any(
        step.get("step") == step_number and step.get("status") == "passed"
        for step in _steps(result)
    )


def _has_failed_step(result: dict[str, object]) -> bool:
    return any(step.get("status") == "failed" for step in _steps(result))


def _human_verification(result: dict[str, object]) -> list[dict[str, object]]:
    items = result.get("human_verification", [])
    return items if isinstance(items, list) else []


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


def _focused_element_payload(observation: FocusedElementObservation) -> dict[str, object]:
    return {
        "tag_name": observation.tag_name,
        "role": observation.role,
        "accessible_name": observation.accessible_name,
        "text": observation.text,
        "tabindex": observation.tabindex,
        "outer_html": observation.outer_html,
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


def _saved_workspace_rows_from_state(state: dict[str, object]) -> list[dict[str, object]]:
    rows = state.get("saved_workspace_rows", [])
    return rows if isinstance(rows, list) else []


def _active_workspace_name_from_state(state: dict[str, object]) -> object:
    return state.get("active_workspace_name")


def _switcher_from_state(state: dict[str, object]) -> dict[str, object]:
    switcher = state.get("switcher", {})
    return switcher if isinstance(switcher, dict) else {}


def _panel_from_state(state: dict[str, object]) -> dict[str, object]:
    panel = state.get("panel", {})
    return panel if isinstance(panel, dict) else {}


def _active_from_state(state: dict[str, object]) -> dict[str, object]:
    active = state.get("active", {})
    return active if isinstance(active, dict) else {}


def _focus_from_state(state: dict[str, object]) -> dict[str, object]:
    focus = state.get("focus", {})
    return focus if isinstance(focus, dict) else {}


def _row_focus_from_state(state: dict[str, object], display_name: str) -> dict[str, object]:
    row_focus = state.get("row_focus", {})
    if not isinstance(row_focus, dict):
        return {}
    candidate = row_focus.get(display_name, {})
    return candidate if isinstance(candidate, dict) else {}


def _button_from_state(state: dict[str, object], display_name: str) -> dict[str, object]:
    row_buttons = state.get("row_buttons", {})
    if not isinstance(row_buttons, dict):
        return {}
    candidate = row_buttons.get(display_name, {})
    return candidate if isinstance(candidate, dict) else {}


def _row_contains_active(state: dict[str, object], display_name: str) -> bool:
    button = _button_from_state(state, display_name)
    if "active_within" in button:
        return bool(button.get("active_within"))
    return bool(_row_focus_from_state(state, display_name).get("row_contains_active"))


def _monitor_from_state(state: dict[str, object]) -> dict[str, object]:
    monitor = state.get("monitor", {})
    return monitor if isinstance(monitor, dict) else {}


def _active_label_for_summary(state: object) -> object:
    if not isinstance(state, dict):
        return None
    return _active_from_state(state).get("accessible_name")


def _row_focus_value(state: object, display_name: str, key: str) -> object:
    if not isinstance(state, dict):
        return None
    return _row_focus_from_state(state, display_name).get(key)


def _snippet(text: str, limit: int = 160) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1] + "…"


if __name__ == "__main__":
    main()
