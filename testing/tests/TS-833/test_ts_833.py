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

TICKET_KEY = "TS-833"
TEST_CASE_TITLE = (
    "Press Arrow Down in workspace switcher — active selection moves to next workspace"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-833/test_ts_833.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 960}
KEY_STABILITY_MS = 1_000
DEFAULT_BRANCH = "main"
ACTIVE_WORKSPACE_DISPLAY_NAME = "Hosted main workspace"
SECONDARY_WORKSPACE_DISPLAY_NAME = "Hosted alt workspace"
SECONDARY_WRITE_BRANCH = "ts-833-alt"
TEST_CASE_STEPS = [
    "Observe the list of workspaces and note which one is currently highlighted/selected (e.g., 'Hosted main workspace').",
    "Press the 'Arrow Down' key.",
]
AUTOMATION_STEPS = [
    TEST_CASE_STEPS[0],
    "Click the active saved-workspace row and confirm the open saved-workspace list interaction target is engaged before pressing Arrow Down.",
    TEST_CASE_STEPS[1],
]
EXPECTED_RESULT = (
    "The active selection indicator moves from the current workspace to the next "
    "saved workspace in the list (e.g., 'Hosted alt workspace'), while the panel remains open."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
INPUTS_DIR = REPO_ROOT / "input" / TICKET_KEY
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
REVIEW_REPLIES_PATH = OUTPUTS_DIR / "review_replies.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
DISCUSSIONS_RAW_PATH = INPUTS_DIR / "pr_discussions_raw.json"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts833_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts833_failure.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-833 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
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
        "linked_bugs": ["TS-827", "TS-836"],
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
                            "desktop state before the Arrow Down scenario began.\n"
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
                    result["saved_workspace_rows_before_arrow"] = _saved_workspace_rows_payload(
                        saved_workspace_rows,
                    )
                    result["active_workspace_before_arrow"] = active_workspace.display_name
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
                        "the Workspace switcher title plus the saved workspace list were visible "
                        "and that Hosted main workspace was marked active before pressing Arrow Down."
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
                    page.click_saved_workspace_row_surface(ACTIVE_WORKSPACE_DISPLAY_NAME)
                    page.wait_for_surface_to_remain_open(
                        stability_ms=KEY_STABILITY_MS,
                        timeout_ms=4_000,
                    )
                    saved_workspace_rows_after_click = page.observe_saved_workspace_rows(
                        timeout_ms=4_000,
                    )
                    focus_precondition = page.observe_focus_ownership(panel=panel)
                    result["focus_precondition"] = _focus_ownership_payload(
                        focus_precondition,
                    )
                    result["saved_workspace_rows_after_click"] = _saved_workspace_rows_payload(
                        saved_workspace_rows_after_click,
                    )
                    _assert_arrow_down_interaction_precondition(
                        observation=focus_precondition,
                        clicked_x=click_x,
                        clicked_y=click_y,
                        expected_workspace_name=active_workspace.display_name,
                        saved_workspace_rows=saved_workspace_rows_after_click,
                    )
                except AssertionError as error:
                    result["product_gap"] = (
                        "Clicking the active saved-workspace row does not transfer keyboard "
                        "focus to a switcher-owned target inside the open panel, so the "
                        "saved-workspace list cannot be exercised from a validated Arrow Down "
                        "keyboard state."
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
                        f"active_workspace_after_click={_selected_saved_workspace(saved_workspace_rows_after_click).display_name if _selected_saved_workspace(saved_workspace_rows_after_click) is not None else None!r}; "
                        f"focus_owned_by_switcher={focus_precondition.focus_owned_by_switcher}; "
                        f"active_within_switcher={focus_precondition.active_within_switcher}; "
                        f"active_on_trigger={focus_precondition.active_on_trigger}; "
                        f"focus_label={focus_precondition.active_label!r}; "
                        f"focus_role={focus_precondition.active_role!r}; "
                        f"focus_tag={focus_precondition.active_tag_name!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Clicked the active saved-workspace row and confirmed the visible "
                        "saved-workspace list stayed on that row as the last user-targeted "
                        "interaction point before pressing Arrow Down."
                    ),
                    observed=(
                        f"click_point=({click_x:.1f}, {click_y:.1f}); "
                        f"active_workspace_after_click={_selected_saved_workspace(saved_workspace_rows_after_click).display_name if _selected_saved_workspace(saved_workspace_rows_after_click) is not None else None!r}; "
                        f"focus_label={focus_precondition.active_label!r}; "
                        f"focus_role={focus_precondition.active_role!r}; "
                        f"focus_within_switcher={focus_precondition.active_within_switcher}; "
                        f"focus_owned_by_switcher={focus_precondition.focus_owned_by_switcher}; "
                        f"focus_on_trigger={focus_precondition.active_on_trigger}"
                    ),
                )

                arrow_down = _press_key_and_observe(page=page, key="ArrowDown")
                result["arrow_down_observation"] = arrow_down
                try:
                    _assert_arrow_down_navigated_between_workspaces(
                        observation=arrow_down,
                        before_active_workspace=active_workspace.display_name,
                        expected_active_workspace=SECONDARY_WORKSPACE_DISPLAY_NAME,
                    )
                except Exception as error:
                    result["product_gap"] = (
                        "Pressing Arrow Down after clicking the active saved-workspace row "
                        "did not move the active saved workspace to the next visible row."
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
                        f"panel_kind={arrow_down['panel']['container_kind']}; "
                        f"saved_workspace_row_count={len(arrow_down['saved_workspace_rows'])}; "
                        f"active_workspace_before={active_workspace.display_name!r}; "
                        f"active_workspace_after={arrow_down['active_workspace_name']!r}; "
                        f"monitor_hidden_after_visible={arrow_down['monitor']['ever_hidden_after_visible']}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Pressed Arrow Down in the open workspace switcher and "
                        "watched the active selection change the way a desktop user would."
                    ),
                    observed=(
                        f"active_before_arrow={active_workspace.display_name!r}; "
                        f"active_after_arrow={arrow_down['active_workspace_name']!r}; "
                        f"focus_after={arrow_down['active']['accessible_name']!r}; "
                        f"panel_hidden_after_arrow={arrow_down['monitor']['ever_hidden_after_visible']}; "
                        f"text_excerpt={_snippet(str(arrow_down['switcher']['switcher_text']))!r}"
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


def _press_key_and_observe(
    *,
    page: LiveWorkspaceSwitcherPage,
    key: str,
) -> dict[str, object]:
    page.start_transition_monitor()
    page.press_key(key)
    page.wait_for_surface_to_remain_open(
        stability_ms=KEY_STABILITY_MS,
        timeout_ms=4_000,
    )
    switcher = page.observe_open_switcher(timeout_ms=4_000)
    panel = page.observe_open_panel(
        expected_container_kinds=("anchored-panel", "surface"),
        timeout_ms=4_000,
    )
    active = page.active_element()
    saved_workspace_rows = page.observe_saved_workspace_rows(timeout_ms=4_000)
    monitor = page.read_transition_monitor(clear=True)
    active_workspace = _selected_saved_workspace(saved_workspace_rows)
    return {
        "key": key,
        "switcher": _switcher_payload(switcher),
        "panel": asdict(panel),
        "active": _focused_element_payload(active),
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
            "two saved workspace rows needed to exercise Arrow Down navigation.\n"
            f"Observed rows: {json.dumps(_saved_workspace_rows_payload(rows), indent=2)}",
        )
    active_workspace = _selected_saved_workspace(rows)
    if active_workspace is None:
        raise AssertionError(
            "Step 1 failed: none of the visible saved workspace rows was marked "
            "active before pressing Arrow Down.\n"
            f"Observed rows: {json.dumps(_saved_workspace_rows_payload(rows), indent=2)}",
        )
    if active_workspace.display_name != ACTIVE_WORKSPACE_DISPLAY_NAME:
        raise AssertionError(
            "Step 1 failed: the preloaded active saved workspace was not the expected "
            "Arrow Down starting point.\n"
            f"Observed active workspace: {active_workspace.display_name!r}\n"
            f"Observed rows: {json.dumps(_saved_workspace_rows_payload(rows), indent=2)}",
        )
    return active_workspace


def _assert_arrow_down_interaction_precondition(
    *,
    observation: WorkspaceSwitcherFocusOwnershipObservation,
    clicked_x: float,
    clicked_y: float,
    expected_workspace_name: str,
    saved_workspace_rows: tuple[WorkspaceSwitcherSavedWorkspaceRowObservation, ...],
) -> None:
    active_workspace = _selected_saved_workspace(saved_workspace_rows)
    failures: list[str] = []
    if not observation.focus_owned_by_switcher:
        failures.append(
            "keyboard focus was not owned by the open workspace switcher after clicking the active row",
        )
    if not observation.active_within_switcher:
        failures.append(
            "the focused element remained outside the open workspace switcher after clicking the active row",
        )
    if observation.active_on_trigger:
        failures.append(
            "keyboard focus remained on the workspace-switcher trigger after clicking the active row",
        )
    if len(saved_workspace_rows) < 2:
        failures.append("fewer than two saved workspace rows remained visible after clicking the active row")
    if active_workspace is None:
        failures.append("no saved workspace row remained active after clicking the active row")
    elif active_workspace.display_name != expected_workspace_name:
        failures.append(
            f"the active saved workspace changed to {active_workspace.display_name!r} before Arrow Down instead of remaining on {expected_workspace_name!r}",
        )
    active_row = next(
        (
            row
            for row in saved_workspace_rows
            if row.display_name == expected_workspace_name
        ),
        None,
    )
    if active_row is None:
        failures.append(
            f"the clicked saved workspace row {expected_workspace_name!r} was not visible after the precondition click",
        )
    else:
        right = active_row.left + active_row.width
        bottom = active_row.top + active_row.height
        if not (
            active_row.left <= clicked_x <= right
            and active_row.top <= clicked_y <= bottom
        ):
            failures.append(
                "the saved-workspace precondition click did not land within the visible active-row bounds",
            )

    if failures:
        raise AssertionError(
            "Step 2 failed: clicking the active saved workspace row did not establish a "
            "valid saved-workspace interaction precondition before pressing Arrow Down.\n"
            + "\n".join(f"- {item}" for item in failures)
            + "\n"
            + f"Expected active workspace row: {expected_workspace_name!r}\n"
            + f"Clicked point: ({clicked_x:.1f}, {clicked_y:.1f})\n"
            + f"Observed focus label: {observation.active_label!r}\n"
            + f"Observed focus role: {observation.active_role!r}\n"
            + f"Observed focus tag: {observation.active_tag_name!r}\n"
            + f"Observed focus HTML: {observation.active_outer_html}\n"
            + f"Observed rows after click: {json.dumps(_saved_workspace_rows_payload(saved_workspace_rows), indent=2)}"
        )


def _assert_arrow_down_navigated_between_workspaces(
    *,
    observation: dict[str, object],
    before_active_workspace: str,
    expected_active_workspace: str,
) -> None:
    _assert_key_kept_panel_open(key="Arrow Down", observation=observation)
    saved_workspace_rows = observation["saved_workspace_rows"]
    active_workspace_name = observation["active_workspace_name"]
    assert isinstance(saved_workspace_rows, list)

    failures: list[str] = []
    if len(saved_workspace_rows) < 2:
        failures.append("fewer than two saved workspace rows remained visible after Arrow Down")
    if active_workspace_name == before_active_workspace:
        failures.append(
            f"the active saved workspace stayed on {before_active_workspace!r} instead of moving",
        )
    if active_workspace_name != expected_active_workspace:
        failures.append(
            f"the active saved workspace became {active_workspace_name!r} instead of "
            f"{expected_active_workspace!r}",
        )
    if failures:
        raise AssertionError(
            "Step 3 failed: pressing Arrow Down from the visible saved-workspace "
            "switcher did not navigate to another workspace while the panel remained "
            "open.\n"
            f"Active workspace before Arrow Down: {before_active_workspace!r}\n"
            f"Active workspace after Arrow Down: {active_workspace_name!r}\n"
            f"Observed saved rows: {json.dumps(saved_workspace_rows, indent=2)}\n"
            + "\n".join(f"- {item}" for item in failures)
        )


def _assert_key_kept_panel_open(
    *,
    key: str,
    observation: dict[str, object],
) -> None:
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
            f"the transition monitor observed the panel become hidden after pressing {key}",
        )
    if int(monitor.get("visible_sample_count", 0)) <= 0:
        failures.append(
            f"the transition monitor did not capture any visible switcher samples after pressing {key}",
        )

    if failures:
        raise AssertionError(
            f"Step 3 failed: pressing {key} did not leave the workspace switcher visibly open.\n"
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
    _write_review_replies(result, passed=True)
    JIRA_COMMENT_PATH.write_text(_jira_comment(result, passed=True), encoding="utf-8")
    PR_BODY_PATH.write_text(_markdown_summary(result, passed=True), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_summary(result, passed=True), encoding="utf-8")


def _write_failure_outputs(result: dict[str, object]) -> None:
    error = str(result.get("error", "AssertionError: TS-833 failed"))
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
    _write_review_replies(result, passed=False)
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
        "* Opened the deployed TrackState app in Chromium with a stored hosted token and two preloaded saved hosted workspaces.",
        "* Opened the desktop workspace switcher from Dashboard.",
        "* Observed the currently selected saved workspace in the open desktop workspace switcher.",
        "* Clicked the active saved-workspace row and confirmed the list interaction target stayed on that row before sending Arrow Down.",
        "* Pressed Arrow Down and checked whether the active saved workspace moved to the next row while the panel stayed open.",
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
        "## What was automated",
        "- Opened the deployed TrackState app in Chromium with a stored hosted token and two preloaded saved hosted workspaces.",
        "- Opened the desktop workspace switcher from Dashboard.",
        "- Observed the currently selected saved workspace in the open desktop workspace switcher.",
        "- Clicked the active saved-workspace row and confirmed the list interaction target stayed on that row before sending Arrow Down.",
        "- Pressed Arrow Down and checked whether the active saved workspace moved to the next row while the panel stayed visible.",
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
        "- Added TS-833 live desktop coverage for Arrow Down workspace-switcher navigation.",
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
            else "- Outcome: Arrow Down moved the active saved workspace from Hosted main workspace to Hosted alt workspace while the panel remained visibly open."
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
            f"# {TICKET_KEY} - Arrow Down does not move the active saved workspace in the workspace switcher",
            "",
            "## Steps to reproduce",
            *[f"{index}. {step}" for index, step in enumerate(TEST_CASE_STEPS, start=1)],
            "",
            "## Exact steps from the automated run with observations",
            _annotated_step_line(result, 1, AUTOMATION_STEPS[0]),
            _annotated_step_line(result, 2, AUTOMATION_STEPS[1]),
            _annotated_step_line(result, 3, AUTOMATION_STEPS[2]),
            "",
            "## Exact error message or assertion failure",
            "```text",
            str(result.get("traceback", result.get("error", ""))),
            "```",
            "",
            "## Actual vs Expected",
            f"- Expected: {EXPECTED_RESULT}",
            f"- Actual: {result.get('error', '<missing error>')}",
            "",
            "## Missing or broken production capability",
            (
                f"- {result.get('product_gap')}"
                if result.get("product_gap")
                else "- Pressing Arrow Down in the open workspace switcher does not move the active selection to the next saved workspace."
            ),
            "",
            "## Environment details",
            f"- URL: {result.get('app_url')}",
            (
                f"- Repository: {result.get('repository')} @ "
                f"{result.get('repository_ref')}"
            ),
            f"- Browser: {result.get('browser')}",
            f"- OS: {result.get('os')}",
            f"- Viewport: {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
            f"- Run command: {RUN_COMMAND}",
            "",
            "## Screenshots or logs",
            f"- Screenshot: {result.get('screenshot', '<no screenshot recorded>')}",
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


def _write_review_replies(result: dict[str, object], *, passed: bool) -> None:
    replies = [
        {
            "inReplyToId": thread.get("rootCommentId"),
            "threadId": thread.get("threadId"),
            "reply": _review_reply_text(passed=passed, result=result),
        }
        for thread in _discussion_threads()
    ]
    REVIEW_REPLIES_PATH.write_text(
        json.dumps({"replies": replies}) + "\n",
        encoding="utf-8",
    )


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
        "Re-ran "
        f"`{RUN_COMMAND}`: passed (`1 passed, 0 failed`)."
        if passed
        else "Re-ran "
        f"`{RUN_COMMAND}`: failed at {_failed_step_summary(result)}"
    )
    return (
        "Fixed: Step 2 now asserts the saved-row focus-ownership probe after the click, "
        "requiring visible switcher-owned focus inside the open panel and off the trigger "
        "before `ArrowDown`. "
        + rerun_summary
    )


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


def _workspace_state(repository: str) -> dict[str, object]:
    main_id = f"hosted:{repository.lower()}@{DEFAULT_BRANCH}"
    secondary_id = f"hosted:{repository.lower()}@{DEFAULT_BRANCH}:{SECONDARY_WRITE_BRANCH}"
    return {
        "activeWorkspaceId": main_id,
        "migrationComplete": True,
        "profiles": [
            {
                "id": main_id,
                "displayName": ACTIVE_WORKSPACE_DISPLAY_NAME,
                "customDisplayName": ACTIVE_WORKSPACE_DISPLAY_NAME,
                "targetType": "hosted",
                "target": repository,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": DEFAULT_BRANCH,
                "lastOpenedAt": "2026-05-18T03:30:00.000Z",
            },
            {
                "id": secondary_id,
                "displayName": SECONDARY_WORKSPACE_DISPLAY_NAME,
                "customDisplayName": SECONDARY_WORKSPACE_DISPLAY_NAME,
                "targetType": "hosted",
                "target": repository,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": SECONDARY_WRITE_BRANCH,
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


def _snippet(text: str, *, length: int = 220) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= length:
        return normalized
    return normalized[: length - 3] + "..."


if __name__ == "__main__":
    main()
