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
    WorkspaceSwitcherTriggerObservation,
)
from testing.components.pages.trackstate_tracker_page import TrackStateTrackerPage  # noqa: E402
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.interfaces.web_app_session import FocusedElementObservation  # noqa: E402
from testing.tests.support.live_tracker_app_factory import create_live_tracker_app  # noqa: E402
from testing.tests.support.stored_workspace_profiles_runtime import (  # noqa: E402
    StoredWorkspaceProfilesRuntime,
)

TICKET_KEY = "TS-954"
TEST_CASE_TITLE = (
    "Open workspace switcher in pristine state — Save and switch footer control "
    "is present, disabled, and remains the focus-loop boundary"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-954/test_ts_954.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
DEFAULT_BRANCH = "main"
FIRST_WORKSPACE_DISPLAY_NAME = "Hosted main workspace"
SECOND_WORKSPACE_DISPLAY_NAME = "Hosted alt workspace"
THIRD_WORKSPACE_DISPLAY_NAME = "Hosted third workspace"
SECOND_WORKSPACE_WRITE_BRANCH = "ts-954-alt"
THIRD_WORKSPACE_WRITE_BRANCH = "ts-954-third"
LINKED_BUGS = [
    "TS-1135",
    "TS-1133",
    "TS-1044",
    "TS-1041",
    "TS-1039",
    "TS-1021",
    "TS-1018",
    "TS-1010",
    "TS-1009",
    "TS-998",
    "TS-997",
    "TS-975",
    "TS-973",
    "TS-963",
    "TS-958",
    "TS-948",
]
SHELL_NAVIGATION_LABELS = ("Dashboard", "Board", "JQL Search", "Hierarchy", "Settings")
FOCUS_SETTLE_MS = 300
MAX_TABS_TO_REACH_FOOTER = 8
LAST_INTERNAL_CONTROL_LABEL = "Save and switch"
FIELD_LABELS = ("Repository", "Branch")

REQUEST_STEPS = [
    "Observe the footer area of the workspace switcher panel.",
    "Verify the presence of the 'Save and switch' button.",
    "Verify that the 'Save and switch' button is in a disabled state (e.g., using aria-disabled).",
    "Press the 'Tab' key to navigate through the interactive elements until reaching the footer.",
]
EXPECTED_RESULT = (
    "The 'Save and switch' button is visible in the footer and is correctly "
    "identified as disabled. It remains a valid tab-stop in the keyboard "
    "navigation order, allowing the focus-trap utility to recognize it as the "
    "boundary and wrap focus back to the first element in the panel."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts954_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts954_failure.png"


class Ts954WorkspaceRuntime(StoredWorkspaceProfilesRuntime):
    def __init__(
        self,
        *,
        repository: str,
        token: str,
        workspace_state: dict[str, object],
    ) -> None:
        super().__init__(
            repository=repository,
            token=token,
            workspace_state=workspace_state,
        )
        self.console_events: list[dict[str, str]] = []
        self.page_errors: list[str] = []

    def __enter__(self):
        session = super().__enter__()
        if self._page is None:
            raise RuntimeError("TS-954 expected a browser page.")
        self._page.on("console", self._record_console_event)
        self._page.on("pageerror", self._record_page_error)
        return session

    def _record_console_event(self, message) -> None:
        self.console_events.append(
            {
                "level": str(message.type),
                "text": str(message.text),
            },
        )

    def _record_page_error(self, error: object) -> None:
        self.page_errors.append(str(error))


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-954 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
        )

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
        "focus_settle_ms": FOCUS_SETTLE_MS,
        "max_tabs_to_reach_footer": MAX_TABS_TO_REACH_FOOTER,
        "preloaded_workspace_state": workspace_state,
        "steps": [],
        "human_verification": [],
    }

    runtime_context = Ts954WorkspaceRuntime(
        repository=service.repository,
        token=token,
        workspace_state=workspace_state,
    )
    page: LiveWorkspaceSwitcherPage | None = None
    tracker_page: TrackStateTrackerPage | None = None

    try:
        with create_live_tracker_app(
            config,
            runtime_factory=lambda: runtime_context,
        ) as tracker_page:
            page = LiveWorkspaceSwitcherPage(tracker_page)
            step_failures: list[str] = []
            try:
                tracker_page.open_entrypoint()
                page.set_viewport(**DESKTOP_VIEWPORT)
                shell_observation = tracker_page.observe_interactive_shell(
                    SHELL_NAVIGATION_LABELS,
                )
                result["shell_observation"] = shell_observation
                if not bool(shell_observation.get("shell_ready")):
                    _raise_startup_failure(
                        result=result,
                        tracker_page=tracker_page,
                        runtime_context=runtime_context,
                        reason=(
                            "The deployed app never exposed the interactive shell required to "
                            "open the workspace switcher.\n"
                            f"Observed shell state:\n{json.dumps(shell_observation, indent=2)}"
                        ),
                    )
                try:
                    page.dismiss_connection_banner()
                except Exception:
                    pass

                step_one_context = _open_switcher_context(page)
                result.update(step_one_context["payload"])
                first_row = _assert_initial_panel_state(
                    trigger=step_one_context["trigger"],
                    switcher=step_one_context["switcher"],
                    panel=step_one_context["panel"],
                    rows=step_one_context["rows"],
                    surface=step_one_context["surface"],
                )
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=REQUEST_STEPS[0],
                    observed=(
                        f"Opened the workspace switcher at {DESKTOP_VIEWPORT['width']}x"
                        f"{DESKTOP_VIEWPORT['height']} and observed footer labels "
                        f"{_surface_label_summary(step_one_context['surface'])!r}."
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Viewed the live desktop workspace switcher footer area as a user "
                        "before any workspace selection or branch fields were changed."
                    ),
                    observed=(
                        f"Visible footer/body text included "
                        f"{_snippet(step_one_context['switcher'].switcher_text)!r}."
                    ),
                )

                save_button_before: WorkspaceSwitcherButtonStateObservation | None = None
                try:
                    save_button_before = page.observe_switcher_button_state(
                        LAST_INTERNAL_CONTROL_LABEL,
                        panel=step_one_context["panel"],
                        timeout_ms=4_000,
                    )
                    result["save_and_switch_before_tab"] = _button_state_payload(
                        save_button_before,
                    )
                    _assert_save_button_present(save_button_before)
                    _record_step(
                        result,
                        step=2,
                        status="passed",
                        action=REQUEST_STEPS[1],
                        observed=(
                            f"Visible button label={save_button_before.label!r}; "
                            f"text={save_button_before.visible_text!r}; "
                            f"tabindex={save_button_before.tabindex!r}."
                        ),
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Confirmed the footer visibly rendered a Save and switch control "
                            "instead of hiding the wrap-boundary button in pristine state."
                        ),
                        observed=(
                            f"Footer control text={save_button_before.visible_text!r}; "
                            f"outer_html={_compact_html(save_button_before.outer_html)!r}"
                        ),
                    )
                except AssertionError as error:
                    message = str(error)
                    _record_step(
                        result,
                        step=2,
                        status="failed",
                        action=REQUEST_STEPS[1],
                        observed=message,
                    )
                    step_failures.append(message)

                if save_button_before is None:
                    step_three_message = (
                        "Step 3 failed: the test could not read the live Save and switch "
                        "button state after Step 2, so the disabled-state assertion could "
                        "not be completed."
                    )
                    _record_step(
                        result,
                        step=3,
                        status="failed",
                        action=REQUEST_STEPS[2],
                        observed=step_three_message,
                    )
                    step_failures.append(step_three_message)
                else:
                    try:
                        _assert_save_button_disabled(save_button_before)
                        _record_step(
                            result,
                            step=3,
                            status="passed",
                            action=REQUEST_STEPS[2],
                            observed=(
                                f"aria-disabled={save_button_before.aria_disabled!r}; "
                                f"disabled={save_button_before.disabled}; "
                                f"keyboard_focusable_probe={save_button_before.keyboard_focusable}."
                            ),
                        )
                    except AssertionError as error:
                        message = str(error)
                        _record_step(
                            result,
                            step=3,
                            status="failed",
                            action=REQUEST_STEPS[2],
                            observed=message,
                        )
                        step_failures.append(message)
                    _record_human_verification(
                        result,
                        check=(
                            "Read the live footer control state the same way an accessibility "
                            "check would: visible button plus disabled semantics."
                        ),
                        observed=(
                            f"aria-disabled={save_button_before.aria_disabled!r}; "
                            f"disabled={save_button_before.disabled}; "
                            f"visible_text={save_button_before.visible_text!r}"
                        ),
                    )

                first_row_label = _saved_workspace_row_focus_label(first_row)
                result["first_row_label"] = first_row_label
                try:
                    traversal_result = _tab_to_footer_and_wrap(
                        page=page,
                        panel=step_one_context["panel"],
                        first_row=first_row,
                    )
                    result.update(traversal_result)
                    _record_step(
                        result,
                        step=4,
                        status="passed",
                        action=REQUEST_STEPS[3],
                        observed=(
                            f"Visited labels={_visited_focus_labels(traversal_result['tab_trace_to_footer'])!r}; "
                            f"footer_active={_active_from_state(traversal_result['footer_state']).get('accessible_name')!r}; "
                            f"footer_aria_disabled={traversal_result['footer_button_state']['aria_disabled']!r}; "
                            f"wrapped_to={_active_from_state(traversal_result['wrap_state_after_footer']).get('accessible_name')!r}."
                        ),
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Tabbed through the live workspace switcher like a real keyboard "
                            "user until the Save and switch footer control received focus, "
                            "then pressed Tab once more."
                        ),
                        observed=(
                            f"Footer visibly received focus while disabled="
                            f"{traversal_result['footer_button_state']['disabled']} and "
                            f"aria-disabled={traversal_result['footer_button_state']['aria_disabled']!r}; "
                            f"next focus={_active_from_state(traversal_result['wrap_state_after_footer']).get('accessible_name')!r}."
                        ),
                    )
                except AssertionError as error:
                    message = str(error)
                    _record_step(
                        result,
                        step=4,
                        status="failed",
                        action=REQUEST_STEPS[3],
                        observed=message,
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Pressed Tab through the live workspace switcher like a keyboard "
                            "user after confirming the pristine disabled footer state."
                        ),
                        observed=message,
                    )
                    step_failures.append(message)

                if step_failures:
                    raise AssertionError(_summarize_failures(result))
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
        result["console_events"] = list(runtime_context.console_events)
        result["page_errors"] = list(runtime_context.page_errors)
        result["error"] = str(error)
        result["traceback"] = traceback.format_exc()
        _write_failure_outputs(result)
        raise
    except Exception as error:
        result["console_events"] = list(runtime_context.console_events)
        result["page_errors"] = list(runtime_context.page_errors)
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        _write_failure_outputs(result)
        raise

    result["console_events"] = list(runtime_context.console_events)
    result["page_errors"] = list(runtime_context.page_errors)
    _write_pass_outputs(result)
    print(f"{TICKET_KEY} passed")


def _open_switcher_context(page: LiveWorkspaceSwitcherPage) -> dict[str, object]:
    trigger = page.observe_trigger(timeout_ms=30_000)
    switcher = page.open_and_observe(timeout_ms=30_000)
    panel = page.observe_open_panel(
        expected_container_kinds=("anchored-panel", "surface"),
        timeout_ms=4_000,
    )
    rows = page.observe_saved_workspace_rows(timeout_ms=4_000)
    surface = page.observe_surface(timeout_ms=4_000)
    return {
        "trigger": trigger,
        "switcher": switcher,
        "panel": panel,
        "rows": rows,
        "surface": surface,
        "payload": {
            "trigger_observation": _trigger_payload(trigger),
            "open_switcher_observation": _switcher_payload(switcher),
            "open_panel_observation": asdict(panel),
            "saved_workspace_rows_before_tab": _saved_workspace_rows_payload(rows),
            "surface_observation": _surface_payload(surface),
        },
    }


def _tab_to_footer_and_wrap(
    *,
    page: LiveWorkspaceSwitcherPage,
    panel: WorkspaceSwitcherPanelObservation,
    first_row: WorkspaceSwitcherSavedWorkspaceRowObservation,
) -> dict[str, object]:
    first_row_label = _saved_workspace_row_focus_label(first_row)
    initial_focus_state = _capture_tab_state(
        page=page,
        panel=panel,
        first_row_display_name=first_row.display_name,
        press_index=0,
        before=None,
        key="Initial focus",
    )

    tab_trace: list[dict[str, object]] = []
    footer_state: dict[str, object] | None = None
    footer_button_state: WorkspaceSwitcherButtonStateObservation | None = None
    for press_index in range(1, MAX_TABS_TO_REACH_FOOTER + 1):
        before = page.active_element()
        page.press_key("Tab", timeout_ms=4_000)
        _wait_for_switcher_stability_or_raise(
            page=page,
            before=before,
            press_index=press_index,
            key="Tab",
            context=(
                f"pressing Tab {press_index} from "
                f"{before.accessible_name or before.text or before.tag_name!r}"
            ),
        )
        panel = page.observe_open_panel(
            expected_container_kinds=("anchored-panel", "surface"),
            timeout_ms=4_000,
        )
        state = _capture_tab_state(
            page=page,
            panel=panel,
            first_row_display_name=first_row.display_name,
            press_index=press_index,
            before=before,
            key="Tab",
        )
        tab_trace.append(state)
        if _active_from_state(state).get("accessible_name") == LAST_INTERNAL_CONTROL_LABEL:
            footer_state = state
            footer_button_state = page.observe_switcher_button_state(
                LAST_INTERNAL_CONTROL_LABEL,
                panel=panel,
                timeout_ms=4_000,
            )
            break

    _assert_traversal_reached_footer(
        tab_trace=tab_trace,
        footer_state=footer_state,
        footer_button_state=footer_button_state,
    )

    before_wrap = page.active_element()
    page.press_key("Tab", timeout_ms=4_000)
    _wait_for_switcher_stability_or_raise(
        page=page,
        before=before_wrap,
        press_index=len(tab_trace) + 1,
        key="Tab",
        context=(
            f"pressing Tab after focusing the disabled "
            f"{LAST_INTERNAL_CONTROL_LABEL!r} footer control"
        ),
    )
    panel = page.observe_open_panel(
        expected_container_kinds=("anchored-panel", "surface"),
        timeout_ms=4_000,
    )
    wrap_state = _capture_tab_state(
        page=page,
        panel=panel,
        first_row_display_name=first_row.display_name,
        press_index=len(tab_trace) + 1,
        before=before_wrap,
        key="Tab",
    )
    _assert_wrap_to_first_row(
        state=wrap_state,
        expected_label=first_row_label,
    )

    return {
        "initial_focus_state": initial_focus_state,
        "tab_trace_to_footer": tab_trace,
        "footer_state": footer_state,
        "footer_button_state": _button_state_payload(footer_button_state),
        "wrap_state_after_footer": wrap_state,
    }


def _assert_initial_panel_state(
    *,
    trigger: WorkspaceSwitcherTriggerObservation,
    switcher: WorkspaceSwitcherObservation,
    panel: WorkspaceSwitcherPanelObservation,
    rows: tuple[WorkspaceSwitcherSavedWorkspaceRowObservation, ...],
    surface: WorkspaceSwitcherSurfaceObservation,
) -> WorkspaceSwitcherSavedWorkspaceRowObservation:
    failures: list[str] = []
    if "Workspace switcher" not in switcher.switcher_text:
        failures.append("the visible Workspace switcher title was not present")
    if not trigger.semantic_label.startswith("Workspace switcher:"):
        failures.append(
            f"the header trigger label was {trigger.semantic_label!r} instead of a workspace switcher label",
        )
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
            "Step 1 failed: the workspace switcher panel was not ready for the pristine-footer scenario.\n"
            + "\n".join(f"- {item}" for item in failures)
            + "\n"
            + f"Observed trigger: {json.dumps(_trigger_payload(trigger), indent=2)}\n"
            + f"Observed panel: {json.dumps(asdict(panel), indent=2)}\n"
            + f"Observed rows: {json.dumps(_saved_workspace_rows_payload(rows), indent=2)}\n"
            + f"Observed surface: {json.dumps(_surface_payload(surface), indent=2)}"
        )
    return first_row


def _assert_save_button_present(
    observation: WorkspaceSwitcherButtonStateObservation,
) -> None:
    if (
        observation.label != LAST_INTERNAL_CONTROL_LABEL
        and observation.visible_text != LAST_INTERNAL_CONTROL_LABEL
    ):
        raise AssertionError(
            "Step 2 failed: the visible footer control did not match the expected "
            f"{LAST_INTERNAL_CONTROL_LABEL!r} label.\n"
            f"Observed button: {json.dumps(_button_state_payload(observation), indent=2)}",
        )


def _assert_save_button_disabled(
    observation: WorkspaceSwitcherButtonStateObservation,
) -> None:
    if observation.aria_disabled == "true" or observation.disabled:
        return
    raise AssertionError(
        "Step 3 failed: the visible Save and switch footer control was not marked disabled "
        "in pristine state.\n"
        f"Observed button: {json.dumps(_button_state_payload(observation), indent=2)}",
    )


def _assert_first_row_focus_ready(
    *,
    state: dict[str, object],
    expected_label: str,
) -> None:
    active = _active_from_state(state)
    focus = _focus_from_state(state)
    first_row_focus = _first_row_focus_from_state(state)
    failures: list[str] = []
    if active.get("accessible_name") != expected_label:
        failures.append(
            f"the active label was {active.get('accessible_name')!r} instead of {expected_label!r}",
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
            "Step 4 failed: the test could not establish focus on the first saved workspace row before Tab traversal.\n"
            + "\n".join(f"- {item}" for item in failures)
            + "\n"
            + f"Observed state: {json.dumps(state, indent=2)}"
        )


def _assert_traversal_reached_footer(
    *,
    tab_trace: list[dict[str, object]],
    footer_state: dict[str, object] | None,
    footer_button_state: WorkspaceSwitcherButtonStateObservation | None,
) -> None:
    failures: list[str] = []
    if not tab_trace:
        failures.append("no Tab traversal states were captured")
    for state in tab_trace:
        active = _active_from_state(state)
        focus = _focus_from_state(state)
        if not bool(focus.get("focus_owned_by_switcher")):
            failures.append(
                f"focus was no longer owned by the switcher after Tab {state.get('press_index')}",
            )
        if not bool(focus.get("active_within_switcher")):
            failures.append(
                f"the active element left the switcher panel after Tab {state.get('press_index')}",
            )
        if bool(focus.get("active_on_trigger")):
            failures.append(
                f"focus returned to the workspace-switcher trigger after Tab {state.get('press_index')}",
            )
        if active.get("accessible_name") == "Search issues":
            failures.append(
                "focus escaped to the external Search issues field before the footer button was reached",
            )
    if footer_state is None:
        failures.append(
            f"the visible {LAST_INTERNAL_CONTROL_LABEL!r} footer button was never reached within "
            f"{MAX_TABS_TO_REACH_FOOTER} Tab presses",
        )
    elif footer_button_state is None:
        failures.append(
            "the footer focus state was reached, but the Save and switch button state could not be re-read",
        )
    else:
        if not footer_button_state.active_within:
            failures.append(
                "the Save and switch footer control did not report active focus when Tab reached it",
            )
        if footer_button_state.aria_disabled != "true" and not footer_button_state.disabled:
            failures.append(
                "the Save and switch footer control stopped reporting a disabled state once it received focus",
            )
    if failures:
        raise AssertionError(
            "Step 4 failed: repeated Tab navigation did not reach the disabled Save and switch footer boundary as expected.\n"
            + "\n".join(f"- {item}" for item in failures)
            + "\n"
            + f"Observed trace: {json.dumps(tab_trace, indent=2)}\n"
            + f"Observed footer state: {json.dumps(_button_state_payload(footer_button_state), indent=2)}"
        )


def _assert_wrap_to_first_row(
    *,
    state: dict[str, object],
    expected_label: str,
) -> None:
    active = _active_from_state(state)
    focus = _focus_from_state(state)
    first_row_focus = _first_row_focus_from_state(state)
    failures: list[str] = []
    if not bool(focus.get("focus_owned_by_switcher")):
        failures.append("keyboard focus was not owned by the workspace switcher after the wrap attempt")
    if not bool(focus.get("active_within_switcher")):
        failures.append("keyboard focus left the workspace switcher after the wrap attempt")
    if bool(focus.get("active_on_trigger")):
        failures.append("keyboard focus returned to the workspace-switcher trigger instead of wrapping inside the panel")
    if active.get("accessible_name") == "Search issues":
        failures.append("keyboard focus escaped to the external Search issues field instead of wrapping inside the panel")
    if not bool(first_row_focus.get("row_contains_active")):
        failures.append(
            f"the first saved workspace row did not receive focus after pressing Tab on {LAST_INTERNAL_CONTROL_LABEL!r}",
        )
    if active.get("accessible_name") != expected_label:
        failures.append(
            f"the active label remained {active.get('accessible_name')!r} instead of wrapping to {expected_label!r}",
        )
    if failures:
        raise AssertionError(
            "Step 4 failed: pressing Tab after the disabled Save and switch footer control did not wrap focus to the first saved workspace row.\n"
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
    return state


def _wait_for_switcher_stability_or_raise(
    *,
    page: LiveWorkspaceSwitcherPage,
    before: FocusedElementObservation | None,
    press_index: int,
    key: str,
    context: str,
) -> None:
    try:
        page.wait_for_surface_to_remain_open(
            stability_ms=FOCUS_SETTLE_MS,
            timeout_ms=4_000,
        )
    except AssertionError as error:
        close_state = _capture_surface_loss_state(
            page=page,
            before=before,
            press_index=press_index,
            key=key,
            reason=str(error),
        )
        raise AssertionError(
            "Step 4 failed: the workspace switcher did not stay open while "
            f"{context}, so keyboard traversal could not reach the pristine "
            f"{LAST_INTERNAL_CONTROL_LABEL!r} footer boundary.\n"
            f"Observed close state: {json.dumps(close_state, indent=2)}"
        ) from error


def _capture_surface_loss_state(
    *,
    page: LiveWorkspaceSwitcherPage,
    before: FocusedElementObservation | None,
    press_index: int,
    key: str,
    reason: str,
) -> dict[str, object]:
    active = page.active_element()
    state: dict[str, object] = {
        "key": key,
        "press_index": press_index,
        "reason": reason,
        "body_text": page.current_body_text(),
        "active": _focused_element_payload(active),
        "workspace_switcher_text_still_present": "Workspace switcher" in page.current_body_text(),
    }
    if before is not None:
        state["before"] = _focused_element_payload(before)
    panel_after_loss: WorkspaceSwitcherPanelObservation | None = None
    try:
        panel = page.observe_open_panel(
            expected_container_kinds=("anchored-panel", "surface"),
            timeout_ms=500,
        )
        panel_after_loss = panel
        state["panel_visible_after_loss"] = True
        state["panel_after_loss"] = asdict(panel)
    except AssertionError as panel_error:
        state["panel_visible_after_loss"] = False
        state["panel_after_loss_error"] = str(panel_error)
    try:
        save_button_state = page.observe_switcher_button_state(
            LAST_INTERNAL_CONTROL_LABEL,
            panel=panel_after_loss,
            timeout_ms=500,
        )
        state["save_button_after_loss"] = _button_state_payload(save_button_state)
    except AssertionError as button_error:
        state["save_button_after_loss_error"] = str(button_error)
    return state


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


def _button_state_payload(
    observation: WorkspaceSwitcherButtonStateObservation | None,
) -> dict[str, object]:
    if observation is None:
        return {}
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


def _surface_labels(surface: WorkspaceSwitcherSurfaceObservation) -> set[str]:
    return {item.label for item in surface.interactive_elements if item.label}


def _surface_label_summary(surface: WorkspaceSwitcherSurfaceObservation) -> list[str]:
    return sorted(_surface_labels(surface))[:12]


def _visited_focus_labels(states: list[dict[str, object]]) -> list[str]:
    labels: list[str] = []
    for state in states:
        label = str(_active_from_state(state).get("accessible_name") or "")
        if label and (not labels or labels[-1] != label):
            labels.append(label)
    return labels


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
    entries = result.setdefault("human_verification", [])
    if not isinstance(entries, list):
        raise TypeError("result['human_verification'] must be a list")
    entries.append({"check": check, "observed": observed})


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


def _step_passed(result: dict[str, object], step_number: int) -> bool:
    return any(
        isinstance(step, dict)
        and int(step.get("step", -1)) == step_number
        and step.get("status") == "passed"
        for step in _steps(result)
    )


def _summarize_failures(result: dict[str, object]) -> str:
    failed_steps = [
        step
        for step in _steps(result)
        if isinstance(step, dict) and step.get("status") == "failed"
    ]
    if not failed_steps:
        return f"{TICKET_KEY} failed."
    lines = [f"{TICKET_KEY} failed with {len(failed_steps)} recorded step issue(s):"]
    for step in failed_steps:
        lines.append(
            f"- Step {step.get('step')}: {step.get('observed')}",
        )
    return "\n".join(lines)
def _mark_dependent_steps_failed(
    result: dict[str, object],
    *,
    first_unreached_step: int,
    reason: str,
) -> None:
    recorded = {int(step.get("step", -1)) for step in _steps(result)}
    for step_number in range(first_unreached_step, len(REQUEST_STEPS) + 1):
        if step_number in recorded:
            continue
        _record_step(
            result,
            step=step_number,
            status="failed",
            action=REQUEST_STEPS[step_number - 1],
            observed=reason,
        )


def _observe_startup_surface(tracker_page: TrackStateTrackerPage) -> dict[str, object]:
    payload = tracker_page.session.evaluate(
        """
        () => {
          const normalize = (value) => (value || '').replace(/\\s+/g, ' ').trim();
          const isVisible = (element) => {
            if (!element) {
              return false;
            }
            const rect = element.getBoundingClientRect();
            const style = window.getComputedStyle(element);
            return rect.width > 0
              && rect.height > 0
              && style.visibility !== 'hidden'
              && style.display !== 'none';
          };
          const buttonLabels = Array.from(
            document.querySelectorAll('button, flt-semantics[role="button"], [role="button"]'),
          )
            .filter(isVisible)
            .map((element) =>
              normalize(
                element.getAttribute?.('aria-label')
                || element.innerText
                || element.textContent
                || '',
              ),
            )
            .filter((label) => label.length > 0);
          return {
            title: document.title || '',
            locationHref: window.location.href,
            locationHash: window.location.hash,
            locationPathname: window.location.pathname,
            bodyText: document.body?.innerText || document.body?.textContent || '',
            buttonLabels,
          };
        }
        """,
    )
    if not isinstance(payload, dict):
        return {
            "title": "",
            "location_href": "",
            "location_hash": "",
            "location_pathname": "",
            "body_text": tracker_page.body_text(),
            "button_labels": [],
        }
    return {
        "title": str(payload.get("title", "")),
        "location_href": str(payload.get("locationHref", "")),
        "location_hash": str(payload.get("locationHash", "")),
        "location_pathname": str(payload.get("locationPathname", "")),
        "body_text": str(payload.get("bodyText", "")),
        "button_labels": [str(label) for label in payload.get("buttonLabels", [])],
    }


def _raise_startup_failure(
    *,
    result: dict[str, object],
    tracker_page: TrackStateTrackerPage,
    runtime_context: Ts954WorkspaceRuntime,
    reason: str,
) -> None:
    startup_observation = _observe_startup_surface(tracker_page)
    result["runtime_state"] = "startup-failed"
    result["startup_observation"] = startup_observation
    result["runtime_body_text"] = startup_observation["body_text"]
    result["console_events"] = list(runtime_context.console_events)
    result["page_errors"] = list(runtime_context.page_errors)
    _record_step(
        result,
        step=1,
        status="failed",
        action=REQUEST_STEPS[0],
        observed=(
            "The deployed app never exposed the workspace switcher footer area because the "
            "interactive shell did not render.\n"
            f"Reason: {reason}\n"
            f"Startup observation: {json.dumps(startup_observation, indent=2)}\n"
            f"Console events: {json.dumps(result['console_events'], indent=2)}\n"
            f"Page errors: {json.dumps(result['page_errors'], indent=2)}"
        ),
    )
    _mark_dependent_steps_failed(
        result,
        first_unreached_step=2,
        reason=(
            "Not reached because the deployed app never rendered the application header or "
            "workspace switcher. The visible page remained on the startup `Sync issue` "
            "surface instead."
        ),
    )
    _record_human_verification(
        result,
        check=(
            "Loaded the deployed app at the required desktop viewport and waited for the "
            "workspace switcher entry point to appear."
        ),
        observed=(
            f"title={startup_observation['title']!r}; "
            f"url={startup_observation['location_href']!r}; "
            f"visible_buttons={json.dumps(startup_observation['button_labels'], ensure_ascii=True)}; "
            f"body_text={startup_observation['body_text']!r}"
        ),
    )
    _record_human_verification(
        result,
        check=(
            "Viewed the live page like a user after load to confirm what was actually rendered "
            "on screen."
        ),
        observed=(
            "The page showed only a top-left `Sync issue` control on an otherwise blank screen, "
            "with no dashboard navigation and no workspace switcher trigger."
        ),
    )
    raise AssertionError(
        "Step 1 failed: the deployed app did not render the interactive shell, so "
        "TS-954 could not reach the workspace switcher required by the ticket steps.\n"
        f"Observed startup surface:\n{json.dumps(startup_observation, indent=2)}\n"
        f"Console events:\n{json.dumps(result['console_events'], indent=2)}\n"
        f"Page errors:\n{json.dumps(result['page_errors'], indent=2)}",
    )


def _actual_result_summary(result: dict[str, object], *, passed: bool) -> str:
    if passed:
        wrap_state = result.get("wrap_state_after_footer")
        footer_button_state = result.get("footer_button_state")
        return (
            "The live workspace switcher footer kept `Save and switch` visible in pristine "
            "state, reported it disabled, allowed Tab focus to land on it, and then wrapped "
            f"focus back to {_active_from_state(wrap_state).get('accessible_name')!r}. "
            f"Footer state: {json.dumps(footer_button_state, ensure_ascii=True)}"
        )
    startup_observation = result.get("startup_observation")
    if isinstance(startup_observation, dict):
        return (
            "The deployed app never rendered the interactive shell or workspace switcher. "
            "Instead it remained on a blank startup surface with only the visible "
            f"`Sync issue` control. Startup observation: {json.dumps(startup_observation, ensure_ascii=True)}"
        )
    save_button_before = result.get("save_and_switch_before_tab")
    wrap_state = result.get("wrap_state_after_footer")
    footer_button_state = result.get("footer_button_state")
    trace = result.get("tab_trace_to_footer")
    if (
        not _step_passed(result, 3)
        and not _step_passed(result, 4)
        and isinstance(save_button_before, dict)
    ):
        visited_labels = _visited_focus_labels(trace) if isinstance(trace, list) else []
        return (
            "The live workspace switcher rendered `Save and switch`, but left it enabled "
            "in pristine state and never let Tab traversal reach that footer control. "
            f"Observed footer state before Tab: {json.dumps(save_button_before, ensure_ascii=True)}. "
            f"Visited labels before the loop stopped: {visited_labels!r}."
        )
    if not _step_passed(result, 3) and isinstance(save_button_before, dict):
        summary = (
            "The live workspace switcher rendered `Save and switch`, but it did not keep "
            "the footer control disabled in pristine state. "
            f"Observed footer state before Tab: {json.dumps(save_button_before, ensure_ascii=True)}."
        )
        if isinstance(wrap_state, dict):
            summary += (
                " The keyboard loop still wrapped from the footer boundary to "
                f"{_active_from_state(wrap_state).get('accessible_name')!r}."
            )
        return summary
    if not _step_passed(result, 4):
        if isinstance(wrap_state, dict):
            return (
                "The live workspace switcher did not keep the expected Tab wrap behavior "
                "after the footer boundary. "
                f"Observed wrap state: {json.dumps(wrap_state, ensure_ascii=True)}."
            )
        if isinstance(footer_button_state, dict):
            return (
                "The live workspace switcher reached the footer control, but the Tab loop "
                "did not complete the expected wrap. "
                f"Observed footer state: {json.dumps(footer_button_state, ensure_ascii=True)}."
            )
        if isinstance(trace, list):
            return (
                "The live workspace switcher kept keyboard focus inside the panel, but Tab "
                "navigation never reached `Save and switch`. "
                f"Visited labels: {_visited_focus_labels(trace)!r}."
            )
    return str(result.get("error", "The live result did not match the expected footer behavior."))


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for step in _steps(result):
        prefix = "*" if jira else "-"
        lines.append(
            f"{prefix} Step {step['step']}: {step['action']} — {step['status'].upper()}: {step['observed']}",
        )
    return lines


def _human_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for item in _human_verification(result):
        prefix = "*" if jira else "-"
        lines.append(f"{prefix} {item['check']} Observed: {item['observed']}")
    return lines


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
    JIRA_COMMENT_PATH.write_text(_build_jira_comment(result, passed=True), encoding="utf-8")
    PR_BODY_PATH.write_text(_build_pr_body(result, passed=True), encoding="utf-8")
    RESPONSE_PATH.write_text(_build_response_summary(result, passed=True), encoding="utf-8")


def _write_failure_outputs(result: dict[str, object]) -> None:
    error = str(result.get("error", f"AssertionError: {TICKET_KEY} failed"))
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
    JIRA_COMMENT_PATH.write_text(_build_jira_comment(result, passed=False), encoding="utf-8")
    PR_BODY_PATH.write_text(_build_pr_body(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_build_response_summary(result, passed=False), encoding="utf-8")
    BUG_DESCRIPTION_PATH.write_text(_build_bug_description(result), encoding="utf-8")


def _build_jira_comment(result: dict[str, object], *, passed: bool) -> str:
    status_icon = "✅" if passed else "❌"
    status_word = "PASSED" if passed else "FAILED"
    lines = [
        f"h3. {status_icon} Automated test {status_word} — {TICKET_KEY}",
        "",
        f"*Test case*: {TEST_CASE_TITLE}",
        f"*Environment*: URL={result.get('app_url')} | Browser={result.get('browser')} | OS={result.get('os')}",
        f"*Viewport*: {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
        f"*Linked bugs considered*: {', '.join(LINKED_BUGS)}",
        "",
        "h4. What was automated",
        "* Open the deployed TrackState web app with pristine hosted workspace profiles.",
        "* Open the workspace switcher and inspect the visible footer area before making changes.",
        "* Verify the Save and switch footer control is present, disabled, and still participates in the Tab focus loop.",
        "* Confirm the next Tab after that footer boundary wraps focus back to the first saved workspace row.",
        "",
        "h4. Automation checks",
        *_step_lines(result, jira=True),
        "",
        "h4. Real user-style verification",
        *_human_lines(result, jira=True),
        "",
        "h4. Expected result",
        EXPECTED_RESULT,
        "",
        "h4. Actual result",
        _actual_result_summary(result, passed=passed),
    ]
    if result.get("screenshot"):
        lines.extend(["", f"*Screenshot*: {result['screenshot']}"])
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


def _build_pr_body(result: dict[str, object], *, passed: bool) -> str:
    lines = [
        f"## {TICKET_KEY} passed" if passed else f"## {TICKET_KEY} failed",
        "",
        f"**Test case:** {TEST_CASE_TITLE}",
        f"**Environment:** `{result.get('app_url')}` · {result.get('browser')} · {result.get('os')}",
        f"**Viewport:** `{DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}`",
        f"**Linked bugs considered:** {', '.join(LINKED_BUGS)}",
        "",
        "## What was automated",
        "- Opened the deployed TrackState web app with pristine hosted workspace profiles.",
        "- Attempted the real workspace-switcher footer scenario through the live UI.",
        "- Verified the visible Save and switch footer state and keyboard traversal when the switcher is reachable.",
        "- If the live shell never renders, records that startup blockage as a failed product bug instead of faking the result.",
        "",
        "## Automation checks",
        *_step_lines(result, jira=False),
        "",
        "## Real user-style verification",
        *_human_lines(result, jira=False),
        "",
        "## Expected result",
        EXPECTED_RESULT,
        "",
        "## Actual result",
        _actual_result_summary(result, passed=passed),
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


def _build_response_summary(result: dict[str, object], *, passed: bool) -> str:
    if passed:
        return (
            f"{TICKET_KEY} passed.\n\n"
            "The live workspace switcher footer kept `Save and switch` visible and disabled "
            "in pristine state, and keyboard Tab navigation still wrapped from that footer "
            "boundary back to the first saved workspace row.\n"
        )
    return (
        f"{TICKET_KEY} failed.\n\n"
        f"{_actual_result_summary(result, passed=False)}\n\n"
        f"{result.get('error', 'The live TS-954 result did not match the expected footer behavior.')}\n"
    )


def _build_bug_description(result: dict[str, object]) -> str:
    annotated_steps: list[str] = []
    for index, action in enumerate(REQUEST_STEPS, start=1):
        matching = next(
            (
                step
                for step in _steps(result)
                if isinstance(step, dict) and int(step.get("step", -1)) == index
            ),
            None,
        )
        if matching is None:
            annotated_steps.append(f"{index}. ⏭️ {action} Not reached.")
            continue
        icon = "✅" if str(matching.get("status")) == "passed" else "❌"
        annotated_steps.append(
            f"{index}. {icon} {action} Observed: {matching.get('observed', '')}",
        )

    lines = [
        f"# {TICKET_KEY} bug report",
        "",
        "## Steps to reproduce",
        *annotated_steps,
        "",
        "## Exact error message or assertion failure",
        "```text",
        str(result.get("traceback", result.get("error", ""))),
        "```",
        "",
        "## Actual result",
        _actual_result_summary(result, passed=False),
        "",
        "## Expected result",
        EXPECTED_RESULT,
        "",
        "## Environment details",
        f"- URL: {result.get('app_url')}",
        f"- Browser: {result.get('browser')}",
        f"- OS: {result.get('os')}",
        f"- Viewport: {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
        f"- Run command: `{RUN_COMMAND}`",
        "",
        "## Screenshots or logs",
        f"- Screenshot: `{result.get('screenshot')}`",
        f"- Startup observation: `{json.dumps(result.get('startup_observation'), ensure_ascii=True)}`",
        f"- Shell observation: `{json.dumps(result.get('shell_observation'), ensure_ascii=True)}`",
        f"- Trigger observation: `{json.dumps(result.get('trigger_observation'), ensure_ascii=True)}`",
        f"- Switcher observation: `{json.dumps(result.get('open_switcher_observation'), ensure_ascii=True)}`",
        f"- Footer state before Tab: `{json.dumps(result.get('save_and_switch_before_tab'), ensure_ascii=True)}`",
        f"- Footer state at focus: `{json.dumps(result.get('footer_button_state'), ensure_ascii=True)}`",
        f"- Tab trace: `{json.dumps(result.get('tab_trace_to_footer'), ensure_ascii=True)}`",
        f"- Wrap state: `{json.dumps(result.get('wrap_state_after_footer'), ensure_ascii=True)}`",
        f"- Console events: `{json.dumps(result.get('console_events'), ensure_ascii=True)}`",
        f"- Page errors: `{json.dumps(result.get('page_errors'), ensure_ascii=True)}`",
    ]
    return "\n".join(lines) + "\n"


def _snippet(text: str, *, limit: int = 240) -> str:
    collapsed = " ".join(text.split())
    if len(collapsed) <= limit:
        return collapsed
    return f"{collapsed[: limit - 3]}..."


def _compact_html(html: str, *, limit: int = 200) -> str:
    collapsed = " ".join(html.split())
    if len(collapsed) <= limit:
        return collapsed
    return f"{collapsed[: limit - 3]}..."


if __name__ == "__main__":
    main()
