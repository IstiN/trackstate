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

TICKET_KEY = "TS-868"
TEST_CASE_TITLE = (
    "Home and End keys navigation in switcher — selection and focus move to list boundaries"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-868/test_ts_868.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 960}
KEY_STABILITY_MS = 1_000
DEFAULT_BRANCH = "main"
FIRST_WORKSPACE_DISPLAY_NAME = "Hosted main workspace"
SECOND_WORKSPACE_DISPLAY_NAME = "Hosted alt workspace"
LAST_WORKSPACE_DISPLAY_NAME = "Hosted end workspace"
SECOND_WORKSPACE_WRITE_BRANCH = "ts-868-alt"
LAST_WORKSPACE_WRITE_BRANCH = "ts-868-end"
LINKED_BUGS = ["TS-866", "TS-869"]

PRECONDITIONS = [
    "The workspace switcher panel is open.",
    "At least three saved workspaces exist.",
    "The second workspace row is currently selected.",
]
REQUEST_STEPS = [
    "Press the Home key.",
    "Press the End key.",
]
AUTOMATION_STEPS = [
    "Open the desktop workspace switcher and confirm at least three saved workspace rows are visible with Hosted main workspace active first.",
    "Press Arrow Down once to establish the ticket precondition that Hosted alt workspace is the selected and focused row.",
    "Press Home and verify Hosted main workspace becomes the selected and focused row button while the switcher remains open.",
    "Press End and verify Hosted end workspace becomes the selected and focused row button while the switcher remains open.",
]
EXPECTED_RESULT = (
    "Pressing the Home key immediately moves both the visual selection indicator and "
    "the programmatic DOM focus to the first workspace row. Pressing the End key moves "
    "both the indicator and focus to the last workspace row in the list."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
REVIEW_REPLIES_PATH = OUTPUTS_DIR / "review_replies.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts868_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts868_failure.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-868 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
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
        "linked_bugs": LINKED_BUGS,
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
                switcher: WorkspaceSwitcherObservation | None = None
                panel: WorkspaceSwitcherPanelObservation | None = None
                saved_workspace_rows: tuple[WorkspaceSwitcherSavedWorkspaceRowObservation, ...] = ()
                active_workspace: WorkspaceSwitcherSavedWorkspaceRowObservation | None = None
                try:
                    runtime = tracker_page.open()
                    result["runtime_state"] = runtime.kind
                    result["runtime_body_text"] = runtime.body_text
                    if runtime.kind != "ready":
                        raise AssertionError(
                            "Step 1 failed: the deployed app did not reach an interactive "
                            "desktop state before the Home/End navigation scenario began.\n"
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
                    result["saved_workspace_rows_before_keys"] = _saved_workspace_rows_payload(
                        saved_workspace_rows,
                    )
                    result["active_workspace_before_keys"] = active_workspace.display_name
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
                        f"first_row={saved_workspace_rows[0].display_name!r}; "
                        f"second_row={saved_workspace_rows[1].display_name!r}; "
                        f"last_row={saved_workspace_rows[-1].display_name!r}; "
                        f"active_workspace={active_workspace.display_name!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Opened the desktop workspace switcher and visually confirmed the "
                        "Workspace switcher title plus three saved workspace rows were visible "
                        "with Hosted main workspace highlighted first."
                    ),
                    observed=(
                        "title='Workspace switcher'; "
                        f"saved_workspace_row_count={len(saved_workspace_rows)}; "
                        f"first_row={saved_workspace_rows[0].display_name!r}; "
                        f"second_row={saved_workspace_rows[1].display_name!r}; "
                        f"last_row={saved_workspace_rows[-1].display_name!r}; "
                        f"text_excerpt={_snippet(switcher.switcher_text)!r}"
                    ),
                )

                arrow_down_observation: dict[str, object] | None = None
                try:
                    arrow_down_observation = _press_key_and_observe(
                        page=page,
                        key="ArrowDown",
                        expected_active_workspace=SECOND_WORKSPACE_DISPLAY_NAME,
                    )
                    result["arrow_down_precondition_observation"] = arrow_down_observation
                    _assert_key_moved_to_workspace_row(
                        observation=arrow_down_observation,
                        key="ArrowDown",
                        before_active_workspace=FIRST_WORKSPACE_DISPLAY_NAME,
                        expected_active_workspace=SECOND_WORKSPACE_DISPLAY_NAME,
                    )
                except Exception as error:
                    result["product_gap"] = (
                        "The linked ArrowDown focus-management fix could not establish the "
                        "TS-868 precondition because selection and keyboard focus did not "
                        "both land on the second saved workspace row button."
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
                        f"active_workspace_after_arrow={arrow_down_observation['active_workspace_name']!r}; "
                        f"focused_label_after_arrow={arrow_down_observation['active']['accessible_name']!r}; "
                        f"focus_on_trigger={arrow_down_observation['focus']['active_on_trigger']}; "
                        f"row_contains_active={arrow_down_observation['row_focus']['row_contains_active']}; "
                        f"panel_hidden_after_arrow={arrow_down_observation['monitor']['ever_hidden_after_visible']}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Pressed Arrow Down once in the open switcher to reach the ticket "
                        "precondition and watched Hosted alt workspace become the selected "
                        "row with keyboard focus on that row button."
                    ),
                    observed=(
                        f"active_after_arrow={arrow_down_observation['active_workspace_name']!r}; "
                        f"focus_after_arrow={arrow_down_observation['active']['accessible_name']!r}; "
                        f"row_text_after_arrow={_snippet(str(arrow_down_observation['row_focus']['row_text']))!r}"
                    ),
                )

                home_observation: dict[str, object] | None = None
                try:
                    home_observation = _press_key_and_observe(
                        page=page,
                        key="Home",
                        expected_active_workspace=FIRST_WORKSPACE_DISPLAY_NAME,
                    )
                    result["home_observation"] = home_observation
                    _assert_key_moved_to_workspace_row(
                        observation=home_observation,
                        key="Home",
                        before_active_workspace=SECOND_WORKSPACE_DISPLAY_NAME,
                        expected_active_workspace=FIRST_WORKSPACE_DISPLAY_NAME,
                    )
                except Exception as error:
                    result["product_gap"] = (
                        "Pressing Home from the second saved workspace row does not move "
                        "both selection and DOM focus to the first saved workspace row button "
                        "while the switcher remains open."
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
                        f"active_workspace_after_home={home_observation['active_workspace_name']!r}; "
                        f"focused_label_after_home={home_observation['active']['accessible_name']!r}; "
                        f"focus_on_trigger={home_observation['focus']['active_on_trigger']}; "
                        f"row_contains_active={home_observation['row_focus']['row_contains_active']}; "
                        f"panel_hidden_after_home={home_observation['monitor']['ever_hidden_after_visible']}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Pressed Home from the selected second row and watched the visible "
                        "highlight plus keyboard focus jump to Hosted main workspace at the "
                        "top of the list."
                    ),
                    observed=(
                        f"active_after_home={home_observation['active_workspace_name']!r}; "
                        f"focus_after_home={home_observation['active']['accessible_name']!r}; "
                        f"row_text_after_home={_snippet(str(home_observation['row_focus']['row_text']))!r}"
                    ),
                )

                end_observation: dict[str, object] | None = None
                try:
                    end_observation = _press_key_and_observe(
                        page=page,
                        key="End",
                        expected_active_workspace=LAST_WORKSPACE_DISPLAY_NAME,
                    )
                    result["end_observation"] = end_observation
                    _assert_key_moved_to_workspace_row(
                        observation=end_observation,
                        key="End",
                        before_active_workspace=FIRST_WORKSPACE_DISPLAY_NAME,
                        expected_active_workspace=LAST_WORKSPACE_DISPLAY_NAME,
                    )
                except Exception as error:
                    result["product_gap"] = (
                        "Pressing End from the first saved workspace row does not move both "
                        "selection and DOM focus to the last saved workspace row button while "
                        "the switcher remains open."
                    )
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
                        f"active_workspace_after_end={end_observation['active_workspace_name']!r}; "
                        f"focused_label_after_end={end_observation['active']['accessible_name']!r}; "
                        f"focus_on_trigger={end_observation['focus']['active_on_trigger']}; "
                        f"row_contains_active={end_observation['row_focus']['row_contains_active']}; "
                        f"panel_hidden_after_end={end_observation['monitor']['ever_hidden_after_visible']}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Pressed End immediately after Home and watched the visible highlight "
                        "plus keyboard focus jump to Hosted end workspace at the bottom of the list."
                    ),
                    observed=(
                        f"active_after_end={end_observation['active_workspace_name']!r}; "
                        f"focus_after_end={end_observation['active']['accessible_name']!r}; "
                        f"row_text_after_end={_snippet(str(end_observation['row_focus']['row_text']))!r}"
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
    expected_active_workspace: str,
) -> dict[str, object]:
    page.start_transition_monitor()
    page.press_key(key)
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
        "key": key,
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
            f"Observed trigger bounds: left={trigger.left:.1f}, top={trigger.top:.1f}, "
            f"width={trigger.width:.1f}, height={trigger.height:.1f}",
        )


def _assert_saved_workspace_navigation_ready(
    rows: tuple[WorkspaceSwitcherSavedWorkspaceRowObservation, ...],
) -> WorkspaceSwitcherSavedWorkspaceRowObservation:
    if len(rows) < 3:
        raise AssertionError(
            "Step 1 failed: the visible workspace switcher did not expose at least "
            "three saved workspace rows needed to exercise Home and End boundary navigation.\n"
            f"Observed rows: {json.dumps(_saved_workspace_rows_payload(rows), indent=2)}",
        )
    active_workspace = _selected_saved_workspace(rows)
    if active_workspace is None:
        raise AssertionError(
            "Step 1 failed: none of the visible saved workspace rows was marked "
            "active before the Home/End navigation scenario began.\n"
            f"Observed rows: {json.dumps(_saved_workspace_rows_payload(rows), indent=2)}",
        )
    failures: list[str] = []
    if active_workspace.display_name != FIRST_WORKSPACE_DISPLAY_NAME:
        failures.append(
            f"the active saved workspace was {active_workspace.display_name!r} instead of "
            f"{FIRST_WORKSPACE_DISPLAY_NAME!r}",
        )
    if rows[0].display_name != FIRST_WORKSPACE_DISPLAY_NAME:
        failures.append(
            f"the first visible row was {rows[0].display_name!r} instead of "
            f"{FIRST_WORKSPACE_DISPLAY_NAME!r}",
        )
    if rows[1].display_name != SECOND_WORKSPACE_DISPLAY_NAME:
        failures.append(
            f"the second visible row was {rows[1].display_name!r} instead of "
            f"{SECOND_WORKSPACE_DISPLAY_NAME!r}",
        )
    if rows[-1].display_name != LAST_WORKSPACE_DISPLAY_NAME:
        failures.append(
            f"the last visible row was {rows[-1].display_name!r} instead of "
            f"{LAST_WORKSPACE_DISPLAY_NAME!r}",
        )
    if failures:
        raise AssertionError(
            "Step 1 failed: the preloaded workspace rows were not in the expected order for "
            "the Home/End boundary scenario.\n"
            f"Observed rows: {json.dumps(_saved_workspace_rows_payload(rows), indent=2)}\n"
            + "\n".join(f"- {item}" for item in failures)
        )
    return active_workspace


def _assert_key_moved_to_workspace_row(
    *,
    observation: dict[str, object],
    key: str,
    before_active_workspace: str,
    expected_active_workspace: str,
) -> None:
    _assert_key_kept_panel_open(key=key, observation=observation)
    active = observation["active"]
    focus = observation["focus"]
    row_focus = observation["row_focus"]
    saved_workspace_rows = observation["saved_workspace_rows"]
    active_workspace_name = observation["active_workspace_name"]
    assert isinstance(active, dict)
    assert isinstance(focus, dict)
    assert isinstance(row_focus, dict)
    assert isinstance(saved_workspace_rows, list)
    active_label = str(active.get("accessible_name") or "")
    active_text = str(active.get("text") or "")

    failures: list[str] = []
    if len(saved_workspace_rows) < 3:
        failures.append("fewer than three saved workspace rows remained visible after the key press")
    if active_workspace_name == before_active_workspace:
        failures.append(
            f"the active saved workspace stayed on {before_active_workspace!r} instead of moving to {expected_active_workspace!r}",
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
            f"the row-focus probe could not find the expected saved workspace row {expected_active_workspace!r}",
        )
    if not bool(row_focus.get("row_contains_active")):
        failures.append("the focused element was not contained by the expected saved-workspace row")
    if str(active.get("role")) != "button":
        failures.append(
            f"the active element role was {active.get('role')!r} instead of the saved-workspace row button",
        )
    if expected_active_workspace not in active_label and expected_active_workspace not in active_text:
        failures.append(
            "the active element label did not identify the expected saved workspace row",
        )
    if "Branch:" not in active_label and "Branch:" not in active_text:
        failures.append(
            "the active element label did not expose the saved workspace row details",
        )
    if "Delete:" in active_label or "Delete:" in active_text:
        failures.append(
            "the active element was a nested Delete control instead of the saved workspace row button",
        )
    if failures:
        raise AssertionError(
            f"Step failed: pressing {key} did not move selection and focus to the expected "
            "saved workspace row button while the panel remained open.\n"
            f"Active workspace before {key}: {before_active_workspace!r}\n"
            f"Active workspace after {key}: {active_workspace_name!r}\n"
            f"Observed active element: {json.dumps(active, indent=2)}\n"
            f"Observed focus ownership: {json.dumps(focus, indent=2)}\n"
            f"Observed row focus: {json.dumps(row_focus, indent=2)}\n"
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
    if not saved_workspace_rows:
        failures.append("no visible saved workspace rows remained in the open switcher")
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
    if failures:
        raise AssertionError(
            f"Pressing {key} did not leave the workspace switcher visibly open.\n"
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
    _write_review_replies()


def _write_failure_outputs(result: dict[str, object]) -> None:
    error = str(result.get("error", "AssertionError: TS-868 failed"))
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
    _write_review_replies()
    BUG_DESCRIPTION_PATH.write_text(_bug_description(result), encoding="utf-8")


def _write_review_replies() -> None:
    REVIEW_REPLIES_PATH.write_text(
        json.dumps({"replies": []}) + "\n",
        encoding="utf-8",
    )


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
        "* Opened the deployed TrackState app in Chromium with a stored hosted token and three preloaded saved hosted workspaces.",
        "* Opened the desktop workspace switcher from Dashboard.",
        "* Established the ticket precondition by moving selection and focus to Hosted alt workspace with Arrow Down.",
        "* Pressed Home and verified the active selection plus DOM focus moved to Hosted main workspace while the switcher remained open.",
        "* Pressed End and verified the active selection plus DOM focus moved to Hosted end workspace while the switcher remained open.",
        "",
        "h4. Result",
        (
            "* Matched the expected result."
            if passed
            else f"* Did not match the expected result. {_failed_step_summary(result)}"
        ),
        f"* Expected result: {EXPECTED_RESULT}",
        (
            f"* Actual result: {_actual_result_summary(result)}"
            if not passed
            else "* Actual result: Home moved selection and focus to the first row, and End moved selection and focus to the last row, in the live UI."
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
        "- Opened the deployed TrackState app in Chromium with a stored hosted token and three preloaded saved hosted workspaces.",
        "- Opened the desktop workspace switcher from Dashboard.",
        "- Established the ticket precondition by moving selection and focus to Hosted alt workspace with ArrowDown.",
        "- Pressed Home and verified the active selection plus DOM focus moved to Hosted main workspace while the switcher stayed visible.",
        "- Pressed End and verified the active selection plus DOM focus moved to Hosted end workspace while the switcher stayed visible.",
        "",
        "## Result",
        (
            "- Matched the expected result."
            if passed
            else f"- Did not match the expected result. {_failed_step_summary(result)}"
        ),
        f"- Expected result: {EXPECTED_RESULT}",
        (
            f"- Actual result: {_actual_result_summary(result)}"
            if not passed
            else "- Actual result: Home moved selection and focus to the first row, and End moved selection and focus to the last row, in the live UI."
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
            "- Verified the live desktop workspace switcher moves both selection and DOM focus to the first row on Home and to the last row on End after the second-row precondition is established."
            if passed
            else f"- Re-run failed: {_failed_step_summary(result)}"
        ),
        "",
        "## Files Modified",
        "- `testing/tests/TS-868/config.yaml`",
        "- `testing/tests/TS-868/README.md`",
        "- `testing/tests/TS-868/test_ts_868.py`",
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
            f"# {TICKET_KEY} - Home/End boundary navigation in the workspace switcher does not match the expected focus behavior",
            "",
            "## Exact steps to reproduce",
            *_ticket_reproduction_lines(result),
            "",
            "## Expected result",
            EXPECTED_RESULT,
            "",
            "## Actual vs Expected",
            f"- Expected: {EXPECTED_RESULT}",
            f"- Actual: {_actual_result_summary(result)}",
            "",
            "## Missing or broken production capability",
            (
                "The live workspace switcher does not fully support the requested boundary "
                "keyboard navigation path. Either the ArrowDown precondition cannot place both "
                "selection and focus on the second row, or Home/End does not keep the visible "
                "switcher open while moving both selection and DOM focus to the expected boundary row button."
            ),
            "",
            "## Exact error message or assertion failure",
            "```text",
            str(result.get("traceback", result.get("error", ""))),
            "```",
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
            f"- Screenshot: `{result.get('screenshot', '<no screenshot recorded>')}`",
            (
                f"- ArrowDown precondition observation: ```json\n{json.dumps(result.get('arrow_down_precondition_observation'), indent=2)}\n```"
                if result.get("arrow_down_precondition_observation") is not None
                else "- ArrowDown precondition observation: <missing>"
            ),
            (
                f"- Home observation: ```json\n{json.dumps(result.get('home_observation'), indent=2)}\n```"
                if result.get("home_observation") is not None
                else "- Home observation: <missing>"
            ),
            (
                f"- End observation: ```json\n{json.dumps(result.get('end_observation'), indent=2)}\n```"
                if result.get("end_observation") is not None
                else "- End observation: <missing>"
            ),
            (
                f"- Product gap: {result.get('product_gap')}"
                if result.get("product_gap")
                else "- Product gap: the live UI did not complete the requested Home/End focus traversal path."
            ),
        ],
    ) + "\n"


def _ticket_reproduction_lines(result: dict[str, object]) -> list[str]:
    step1_status = _step_status(result, 1)
    step2_status = _step_status(result, 2)
    step3_status = _step_status(result, 3)
    step4_status = _step_status(result, 4)
    rows = result.get("saved_workspace_rows_before_keys")
    row_count = len(rows) if isinstance(rows, list) else 0
    active_before = result.get("active_workspace_before_keys", "<unknown>")

    arrow_down = result.get("arrow_down_precondition_observation")
    arrow_after = (
        arrow_down.get("active_workspace_name")
        if isinstance(arrow_down, dict)
        else "<unknown>"
    )
    arrow_focus = arrow_down.get("active") if isinstance(arrow_down, dict) else None
    arrow_focus_label = (
        _snippet(str(arrow_focus.get("accessible_name") or arrow_focus.get("text") or ""))
        if isinstance(arrow_focus, dict)
        else "<missing>"
    )

    home = result.get("home_observation")
    home_after = home.get("active_workspace_name") if isinstance(home, dict) else "<unknown>"
    home_focus = home.get("active") if isinstance(home, dict) else None
    home_focus_label = (
        _snippet(str(home_focus.get("accessible_name") or home_focus.get("text") or ""))
        if isinstance(home_focus, dict)
        else "<missing>"
    )

    end = result.get("end_observation")
    end_after = end.get("active_workspace_name") if isinstance(end, dict) else "<unknown>"
    end_focus = end.get("active") if isinstance(end, dict) else None
    end_focus_label = (
        _snippet(str(end_focus.get("accessible_name") or end_focus.get("text") or ""))
        if isinstance(end_focus, dict)
        else "<missing>"
    )

    lines = [
        (
            f"1. Open the workspace switcher panel with at least three saved workspaces visible — "
            f"{'✅' if step1_status == 'passed' else '❌'} Observed `saved_workspace_row_count={row_count}` "
            f"and `active_workspace_before_keys={active_before!r}`. {_step_observation(result, 1)}"
        ),
        (
            f"2. Ensure the second workspace row is currently selected — "
            f"{'✅' if step2_status == 'passed' else '❌'} Observed "
            f"`active_workspace_after_arrow={arrow_after!r}` and "
            f"`focused_label_after_arrow={arrow_focus_label!r}`. {_step_observation(result, 2)}"
        ),
        (
            f"3. {REQUEST_STEPS[0]} — "
            f"{'✅' if step3_status == 'passed' else '❌'} Observed "
            f"`active_workspace_after_home={home_after!r}` and "
            f"`focused_label_after_home={home_focus_label!r}`. {_step_observation(result, 3)}"
        ),
    ]
    if step4_status == "passed":
        lines.append(
            (
                f"4. {REQUEST_STEPS[1]} — ✅ Observed "
                f"`active_workspace_after_end={end_after!r}` and "
                f"`focused_label_after_end={end_focus_label!r}`. {_step_observation(result, 4)}"
            ),
        )
    else:
        lines.append(
            (
                f"4. {REQUEST_STEPS[1]} — "
                f"{'❌' if step4_status == 'failed' else '⚪'} "
                + (
                    f"Observed `active_workspace_after_end={end_after!r}` and "
                    f"`focused_label_after_end={end_focus_label!r}`. {_step_observation(result, 4)}"
                    if step4_status == "failed"
                    else "Not executed because an earlier required step failed."
                )
            ),
        )
    return lines


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


def _actual_result_summary(result: dict[str, object]) -> str:
    failed_status = _step_status(result, 4)
    if failed_status == "failed":
        observation = result.get("end_observation")
        label = "End"
    elif _step_status(result, 3) == "failed":
        observation = result.get("home_observation")
        label = "Home"
    elif _step_status(result, 2) == "failed":
        observation = result.get("arrow_down_precondition_observation")
        label = "ArrowDown precondition"
    else:
        observation = result.get("end_observation")
        label = "End"
        if not isinstance(observation, dict):
            observation = result.get("home_observation")
            label = "Home"
        if not isinstance(observation, dict):
            observation = result.get("arrow_down_precondition_observation")
            label = "ArrowDown precondition"

    if isinstance(observation, dict):
        active_after = observation.get("active_workspace_name")
        active = observation.get("active")
        focus = observation.get("focus")
        row_focus = observation.get("row_focus")
        active_role = active.get("role") if isinstance(active, dict) else "<missing>"
        active_label = (
            _snippet(str(active.get("accessible_name") or active.get("text") or ""))
            if isinstance(active, dict)
            else "<missing>"
        )
        active_on_trigger = (
            focus.get("active_on_trigger") if isinstance(focus, dict) else "<missing>"
        )
        row_contains_active = (
            row_focus.get("row_contains_active")
            if isinstance(row_focus, dict)
            else "<missing>"
        )
        return (
            f"After {label}, the active saved workspace was {active_after!r}, with "
            f"focused element `role={active_role}` and `label={active_label}`; "
            f"`active_on_trigger={active_on_trigger}` and "
            f"`row_contains_active={row_contains_active}`."
        )
    return _failed_step_summary(result)


def _step_status(result: dict[str, object], step_number: int) -> str:
    steps = result.get("steps", [])
    if not isinstance(steps, list):
        return "not_run"
    for step in steps:
        if isinstance(step, dict) and step.get("step") == step_number:
            return str(step.get("status", "not_run"))
    return "not_run"


def _step_observation(result: dict[str, object], step_number: int) -> str:
    steps = result.get("steps", [])
    if not isinstance(steps, list):
        return "<no observation recorded>"
    for step in steps:
        if isinstance(step, dict) and step.get("step") == step_number:
            return str(step.get("observed", "<no observation recorded>"))
    return "<not executed>"


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
    first_id = f"hosted:{repository.lower()}@{DEFAULT_BRANCH}"
    second_id = f"hosted:{repository.lower()}@{DEFAULT_BRANCH}:{SECOND_WORKSPACE_WRITE_BRANCH}"
    last_id = f"hosted:{repository.lower()}@{DEFAULT_BRANCH}:{LAST_WORKSPACE_WRITE_BRANCH}"
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
                "id": last_id,
                "displayName": LAST_WORKSPACE_DISPLAY_NAME,
                "customDisplayName": LAST_WORKSPACE_DISPLAY_NAME,
                "targetType": "hosted",
                "target": repository,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": LAST_WORKSPACE_WRITE_BRANCH,
                "lastOpenedAt": "2026-05-18T03:10:00.000Z",
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
        "observed_active_workspace_names": list(
            observation.observed_active_workspace_names,
        ),
        "latest_visible_container_kind": observation.latest_visible_container_kind,
        "latest_visible_row_count": observation.latest_visible_row_count,
        "latest_visible_active_workspace_name": observation.latest_visible_active_workspace_name,
    }


def _snippet(value: str, *, limit: int = 160) -> str:
    normalized = " ".join(str(value).split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3] + "..."


if __name__ == "__main__":
    main()
