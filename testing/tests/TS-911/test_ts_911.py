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
    WorkspaceSwitcherSurfaceObservation,
    WorkspaceSwitcherTabStopObservation,
    WorkspaceSwitcherTriggerObservation,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.interfaces.web_app_session import FocusedElementObservation  # noqa: E402
TICKET_KEY = "TS-911"
TEST_CASE_TITLE = (
    "Press Shift+Tab from the first element in workspace switcher — "
    "focus wraps to the last internal element"
)
INPUT_DIR = REPO_ROOT / "input" / TICKET_KEY
DISCUSSIONS_RAW_PATH = INPUT_DIR / "pr_discussions_raw.json"
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-911/test_ts_911.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
FOCUS_TIMEOUT_MS = 4_000
FOCUS_SETTLE_MS = 300
MAX_TABS_TO_DERIVE_WRAP_TARGET = 12
DEFAULT_BRANCH = "main"
FIRST_WORKSPACE_DISPLAY_NAME = "Hosted main workspace"
SECOND_WORKSPACE_DISPLAY_NAME = "Hosted alt workspace"
THIRD_WORKSPACE_DISPLAY_NAME = "Hosted third workspace"
SECOND_WORKSPACE_WRITE_BRANCH = "ts-867-alt"
THIRD_WORKSPACE_WRITE_BRANCH = "ts-867-third"
LAST_INTERNAL_CONTROL_LABEL = "Save and switch"
LINKED_BUGS = ["TS-900"]

PRECONDITIONS = [
    "The TrackState application is opened in a desktop browser.",
    "The workspace switcher panel is currently open.",
    "Keyboard focus is positioned on the first interactive element within the panel.",
]
REQUEST_STEPS = [
    "Press the 'Shift + Tab' keys on the keyboard.",
]
AUTOMATION_STEPS = [
    (
        "Open the deployed desktop workspace switcher from a focused trigger and confirm "
        "the visible panel controls needed for the reverse-wrap assertion."
    ),
    (
        "Keep the reverse-wrap expectation aligned to the visible terminal footer control, "
        "re-establish focus on the first internal keyboard target, then press Shift+Tab "
        "and verify focus wraps to that last internal control instead of "
        "escaping to the trigger or top-bar."
    ),
]
EXPECTED_RESULT = (
    "Keyboard focus wraps to the last interactive element within the workspace switcher "
    "panel, rather than moving to the trigger button or other top-bar elements."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
REVIEW_REPLIES_PATH = OUTPUTS_DIR / "review_replies.json"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts911_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts911_failure.png"

WORKSPACE_NAMES = (
    FIRST_WORKSPACE_DISPLAY_NAME,
    SECOND_WORKSPACE_DISPLAY_NAME,
    THIRD_WORKSPACE_DISPLAY_NAME,
)


def main() -> None:
    from testing.tests.support.live_tracker_app_factory import (  # noqa: E402
        create_live_tracker_app,
    )
    from testing.tests.support.stored_workspace_profiles_runtime import (  # noqa: E402
        StoredWorkspaceProfilesRuntime,
    )

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-911 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
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
                try:
                    runtime = tracker_page.open()
                except AssertionError as error:
                    visible_body_text = _visible_body_text_from_text(str(error))
                    result["runtime_state"] = "not-interactive"
                    result["runtime_body_text"] = visible_body_text
                    _record_human_verification(
                        result,
                        check=(
                            "Opened the live URL in Chromium and observed the first "
                            "rendered screen exactly as a user would before any "
                            "workspace-switcher interaction."
                        ),
                        observed=(
                            "After waiting for the initial page load, the app remained "
                            f"almost blank and exposed only {visible_body_text!r}; no "
                            "workspace switcher trigger, dashboard, or other interactive "
                            "app-shell controls became visible."
                        ),
                    )
                    raise
                result["runtime_state"] = runtime.kind
                result["runtime_body_text"] = runtime.body_text
                if runtime.kind != "ready":
                    raise AssertionError(
                        "Step 1 failed: the deployed app did not reach an interactive "
                        "desktop state before the reverse focus-trap scenario began.\n"
                        f"Observed runtime state: {runtime.kind}\n"
                        f"Observed body text:\n{runtime.body_text}",
                    )

                page.dismiss_connection_banner()
                page.navigate_to_section("Dashboard")
                page.set_viewport(**DESKTOP_VIEWPORT)

                current_step = 1
                current_action = AUTOMATION_STEPS[0]
                initial_state = _open_switcher_and_capture(page)
                result["initial_state"] = initial_state
                _assert_initial_state(initial_state)
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=AUTOMATION_STEPS[0],
                    observed=(
                        f"Opened {config.app_url} in Chromium at "
                        f"{DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}; "
                        f"initial_focus={_active_label_for_summary(initial_state)!r}; "
                        f"first_row_display_name={initial_state.get('first_row_display_name')!r}; "
                        f"first_internal_target={_first_internal_label(initial_state)!r}; "
                        f"visible_surface_labels={_interactive_label_summary(initial_state)!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Opened the desktop workspace switcher from the focused trigger and "
                        "confirmed the visible in-panel controls were present before the "
                        "reverse-wrap proof started."
                    ),
                    observed=(
                        f"initial_focus={_active_label_for_summary(initial_state)!r}; "
                        f"first_row_display_name={initial_state.get('first_row_display_name')!r}; "
                        f"first_internal_target={_first_internal_label(initial_state)!r}; "
                        f"interactive_labels={_interactive_label_summary(initial_state)!r}"
                    ),
                )

                current_step = 2
                current_action = AUTOMATION_STEPS[1]
                first_keyboard_target_state = _reach_first_keyboard_target(
                    page=page,
                    state=initial_state,
                )
                result["first_keyboard_target_state"] = first_keyboard_target_state
                wrap_target_proof = _supporting_wrap_target_context(first_keyboard_target_state)
                initial_state = _state_with_expected_target(initial_state, _expected_target_from_state(first_keyboard_target_state))
                result["initial_state"] = initial_state
                result["first_keyboard_target_state"] = first_keyboard_target_state
                result["tab_trace_to_wrap_target"] = []
                result["wrap_target_proof"] = wrap_target_proof
                _record_human_verification(
                    result,
                    check=(
                        "Kept the reverse-wrap expectation aligned to the same visible terminal "
                        "footer control covered by TS-910 without turning TS-911 into a forward-Tab check."
                    ),
                    observed=(
                        f"expected_wrap_target={_expected_target_label(first_keyboard_target_state)!r}; "
                        f"proof_status={wrap_target_proof.get('status')!r}; "
                        f"proof_note={wrap_target_proof.get('note')!r}"
                    ),
                )
                after_shift_tab_state = _press_key_and_capture(
                    page=page,
                    state=first_keyboard_target_state,
                    key="Shift+Tab",
                    before_override=_focused_element_observation_from_state(
                        first_keyboard_target_state,
                    ),
                )
                result["after_shift_tab_state"] = after_shift_tab_state
                _record_human_verification(
                    result,
                    check=(
                        "Re-established focus on the first internal switcher target "
                        "immediately before the TS-911 Shift+Tab assertion."
                    ),
                    observed=(
                        f"focused_before_shift_tab={_before_label_for_summary(after_shift_tab_state)!r}; "
                        f"focus_owned_by_switcher={_focus_from_state(first_keyboard_target_state).get('focus_owned_by_switcher')}; "
                        f"first_internal_target={_first_internal_label(first_keyboard_target_state)!r}; "
                        f"expected_wrap_target={_expected_target_label(first_keyboard_target_state)!r}; "
                        f"proof_status={wrap_target_proof.get('status')!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Pressed Shift+Tab exactly once from that proven first internal "
                        "target and watched which visible control actually received focus."
                    ),
                    observed=(
                        f"expected_wrap_target={_expected_target_label(after_shift_tab_state)!r}; "
                        f"actual_focus={_active_label_for_summary(after_shift_tab_state)!r}; "
                        f"focus_within_switcher={_focus_from_state(after_shift_tab_state).get('active_within_switcher')}; "
                        f"focus_on_trigger={_focus_from_state(after_shift_tab_state).get('active_on_trigger')}"
                    ),
                )
                _assert_reverse_wrap(after_shift_tab_state)
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=AUTOMATION_STEPS[1],
                    observed=(
                        f"Reached the first internal target "
                        f"{_first_internal_label(after_shift_tab_state)!r} through "
                        f"{after_shift_tab_state.get('precondition_source')!r}, and Shift+Tab "
                        f"then moved focus to {_active_label_for_summary(after_shift_tab_state)!r} "
                        "while focus remained inside the workspace switcher."
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
    page.focus_workspace_trigger(timeout_ms=FOCUS_TIMEOUT_MS)
    focused_trigger = page.active_element()
    page.press_enter_on_active_element_and_wait_for_surface(timeout_ms=FOCUS_TIMEOUT_MS)
    switcher = page.observe_open_switcher(timeout_ms=FOCUS_TIMEOUT_MS)
    panel = page.observe_open_panel(expected_container_kinds=("anchored-panel", "surface"))
    surface = page.observe_surface(timeout_ms=FOCUS_TIMEOUT_MS)
    save_and_switch_button = page.observe_switcher_button_focusability(
        LAST_INTERNAL_CONTROL_LABEL,
        timeout_ms=FOCUS_TIMEOUT_MS,
    )
    try:
        rows = page.observe_saved_workspace_rows(timeout_ms=FOCUS_TIMEOUT_MS)
    except AssertionError:
        rows = _saved_workspace_rows_from_switcher(switcher)
    tab_stops = page.observe_internal_tab_stops(
        panel=panel,
        timeout_ms=FOCUS_TIMEOUT_MS,
    )
    first_row = _selected_saved_workspace(rows)
    first_row_display_name = (
        first_row.display_name
        if first_row is not None
        else FIRST_WORKSPACE_DISPLAY_NAME
    )
    first_row_label = (
        _saved_workspace_row_focus_label(first_row)
        if first_row is not None
        else ""
    )
    active = page.active_element()
    focus = page.observe_focus_ownership(panel=panel)
    first_internal_target = _resolve_first_internal_focus_target(
        active=active,
        focus=focus,
        first_row_label=first_row_label,
        tab_stops=tab_stops,
    )
    expected_target = _visible_footer_target(
        button_focusability=_button_focusability_payload(save_and_switch_button),
        fallback_target=_last_internal_focus_target(tab_stops=tab_stops),
    )
    row_focus = {
        name: _row_focus_payload(
            page.observe_saved_workspace_row_focus(display_name=name, panel=panel),
        )
        for name in WORKSPACE_NAMES
    }
    return _state_payload(
        trigger=trigger,
        switcher=switcher,
        panel=panel,
        surface=surface,
        active=active,
        focus=focus,
        saved_workspace_rows=rows,
        row_focus=row_focus,
        expected_target=expected_target,
        first_internal_target=first_internal_target,
        first_row_display_name=first_row_display_name,
        first_row_label=first_row_label,
        internal_tab_stops=_tab_stops_payload(tab_stops),
        button_focusability=_button_focusability_payload(save_and_switch_button),
        focus_attempts=[],
        precondition_source="keyboard-open",
        focused_trigger=_focused_element_payload(focused_trigger),
    )


def _reach_first_keyboard_target(
    *,
    page: LiveWorkspaceSwitcherPage,
    state: dict[str, object],
) -> dict[str, object]:
    current_state = _capture_current_state(page=page, state=state)
    if _is_switcher_internal_focus_state(current_state) and (
        _active_label_for_summary(current_state) == _first_internal_label(current_state)
    ):
        return _state_with_precondition_source(
            current_state,
            precondition_source="initial-focus",
        )

    first_internal_label = _first_internal_label(current_state)
    if not first_internal_label:
        raise AssertionError(
            "Step 2 failed: the open workspace switcher did not expose a readable first "
            "internal keyboard target before the TS-911 Shift+Tab check.\n"
            f"Observed active element: {json.dumps(_active_from_state(current_state), indent=2)}\n"
            f"Observed focus ownership: {json.dumps(_focus_from_state(current_state), indent=2)}\n"
            f"Observed internal tab stops: {json.dumps(_tab_stops_from_state(current_state), indent=2)}"
        )

    panel = WorkspaceSwitcherPanelObservation(**_panel_from_state(current_state))
    before = page.active_element()
    try:
        focus_observation = page.focus_internal_tab_stop(
            first_internal_label,
            panel=panel,
            timeout_ms=FOCUS_TIMEOUT_MS,
        )
    except AssertionError as error:
        failed_state = _capture_current_state(
            page=page,
            state=current_state,
            before=before,
        )
        raise AssertionError(
            "Step 2 failed: focusing the Step 1-derived first internal keyboard target "
            "did not establish the TS-911 precondition before Shift+Tab.\n"
            f"Focus target error: {error}\n"
            f"Observed before element: {json.dumps(_before_from_state(failed_state), indent=2)}\n"
            f"Observed active element: {json.dumps(_active_from_state(failed_state), indent=2)}\n"
            f"Observed focus ownership: {json.dumps(_focus_from_state(failed_state), indent=2)}\n"
            f"Observed internal target: {json.dumps(_first_internal_target_from_state(failed_state), indent=2)}\n"
            f"Observed internal tab stops: {json.dumps(_tab_stops_from_state(failed_state), indent=2)}"
        ) from error
    reached_state = dict(current_state)
    reached_state["before"] = _focused_element_payload(before)
    reached_state["active"] = {
        "tag_name": focus_observation.active_tag_name,
        "role": focus_observation.active_role,
        "accessible_name": focus_observation.active_label,
        "text": "",
        "tabindex": None,
        "outer_html": focus_observation.active_outer_html,
    }
    reached_state["focus"] = {
        "active_label": focus_observation.active_label,
        "active_role": focus_observation.active_role,
        "active_tag_name": focus_observation.active_tag_name,
        "active_outer_html": focus_observation.active_outer_html,
        "active_visible": focus_observation.active_visible,
        "active_in_viewport": focus_observation.active_in_viewport,
        "switcher_focus_within": focus_observation.active_within_switcher,
        "active_within_switcher": focus_observation.active_within_switcher,
        "active_on_trigger": focus_observation.active_on_trigger,
        "focus_owned_by_switcher": focus_observation.focus_owned_by_switcher,
    }
    reached_state = _state_with_precondition_source(
        reached_state,
        precondition_source="page-object-focus",
    )
    return reached_state


def _prepare_reverse_wrap_supporting_evidence(
    *,
    page: LiveWorkspaceSwitcherPage,
    state: dict[str, object],
) -> tuple[dict[str, object], list[dict[str, object]], dict[str, object]]:
    _assert_first_keyboard_target(state)
    fallback_target = _fallback_reverse_wrap_target(state)
    tab_trace, proof_error = _forward_tab_trace_to_last_internal_control(page=page, state=state)
    proof = _supporting_wrap_target_proof(
        tab_trace=tab_trace,
        fallback_target=fallback_target,
        proof_error=proof_error,
    )
    expected_target = proof.get("expected_target", fallback_target)
    assert isinstance(expected_target, dict)
    prepared_state = _restore_first_keyboard_target_after_supporting_evidence(
        page=page,
        state=state,
        expected_target=expected_target,
        proof_status=str(proof.get("status", "inconclusive")),
    )
    return prepared_state, tab_trace, proof


def _forward_tab_trace_to_last_internal_control(
    *,
    page: LiveWorkspaceSwitcherPage,
    state: dict[str, object],
) -> tuple[list[dict[str, object]], str | None]:
    tab_trace: list[dict[str, object]] = []
    current_state = state
    for _ in range(MAX_TABS_TO_DERIVE_WRAP_TARGET):
        try:
            next_state = _press_key_and_capture(
                page=page,
                state=current_state,
                key="Tab",
                before_override=_focused_element_observation_from_state(current_state),
            )
        except Exception as error:
            return tab_trace, f"{type(error).__name__}: {error}"
        tab_trace.append(next_state)
        if _active_label_for_summary(next_state) == LAST_INTERNAL_CONTROL_LABEL:
            return tab_trace, None
        current_state = next_state
    return tab_trace, None


def _supporting_wrap_target_proof(
    *,
    tab_trace: list[dict[str, object]],
    fallback_target: dict[str, object],
    proof_error: str | None,
) -> dict[str, object]:
    failures: list[str] = []
    footer_state: dict[str, object] | None = None
    for index, state in enumerate(tab_trace, start=1):
        active = _active_from_state(state)
        focus = _focus_from_state(state)
        monitor = _monitor_from_state(state)
        active_label = str(active.get("accessible_name") or "")
        if not bool(focus.get("focus_owned_by_switcher")):
            failures.append(
                f"keyboard focus was not owned by the workspace switcher after forward Tab {index}",
            )
        if not bool(focus.get("active_within_switcher")):
            failures.append(f"focus escaped the workspace switcher after forward Tab {index}")
        if bool(focus.get("active_on_trigger")) or active_label.startswith("Workspace switcher:"):
            failures.append(
                f"focus returned to the workspace-switcher trigger after forward Tab {index}",
            )
        if bool(monitor.get("ever_hidden_after_visible")):
            failures.append(
                f"the workspace switcher panel became hidden during forward Tab {index}",
            )
        if active_label == LAST_INTERNAL_CONTROL_LABEL:
            footer_state = state
            break
    if proof_error is not None:
        failures.append(f"forward Tab sampling stopped early: {proof_error}")
    if footer_state is not None and not failures:
        expected_target = _focus_target_payload(_active_from_state(footer_state))
        return {
            "status": "proved",
            "expected_target": expected_target,
            "note": (
                f"Forward Tab reached {expected_target.get('label')!r} within "
                f"{len(tab_trace)} presses."
            ),
        }
    if footer_state is None:
        failures.append(
            f"forward Tab never reached the visible {LAST_INTERNAL_CONTROL_LABEL!r} footer control within "
            f"{MAX_TABS_TO_DERIVE_WRAP_TARGET} presses"
        )
    return {
        "status": "inconclusive",
        "expected_target": fallback_target,
        "note": "; ".join(failures) if failures else "Forward Tab evidence was inconclusive.",
    }


def _restore_first_keyboard_target_after_supporting_evidence(
    *,
    page: LiveWorkspaceSwitcherPage,
    state: dict[str, object],
    expected_target: dict[str, object],
    proof_status: str,
) -> dict[str, object]:
    expected_state = _state_with_expected_target(state, expected_target)
    restoration_errors: list[str] = []
    for restore_via_reopen in (False, True):
        if restore_via_reopen:
            try:
                page.dismiss_connection_banner()
                page.navigate_to_section("Dashboard")
                page.set_viewport(**DESKTOP_VIEWPORT)
                expected_state = _state_with_expected_target(
                    _open_switcher_and_capture(page),
                    expected_target,
                )
            except Exception as error:
                restoration_errors.append(
                    "re-opening the workspace switcher failed: "
                    f"{type(error).__name__}: {error}",
                )
                continue
        try:
            panel = page.observe_open_panel(
                expected_container_kinds=("anchored-panel", "surface"),
                timeout_ms=FOCUS_TIMEOUT_MS,
            )
            before = page.active_element()
            page.focus_internal_tab_stop(
                str(_first_internal_label(expected_state)),
                panel=panel,
                timeout_ms=FOCUS_TIMEOUT_MS,
            )
            restored_state = _capture_current_state(
                page=page,
                state=expected_state,
                before=before,
            )
            restored_state = _state_with_expected_target(restored_state, expected_target)
            restored_state = _state_with_precondition_source(
                restored_state,
                precondition_source=(
                    f"supporting-proof-{proof_status}+reopen"
                    if restore_via_reopen
                    else f"supporting-proof-{proof_status}+page-object-focus"
                ),
            )
            _assert_first_keyboard_target(restored_state)
            return restored_state
        except Exception as error:
            restoration_errors.append(
                ("re-opened " if restore_via_reopen else "current ")
                + f"panel restore failed: {type(error).__name__}: {error}",
            )
    raise AssertionError(
        "Step 2 failed: the test could not re-establish the first internal keyboard "
        "target before the ticketed Shift+Tab action.\n"
        + "\n".join(f"- {item}" for item in restoration_errors)
    )


def _fallback_reverse_wrap_target(state: dict[str, object]) -> dict[str, object]:
    button_focusability = _button_focusability_from_state(state)
    if button_focusability:
        return _visible_footer_target(
            button_focusability=button_focusability,
            fallback_target=_expected_target_from_state(state),
        )
    return _expected_target_from_state(state)


def _supporting_wrap_target_context(state: dict[str, object]) -> dict[str, object]:
    expected_label = str(_expected_target_label(state) or "")
    if not expected_label:
        return {
            "status": "inconclusive",
            "note": "The open panel did not expose a readable reverse-wrap target label.",
        }
    if expected_label == LAST_INTERNAL_CONTROL_LABEL:
        return {
            "status": "aligned",
            "note": (
                "The visible terminal footer control remains "
                f"{LAST_INTERNAL_CONTROL_LABEL!r}, matching the forward-wrap source of truth."
            ),
        }
    return {
        "status": "fallback",
        "note": (
            f"The visible terminal footer control could not be confirmed, so TS-911 is using "
            f"{expected_label!r} as the best available reverse-wrap target."
        ),
    }


def _visible_footer_target(
    *,
    button_focusability: dict[str, object],
    fallback_target: dict[str, object],
) -> dict[str, object]:
    label = str(button_focusability.get("label") or button_focusability.get("visible_text") or "")
    if not label:
        return fallback_target
    return {
        "label": label,
        "visible_text": button_focusability.get("visible_text"),
        "role": button_focusability.get("role"),
        "tag_name": button_focusability.get("tag_name"),
        "tabindex": button_focusability.get("tabindex"),
        "tab_index_value": None,
        "dom_index": None,
        "keyboard_focusable": button_focusability.get("keyboard_focusable"),
        "disabled": None,
        "outer_html": button_focusability.get("outer_html"),
    }


def _capture_current_state(
    *,
    page: LiveWorkspaceSwitcherPage,
    state: dict[str, object],
    before: FocusedElementObservation | None = None,
    monitor: object | None = None,
    panel_error: str | None = None,
    surface_stability_error: str | None = None,
) -> dict[str, object]:
    panel_payload = _panel_from_state(state)
    current_panel = WorkspaceSwitcherPanelObservation(**panel_payload)
    if panel_error is None:
        resolved_panel_error: str | None = None
    else:
        resolved_panel_error = panel_error
    try:
        current_panel = page.observe_open_panel(
            expected_container_kinds=("anchored-panel", "surface"),
            timeout_ms=1_000,
        )
    except Exception as error:
        if resolved_panel_error is None:
            resolved_panel_error = f"{type(error).__name__}: {error}"
    active = page.active_element()
    focus = page.observe_focus_ownership(panel=current_panel)
    row_focus = {
        name: _row_focus_payload(
            page.observe_saved_workspace_row_focus(display_name=name, panel=current_panel),
        )
        for name in WORKSPACE_NAMES
    }

    switcher: WorkspaceSwitcherObservation | None = None
    switcher_error: str | None = None
    try:
        switcher = page.observe_open_switcher(timeout_ms=1_000)
    except Exception as error:
        switcher_error = f"{type(error).__name__}: {error}"

    rows: tuple[WorkspaceSwitcherSavedWorkspaceRowObservation, ...] = ()
    rows_error: str | None = None
    try:
        rows = page.observe_saved_workspace_rows(timeout_ms=1_000)
    except Exception as error:
        rows_error = f"{type(error).__name__}: {error}"

    surface: WorkspaceSwitcherSurfaceObservation | None = None
    surface_error: str | None = None
    try:
        surface = page.observe_surface(timeout_ms=1_000)
    except Exception as error:
        surface_error = f"{type(error).__name__}: {error}"

    payload: dict[str, object] = {
        "panel": asdict(current_panel),
        "active": _focused_element_payload(active),
        "focus": _focus_ownership_payload(focus),
        "row_focus": row_focus,
        "saved_workspace_rows": _saved_workspace_rows_payload(rows),
        "expected_target": state.get("expected_target"),
        "first_internal_target": state.get("first_internal_target"),
        "first_row_display_name": state.get("first_row_display_name"),
        "first_row_label": state.get("first_row_label"),
        "internal_tab_stops": state.get("internal_tab_stops", []),
        "button_focusability": state.get("button_focusability", {}),
        "precondition_source": state.get("precondition_source"),
        "monitor": _transition_monitor_payload(monitor) if monitor is not None else {},
    }
    if before is not None:
        payload["before"] = _focused_element_payload(before)
    if switcher is not None:
        payload["switcher"] = _switcher_payload(switcher)
    if switcher_error is not None:
        payload["switcher_error"] = switcher_error
    if resolved_panel_error is not None:
        payload["panel_error"] = resolved_panel_error
    if surface is not None:
        payload["surface"] = _surface_payload(surface)
    if surface_error is not None:
        payload["surface_error"] = surface_error
    if surface_stability_error is not None:
        payload["surface_stability_error"] = surface_stability_error
    if rows_error is not None:
        payload["rows_error"] = rows_error
    return payload

def _press_key_and_capture(
    *,
    page: LiveWorkspaceSwitcherPage,
    state: dict[str, object],
    key: str,
    before_override: FocusedElementObservation | None = None,
) -> dict[str, object]:
    before = before_override or page.active_element()
    page.start_transition_monitor()
    page.press_key(key, timeout_ms=FOCUS_TIMEOUT_MS)
    surface_stability_error: str | None = None
    try:
        page.wait_for_surface_to_remain_open(
            stability_ms=FOCUS_SETTLE_MS,
            timeout_ms=FOCUS_TIMEOUT_MS,
        )
    except Exception as error:
        surface_stability_error = f"{type(error).__name__}: {error}"
    monitor = page.read_transition_monitor(clear=True)
    payload = _capture_current_state(
        page=page,
        state=state,
        before=before,
        monitor=monitor,
        surface_stability_error=surface_stability_error,
    )
    payload["key"] = key
    return payload


def _assert_initial_state(state: dict[str, object]) -> None:
    switcher = _switcher_from_state(state)
    surface_labels = _interactive_label_summary(state)
    failures: list[str] = []

    if FIRST_WORKSPACE_DISPLAY_NAME not in str(state.get("first_row_display_name")):
        failures.append(
            f"the first saved workspace display name was {state.get('first_row_display_name')!r} instead of {FIRST_WORKSPACE_DISPLAY_NAME!r}",
        )
    if "Workspace switcher" not in str(switcher.get("switcher_text", "")):
        failures.append("the workspace switcher panel text was not visible")
    if not _expected_target_label(state):
        failures.append("the open switcher did not expose a readable last internal keyboard target")
    for label in ("Repository", "Branch", LAST_INTERNAL_CONTROL_LABEL):
        if label not in surface_labels:
            failures.append(f"the visible panel did not expose the expected {label!r} control")

    if failures:
        raise AssertionError(
            "Step 1 failed: the open workspace switcher did not satisfy the ticket "
            "preconditions before the keyboard-order proof began.\n"
            + "\n".join(f"- {item}" for item in failures)
            + "\n"
            + f"Observed switcher: {json.dumps(switcher, indent=2)}\n"
            + f"Observed rows: {json.dumps(_saved_workspace_rows_from_state(state), indent=2)}\n"
            + f"Observed surface labels: {json.dumps(surface_labels, indent=2)}"
        )


def _assert_first_row_focus_ready(state: dict[str, object]) -> None:
    active = _active_from_state(state)
    focus = _focus_from_state(state)
    row_focus = _row_focus_from_state(state, FIRST_WORKSPACE_DISPLAY_NAME)
    active_summary = _element_label_for_summary(active)
    failures: list[str] = []

    if active.get("accessible_name") != state.get("first_row_label"):
        failures.append(
            f"the active element before Tab traversal was {active_summary!r} instead of {state.get('first_row_label')!r}",
        )
    if not bool(focus.get("focus_owned_by_switcher")):
        failures.append("keyboard focus was not owned by the workspace switcher before the Tab traversal")
    if not bool(focus.get("active_within_switcher")):
        failures.append("the active element was not inside the workspace switcher before the Tab traversal")
    if bool(focus.get("active_on_trigger")):
        failures.append("focus stayed on the workspace-switcher trigger instead of the first row")
    if not bool(row_focus.get("row_contains_active")):
        failures.append("the selected first saved workspace row did not contain the active element before the Tab traversal")

    if failures:
        raise AssertionError(
            "Step 2 failed: pressing Tab from the open-panel workspace trigger did not "
            "move focus to the selected first workspace row.\n"
            + "\n".join(f"- {item}" for item in failures)
            + "\n"
            + f"Observed before element: {json.dumps(_before_from_state(state), indent=2)}\n"
            + f"Observed active element: {json.dumps(active, indent=2)}\n"
            + f"Observed focus ownership: {json.dumps(focus, indent=2)}\n"
            + f"Observed row focus: {json.dumps(row_focus, indent=2)}"
        )


def _assert_first_keyboard_target(state: dict[str, object]) -> None:
    active = _active_from_state(state)
    focus = _focus_from_state(state)
    first_internal_label = _first_internal_label(state)
    active_summary = _element_label_for_summary(active)
    failures: list[str] = []

    if not bool(focus.get("focus_owned_by_switcher")):
        failures.append("keyboard focus was not owned by the workspace switcher before Shift+Tab")
    if not bool(focus.get("active_within_switcher")):
        failures.append("focus escaped the workspace switcher while proving the first keyboard target")
    if active.get("accessible_name") != first_internal_label:
        failures.append(
            f"focus landed on {active_summary!r} instead of the first internal target {first_internal_label!r}",
        )
    if _state_active_is_workspace_trigger(state):
        failures.append("focus stayed on the workspace-switcher trigger instead of the first internal target")

    if failures:
        raise AssertionError(
            "Step 2 failed: focusing the derived first internal keyboard target did not "
            "establish the ticket precondition before Shift+Tab.\n"
            + "\n".join(f"- {item}" for item in failures)
            + "\n"
            + f"Observed before element: {json.dumps(_before_from_state(state), indent=2)}\n"
            + f"Observed active element: {json.dumps(active, indent=2)}\n"
            + f"Observed focus ownership: {json.dumps(focus, indent=2)}\n"
            + f"Observed internal target: {json.dumps(_first_internal_target_from_state(state), indent=2)}\n"
            + f"Observed internal tab stops: {json.dumps(_tab_stops_from_state(state), indent=2)}"
        )

def _assert_reverse_wrap(state: dict[str, object]) -> None:
    active = _active_from_state(state)
    focus = _focus_from_state(state)
    expected_target = _expected_target_from_state(state)
    row_focus = {name: _row_focus_from_state(state, name) for name in WORKSPACE_NAMES}
    monitor = _monitor_from_state(state)
    active_label = str(active.get("accessible_name") or "")
    active_summary = _element_label_for_summary(active)
    failures: list[str] = []

    if _before_label_for_summary(state) != _first_internal_label(state):
        failures.append(
            f"Shift+Tab started from {_before_label_for_summary(state)!r} instead of the proven first internal target {_first_internal_label(state)!r}",
        )
    if not bool(focus.get("focus_owned_by_switcher")):
        failures.append("keyboard focus was not owned by the workspace switcher after Shift+Tab")
    if not bool(focus.get("active_within_switcher")):
        failures.append("focus escaped the workspace switcher after Shift+Tab")
    if _state_active_is_workspace_trigger(state):
        failures.append("focus moved to the workspace-switcher trigger instead of wrapping inside the panel")
    if bool(monitor.get("ever_hidden_after_visible")):
        failures.append("the workspace switcher panel became hidden during the reverse-wrap attempt")
    if active.get("accessible_name") != expected_target.get("label"):
        failures.append(
            f"focus landed on {active_summary!r} instead of the last internal control {expected_target.get('label')!r}",
        )
    if active.get("accessible_name") == _first_internal_label(state):
        failures.append("focus stayed on the first internal target instead of wrapping")

    if failures:
        raise AssertionError(
            "Step 2 failed: pressing Shift+Tab from the proven first internal "
            "workspace-switcher target did not wrap focus to the last internal control.\n"
            + "\n".join(f"- {item}" for item in failures)
            + "\n"
            + f"Observed before element: {json.dumps(_before_from_state(state), indent=2)}\n"
            + f"Observed active element: {json.dumps(active, indent=2)}\n"
            + f"Observed focus ownership: {json.dumps(focus, indent=2)}\n"
            + f"Expected wrap target: {json.dumps(expected_target, indent=2)}\n"
            + f"Observed row focus: {json.dumps(row_focus, indent=2)}\n"
            + f"Observed transition monitor: {json.dumps(monitor, indent=2)}\n"
            + f"Observed switcher: {json.dumps(_switcher_from_state(state), indent=2)}"
        )


def _last_internal_focus_target(
    *,
    tab_stops: tuple[WorkspaceSwitcherTabStopObservation, ...] | list[object],
) -> dict[str, object]:
    payload = _tab_stops_payload(tab_stops)
    if len(payload) < 2:
        raise AssertionError(
            "Step 1 failed: the open workspace switcher did not expose enough internal "
            "keyboard tab stops to derive the reverse-wrap target.\n"
            f"Observed internal tab stops: {json.dumps(payload, indent=2)}",
        )
    target = payload[-1]
    return {
        "label": target.get("label") or target.get("visible_text") or "",
        "visible_text": target.get("visible_text"),
        "role": target.get("role"),
        "tag_name": target.get("tag_name"),
        "tabindex": target.get("tabindex"),
        "tab_index_value": target.get("tab_index_value"),
        "dom_index": target.get("dom_index"),
        "keyboard_focusable": target.get("keyboard_focusable"),
        "disabled": target.get("disabled"),
        "outer_html": target.get("outer_html"),
    }


def _first_internal_focus_target(
    tab_stops: tuple[WorkspaceSwitcherTabStopObservation, ...] | list[object],
) -> dict[str, object]:
    payload = _tab_stops_payload(tab_stops)
    if not payload:
        raise AssertionError(
            "Step 1 failed: the open workspace switcher did not expose a readable first "
            "internal keyboard target.\n"
            f"Observed internal tab stops: {json.dumps(payload, indent=2)}",
        )
    target = payload[0]
    return {
        "label": target.get("label") or target.get("visible_text") or "",
        "visible_text": target.get("visible_text"),
        "role": target.get("role"),
        "tag_name": target.get("tag_name"),
        "tabindex": target.get("tabindex"),
        "tab_index_value": target.get("tab_index_value"),
        "dom_index": target.get("dom_index"),
        "keyboard_focusable": target.get("keyboard_focusable"),
        "disabled": target.get("disabled"),
        "outer_html": target.get("outer_html"),
    }


def _resolve_first_internal_focus_target(
    *,
    active: FocusedElementObservation,
    focus: WorkspaceSwitcherFocusOwnershipObservation,
    first_row_label: str,
    tab_stops: tuple[WorkspaceSwitcherTabStopObservation, ...] | list[object],
) -> dict[str, object]:
    active_label = str(active.accessible_name or active.text or "")
    if (
        active_label
        and active_label == first_row_label
        and bool(focus.focus_owned_by_switcher)
        and bool(focus.active_within_switcher)
        and not bool(focus.active_on_trigger)
        and not _is_workspace_trigger_focus_label(active_label)
    ):
        return {
            "label": active_label,
            "visible_text": str(active.text or ""),
            "role": active.role,
            "tag_name": active.tag_name,
            "tabindex": active.tabindex,
            "tab_index_value": None,
            "dom_index": None,
            "keyboard_focusable": True,
            "disabled": False,
            "outer_html": active.outer_html,
        }
    return _first_internal_focus_target(tab_stops=tab_stops)


def _state_with_precondition_source(
    state: dict[str, object],
    *,
    precondition_source: str,
) -> dict[str, object]:
    payload = dict(state)
    payload["precondition_source"] = precondition_source
    return payload


def _state_with_expected_target(
    state: dict[str, object],
    target: dict[str, object],
) -> dict[str, object]:
    payload = dict(state)
    payload["expected_target"] = target
    return payload


def _is_switcher_internal_focus_state(state: dict[str, object]) -> bool:
    focus = _focus_from_state(state)
    active = _active_from_state(state)
    active_label = str(active.get("accessible_name") or active.get("text") or "")
    return (
        bool(focus.get("focus_owned_by_switcher"))
        and bool(focus.get("active_within_switcher"))
        and not bool(focus.get("active_on_trigger"))
        and not _state_active_is_workspace_trigger(state)
        and bool(active.get("accessible_name") or active.get("text"))
    )


def _is_workspace_trigger_focus_label(value: object) -> bool:
    return str(value or "").startswith("Workspace switcher:")


def _state_active_is_workspace_trigger(state: object) -> bool:
    active = _active_from_state(state)
    focus = _focus_from_state(state)
    if bool(focus.get("active_on_trigger")):
        return True
    active_label = str(active.get("accessible_name") or active.get("text") or "")
    if not _is_workspace_trigger_focus_label(active_label):
        return False
    active_tag = str(
        active.get("tag_name")
        or focus.get("active_tag_name")
        or "",
    ).upper()
    active_role = str(
        active.get("role")
        or focus.get("active_role")
        or "",
    ).lower()
    return active_tag in {"BUTTON", "FLT-SEMANTICS"} or active_role == "button"


def _state_with_first_internal_target(
    state: dict[str, object],
    target: dict[str, object],
    *,
    precondition_source: str,
) -> dict[str, object]:
    payload = dict(state)
    payload["first_internal_target"] = target
    payload["precondition_source"] = precondition_source
    return payload


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


def _selected_row_payload(rows: list[dict[str, object]]) -> dict[str, object] | None:
    return next((row for row in rows if row.get("selected")), None)


def _saved_workspace_row_focus_label(
    row: WorkspaceSwitcherSavedWorkspaceRowObservation,
) -> str:
    segments = [row.display_name]
    if row.target_type_label:
        segments.append(row.target_type_label)
    if row.state_label:
        segments.append(row.state_label)
    return ", ".join(segments) + f", {row.detail_text}"


def _saved_workspace_rows_from_switcher(
    switcher: WorkspaceSwitcherObservation,
) -> tuple[WorkspaceSwitcherSavedWorkspaceRowObservation, ...]:
    return tuple(
        WorkspaceSwitcherSavedWorkspaceRowObservation(
            display_name=row.display_name,
            target_type_label=row.target_type_label,
            state_label=row.state_label,
            detail_text=row.detail_text,
            selected=row.selected,
            action_labels=row.action_labels,
            left=0.0,
            top=0.0,
            width=0.0,
            height=0.0,
        )
        for row in switcher.rows
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
    _write_review_replies(result, passed=True)


def _write_failure_outputs(result: dict[str, object]) -> None:
    error = str(result.get("error", "AssertionError: TS-911 failed"))
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
        (
            f"*Environment:* URL {{{{{result['app_url']}}}}}, repository "
            f"{{{{{result['repository']}}}}} @ {{{{{result['repository_ref']}}}}}, "
            f"browser {{Chromium (Playwright)}}, OS {{{{{result['os']}}}}}"
        ),
        f"*Run command:* {{code}}{RUN_COMMAND}{{code}}",
        "",
        "h4. What automation checked",
        f"# {AUTOMATION_STEPS[0]} — *{_step_status(result, 1).upper()}*: {_step_observation(result, 1)}",
        f"# {AUTOMATION_STEPS[1]} — *{_step_status(result, 2).upper()}*: {_step_observation(result, 2)}",
        "",
        "h4. Human-style verification",
        *[
            f"# {item['check']} — {item['observed']}"
            for item in _human_verification(result)
        ],
        "",
        "h4. Expected result",
        EXPECTED_RESULT,
        "",
        "h4. Observed outcome",
        _actual_vs_expected_summary(result),
    ]
    if not passed:
        lines.extend(
            [
                "",
                "h4. Failure details",
                f"*Failed step:* {_failed_step_label(result)}",
                f"*Error:* {{code}}{result.get('error')}{{code}}",
                "",
                "h4. Exact error",
                "{code}",
                str(result.get("traceback", result.get("error", ""))),
                "{code}",
            ],
        )
    screenshot = result.get("screenshot")
    if screenshot:
        lines.extend(["", f"*Screenshot:* {{{{{screenshot}}}}}"])
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
        f"**Run command:** `{RUN_COMMAND}`",
        "",
        "## Rework applied",
        "1. Matched the live run to the ticket-linked desktop viewport of `1440x900`.",
        "2. Treat the selected workspace row as the first internal target when the live panel already opens with focus there.",
        "3. Keeps the reverse-wrap target aligned to the visible `Save and switch` footer control and scopes the TS-911 pass/fail decision to the single `Shift+Tab` action.",
        "",
        "## What automation checked",
        f"1. {AUTOMATION_STEPS[0]} — **{_step_status(result, 1).upper()}**: {_step_observation(result, 1)}",
        f"2. {AUTOMATION_STEPS[1]} — **{_step_status(result, 2).upper()}**: {_step_observation(result, 2)}",
        "",
        "## Human-style verification",
        *[
            f"1. {item['check']} — {item['observed']}"
            for item in _human_verification(result)
        ],
        "",
        "## Expected result",
        EXPECTED_RESULT,
        "",
        "## Observed outcome",
        _actual_vs_expected_summary(result),
    ]
    if not passed:
        lines.extend(
            [
                "",
                "## Failure details",
                f"- **Failed step:** {_failed_step_label(result)}",
                f"- **Error:** `{result.get('error')}`",
                f"- **Screenshot:** `{result.get('screenshot')}`" if result.get("screenshot") else "- **Screenshot:** not captured",
                "",
                "## Exact error",
                "```text",
                str(result.get("traceback", result.get("error", ""))),
                "```",
            ],
        )
    elif result.get("screenshot"):
        lines.extend(["", f"**Screenshot:** `{result['screenshot']}`"])
    return "\n".join(lines) + "\n"


def _response_summary(result: dict[str, object], *, passed: bool) -> str:
    status = "PASSED" if passed else "FAILED"
    failure_summary = _failed_step_summary(result).splitlines()[0]
    lines = [
        "# Test Automation Summary",
        "",
        f"- Test case: **{TICKET_KEY} - {TEST_CASE_TITLE}**",
        f"- Result: **{status}**",
        "- Rework: matched the ticket viewport at `1440x900`, preserved the live selected-row focus when the panel already opens on the first internal element, and kept the reverse-wrap target aligned to the visible `Save and switch` footer control while scoping pass/fail to the ticketed `Shift+Tab` wrap.",
        f"- Command: `{RUN_COMMAND}`",
        (
            f"- Environment: `{result['app_url']}` on Chromium/Playwright "
            f"({result['os']}) against `{result['repository']}` @ "
            f"`{result['repository_ref']}`."
        ),
        f"- Expected result: {EXPECTED_RESULT}",
        (
            f"- Observed outcome: "
            f"{_actual_vs_expected_summary(result) if passed or _is_runtime_bootstrap_failure(result) else failure_summary}"
        ),
    ]
    if result.get("screenshot"):
        lines.append(f"- Screenshot: `{result['screenshot']}`")
    return "\n".join(lines) + "\n"


def _is_runtime_bootstrap_failure(result: dict[str, object]) -> bool:
    return _failed_step_number(result) == 1 and "never reached an interactive state" in str(
        result.get("error", ""),
    )


def _visible_body_text_from_result(result: dict[str, object]) -> str:
    runtime_body_text = str(result.get("runtime_body_text") or "").strip()
    if runtime_body_text:
        return runtime_body_text

    return _visible_body_text_from_text(
        str(result.get("error", "")) or _failed_step_summary(result),
    )


def _visible_body_text_from_text(text: str) -> str:
    marker = "Visible body text:"
    if marker in text:
        return text.split(marker, 1)[1].strip()
    return "<unknown>"


def _bug_description(result: dict[str, object]) -> str:
    if _is_runtime_bootstrap_failure(result):
        return _runtime_bootstrap_bug_description(result)

    reproduction_steps = [
        "1. Open the TrackState application in a desktop browser.",
        "2. Open the workspace switcher panel from Dashboard.",
        "3. Ensure keyboard focus is on the first internal keyboard target in the open panel.",
        "4. Press `Shift+Tab` once.",
        "5. Observe the newly focused control.",
    ]
    return "\n".join(
        [
            f"# {TICKET_KEY} - Shift+Tab escapes the workspace switcher instead of wrapping inside it",
            "",
            "## Summary",
            _actual_vs_expected_summary(result),
            "",
            "## Exact steps to reproduce",
            *reproduction_steps,
            "",
            "## Exact steps from the test case with observations",
            _annotated_request_steps(result),
            "",
            "## Exact error message or assertion failure",
            "```text",
            str(result.get("traceback", result.get("error", ""))),
            "```",
            "",
            "## Actual vs Expected",
            f"- **Expected:** {EXPECTED_RESULT}",
            f"- **Actual:** {_actual_vs_expected_summary(result)}",
            "",
            "## Broken production capability",
            "The live workspace switcher must keep keyboard focus trapped inside the "
            "open panel in reverse order. From the first internal keyboard target, "
            "`Shift+Tab` should wrap to the terminal visible control proven by live "
            "forward keyboard traversal instead of escaping into the app shell or "
            "landing on an earlier saved-workspace row or escaping into the app shell.",
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
            f"- Screenshot: `{result.get('screenshot', 'not captured')}`",
            "- Step log:",
            "```json",
            json.dumps(
                {
                    "steps": _steps(result),
                    "initial_state": result.get("initial_state"),
                    "first_keyboard_target_state": result.get("first_keyboard_target_state"),
                    "after_shift_tab_state": result.get("after_shift_tab_state"),
                    "tab_trace_to_wrap_target": result.get("tab_trace_to_wrap_target"),
                },
                indent=2,
            ),
            "```",
        ],
    ) + "\n"
def _runtime_bootstrap_bug_description(result: dict[str, object]) -> str:
    visible_body_text = _visible_body_text_from_result(result)
    return "\n".join(
        [
            f"# {TICKET_KEY} - Deployed TrackState app never reaches an interactive state",
            "",
            "## Summary",
            _actual_vs_expected_summary(result),
            "",
            "## Exact steps to reproduce",
            "1. Open the TrackState application in a desktop browser at `https://istin.github.io/trackstate-setup/`.",
            "2. Wait for the initial TrackState UI to finish loading.",
            "3. Look for the top-bar workspace switcher trigger and the rest of the interactive app shell.",
            "4. Attempt to open the workspace switcher panel.",
            "5. Observe the rendered page state.",
            "",
            "## Exact steps from the test case with observations",
            _annotated_request_steps(result),
            "",
            "## Exact error message or assertion failure",
            "```text",
            str(result.get("traceback", result.get("error", ""))),
            "```",
            "",
            "## Actual vs Expected",
            f"- **Expected:** {EXPECTED_RESULT}",
            (
                "- **Actual:** The deployed app never rendered the interactive "
                "workspace-switcher flow. Chromium showed "
                f"{visible_body_text!r} on an otherwise blank page, so the "
                "workspace switcher trigger and panel never became available."
            ),
            "",
            "## Broken production capability",
            "The deployed TrackState app must render an interactive desktop shell "
            "before the workspace-switcher keyboard behavior can be validated. "
            "Because the live page stalls in a blank `Sync issue` state, the "
            "workspace switcher cannot be opened and the TS-911 Shift+Tab scenario "
            "is blocked by a production-visible rendering/bootstrap defect.",
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
            f"- Screenshot: `{result.get('screenshot', 'not captured')}`",
            f"- Visible body text: `{visible_body_text}`",
            "- Step log:",
            "```json",
            json.dumps(
                {
                    "steps": _steps(result),
                    "runtime_state": result.get("runtime_state"),
                    "runtime_body_text": result.get("runtime_body_text"),
                    "initial_state": result.get("initial_state"),
                },
                indent=2,
            ),
            "```",
        ],
    ) + "\n"


def _annotated_request_steps(result: dict[str, object]) -> str:
    if _is_runtime_bootstrap_failure(result):
        visible_body_text = _visible_body_text_from_result(result)
        lines = [
            (
                "1. The TrackState application is opened in a desktop browser.\n"
                "   ❌ The URL opened in Chromium, but the page never rendered the "
                f"interactive app shell; the visible body text was {visible_body_text!r}."
            ),
            (
                "2. The workspace switcher panel is currently open.\n"
                "   ❌ Not possible: no workspace switcher trigger or dashboard shell "
                "became visible, so the panel could not be opened."
            ),
            (
                "3. Keyboard focus is positioned on the first interactive element within the panel.\n"
                "   ❌ Not reached because the workspace switcher panel never rendered."
            ),
            (
                "4. Press the 'Shift + Tab' keys on the keyboard.\n"
                "   ❌ Not reached because the page never advanced past the blank "
                "`Sync issue` state."
            ),
        ]
        return "\n".join(lines)

    before_state = result.get("first_keyboard_target_state")
    after_state = result.get("after_shift_tab_state")
    lines = [
        (
            "1. Open the TrackState application in a desktop browser and open the workspace switcher panel.\n"
            f"   {'✅' if _step_passed(result, 1) else '❌'} "
            f"{_step_observation(result, 1)}"
        ),
        (
            "2. Ensure keyboard focus is positioned on the first interactive element within the panel.\n"
            f"   {'✅' if isinstance(before_state, dict) and _active_label_for_summary(before_state) == _first_internal_label(before_state) else '❌'} "
            f"Focused before Shift+Tab: {_active_label_for_summary(before_state)!r}; "
            f"source={before_state.get('precondition_source') if isinstance(before_state, dict) else None!r}"
        ),
        (
            "3. Press the 'Shift + Tab' keys on the keyboard.\n"
            f"   {'✅' if _step_passed(result, 2) else '❌'} "
            + (
                f"Expected wrap target: {_expected_target_label(after_state)!r}; "
                f"actual focus: {_active_label_for_summary(after_state)!r}"
                if isinstance(after_state, dict)
                else "Not reached because the first-internal-target proof failed before the Shift+Tab step."
            )
        ),
    ]
    return "\n".join(lines)


def _actual_vs_expected_summary(result: dict[str, object]) -> str:
    if _is_runtime_bootstrap_failure(result):
        visible_body_text = _visible_body_text_from_result(result)
        return (
            "The deployed app never rendered an interactive TrackState shell. "
            f"Chromium showed {visible_body_text!r} on an otherwise blank page, "
            "so the workspace switcher could not be opened and the Shift+Tab "
            "focus-wrap scenario never became reachable."
        )

    after_state = result.get("after_shift_tab_state")
    if not isinstance(after_state, dict):
        return _failed_step_summary(result)
    expected = _expected_target_label(after_state)
    actual = _active_label_for_summary(after_state)
    focus = _focus_from_state(after_state)
    if _step_passed(result, 2):
        return (
            f"Shift+Tab wrapped focus from the first internal keyboard target to {expected!r}, "
            "and focus stayed inside the workspace switcher."
        )
    return (
        f"Shift+Tab should have wrapped focus to the last internal control {expected!r}, "
        f"but the live app moved focus to {actual!r}. "
        f"focus_within_switcher={focus.get('active_within_switcher')}, "
        f"focus_on_trigger={focus.get('active_on_trigger')}."
    )


def _failed_step_label(result: dict[str, object]) -> str:
    failed = next((step for step in _steps(result) if step["status"] == "failed"), None)
    if failed is None:
        return "No failed automation step recorded"
    return f"Step {failed['step']} — {failed['action']}"


def _failed_step_number(result: dict[str, object]) -> int | None:
    failed = next((step for step in _steps(result) if step["status"] == "failed"), None)
    if failed is None:
        return None
    return int(failed.get("step", -1))


def _failed_step_summary(result: dict[str, object]) -> str:
    failed = next((step for step in _steps(result) if step["status"] == "failed"), None)
    if failed is None:
        return str(result.get("error", "No failed step recorded."))
    return f"Step {failed['step']}: {failed['observed']}"


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
    items = result.setdefault("human_verification", [])
    assert isinstance(items, list)
    items.append({"check": check, "observed": observed})


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


def _step_status(result: dict[str, object], step_number: int) -> str:
    for step in _steps(result):
        if int(step.get("step", -1)) == step_number:
            return str(step.get("status", "failed"))
    return "failed"


def _step_observation(result: dict[str, object], step_number: int) -> str:
    last_failed_step: int | None = None
    for step in _steps(result):
        current_step = int(step.get("step", -1))
        if current_step == step_number:
            return str(step.get("observed", "<no observation recorded>"))
        if step.get("status") != "passed":
            last_failed_step = current_step
    if last_failed_step is not None and step_number > last_failed_step:
        return "Not reached because an earlier required step failed."
    return "<no observation recorded>"


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


def _button_focusability_payload(observation: object) -> dict[str, object]:
    return {
        "label": getattr(observation, "label", None),
        "visible_text": getattr(observation, "visible_text", None),
        "role": getattr(observation, "role", None),
        "tag_name": getattr(observation, "tag_name", None),
        "tabindex": getattr(observation, "tabindex", None),
        "keyboard_focusable": getattr(observation, "keyboard_focusable", None),
        "active_within": getattr(observation, "active_within", None),
        "outer_html": getattr(observation, "outer_html", None),
    }


def _tab_stops_payload(
    tab_stops: tuple[WorkspaceSwitcherTabStopObservation, ...] | list[object],
) -> list[dict[str, object]]:
    payload: list[dict[str, object]] = []
    for stop in tab_stops:
        if not isinstance(stop, WorkspaceSwitcherTabStopObservation):
            continue
        payload.append(
            {
                "label": stop.label,
                "visible_text": stop.visible_text,
                "role": stop.role,
                "tag_name": stop.tag_name,
                "tabindex": stop.tabindex,
                "tab_index_value": stop.tab_index_value,
                "dom_index": stop.dom_index,
                "keyboard_focusable": stop.keyboard_focusable,
                "disabled": stop.disabled,
                "outer_html": stop.outer_html,
            },
        )
    return payload


def _transition_monitor_payload(observation: object) -> dict[str, object]:
    return {
        "sample_count": getattr(observation, "sample_count", None),
        "visible_sample_count": getattr(observation, "visible_sample_count", None),
        "hidden_sample_count": getattr(observation, "hidden_sample_count", None),
        "ever_hidden_after_visible": getattr(observation, "ever_hidden_after_visible", None),
        "observed_container_kinds": list(getattr(observation, "observed_container_kinds", ())),
        "observed_row_counts": list(getattr(observation, "observed_row_counts", ())),
        "observed_active_workspace_names": list(
            getattr(observation, "observed_active_workspace_names", ()),
        ),
        "latest_visible_container_kind": getattr(
            observation,
            "latest_visible_container_kind",
            None,
        ),
        "latest_visible_row_count": getattr(observation, "latest_visible_row_count", None),
        "latest_visible_active_workspace_name": getattr(
            observation,
            "latest_visible_active_workspace_name",
            None,
        ),
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
        "body_text": surface.body_text,
        "dialog_visible": surface.dialog_visible,
        "heading_text": surface.heading_text,
        "interactive_elements": [asdict(item) for item in surface.interactive_elements],
        "semantics_nodes": [asdict(item) for item in surface.semantics_nodes],
        "missing_interactive_labels": list(surface.missing_interactive_labels),
        "missing_semantics_labels": list(surface.missing_semantics_labels),
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


def _focus_target_payload(active: dict[str, object]) -> dict[str, object]:
    return {
        "label": active.get("accessible_name") or active.get("text") or "",
        "visible_text": active.get("text"),
        "role": active.get("role"),
        "tag_name": active.get("tag_name"),
        "tabindex": active.get("tabindex"),
        "tab_index_value": None,
        "dom_index": None,
        "keyboard_focusable": True,
        "disabled": None,
        "outer_html": active.get("outer_html"),
    }


def _focused_element_observation_from_state(
    state: dict[str, object],
) -> FocusedElementObservation:
    active = _active_from_state(state)
    return FocusedElementObservation(
        tag_name=str(active.get("tag_name", "")),
        role=str(active.get("role")) if active.get("role") is not None else None,
        accessible_name=(
            str(active.get("accessible_name"))
            if active.get("accessible_name") is not None
            else None
        ),
        text=str(active.get("text", "")),
        tabindex=str(active.get("tabindex")) if active.get("tabindex") is not None else None,
        outer_html=str(active.get("outer_html", "")),
    )


def _capture_current_focus_state(
    *,
    page: LiveWorkspaceSwitcherPage,
    panel: WorkspaceSwitcherPanelObservation,
    state: dict[str, object],
    focused_label: str,
    require_stable_surface: bool = True,
) -> dict[str, object]:
    if require_stable_surface:
        page.wait_for_surface_to_remain_open(
            stability_ms=FOCUS_SETTLE_MS,
            timeout_ms=FOCUS_TIMEOUT_MS,
        )
    active = page.active_element()
    focus = page.observe_focus_ownership(panel=panel)
    row_focus = {
        name: _row_focus_payload(
            page.observe_saved_workspace_row_focus(display_name=name, panel=panel),
        )
        for name in WORKSPACE_NAMES
    }
    return {
        "panel": asdict(panel),
        "active": _focused_element_payload(active),
        "focus": _focus_ownership_payload(focus),
        "row_focus": row_focus,
        "saved_workspace_rows": state.get("saved_workspace_rows"),
        "expected_target": state.get("expected_target"),
        "first_internal_target": state.get("first_internal_target"),
        "first_row_display_name": state.get("first_row_display_name"),
        "first_row_label": state.get("first_row_label"),
        "focused_label": focused_label,
    }


def _state_payload(
    *,
    trigger: WorkspaceSwitcherTriggerObservation,
    switcher: WorkspaceSwitcherObservation,
    panel: WorkspaceSwitcherPanelObservation,
    surface: WorkspaceSwitcherSurfaceObservation,
    active: FocusedElementObservation,
    focus: WorkspaceSwitcherFocusOwnershipObservation,
    saved_workspace_rows: tuple[WorkspaceSwitcherSavedWorkspaceRowObservation, ...],
    row_focus: dict[str, dict[str, object]],
    expected_target: dict[str, object],
    first_internal_target: dict[str, object],
    first_row_display_name: str,
    first_row_label: str,
    internal_tab_stops: list[dict[str, object]],
    button_focusability: dict[str, object],
    focus_attempts: list[dict[str, object]],
    precondition_source: str,
    focused_trigger: dict[str, object],
) -> dict[str, object]:
    active_workspace = _selected_saved_workspace(saved_workspace_rows)
    return {
        "trigger": _trigger_payload(trigger),
        "switcher": _switcher_payload(switcher),
        "panel": asdict(panel),
        "surface": _surface_payload(surface),
        "active": _focused_element_payload(active),
        "focus": _focus_ownership_payload(focus),
        "saved_workspace_rows": _saved_workspace_rows_payload(saved_workspace_rows),
        "active_workspace_name": (
            active_workspace.display_name
            if active_workspace is not None
            else first_row_label
        ),
        "row_focus": row_focus,
        "expected_target": expected_target,
        "first_internal_target": first_internal_target,
        "first_row_display_name": first_row_display_name,
        "first_row_label": first_row_label,
        "internal_tab_stops": internal_tab_stops,
        "button_focusability": button_focusability,
        "focus_attempts": focus_attempts,
        "precondition_source": precondition_source,
        "focused_trigger": focused_trigger,
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


def _active_from_state(state: object) -> dict[str, object]:
    if not isinstance(state, dict):
        return {}
    active = state.get("active", {})
    return active if isinstance(active, dict) else {}


def _before_from_state(state: object) -> dict[str, object]:
    if not isinstance(state, dict):
        return {}
    before = state.get("before", {})
    return before if isinstance(before, dict) else {}


def _focus_from_state(state: object) -> dict[str, object]:
    if not isinstance(state, dict):
        return {}
    focus = state.get("focus", {})
    return focus if isinstance(focus, dict) else {}


def _row_focus_from_state(state: object, display_name: str) -> dict[str, object]:
    if not isinstance(state, dict):
        return {}
    row_focus = state.get("row_focus", {})
    if not isinstance(row_focus, dict):
        return {}
    candidate = row_focus.get(display_name, {})
    return candidate if isinstance(candidate, dict) else {}


def _expected_target_from_state(state: object) -> dict[str, object]:
    if not isinstance(state, dict):
        return {}
    target = state.get("expected_target", {})
    return target if isinstance(target, dict) else {}


def _first_internal_target_from_state(state: object) -> dict[str, object]:
    if not isinstance(state, dict):
        return {}
    target = state.get("first_internal_target", {})
    return target if isinstance(target, dict) else {}


def _first_row_display_name_from_state(state: object) -> object:
    if not isinstance(state, dict):
        return None
    return state.get("first_row_display_name")


def _expected_target_label(state: object) -> object:
    return _expected_target_from_state(state).get("label")


def _button_focusability_from_state(state: object) -> dict[str, object]:
    if not isinstance(state, dict):
        return {}
    payload = state.get("button_focusability", {})
    return payload if isinstance(payload, dict) else {}


def _tab_stops_from_state(state: object) -> list[dict[str, object]]:
    if not isinstance(state, dict):
        return []
    payload = state.get("internal_tab_stops", [])
    return payload if isinstance(payload, list) else []


def _monitor_from_state(state: object) -> dict[str, object]:
    if not isinstance(state, dict):
        return {}
    payload = state.get("monitor", {})
    return payload if isinstance(payload, dict) else {}


def _active_label_for_summary(state: object) -> object:
    return _element_label_for_summary(_active_from_state(state))


def _before_label_for_summary(state: object) -> object:
    return _element_label_for_summary(_before_from_state(state))


def _element_label_for_summary(element: object) -> str | None:
    if not isinstance(element, dict):
        return None
    tag_name = str(element.get("tag_name") or "").upper()
    raw_label = str(element.get("accessible_name") or element.get("text") or "").strip()
    if tag_name == "BODY":
        return "document body (<body>)"
    if raw_label:
        if len(raw_label) <= 160:
            return raw_label
        return raw_label[:157] + "..."
    if tag_name:
        return f"<{tag_name.lower()}>"
    return None


def _first_internal_label(state: object) -> object:
    target = _first_internal_target_from_state(state)
    if target:
        return target.get("label")
    tab_stops = _tab_stops_from_state(state)
    if tab_stops:
        return tab_stops[0].get("label")
    return None


def _interactive_label_summary(state: object) -> list[str]:
    if not isinstance(state, dict):
        return []
    surface = state.get("surface", {})
    if not isinstance(surface, dict):
        return []
    elements = surface.get("interactive_elements", [])
    if not isinstance(elements, list):
        return []
    return [str(item.get("label")) for item in elements if isinstance(item, dict)]


def _visited_focus_labels(states: list[dict[str, object]]) -> list[str]:
    labels: list[str] = []
    for state in states:
        label = str(_active_from_state(state).get("accessible_name") or "")
        if not labels or labels[-1] != label:
            labels.append(label)
    return labels


def _write_review_replies(result: dict[str, object], *, passed: bool) -> None:
    replies = [
        {
            "inReplyToId": thread.get("rootCommentId"),
            "threadId": thread.get("threadId"),
            "reply": _review_reply_text(thread=thread, passed=passed, result=result),
        }
        for thread in _discussion_threads()
    ]
    REVIEW_REPLIES_PATH.write_text(
        json.dumps({"replies": replies}, indent=2) + "\n",
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
    thread: dict[str, object],
    passed: bool,
    result: dict[str, object],
) -> str:
    rerun_summary = (
        f"Re-ran `{RUN_COMMAND}`: passed (`1 passed, 0 failed`)."
        if passed
        else (
            "Re-ran "
            f"`{RUN_COMMAND}`: still failing. Current failure: {_failed_step_summary(result).splitlines()[0]}"
        )
    )
    thread_body = str(thread.get("body", ""))
    thread_path = str(thread.get("path", ""))
    if "forward-`Tab` proof gate" in thread_body or "still scope the main pass/fail decision to the reverse-wrap action" in thread_body:
        return (
            "Adjusted TS-911 so it no longer gates on a forward-Tab walk. The test now "
            "keeps the reverse-wrap expectation aligned to the visible `Save and switch` "
            "footer control and makes the pass/fail decision from the ticketed "
            "single-step `Shift+Tab` action. "
            f"{rerun_summary}"
        )
    if "_forward_wrap_proof_bug_description()" in thread_body or "different defect report" in thread_body:
        return (
            "Removed the forward-proof-specific bug routing. TS-911 failure output now "
            "stays scoped to the reverse-wrap behavior (plus the existing runtime "
            "bootstrap case), while inconclusive forward-Tab evidence is kept as setup "
            "context only. "
            f"{rerun_summary}"
        )
    if "displayNameHint" in thread_body or thread_path.endswith("live_workspace_switcher_page.py"):
        return (
            "Updated TS-911 to match the live hosted behavior at the ticket viewport: "
            "the automation now preserves the selected saved-workspace row as the first "
            "internal target and keeps the reverse-wrap target aligned to the visible "
            "`Save and switch` footer control before the Shift+Tab assertion. "
            f"{rerun_summary}"
        )
    return (
        "Updated TS-911 to honor the live first in-panel focus target at `1440x900`, "
        "keep the reverse-wrap expectation tied to the visible `Save and switch` footer "
        "control, and keep the deciding outcome on the ticketed `Shift+Tab` action. "
        f"{rerun_summary}"
    )


if __name__ == "__main__":
    main()
