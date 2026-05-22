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

TICKET_KEY = "TS-825"
TEST_CASE_TITLE = "Press non-Escape navigation keys — workspace switcher panel remains open"
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-825/test_ts_825.py"
TEST_FILE_PATH = "testing/tests/TS-825/test_ts_825.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 960}
KEY_STABILITY_MS = 1_000
START_FIELD_LABEL = "Repository"
EXPECTED_TAB_TARGET_LABELS = ("Branch", "Hosted", "Local", "Save and switch")
DEFAULT_BRANCH = "main"
ACTIVE_WORKSPACE_DISPLAY_NAME = "Hosted main workspace"
SECONDARY_WORKSPACE_DISPLAY_NAME = "Hosted alt workspace"
SECONDARY_WRITE_BRANCH = "ts-825-alt"

REQUEST_STEPS = [
    "Launch the application on a desktop browser.",
    "Click the workspace switcher trigger to open the panel.",
    "Press the 'Arrow Down' key to navigate between workspaces.",
    "Press the 'Shift' key.",
    "Press the 'Tab' key to move focus within the panel.",
]
EXPECTED_RESULT = (
    "The workspace switcher panel remains open and does not dismiss on any of "
    "these navigation keystrokes."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts825_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts825_failure.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-825 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
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
        "start_field_label": START_FIELD_LABEL,
        "expected_tab_target_labels": EXPECTED_TAB_TARGET_LABELS,
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
                            "desktop state before the non-Escape key scenario began.\n"
                            f"Observed runtime state: {runtime.kind}\n"
                            f"Observed body text:\n{runtime.body_text}",
                        )

                    page.dismiss_connection_banner()
                    page.navigate_to_section("Dashboard")
                    page.set_viewport(**DESKTOP_VIEWPORT)
                    trigger = page.observe_trigger()
                    result["trigger_observation"] = _trigger_payload(trigger)
                except AssertionError as error:
                    _record_step(
                        result,
                        step=1,
                        status="failed",
                        action=REQUEST_STEPS[0],
                        observed=str(error),
                    )
                    raise
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=REQUEST_STEPS[0],
                    observed=(
                        f"Opened {config.app_url} in Chromium at "
                        f"{DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}; "
                        "preloaded two saved hosted workspaces for keyboard "
                        "navigation coverage; "
                        f"trigger_label={trigger.semantic_label!r}; "
                        f"trigger_text={trigger.visible_text!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Viewed the desktop app shell before opening the panel and "
                        "confirmed Dashboard plus the visible workspace switcher trigger "
                        "for the preloaded active workspace were rendered."
                    ),
                    observed=(
                        f"trigger_text={trigger.visible_text!r}; "
                        f"top_buttons={list(trigger.top_button_labels)!r}"
                    ),
                )

                try:
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
                    page.click_saved_workspace_row_surface(ACTIVE_WORKSPACE_DISPLAY_NAME)
                    result["open_switcher_observation"] = _switcher_payload(switcher)
                    result["open_panel_observation"] = asdict(panel)
                    result["saved_workspace_rows_before_arrow"] = _saved_workspace_rows_payload(
                        saved_workspace_rows,
                    )
                    result["active_workspace_before_arrow"] = active_workspace.display_name
                except Exception as error:
                    _record_step(
                        result,
                        step=2,
                        status="failed",
                        action=REQUEST_STEPS[1],
                        observed=str(error),
                    )
                    raise
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=REQUEST_STEPS[1],
                    observed=(
                        f"container_kind={panel.container_kind}; "
                        f"saved_workspace_row_count={len(saved_workspace_rows)}; "
                        f"title_visible={'Workspace switcher' in switcher.switcher_text}; "
                        f"active_workspace={active_workspace.display_name!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Opened the visible desktop workspace switcher and confirmed the "
                        "title plus at least two saved workspace rows were visible before "
                        "trying Arrow Down navigation."
                    ),
                    observed=(
                        "title='Workspace switcher'; "
                        f"saved_workspace_row_count={len(saved_workspace_rows)}; "
                        f"active_workspace={active_workspace.display_name!r}; "
                        f"text_excerpt={_snippet(switcher.switcher_text)}"
                    ),
                )

                arrow_down = _press_key_and_observe(
                    page=page,
                    key="ArrowDown",
                    expected_active_workspace=SECONDARY_WORKSPACE_DISPLAY_NAME,
                )
                result["arrow_down_observation"] = arrow_down
                try:
                    _assert_arrow_down_navigated_between_workspaces(
                        observation=arrow_down,
                        before_active_workspace=active_workspace.display_name,
                        expected_active_workspace=SECONDARY_WORKSPACE_DISPLAY_NAME,
                    )
                except Exception as error:
                    result["product_gap"] = (
                        "The desktop workspace switcher exposes only button-based row "
                        "actions (`Open`/`Delete`) for saved workspaces and does not "
                        "change the active saved workspace when Arrow Down is pressed "
                        "from the visible saved-workspace surface."
                    )
                    _record_step(
                        result,
                        step=3,
                        status="failed",
                        action=REQUEST_STEPS[2],
                        observed=str(error),
                    )
                    raise
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action=REQUEST_STEPS[2],
                    observed=(
                        f"panel_kind={arrow_down['panel']['container_kind']}; "
                        f"saved_workspace_row_count={len(arrow_down['saved_workspace_rows'])}; "
                        f"active_workspace_after={arrow_down['active_workspace_name']!r}; "
                        f"monitor_hidden_after_visible="
                        f"{arrow_down['monitor']['ever_hidden_after_visible']}"
                    ),
                )

                shift = _press_key_and_observe(
                    page=page,
                    key="Shift",
                )
                result["shift_observation"] = shift
                try:
                    _assert_key_kept_panel_open(
                        key="Shift",
                        observation=shift,
                        expected_focus_label="Saved workspaces",
                        allow_focus_change=True,
                    )
                except Exception as error:
                    _record_step(
                        result,
                        step=4,
                        status="failed",
                        action=REQUEST_STEPS[3],
                        observed=str(error),
                    )
                    raise
                _record_step(
                    result,
                    step=4,
                    status="passed",
                    action=REQUEST_STEPS[3],
                    observed=(
                        f"panel_kind={shift['panel']['container_kind']}; "
                        f"saved_workspace_row_count={len(shift['saved_workspace_rows'])}; "
                        f"focus_after={shift['active']['accessible_name']!r}; "
                        f"monitor_hidden_after_visible="
                        f"{shift['monitor']['ever_hidden_after_visible']}"
                    ),
                )

                focused_field = page.focus_switcher_text_field(START_FIELD_LABEL)
                _assert_focused_field(
                    focused_field,
                    expected_label=START_FIELD_LABEL,
                    step=5,
                )
                before_tab = page.active_element()
                result["before_tab_focus"] = _focused_element_payload(before_tab)
                tab = _press_key_and_observe(
                    page=page,
                    key="Tab",
                )
                result["tab_observation"] = tab
                try:
                    _assert_tab_kept_focus_within_panel(
                        before=before_tab,
                        observation=tab,
                    )
                except Exception as error:
                    _record_step(
                        result,
                        step=5,
                        status="failed",
                        action=REQUEST_STEPS[4],
                        observed=str(error),
                    )
                    raise
                _record_step(
                    result,
                    step=5,
                    status="passed",
                    action=REQUEST_STEPS[4],
                    observed=(
                        f"panel_kind={tab['panel']['container_kind']}; "
                        f"saved_workspace_row_count={len(tab['saved_workspace_rows'])}; "
                        f"focus_before={before_tab.accessible_name!r}; "
                        f"focus_after={tab['active']['accessible_name']!r}; "
                        f"monitor_hidden_after_visible="
                        f"{tab['monitor']['ever_hidden_after_visible']}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Started from the visible saved-workspace list surface, pressed "
                        "Arrow Down, and watched whether the active row changed while the "
                        "panel stayed on screen."
                    ),
                    observed=(
                        f"active_before_arrow={active_workspace.display_name!r}; "
                        f"active_after_arrow={arrow_down['active_workspace_name']!r}; "
                        f"shift_focus={shift['active']['accessible_name']!r}; "
                        f"arrow_down_hidden={arrow_down['monitor']['ever_hidden_after_visible']}; "
                        f"shift_hidden={shift['monitor']['ever_hidden_after_visible']}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Pressed Tab from the visible Repository field and confirmed the "
                        "keyboard focus moved to another visible control inside the panel "
                        "while the panel title and workspace content stayed visible."
                    ),
                    observed=(
                        f"focus_before={before_tab.accessible_name!r}; "
                        f"focus_after={tab['active']['accessible_name']!r}; "
                        f"allowed_targets={list(EXPECTED_TAB_TARGET_LABELS)!r}; "
                        f"text_excerpt={_snippet(tab['switcher']['switcher_text'])}"
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
    expected_active_workspace: str | None = None,
) -> dict[str, object]:
    page.start_transition_monitor()
    page.press_key(key)
    page.wait_for_surface_to_remain_open(
        stability_ms=KEY_STABILITY_MS,
        timeout_ms=4_000,
    )
    if expected_active_workspace is not None:
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
            "Step 2 failed: opening the workspace switcher did not expose the visible "
            "Workspace switcher title.\n"
            f"Observed switcher text:\n{switcher.switcher_text}",
        )
    if panel.container_kind not in {"anchored-panel", "surface"}:
        raise AssertionError(
            "Step 2 failed: clicking the workspace switcher trigger did not open the "
            "expected desktop panel-style surface.\n"
            f"Observed container kind: {panel.container_kind}\n"
            f"Observed bounds: left={panel.left:.1f}, top={panel.top:.1f}, "
            f"width={panel.width:.1f}, height={panel.height:.1f}",
        )
    if panel.width <= 0 or panel.height <= 0:
        raise AssertionError(
            "Step 2 failed: clicking the workspace switcher trigger did not expose a "
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
            "Step 2 failed: the visible workspace switcher did not expose at least "
            "two saved workspace rows needed to exercise Arrow Down navigation.\n"
            f"Observed rows: {json.dumps(_saved_workspace_rows_payload(rows), indent=2)}",
        )
    active_workspace = _selected_saved_workspace(rows)
    if active_workspace is None:
        raise AssertionError(
            "Step 2 failed: none of the visible saved workspace rows was marked "
            "active before pressing Arrow Down.\n"
            f"Observed rows: {json.dumps(_saved_workspace_rows_payload(rows), indent=2)}",
        )
    if active_workspace.display_name != ACTIVE_WORKSPACE_DISPLAY_NAME:
        raise AssertionError(
            "Step 2 failed: the preloaded active saved workspace was not the expected "
            "Arrow Down starting point.\n"
            f"Observed active workspace: {active_workspace.display_name!r}\n"
            f"Observed rows: {json.dumps(_saved_workspace_rows_payload(rows), indent=2)}",
        )
    return active_workspace


def _assert_focused_field(
    observation: FocusedElementObservation,
    *,
    expected_label: str,
    step: int,
) -> None:
    if observation.accessible_name == expected_label:
        return
    raise AssertionError(
        f"Step {step} failed: the keyboard setup did not focus the expected "
        f'"{expected_label}" field inside the open workspace switcher.\n'
        f"Observed focus label: {observation.accessible_name!r}\n"
        f"Observed focus role: {observation.role!r}\n"
        f"Observed focus tag: {observation.tag_name!r}",
    )


def _assert_arrow_down_navigated_between_workspaces(
    *,
    observation: dict[str, object],
    before_active_workspace: str,
    expected_active_workspace: str,
) -> None:
    _assert_key_kept_panel_open(
        key="Arrow Down",
        observation=observation,
        expected_focus_label="Saved workspaces",
        allow_focus_change=True,
    )
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
            "surface did not navigate to another workspace while the panel remained "
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
    expected_focus_label: str,
    allow_focus_change: bool,
) -> None:
    switcher = observation["switcher"]
    panel = observation["panel"]
    active = observation["active"]
    monitor = observation["monitor"]
    saved_workspace_rows = observation.get("saved_workspace_rows", [])
    assert isinstance(switcher, dict)
    assert isinstance(panel, dict)
    assert isinstance(active, dict)
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
            "the transition monitor observed the panel become hidden after the key press",
        )
    if int(monitor.get("visible_sample_count", 0)) <= 0:
        failures.append(
            "the transition monitor did not capture any visible switcher samples after the key press",
        )
    if not allow_focus_change and active.get("accessible_name") != expected_focus_label:
        failures.append(
            f"focus moved away from {expected_focus_label!r} to "
            f"{active.get('accessible_name')!r}",
        )

    if failures:
        raise AssertionError(
            f"Step {'3' if key == 'Arrow Down' else '4'} failed: pressing {key} did not "
            "leave the workspace switcher visibly open.\n"
            + "\n".join(f"- {item}" for item in failures)
        )


def _assert_tab_kept_focus_within_panel(
    *,
    before: FocusedElementObservation,
    observation: dict[str, object],
) -> None:
    switcher = observation["switcher"]
    panel = observation["panel"]
    active = observation["active"]
    monitor = observation["monitor"]
    assert isinstance(switcher, dict)
    assert isinstance(panel, dict)
    assert isinstance(active, dict)
    assert isinstance(monitor, dict)
    saved_workspace_rows = observation.get("saved_workspace_rows", [])
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
            "the transition monitor observed the panel become hidden after pressing Tab",
        )
    if int(monitor.get("visible_sample_count", 0)) <= 0:
        failures.append(
            "the transition monitor did not capture any visible switcher samples after Tab",
        )
    after_label = active.get("accessible_name")
    if after_label == before.accessible_name:
        failures.append(
            f"focus did not move away from {before.accessible_name!r}",
        )
    if after_label not in EXPECTED_TAB_TARGET_LABELS:
        failures.append(
            f"focus moved to {after_label!r} instead of another known visible in-panel "
            f"control {list(EXPECTED_TAB_TARGET_LABELS)!r}",
        )

    if failures:
        raise AssertionError(
            "Step 5 failed: pressing Tab from the open workspace switcher did not keep "
            "focus within the visible panel.\n"
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
    error = str(result.get("error", "AssertionError: TS-825 failed"))
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
        (
            "* Started Arrow Down from the visible saved-workspace surface so the "
            "keyboard path targeted the actual workspace list rather than the add-workspace form."
        ),
        (
            "* Pressed Arrow Down and checked whether the active saved workspace moved to another row while the panel stayed open."
        ),
        (
            f"* For the in-panel focus traversal step, moved focus to {{{START_FIELD_LABEL}}} and used Tab to confirm focus stayed inside the panel."
        ),
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
        "",
        "h4. Test file",
        "{code}",
        TEST_FILE_PATH,
        "{code}",
        "",
        "h4. Run command",
        "{code:bash}",
        RUN_COMMAND,
        "{code}",
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
        (
            "- Started Arrow Down from the visible saved-workspace surface so the key path targeted the actual workspace list."
        ),
        "- Pressed Arrow Down, Shift, and Tab while the panel was visible.",
        (
            f"- Used `{START_FIELD_LABEL}` only for the separate Tab focus-traversal step after the workspace-row Arrow Down check."
        ),
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
            "- Added TS-825 live desktop coverage for non-Escape keyboard handling in "
            "the workspace switcher."
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
            f"- Outcome: {_failed_step_summary(result)}"
            if not passed
            else "- Outcome: Arrow Down moved the active saved workspace to another visible row without dismissing the panel, Shift kept the panel open, and Tab moved focus from Repository to another visible in-panel control."
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
            f"# {TICKET_KEY} - Workspace switcher does not support Arrow Down navigation between saved workspaces",
            "",
            "## Steps to reproduce",
            *[f"{index}. {step}" for index, step in enumerate(REQUEST_STEPS, start=1)],
            "",
            "## Exact steps from the test case with observations",
            _annotated_step_line(result, 1, REQUEST_STEPS[0]),
            _annotated_step_line(result, 2, REQUEST_STEPS[1]),
            _annotated_step_line(result, 3, REQUEST_STEPS[2]),
            _annotated_step_line(result, 4, REQUEST_STEPS[3]),
            _annotated_step_line(result, 5, REQUEST_STEPS[4]),
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
                else "- The desktop workspace switcher does not expose a production-visible Arrow Down navigation path between saved workspace rows."
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
    status = _step_status(result, step_number)
    if status == "passed":
        marker = "✅"
    elif status == "failed":
        marker = "❌"
    else:
        marker = "⏭️"
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
        return "not_run"
    for step in steps:
        if isinstance(step, dict) and step.get("step") == step_number:
            return str(step.get("status", "failed"))
    return "not_run"


def _step_observation(result: dict[str, object], step_number: int) -> str:
    steps = result.get("steps", [])
    if not isinstance(steps, list):
        return "Not reached because an earlier test step failed."
    for step in steps:
        if isinstance(step, dict) and step.get("step") == step_number:
            return str(step.get("observed", "<no observation recorded>"))
    first_failed = next(
        (
            step
            for step in steps
            if isinstance(step, dict) and step.get("status") == "failed"
        ),
        None,
    )
    if isinstance(first_failed, dict):
        return (
            f"Not reached because Step {first_failed.get('step')} failed: "
            f"{first_failed.get('action')}"
        )
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
