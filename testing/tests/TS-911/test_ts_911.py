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

TICKET_KEY = "TS-911"
TEST_CASE_TITLE = (
    "Press Shift+Tab from the first element in workspace switcher — "
    "focus wraps to the last internal element"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-911/test_ts_911.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 960}
FOCUS_TIMEOUT_MS = 4_000
DEFAULT_BRANCH = "main"
FIRST_WORKSPACE_DISPLAY_NAME = "Hosted main workspace"
SECOND_WORKSPACE_DISPLAY_NAME = "Hosted alt workspace"
THIRD_WORKSPACE_DISPLAY_NAME = "Hosted third workspace"
SECOND_WORKSPACE_WRITE_BRANCH = "ts-867-alt"
THIRD_WORKSPACE_WRITE_BRANCH = "ts-867-third"
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
        "Open the deployed desktop workspace switcher, confirm the first saved workspace "
        "row owns keyboard focus, and identify the last visible internal control that "
        "Shift+Tab should wrap to."
    ),
    (
        "Press Shift+Tab from the first internal workspace row and verify keyboard focus "
        "wraps to the last internal control instead of escaping to the trigger or top-bar."
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
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts911_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts911_failure.png"

WORKSPACE_NAMES = (
    FIRST_WORKSPACE_DISPLAY_NAME,
    SECOND_WORKSPACE_DISPLAY_NAME,
    THIRD_WORKSPACE_DISPLAY_NAME,
)


def main() -> None:
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
                runtime = tracker_page.open()
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
                        f"active_row={_active_workspace_name_from_state(initial_state)!r}; "
                        f"focused_before_shift_tab={_active_label_for_summary(initial_state)!r}; "
                        f"expected_wrap_target={_expected_target_label(initial_state)!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Viewed the open desktop workspace switcher and confirmed the first "
                        "saved workspace row had keyboard focus before pressing Shift+Tab."
                    ),
                    observed=(
                        f"focused_before_shift_tab={_active_label_for_summary(initial_state)!r}; "
                        f"expected_wrap_target={_expected_target_label(initial_state)!r}; "
                        f"interactive_labels={_interactive_label_summary(initial_state)!r}"
                    ),
                )

                current_step = 2
                current_action = AUTOMATION_STEPS[1]
                after_shift_tab_state = _press_shift_tab_and_capture(page=page, state=initial_state)
                result["after_shift_tab_state"] = after_shift_tab_state
                _record_human_verification(
                    result,
                    check=(
                        "Pressed Shift+Tab exactly once from the first workspace row and "
                        "watched which visible control actually received focus."
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
                        f"Shift+Tab wrapped focus from "
                        f"{_first_internal_label(after_shift_tab_state)!r} "
                        f"to {_active_label_for_summary(after_shift_tab_state)!r} "
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
    switcher = page.open_and_observe()
    panel = page.observe_open_panel(expected_container_kinds=("anchored-panel", "surface"))
    surface = page.observe_surface(timeout_ms=FOCUS_TIMEOUT_MS)
    rows = page.observe_saved_workspace_rows(timeout_ms=FOCUS_TIMEOUT_MS)
    first_row = _selected_saved_workspace(rows)
    if first_row is None:
        raise AssertionError(
            "Step 1 failed: the open workspace switcher did not expose a selected first "
            "saved workspace row.\n"
            f"Observed rows: {json.dumps(_saved_workspace_rows_payload(rows), indent=2)}",
        )
    first_row_label = _saved_workspace_row_focus_label(first_row)
    expected_target = _expected_last_internal_focus_target(
        surface=surface,
        first_row_label=first_row_label,
    )
    focus_attempts = _ensure_first_internal_focus(
        page=page,
        panel=panel,
        first_row=first_row,
        first_row_label=first_row_label,
    )
    active = page.active_element()
    focus = page.observe_focus_ownership(panel=panel)
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
        first_row_label=first_row_label,
        focus_attempts=focus_attempts,
    )


def _press_shift_tab_and_capture(
    *,
    page: LiveWorkspaceSwitcherPage,
    state: dict[str, object],
) -> dict[str, object]:
    panel_payload = _panel_from_state(state)
    panel = WorkspaceSwitcherPanelObservation(**panel_payload)
    page.press_key("Shift+Tab", timeout_ms=FOCUS_TIMEOUT_MS)
    active = page.active_element()
    focus = page.observe_focus_ownership(panel=panel)
    row_focus = {
        name: _row_focus_payload(
            page.observe_saved_workspace_row_focus(display_name=name, panel=panel),
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

    payload = {
        "active": _focused_element_payload(active),
        "focus": _focus_ownership_payload(focus),
        "row_focus": row_focus,
        "saved_workspace_rows": _saved_workspace_rows_payload(rows),
        "expected_target": state.get("expected_target"),
        "first_row_label": state.get("first_row_label"),
    }
    if switcher is not None:
        payload["switcher"] = _switcher_payload(switcher)
    if switcher_error is not None:
        payload["switcher_error"] = switcher_error
    if surface is not None:
        payload["surface"] = _surface_payload(surface)
    if surface_error is not None:
        payload["surface_error"] = surface_error
    if rows_error is not None:
        payload["rows_error"] = rows_error
    return payload


def _assert_initial_state(state: dict[str, object]) -> None:
    rows = _saved_workspace_rows_from_state(state)
    active = _active_from_state(state)
    focus = _focus_from_state(state)
    first_row = _selected_row_payload(rows)
    expected_target = _expected_target_from_state(state)
    failures: list[str] = []

    if len(rows) < 3:
        failures.append("the visible switcher did not expose the expected saved workspace rows")
    if first_row is None:
        failures.append("no selected first saved workspace row was exposed")
    elif first_row.get("display_name") != FIRST_WORKSPACE_DISPLAY_NAME:
        failures.append(
            f"the selected row was {first_row.get('display_name')!r} instead of {FIRST_WORKSPACE_DISPLAY_NAME!r}",
        )
    if active.get("accessible_name") != state.get("first_row_label"):
        failures.append(
            f"the active element before Shift+Tab was {active.get('accessible_name')!r} instead of the first row {state.get('first_row_label')!r}",
        )
    if not bool(focus.get("focus_owned_by_switcher")):
        failures.append("keyboard focus was not owned by the open workspace switcher")
    if not bool(focus.get("active_within_switcher")):
        failures.append("the active element was not inside the open workspace switcher")
    if bool(focus.get("active_on_trigger")):
        failures.append("focus stayed on the workspace-switcher trigger instead of the first internal row")
    if not bool(_row_focus_from_state(state, FIRST_WORKSPACE_DISPLAY_NAME).get("row_contains_active")):
        failures.append("the first saved workspace row did not contain the active element")
    if expected_target.get("label") in {"", None}:
        failures.append("the open switcher did not expose a readable last internal focus target")
    if expected_target.get("label") == state.get("first_row_label"):
        failures.append("the computed last internal focus target incorrectly matched the first row")

    if failures:
        raise AssertionError(
            "Step 1 failed: the open workspace switcher did not satisfy the ticket "
            "preconditions before Shift+Tab was pressed.\n"
            + "\n".join(f"- {item}" for item in failures)
            + "\n"
            + f"Observed active element: {json.dumps(active, indent=2)}\n"
            + f"Observed focus ownership: {json.dumps(focus, indent=2)}\n"
            + f"Observed rows: {json.dumps(rows, indent=2)}\n"
            + f"Observed expected target: {json.dumps(expected_target, indent=2)}\n"
            + f"Observed focus attempts: {json.dumps(state.get('focus_attempts', []), indent=2)}"
        )


def _assert_reverse_wrap(state: dict[str, object]) -> None:
    active = _active_from_state(state)
    focus = _focus_from_state(state)
    expected_target = _expected_target_from_state(state)
    row_focus = {name: _row_focus_from_state(state, name) for name in WORKSPACE_NAMES}
    failures: list[str] = []

    if not bool(focus.get("focus_owned_by_switcher")):
        failures.append("keyboard focus was not owned by the workspace switcher after Shift+Tab")
    if not bool(focus.get("active_within_switcher")):
        failures.append("focus escaped the workspace switcher after Shift+Tab")
    if bool(focus.get("active_on_trigger")):
        failures.append("focus moved to the workspace-switcher trigger instead of wrapping inside the panel")
    if active.get("accessible_name") != expected_target.get("label"):
        failures.append(
            f"focus landed on {active.get('accessible_name')!r} instead of the last internal control {expected_target.get('label')!r}",
        )
    if active.get("accessible_name") == state.get("first_row_label"):
        failures.append("focus stayed on the first internal row instead of wrapping")
    if bool(row_focus.get(FIRST_WORKSPACE_DISPLAY_NAME, {}).get("row_contains_active")):
        failures.append("the first saved workspace row still contained the active element after Shift+Tab")

    if failures:
        raise AssertionError(
            "Step 2 failed: pressing Shift+Tab from the first workspace-switcher row did "
            "not wrap focus to the last internal control.\n"
            + "\n".join(f"- {item}" for item in failures)
            + "\n"
            + f"Observed active element: {json.dumps(active, indent=2)}\n"
            + f"Observed focus ownership: {json.dumps(focus, indent=2)}\n"
            + f"Expected wrap target: {json.dumps(expected_target, indent=2)}\n"
            + f"Observed row focus: {json.dumps(row_focus, indent=2)}\n"
            + f"Observed switcher: {json.dumps(_switcher_from_state(state), indent=2)}"
        )


def _ensure_first_internal_focus(
    *,
    page: LiveWorkspaceSwitcherPage,
    panel: WorkspaceSwitcherPanelObservation,
    first_row: WorkspaceSwitcherSavedWorkspaceRowObservation,
    first_row_label: str,
) -> list[dict[str, object]]:
    attempts: list[dict[str, object]] = []

    def record(action: str) -> WorkspaceSwitcherFocusOwnershipObservation:
        focus = page.observe_focus_ownership(panel=panel)
        row_focus = page.observe_saved_workspace_row_focus(
            display_name=first_row.display_name,
            panel=panel,
        )
        active = page.active_element()
        attempts.append(
            {
                "action": action,
                "active": _focused_element_payload(active),
                "focus": _focus_ownership_payload(focus),
                "row_focus": _row_focus_payload(row_focus),
            },
        )
        return focus

    focus = record("after-open")
    active = page.active_element()
    if (
        active.accessible_name == first_row_label
        and focus.focus_owned_by_switcher
        and focus.active_within_switcher
        and not focus.active_on_trigger
    ):
        return attempts

    page.focus_switcher_button(first_row_label, panel=panel, timeout_ms=FOCUS_TIMEOUT_MS)
    record("focus_switcher_button")
    return attempts


def _expected_last_internal_focus_target(
    *,
    surface: WorkspaceSwitcherSurfaceObservation,
    first_row_label: str,
) -> dict[str, object]:
    candidates = [
        item
        for item in surface.interactive_elements
        if item.label
        and item.label != first_row_label
    ]
    if not candidates:
        raise AssertionError(
            "Step 1 failed: the open workspace switcher did not expose enough interactive "
            "controls to compute a reverse-wrap target.\n"
            f"Observed interactive elements: {json.dumps(_surface_payload(surface), indent=2)}",
        )
    target = max(
        candidates,
        key=lambda item: (
            round(item.y + (item.height / 2), 2),
            round(item.x + (item.width / 2), 2),
            item.label,
        ),
    )
    return {
        "label": target.label,
        "accessible_label": target.accessible_label,
        "role": target.role,
        "tag_name": target.tag_name,
        "x": target.x,
        "y": target.y,
        "width": target.width,
        "height": target.height,
    }


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
    lines = [
        "# Test Automation Summary",
        "",
        f"- Test case: **{TICKET_KEY} - {TEST_CASE_TITLE}**",
        f"- Result: **{status}**",
        f"- Command: `{RUN_COMMAND}`",
        (
            f"- Environment: `{result['app_url']}` on Chromium/Playwright "
            f"({result['os']}) against `{result['repository']}` @ "
            f"`{result['repository_ref']}`."
        ),
        f"- Expected result: {EXPECTED_RESULT}",
        f"- Observed outcome: {_actual_vs_expected_summary(result)}",
    ]
    if result.get("screenshot"):
        lines.append(f"- Screenshot: `{result['screenshot']}`")
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
    reproduction_steps = [
        "1. Open the TrackState application in a desktop browser.",
        "2. Open the workspace switcher panel from Dashboard.",
        "3. Ensure keyboard focus is on the first internal workspace row in the open panel.",
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
                    "after_shift_tab_state": result.get("after_shift_tab_state"),
                },
                indent=2,
            ),
            "```",
        ],
    ) + "\n"


def _annotated_request_steps(result: dict[str, object]) -> str:
    before_state = result.get("initial_state")
    after_state = result.get("after_shift_tab_state")
    lines = [
        (
            "1. Open the TrackState application in a desktop browser and open the workspace switcher panel.\n"
            f"   {'✅' if _step_passed(result, 1) else '❌'} "
            f"{_step_observation(result, 1)}"
        ),
        (
            "2. Ensure keyboard focus is positioned on the first interactive element within the panel.\n"
            f"   {'✅' if _step_passed(result, 1) else '❌'} "
            f"Focused before Shift+Tab: {_active_label_for_summary(before_state)!r}"
        ),
        (
            "3. Press the 'Shift + Tab' keys on the keyboard.\n"
            f"   {'✅' if _step_passed(result, 2) else '❌'} "
            f"Expected wrap target: {_expected_target_label(after_state)!r}; "
            f"actual focus: {_active_label_for_summary(after_state)!r}"
        ),
    ]
    return "\n".join(lines)


def _actual_vs_expected_summary(result: dict[str, object]) -> str:
    after_state = result.get("after_shift_tab_state")
    if not isinstance(after_state, dict):
        return _failed_step_summary(result)
    expected = _expected_target_label(after_state)
    actual = _active_label_for_summary(after_state)
    focus = _focus_from_state(after_state)
    if _step_passed(result, 2):
        return (
            f"Shift+Tab wrapped focus from the first internal workspace row to {expected!r}, "
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
    first_row_label: str,
    focus_attempts: list[dict[str, object]],
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
            active_workspace.display_name if active_workspace is not None else None
        ),
        "row_focus": row_focus,
        "expected_target": expected_target,
        "first_row_label": first_row_label,
        "focus_attempts": focus_attempts,
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


def _expected_target_label(state: object) -> object:
    return _expected_target_from_state(state).get("label")


def _active_label_for_summary(state: object) -> object:
    return _active_from_state(state).get("accessible_name")


def _first_internal_label(state: object) -> object:
    if not isinstance(state, dict):
        return None
    return state.get("first_row_label")


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


if __name__ == "__main__":
    main()
