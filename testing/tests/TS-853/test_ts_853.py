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

TICKET_KEY = "TS-853"
TEST_CASE_TITLE = (
    "Press Arrow Up on the first workspace item — selection wraps to the last item"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-853/test_ts_853.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 960}
KEY_STABILITY_MS = 1_000
DEFAULT_BRANCH = "main"
FIRST_WORKSPACE_DISPLAY_NAME = "Hosted main workspace"
LAST_WORKSPACE_DISPLAY_NAME = "Hosted alt workspace"
LAST_WORKSPACE_WRITE_BRANCH = "ts-853-alt"

PRECONDITIONS = [
    "The workspace switcher panel is open.",
    "At least two workspaces are saved in the account.",
    "The first workspace row in the list is currently selected/highlighted.",
]
TEST_CASE_STEPS = [
    "Press the 'Arrow Up' key.",
]
AUTOMATION_STEPS = [
    "Open the desktop workspace switcher and confirm the first saved workspace row is active before the boundary interaction.",
    "Click the active first saved-workspace row and verify the row button receives keyboard focus inside the open switcher.",
    "Press the 'Arrow Up' key and wait for the last saved workspace row to become active while the switcher remains open.",
]
EXPECTED_RESULT = (
    "The selection indicator wraps around from the first item to the last workspace "
    "row in the list, and keyboard focus remains trapped within the switcher "
    "component instead of escaping to the document body."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts853_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts853_failure.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-853 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
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
        "linked_bugs": ["TS-852", "TS-851"],
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
                try:
                    runtime = tracker_page.open()
                    result["runtime_state"] = runtime.kind
                    result["runtime_body_text"] = runtime.body_text
                    if runtime.kind != "ready":
                        raise AssertionError(
                            "Step 1 failed: the deployed app did not reach an interactive "
                            "desktop state before the workspace-row focus scenario began.\n"
                            f"Observed runtime state: {runtime.kind}\n"
                            f"Observed body text:\n{runtime.body_text}",
                        )

                    page.dismiss_connection_banner()
                    page.navigate_to_section("Dashboard")
                    page.set_viewport(**DESKTOP_VIEWPORT)
                    trigger = page.observe_trigger()
                    switcher = page.open_and_observe()
                    panel = page.observe_open_panel(
                        expected_container_kinds=("anchored-panel", "surface"),
                    )
                    saved_workspace_rows = page.observe_saved_workspace_rows()
                    _assert_desktop_panel_open(
                        trigger=trigger,
                        switcher=switcher,
                        panel=panel,
                    )
                    active_workspace = _assert_saved_workspace_navigation_ready(
                        saved_workspace_rows,
                    )
                    result["trigger_observation"] = _trigger_payload(trigger)
                    result["open_switcher_observation"] = _switcher_payload(switcher)
                    result["open_panel_observation"] = asdict(panel)
                    result["saved_workspace_rows_before_click"] = _saved_workspace_rows_payload(
                        saved_workspace_rows,
                    )
                    result["active_workspace_before_click"] = active_workspace.display_name
                except AssertionError as error:
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
                        f"trigger_text={trigger.visible_text!r}; "
                        f"container_kind={panel.container_kind}; "
                        f"saved_workspace_row_count={len(saved_workspace_rows)}; "
                        f"active_workspace={active_workspace.display_name!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Opened the desktop workspace switcher and visually checked that "
                        "the Workspace switcher title plus both saved workspace rows were "
                        "visible with the first workspace row highlighted before the "
                        "Arrow Up boundary action."
                    ),
                    observed=(
                        "title='Workspace switcher'; "
                        f"saved_workspace_row_count={len(saved_workspace_rows)}; "
                        f"active_workspace={active_workspace.display_name!r}; "
                        f"text_excerpt={_snippet(switcher.switcher_text)!r}"
                    ),
                )

                try:
                    click_x, click_y = _saved_workspace_click_point(active_workspace)
                    page.click_saved_workspace_row_surface(FIRST_WORKSPACE_DISPLAY_NAME)
                    page.wait_for_surface_to_remain_open(
                        stability_ms=KEY_STABILITY_MS,
                        timeout_ms=4_000,
                    )
                    focused_element = page.active_element()
                    focus_ownership = page.observe_focus_ownership(panel=panel)
                    row_focus = page.observe_saved_workspace_row_focus(
                        display_name=FIRST_WORKSPACE_DISPLAY_NAME,
                        panel=panel,
                    )
                    saved_workspace_rows_after_click = page.observe_saved_workspace_rows(
                        timeout_ms=4_000,
                    )
                    result["focused_element_after_click"] = _focused_element_payload(
                        focused_element,
                    )
                    result["focus_ownership_after_click"] = _focus_ownership_payload(
                        focus_ownership,
                    )
                    result["row_focus_after_click"] = _row_focus_payload(row_focus)
                    result["saved_workspace_rows_after_click"] = _saved_workspace_rows_payload(
                        saved_workspace_rows_after_click,
                    )
                    _assert_row_click_established_keyboard_focus(
                        clicked_x=click_x,
                        clicked_y=click_y,
                        expected_workspace_name=FIRST_WORKSPACE_DISPLAY_NAME,
                        focused_element=focused_element,
                        focus_ownership=focus_ownership,
                        row_focus=row_focus,
                        saved_workspace_rows=saved_workspace_rows_after_click,
                    )
                except AssertionError as error:
                    result["product_gap"] = (
                        "Clicking the first saved-workspace row does not leave keyboard "
                        "focus on the clicked row inside the open workspace switcher, so "
                        "Arrow Up is not driven from the saved-workspace interaction target."
                    )
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
                        f"click_point=({click_x:.1f}, {click_y:.1f}); "
                        f"focus_label={focused_element.accessible_name!r}; "
                        f"focus_role={focused_element.role!r}; "
                        f"focus_owned_by_switcher={focus_ownership.focus_owned_by_switcher}; "
                        f"row_focus_found={row_focus.row_found}; "
                        f"active_workspace_after_click={_selected_saved_workspace(saved_workspace_rows_after_click).display_name if _selected_saved_workspace(saved_workspace_rows_after_click) is not None else None!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Clicked the first saved-workspace row and checked that the "
                        "keyboard target became the row button itself inside the open "
                        "switcher, not the global app shell or the trigger."
                    ),
                    observed=(
                        f"focus_label={focused_element.accessible_name!r}; "
                        f"focus_role={focused_element.role!r}; "
                        f"focus_within_switcher={focus_ownership.active_within_switcher}; "
                        f"focus_owned_by_switcher={focus_ownership.focus_owned_by_switcher}; "
                        f"focus_on_trigger={focus_ownership.active_on_trigger}; "
                        f"row_text_excerpt={_snippet(row_focus.row_text)!r}"
                    ),
                )

                arrow_up = _press_arrow_up_and_observe(
                    page=page,
                    panel=panel,
                    expected_active_workspace=LAST_WORKSPACE_DISPLAY_NAME,
                )
                result["arrow_up_observation"] = arrow_up
                try:
                    _assert_arrow_up_wrapped_to_last_workspace(
                        observation=arrow_up,
                        before_active_workspace=FIRST_WORKSPACE_DISPLAY_NAME,
                        expected_active_workspace=LAST_WORKSPACE_DISPLAY_NAME,
                    )
                except Exception as error:
                    result["product_gap"] = (
                        "After clicking the first saved-workspace row and confirming row "
                        "focus, pressing Arrow Up does not wrap the active saved workspace "
                        "to the last visible row while the switcher remains open."
                    )
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
                        f"active_workspace_after={arrow_up['active_workspace_name']!r}; "
                        f"panel_kind={arrow_up['panel']['container_kind']!r}; "
                        f"monitor_hidden_after_visible="
                        f"{arrow_up['monitor']['ever_hidden_after_visible']}; "
                        f"row_contains_active={arrow_up['row_focus']['row_contains_active']}; "
                        f"wrapped_row_text_excerpt={_snippet(str(arrow_up['row_focus']['row_text']))!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Pressed Arrow Up from the focused first row and watched the active "
                        "selection wrap from Hosted main workspace to Hosted alt workspace "
                        "while the workspace switcher stayed visible."
                    ),
                    observed=(
                        f"active_before_arrow={FIRST_WORKSPACE_DISPLAY_NAME!r}; "
                        f"active_after_arrow={arrow_up['active_workspace_name']!r}; "
                        f"wrapped_row_contains_active={arrow_up['row_focus']['row_contains_active']}; "
                        f"panel_hidden_after_arrow={arrow_up['monitor']['ever_hidden_after_visible']}; "
                        f"wrapped_row_text_excerpt={_snippet(str(arrow_up['row_focus']['row_text']))!r}; "
                        f"text_excerpt={_snippet(str(arrow_up['switcher']['switcher_text']))!r}"
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


def _press_arrow_up_and_observe(
    *,
    page: LiveWorkspaceSwitcherPage,
    panel: WorkspaceSwitcherPanelObservation,
    expected_active_workspace: str,
) -> dict[str, object]:
    page.start_transition_monitor()
    page.press_key("ArrowUp")
    page.wait_for_surface_to_remain_open(
        stability_ms=KEY_STABILITY_MS,
        timeout_ms=4_000,
    )
    page.wait_for_active_saved_workspace(
        expected_active_workspace,
        timeout_ms=10_000,
    )
    switcher = page.observe_open_switcher(timeout_ms=4_000)
    panel = page.observe_open_panel(
        expected_container_kinds=("anchored-panel", "surface"),
        timeout_ms=4_000,
    )
    active = page.active_element()
    focus = page.observe_focus_ownership(panel=panel)
    row_focus = page.observe_saved_workspace_row_focus(
        display_name=expected_active_workspace,
        panel=panel,
    )
    saved_workspace_rows = page.observe_saved_workspace_rows(timeout_ms=4_000)
    monitor = page.read_transition_monitor(clear=True)
    active_workspace = _selected_saved_workspace(saved_workspace_rows)
    return {
        "key": "ArrowUp",
        "switcher": _switcher_payload(switcher),
        "panel": asdict(panel),
        "active": _focused_element_payload(active),
        "focus": _focus_ownership_payload(focus),
        "row_focus": _row_focus_payload(row_focus),
        "saved_workspace_rows": _saved_workspace_rows_payload(saved_workspace_rows),
        "active_workspace_name": (
            active_workspace.display_name if active_workspace is not None else None
        ),
        "monitor": _monitor_payload(monitor),
    }


def _assert_desktop_panel_open(
    *,
    trigger: WorkspaceSwitcherTriggerObservation,
    switcher: WorkspaceSwitcherObservation,
    panel: WorkspaceSwitcherPanelObservation,
) -> None:
    if "Workspace switcher" not in switcher.switcher_text:
        raise AssertionError(
            "Step 1 failed: opening the workspace switcher did not expose the visible "
            "Workspace switcher title.\n"
            f"Observed switcher text:\n{switcher.switcher_text}",
        )
    if panel.container_kind not in {"anchored-panel", "surface"}:
        raise AssertionError(
            "Step 1 failed: clicking the workspace switcher trigger did not open the "
            "expected desktop panel-style surface.\n"
            f"Observed container kind: {panel.container_kind}\n"
            f"Observed bounds: left={panel.left:.1f}, top={panel.top:.1f}, "
            f"width={panel.width:.1f}, height={panel.height:.1f}",
        )
    if panel.width <= 0 or panel.height <= 0:
        raise AssertionError(
            "Step 1 failed: clicking the workspace switcher trigger did not expose a "
            "readable desktop panel surface.\n"
            f"Observed panel bounds: left={panel.left:.1f}, top={panel.top:.1f}, "
            f"width={panel.width:.1f}, height={panel.height:.1f}\n"
            f"Observed trigger bounds: left={trigger.left:.1f}, top={trigger.top:.1f}, "
            f"width={trigger.width:.1f}, height={trigger.height:.1f}",
        )


def _assert_saved_workspace_navigation_ready(
    rows: tuple[WorkspaceSwitcherSavedWorkspaceRowObservation, ...],
) -> WorkspaceSwitcherSavedWorkspaceRowObservation:
    if len(rows) < 2:
        raise AssertionError(
            "Step 1 failed: the visible workspace switcher did not expose at least "
            "two saved workspace rows needed to exercise keyboard navigation.\n"
            f"Observed rows: {json.dumps(_saved_workspace_rows_payload(rows), indent=2)}",
        )
    active_workspace = _selected_saved_workspace(rows)
    if active_workspace is None:
        raise AssertionError(
            "Step 1 failed: none of the visible saved workspace rows was marked "
            "active before clicking the row.\n"
            f"Observed rows: {json.dumps(_saved_workspace_rows_payload(rows), indent=2)}",
        )
    if active_workspace.display_name != FIRST_WORKSPACE_DISPLAY_NAME:
        raise AssertionError(
            "Step 1 failed: the preloaded active saved workspace was not the expected "
            "starting point.\n"
            f"Observed active workspace: {active_workspace.display_name!r}\n"
            f"Observed rows: {json.dumps(_saved_workspace_rows_payload(rows), indent=2)}",
        )
    return active_workspace


def _assert_row_click_established_keyboard_focus(
    *,
    clicked_x: float,
    clicked_y: float,
    expected_workspace_name: str,
    focused_element: FocusedElementObservation,
    focus_ownership: WorkspaceSwitcherFocusOwnershipObservation,
    row_focus: WorkspaceSwitcherRowFocusObservation,
    saved_workspace_rows: tuple[WorkspaceSwitcherSavedWorkspaceRowObservation, ...],
) -> None:
    active_workspace = _selected_saved_workspace(saved_workspace_rows)
    active_label = focused_element.accessible_name or ""
    active_text = focused_element.text or ""

    failures: list[str] = []
    if not focus_ownership.focus_owned_by_switcher:
        failures.append(
            "keyboard focus was not owned by the open workspace switcher after clicking the active row",
        )
    if not focus_ownership.active_within_switcher:
        failures.append(
            "the focused element remained outside the open workspace switcher after clicking the active row",
        )
    if focus_ownership.active_on_trigger:
        failures.append(
            "keyboard focus remained on the workspace-switcher trigger after clicking the active row",
        )
    if focused_element.role != "button":
        failures.append(
            f"the focused element role was {focused_element.role!r} instead of the saved-row button",
        )
    if expected_workspace_name not in active_label and expected_workspace_name not in active_text:
        failures.append(
            "the focused element label did not identify the clicked saved workspace row",
        )
    if "Branch:" not in active_label and "Branch:" not in active_text:
        failures.append(
            "the focused element label did not retain the saved workspace branch details",
        )
    if not row_focus.row_found:
        failures.append(
            "the row-focus probe did not find any visible saved-workspace row matching the clicked workspace",
        )
    if active_workspace is None:
        failures.append("no saved workspace row remained active after clicking the active row")
    elif active_workspace.display_name != expected_workspace_name:
        failures.append(
            f"the active saved workspace changed to {active_workspace.display_name!r} before Arrow Up instead of remaining on {expected_workspace_name!r}",
        )
    if len(saved_workspace_rows) < 2:
        failures.append("fewer than two saved workspace rows remained visible after clicking the active row")

    if failures:
        raise AssertionError(
            "Step 2 failed: clicking the active saved workspace row did not move keyboard "
            "focus onto the clicked row inside the open switcher.\n"
            + "\n".join(f"- {item}" for item in failures)
            + "\n"
            + f"Clicked point: ({clicked_x:.1f}, {clicked_y:.1f})\n"
            + f"Focused label: {focused_element.accessible_name!r}\n"
            + f"Focused role: {focused_element.role!r}\n"
            + f"Focused tag: {focused_element.tag_name!r}\n"
            + f"Focused HTML: {focused_element.outer_html}\n"
            + f"Focus ownership: {json.dumps(_focus_ownership_payload(focus_ownership), indent=2)}\n"
            + f"Row focus probe: {json.dumps(_row_focus_payload(row_focus), indent=2)}\n"
            + f"Observed rows after click: {json.dumps(_saved_workspace_rows_payload(saved_workspace_rows), indent=2)}"
        )


def _assert_arrow_up_wrapped_to_last_workspace(
    *,
    observation: dict[str, object],
    before_active_workspace: str,
    expected_active_workspace: str,
) -> None:
    _assert_key_kept_panel_open(observation=observation)
    focus = observation["focus"]
    row_focus = observation["row_focus"]
    saved_workspace_rows = observation["saved_workspace_rows"]
    active_workspace_name = observation["active_workspace_name"]
    assert isinstance(focus, dict)
    assert isinstance(row_focus, dict)
    assert isinstance(saved_workspace_rows, list)

    failures: list[str] = []
    if len(saved_workspace_rows) < 2:
        failures.append("fewer than two saved workspace rows remained visible after Arrow Up")
    if active_workspace_name == before_active_workspace:
        failures.append(
            f"the active saved workspace stayed on {before_active_workspace!r} instead of wrapping",
        )
    if active_workspace_name != expected_active_workspace:
        failures.append(
            f"the active saved workspace became {active_workspace_name!r} instead of "
            f"{expected_active_workspace!r}",
        )
    if not bool(focus.get("focus_owned_by_switcher")):
        failures.append("keyboard focus escaped the workspace switcher")
    if not bool(focus.get("active_within_switcher")):
        failures.append("the active element was no longer inside the open switcher")
    if bool(focus.get("active_on_trigger")):
        failures.append("keyboard focus jumped back to the workspace-switcher trigger")
    if not bool(row_focus.get("row_found")):
        failures.append(
            f"the row-focus probe could not find the last saved workspace row {expected_active_workspace!r}",
        )
    if not bool(row_focus.get("row_contains_active")):
        failures.append(
            "the focused element was not contained by the wrapped last saved-workspace row",
        )
    if failures:
        raise AssertionError(
            "Step 3 failed: pressing Arrow Up from the focused first saved-workspace row "
            "did not wrap selection and focus to the last workspace while the panel "
            "remained open.\n"
            f"Active workspace before Arrow Up: {before_active_workspace!r}\n"
            f"Active workspace after Arrow Up: {active_workspace_name!r}\n"
            f"Observed focus ownership: {json.dumps(focus, indent=2)}\n"
            f"Observed row focus: {json.dumps(row_focus, indent=2)}\n"
            f"Observed saved rows: {json.dumps(saved_workspace_rows, indent=2)}\n"
            + "\n".join(f"- {item}" for item in failures)
        )


def _assert_key_kept_panel_open(*, observation: dict[str, object]) -> None:
    switcher = observation["switcher"]
    panel = observation["panel"]
    monitor = observation["monitor"]
    saved_workspace_rows = observation.get("saved_workspace_rows", [])
    assert isinstance(switcher, dict)
    assert isinstance(panel, dict)
    assert isinstance(monitor, dict)
    assert isinstance(saved_workspace_rows, list)

    failures: list[str] = []
    if saved_workspace_rows:
        if len(saved_workspace_rows) <= 0:
            failures.append("no visible saved workspace rows remained in the open switcher")
    elif int(switcher.get("row_count", 0)) <= 0:
        failures.append("no visible workspace rows remained in the open switcher")
    if "Workspace switcher" not in str(switcher.get("switcher_text", "")):
        failures.append("the visible Workspace switcher title was not present")
    if str(panel.get("container_kind")) not in {"anchored-panel", "surface"}:
        failures.append(
            f"the visible container kind became {panel.get('container_kind')!r}",
        )
    if bool(monitor.get("ever_hidden_after_visible")):
        failures.append(
            "the transition monitor observed the panel become hidden after pressing Arrow Up",
        )
    if int(monitor.get("visible_sample_count", 0)) <= 0:
        failures.append(
            "the transition monitor did not capture any visible switcher samples after pressing Arrow Up",
        )
    if failures:
        raise AssertionError(
            "Step 3 failed: pressing Arrow Up did not leave the workspace switcher visibly open.\n"
            + "\n".join(f"- {item}" for item in failures)
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
    error = str(result.get("error", "AssertionError: TS-853 failed"))
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
        "* Opened the deployed TrackState app in Chromium with a stored hosted token and two preloaded saved hosted workspaces.",
        "* Opened the desktop workspace switcher from Dashboard.",
        "* Confirmed the first saved workspace row started as the active/highlighted item.",
        "* Clicked the first saved-workspace row and verified the focused element became the row button inside the open switcher rather than the trigger or global view.",
        "* Pressed Arrow Up and waited for the active saved workspace to wrap to the last visible row while the panel remained open.",
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
        "- Opened the deployed TrackState app in Chromium with a stored hosted token and two preloaded saved hosted workspaces.",
        "- Opened the desktop workspace switcher from Dashboard.",
        "- Confirmed the first saved workspace row started as the active/highlighted item.",
        "- Clicked the first saved-workspace row and verified the focused element became the row button inside the open switcher rather than the trigger or global app view.",
        "- Pressed Arrow Up and waited for the active saved workspace to wrap from Hosted main workspace to Hosted alt workspace while the panel stayed visible.",
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
    status = "passed" if passed else "failed"
    screenshot_path = result.get(
        "screenshot",
        SUCCESS_SCREENSHOT_PATH if passed else FAILURE_SCREENSHOT_PATH,
    )
    lines = [
        f"# {TICKET_KEY} {status}",
        "",
        "## Summary",
        (
            "- Verified the live desktop workspace switcher keeps keyboard focus inside the component and wraps the active selection from the first saved workspace to the last when ArrowUp is pressed."
            if passed
            else f"- Re-run failed: {_failed_step_summary(result)}"
        ),
        "",
        "## Files Modified",
        "- `testing/tests/TS-853/config.yaml`",
        "- `testing/tests/TS-853/README.md`",
        "- `testing/tests/TS-853/test_ts_853.py`",
        "",
        "## Coverage",
        f"- Test case: `{TICKET_KEY} - {TEST_CASE_TITLE}`",
        f"- Result: `{status}`",
        f"- Command: `{RUN_COMMAND}`",
        f"- Screenshot: `{screenshot_path}`",
        (
            f"- Environment: `{result['app_url']}` on Chromium/Playwright "
            f"({result['os']}) against `{result['repository']}` @ "
            f"`{result['repository_ref']}`."
        ),
        f"- Step results: {', '.join(_step_status_summary(result))}",
    ]
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
            f"# {TICKET_KEY} - Arrow Up on the first workspace row does not wrap selection and focus to the last row",
            "",
            "h4. Environment",
            f"* URL: {result.get('app_url')}",
            f"* Repository: {result.get('repository')} @ {result.get('repository_ref')}",
            f"* Browser: {result.get('browser')}",
            f"* OS: {result.get('os')}",
            f"* Viewport: {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
            f"* Run command: {RUN_COMMAND}",
            "",
            "h4. Steps to Reproduce",
            *[f"{index}. {step}" for index, step in enumerate(TEST_CASE_STEPS, start=1)],
            "",
            "h4. Exact steps from the automated run with observations",
            _annotated_step_line(result, 1, AUTOMATION_STEPS[0]),
            _annotated_step_line(result, 2, AUTOMATION_STEPS[1]),
            _annotated_step_line(result, 3, AUTOMATION_STEPS[2]),
            "",
            "h4. Expected Result",
            EXPECTED_RESULT,
            "",
            "h4. Actual Result",
            str(result.get("error", "<missing error>")),
            "",
            "h4. Logs / Error Output",
            "{code}",
            str(result.get("traceback", result.get("error", ""))),
            "{code}",
            "",
            "h4. Notes",
            (
                f"- {result.get('product_gap')}"
                if result.get("product_gap")
                else "- The first-row Arrow Up boundary behavior did not keep selection and focus inside the visible workspace switcher list."
            ),
            "",
            "h4. Screenshots or logs",
            f"- Screenshot: {result.get('screenshot', '<no screenshot recorded>')}",
            (
                f"- Arrow Up observation: {json.dumps(result.get('arrow_up_observation'), indent=2)}"
                if result.get("arrow_up_observation") is not None
                else "- Arrow Up observation: <missing>"
            ),
        ],
    ) + "\n"


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
            if isinstance(step, dict) and step.get("status") == "failed":
                return (
                    f"Step {step.get('step')} ({step.get('action')}) failed: "
                    f"{step.get('observed')}"
                )
    return str(result.get("error", "No failure details recorded."))


def _step_status(result: dict[str, object], step_number: int) -> str:
    steps = result.get("steps", [])
    if not isinstance(steps, list):
        return "failed"
    for step in steps:
        if isinstance(step, dict) and step.get("step") == step_number:
            return str(step.get("status", "failed"))
    return "failed"


def _step_observation(result: dict[str, object], step_number: int) -> str:
    steps = result.get("steps", [])
    if not isinstance(steps, list):
        return "<no observation recorded>"
    for step in steps:
        if isinstance(step, dict) and step.get("step") == step_number:
            return str(step.get("observed", "<no observation recorded>"))
    return "<no observation recorded>"


def _step_status_summary(result: dict[str, object]) -> list[str]:
    steps = result.get("steps", [])
    if not isinstance(steps, list):
        return ["no step data recorded"]
    summary: list[str] = []
    for step in steps:
        if isinstance(step, dict):
            summary.append(f"Step {step.get('step')}: {step.get('status')}")
    return summary or ["no step data recorded"]


def _workspace_state(repository: str) -> dict[str, object]:
    main_id = f"hosted:{repository.lower()}@{DEFAULT_BRANCH}"
    last_id = f"hosted:{repository.lower()}@{DEFAULT_BRANCH}:{LAST_WORKSPACE_WRITE_BRANCH}"
    return {
        "activeWorkspaceId": main_id,
        "migrationComplete": True,
        "profiles": [
            {
                "id": main_id,
                "displayName": FIRST_WORKSPACE_DISPLAY_NAME,
                "customDisplayName": FIRST_WORKSPACE_DISPLAY_NAME,
                "targetType": "hosted",
                "target": repository,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": DEFAULT_BRANCH,
                "lastOpenedAt": "2026-05-18T03:30:00.000Z",
            },
            {
                "id": last_id,
                "displayName": LAST_WORKSPACE_DISPLAY_NAME,
                "customDisplayName": LAST_WORKSPACE_DISPLAY_NAME,
                "targetType": "hosted",
                "target": repository,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": LAST_WORKSPACE_WRITE_BRANCH,
                "lastOpenedAt": "2026-05-18T03:20:00.000Z",
            },
        ],
    }


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


def _saved_workspace_click_point(
    row: WorkspaceSwitcherSavedWorkspaceRowObservation,
) -> tuple[float, float]:
    return (
        row.left + min(40.0, row.width * 0.15),
        row.top + min(28.0, row.height * 0.25),
    )


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


def _selected_saved_workspace(
    rows: tuple[WorkspaceSwitcherSavedWorkspaceRowObservation, ...],
) -> WorkspaceSwitcherSavedWorkspaceRowObservation | None:
    for row in rows:
        if row.selected:
            return row
    return None


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


def _snippet(text: str, limit: int = 160) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1] + "…"


if __name__ == "__main__":
    main()
