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

TICKET_KEY = "TS-842"
TEST_CASE_TITLE = (
    "Press Arrow Down on the last workspace item — selection state remains within list boundaries"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-842/test_ts_842.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 960}
KEY_STABILITY_MS = 1_000
DEFAULT_BRANCH = "main"
ACTIVE_WORKSPACE_DISPLAY_NAME = "Hosted main workspace"
LAST_WORKSPACE_DISPLAY_NAME = "Hosted alt workspace"
LAST_WORKSPACE_WRITE_BRANCH = "ts-842-alt"
BOUNDARY_TRIAL_COUNT = 5
TEST_CASE_STEPS = ["Press the 'Arrow Down' key."]
EXPECTED_RESULT = (
    "The selection state remains valid (the indicator either stays on the last item "
    "or loops back to the first item depending on implementation), and no focus is "
    "lost to the global view."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts842_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts842_failure.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-842 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
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
        "linked_bugs": ["TS-836", "TS-851", "TS-852"],
        "preloaded_workspace_state": workspace_state,
        "user_login": user.login,
        "steps": [],
        "human_verification": [],
        "boundary_trials": [],
    }

    page: LiveWorkspaceSwitcherPage | None = None
    try:
        for trial in range(1, BOUNDARY_TRIAL_COUNT + 1):
            with create_live_tracker_app(
                config,
                runtime_factory=lambda: StoredWorkspaceProfilesRuntime(
                    repository=service.repository,
                    token=token,
                    workspace_state=workspace_state,
                ),
            ) as tracker_page:
                page = LiveWorkspaceSwitcherPage(tracker_page)
                runtime = tracker_page.open()
                if trial == 1:
                    result["runtime_state"] = runtime.kind
                    result["runtime_body_text"] = runtime.body_text
                if runtime.kind != "ready":
                    raise AssertionError(
                        "Step 1 failed: the deployed app did not reach an interactive "
                        "desktop state before the boundary-navigation scenario began.\n"
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
                active_workspace = _assert_workspace_navigation_ready(saved_workspace_rows)

                if trial == 1:
                    result["trigger_observation"] = _trigger_payload(trigger)
                    result["open_switcher_observation"] = _switcher_payload(switcher)
                    result["open_panel_observation"] = asdict(panel)
                    result["saved_workspace_rows_before_trials"] = _saved_workspace_rows_payload(
                        saved_workspace_rows,
                    )
                    result["active_workspace_before_trials"] = active_workspace.display_name
                    _record_step(
                        result,
                        step=1,
                        status="passed",
                        action=(
                            "Open the desktop workspace switcher with two saved workspaces "
                            "available."
                        ),
                        observed=(
                            f"Opened {config.app_url} in Chromium at "
                            f"{DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}; "
                            f"container_kind={panel.container_kind}; "
                            f"saved_workspace_row_count={len(saved_workspace_rows)}; "
                            f"active_workspace={active_workspace.display_name!r}"
                        ),
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Opened the desktop workspace switcher and visually confirmed "
                            "the Workspace switcher title plus both saved workspace rows "
                            "were visible before the boundary test."
                        ),
                        observed=(
                            "title='Workspace switcher'; "
                            f"visible_rows={len(saved_workspace_rows)}; "
                            f"active_workspace={active_workspace.display_name!r}; "
                            f"text_excerpt={_snippet(switcher.switcher_text)!r}"
                        ),
                    )

                page.click_saved_workspace_row_surface(ACTIVE_WORKSPACE_DISPLAY_NAME)
                page.wait_for_surface_to_remain_open(
                    stability_ms=KEY_STABILITY_MS,
                    timeout_ms=4_000,
                )
                focus_precondition = page.observe_focus_ownership(panel=panel)
                _assert_boundary_focus_precondition(
                    observation=focus_precondition,
                    expected_workspace_name=ACTIVE_WORKSPACE_DISPLAY_NAME,
                    saved_workspace_rows=page.observe_saved_workspace_rows(timeout_ms=4_000),
                )

                if trial == 1:
                    _record_step(
                        result,
                        step=2,
                        status="passed",
                        action=(
                            "Click the active saved-workspace row to engage keyboard "
                            "interaction inside the open switcher."
                        ),
                        observed=(
                            f"focus_owned_by_switcher={focus_precondition.focus_owned_by_switcher}; "
                            f"active_within_switcher={focus_precondition.active_within_switcher}; "
                            f"active_on_trigger={focus_precondition.active_on_trigger}; "
                            f"focus_label={focus_precondition.active_label!r}; "
                            f"focus_role={focus_precondition.active_role!r}"
                        ),
                    )

                last_row_observation = _navigate_to_last_workspace(
                    page=page,
                    panel=panel,
                    trial=trial,
                )

                last_row_focus = _focus_last_workspace_row_for_boundary(
                    page=page,
                    panel=panel,
                    saved_workspace_rows=page.observe_saved_workspace_rows(timeout_ms=4_000),
                )
                if trial == 1:
                    _record_step(
                        result,
                        step=3,
                        status="passed",
                        action=(
                            "Establish the ticket precondition by moving selection to the "
                            "last saved workspace row and restoring row-owned keyboard focus."
                        ),
                        observed=(
                            f"last_workspace={last_row_observation['active_workspace_name']!r}; "
                            f"focus_owned_by_switcher={last_row_focus['focus_owned_by_switcher']}; "
                            f"active_within_switcher={last_row_focus['active_within_switcher']}; "
                            f"focus_label={last_row_focus['active_label']!r}; "
                            f"panel_hidden_after_arrow={last_row_observation['monitor']['ever_hidden_after_visible']}"
                        ),
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Used keyboard navigation to highlight the last saved workspace "
                            "row, then confirmed the row itself visibly held keyboard focus "
                            "before the boundary Arrow Down press."
                        ),
                        observed=(
                            f"last_row_active={last_row_observation['active_workspace_name']!r}; "
                            f"visible_rows={len(last_row_observation['saved_workspace_rows'])}; "
                            f"focus_label={last_row_focus['active_label']!r}; "
                            f"text_excerpt={_snippet(str(last_row_observation['switcher']['switcher_text']))!r}"
                        ),
                    )

                boundary_observation = _press_key_and_observe(
                    page=page,
                    panel=panel,
                    key="ArrowDown",
                )
                boundary_observation["trial"] = trial
                boundary_observation["starting_workspace_name"] = LAST_WORKSPACE_DISPLAY_NAME
                trials = result.setdefault("boundary_trials", [])
                assert isinstance(trials, list)
                trials.append(boundary_observation)

                try:
                    _assert_boundary_behavior(observation=boundary_observation)
                except AssertionError as error:
                    result["product_gap"] = (
                        "Pressing Arrow Down from the last saved workspace row is not "
                        "stable: the visible selection may remain valid, but keyboard "
                        "focus can escape the workspace switcher and land on the global "
                        "page view."
                    )
                    result["failing_trial"] = trial
                    result["failing_trial_observation"] = boundary_observation
                    raise

                if trial == 1:
                    _record_human_verification(
                        result,
                        check=(
                            "Pressed Arrow Down with the last saved workspace highlighted "
                            "and watched the visible selection the way a desktop user would."
                        ),
                        observed=(
                            f"active_after_boundary={boundary_observation['active_workspace_name']!r}; "
                            f"focus_after_boundary={boundary_observation['focus']['active_label']!r}; "
                            f"panel_hidden_after_boundary={boundary_observation['monitor']['ever_hidden_after_visible']}"
                        ),
                    )

        _record_step(
            result,
            step=4,
            status="passed",
            action=TEST_CASE_STEPS[0],
            observed=(
                f"Completed {BOUNDARY_TRIAL_COUNT} fresh boundary trials; every trial kept the "
                "workspace switcher open, left a valid saved workspace selected, and preserved "
                "switcher-owned keyboard focus."
            ),
        )
        _record_human_verification(
            result,
            check=(
                "Repeated the boundary Arrow Down scenario across fresh desktop sessions "
                "to confirm it remained stable for a real user."
            ),
            observed=(
                f"Trials={BOUNDARY_TRIAL_COUNT}; "
                "each trial kept the highlight within the saved-workspace list and "
                "did not return focus to the global page."
            ),
        )
        if page is not None:
            try:
                page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
            except Exception as screenshot_error:
                result["screenshot_error"] = (
                    f"{type(screenshot_error).__name__}: {screenshot_error}"
                )
        _write_pass_outputs(result)
        print(f"{TICKET_KEY} passed")
    except AssertionError as error:
        result["error"] = str(error)
        result["traceback"] = traceback.format_exc()
        if page is not None:
            try:
                page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
            except Exception as screenshot_error:
                result["screenshot_error"] = (
                    f"{type(screenshot_error).__name__}: {screenshot_error}"
                )
        _record_step(
            result,
            step=4,
            status="failed",
            action=TEST_CASE_STEPS[0],
            observed=str(error),
        )
        _record_human_verification(
            result,
            check=(
                "Observed the boundary Arrow Down result from the last saved workspace row "
                "as a desktop user would."
            ),
            observed=_human_boundary_summary(result),
        )
        _write_failure_outputs(result)
        raise
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        if page is not None:
            try:
                page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
            except Exception as screenshot_error:
                result["screenshot_error"] = (
                    f"{type(screenshot_error).__name__}: {screenshot_error}"
                )
        _write_failure_outputs(result)
        raise


def _navigate_to_last_workspace(
    *,
    page: LiveWorkspaceSwitcherPage,
    panel: WorkspaceSwitcherPanelObservation,
    trial: int,
) -> dict[str, object]:
    for attempt in range(1, 4):
        observation = _press_key_and_observe(
            page=page,
            panel=panel,
            key="ArrowDown",
        )
        observation["attempt"] = attempt
        if observation["active_workspace_name"] == LAST_WORKSPACE_DISPLAY_NAME:
            return observation
    raise AssertionError(
        "Step 3 failed: the ticket precondition could not be established because "
        f"Arrow Down never highlighted {LAST_WORKSPACE_DISPLAY_NAME!r} within 3 "
        f"attempts during trial {trial}.\n"
        f"Last observation:\n{json.dumps(observation, indent=2)}"
    )


def _press_key_and_observe(
    *,
    page: LiveWorkspaceSwitcherPage,
    panel: WorkspaceSwitcherPanelObservation,
    key: str,
) -> dict[str, object]:
    page.start_transition_monitor()
    page.press_key(key)
    page.wait_for_surface_to_remain_open(
        stability_ms=KEY_STABILITY_MS,
        timeout_ms=4_000,
    )
    switcher = page.observe_open_switcher(timeout_ms=4_000)
    saved_workspace_rows = page.observe_saved_workspace_rows(timeout_ms=4_000)
    focus = page.observe_focus_ownership(panel=panel)
    active = page.active_element()
    monitor = page.read_transition_monitor(clear=True)
    active_workspace = _selected_saved_workspace(saved_workspace_rows)
    return {
        "key": key,
        "switcher": _switcher_payload(switcher),
        "panel": asdict(
            page.observe_open_panel(
                expected_container_kinds=("anchored-panel", "surface"),
                timeout_ms=4_000,
            ),
        ),
        "focus": _focus_ownership_payload(focus),
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
            f"Observed trigger bounds: left={trigger.left:.1f}, top={trigger.top:.1f}, "
            f"width={trigger.width:.1f}, height={trigger.height:.1f}",
        )


def _assert_workspace_navigation_ready(
    rows: tuple[WorkspaceSwitcherSavedWorkspaceRowObservation, ...],
) -> WorkspaceSwitcherSavedWorkspaceRowObservation:
    if len(rows) < 2:
        raise AssertionError(
            "Step 1 failed: the visible workspace switcher did not expose at least "
            "two saved workspace rows needed to exercise boundary navigation.\n"
            f"Observed rows: {json.dumps(_saved_workspace_rows_payload(rows), indent=2)}",
        )
    active_workspace = _selected_saved_workspace(rows)
    if active_workspace is None:
        raise AssertionError(
            "Step 1 failed: none of the visible saved workspace rows was marked "
            "active before the boundary Arrow Down scenario began.\n"
            f"Observed rows: {json.dumps(_saved_workspace_rows_payload(rows), indent=2)}",
        )
    if active_workspace.display_name != ACTIVE_WORKSPACE_DISPLAY_NAME:
        raise AssertionError(
            "Step 1 failed: the preloaded active saved workspace was not the expected "
            "starting point for the boundary scenario.\n"
            f"Observed active workspace: {active_workspace.display_name!r}\n"
            f"Observed rows: {json.dumps(_saved_workspace_rows_payload(rows), indent=2)}",
        )
    return active_workspace


def _assert_boundary_focus_precondition(
    *,
    observation: WorkspaceSwitcherFocusOwnershipObservation,
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
    if active_workspace is None:
        failures.append("no saved workspace row remained active after clicking the active row")
    elif active_workspace.display_name != expected_workspace_name:
        failures.append(
            f"the active saved workspace changed to {active_workspace.display_name!r} "
            f"instead of remaining on {expected_workspace_name!r}",
        )
    if failures:
        raise AssertionError(
            "Step 2 failed: clicking the active saved workspace row did not establish a "
            "valid keyboard-interaction precondition before the boundary Arrow Down press.\n"
            + "\n".join(f"- {item}" for item in failures)
            + "\n"
            + f"Observed focus label: {observation.active_label!r}\n"
            + f"Observed focus role: {observation.active_role!r}\n"
            + f"Observed focus tag: {observation.active_tag_name!r}\n"
            + f"Observed rows after click: {json.dumps(_saved_workspace_rows_payload(saved_workspace_rows), indent=2)}"
        )


def _focus_last_workspace_row_for_boundary(
    *,
    page: LiveWorkspaceSwitcherPage,
    panel: WorkspaceSwitcherPanelObservation,
    saved_workspace_rows: tuple[WorkspaceSwitcherSavedWorkspaceRowObservation, ...],
) -> dict[str, object]:
    last_workspace = _selected_saved_workspace(saved_workspace_rows)
    if last_workspace is None:
        raise AssertionError(
            "Step 3 failed: no saved workspace row remained active before the boundary "
            "Arrow Down press.\n"
            f"Observed rows: {json.dumps(_saved_workspace_rows_payload(saved_workspace_rows), indent=2)}",
        )
    if last_workspace.display_name != LAST_WORKSPACE_DISPLAY_NAME:
        raise AssertionError(
            "Step 3 failed: the last saved workspace row was not the active selection "
            "before the boundary Arrow Down press.\n"
            f"Observed active workspace: {last_workspace.display_name!r}\n"
            f"Observed rows: {json.dumps(_saved_workspace_rows_payload(saved_workspace_rows), indent=2)}",
        )

    expected_label = _saved_workspace_row_focus_label(last_workspace)
    page.focus_switcher_button(
        expected_label,
        panel=panel,
        timeout_ms=4_000,
    )
    observation = page.observe_focus_ownership(panel=panel)
    failures: list[str] = []
    if not observation.focus_owned_by_switcher:
        failures.append("keyboard focus was not owned by the workspace switcher")
    if not observation.active_within_switcher:
        failures.append("the active element was not inside the open workspace switcher")
    if observation.active_on_trigger:
        failures.append("keyboard focus fell back to the workspace-switcher trigger")
    if observation.active_label != expected_label:
        failures.append(
            f"the focused element label was {observation.active_label!r} instead of "
            f"{expected_label!r}",
        )
    if failures:
        raise AssertionError(
            "Step 3 failed: the last saved workspace row could not be focused as the "
            "boundary-navigation precondition.\n"
            + "\n".join(f"- {item}" for item in failures)
            + "\n"
            + f"Observed rows: {json.dumps(_saved_workspace_rows_payload(saved_workspace_rows), indent=2)}"
        )
    return _focus_ownership_payload(observation)


def _assert_boundary_behavior(*, observation: dict[str, object]) -> None:
    _assert_key_kept_panel_open(key="Arrow Down", observation=observation)
    active_workspace_name = observation["active_workspace_name"]
    focus = observation["focus"]
    saved_workspace_rows = observation["saved_workspace_rows"]
    assert isinstance(focus, dict)
    assert isinstance(saved_workspace_rows, list)

    failures: list[str] = []
    if active_workspace_name not in {
        ACTIVE_WORKSPACE_DISPLAY_NAME,
        LAST_WORKSPACE_DISPLAY_NAME,
    }:
        failures.append(
            f"the active saved workspace left the list boundaries and became {active_workspace_name!r}",
        )
    if not bool(focus.get("focus_owned_by_switcher")):
        failures.append("keyboard focus escaped the workspace switcher")
    if not bool(focus.get("active_within_switcher")):
        failures.append("the active element was no longer inside the open switcher")
    if bool(focus.get("active_on_trigger")):
        failures.append("keyboard focus jumped back to the workspace-switcher trigger")

    if failures:
        raise AssertionError(
            "Step 4 failed: pressing Arrow Down on the last saved workspace row did "
            "not keep keyboard navigation within the workspace list boundaries.\n"
            f"Observed active workspace after boundary Arrow Down: {active_workspace_name!r}\n"
            f"Observed focus label: {focus.get('active_label')!r}\n"
            f"Observed focus role: {focus.get('active_role')!r}\n"
            f"Observed focus tag: {focus.get('active_tag_name')!r}\n"
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
            f"Step 4 failed: pressing {key} did not leave the workspace switcher visibly open.\n"
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
    error = str(result.get("error", "AssertionError: TS-842 failed"))
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
        "* Opened the deployed TrackState app in Chromium with a stored hosted token and two preloaded saved hosted workspaces.",
        "* Opened the desktop workspace switcher from Dashboard.",
        "* Established the last saved workspace row as the current selection/highlight and restored keyboard focus to that row.",
        "* Pressed Arrow Down from the last saved workspace row across fresh live trials.",
        "* Checked that the panel stayed open, the selection stayed within the visible list boundaries, and keyboard focus did not escape to the global view.",
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
        "h4. Boundary trials",
        *_trial_lines(result, jira=True),
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
        "- Established the last saved workspace row as the current selection/highlight and restored keyboard focus to that row.",
        "- Pressed Arrow Down from the last saved workspace row across fresh live trials.",
        "- Checked that the panel stayed open, the selection stayed within the list boundaries, and keyboard focus did not escape to the global page.",
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
        "## Boundary trials",
        *_trial_lines(result, jira=False),
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
        "- Added TS-842 live desktop coverage for workspace-switcher Arrow Down boundary navigation.",
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
            else "- Outcome: repeated live boundary Arrow Down trials kept selection within the workspace list and preserved switcher-owned keyboard focus."
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
    failing_trial = result.get("failing_trial")
    trial_observation = result.get("failing_trial_observation")
    return "\n".join(
        [
            f"# {TICKET_KEY} - Arrow Down at the end of the workspace list can lose keyboard focus",
            "",
            "## Steps to reproduce",
            "1. Open the workspace switcher panel.",
            (
                f"2. Ensure the last saved workspace row ({LAST_WORKSPACE_DISPLAY_NAME}) is "
                "currently selected/highlighted and that keyboard focus is on that row."
            ),
            "3. Press the `Arrow Down` key once.",
            "",
            "## Exact steps from the automated run with observations",
            "1. ✅ Opened the deployed TrackState app, navigated to Dashboard, and opened the desktop workspace switcher.",
            "2. ✅ Clicked the active saved-workspace row and confirmed keyboard focus was owned by the open switcher.",
            (
                f"3. ✅ Established the last-row precondition by moving selection to "
                f"{LAST_WORKSPACE_DISPLAY_NAME!r} and restoring keyboard focus to that row."
            ),
            "4. ❌ Pressed the `Arrow Down` key once from the focused last row.",
            (
                f"   Actual: boundary trial {failing_trial} switched the visible active row "
                f"to {(_extract_boundary_trial(result) or {}).get('active_workspace_name')!r} "
                f"while keyboard focus escaped to `{((_extract_boundary_trial(result) or {}).get('focus') or {}).get('active_tag_name', '<unknown>')}` outside the open switcher."
            ),
            f"   Assertion: {_failed_step_summary(result)}",
            "",
            "## Exact error message or assertion failure",
            "```text",
            str(result.get("traceback", result.get("error", ""))),
            "```",
            "",
            "## Actual vs Expected",
            f"- Expected: {EXPECTED_RESULT}",
            (
                "- Actual: the workspace switcher stayed open and the visible selection "
                f"wrapped to {(_extract_boundary_trial(result) or {}).get('active_workspace_name')!r}, "
                f"but keyboard focus escaped the switcher and landed on `{((_extract_boundary_trial(result) or {}).get('focus') or {}).get('active_tag_name', '<unknown>')}` "
                "instead of remaining on a switcher-owned element."
            ),
            "",
            "## Environment details",
            f"- URL: {result.get('app_url')}",
            f"- Repository: {result.get('repository')} @ {result.get('repository_ref')}",
            f"- Browser: {result.get('browser')}",
            f"- OS: {result.get('os')}",
            f"- Viewport: {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
            f"- Run command: {RUN_COMMAND}",
            (
                f"- Failing trial observation: {json.dumps(trial_observation, indent=2)}"
                if isinstance(trial_observation, dict)
                else "- Failing trial observation: <missing>"
            ),
            "",
            "## Screenshots or logs",
            f"- Screenshot: {result.get('screenshot', '<no screenshot recorded>')}",
        ],
    ) + "\n"


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


def _extract_boundary_trial(result: dict[str, object]) -> dict[str, object] | None:
    trial = result.get("failing_trial_observation")
    return trial if isinstance(trial, dict) else None


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


def _trial_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    prefix = "*" if jira else "-"
    trials = result.get("boundary_trials", [])
    if not isinstance(trials, list):
        return [f"{prefix} <no trial data recorded>"]
    lines: list[str] = []
    for trial in trials:
        if not isinstance(trial, dict):
            continue
        focus = trial.get("focus", {})
        monitor = trial.get("monitor", {})
        lines.append(
            f"{prefix} Trial {trial.get('trial')}: "
            f"active_after_boundary={trial.get('active_workspace_name')!r}; "
            f"focus_owned_by_switcher={focus.get('focus_owned_by_switcher') if isinstance(focus, dict) else None}; "
            f"active_within_switcher={focus.get('active_within_switcher') if isinstance(focus, dict) else None}; "
            f"active_tag={focus.get('active_tag_name') if isinstance(focus, dict) else None!r}; "
            f"panel_hidden_after_visible={monitor.get('ever_hidden_after_visible') if isinstance(monitor, dict) else None}"
        )
    return lines or [f"{prefix} <no trial data recorded>"]


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


def _human_boundary_summary(result: dict[str, object]) -> str:
    trial = result.get("failing_trial_observation")
    if not isinstance(trial, dict):
        return "The boundary Arrow Down scenario failed."
    focus = trial.get("focus", {})
    return (
        f"Boundary trial {trial.get('trial')} left the visible selection on "
        f"{trial.get('active_workspace_name')!r} while the panel stayed open, but the "
        f"active element moved to {focus.get('active_tag_name') if isinstance(focus, dict) else None!r} "
        f"with label {focus.get('active_label') if isinstance(focus, dict) else None!r}, "
        "which means focus escaped the workspace switcher."
    )


def _workspace_state(repository: str) -> dict[str, object]:
    main_id = f"hosted:{repository.lower()}@{DEFAULT_BRANCH}"
    last_id = f"hosted:{repository.lower()}@{DEFAULT_BRANCH}:{LAST_WORKSPACE_WRITE_BRANCH}"
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
                "bounds": {
                    "left": row.left,
                    "top": row.top,
                    "width": row.width,
                    "height": row.height,
                },
            },
        )
    return payload


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
