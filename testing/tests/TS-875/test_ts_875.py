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
    WorkspaceSwitcherFocusTargetObservation,
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

TICKET_KEY = "TS-875"
TEST_CASE_TITLE = (
    "Press Arrow Down while internal Save and switch button is focused — selection advances to next workspace"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-875/test_ts_875.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 960}
KEY_STABILITY_MS = 1_000
DEFAULT_BRANCH = "main"
FIRST_WORKSPACE_DISPLAY_NAME = "Hosted main workspace"
SECOND_WORKSPACE_DISPLAY_NAME = "Hosted alt workspace"
SECOND_WORKSPACE_WRITE_BRANCH = "ts-875-alt"
LINKED_BUGS = ["TS-857"]
INTERNAL_BUTTON_LABEL = "Save and switch"

PRECONDITIONS = [
    "At least two workspaces are saved in the account.",
    "The workspace switcher panel is open.",
    "The focus is explicitly set on an internal interactive element (for example the Save and switch button) within the panel.",
]
REQUEST_STEPS = [
    "Press the 'Arrow Down' key on the keyboard.",
]
AUTOMATION_STEPS = [
    "Open the deployed desktop workspace switcher, confirm at least two saved workspaces are visible, and confirm Hosted main workspace starts selected.",
    "Move keyboard focus to the visible Save and switch button inside the open switcher and confirm that focus stays owned by the switcher.",
    "Press Arrow Down from the Save and switch button and verify the active saved workspace advances to Hosted alt workspace while the panel remains open.",
]
EXPECTED_RESULT = (
    "The active selection indicator moves to the next saved workspace in the list, "
    "and the keyboard event is handled by the workspace-switcher container even "
    "though focus is on the nested Save and switch button."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts875_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts875_failure.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-875 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
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
                runtime = tracker_page.open()
                result["runtime_state"] = runtime.kind
                result["runtime_body_text"] = runtime.body_text
                if runtime.kind != "ready":
                    raise AssertionError(
                        "Step 1 failed: the deployed app did not reach an interactive "
                        "desktop state before the Save and switch Arrow Down scenario began.\n"
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
                rows = page.observe_saved_workspace_rows()
                save_button = page.observe_switcher_button_focusability(
                    INTERNAL_BUTTON_LABEL,
                )

                result["trigger_observation"] = _trigger_payload(trigger)
                result["open_switcher_observation"] = _switcher_payload(switcher)
                result["open_panel_observation"] = asdict(panel)
                result["saved_workspace_rows_before_arrow"] = _saved_workspace_rows_payload(
                    rows,
                )
                result["save_and_switch_button_before_focus"] = _button_focusability_payload(
                    save_button,
                )
                active_workspace = _assert_initial_switcher_state(
                    trigger=trigger,
                    switcher=switcher,
                    panel=panel,
                    rows=rows,
                    save_button=save_button,
                )
                result["active_workspace_before_arrow"] = active_workspace.display_name
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=AUTOMATION_STEPS[0],
                    observed=(
                        f"Opened {config.app_url} in Chromium at "
                        f"{DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}; "
                        f"saved_workspace_row_count={len(rows)}; "
                        f"active_workspace={active_workspace.display_name!r}; "
                        f"button_label={save_button.label!r}; "
                        f"button_keyboard_focusable={save_button.keyboard_focusable}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Opened the desktop workspace switcher and visually confirmed the "
                        "Workspace switcher title, the saved workspace rows, and the "
                        "visible Save and switch button before pressing Arrow Down."
                    ),
                    observed=(
                        f"active_workspace={active_workspace.display_name!r}; "
                        f"save_button_text={save_button.visible_text!r}; "
                        f"text_excerpt={_snippet(switcher.switcher_text)!r}"
                    ),
                )

                focus_target = page.focus_switcher_button(
                    INTERNAL_BUTTON_LABEL,
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
                focused_button = page.observe_switcher_button_focusability(
                    INTERNAL_BUTTON_LABEL,
                    timeout_ms=4_000,
                )
                active_before_arrow = page.active_element()
                focus_ownership = page.observe_focus_ownership(panel=panel)

                result["save_and_switch_focus_target"] = _switcher_focus_payload(
                    focus_target,
                )
                result["save_and_switch_button_after_focus"] = _button_focusability_payload(
                    focused_button,
                )
                result["focused_element_before_arrow"] = _focused_element_payload(
                    active_before_arrow,
                )
                result["focus_ownership_before_arrow"] = _focus_ownership_payload(
                    focus_ownership,
                )
                _assert_internal_button_focus_ready(
                    focus_target=focus_target,
                    focused_button=focused_button,
                    active=active_before_arrow,
                    focus_ownership=focus_ownership,
                )
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=AUTOMATION_STEPS[1],
                    observed=(
                        f"focused_label={focus_target.active_label!r}; "
                        f"focused_role={focus_target.active_role!r}; "
                        f"button_active_within={focused_button.active_within}; "
                        f"focus_owned_by_switcher={focus_ownership.focus_owned_by_switcher}; "
                        f"active_within_switcher={focus_ownership.active_within_switcher}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Moved focus onto the visible Save and switch button and confirmed "
                        "the user-visible focus stayed inside the open workspace switcher "
                        "instead of jumping back to the trigger or outside the panel."
                    ),
                    observed=(
                        f"focused_label={focus_target.active_label!r}; "
                        f"active_role={focus_target.active_role!r}; "
                        f"button_active_within={focused_button.active_within}; "
                        f"focus_on_trigger={focus_ownership.active_on_trigger}"
                    ),
                )

                arrow_down = _press_arrow_down_and_observe(
                    page=page,
                    panel=panel,
                    expected_active_workspace=SECOND_WORKSPACE_DISPLAY_NAME,
                )
                result["arrow_down_observation"] = arrow_down
                try:
                    _assert_arrow_down_advanced_selection(
                        observation=arrow_down,
                        before_active_workspace=FIRST_WORKSPACE_DISPLAY_NAME,
                        expected_active_workspace=SECOND_WORKSPACE_DISPLAY_NAME,
                    )
                except Exception as error:
                    result["product_gap"] = (
                        "When keyboard focus is on the visible Save and switch button, "
                        "Arrow Down does not advance the active saved workspace to the "
                        "next row inside the desktop workspace switcher."
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
                        f"active_workspace_after={arrow_down['active_workspace_name']!r}; "
                        f"focused_label_after_arrow={arrow_down['active']['accessible_name']!r}; "
                        f"panel_kind={arrow_down['panel']['container_kind']!r}; "
                        f"focus_owned_by_switcher={arrow_down['focus']['focus_owned_by_switcher']}; "
                        f"monitor_hidden_after_visible={arrow_down['monitor']['ever_hidden_after_visible']}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Pressed Arrow Down while the Save and switch button visibly owned "
                        "focus and watched the highlighted active saved workspace move from "
                        "Hosted main workspace to Hosted alt workspace without the panel closing."
                    ),
                    observed=(
                        f"active_before_arrow={FIRST_WORKSPACE_DISPLAY_NAME!r}; "
                        f"active_after_arrow={arrow_down['active_workspace_name']!r}; "
                        f"focused_label_after_arrow={arrow_down['active']['accessible_name']!r}; "
                        f"focus_within_switcher_after_arrow={arrow_down['focus']['active_within_switcher']}; "
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


def _press_arrow_down_and_observe(
    *,
    page: LiveWorkspaceSwitcherPage,
    panel: WorkspaceSwitcherPanelObservation,
    expected_active_workspace: str,
) -> dict[str, object]:
    before_key_focus = page.observe_switcher_focus_target(panel=panel)
    page.start_transition_monitor()
    page.press_key("ArrowDown")
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
    rows = page.observe_saved_workspace_rows(timeout_ms=4_000)
    active = page.active_element()
    focus = page.observe_focus_ownership(panel=panel)
    save_button = page.observe_switcher_button_focusability(
        INTERNAL_BUTTON_LABEL,
        timeout_ms=4_000,
    )
    monitor = page.read_transition_monitor(clear=True)
    active_workspace = _selected_saved_workspace(rows)
    return {
        "key": "ArrowDown",
        "before_key_focus": _switcher_focus_payload(before_key_focus),
        "switcher": _switcher_payload(switcher),
        "panel": asdict(panel),
        "saved_workspace_rows": _saved_workspace_rows_payload(rows),
        "active": _focused_element_payload(active),
        "focus": _focus_ownership_payload(focus),
        "save_and_switch_button": _button_focusability_payload(save_button),
        "active_workspace_name": (
            active_workspace.display_name if active_workspace is not None else None
        ),
        "monitor": _monitor_payload(monitor),
    }


def _assert_initial_switcher_state(
    *,
    trigger: WorkspaceSwitcherTriggerObservation,
    switcher: WorkspaceSwitcherObservation,
    panel: WorkspaceSwitcherPanelObservation,
    rows: tuple[WorkspaceSwitcherSavedWorkspaceRowObservation, ...],
    save_button: WorkspaceSwitcherButtonFocusabilityObservation,
) -> WorkspaceSwitcherSavedWorkspaceRowObservation:
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
            f"Observed trigger bounds: {json.dumps(_trigger_payload(trigger), indent=2)}",
        )
    if len(rows) < 2:
        raise AssertionError(
            "Step 1 failed: the visible workspace switcher did not expose at least two "
            "saved workspace rows needed to exercise Arrow Down navigation.\n"
            f"Observed rows: {json.dumps(_saved_workspace_rows_payload(rows), indent=2)}",
        )
    active_workspace = _selected_saved_workspace(rows)
    if active_workspace is None:
        raise AssertionError(
            "Step 1 failed: none of the visible saved workspace rows was marked active "
            "before the Save and switch focus scenario began.\n"
            f"Observed rows: {json.dumps(_saved_workspace_rows_payload(rows), indent=2)}",
        )
    if active_workspace.display_name != FIRST_WORKSPACE_DISPLAY_NAME:
        raise AssertionError(
            "Step 1 failed: the preloaded active saved workspace was not the expected "
            "starting point.\n"
            f"Observed active workspace: {active_workspace.display_name!r}\n"
            f"Observed rows: {json.dumps(_saved_workspace_rows_payload(rows), indent=2)}",
        )
    if not save_button.keyboard_focusable:
        raise AssertionError(
            f'Step 1 failed: the visible "{INTERNAL_BUTTON_LABEL}" control was not '
            "keyboard focusable inside the open workspace switcher.\n"
            f"Observed button: {json.dumps(_button_focusability_payload(save_button), indent=2)}",
        )
    return active_workspace


def _assert_internal_button_focus_ready(
    *,
    focus_target: WorkspaceSwitcherFocusTargetObservation,
    focused_button: WorkspaceSwitcherButtonFocusabilityObservation,
    active: FocusedElementObservation,
    focus_ownership: WorkspaceSwitcherFocusOwnershipObservation,
) -> None:
    failures: list[str] = []
    if not focus_target.focus_owned_by_switcher:
        failures.append("keyboard focus was not owned by the open workspace switcher")
    if not focus_target.active_within_switcher:
        failures.append("keyboard focus was not inside the visible switcher panel")
    if focus_target.active_on_trigger:
        failures.append("keyboard focus stayed on the workspace-switcher trigger")
    if str(focus_target.active_role) != "button":
        failures.append(
            f"the active role was {focus_target.active_role!r} instead of a button",
        )
    if INTERNAL_BUTTON_LABEL not in str(focus_target.active_label or "") and INTERNAL_BUTTON_LABEL not in str(active.accessible_name or ""):
        failures.append(
            f'the focused control label did not identify "{INTERNAL_BUTTON_LABEL}"',
        )
    if not focused_button.active_within:
        failures.append(
            f'the visible "{INTERNAL_BUTTON_LABEL}" button did not contain the active element after focus was moved',
        )
    if not focus_ownership.focus_owned_by_switcher or not focus_ownership.active_within_switcher:
        failures.append(
            "the focus-ownership probe did not keep focus inside the switcher after targeting the internal button",
        )
    if failures:
        raise AssertionError(
            "Step 2 failed: the visible Save and switch button could not be established "
            "as the in-panel keyboard target before Arrow Down.\n"
            f"Observed focus target: {json.dumps(_switcher_focus_payload(focus_target), indent=2)}\n"
            f"Observed button: {json.dumps(_button_focusability_payload(focused_button), indent=2)}\n"
            f"Observed active element: {json.dumps(_focused_element_payload(active), indent=2)}\n"
            f"Observed focus ownership: {json.dumps(_focus_ownership_payload(focus_ownership), indent=2)}\n"
            + "\n".join(f"- {item}" for item in failures)
        )


def _assert_arrow_down_advanced_selection(
    *,
    observation: dict[str, object],
    before_active_workspace: str,
    expected_active_workspace: str,
) -> None:
    switcher = observation["switcher"]
    panel = observation["panel"]
    saved_workspace_rows = observation["saved_workspace_rows"]
    active = observation["active"]
    focus = observation["focus"]
    before_key_focus = observation["before_key_focus"]
    save_button = observation["save_and_switch_button"]
    active_workspace_name = observation["active_workspace_name"]
    monitor = observation["monitor"]
    assert isinstance(switcher, dict)
    assert isinstance(panel, dict)
    assert isinstance(saved_workspace_rows, list)
    assert isinstance(active, dict)
    assert isinstance(focus, dict)
    assert isinstance(before_key_focus, dict)
    assert isinstance(save_button, dict)
    assert isinstance(monitor, dict)

    failures: list[str] = []
    if INTERNAL_BUTTON_LABEL not in str(before_key_focus.get("active_label") or ""):
        failures.append(
            "the pre-key focus target was not the Save and switch button",
        )
    if not bool(before_key_focus.get("focus_owned_by_switcher")):
        failures.append("keyboard focus was not owned by the switcher before Arrow Down")
    if not bool(before_key_focus.get("active_within_switcher")):
        failures.append("keyboard focus was not inside the open switcher before Arrow Down")
    if "Workspace switcher" not in str(switcher.get("switcher_text", "")):
        failures.append("the visible Workspace switcher title was not present after Arrow Down")
    if str(panel.get("container_kind")) not in {"anchored-panel", "surface"}:
        failures.append(
            f"the visible container kind became {panel.get('container_kind')!r}",
        )
    if bool(monitor.get("ever_hidden_after_visible")):
        failures.append(
            "the transition monitor observed the panel become hidden after pressing Arrow Down",
        )
    if int(monitor.get("visible_sample_count", 0)) <= 0:
        failures.append(
            "the transition monitor did not capture any visible switcher samples after pressing Arrow Down",
        )
    if len(saved_workspace_rows) < 2:
        failures.append("fewer than two saved workspace rows remained visible after Arrow Down")
    if active_workspace_name == before_active_workspace:
        failures.append(
            f"the active saved workspace stayed on {before_active_workspace!r} instead of moving to the next row",
        )
    if active_workspace_name != expected_active_workspace:
        failures.append(
            f"the active saved workspace became {active_workspace_name!r} instead of {expected_active_workspace!r}",
        )
    if not bool(focus.get("focus_owned_by_switcher")):
        failures.append("keyboard focus escaped the workspace switcher after Arrow Down")
    if not bool(focus.get("active_within_switcher")):
        failures.append("the active element was no longer inside the open switcher after Arrow Down")
    if not bool(save_button.get("keyboard_focusable")):
        failures.append("the visible Save and switch button stopped being keyboard focusable after Arrow Down")
    if not str(active.get("accessible_name") or "") and not str(active.get("text") or ""):
        failures.append("the active element after Arrow Down did not expose readable text")
    if failures:
        raise AssertionError(
            "Step 3 failed: pressing Arrow Down from the Save and switch button did "
            "not advance the active saved workspace while keeping the workspace "
            "switcher visibly open.\n"
            f"Active workspace before Arrow Down: {before_active_workspace!r}\n"
            f"Active workspace after Arrow Down: {active_workspace_name!r}\n"
            f"Observed focus before Arrow Down: {json.dumps(before_key_focus, indent=2)}\n"
            f"Observed active element after Arrow Down: {json.dumps(active, indent=2)}\n"
            f"Observed focus ownership after Arrow Down: {json.dumps(focus, indent=2)}\n"
            f"Observed save button state after Arrow Down: {json.dumps(save_button, indent=2)}\n"
            f"Observed saved rows: {json.dumps(saved_workspace_rows, indent=2)}\n"
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
    error = str(result.get("error", "AssertionError: TS-875 failed"))
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
        "* Opened the desktop workspace switcher from Dashboard and confirmed Hosted main workspace started as the active saved workspace.",
        "* Moved keyboard focus onto the visible Save and switch button inside the workspace switcher.",
        "* Pressed Arrow Down from that internal button and verified whether the active saved workspace advanced to Hosted alt workspace while the panel stayed open.",
        "",
        "h4. Result",
        (
            "* Matched the expected result."
            if passed
            else f"* Did not match the expected result. {_failed_step_summary(result)}"
        ),
        f"* Expected result: {EXPECTED_RESULT}",
        (
            "* Actual result: matched the expected behavior in the live UI."
            if passed
            else f"* Actual result: {_actual_result_summary(result)}"
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
        "- Opened the deployed TrackState app in Chromium with a stored hosted token and two preloaded saved hosted workspaces.",
        "- Opened the desktop workspace switcher from Dashboard and confirmed Hosted main workspace started selected.",
        "- Focused the visible `Save and switch` button inside the open switcher and verified focus stayed owned by the switcher.",
        "- Pressed `ArrowDown` from that internal button and verified whether the highlighted saved workspace advanced to Hosted alt workspace while the panel remained open.",
        "",
        "## Result",
        (
            "- Matched the expected result."
            if passed
            else f"- Did not match the expected result. {_failed_step_summary(result)}"
        ),
        f"- Expected result: {EXPECTED_RESULT}",
        (
            "- Actual result: matched the expected behavior in the live UI."
            if passed
            else f"- Actual result: {_actual_result_summary(result)}"
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
        "## Issues/Notes",
        (
            "- No outstanding harness issues. The live in-panel Save and switch keyboard path is covered."
            if passed
            else f"- Re-run failed: {_failed_step_summary(result)}"
        ),
        "",
        "## Approach",
        "- Exercised the deployed hosted TrackState app in Chromium against the live setup repository.",
        "- Opened the desktop workspace switcher with two preloaded saved workspaces.",
        "- Focused the visible `Save and switch` button and pressed `ArrowDown` to verify the active saved workspace changed through the real UI.",
        "",
        "## Files Modified",
        "- `testing/tests/TS-875/test_ts_875.py`",
        "",
        "## Test Coverage",
        f"- Test case: `{TICKET_KEY} - {TEST_CASE_TITLE}`",
        f"- Result: `{status}`",
        f"- Command: `{RUN_COMMAND}`",
        f"- Screenshot: `{screenshot_path}`",
        (
            f"- Environment: `{result['app_url']}` on Chromium/Playwright "
            f"({result['os']}) against `{result['repository']}` @ "
            f"`{result['repository_ref']}`."
        ),
        (
            "- Outcome: Arrow Down advanced the active saved workspace from Hosted main workspace to Hosted alt workspace while focus started on the visible Save and switch button."
            if passed
            else f"- Outcome: {_actual_result_summary(result)}"
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
            f"# {TICKET_KEY} - Arrow Down from Save and switch does not advance workspace selection",
            "",
            "## Steps to reproduce",
            *[f"{index}. {step}" for index, step in enumerate(REQUEST_STEPS, start=1)],
            "",
            "## Exact steps from the test case with observations",
            _annotated_step_line(result, 1, REQUEST_STEPS[0]),
            "",
            "## Preconditions established before the failing step",
            f"- Opened `{result.get('app_url')}` in Chromium at {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}.",
            f"- Opened the desktop workspace switcher and observed `{FIRST_WORKSPACE_DISPLAY_NAME}` as the active saved workspace.",
            f"- Focused the visible `{INTERNAL_BUTTON_LABEL}` button and confirmed focus was inside the switcher before pressing Arrow Down.",
            "",
            "## Exact error message or assertion failure",
            "```text",
            str(result.get("traceback", result.get("error", ""))),
            "```",
            "",
            "## Actual vs Expected",
            f"- Expected: {EXPECTED_RESULT}",
            f"- Actual: {_actual_result_summary(result)}",
            "",
            "## Missing or broken production capability",
            (
                f"- {result.get('product_gap')}"
                if result.get("product_gap")
                else "- The workspace switcher does not advance the active saved workspace from the nested Save and switch button path."
            ),
            "",
            "## Environment details",
            f"- URL: {result.get('app_url')}",
            f"- Repository: {result.get('repository')} @ {result.get('repository_ref')}",
            f"- Browser: {result.get('browser')}",
            f"- OS: {result.get('os')}",
            f"- Viewport: {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
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
            (
                "- Arrow Down observation: ```json\n"
                + json.dumps(result.get("arrow_down_observation"), indent=2)
                + "\n```"
                if result.get("arrow_down_observation") is not None
                else "- Arrow Down observation: <missing>"
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


def _step_status_summary(result: dict[str, object]) -> list[str]:
    steps = result.get("steps", [])
    if not isinstance(steps, list):
        return ["no step data recorded"]
    summary: list[str] = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        summary.append(
            f"Step {step.get('step')}: {'passed' if step.get('status') == 'passed' else 'failed'}",
        )
    return summary or ["no step data recorded"]


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
    screenshot = result.get("screenshot")
    if not screenshot:
        return []
    prefix = "*" if jira else "-"
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
    arrow_down = result.get("arrow_down_observation")
    if not isinstance(arrow_down, dict):
        return _failed_step_summary(result)
    active_after = arrow_down.get("active_workspace_name")
    focused_after = None
    active_payload = arrow_down.get("active")
    if isinstance(active_payload, dict):
        focused_after = active_payload.get("accessible_name") or active_payload.get("text")
    return (
        f"After ArrowDown from the visible {INTERNAL_BUTTON_LABEL!r} button, the active "
        f"saved workspace was {active_after!r} and the focused element was "
        f"{focused_after!r}."
    )


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
    secondary_id = f"hosted:{repository.lower()}@{DEFAULT_BRANCH}:{SECOND_WORKSPACE_WRITE_BRANCH}"
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
                "id": secondary_id,
                "displayName": SECOND_WORKSPACE_DISPLAY_NAME,
                "customDisplayName": SECOND_WORKSPACE_DISPLAY_NAME,
                "targetType": "hosted",
                "target": repository,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": SECOND_WORKSPACE_WRITE_BRANCH,
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
        "observed_active_workspace_names": list(
            observation.observed_active_workspace_names,
        ),
        "latest_visible_container_kind": observation.latest_visible_container_kind,
        "latest_visible_row_count": observation.latest_visible_row_count,
        "latest_visible_active_workspace_name": (
            observation.latest_visible_active_workspace_name
        ),
    }


def _snippet(text: str, *, length: int = 220) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= length:
        return normalized
    return normalized[: length - 3] + "..."


if __name__ == "__main__":
    main()
