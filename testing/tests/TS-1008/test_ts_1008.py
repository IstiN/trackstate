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
    WorkspaceSwitcherButtonStateObservation,
    WorkspaceSwitcherFocusOwnershipObservation,
    WorkspaceSwitcherInternalClickObservation,
    WorkspaceSwitcherObservation,
    WorkspaceSwitcherPanelObservation,
    WorkspaceSwitcherTransitionMonitorObservation,
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

TICKET_KEY = "TS-1008"
TEST_CASE_TITLE = (
    "Click on disabled 'Save and switch' button in pristine state — workspace "
    "switcher remains open"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-1008/test_ts_1008.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
DEFAULT_BRANCH = "main"
FIRST_WORKSPACE_DISPLAY_NAME = "Hosted main workspace"
SECOND_WORKSPACE_DISPLAY_NAME = "Hosted alt workspace"
THIRD_WORKSPACE_DISPLAY_NAME = "Hosted third workspace"
SECOND_WORKSPACE_WRITE_BRANCH = "ts-1008-alt"
THIRD_WORKSPACE_WRITE_BRANCH = "ts-1008-third"
LAST_INTERNAL_CONTROL_LABEL = "Save and switch"
POST_CLICK_STABILITY_MS = 1_000
SURFACE_TIMEOUT_MS = 4_000

PRECONDITIONS = ["The workspace switcher is open in a pristine state."]
REQUEST_STEPS = [
    "Click the 'Save and switch' button in the footer (which is currently in a disabled state).",
]
AUTOMATION_STEPS = [
    "Launch the deployed desktop app and open the workspace switcher in a pristine state.",
    "Verify the visible footer renders a disabled Save and switch button.",
    "Click the disabled Save and switch footer button with a real pointer click.",
    "Observe the workspace switcher after the click and verify it remains visibly open.",
]
EXPECTED_RESULT = (
    "The workspace switcher panel remains open. The blur event handler correctly "
    "recognizes the click target (relatedTarget) as being within the switcher's "
    "DOM tree, preventing an automatic panel collapse."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1008_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1008_failure.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-1008 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
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
        "linked_bugs": ["TS-997"],
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
                trigger = None
                panel_before = None
                switcher_before = None
                button_before = None
                focus_before = None
                focus_ownership_before = None

                try:
                    runtime = tracker_page.open()
                    result["runtime_state"] = runtime.kind
                    result["runtime_body_text"] = runtime.body_text
                    if runtime.kind != "ready":
                        raise AssertionError(
                            "Step 1 failed: the deployed app did not reach an interactive "
                            "desktop state before the pristine footer-click scenario began.\n"
                            f"Observed runtime state: {runtime.kind}\n"
                            f"Observed body text:\n{runtime.body_text}",
                        )
                    page.dismiss_connection_banner()
                    page.set_viewport(**DESKTOP_VIEWPORT)
                    trigger = page.observe_trigger()
                    page.open_switcher()
                    panel_before = page.observe_open_panel(
                        expected_container_kinds=("anchored-panel", "surface"),
                        timeout_ms=SURFACE_TIMEOUT_MS,
                    )
                    switcher_before = page.observe_open_switcher(
                        timeout_ms=SURFACE_TIMEOUT_MS,
                    )
                    focus_before = page.active_element()
                    focus_ownership_before = page.observe_focus_ownership(panel=panel_before)
                    result["trigger_observation"] = asdict(trigger)
                    result["panel_before_click"] = asdict(panel_before)
                    result["switcher_before_click"] = _switcher_payload(switcher_before)
                    result["focused_before_click"] = _focused_element_payload(focus_before)
                    result["focus_ownership_before_click"] = _focus_ownership_payload(
                        focus_ownership_before,
                    )
                    _assert_switcher_open_state(
                        panel=panel_before,
                        switcher=switcher_before,
                    )
                except Exception as error:
                    record_step(
                        result,
                        step=1,
                        status="failed",
                        action=AUTOMATION_STEPS[0],
                        observed=str(error),
                    )
                    raise
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
                        f"row_count={switcher_before.row_count}."
                    ),
                )
                record_human_verification(
                    result,
                    check=(
                        "Opened the live desktop workspace switcher and visually confirmed "
                        "the Workspace switcher title plus the saved-workspace list were "
                        "present before any workspace change was made."
                    ),
                    observed=(
                        f"title_visible={'Workspace switcher' in switcher_before.switcher_text}; "
                        f"selected_workspace={_selected_workspace_name(switcher_before)!r}; "
                        f"text_excerpt={snippet(switcher_before.switcher_text)!r}"
                    ),
                )

                try:
                    button_before = page.observe_switcher_button_state(
                        LAST_INTERNAL_CONTROL_LABEL,
                        timeout_ms=SURFACE_TIMEOUT_MS,
                    )
                    result["button_before_click"] = _button_payload(button_before)
                    _assert_disabled_save_button(button_before)
                except Exception as error:
                    record_step(
                        result,
                        step=2,
                        status="failed",
                        action=AUTOMATION_STEPS[1],
                        observed=str(error),
                    )
                    raise
                record_step(
                    result,
                    step=2,
                    status="passed",
                    action=AUTOMATION_STEPS[1],
                    observed=(
                        f"button_text={button_before.visible_text!r}; "
                        f"aria_disabled={button_before.aria_disabled!r}; "
                        f"disabled={button_before.disabled}; "
                        f"tabindex={button_before.tabindex!r}."
                    ),
                )
                record_human_verification(
                    result,
                    check=(
                        "Viewed the footer itself and confirmed the exact Save and switch "
                        "label was visible there in a disabled state, not hidden or replaced."
                    ),
                    observed=(
                        f"footer_text={button_before.visible_text!r}; "
                        f"outer_html={_compact_html(button_before.outer_html)!r}"
                    ),
                )

                click_observation = None
                try:
                    page.start_transition_monitor()
                    click_observation = page.click_switcher_button_center(
                        LAST_INTERNAL_CONTROL_LABEL,
                        timeout_ms=SURFACE_TIMEOUT_MS,
                    )
                    result["click_observation"] = asdict(click_observation)
                    _assert_click_target(click_observation)
                except Exception as error:
                    record_step(
                        result,
                        step=3,
                        status="failed",
                        action=AUTOMATION_STEPS[2],
                        observed=str(error),
                    )
                    raise
                record_step(
                    result,
                    step=3,
                    status="passed",
                    action=AUTOMATION_STEPS[2],
                    observed=(
                        f"clicked_point=({click_observation.click_x:.1f}, "
                        f"{click_observation.click_y:.1f}); "
                        f"target_label={click_observation.target_label!r}; "
                        f"target_text={click_observation.target_text!r}; "
                        f"target_role={click_observation.target_role!r}."
                    ),
                )

                panel_after = None
                switcher_after = None
                button_after = None
                focus_after = None
                focus_ownership_after = None
                monitor = None
                try:
                    page.wait_for_surface_to_remain_open(
                        stability_ms=POST_CLICK_STABILITY_MS,
                        timeout_ms=SURFACE_TIMEOUT_MS,
                    )
                    monitor = page.read_transition_monitor(clear=True)
                    page.stop_transition_monitor()
                    panel_after = page.observe_open_panel(
                        expected_container_kinds=("anchored-panel", "surface"),
                        timeout_ms=SURFACE_TIMEOUT_MS,
                    )
                    switcher_after = page.observe_open_switcher(
                        timeout_ms=SURFACE_TIMEOUT_MS,
                    )
                    button_after = page.observe_switcher_button_state(
                        LAST_INTERNAL_CONTROL_LABEL,
                        timeout_ms=SURFACE_TIMEOUT_MS,
                    )
                    focus_after = page.active_element()
                    focus_ownership_after = page.observe_focus_ownership(panel=panel_after)
                    result["monitor_after_click"] = _monitor_payload(monitor)
                    result["panel_after_click"] = asdict(panel_after)
                    result["switcher_after_click"] = _switcher_payload(switcher_after)
                    result["button_after_click"] = _button_payload(button_after)
                    result["focused_after_click"] = _focused_element_payload(focus_after)
                    result["focus_ownership_after_click"] = _focus_ownership_payload(
                        focus_ownership_after,
                    )
                    _assert_switcher_remains_open_after_click(
                        before_panel=panel_before,
                        before_switcher=switcher_before,
                        after_panel=panel_after,
                        after_switcher=switcher_after,
                        before_button=button_before,
                        after_button=button_after,
                        monitor=monitor,
                    )
                except Exception as error:
                    record_step(
                        result,
                        step=4,
                        status="failed",
                        action=AUTOMATION_STEPS[3],
                        observed=str(error),
                    )
                    raise
                record_step(
                    result,
                    step=4,
                    status="passed",
                    action=AUTOMATION_STEPS[3],
                    observed=(
                        f"panel_kind={panel_after.container_kind!r}; "
                        f"row_count={switcher_after.row_count}; "
                        f"monitor_hidden_after_visible={monitor.ever_hidden_after_visible}; "
                        f"button_disabled={button_after.disabled or button_after.aria_disabled == 'true'}."
                    ),
                )
                record_human_verification(
                    result,
                    check=(
                        "Clicked the disabled footer button like a user and watched the UI "
                        "after the click to make sure the panel did not collapse."
                    ),
                    observed=(
                        f"title_visible={'Workspace switcher' in switcher_after.switcher_text}; "
                        f"selected_workspace={_selected_workspace_name(switcher_after)!r}; "
                        f"footer_text={button_after.visible_text!r}; "
                        f"footer_disabled={button_after.disabled or button_after.aria_disabled == 'true'}; "
                        f"monitor_hidden_after_visible={monitor.ever_hidden_after_visible}; "
                        f"focus_after_click={focus_after.accessible_name!r}"
                    ),
                )
            except Exception:
                if page is not None:
                    try:
                        page.stop_transition_monitor()
                    except Exception:
                        pass
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


def _assert_switcher_open_state(
    *,
    panel: WorkspaceSwitcherPanelObservation,
    switcher: WorkspaceSwitcherObservation,
) -> None:
    failures: list[str] = []
    if panel.container_kind not in {"anchored-panel", "surface"}:
        failures.append(
            f"container_kind was {panel.container_kind!r} instead of an anchored desktop panel",
        )
    if panel.background_dimmed:
        failures.append("the workspace switcher dimmed the background like a modal")
    if switcher.row_count <= 0:
        failures.append("no visible saved workspace rows were rendered")
    if "Workspace switcher" not in switcher.switcher_text:
        failures.append('the visible "Workspace switcher" heading was missing')
    if failures:
        raise AssertionError(
            "Step 1 failed: the live app did not expose the expected pristine desktop "
            "workspace switcher surface.\n"
            + "\n".join(f"- {failure}" for failure in failures)
            + "\n"
            + f"Observed panel: {json.dumps(asdict(panel), indent=2)}\n"
            + f"Observed switcher text:\n{switcher.switcher_text}"
        )


def _assert_disabled_save_button(
    observation: WorkspaceSwitcherButtonStateObservation,
) -> None:
    if observation.visible_text != LAST_INTERNAL_CONTROL_LABEL and observation.label != LAST_INTERNAL_CONTROL_LABEL:
        raise AssertionError(
            "Step 2 failed: the visible footer control did not expose the expected "
            "Save and switch label.\n"
            f"Observed label={observation.label!r}\n"
            f"Observed text={observation.visible_text!r}\n"
            f"Observed outer HTML={observation.outer_html!r}",
        )
    if observation.aria_disabled == "true" or observation.disabled:
        return
    raise AssertionError(
        "Step 2 failed: the visible Save and switch footer control was not disabled in "
        "pristine state.\n"
        f"Observed aria-disabled={observation.aria_disabled!r}\n"
        f"Observed disabled={observation.disabled}\n"
        f"Observed outer HTML={observation.outer_html!r}",
    )


def _assert_click_target(observation: WorkspaceSwitcherInternalClickObservation) -> None:
    failures: list[str] = []
    if observation.click_x <= 0 or observation.click_y <= 0:
        failures.append("the resolved pointer click coordinates were invalid")
    target_matches = LAST_INTERNAL_CONTROL_LABEL in {
        observation.target_label,
        observation.target_text,
    }
    if not target_matches:
        failures.append(
            "the pointer click did not target the visible Save and switch button surface",
        )
    if failures:
        raise AssertionError(
            "Step 3 failed: the test could not click the disabled Save and switch footer "
            "button with a real pointer target.\n"
            + "\n".join(f"- {failure}" for failure in failures)
            + "\n"
            + f"Observed click target: {json.dumps(asdict(observation), indent=2)}"
        )


def _assert_switcher_remains_open_after_click(
    *,
    before_panel: WorkspaceSwitcherPanelObservation,
    before_switcher: WorkspaceSwitcherObservation,
    after_panel: WorkspaceSwitcherPanelObservation,
    after_switcher: WorkspaceSwitcherObservation,
    before_button: WorkspaceSwitcherButtonStateObservation,
    after_button: WorkspaceSwitcherButtonStateObservation,
    monitor: WorkspaceSwitcherTransitionMonitorObservation,
) -> None:
    failures: list[str] = []
    if after_panel.container_kind not in {"anchored-panel", "surface"}:
        failures.append(
            f"container_kind became {after_panel.container_kind!r} instead of staying a desktop panel",
        )
    if after_panel.background_dimmed:
        failures.append("the switcher became background-dimmed after the click")
    if "Workspace switcher" not in after_switcher.switcher_text:
        failures.append('the visible "Workspace switcher" heading disappeared after the click')
    if after_switcher.row_count <= 0:
        failures.append("the switcher no longer exposed any visible workspace rows after the click")
    if after_switcher.row_count != before_switcher.row_count:
        failures.append(
            f"the visible workspace row count changed from {before_switcher.row_count} to {after_switcher.row_count}",
        )
    if _selected_workspace_name(after_switcher) != _selected_workspace_name(before_switcher):
        failures.append(
            "the selected workspace changed even though the disabled footer button was clicked",
        )
    if after_button.visible_text != LAST_INTERNAL_CONTROL_LABEL:
        failures.append(
            f"the footer button text changed to {after_button.visible_text!r}",
        )
    if after_button.aria_disabled != "true" and not after_button.disabled:
        failures.append("the footer button stopped reporting a disabled state after the click")
    if before_button.visible_text != after_button.visible_text:
        failures.append(
            f"the footer button label changed from {before_button.visible_text!r} to "
            f"{after_button.visible_text!r}",
        )
    if after_panel.container_kind != before_panel.container_kind:
        failures.append(
            f"the panel kind changed from {before_panel.container_kind!r} to {after_panel.container_kind!r}",
        )
    if monitor.ever_hidden_after_visible:
        failures.append("the transition monitor observed the panel become hidden after the click")
    if monitor.visible_sample_count <= 0:
        failures.append("the transition monitor captured no visible switcher samples after the click")
    if failures:
        raise AssertionError(
            "Step 4 failed: clicking the disabled Save and switch footer button did not "
            "leave the workspace switcher visibly open.\n"
            + "\n".join(f"- {failure}" for failure in failures)
            + "\n"
            + f"Observed after-panel: {json.dumps(asdict(after_panel), indent=2)}\n"
            + f"Observed transition monitor: {json.dumps(_monitor_payload(monitor), indent=2)}\n"
            + f"Observed switcher text after click:\n{after_switcher.switcher_text}"
        )


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


def _selected_workspace_name(switcher: WorkspaceSwitcherObservation) -> str | None:
    for row in switcher.rows:
        if row.selected:
            return row.display_name
    return None


def _switcher_payload(observation: WorkspaceSwitcherObservation) -> dict[str, object]:
    return {
        "row_count": observation.row_count,
        "selected_workspace": _selected_workspace_name(observation),
        "switcher_text": observation.switcher_text,
        "rows": [asdict(row) for row in observation.rows],
    }


def _button_payload(
    observation: WorkspaceSwitcherButtonStateObservation,
) -> dict[str, object]:
    return {
        "label": observation.label,
        "visible_text": observation.visible_text,
        "role": observation.role,
        "tag_name": observation.tag_name,
        "tabindex": observation.tabindex,
        "tab_index_value": observation.tab_index_value,
        "aria_disabled": observation.aria_disabled,
        "disabled": observation.disabled,
        "keyboard_focusable": observation.keyboard_focusable,
        "active_within": observation.active_within,
        "outer_html": observation.outer_html,
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


def _compact_html(value: str, *, limit: int = 280) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit].rstrip()}..."


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
    error = str(result.get("error", "AssertionError: TS-1008 failed"))
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
            "Clicked the disabled `Save and switch` footer button in pristine state and "
            "the live workspace switcher stayed visibly open: the heading, saved "
            "workspace rows, and disabled footer control all remained on screen, and the "
            "transition monitor never observed the panel hide."
        )
    return str(result.get("error", "TS-1008 failed."))


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
                    "status": "failed",
                    "action": REQUEST_STEPS[0],
                    "observed": str(result.get("error", "")),
                },
            ],
        },
        request_steps=REQUEST_STEPS,
    )
    actual_details = _actual_failure_details(result)
    screenshot = result.get("screenshot", "No screenshot captured.")
    return "\n".join(
        [
            f"# {TICKET_KEY}: Clicking disabled Save and switch collapses or destabilizes the pristine workspace switcher",
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
            actual_details,
            "",
            "## Expected result",
            EXPECTED_RESULT,
            "",
            "## Environment",
            f"- {_environment_summary(result)}",
            "",
            "## Evidence",
            f"- Screenshot: {screenshot}",
            f"- Focus before click: {json.dumps(result.get('focused_before_click', {}), indent=2)}",
            f"- Focus after click: {json.dumps(result.get('focused_after_click', {}), indent=2)}",
            f"- Transition monitor: {json.dumps(result.get('monitor_after_click', {}), indent=2)}",
            f"- Button before click: {json.dumps(result.get('button_before_click', {}), indent=2)}",
            f"- Button after click: {json.dumps(result.get('button_after_click', {}), indent=2)}",
        ],
    ) + "\n"


def _actual_failure_details(result: dict[str, object]) -> str:
    monitor = json.dumps(result.get("monitor_after_click", {}), indent=2)
    button_after = json.dumps(result.get("button_after_click", {}), indent=2)
    return (
        "After clicking the disabled `Save and switch` footer button in the live pristine "
        "workspace switcher, the observed behavior did not match the expected internal-click "
        "handling. "
        + str(result.get("error", ""))
        + "\n\nObserved transition monitor:\n"
        + monitor
        + "\n\nObserved footer state after click:\n"
        + button_after
    )


if __name__ == "__main__":
    main()
