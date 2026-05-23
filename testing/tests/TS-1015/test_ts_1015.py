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
    WorkspaceSwitcherRowClickObservation,
    WorkspaceSwitcherSavedWorkspaceRowObservation,
    WorkspaceSwitcherTransitionMonitorObservation,
    WorkspaceSwitcherTriggerObservation,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.interfaces.web_app_session import FocusedElementObservation  # noqa: E402
from testing.tests.support.live_startup_case_support import (  # noqa: E402
    build_annotated_steps,
    format_human_lines,
    format_step_lines,
    record_human_verification,
    record_not_reached_steps,
    record_step,
    snippet,
    write_test_automation_result,
)
from testing.tests.support.live_tracker_app_factory import create_live_tracker_app  # noqa: E402
from testing.tests.support.stored_workspace_profiles_runtime import (  # noqa: E402
    StoredWorkspaceProfilesRuntime,
)

TICKET_KEY = "TS-1015"
TEST_CASE_TITLE = (
    "Click on a disabled workspace list item — workspace switcher remains open"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-1015/test_ts_1015.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
DEFAULT_BRANCH = "main"
ACTIVE_WORKSPACE_DISPLAY_NAME = "Hosted main workspace"
SECOND_WORKSPACE_DISPLAY_NAME = "Hosted alt workspace"
THIRD_WORKSPACE_DISPLAY_NAME = "Hosted third workspace"
SECOND_WORKSPACE_WRITE_BRANCH = "ts-1015-alt"
THIRD_WORKSPACE_WRITE_BRANCH = "ts-1015-third"
POST_CLICK_STABILITY_MS = 1_000
SURFACE_TIMEOUT_MS = 4_000
LINKED_BUGS = ["TS-1010"]

PRECONDITIONS = [
    "The workspace switcher is open.",
    "At least one workspace entry in the list is in a disabled state (for this live scenario, the current active workspace entry).",
]
REQUEST_STEPS = [
    "Locate the disabled workspace entry within the switcher panel.",
    "Click directly on the disabled workspace entry using a pointer interaction.",
]
AUTOMATION_STEPS = [
    "Launch the deployed desktop app and open the workspace switcher.",
    "Verify the current active workspace row is present as the inert current-workspace entry before clicking it.",
    "Click the current active workspace row with a real pointer click on the row surface.",
    "Observe the workspace switcher after the click and verify it remains visibly open for the required stability window.",
]
EXPECTED_RESULT = (
    "The workspace switcher remains open. The blur event handler correctly "
    "identifies the interaction target as a descendant of the switcher container, "
    "even though the row does not create a workspace switch action."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1015_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1015_failure.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-1015 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
        )

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
        "request_steps": REQUEST_STEPS,
        "automation_steps": AUTOMATION_STEPS,
        "post_click_stability_ms": POST_CLICK_STABILITY_MS,
        "surface_timeout_ms": SURFACE_TIMEOUT_MS,
        "preloaded_workspace_state": workspace_state,
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
                        "desktop state before the disabled-row click scenario began.\n"
                        f"Observed runtime state: {runtime.kind}\n"
                        f"Observed body text:\n{runtime.body_text}",
                    )
                page.dismiss_connection_banner()
                page.navigate_to_section("Dashboard")
                page.set_viewport(**DESKTOP_VIEWPORT)

                trigger = page.observe_trigger()
                switcher_before = page.open_and_observe(timeout_ms=10_000)
                panel_before = page.observe_open_panel(
                    expected_container_kinds=("anchored-panel", "surface"),
                    timeout_ms=SURFACE_TIMEOUT_MS,
                )
                rows_before = page.observe_saved_workspace_rows(timeout_ms=10_000)
                result["trigger_observation"] = _trigger_payload(trigger)
                result["panel_before_click"] = asdict(panel_before)
                result["switcher_before_click"] = _switcher_payload(switcher_before)
                result["rows_before_click"] = _rows_payload(rows_before)
                _assert_switcher_open_state(
                    trigger=trigger,
                    panel=panel_before,
                    switcher=switcher_before,
                    rows=rows_before,
                )
                record_step(
                    result,
                    step=1,
                    status="passed",
                    action=AUTOMATION_STEPS[0],
                    observed=(
                        f"Opened {config.app_url} in Chromium at "
                        f"{DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}; "
                        f"trigger_label={trigger.semantic_label!r}; "
                        f"panel_kind={panel_before.container_kind!r}; "
                        f"row_count={len(rows_before)}."
                    ),
                )
                record_human_verification(
                    result,
                    check=(
                        "Opened the live desktop workspace switcher and visually confirmed "
                        "the Workspace switcher title plus the current workspace row were visible."
                    ),
                    observed=(
                        f"selected_workspace={_selected_workspace_name(rows_before)!r}; "
                        f"text_excerpt={snippet(switcher_before.switcher_text)!r}"
                    ),
                )

                active_row = _find_active_workspace_row(rows_before)
                row_candidates = page.debug_saved_workspace_row_candidates(
                    ACTIVE_WORKSPACE_DISPLAY_NAME,
                )
                result["active_row_before_click"] = asdict(active_row)
                result["active_row_candidates_before_click"] = row_candidates
                resolved_candidate = _find_row_candidate(row_candidates)
                _assert_current_workspace_inert_row(
                    active_row=active_row,
                    row_candidate=resolved_candidate,
                    all_candidates=row_candidates,
                )
                record_step(
                    result,
                    step=2,
                    status="passed",
                    action=AUTOMATION_STEPS[1],
                    observed=(
                        f"selected={active_row.selected}; "
                        f"action_labels={list(active_row.action_labels)!r}; "
                        f"state_label={active_row.state_label!r}; "
                        f"resolved_candidate={json.dumps(resolved_candidate, ensure_ascii=True)}"
                    ),
                )
                record_human_verification(
                    result,
                    check=(
                        "Verified the visible current workspace entry was the highlighted inert row "
                        "showing Active rather than an Open action before clicking it."
                    ),
                    observed=(
                        f"display_name={active_row.display_name!r}; "
                        f"action_labels={list(active_row.action_labels)!r}; "
                        f"detail_text={active_row.detail_text!r}"
                    ),
                )

                page.start_transition_monitor()
                click_observation = page.click_saved_workspace_row_surface(
                    ACTIVE_WORKSPACE_DISPLAY_NAME,
                    timeout_ms=SURFACE_TIMEOUT_MS,
                )
                result["click_observation"] = _row_click_payload(click_observation)
                _assert_click_target(click_observation)
                record_step(
                    result,
                    step=3,
                    status="passed",
                    action=AUTOMATION_STEPS[2],
                    observed=(
                        f"clicked_point=({click_observation.click_x:.1f}, {click_observation.click_y:.1f}); "
                        f"target_label={click_observation.target_label!r}; "
                        f"target_identifier={click_observation.target_identifier!r}; "
                        f"target_aria_current={click_observation.target_aria_current!r}."
                    ),
                )

                step4_error: Exception | None = None
                try:
                    page.wait_for_surface_to_remain_open(
                        stability_ms=POST_CLICK_STABILITY_MS,
                        timeout_ms=SURFACE_TIMEOUT_MS,
                    )
                except Exception as error:
                    step4_error = error

                monitor_after_click = _try_read_transition_monitor(page)
                _try_stop_transition_monitor(page)
                result["monitor_after_click"] = (
                    _monitor_payload(monitor_after_click)
                    if monitor_after_click is not None
                    else {}
                )
                result["body_text_after_click"] = page.current_body_text()
                focus_after_click = page.active_element()
                result["focused_after_click"] = _focused_element_payload(focus_after_click)

                panel_after_click = _safe_observe_panel(page)
                switcher_after_click = _safe_observe_switcher(page)
                rows_after_click = _safe_observe_rows(page)
                focus_ownership_after_click = (
                    page.observe_focus_ownership(panel=panel_after_click)
                    if panel_after_click is not None
                    else None
                )
                if panel_after_click is not None:
                    result["panel_after_click"] = asdict(panel_after_click)
                if switcher_after_click is not None:
                    result["switcher_after_click"] = _switcher_payload(switcher_after_click)
                if rows_after_click is not None:
                    result["rows_after_click"] = _rows_payload(rows_after_click)
                if focus_ownership_after_click is not None:
                    result["focus_ownership_after_click"] = _focus_ownership_payload(
                        focus_ownership_after_click,
                    )

                if step4_error is not None:
                    raise AssertionError(
                        "Step 4 failed: clicking the current disabled workspace row did not "
                        "leave the workspace switcher visibly open for the required stability window.\n"
                        f"Original error: {step4_error}\n"
                        f"Observed transition monitor: {json.dumps(result.get('monitor_after_click', {}), indent=2)}\n"
                        f"Observed body text after click:\n{result['body_text_after_click']}",
                    ) from step4_error

                _assert_switcher_remains_open_after_click(
                    before_panel=panel_before,
                    before_switcher=switcher_before,
                    before_rows=rows_before,
                    after_panel=panel_after_click,
                    after_switcher=switcher_after_click,
                    after_rows=rows_after_click,
                    monitor=monitor_after_click,
                    focus_after=focus_after_click,
                    focus_ownership_after=focus_ownership_after_click,
                )
                record_step(
                    result,
                    step=4,
                    status="passed",
                    action=AUTOMATION_STEPS[3],
                    observed=(
                        f"panel_kind={panel_after_click.container_kind if panel_after_click else None!r}; "
                        f"row_count={switcher_after_click.row_count if switcher_after_click else None}; "
                        f"monitor_hidden_after_visible={monitor_after_click.ever_hidden_after_visible if monitor_after_click else None}; "
                        f"selected_workspace_after_click={_selected_workspace_name(rows_after_click) if rows_after_click else None!r}."
                    ),
                )
                record_human_verification(
                    result,
                    check=(
                        "Clicked the current workspace row like a user and watched whether the "
                        "workspace switcher stayed on screen instead of collapsing."
                    ),
                    observed=(
                        f"title_visible={bool(switcher_after_click and 'Workspace switcher' in switcher_after_click.switcher_text)}; "
                        f"selected_workspace_after_click={_selected_workspace_name(rows_after_click) if rows_after_click else None!r}; "
                        f"focus_after_click={focus_after_click.accessible_name!r}; "
                        f"monitor_hidden_after_visible={monitor_after_click.ever_hidden_after_visible if monitor_after_click else None}"
                    ),
                )
            except Exception:
                _try_stop_transition_monitor(page)
                if page is not None:
                    try:
                        page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                        result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                    except Exception as screenshot_error:
                        result["screenshot_error"] = (
                            f"{type(screenshot_error).__name__}: {screenshot_error}"
                        )
                _record_not_reached_steps_if_needed(result)
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
                "displayName": ACTIVE_WORKSPACE_DISPLAY_NAME,
                "customDisplayName": ACTIVE_WORKSPACE_DISPLAY_NAME,
                "targetType": "hosted",
                "target": repository,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": DEFAULT_BRANCH,
                "lastOpenedAt": "2026-05-23T00:00:00.000Z",
            },
            {
                "id": second_id,
                "displayName": SECOND_WORKSPACE_DISPLAY_NAME,
                "customDisplayName": SECOND_WORKSPACE_DISPLAY_NAME,
                "targetType": "hosted",
                "target": repository,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": SECOND_WORKSPACE_WRITE_BRANCH,
                "lastOpenedAt": "2026-05-22T23:50:00.000Z",
            },
            {
                "id": third_id,
                "displayName": THIRD_WORKSPACE_DISPLAY_NAME,
                "customDisplayName": THIRD_WORKSPACE_DISPLAY_NAME,
                "targetType": "hosted",
                "target": repository,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": THIRD_WORKSPACE_WRITE_BRANCH,
                "lastOpenedAt": "2026-05-22T23:40:00.000Z",
            },
        ],
    }


def _assert_switcher_open_state(
    *,
    trigger: WorkspaceSwitcherTriggerObservation,
    panel: WorkspaceSwitcherPanelObservation,
    switcher: WorkspaceSwitcherObservation,
    rows: tuple[WorkspaceSwitcherSavedWorkspaceRowObservation, ...],
) -> None:
    failures: list[str] = []
    if not trigger.semantic_label:
        failures.append("the workspace-switcher trigger did not expose an accessibility label")
    if panel.container_kind not in {"anchored-panel", "surface"}:
        failures.append(
            f"container_kind was {panel.container_kind!r} instead of an anchored desktop panel",
        )
    if panel.background_dimmed:
        failures.append("the workspace switcher dimmed the background like a modal")
    if switcher.row_count <= 0 or not rows:
        failures.append("no visible saved workspace rows were rendered")
    if "Workspace switcher" not in switcher.switcher_text:
        failures.append('the visible "Workspace switcher" heading was missing')
    if failures:
        raise AssertionError(
            "Step 1 failed: the live app did not expose the expected desktop workspace "
            "switcher surface.\n"
            + "\n".join(f"- {failure}" for failure in failures)
            + "\n"
            + f"Observed panel: {json.dumps(asdict(panel), indent=2)}\n"
            + f"Observed switcher text:\n{switcher.switcher_text}"
        )


def _find_active_workspace_row(
    rows: tuple[WorkspaceSwitcherSavedWorkspaceRowObservation, ...],
) -> WorkspaceSwitcherSavedWorkspaceRowObservation:
    row = next((candidate for candidate in rows if candidate.display_name == ACTIVE_WORKSPACE_DISPLAY_NAME), None)
    if row is None:
        raise AssertionError(
            "Step 2 failed: the workspace switcher did not expose the expected current "
            f'workspace row "{ACTIVE_WORKSPACE_DISPLAY_NAME}".\n'
            f"Observed rows: {json.dumps(_rows_payload(rows), indent=2)}",
        )
    return row


def _assert_current_workspace_inert_row(
    *,
    active_row: WorkspaceSwitcherSavedWorkspaceRowObservation,
    row_candidate: dict[str, object],
    all_candidates: list[dict[str, object]],
) -> None:
    failures: list[str] = []
    if not active_row.selected:
        failures.append("the current workspace row was not marked selected")
    if "Active" not in active_row.action_labels:
        failures.append(
            f"the current workspace row exposed {list(active_row.action_labels)!r} instead of an Active marker",
        )
    if str(row_candidate.get("aria_current")) != "true":
        failures.append(
            f"the resolved row candidate did not expose aria-current=true (observed {row_candidate.get('aria_current')!r})",
        )
    identifier = str(row_candidate.get("identifier", ""))
    if "trackstate-workspace-switcher-row-" not in identifier:
        failures.append(
            f"the resolved row candidate did not look like a switcher row surface (identifier={identifier!r})",
        )
    if failures:
        raise AssertionError(
            "Step 2 failed: the live switcher did not expose the expected inert current-workspace "
            "entry before the pointer click.\n"
            + "\n".join(f"- {failure}" for failure in failures)
            + "\n"
            + f"Observed current row: {json.dumps(asdict(active_row), indent=2)}\n"
            + f"Observed row candidates: {json.dumps(all_candidates, indent=2)}"
        )


def _find_row_candidate(candidates: list[dict[str, object]]) -> dict[str, object]:
    row_candidate = next(
        (
            candidate
            for candidate in candidates
            if (
                str(candidate.get("identifier", "")).startswith("trackstate-workspace-switcher-row-")
                or str(candidate.get("aria_current")) == "true"
            )
        ),
        None,
    )
    if row_candidate is None:
        raise AssertionError(
            "Step 2 failed: no row-like DOM candidate was available for the current workspace entry.\n"
            f"Observed candidates: {json.dumps(candidates, indent=2)}",
        )
    return row_candidate


def _assert_click_target(observation: WorkspaceSwitcherRowClickObservation) -> None:
    failures: list[str] = []
    if observation.click_x <= 0 or observation.click_y <= 0:
        failures.append("the resolved pointer click coordinates were invalid")
    if ACTIVE_WORKSPACE_DISPLAY_NAME not in {
        observation.display_name,
        observation.target_label,
        observation.target_text,
    }:
        failures.append("the pointer click did not target the current workspace row")
    if observation.target_identifier and "trigger" in observation.target_identifier:
        failures.append("the pointer click targeted the workspace-switcher trigger instead of the row")
    if failures:
        raise AssertionError(
            "Step 3 failed: the test could not click the current workspace row with a real "
            "pointer target.\n"
            + "\n".join(f"- {failure}" for failure in failures)
            + "\n"
            + f"Observed click target: {json.dumps(_row_click_payload(observation), indent=2)}"
        )


def _assert_switcher_remains_open_after_click(
    *,
    before_panel: WorkspaceSwitcherPanelObservation,
    before_switcher: WorkspaceSwitcherObservation,
    before_rows: tuple[WorkspaceSwitcherSavedWorkspaceRowObservation, ...],
    after_panel: WorkspaceSwitcherPanelObservation | None,
    after_switcher: WorkspaceSwitcherObservation | None,
    after_rows: tuple[WorkspaceSwitcherSavedWorkspaceRowObservation, ...] | None,
    monitor: WorkspaceSwitcherTransitionMonitorObservation | None,
    focus_after: FocusedElementObservation,
    focus_ownership_after: WorkspaceSwitcherFocusOwnershipObservation | None,
) -> None:
    failures: list[str] = []
    if after_panel is None:
        failures.append("the switcher panel could no longer be observed after the click")
    elif after_panel.container_kind not in {"anchored-panel", "surface"}:
        failures.append(
            f"container_kind became {after_panel.container_kind!r} instead of staying a desktop panel",
        )
    if after_switcher is None:
        failures.append("the switcher text surface disappeared after the click")
    else:
        if "Workspace switcher" not in after_switcher.switcher_text:
            failures.append('the visible "Workspace switcher" heading disappeared after the click')
        if after_switcher.row_count != before_switcher.row_count:
            failures.append(
                f"the visible workspace row count changed from {before_switcher.row_count} to {after_switcher.row_count}",
            )
    if after_rows is None:
        failures.append("no saved workspace rows were readable after the click")
    else:
        if _selected_workspace_name(after_rows) != _selected_workspace_name(before_rows):
            failures.append("the selected workspace changed even though the current row was clicked")
    if monitor is None:
        failures.append("the transition monitor did not return post-click samples")
    else:
        if monitor.ever_hidden_after_visible:
            failures.append("the transition monitor observed the panel become hidden after the click")
        if monitor.visible_sample_count <= 0:
            failures.append("the transition monitor captured no visible switcher samples after the click")
    if focus_ownership_after is None:
        failures.append("keyboard focus ownership could not be observed after the click")
    elif not focus_ownership_after.focus_owned_by_switcher:
        failures.append("keyboard focus was no longer owned by the switcher after the click")
    if failures:
        raise AssertionError(
            "Step 4 failed: clicking the current disabled workspace row did not leave the "
            "workspace switcher visibly open.\n"
            + "\n".join(f"- {failure}" for failure in failures)
            + "\n"
            + f"Observed focus after click: {json.dumps(_focused_element_payload(focus_after), indent=2)}\n"
            + f"Observed transition monitor: {json.dumps(_monitor_payload(monitor) if monitor else {}, indent=2)}"
        )
    if before_panel.container_kind != after_panel.container_kind:
        raise AssertionError(
            "Step 4 failed: the visible panel container changed after clicking the inert row.\n"
            f"Before={before_panel.container_kind!r} After={after_panel.container_kind!r}",
        )


def _trigger_payload(observation: WorkspaceSwitcherTriggerObservation) -> dict[str, object]:
    return {
        "semantic_label": observation.semantic_label,
        "visible_text": observation.visible_text,
        "display_name": observation.display_name,
        "workspace_type": observation.workspace_type,
        "state_label": observation.state_label,
        "top_button_labels": list(observation.top_button_labels),
    }


def _switcher_payload(observation: WorkspaceSwitcherObservation) -> dict[str, object]:
    return {
        "row_count": observation.row_count,
        "switcher_text": observation.switcher_text,
        "selected_workspace": _selected_workspace_name(observation.rows),
        "rows": [asdict(row) for row in observation.rows],
    }


def _rows_payload(
    rows: tuple[WorkspaceSwitcherSavedWorkspaceRowObservation, ...] | None,
) -> list[dict[str, object]]:
    if not rows:
        return []
    return [asdict(row) for row in rows]


def _row_click_payload(observation: WorkspaceSwitcherRowClickObservation) -> dict[str, object]:
    return {
        "display_name": observation.display_name,
        "click_x": observation.click_x,
        "click_y": observation.click_y,
        "target_tag_name": observation.target_tag_name,
        "target_role": observation.target_role,
        "target_label": observation.target_label,
        "target_text": observation.target_text,
        "target_tabindex": observation.target_tabindex,
        "target_disabled": observation.target_disabled,
        "target_aria_current": observation.target_aria_current,
        "target_identifier": observation.target_identifier,
    }


def _monitor_payload(
    observation: WorkspaceSwitcherTransitionMonitorObservation | None,
) -> dict[str, object]:
    if observation is None:
        return {}
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


def _focused_element_payload(observation: FocusedElementObservation) -> dict[str, object]:
    return {
        "accessible_name": observation.accessible_name,
        "role": observation.role,
        "tag_name": observation.tag_name,
        "text": observation.text,
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
        "switcher_focus_within": observation.switcher_focus_within,
        "active_within_switcher": observation.active_within_switcher,
        "active_on_trigger": observation.active_on_trigger,
        "focus_owned_by_switcher": observation.focus_owned_by_switcher,
    }


def _selected_workspace_name(
    rows: tuple[WorkspaceSwitcherSavedWorkspaceRowObservation, ...] | None,
) -> str | None:
    if not rows:
        return None
    for row in rows:
        if row.selected:
            return row.display_name
    return None


def _safe_observe_panel(
    page: LiveWorkspaceSwitcherPage,
) -> WorkspaceSwitcherPanelObservation | None:
    try:
        return page.observe_open_panel(
            expected_container_kinds=("anchored-panel", "surface"),
            timeout_ms=SURFACE_TIMEOUT_MS,
        )
    except AssertionError:
        return None


def _safe_observe_switcher(
    page: LiveWorkspaceSwitcherPage,
) -> WorkspaceSwitcherObservation | None:
    try:
        return page.observe_open_switcher(timeout_ms=SURFACE_TIMEOUT_MS)
    except AssertionError:
        return None


def _safe_observe_rows(
    page: LiveWorkspaceSwitcherPage,
) -> tuple[WorkspaceSwitcherSavedWorkspaceRowObservation, ...] | None:
    try:
        return page.observe_saved_workspace_rows(timeout_ms=SURFACE_TIMEOUT_MS)
    except AssertionError:
        return None


def _try_read_transition_monitor(
    page: LiveWorkspaceSwitcherPage,
) -> WorkspaceSwitcherTransitionMonitorObservation | None:
    try:
        return page.read_transition_monitor(clear=True)
    except AssertionError:
        return None


def _try_stop_transition_monitor(page: LiveWorkspaceSwitcherPage | None) -> None:
    if page is None:
        return
    try:
        page.stop_transition_monitor()
    except AssertionError:
        return


def _record_not_reached_steps_if_needed(result: dict[str, object]) -> None:
    recorded_steps = [
        int(step["step"])
        for step in result.get("steps", [])
        if isinstance(step, dict) and isinstance(step.get("step"), int)
    ]
    if not recorded_steps:
        return
    highest_step = max(recorded_steps)
    if highest_step < len(AUTOMATION_STEPS):
        record_not_reached_steps(
            result,
            starting_step=highest_step + 1,
            request_steps=AUTOMATION_STEPS,
        )


def _write_pass_outputs(result: dict[str, object]) -> None:
    BUG_DESCRIPTION_PATH.unlink(missing_ok=True)
    write_test_automation_result(RESULT_PATH, passed=True)
    JIRA_COMMENT_PATH.write_text(_jira_comment(result, passed=True), encoding="utf-8")
    PR_BODY_PATH.write_text(_pr_body(result, passed=True), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_summary(result, passed=True), encoding="utf-8")


def _write_failure_outputs(result: dict[str, object]) -> None:
    error = str(result.get("error", "AssertionError: TS-1015 failed"))
    write_test_automation_result(RESULT_PATH, passed=False, error=error)
    JIRA_COMMENT_PATH.write_text(_jira_comment(result, passed=False), encoding="utf-8")
    PR_BODY_PATH.write_text(_pr_body(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_summary(result, passed=False), encoding="utf-8")
    if _is_product_failure(result):
        BUG_DESCRIPTION_PATH.write_text(_bug_description(result), encoding="utf-8")
    else:
        BUG_DESCRIPTION_PATH.unlink(missing_ok=True)


def _is_product_failure(result: dict[str, object]) -> bool:
    error = str(result.get("error", ""))
    if not error:
        return False
    infrastructure_prefixes = (
        "RuntimeError:",
        "ModuleNotFoundError:",
        "ImportError:",
        "SyntaxError:",
    )
    return not error.startswith(infrastructure_prefixes)


def _jira_comment(result: dict[str, object], *, passed: bool) -> str:
    status = "✅ PASSED" if passed else "❌ FAILED"
    lines = [
        "h3. Test Automation Result",
        "",
        f"*Ticket:* {TICKET_KEY}",
        f"*Status:* {status}",
        f"*Test case:* {TEST_CASE_TITLE}",
        f"*Environment:* {{code}}{_environment_summary(result)}{{code}}",
        f"*Linked bugs covered:* {', '.join(result.get('linked_bugs', []))}",
        "",
        "h4. Automated checks",
        *format_step_lines(result, jira=True),
        "",
        "h4. Human-style verification",
        *format_human_lines(result, jira=True),
        "",
        "h4. Observed result",
        f"{{code}}{_result_summary(result, passed=passed)}{{code}}",
    ]
    screenshot = result.get("screenshot")
    if screenshot:
        lines.extend(["", f"*Screenshot:* {{code}}{screenshot}{{code}}"])
    return "\n".join(lines) + "\n"


def _pr_body(result: dict[str, object], *, passed: bool) -> str:
    status = "✅ PASSED" if passed else "❌ FAILED"
    lines = [
        f"## {status} {TICKET_KEY}",
        "",
        f"**Test case:** {TEST_CASE_TITLE}",
        "",
        f"**Environment:** `{_environment_summary(result)}`",
        "",
        "### Automated checks",
        *format_step_lines(result, jira=False),
        "",
        "### Human-style verification",
        *format_human_lines(result, jira=False),
        "",
        "### Observed result",
        _result_summary(result, passed=passed),
    ]
    screenshot = result.get("screenshot")
    if screenshot:
        lines.extend(["", f"**Screenshot:** `{screenshot}`"])
    return "\n".join(lines) + "\n"


def _response_summary(result: dict[str, object], *, passed: bool) -> str:
    status = "passed" if passed else "failed"
    return (
        f"# {TICKET_KEY} {status}\n\n"
        f"{_result_summary(result, passed=passed)}\n\n"
        f"Environment: `{_environment_summary(result)}`\n"
    )


def _result_summary(result: dict[str, object], *, passed: bool) -> str:
    if passed:
        return (
            "Clicked the inert current workspace row in the live switcher and the panel "
            "stayed visibly open: the heading, workspace rows, and selected Active row all "
            "remained on screen, and the transition monitor never observed the panel hide."
        )
    return str(result.get("error", "TS-1015 failed."))


def _environment_summary(result: dict[str, object]) -> str:
    viewport = result.get("desktop_viewport", {})
    width = viewport.get("width")
    height = viewport.get("height")
    return (
        f"URL={result.get('app_url')} | browser={result.get('browser')} | "
        f"OS={result.get('os')} | viewport={width}x{height} | "
        f"repo={result.get('repository')}@{result.get('repository_ref')}"
    )


def _bug_description(result: dict[str, object]) -> str:
    annotated_steps = build_annotated_steps(
        {
            "steps": [
                {
                    "step": 1,
                    "status": "passed",
                    "action": REQUEST_STEPS[0],
                    "observed": (
                        f'Located the current workspace row {ACTIVE_WORKSPACE_DISPLAY_NAME!r} in the open '
                        "switcher; it was selected and showed the Active marker."
                    ),
                },
                {
                    "step": 2,
                    "status": "failed",
                    "action": REQUEST_STEPS[1],
                    "observed": str(result.get("error", "")),
                },
            ],
        },
        request_steps=REQUEST_STEPS,
    )
    screenshot = result.get("screenshot", "No screenshot captured.")
    return "\n".join(
        [
            f"# {TICKET_KEY}: Clicking the current disabled workspace row collapses the workspace switcher",
            "",
            "## Preconditions",
            *[f"- {item}" for item in PRECONDITIONS],
            "",
            "## Steps to reproduce",
            *annotated_steps,
            "",
            "## Exact error message / assertion failure",
            "```text",
            str(result.get("traceback", result.get("error", ""))),
            "```",
            "",
            "## Actual result",
            _actual_failure_details(result),
            "",
            "## Expected result",
            EXPECTED_RESULT,
            "",
            "## Environment",
            f"- {_environment_summary(result)}",
            "",
            "## Evidence",
            f"- Screenshot: {screenshot}",
            f"- Click observation: {json.dumps(result.get('click_observation', {}), indent=2)}",
            f"- Active row before click: {json.dumps(result.get('active_row_before_click', {}), indent=2)}",
            f"- Active row candidates before click: {json.dumps(result.get('active_row_candidates_before_click', []), indent=2)}",
            f"- Transition monitor after click: {json.dumps(result.get('monitor_after_click', {}), indent=2)}",
            f"- Focus after click: {json.dumps(result.get('focused_after_click', {}), indent=2)}",
            f"- Body text after click:\n{result.get('body_text_after_click', '')}",
        ],
    ) + "\n"


def _actual_failure_details(result: dict[str, object]) -> str:
    return (
        "After clicking the current workspace row in the live workspace switcher, the panel "
        "did not stay open for the required 1000 ms stability window. The visible "
        "`Workspace switcher` surface disappeared and the page returned to the dashboard "
        "shell instead of keeping the switcher open.\n\n"
        f"Observed error:\n{result.get('error', '')}\n\n"
        "Observed transition monitor:\n"
        + json.dumps(result.get("monitor_after_click", {}), indent=2)
        + "\n\nObserved focus after click:\n"
        + json.dumps(result.get("focused_after_click", {}), indent=2)
    )


if __name__ == "__main__":
    main()
