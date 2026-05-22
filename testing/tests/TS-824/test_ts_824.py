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
    WorkspaceSwitcherEscapeDismissObservation,
    WorkspaceSwitcherFocusOwnershipObservation,
    WorkspaceSwitcherInternalFocusObservation,
    WorkspaceSwitcherObservation,
    WorkspaceSwitcherPanelObservation,
    WorkspaceTriggerFocusabilityObservation,
    WorkspaceSwitcherTransitionMonitorObservation,
    WorkspaceSwitcherTriggerObservation,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.interfaces.web_app_session import FocusedElementObservation  # noqa: E402
from testing.tests.support.live_tracker_app_factory import (  # noqa: E402
    create_live_tracker_app_with_stored_token,
)

TICKET_KEY = "TS-824"
TEST_CASE_TITLE = (
    "Press Escape with focus on internal panel element — workspace switcher "
    "dismisses and restores focus"
)
INPUT_DIR = REPO_ROOT / "input" / TICKET_KEY
DISCUSSIONS_RAW_PATH = INPUT_DIR / "pr_discussions_raw.json"
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-824/test_ts_824.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 960}
TAB_FOCUS_TIMEOUT_MS = 4_000
ESCAPE_DISMISS_TIMEOUT_MS = 4_000
PRE_TAB_TRIGGER_SHIFT_TAB_LIMIT = 3

REQUEST_STEPS = [
    "Launch the application on a desktop browser.",
    "Move keyboard focus to the workspace switcher trigger and open the panel.",
    "Press the 'Tab' key to move keyboard focus to an item within the workspace switcher panel.",
    "Press the 'Escape' key on the keyboard.",
    "Observe the state of the workspace switcher panel.",
]
EXPECTED_RESULT = (
    "The workspace switcher panel closes immediately and keyboard focus is "
    "programmatically returned to the workspace switcher trigger button."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
REVIEW_REPLIES_PATH = OUTPUTS_DIR / "review_replies.json"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts824_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts824_failure.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-824 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
        )
    user = service.fetch_authenticated_user()

    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "test_case_title": TEST_CASE_TITLE,
        "app_url": config.app_url,
        "repository": service.repository,
        "repository_ref": service.ref,
        "browser": "Chromium (Playwright)",
        "os": platform.platform(),
        "run_command": RUN_COMMAND,
        "desktop_viewport": DESKTOP_VIEWPORT,
        "expected_result": EXPECTED_RESULT,
        "tab_focus_timeout_ms": TAB_FOCUS_TIMEOUT_MS,
        "escape_dismiss_timeout_ms": ESCAPE_DISMISS_TIMEOUT_MS,
        "user_login": user.login,
        "steps": [],
        "human_verification": [],
    }

    page: LiveWorkspaceSwitcherPage | None = None
    try:
        with create_live_tracker_app_with_stored_token(config, token=token) as tracker_page:
            page = LiveWorkspaceSwitcherPage(tracker_page)
            try:
                try:
                    runtime = tracker_page.open()
                    result["runtime_state"] = runtime.kind
                    result["runtime_body_text"] = runtime.body_text
                    if runtime.kind != "ready":
                        raise AssertionError(
                            "Step 1 failed: the deployed app did not reach an interactive "
                            "desktop state before the internal-focus Escape scenario began.\n"
                            f"Observed runtime state: {runtime.kind}\n"
                            f"Observed body text:\n{runtime.body_text}",
                        )
                    page.dismiss_connection_banner()
                    page.dismiss_connection_banner()
                    page.navigate_to_section("Dashboard")
                    page.set_viewport(**DESKTOP_VIEWPORT)
                    trigger_before = page.observe_trigger()
                    result["trigger_before"] = _trigger_payload(trigger_before)
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
                        f"trigger_label={trigger_before.semantic_label!r}; "
                        f"trigger_text={trigger_before.visible_text!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Viewed the desktop app shell before opening the panel and "
                        "confirmed Dashboard plus the visible workspace switcher trigger "
                        "were rendered."
                    ),
                    observed=(
                        f"trigger_text={trigger_before.visible_text!r}; "
                        f"top_buttons={list(trigger_before.top_button_labels)!r}"
                    ),
                )

                try:
                    trigger_focusability = page.observe_trigger_focusability()
                    result["trigger_focusability_observation"] = (
                        _trigger_focusability_payload(trigger_focusability)
                    )
                    try:
                        trigger_focus_steps = page.focus_trigger_via_keyboard(max_tabs=24)
                    except AssertionError as error:
                        raise AssertionError(
                            f"{error}\n"
                            "Observed trigger focusability: "
                            f"label={trigger_focusability.label!r}, "
                            f"role={trigger_focusability.role!r}, "
                            f"tag={trigger_focusability.tag_name!r}, "
                            f"tabindex={trigger_focusability.tabindex!r}, "
                            f"keyboard_focusable={trigger_focusability.keyboard_focusable}\n"
                            f"Observed trigger HTML: {trigger_focusability.outer_html}"
                        ) from error
                    focused_trigger = page.active_element()
                    page.press_enter_on_active_element_and_wait_for_surface(
                        timeout_ms=TAB_FOCUS_TIMEOUT_MS,
                    )
                    switcher = page.observe_open_switcher(
                        timeout_ms=TAB_FOCUS_TIMEOUT_MS,
                    )
                    panel = page.observe_open_panel(
                        expected_container_kinds=("anchored-panel", "surface"),
                        timeout_ms=TAB_FOCUS_TIMEOUT_MS,
                    )
                    _assert_desktop_panel_open(
                        trigger=trigger_before,
                        switcher=switcher,
                        panel=panel,
                    )
                    result["trigger_focus_sequence"] = [
                        asdict(step) for step in trigger_focus_steps
                    ]
                    result["focused_trigger_before_open"] = _focused_element_payload(
                        focused_trigger,
                    )
                    result["open_switcher_observation"] = _switcher_payload(switcher)
                    result["open_panel_observation"] = asdict(panel)
                    (
                        pre_tab_focus,
                        pre_tab_restore_attempts,
                    ) = _ensure_trigger_focus_before_internal_tab(
                        page=page,
                        panel=panel,
                        timeout_ms=TAB_FOCUS_TIMEOUT_MS,
                    )
                    result["pre_tab_focus_observation"] = _focus_ownership_payload(
                        pre_tab_focus,
                    )
                    result["pre_tab_trigger_restore_attempts"] = pre_tab_restore_attempts
                    _assert_trigger_focus_restored_before_internal_tab(
                        observation=pre_tab_focus,
                        attempts=pre_tab_restore_attempts,
                    )
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
                        f"tab_steps_to_trigger={len(trigger_focus_steps)}; "
                        f"keyboard_trigger={_last_focus_step_label(trigger_focus_steps)!r}; "
                        f"active_before_open={focused_trigger.accessible_name!r}; "
                        f"container_kind={panel.container_kind}; "
                        f"anchored_to_trigger={panel.anchored_to_trigger}; "
                        f"pre_tab_focus_on_trigger={pre_tab_focus.active_on_trigger}; "
                        f"pre_tab_restore_attempts={max(0, len(pre_tab_restore_attempts) - 1)}; "
                        f"row_count={switcher.row_count}; "
                        f"title_visible={'Workspace switcher' in switcher.switcher_text}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Reached the workspace switcher trigger through real keyboard Tab "
                        "navigation, opened the visible desktop panel from that focused "
                        "trigger, and confirmed the panel title plus saved workspace rows "
                        "were shown before pressing Tab again."
                    ),
                    observed=(
                        f"tab_steps_to_trigger={len(trigger_focus_steps)}; "
                        f"keyboard_trigger={_last_focus_step_label(trigger_focus_steps)!r}; "
                        f"active_before_open={focused_trigger.accessible_name!r}; "
                        "title='Workspace switcher'; "
                        f"pre_tab_focus={pre_tab_focus.active_label!r}; "
                        f"pre_tab_on_trigger={pre_tab_focus.active_on_trigger}; "
                        f"pre_tab_restore_attempts={len(pre_tab_restore_attempts)}; "
                        f"row_count={switcher.row_count}; "
                        f"text_excerpt={switcher.switcher_text!r}"
                    ),
                )

                try:
                    internal_focus = page.observe_internal_focus_after_tab(
                        panel=panel,
                        timeout_ms=TAB_FOCUS_TIMEOUT_MS,
                    )
                    result["tab_focus_observation"] = _internal_focus_payload(internal_focus)
                    _assert_internal_panel_focus(internal_focus)
                except Exception as error:
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
                        "Pressed Tab once and moved focus from "
                        f"{internal_focus.before_label!r} "
                        f"to {internal_focus.after_label!r} "
                        f"(role={internal_focus.after_role!r}, "
                        f"tag={internal_focus.after_tag_name!r}) inside the visible "
                        "workspace switcher panel."
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Opened the desktop workspace switcher and used Tab exactly as a "
                        "keyboard user would to see which live control received focus next."
                    ),
                    observed=(
                        f"before_focus={internal_focus.before_label!r}; "
                        f"after_focus={internal_focus.after_label!r}; "
                        f"after_role={internal_focus.after_role!r}; "
                        f"after_visible={internal_focus.after_visible}; "
                        f"after_in_viewport={internal_focus.after_in_viewport}; "
                        f"after_within_switcher={internal_focus.after_within_switcher}; "
                        f"after_on_trigger={internal_focus.after_on_trigger}"
                    ),
                )

                try:
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
                        "Pressed Escape while a visible internal switcher element had "
                        "keyboard focus, and the transition monitor observed the panel "
                        f"disappear within {ESCAPE_DISMISS_TIMEOUT_MS} ms."
                    ),
                )

                try:
                    trigger_after = page.observe_trigger()
                    focused_after_escape = page.active_element()
                    result["trigger_after"] = _trigger_payload(trigger_after)
                    result["focused_after_escape"] = _focused_element_payload(
                        focused_after_escape,
                    )
                    _assert_escape_focus_restored_to_trigger(
                        trigger_before=trigger_before,
                        trigger_after=trigger_after,
                        focused_after_escape=focused_after_escape,
                    )
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
                        "The workspace switcher surface disappeared, the trigger still "
                        "showed the same active workspace, and pressing Enter without "
                        "clicking reopened the switcher from the restored keyboard focus."
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Pressed Escape from a real focused control inside the open panel "
                        "and then used the keyboard again without clicking to confirm "
                        "focus had returned to the workspace switcher trigger."
                    ),
                    observed=(
                        f"focused_after_escape={focused_after_escape.accessible_name!r}; "
                        f"focused_after_escape_role={focused_after_escape.role!r}; "
                        f"keyboard_reopen_kind={keyboard_reopen_panel.container_kind!r}; "
                        f"keyboard_reopen_rows={keyboard_reopen_switcher.row_count}"
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


def _assert_desktop_panel_open(
    *,
    trigger: WorkspaceSwitcherTriggerObservation,
    switcher: WorkspaceSwitcherObservation,
    panel: WorkspaceSwitcherPanelObservation,
) -> None:
    if switcher.row_count <= 0:
        raise AssertionError(
            "Step 2 failed: opening the workspace switcher did not expose any visible "
            "workspace rows.\n"
            f"Observed switcher text:\n{switcher.switcher_text}",
        )
    if panel.container_kind not in {"anchored-panel", "surface"}:
        raise AssertionError(
            "Step 2 failed: opening the workspace switcher trigger did not open the "
            "expected desktop panel-style surface.\n"
            f"Observed container kind: {panel.container_kind}\n"
            f"Observed bounds: left={panel.left:.1f}, top={panel.top:.1f}, "
            f"width={panel.width:.1f}, height={panel.height:.1f}",
        )
    if panel.width <= 0 or panel.height <= 0:
        raise AssertionError(
            "Step 2 failed: opening the workspace switcher trigger did not expose a "
            "readable desktop panel surface.\n"
            f"Observed panel bounds: left={panel.left:.1f}, top={panel.top:.1f}, "
            f"width={panel.width:.1f}, height={panel.height:.1f}\n"
            f"Observed trigger bounds: left={trigger.left:.1f}, top={trigger.top:.1f}, "
            f"width={trigger.width:.1f}, height={trigger.height:.1f}",
        )


def _assert_internal_panel_focus(observation: WorkspaceSwitcherInternalFocusObservation) -> None:
    failures: list[str] = []

    if not observation.before_on_trigger:
        failures.append(
            "pre-Tab focus was not on the workspace switcher trigger before moving inside the panel"
        )
    if not observation.after_visible:
        failures.append("the focused element after Tab was not visible")
    if not observation.after_in_viewport:
        failures.append("the focused element after Tab was outside the viewport")
    if not observation.after_within_switcher:
        failures.append("focus did not land on an element inside the workspace switcher panel")
    if observation.after_on_trigger:
        failures.append("focus remained on the workspace switcher trigger instead of moving inside the panel")
    if not observation.after_owned_by_switcher:
        failures.append("the focused element after Tab was not owned by the switcher surface")
    if not observation.after_different_from_before:
        failures.append("focus did not move to a different element after pressing Tab")

    if failures:
        raise AssertionError(
            "Step 3 failed: pressing Tab did not move keyboard focus to a visible item "
            "inside the open workspace switcher panel.\n"
            + "\n".join(f"- {item}" for item in failures)
            + "\n"
            + f"Observed before focus: label={observation.before_label!r}, "
            + f"role={observation.before_role!r}, tag={observation.before_tag_name!r}, "
            + f"visible={observation.before_visible}, "
            + f"in_viewport={observation.before_in_viewport}, "
            + f"within_switcher={observation.before_within_switcher}, "
            + f"on_trigger={observation.before_on_trigger}, "
            + f"owned_by_switcher={observation.before_owned_by_switcher}\n"
            + f"Observed after focus: label={observation.after_label!r}, "
            + f"role={observation.after_role!r}, tag={observation.after_tag_name!r}\n"
            + f"Observed after HTML: {observation.after_outer_html}",
        )


def _ensure_trigger_focus_before_internal_tab(
    *,
    page: LiveWorkspaceSwitcherPage,
    panel: WorkspaceSwitcherPanelObservation,
    timeout_ms: int,
    max_shift_tabs: int = PRE_TAB_TRIGGER_SHIFT_TAB_LIMIT,
) -> tuple[WorkspaceSwitcherFocusOwnershipObservation, list[dict[str, object]]]:
    attempts: list[dict[str, object]] = []
    observation = page.observe_focus_ownership(panel=panel)
    attempts.append(
        {
            "attempt": 0,
            "action": "after-open",
            **_focus_ownership_payload(observation),
        },
    )
    if observation.active_on_trigger:
        return observation, attempts

    page.focus_workspace_trigger(timeout_ms=timeout_ms)
    observation = page.observe_focus_ownership(panel=panel)
    attempts.append(
        {
            "attempt": 1,
            "action": "focus_workspace_trigger",
            **_focus_ownership_payload(observation),
        },
    )
    if observation.active_on_trigger:
        return observation, attempts

    for attempt_index in range(1, max_shift_tabs + 1):
        page.press_key("Shift+Tab", timeout_ms=timeout_ms)
        observation = page.observe_focus_ownership(panel=panel)
        attempts.append(
            {
                "attempt": attempt_index + 1,
                "action": "Shift+Tab",
                **_focus_ownership_payload(observation),
            },
        )
        if observation.active_on_trigger:
            return observation, attempts

    return observation, attempts


def _assert_trigger_focus_restored_before_internal_tab(
    *,
    observation: WorkspaceSwitcherFocusOwnershipObservation,
    attempts: list[dict[str, object]],
) -> None:
    if observation.active_on_trigger:
        return
    raise AssertionError(
        "Step 2 failed: after opening the workspace switcher, keyboard focus could not be "
        "restored to the workspace switcher trigger before the Step 3 Tab observation.\n"
        "Observed focus restoration attempts: "
        + " | ".join(_focus_attempt_summary(attempt) for attempt in attempts)
    )


def _focus_attempt_summary(attempt: dict[str, object]) -> str:
    return (
        f"attempt={attempt.get('attempt')}, "
        f"action={attempt.get('action')!r}, "
        f"label={attempt.get('active_label')!r}, "
        f"role={attempt.get('active_role')!r}, "
        f"tag={attempt.get('active_tag_name')!r}, "
        f"within_switcher={attempt.get('active_within_switcher')}, "
        f"on_trigger={attempt.get('active_on_trigger')}, "
        f"owned_by_switcher={attempt.get('focus_owned_by_switcher')}"
    )


def _last_focus_step_label(focus_steps: tuple[object, ...]) -> str | None:
    if not focus_steps:
        return None
    last_step = focus_steps[-1]
    return str(getattr(last_step, "after_label", None) or "") or None


def _assert_escape_surface_dismissal(
    *,
    dismissal: WorkspaceSwitcherEscapeDismissObservation,
    monitor: WorkspaceSwitcherTransitionMonitorObservation,
) -> None:
    failures: list[str] = []

    if not dismissal.dashboard_visible:
        failures.append("the main Dashboard shell was not visibly present after Escape")
    if not dismissal.trigger_visible:
        failures.append("the workspace switcher trigger was not visible after Escape")
    if monitor.sample_count <= 0 or monitor.visible_sample_count <= 0:
        failures.append(
            "the transition monitor did not capture the visible workspace switcher "
            "surface before Escape",
        )
    if not monitor.ever_hidden_after_visible:
        failures.append(
            "the transition monitor never observed the visible workspace switcher "
            "surface disappear after Escape",
        )

    if failures:
        raise AssertionError(
            "Step 4 failed: pressing Escape from a focused internal panel element did "
            "not dismiss the user-visible workspace switcher surface reliably.\n"
            + "\n".join(f"- {item}" for item in failures)
            + "\n"
            + f"Observed monitor kinds: {list(monitor.observed_container_kinds)!r}\n"
            + f"Observed monitor row counts: {list(monitor.observed_row_counts)!r}\n"
            + f"Observed body text:\n{dismissal.body_text}",
        )


def _assert_escape_focus_restored_to_trigger(
    *,
    trigger_before: WorkspaceSwitcherTriggerObservation,
    trigger_after: WorkspaceSwitcherTriggerObservation,
    focused_after_escape: FocusedElementObservation,
) -> None:
    failures: list[str] = []

    if not _is_workspace_trigger_focus(
        focused_after_escape.accessible_name,
        fallback_text=focused_after_escape.text,
    ):
        failures.append(
            "keyboard focus after Escape was not restored to the workspace switcher "
            "trigger",
        )

    if failures:
        raise AssertionError(
            "Step 5 failed: after Escape, the active element was not the workspace "
            "switcher trigger.\n"
            + "\n".join(f"- {item}" for item in failures)
            + "\n"
            + "Observed focused element after Escape: "
            + f"label={focused_after_escape.accessible_name!r}, "
            + f"role={focused_after_escape.role!r}, tag={focused_after_escape.tag_name!r}, "
            + f"text={focused_after_escape.text!r}",
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
            "Step 5 failed: pressing Enter immediately after Escape did not reopen the "
            f"visible workspace switcher from the restored trigger focus ({error})",
        ) from error


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
    _write_review_replies(result, passed=True)


def _write_failure_outputs(result: dict[str, object]) -> None:
    error = str(result.get("error", "AssertionError: TS-824 failed"))
    error_prefix = error.split(":", 1)[0]
    if ":" not in error or not error_prefix.endswith(("Error", "Exception")):
        error = f"AssertionError: {error}"
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
    _write_review_replies(result, passed=False)


def _jira_comment(result: dict[str, object], *, passed: bool) -> str:
    status = "✅ PASSED" if passed else "❌ FAILED"
    lines = [
        "h3. Test Automation Result",
        "",
        f"*Status:* {status}",
        f"*Test Case:* {TICKET_KEY} - {TEST_CASE_TITLE}",
        "",
        "h4. What was tested",
        "* Opened the deployed TrackState app in Chromium with a stored hosted token.",
        "* Opened the desktop workspace switcher from Dashboard.",
        "* Pressed Tab once and checked whether keyboard focus moved to a visible item inside the workspace switcher panel.",
        "* If focus moved inside the panel, the test would continue with Escape dismissal and trigger-focus restoration checks.",
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
        "## Rework summary",
        "- Uses real keyboard `Tab` navigation to reach the visible workspace switcher trigger.",
        "- Opens the switcher from the focused trigger via `Enter` and measures the next trigger-owned `Tab` transition into the panel.",
        "",
        "## What was automated",
        "- Opened the deployed TrackState app in Chromium with a stored hosted token.",
        "- Opened the desktop workspace switcher from Dashboard.",
        "- Pressed Tab once and checked whether focus moved to a visible item inside the switcher panel.",
        "- If focus moved inside the panel, the test would continue with Escape dismissal and trigger-focus restoration checks.",
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
        "- Uses real keyboard navigation to reach the visible workspace switcher trigger and open the panel from that focused state via `Enter`.",
        "- Measures the exact trigger -> panel `Tab` transition the ticket requires before any Escape assertion runs.",
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
            else "- Outcome: Tab moved focus to an internal switcher item, Escape closed the panel, and the trigger was immediately keyboard-usable again."
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
    first_failed_step = _first_failed_step_number(result)
    title, reproduction_steps, missing_capability = _bug_context(result)
    return "\n".join(
        [
            f"# {title}",
            "",
            "## Steps to reproduce",
            *reproduction_steps,
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
                    "first_failed_step": first_failed_step,
                    "trigger_focusability_observation": result.get(
                        "trigger_focusability_observation",
                    ),
                    "trigger_focus_sequence": result.get("trigger_focus_sequence"),
                    "trigger_before": result.get("trigger_before"),
                    "open_switcher_observation": result.get("open_switcher_observation"),
                    "open_panel_observation": result.get("open_panel_observation"),
                    "pre_tab_focus_observation": result.get("pre_tab_focus_observation"),
                    "pre_tab_trigger_restore_attempts": result.get(
                        "pre_tab_trigger_restore_attempts",
                    ),
                    "tab_focus_observation": result.get("tab_focus_observation"),
                    "escape_dismissal_observation": result.get("escape_dismissal_observation"),
                    "escape_transition_monitor": result.get("escape_transition_monitor"),
                    "trigger_after": result.get("trigger_after"),
                    "focused_after_escape": result.get("focused_after_escape"),
                },
                indent=2,
            ),
            "```",
        ],
    ) + "\n"


def _write_review_replies(result: dict[str, object], *, passed: bool) -> None:
    replies = [
        {
            "inReplyToId": thread.get("rootCommentId"),
            "threadId": thread.get("threadId"),
            "reply": _review_reply_text(
                root_comment_id=thread.get("rootCommentId"),
                passed=passed,
                result=result,
            ),
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


def _review_reply_text(
    *,
    root_comment_id: object,
    passed: bool,
    result: dict[str, object],
) -> str:
    rerun_summary = (
        "Re-ran "
        f"`{RUN_COMMAND}`: passed (`1 passed, 0 failed`)."
        if passed
        else "Re-ran "
        f"`{RUN_COMMAND}`: failed at {_failed_step_summary(result)}"
    )
    if root_comment_id == 3284106691:
        return (
            "Fixed: after opening the switcher, TS-824 now checks whether focus stayed on "
            "the trigger and, when it did not, deterministically restores trigger focus "
            "before observing the Step 3 `Tab` transition into the panel. "
            + rerun_summary
        )
    if root_comment_id == 3284106847:
        return (
            "Fixed: `_discussion_threads()` again skips `resolved: true` entries, so "
            "`review_replies.json` only replies to unresolved GitHub review threads. "
            + rerun_summary
        )
    if root_comment_id == 3284189451:
        return (
            "Fixed: Step 2 now opens the workspace switcher by pressing `Enter` on the "
            "keyboard-focused trigger before the panel assertions run, so the TS-824 "
            "flow is exercised from the required keyboard activation path. "
            + rerun_summary
        )
    return "Fixed the requested TS-824 review item. " + rerun_summary


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
            if isinstance(step, dict) and step.get("status") != "passed":
                return f"Step {step.get('step')}: {step.get('observed')}"
    return str(result.get("error", "No failed step recorded."))


def _first_failed_step_number(result: dict[str, object]) -> int | None:
    steps = result.get("steps", [])
    if not isinstance(steps, list):
        return None
    for step in steps:
        if isinstance(step, dict) and step.get("status") != "passed":
            return int(step.get("step", -1))
    return None


def _bug_context(result: dict[str, object]) -> tuple[str, list[str], str]:
    failed_step = _first_failed_step_number(result)
    if failed_step == 2:
        pre_tab_focus = result.get("pre_tab_focus_observation")
        if isinstance(pre_tab_focus, dict):
            return (
                f"{TICKET_KEY} - Opening the workspace switcher does not return focus to the trigger for the Tab transition",
                [
                    "1. Launch the application on a desktop browser.",
                    "2. Reach the workspace switcher trigger by keyboard.",
                    "3. Open the workspace switcher panel from that focused trigger.",
                    "4. Attempt to restore focus to the workspace switcher trigger without clicking before pressing `Tab` again.",
                    "5. Observe that focus remains away from the trigger.",
                ],
                (
                    "After the workspace switcher opens, the production UI does not keep "
                    "or restore keyboard focus to the workspace switcher trigger before "
                    "the next Tab transition. That prevents the required `trigger -> "
                    "internal panel element -> Escape` flow from being exercised from a "
                    "valid trigger-owned starting state."
                ),
            )
        focusability = result.get("trigger_focusability_observation")
        keyboard_focusable = False
        tabindex: object = None
        if isinstance(focusability, dict):
            keyboard_focusable = bool(focusability.get("keyboard_focusable"))
            tabindex = focusability.get("tabindex")
        return (
            (
                f"{TICKET_KEY} - Workspace switcher trigger is skipped by sequential keyboard navigation in desktop web"
                if keyboard_focusable
                else f"{TICKET_KEY} - Workspace switcher trigger is not keyboard-focusable in desktop web"
            ),
            [
                "1. Launch the application on a desktop browser.",
                "2. Navigate to Dashboard in the desktop web app.",
                "3. Move keyboard focus to the visible top-bar search field.",
                "4. Press `Tab` repeatedly to reach the visible workspace switcher trigger.",
                (
                    "5. Observe that focus cycles other controls and never lands on the workspace switcher trigger, even though the visible trigger advertises keyboard focusability."
                    if keyboard_focusable
                    else "5. Observe that focus cycles other controls and never lands on the workspace switcher trigger."
                ),
            ],
            (
                "The production desktop web UI exposes a visible workspace switcher "
                "trigger with role `button` and "
                f"`tabindex={tabindex!r}`, but real sequential Tab navigation from the "
                "search field still skips it and cycles other controls instead. Because "
                "the trigger cannot be reached through the production keyboard tab order, "
                "the required `trigger -> internal panel element -> Escape` flow cannot "
                "be exercised from the live UI."
                if keyboard_focusable
                else "The production desktop web UI does not expose the visible workspace "
                "switcher trigger as a keyboard-focusable control. In the failing run the "
                "visible trigger was rendered with role `button` but `tabindex=None`, and "
                "real Tab navigation from the search field never reached it. Because the "
                "trigger cannot own keyboard focus, the required `trigger -> internal panel "
                "element -> Escape` flow cannot be exercised from the production UI."
            ),
        )
    if failed_step == 3:
        tab_focus = result.get("tab_focus_observation")
        if isinstance(tab_focus, dict) and not bool(tab_focus.get("before_on_trigger")):
            return (
                f"{TICKET_KEY} - Opening the workspace switcher moves focus inside the panel before the Tab transition",
                [
                    "1. Launch the application on a desktop browser.",
                    "2. Reach the workspace switcher trigger by keyboard and open the panel.",
                    "3. Observe the active element before pressing `Tab` again.",
                    "4. Press `Tab` once and compare the before/after focus targets.",
                ],
                (
                    "The open workspace switcher does not preserve trigger-owned focus for "
                    "the ticket's keyboard path. Focus is already inside the panel before "
                    "the Step 3 Tab press, so the required `trigger -> internal panel "
                    "element` transition cannot be exercised as specified."
                ),
            )
        return (
            f"{TICKET_KEY} - Tab does not move focus into the open workspace switcher panel",
            [
                "1. Launch the application on a desktop browser.",
                "2. Reach the workspace switcher trigger by keyboard and open the panel.",
                "3. Press `Tab` once while the panel is open.",
                "4. Observe the newly focused element.",
            ],
            (
                "After the workspace switcher is opened from a keyboard-focused trigger, "
                "the next Tab press does not move focus to a visible interactive element "
                "inside the panel. The production panel therefore does not expose the "
                "ticket's required keyboard path into the switcher surface."
            ),
        )
    if failed_step == 4:
        return (
            f"{TICKET_KEY} - Escape does not dismiss the open workspace switcher panel",
            [
                "1. Launch the application on a desktop browser.",
                "2. Reach the workspace switcher trigger by keyboard and open the panel.",
                "3. Press `Tab` to move focus to an interactive element inside the panel.",
                "4. Press `Escape`.",
                "5. Observe whether the visible switcher surface disappears.",
            ],
            (
                "The production workspace switcher does not reliably dismiss the visible "
                "desktop panel when Escape is pressed from an internally focused panel "
                "element."
            ),
        )
    if failed_step == 5:
        return (
            f"{TICKET_KEY} - Escape dismissal does not restore focus to the workspace switcher trigger",
            [
                "1. Launch the application on a desktop browser.",
                "2. Reach the workspace switcher trigger by keyboard and open the panel.",
                "3. Press `Tab` to move focus to an interactive element inside the panel.",
                "4. Press `Escape` to dismiss the panel.",
                "5. Observe the active element after dismissal.",
            ],
            (
                "After Escape dismisses the visible workspace switcher panel, the "
                "production UI does not restore keyboard focus to the workspace switcher "
                "trigger as required."
            ),
        )
    return (
        f"{TICKET_KEY} - Desktop workspace switcher Escape flow is broken",
        [
            "1. Launch the application on a desktop browser.",
            "2. Attempt the TS-824 workspace-switcher keyboard scenario.",
            "3. Observe the first failing boundary.",
        ],
        (
            "The production desktop workspace-switcher flow does not satisfy the TS-824 "
            "keyboard-dismissal requirement."
        ),
    )


def _step_status(result: dict[str, object], step_number: int) -> str:
    steps = result.get("steps", [])
    if not isinstance(steps, list):
        return "failed"
    for step in steps:
        if isinstance(step, dict) and int(step.get("step", -1)) == step_number:
            return str(step.get("status", "failed"))
    return "failed"


def _step_observation(result: dict[str, object], step_number: int) -> str:
    steps = result.get("steps", [])
    if not isinstance(steps, list):
        return "<no observation recorded>"
    last_failed_step: int | None = None
    for step in steps:
        if not isinstance(step, dict):
            continue
        current_step = int(step.get("step", -1))
        if current_step == step_number:
            return str(step.get("observed", "<no observation recorded>"))
        if step.get("status") != "passed":
            last_failed_step = current_step
    if last_failed_step is not None and step_number > last_failed_step:
        return f"Not reached because step {last_failed_step} failed."
    return "<no observation recorded>"


def _trigger_payload(trigger: WorkspaceSwitcherTriggerObservation) -> dict[str, object]:
    return {
        "semantic_label": trigger.semantic_label,
        "visible_text": trigger.visible_text,
        "raw_text_lines": list(trigger.raw_text_lines),
        "display_name": trigger.display_name,
        "workspace_type": trigger.workspace_type,
        "state_label": trigger.state_label,
        "viewport_width": trigger.viewport_width,
        "viewport_height": trigger.viewport_height,
        "bounds": {
            "left": trigger.left,
            "top": trigger.top,
            "width": trigger.width,
            "height": trigger.height,
        },
        "top_button_labels": list(trigger.top_button_labels),
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


def _escape_dismissal_payload(
    observation: WorkspaceSwitcherEscapeDismissObservation,
) -> dict[str, object]:
    return {
        "body_text": observation.body_text,
        "dashboard_visible": observation.dashboard_visible,
        "trigger_visible": observation.trigger_visible,
    }


def _switcher_payload(switcher: WorkspaceSwitcherObservation) -> dict[str, object]:
    return {
        "row_count": switcher.row_count,
        "switcher_text": switcher.switcher_text,
        "rows": [
            {
                "display_name": row.display_name,
                "target_type_label": row.target_type_label,
                "state_label": row.state_label,
                "detail_text": row.detail_text,
                "visible_text": row.visible_text,
                "selected": row.selected,
                "action_labels": list(row.action_labels),
                "button_labels": list(row.button_labels),
            }
            for row in switcher.rows
        ],
    }


def _transition_monitor_payload(
    monitor: WorkspaceSwitcherTransitionMonitorObservation,
) -> dict[str, object]:
    return {
        "sample_count": monitor.sample_count,
        "visible_sample_count": monitor.visible_sample_count,
        "hidden_sample_count": monitor.hidden_sample_count,
        "ever_hidden_after_visible": monitor.ever_hidden_after_visible,
        "observed_container_kinds": list(monitor.observed_container_kinds),
        "observed_row_counts": list(monitor.observed_row_counts),
        "observed_active_workspace_names": list(
            monitor.observed_active_workspace_names,
        ),
        "latest_visible_container_kind": monitor.latest_visible_container_kind,
        "latest_visible_row_count": monitor.latest_visible_row_count,
        "latest_visible_active_workspace_name": (
            monitor.latest_visible_active_workspace_name
        ),
    }


def _internal_focus_payload(
    observation: WorkspaceSwitcherInternalFocusObservation,
) -> dict[str, object]:
    return {
        "before_focus": {
            "label": observation.before_label,
            "role": observation.before_role,
            "tag_name": observation.before_tag_name,
            "outer_html": observation.before_outer_html,
        },
        "before_visible": observation.before_visible,
        "before_in_viewport": observation.before_in_viewport,
        "before_within_switcher": observation.before_within_switcher,
        "before_on_trigger": observation.before_on_trigger,
        "before_owned_by_switcher": observation.before_owned_by_switcher,
        "after_focus": {
            "label": observation.after_label,
            "role": observation.after_role,
            "tag_name": observation.after_tag_name,
            "outer_html": observation.after_outer_html,
        },
        "after_visible": observation.after_visible,
        "after_in_viewport": observation.after_in_viewport,
        "after_within_switcher": observation.after_within_switcher,
        "after_on_trigger": observation.after_on_trigger,
        "after_owned_by_switcher": observation.after_owned_by_switcher,
        "after_different_from_before": observation.after_different_from_before,
    }


def _focused_element_payload(focused: FocusedElementObservation) -> dict[str, object]:
    return {
        "accessible_name": focused.accessible_name,
        "role": focused.role,
        "tag_name": focused.tag_name,
        "text": focused.text,
        "tabindex": focused.tabindex,
        "outer_html": focused.outer_html,
    }


def _is_workspace_trigger_focus(
    accessible_name: str | None,
    *,
    fallback_text: str | None = None,
) -> bool:
    candidates = (accessible_name or "", fallback_text or "")
    return any(candidate.startswith("Workspace switcher:") for candidate in candidates)


if __name__ == "__main__":
    main()
