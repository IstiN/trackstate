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
    WorkspaceSwitcherFocusTargetObservation,
    WorkspaceSwitcherInternalFocusObservation,
    WorkspaceSwitcherObservation,
    WorkspaceSwitcherPanelObservation,
    WorkspaceSwitcherSavedWorkspaceRowObservation,
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
    create_live_tracker_app,
)
from testing.tests.support.stored_workspace_profiles_runtime import (  # noqa: E402
    StoredWorkspaceProfilesRuntime,
)

TICKET_KEY = "TS-859"
TEST_CASE_TITLE = (
    "Workspace switcher menu interaction — Space on a focused in-panel control "
    "does not trigger the trigger toggle dismissal"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-859/test_ts_859.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 960}
TRIGGER_FOCUS_TIMEOUT_MS = 4_000
SURFACE_OPEN_TIMEOUT_MS = 4_000
SURFACE_OPEN_STABILITY_MS = 600
INTERNAL_FOCUS_TIMEOUT_MS = 4_000
INTERNAL_FOCUS_TAB_LIMIT = 12
POST_SPACE_STABILITY_MS = 1_000
DEFAULT_BRANCH = "main"
ACTIVE_WORKSPACE_DISPLAY_NAME = "Hosted main workspace"
SECONDARY_WORKSPACE_DISPLAY_NAME = "Hosted alt workspace"
SECONDARY_WORKSPACE_WRITE_BRANCH = "ts-859-alt"
BRANCH_FIELD_LABEL = "Branch"

PRECONDITIONS = [
    "The workspace switcher trigger is reachable with real desktop keyboard navigation.",
    "The workspace switcher surface is open.",
    "Keyboard focus is on an interactive control inside the open workspace switcher surface.",
]
REQUEST_STEPS = [
    "Press the 'Space' key on the focused trigger to open the surface.",
    "Use the keyboard to move focus to an interactive element within the surface (the Branch field in the Save and switch section).",
    "Press the 'Space' key.",
]
AUTOMATION_STEPS = [
    "Launch the deployed desktop app and reach the workspace switcher trigger through real keyboard navigation.",
    "Press Space on the focused workspace switcher trigger to open the surface.",
    "Use keyboard Tab navigation to move focus from the open trigger to the Branch field inside the workspace switcher surface.",
    "Press Space on the focused Branch field and verify the field itself handles the key press without triggering the workspace switcher trigger's close toggle.",
]
EXPECTED_RESULT = (
    "The focused in-panel interactive element handles the Space keypress itself. "
    "For the Branch field, the value changes in response to Space while the "
    "workspace switcher remains open, focus stays in the field, and the trigger's "
    "toggle-close logic is not activated by bubbled keyboard events from inside "
    "the surface."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts859_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts859_failure.png"


@dataclass(frozen=True)
class TriggerKeyboardReachObservation:
    method: str
    focus_sequence: tuple[FocusNavigationStep, ...]
    forward_error: str | None = None


@dataclass(frozen=True)
class InternalFocusAttempt:
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
            "TS-859 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
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
        "trigger_focus_timeout_ms": TRIGGER_FOCUS_TIMEOUT_MS,
        "surface_open_timeout_ms": SURFACE_OPEN_TIMEOUT_MS,
        "surface_open_stability_ms": SURFACE_OPEN_STABILITY_MS,
        "internal_focus_timeout_ms": INTERNAL_FOCUS_TIMEOUT_MS,
        "internal_focus_tab_limit": INTERNAL_FOCUS_TAB_LIMIT,
        "post_space_stability_ms": POST_SPACE_STABILITY_MS,
        "linked_bugs": ["TS-848"],
        "preconditions": PRECONDITIONS,
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
                repository=service.repository,
                token=token,
                workspace_state=workspace_state,
            ),
        ) as tracker_page:
            page = LiveWorkspaceSwitcherPage(tracker_page)
            try:
                trigger: WorkspaceSwitcherTriggerObservation | None = None
                focus_reach: TriggerKeyboardReachObservation | None = None
                focus_steps: tuple[FocusNavigationStep, ...] = ()
                focused_trigger: FocusedElementObservation | None = None
                try:
                    runtime = tracker_page.open()
                    result["runtime_state"] = runtime.kind
                    result["runtime_body_text"] = runtime.body_text
                    if runtime.kind != "ready":
                        raise AssertionError(
                            "Step 1 failed: the deployed app did not reach an interactive "
                            "desktop state before the internal-control Space-key scenario "
                            "began.\n"
                            f"Observed runtime state: {runtime.kind}\n"
                            f"Observed body text:\n{runtime.body_text}",
                        )

                    page.dismiss_connection_banner()
                    page.navigate_to_section("Dashboard")
                    page.set_viewport(**DESKTOP_VIEWPORT)
                    trigger = page.observe_trigger()
                    result["trigger_observation"] = _trigger_payload(trigger)

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
                    _record_step(
                        result,
                        step=1,
                        status="failed",
                        action=AUTOMATION_STEPS[0],
                        observed=str(error),
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
                        f"reach_method={focus_reach.method}; "
                        f"tab_steps_to_trigger={len(focus_steps)}; "
                        f"focused_trigger={focused_trigger.accessible_name!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Viewed the live desktop shell, confirmed Dashboard plus the "
                        "visible workspace switcher trigger were rendered, and reached the "
                        "trigger through a real keyboard path before pressing Space."
                    ),
                    observed=(
                        f"trigger_text={trigger.visible_text!r}; "
                        f"focus_sequence={_focus_sequence_summary(focus_steps)}; "
                        f"focused_trigger={focused_trigger.accessible_name!r}"
                    ),
                )

                switcher_before_space: WorkspaceSwitcherObservation | None = None
                panel_before_space: WorkspaceSwitcherPanelObservation | None = None
                surface_before_space: WorkspaceSwitcherSurfaceObservation | None = None
                focused_trigger_after_open: FocusedElementObservation | None = None
                try:
                    page.press_space_on_active_element_and_wait_for_surface(
                        timeout_ms=SURFACE_OPEN_TIMEOUT_MS,
                    )
                    switcher_before_space = page.observe_open_switcher(
                        timeout_ms=SURFACE_OPEN_TIMEOUT_MS,
                    )
                    panel_before_space = page.observe_open_panel(
                        expected_container_kinds=("anchored-panel", "surface"),
                        timeout_ms=SURFACE_OPEN_TIMEOUT_MS,
                    )
                    surface_before_space = page.observe_surface(
                        timeout_ms=SURFACE_OPEN_TIMEOUT_MS,
                    )
                    page.wait_for_surface_to_remain_open(
                        stability_ms=SURFACE_OPEN_STABILITY_MS,
                        timeout_ms=SURFACE_OPEN_TIMEOUT_MS,
                    )
                    focused_trigger_after_open = page.active_element()
                    result["open_switcher_observation"] = _switcher_payload(
                        switcher_before_space,
                    )
                    result["open_panel_observation"] = asdict(panel_before_space)
                    result["surface_observation"] = asdict(surface_before_space)
                    result["focused_trigger_after_open"] = _focused_element_payload(
                        focused_trigger_after_open,
                    )
                    _assert_surface_open_with_trigger_focus(
                        switcher=switcher_before_space,
                        panel=panel_before_space,
                        surface=surface_before_space,
                        focused=focused_trigger_after_open,
                    )
                except Exception as error:
                    _record_step(
                        result,
                        step=2,
                        status="failed",
                        action=AUTOMATION_STEPS[1],
                        observed=str(error),
                    )
                    raise
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=AUTOMATION_STEPS[1],
                    observed=(
                        f"heading={surface_before_space.heading_text!r}; "
                        f"row_count={switcher_before_space.row_count}; "
                        f"panel_kind={panel_before_space.container_kind!r}; "
                        f"focus_after_open={focused_trigger_after_open.accessible_name!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Pressed Space on the focused trigger and visually confirmed the "
                        "Workspace switcher surface opened on screen while the trigger still "
                        "owned keyboard focus."
                    ),
                    observed=(
                        f"heading={surface_before_space.heading_text!r}; "
                        f"switcher_text_excerpt={_snippet(switcher_before_space.switcher_text)!r}; "
                        f"focus_after_open={focused_trigger_after_open.accessible_name!r}"
                    ),
                )

                branch_focus: WorkspaceSwitcherInternalFocusObservation | None = None
                tab_attempts: tuple[InternalFocusAttempt, ...] = ()
                try:
                    branch_focus, tab_attempts = _focus_branch_field_with_keyboard(
                        page=page,
                        panel=panel_before_space,
                        max_tabs=INTERNAL_FOCUS_TAB_LIMIT,
                        timeout_ms=INTERNAL_FOCUS_TIMEOUT_MS,
                    )
                    result["branch_focus_observation"] = _internal_focus_payload(
                        branch_focus,
                    )
                    result["branch_tab_attempts"] = [
                        asdict(attempt) for attempt in tab_attempts
                    ]
                    _assert_branch_field_focused(
                        observation=branch_focus,
                        attempts=tab_attempts,
                    )
                except Exception as error:
                    _record_step(
                        result,
                        step=3,
                        status="failed",
                        action=AUTOMATION_STEPS[2],
                        observed=str(error),
                    )
                    raise
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action=AUTOMATION_STEPS[2],
                    observed=(
                        f"tabs_required={len(tab_attempts)}; "
                        f"before_focus={branch_focus.before_label!r}; "
                        f"after_focus={branch_focus.after_label!r}; "
                        f"after_tag={branch_focus.after_tag_name!r}; "
                        f"after_within_switcher={branch_focus.after_within_switcher}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Used keyboard Tab navigation inside the open surface until a real "
                        "in-panel control received focus, then confirmed that control was the "
                        "visible Branch field in the Save and switch section."
                    ),
                    observed=(
                        f"attempt_sequence={_attempt_summary(tab_attempts)!r}; "
                        f"focused_label={branch_focus.after_label!r}; "
                        f"focused_tag={branch_focus.after_tag_name!r}"
                    ),
                )

                before_internal_space = page.active_element()
                branch_value_before_internal_space = _read_switcher_field_value(page)
                switcher_after_space: WorkspaceSwitcherObservation | None = None
                panel_after_space: WorkspaceSwitcherPanelObservation | None = None
                surface_after_space: WorkspaceSwitcherSurfaceObservation | None = None
                focused_after_internal_space: FocusedElementObservation | None = None
                focus_after_internal_space: WorkspaceSwitcherFocusTargetObservation | None = None
                saved_workspace_rows_after_space: tuple[
                    WorkspaceSwitcherSavedWorkspaceRowObservation,
                    ...,
                ] = ()
                trigger_after_internal_space: WorkspaceSwitcherTriggerObservation | None = None
                try:
                    page.press_key("Space", timeout_ms=INTERNAL_FOCUS_TIMEOUT_MS)
                    page.wait_for_surface_to_remain_open(
                        stability_ms=POST_SPACE_STABILITY_MS,
                        timeout_ms=SURFACE_OPEN_TIMEOUT_MS,
                    )
                    switcher_after_space = page.observe_open_switcher(
                        timeout_ms=SURFACE_OPEN_TIMEOUT_MS,
                    )
                    panel_after_space = page.observe_open_panel(
                        expected_container_kinds=("anchored-panel", "surface"),
                        timeout_ms=SURFACE_OPEN_TIMEOUT_MS,
                    )
                    surface_after_space = page.observe_surface(
                        timeout_ms=SURFACE_OPEN_TIMEOUT_MS,
                    )
                    focused_after_internal_space = page.active_element()
                    focus_after_internal_space = page.observe_switcher_focus_target(
                        panel=panel_after_space,
                    )
                    saved_workspace_rows_after_space = page.observe_saved_workspace_rows(
                        timeout_ms=SURFACE_OPEN_TIMEOUT_MS,
                    )
                    trigger_after_internal_space = page.observe_trigger()
                    result["focused_element_before_internal_space"] = (
                        _focused_element_payload(before_internal_space)
                    )
                    result["branch_field_value_before_internal_space"] = (
                        branch_value_before_internal_space
                    )
                    result["focused_element_after_internal_space"] = (
                        _focused_element_payload(focused_after_internal_space)
                    )
                    result["switcher_after_internal_space"] = _switcher_payload(
                        switcher_after_space,
                    )
                    result["panel_after_internal_space"] = asdict(panel_after_space)
                    result["surface_after_internal_space"] = asdict(surface_after_space)
                    result["focus_after_internal_space"] = _switcher_focus_payload(
                        focus_after_internal_space,
                    )
                    result["saved_workspace_rows_after_internal_space"] = (
                        _saved_workspace_rows_payload(saved_workspace_rows_after_space)
                    )
                    result["trigger_after_internal_space"] = _trigger_payload(
                        trigger_after_internal_space,
                    )
                    branch_value_after_internal_space = _read_switcher_field_value(page)
                    result["branch_field_value_after_internal_space"] = (
                        branch_value_after_internal_space
                    )
                    _assert_branch_field_space_behavior(
                        before_focus=before_internal_space,
                        before_value=branch_value_before_internal_space,
                        after_focus=focused_after_internal_space,
                        after_value=branch_value_after_internal_space,
                        focus_observation=focus_after_internal_space,
                        switcher=switcher_after_space,
                        panel=panel_after_space,
                        surface=surface_after_space,
                        rows=saved_workspace_rows_after_space,
                        trigger=trigger_after_internal_space,
                    )
                except Exception as error:
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
                        f"focus_before_space={before_internal_space.accessible_name!r}; "
                        f"focus_after_space={focused_after_internal_space.accessible_name!r}; "
                        f"branch_value_before_space={branch_value_before_internal_space!r}; "
                        f"branch_value_after_space={branch_value_after_internal_space!r}; "
                        f"panel_kind={panel_after_space.container_kind!r}; "
                        f"active_workspace_after_space={_selected_saved_workspace(saved_workspace_rows_after_space).display_name if _selected_saved_workspace(saved_workspace_rows_after_space) is not None else None!r}; "
                        f"trigger_after_space={trigger_after_internal_space.display_name!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Pressed Space while the Branch field inside the open workspace "
                        "switcher owned focus and watched the live UI like a keyboard user."
                    ),
                    observed=(
                        f"heading_still_visible={surface_after_space.heading_text!r}; "
                        f"focus_after_space={focused_after_internal_space.accessible_name!r}; "
                        f"branch_value_before_space={branch_value_before_internal_space!r}; "
                        f"branch_value_after_space={branch_value_after_internal_space!r}; "
                        f"focus_within_switcher={focus_after_internal_space.active_within_switcher}; "
                        f"active_workspace_after_space={_selected_saved_workspace(saved_workspace_rows_after_space).display_name if _selected_saved_workspace(saved_workspace_rows_after_space) is not None else None!r}"
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
        "Step 1 failed: keyboard navigation did not land on the workspace switcher "
        "trigger before the Space-key scenario began.\n"
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


def _assert_surface_open_with_trigger_focus(
    *,
    switcher: WorkspaceSwitcherObservation,
    panel: WorkspaceSwitcherPanelObservation,
    surface: WorkspaceSwitcherSurfaceObservation,
    focused: FocusedElementObservation,
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
    if not _is_workspace_trigger_focus(
        focused.accessible_name,
        fallback_text=focused.text,
    ):
        failures.append(
            "keyboard focus moved away from the workspace switcher trigger while the "
            "surface was open"
        )
    if failures:
        raise AssertionError(
            "Step 2 failed: pressing Space on the focused trigger did not establish the "
            "expected open workspace switcher state.\n"
            + "\n".join(f"- {item}" for item in failures)
            + "\n"
            + f"Observed focused element: label={focused.accessible_name!r}, "
            + f"role={focused.role!r}, tag={focused.tag_name!r}, text={focused.text!r}\n"
            + f"Observed switcher text:\n{switcher.switcher_text}\n"
            + f"Observed panel bounds: left={panel.left:.1f}, top={panel.top:.1f}, "
            + f"width={panel.width:.1f}, height={panel.height:.1f}",
        )


def _focus_branch_field_with_keyboard(
    *,
    page: LiveWorkspaceSwitcherPage,
    panel: WorkspaceSwitcherPanelObservation,
    max_tabs: int,
    timeout_ms: int,
) -> tuple[WorkspaceSwitcherInternalFocusObservation, tuple[InternalFocusAttempt, ...]]:
    attempts: list[InternalFocusAttempt] = []
    for tab_press in range(1, max_tabs + 1):
        observation = page.observe_internal_focus_after_tab(
            panel=panel,
            timeout_ms=timeout_ms,
        )
        attempt = InternalFocusAttempt(
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
        if (
            observation.after_label == BRANCH_FIELD_LABEL
            and observation.after_tag_name == "INPUT"
            and observation.after_visible
            and observation.after_in_viewport
            and observation.after_within_switcher
            and not observation.after_on_trigger
            and observation.after_owned_by_switcher
        ):
            return observation, tuple(attempts)

    raise AssertionError(
        "Step 3 failed: keyboard Tab navigation inside the open workspace switcher "
        f"never reached the {BRANCH_FIELD_LABEL} field.\n"
        f"Observed Tab attempt sequence: {_attempt_summary(tuple(attempts))}",
    )


def _assert_branch_field_focused(
    *,
    observation: WorkspaceSwitcherInternalFocusObservation,
    attempts: tuple[InternalFocusAttempt, ...],
) -> None:
    failures: list[str] = []
    if observation.after_label != BRANCH_FIELD_LABEL:
        failures.append(
            f"the focused internal control was {observation.after_label!r} instead of {BRANCH_FIELD_LABEL!r}",
        )
    if observation.after_tag_name != "INPUT":
        failures.append(
            f"the focused internal control tag was {observation.after_tag_name!r} instead of 'INPUT'",
        )
    if not observation.after_visible:
        failures.append(f"the {BRANCH_FIELD_LABEL} field was not visibly focused")
    if not observation.after_in_viewport:
        failures.append(f"the {BRANCH_FIELD_LABEL} field focus target was outside the viewport")
    if not observation.after_within_switcher:
        failures.append("keyboard focus did not move inside the open workspace switcher")
    if observation.after_on_trigger:
        failures.append("keyboard focus remained on the workspace switcher trigger")
    if not observation.after_owned_by_switcher:
        failures.append(
            f"the focused {BRANCH_FIELD_LABEL} field was not owned by the workspace switcher",
        )
    if failures:
        raise AssertionError(
            "Step 3 failed: keyboard navigation inside the open workspace switcher did "
            f"not reach the expected {BRANCH_FIELD_LABEL} field.\n"
            + "\n".join(f"- {item}" for item in failures)
            + "\n"
            + f"Observed focus before Tab: {observation.before_label!r} "
            + f"(role={observation.before_role!r}, tag={observation.before_tag_name!r})\n"
            + f"Observed focus after Tab: {observation.after_label!r} "
            + f"(role={observation.after_role!r}, tag={observation.after_tag_name!r})\n"
            + f"Observed Tab attempt sequence: {_attempt_summary(attempts)}",
        )


def _assert_branch_field_space_behavior(
    *,
    before_focus: FocusedElementObservation,
    before_value: str,
    after_focus: FocusedElementObservation,
    after_value: str,
    focus_observation: WorkspaceSwitcherFocusTargetObservation,
    switcher: WorkspaceSwitcherObservation,
    panel: WorkspaceSwitcherPanelObservation,
    surface: WorkspaceSwitcherSurfaceObservation,
    rows: tuple[WorkspaceSwitcherSavedWorkspaceRowObservation, ...],
    trigger: WorkspaceSwitcherTriggerObservation,
) -> None:
    active_workspace = _selected_saved_workspace(rows)
    failures: list[str] = []
    if "Workspace switcher" not in switcher.switcher_text:
        failures.append("the visible switcher title disappeared after pressing Space inside the panel")
    if panel.container_kind not in {"anchored-panel", "surface"}:
        failures.append(f"the visible panel kind became {panel.container_kind!r}")
    if not surface.dialog_visible:
        failures.append("the workspace switcher surface was no longer visible after the in-panel Space keypress")
    if surface.heading_text.strip() != "Workspace switcher":
        failures.append(
            f"the visible heading became {surface.heading_text!r} instead of 'Workspace switcher'",
        )
    if switcher.row_count <= 0:
        failures.append("the visible workspace rows were no longer present after pressing Space")
    if before_focus.accessible_name != BRANCH_FIELD_LABEL:
        failures.append(
            f"the pre-Space focused element was {before_focus.accessible_name!r} instead of {BRANCH_FIELD_LABEL!r}",
        )
    if after_focus.accessible_name != BRANCH_FIELD_LABEL:
        failures.append(
            f"the post-Space focused element was {after_focus.accessible_name!r} instead of {BRANCH_FIELD_LABEL!r}",
        )
    if after_focus.tag_name != "INPUT":
        failures.append(
            f"the post-Space focused tag was {after_focus.tag_name!r} instead of 'INPUT'",
        )
    if before_value == after_value:
        failures.append(
            f"the {BRANCH_FIELD_LABEL} field value did not change after pressing Space "
            f"(before={before_value!r}, after={after_value!r})",
        )
    if " " not in after_value:
        failures.append(
            f"the {BRANCH_FIELD_LABEL} field value {after_value!r} did not expose a literal space character after pressing Space",
        )
    if not focus_observation.active_within_switcher:
        failures.append("keyboard focus was no longer inside the workspace switcher after pressing Space")
    if focus_observation.active_on_trigger:
        failures.append("keyboard focus jumped back to the workspace switcher trigger after pressing Space")
    if not focus_observation.focus_owned_by_switcher:
        failures.append("the focused control was no longer owned by the workspace switcher after pressing Space")
    if active_workspace is None:
        failures.append("no saved workspace row remained selected after pressing Space")
    elif active_workspace.display_name != ACTIVE_WORKSPACE_DISPLAY_NAME:
        failures.append(
            f"the selected workspace changed to {active_workspace.display_name!r} instead of staying on {ACTIVE_WORKSPACE_DISPLAY_NAME!r}",
        )
    if trigger.display_name != ACTIVE_WORKSPACE_DISPLAY_NAME:
        failures.append(
            f"the visible workspace switcher trigger changed to {trigger.display_name!r} instead of staying on {ACTIVE_WORKSPACE_DISPLAY_NAME!r}",
        )
    if failures:
        raise AssertionError(
            f"Step 4 failed: pressing Space on the focused {BRANCH_FIELD_LABEL} field "
            "inside the workspace switcher did not stay scoped to the in-panel control.\n"
            + "\n".join(f"- {item}" for item in failures)
            + "\n"
            + f"Observed focus before Space: label={before_focus.accessible_name!r}, "
            + f"role={before_focus.role!r}, tag={before_focus.tag_name!r}\n"
            + f"Observed focus after Space: label={after_focus.accessible_name!r}, "
            + f"role={after_focus.role!r}, tag={after_focus.tag_name!r}\n"
            + f"Observed field value before Space: {before_value!r}\n"
            + f"Observed field value after Space: {after_value!r}\n"
            + f"Observed switcher focus payload: {json.dumps(_switcher_focus_payload(focus_observation), indent=2)}\n"
            + f"Observed selected rows: {json.dumps(_saved_workspace_rows_payload(rows), indent=2)}\n"
            + f"Observed switcher text:\n{switcher.switcher_text}",
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
    error = str(result.get("error", "AssertionError: TS-859 failed"))
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
        "* Opened the deployed TrackState app in Chromium with a stored hosted token and deterministic saved workspace profiles.",
        "* Reached the workspace switcher trigger through a real keyboard navigation path and opened the surface with Space.",
        "* Used keyboard Tab navigation to move focus to the Branch field inside the open Workspace switcher surface.",
        "* Pressed Space on that focused in-panel control.",
        "* Verified the visible Workspace switcher surface stayed open, the Branch field retained focus, the Branch field value changed to reflect the Space keypress, and the selected workspace did not change.",
        "",
        "h4. Result",
        (
            "* Matched the expected result."
            if passed
            else f"* Did not match the expected result. {_failed_step_summary(result)}"
        ),
        f"* Expected result: {EXPECTED_RESULT}",
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
        "- Opened the deployed TrackState app in Chromium with a stored hosted token and deterministic saved workspace profiles.",
        "- Reached the workspace switcher trigger through a real keyboard path and opened the surface with `Space`.",
        "- Used keyboard `Tab` navigation to move focus to the in-panel `Branch` field.",
        "- Pressed `Space` on that focused in-panel control.",
        "- Verified the visible Workspace switcher surface stayed open, the `Branch` field retained focus, the `Branch` field value changed after `Space`, and the selected workspace stayed unchanged.",
        "",
        "## Result",
        (
            "- Matched the expected result."
            if passed
            else f"- Did not match the expected result. {_failed_step_summary(result)}"
        ),
        f"- Expected result: {EXPECTED_RESULT}",
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
            "- Added TS-859 live desktop coverage for Space-key interaction on a focused "
            "in-panel workspace switcher control."
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
            "- Outcome: pressing Space on the focused Branch field changed the field "
            "value, kept the visible workspace switcher open, and did not trigger the "
            "trigger-toggle dismissal."
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
                    "branch_tab_attempts": result.get("branch_tab_attempts"),
                    "branch_focus_observation": result.get("branch_focus_observation"),
                    "branch_field_value_before_internal_space": result.get(
                        "branch_field_value_before_internal_space",
                    ),
                    "branch_field_value_after_internal_space": result.get(
                        "branch_field_value_after_internal_space",
                    ),
                    "focused_element_before_internal_space": result.get(
                        "focused_element_before_internal_space",
                    ),
                    "focused_element_after_internal_space": result.get(
                        "focused_element_after_internal_space",
                    ),
                    "focus_after_internal_space": result.get("focus_after_internal_space"),
                    "saved_workspace_rows_after_internal_space": result.get(
                        "saved_workspace_rows_after_internal_space",
                    ),
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
            f"{TICKET_KEY} - Workspace switcher trigger cannot be reached through real keyboard navigation",
            [
                "1. Launch the deployed TrackState desktop app.",
                "2. Use real keyboard navigation to move focus through the visible shell controls.",
                "3. Observe whether focus reaches the workspace switcher trigger before the panel is opened.",
            ],
            (
                "The production desktop UI does not reliably expose the workspace switcher "
                "trigger as a real keyboard focus target, so the Space-key regression "
                "scenario cannot begin from the required user-visible precondition."
            ),
        )
    if failed_step == 2:
        return (
            f"{TICKET_KEY} - Pressing Space on the focused workspace switcher trigger does not establish the open-surface precondition",
            [
                "1. Launch the deployed TrackState desktop app.",
                "2. Reach the workspace switcher trigger through keyboard navigation.",
                "3. Press `Space` on the focused trigger.",
                "4. Observe whether the Workspace switcher surface opens and remains visible.",
            ],
            (
                "The production desktop UI does not reliably open and hold the workspace "
                "switcher surface from the focused trigger, so the internal-control "
                "Space-key regression cannot be exercised."
            ),
        )
    if failed_step == 3:
        return (
            f"{TICKET_KEY} - Keyboard navigation inside the open workspace switcher cannot reach the Branch field",
            [
                "1. Open the workspace switcher from the focused trigger with `Space`.",
                "2. Press `Tab` repeatedly inside the open surface.",
                f"3. Observe whether focus reaches the in-panel {BRANCH_FIELD_LABEL} field.",
            ],
            (
                "The production desktop workspace switcher does not expose the expected "
                f"in-panel {BRANCH_FIELD_LABEL} field as a reachable keyboard target, so internal "
                "Space-key interaction cannot be verified through the live UI."
            ),
        )
    return (
        f"{TICKET_KEY} - Pressing Space on a focused in-panel workspace switcher control triggers the wrong behavior",
        [
            "1. Open the workspace switcher from the focused trigger with `Space`.",
            f"2. Use keyboard Tab navigation to focus the {BRANCH_FIELD_LABEL} field inside the open surface.",
            f"3. Press `Space` while the {BRANCH_FIELD_LABEL} field is focused.",
            f"4. Observe whether the surface stays open, the {BRANCH_FIELD_LABEL} field keeps focus, and the field value changes in response to the keypress.",
        ],
        (
            "The production desktop workspace switcher does not keep the Space-key "
            "interaction scoped to the focused in-panel control. Instead of leaving the "
            f"Workspace switcher open with the {BRANCH_FIELD_LABEL} field still focused "
            "and updated by the keypress, the UI activates an unintended behavior."
        ),
    )


def _annotated_request_steps(result: dict[str, object]) -> list[str]:
    steps = result.get("steps", [])
    if not isinstance(steps, list):
        steps = []
    automation_by_index = {
        index + 1: step for index, step in enumerate(steps) if isinstance(step, dict)
    }
    lines: list[str] = []

    open_step = automation_by_index.get(2, {})
    focus_step = automation_by_index.get(3, {})
    space_step = automation_by_index.get(4, {})

    lines.append(
        _annotated_request_step_line(
            request_step=1,
            text=REQUEST_STEPS[0],
            automation_step=open_step,
        ),
    )
    lines.append(
        _annotated_request_step_line(
            request_step=2,
            text=REQUEST_STEPS[1],
            automation_step=focus_step,
        ),
    )
    lines.append(
        _annotated_request_step_line(
            request_step=3,
            text=REQUEST_STEPS[2],
            automation_step=space_step,
        ),
    )
    return lines


def _annotated_request_step_line(
    *,
    request_step: int,
    text: str,
    automation_step: object,
) -> str:
    if not isinstance(automation_step, dict):
        return f"{request_step}. ❌ {text} Observed: no automation observation was recorded."
    status = str(automation_step.get("status", "failed")).lower()
    observed = str(automation_step.get("observed", "")).strip() or "No observation recorded."
    marker = "✅" if status == "passed" else "❌"
    return f"{request_step}. {marker} {text} Observed: {observed}"


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
    entries = result.setdefault("human_verification", [])
    assert isinstance(entries, list)
    entries.append({"check": check, "observed": observed})


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    steps = result.get("steps", [])
    if not isinstance(steps, list):
        return []
    lines: list[str] = []
    for entry in steps:
        if not isinstance(entry, dict):
            continue
        status = str(entry.get("status", "")).lower()
        marker = "✅" if status == "passed" else "❌"
        prefix = "*" if jira else "-"
        lines.append(
            f"{prefix} Step {entry.get('step')}: {marker} {entry.get('action')} "
            f"Observed: {entry.get('observed')}",
        )
    return lines


def _human_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    entries = result.get("human_verification", [])
    if not isinstance(entries, list):
        return []
    prefix = "*" if jira else "-"
    lines: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        lines.append(
            f"{prefix} Checked: {entry.get('check')} Observed: {entry.get('observed')}",
        )
    return lines


def _artifact_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    screenshot = result.get("screenshot")
    if not screenshot:
        return []
    prefix = "*" if jira else "-"
    label = "{{Screenshot}}" if jira else "**Screenshot:**"
    return [f"{prefix} {label} {screenshot}"]


def _failed_step_summary(result: dict[str, object]) -> str:
    steps = result.get("steps", [])
    if isinstance(steps, list):
        for entry in steps:
            if isinstance(entry, dict) and entry.get("status") == "failed":
                return str(entry.get("observed", result.get("error", "Unknown failure")))
    return str(result.get("error", "Unknown failure"))


def _first_failed_step_number(result: dict[str, object]) -> int | None:
    steps = result.get("steps", [])
    if not isinstance(steps, list):
        return None
    for entry in steps:
        if isinstance(entry, dict) and entry.get("status") == "failed":
            step = entry.get("step")
            return int(step) if isinstance(step, int) else None
    return None


def _attempt_summary(attempts: tuple[InternalFocusAttempt, ...]) -> str:
    if not attempts:
        return "<no attempts>"
    return " | ".join(
        (
            f"Tab {attempt.tab_press}: "
            f"{attempt.before_label!r} -> {attempt.after_label!r} "
            f"(role={attempt.after_role!r}, tag={attempt.after_tag_name!r}, "
            f"within={attempt.after_within_switcher}, on_trigger={attempt.after_on_trigger}, "
            f"owned={attempt.after_owned_by_switcher})"
        )
        for attempt in attempts
    )


def _focus_sequence_summary(sequence: tuple[FocusNavigationStep, ...]) -> str:
    if not sequence:
        return "<no focus steps>"
    return " -> ".join(
        _focus_step_target(step.after_label, step.after_tag_name) for step in sequence
    )


def _focus_step_target(label: str | None, tag_name: str | None) -> str:
    normalized = " ".join((label or "").split()).strip()
    if normalized:
        return normalized
    tag = (tag_name or "").strip()
    return f"<{tag or 'unknown'}>"


def _is_workspace_trigger_focus(label: str | None, *, fallback_text: str | None) -> bool:
    for candidate in (label, fallback_text):
        normalized = " ".join(str(candidate or "").split())
        if normalized.startswith("Workspace switcher:"):
            return True
    return False


def _snippet(value: str, limit: int = 220) -> str:
    normalized = " ".join(str(value).split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3] + "..."


def _workspace_state(repository: str) -> dict[str, object]:
    first_id = f"hosted:{repository.lower()}@{DEFAULT_BRANCH}"
    second_id = (
        f"hosted:{repository.lower()}@{DEFAULT_BRANCH}:{SECONDARY_WORKSPACE_WRITE_BRANCH}"
    )
    return {
        "activeWorkspaceId": first_id,
        "migrationComplete": True,
        "profiles": [
            {
                "id": first_id,
                "displayName": ACTIVE_WORKSPACE_DISPLAY_NAME,
                "customDisplayName": ACTIVE_WORKSPACE_DISPLAY_NAME,
                "targetType": "hosted",
                "target": repository,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": DEFAULT_BRANCH,
                "lastOpenedAt": "2026-05-18T03:30:00.000Z",
            },
            {
                "id": second_id,
                "displayName": SECONDARY_WORKSPACE_DISPLAY_NAME,
                "customDisplayName": SECONDARY_WORKSPACE_DISPLAY_NAME,
                "targetType": "hosted",
                "target": repository,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": SECONDARY_WORKSPACE_WRITE_BRANCH,
                "lastOpenedAt": "2026-05-18T03:20:00.000Z",
            },
        ],
    }


def _selected_saved_workspace(
    rows: tuple[WorkspaceSwitcherSavedWorkspaceRowObservation, ...],
) -> WorkspaceSwitcherSavedWorkspaceRowObservation | None:
    for row in rows:
        if row.selected:
            return row
    return None


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
                "bounds": {
                    "left": row.left,
                    "top": row.top,
                    "width": row.width,
                    "height": row.height,
                },
            },
        )
    return payload


def _read_switcher_field_value(page: LiveWorkspaceSwitcherPage) -> str:
    return page.read_switcher_text_field_value(
        BRANCH_FIELD_LABEL,
        timeout_ms=INTERNAL_FOCUS_TIMEOUT_MS,
    )


def _internal_focus_payload(
    observation: WorkspaceSwitcherInternalFocusObservation,
) -> dict[str, object]:
    return {
        "before_label": observation.before_label,
        "before_role": observation.before_role,
        "before_tag_name": observation.before_tag_name,
        "before_outer_html": observation.before_outer_html,
        "before_visible": observation.before_visible,
        "before_in_viewport": observation.before_in_viewport,
        "before_within_switcher": observation.before_within_switcher,
        "before_on_trigger": observation.before_on_trigger,
        "before_owned_by_switcher": observation.before_owned_by_switcher,
        "after_label": observation.after_label,
        "after_role": observation.after_role,
        "after_tag_name": observation.after_tag_name,
        "after_outer_html": observation.after_outer_html,
        "after_visible": observation.after_visible,
        "after_in_viewport": observation.after_in_viewport,
        "after_within_switcher": observation.after_within_switcher,
        "after_on_trigger": observation.after_on_trigger,
        "after_owned_by_switcher": observation.after_owned_by_switcher,
        "after_different_from_before": observation.after_different_from_before,
    }


def _switcher_focus_payload(
    observation: WorkspaceSwitcherFocusTargetObservation,
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
    }


def _focused_element_payload(element: FocusedElementObservation) -> dict[str, object]:
    return {
        "tag_name": element.tag_name,
        "role": element.role,
        "accessible_name": element.accessible_name,
        "text": element.text,
        "tabindex": element.tabindex,
        "outer_html": element.outer_html,
    }


def _trigger_payload(trigger: WorkspaceSwitcherTriggerObservation) -> dict[str, object]:
    return {
        "semantic_label": trigger.semantic_label,
        "visible_text": trigger.visible_text,
        "display_name": trigger.display_name,
        "workspace_type": trigger.workspace_type,
        "state_label": trigger.state_label,
        "top_button_labels": list(trigger.top_button_labels),
        "bounds": {
            "left": trigger.left,
            "top": trigger.top,
            "width": trigger.width,
            "height": trigger.height,
        },
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


if __name__ == "__main__":
    main()
