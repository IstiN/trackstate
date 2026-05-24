from __future__ import annotations

from dataclasses import asdict
import json
import platform
import sys
import traceback
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
TEST_DIR = Path(__file__).resolve().parent
if str(TEST_DIR) not in sys.path:
    sys.path.insert(0, str(TEST_DIR))
TS_983_DIR = REPO_ROOT / "testing/tests/TS-983"
if str(TS_983_DIR) not in sys.path:
    sys.path.insert(0, str(TS_983_DIR))

from testing.components.pages.live_startup_recovery_page import (  # noqa: E402
    LiveStartupRecoveryPage,
    StartupRecoverySurfaceObservation,
)
from testing.components.pages.live_workspace_switcher_page import (  # noqa: E402
    LiveWorkspaceSwitcherPage,
    WorkspaceSwitcherButtonStateObservation,
    WorkspaceSwitcherObservation,
    WorkspaceSwitcherRowObservation,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.interfaces.web_app_session import WebAppTimeoutError  # noqa: E402
from testing.core.utils.polling import poll_until  # noqa: E402
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
from support.ts983_startup_retry_runtime import Ts983StartupRetryRuntime  # noqa: E402

TICKET_KEY = "TS-1023"
TEST_CASE_TITLE = (
    "Retry sync recovery restores Save and switch visibility and reactivity"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-1023/test_ts_1023.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
BLOCKED_BOOTSTRAP_PATH = "DEMO/.trackstate/index/tombstones.json"
LINKED_BUGS = ["TS-1018", "TS-1026", "TS-1028"]
RECOVERY_ACTION_LABELS = ("Sync issue", "Retry")
SHELL_NAVIGATION_LABELS = ("Dashboard", "Board", "JQL Search", "Hierarchy", "Settings")
REQUEST_STEPS = [
    "Click the Retry button in the workspace switcher panel.",
    "Wait for the synchronization to complete and the workspace list to populate.",
    "Verify that both Add workspace and Save and switch are visible in the footer.",
    "Select a workspace row other than the current selection.",
]
EXPECTED_RESULT = (
    "The Save and switch button is visible and transitions to an enabled state "
    "when a new workspace is selected, confirming that the footer state has "
    "been fully refreshed and the reactive state pattern is active following "
    "the recovery."
)
DEFAULT_BRANCH = "main"
FIRST_WORKSPACE_DISPLAY_NAME = "TrackState setup (main)"
SECOND_WORKSPACE_DISPLAY_NAME = "TrackState setup (retry target)"
SECOND_WORKSPACE_WRITE_BRANCH = "ts-1023-retry-target"
SURFACE_TIMEOUT_MS = 10_000
RECOVERY_TIMEOUT_SECONDS = 120
SWITCHER_TIMEOUT_SECONDS = 120
BUTTON_ENABLE_TIMEOUT_SECONDS = 30
SUCCESS_SCREENSHOT_NAME = "ts1023_success.png"
FAILURE_SCREENSHOT_NAME = "ts1023_failure.png"
INFRASTRUCTURE_ERROR_PREFIXES = (
    "RuntimeError:",
    "ModuleNotFoundError:",
    "ImportError:",
    "SyntaxError:",
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / SUCCESS_SCREENSHOT_NAME
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / FAILURE_SCREENSHOT_NAME


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-1023 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
        )

    runtime = Ts983StartupRetryRuntime(
        repository=config.repository,
        token=token,
        workspace_state=_workspace_state(service.repository),
        blocked_path=BLOCKED_BOOTSTRAP_PATH,
        workspace_token_profile_ids=_workspace_profile_ids(service.repository),
    )
    result: dict[str, Any] = {
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
        "blocked_bootstrap_path": BLOCKED_BOOTSTRAP_PATH,
        "preloaded_workspace_state": _workspace_state(service.repository),
        "steps": [],
        "human_verification": [],
    }

    page: LiveWorkspaceSwitcherPage | None = None
    try:
        with create_live_tracker_app(
            config,
            runtime_factory=lambda: runtime,
        ) as tracker_page:
            page = LiveWorkspaceSwitcherPage(tracker_page)
            startup_page = LiveStartupRecoveryPage(tracker_page)
            try:
                startup_page.open()
                page.set_viewport(**DESKTOP_VIEWPORT)

                recovery_ready, recovery_surface = poll_until(
                    probe=lambda: startup_page.observe_recovery_surface(
                        accepted_action_labels=RECOVERY_ACTION_LABELS,
                    ),
                    is_satisfied=lambda observation: isinstance(
                        observation,
                        StartupRecoverySurfaceObservation,
                    )
                    and observation.visible_action_label is not None,
                    timeout_seconds=RECOVERY_TIMEOUT_SECONDS,
                    interval_seconds=1,
                )
                result["recovery_surface_before_retry"] = _recovery_surface_payload(
                    recovery_surface,
                )
                result["blocked_requests_before_retry"] = [
                    asdict(request) for request in runtime.blocked_requests
                ]
                if not recovery_ready:
                    record_step(
                        result,
                        step=1,
                        status="failed",
                        action=REQUEST_STEPS[0],
                        observed=(
                            "The deployed app never exposed a visible Retry action in the "
                            "startup recovery surface.\n"
                            f"Observed recovery surface: "
                            f"{json.dumps(_recovery_surface_payload(recovery_surface), indent=2)}"
                        ),
                    )
                    record_not_reached_steps(
                        result,
                        starting_step=2,
                        request_steps=REQUEST_STEPS,
                    )
                    raise AssertionError(
                        "Step 1 failed: the live app never exposed the startup Retry action "
                        "needed for TS-1023.\n"
                        f"Observed recovery surface:\n"
                        f"{json.dumps(_recovery_surface_payload(recovery_surface), indent=2)}",
                    )
                if len(runtime.blocked_requests) == 0:
                    record_step(
                        result,
                        step=1,
                        status="failed",
                        action=REQUEST_STEPS[0],
                        observed=(
                            "The synthetic startup block for DEMO/project.json was never "
                            "observed before the recovery action appeared."
                        ),
                    )
                    record_not_reached_steps(
                        result,
                        starting_step=2,
                        request_steps=REQUEST_STEPS,
                    )
                    raise AssertionError(
                        "Precondition failed: the synthetic startup fetch block for "
                        f"{BLOCKED_BOOTSTRAP_PATH} never executed before Retry became visible.",
                    )

                runtime.enable_retry_success()
                clicked_action_label = startup_page.click_recovery_action(
                    accepted_action_labels=RECOVERY_ACTION_LABELS,
                )
                record_step(
                    result,
                    step=1,
                    status="passed",
                    action=REQUEST_STEPS[0],
                    observed=(
                        f"visible_action_label={recovery_surface.visible_action_label!r}; "
                        f"clicked_action_label={clicked_action_label!r}; "
                        f"blocked_request_count={len(runtime.blocked_requests)}; "
                        f"surface_text={recovery_surface.surface_text!r}"
                    ),
                )
                record_human_verification(
                    result,
                    check=(
                        "Viewed the startup Sync issue recovery surface and used the visible "
                        "Retry action exactly as a user would."
                    ),
                    observed=(
                        f"visible_buttons={list(recovery_surface.visible_button_labels)!r}; "
                        f"surface_text={recovery_surface.surface_text!r}"
                    ),
                )

                shell_ready, shell_observation = poll_until(
                    probe=lambda: tracker_page.observe_interactive_shell(
                        SHELL_NAVIGATION_LABELS,
                    ),
                    is_satisfied=lambda observation: bool(observation.get("shell_ready")),
                    timeout_seconds=RECOVERY_TIMEOUT_SECONDS,
                    interval_seconds=1,
                )
                result["shell_observation_after_retry"] = shell_observation
                result["successful_retry_requests"] = [
                    asdict(request) for request in runtime.successful_retry_requests
                ]
                if not shell_ready:
                    record_step(
                        result,
                        step=2,
                        status="failed",
                        action=REQUEST_STEPS[1],
                        observed=(
                            "The live app never returned to the interactive shell after Retry.\n"
                            f"Observed shell state: {json.dumps(shell_observation, indent=2)}"
                        ),
                    )
                    record_not_reached_steps(
                        result,
                        starting_step=3,
                        request_steps=REQUEST_STEPS,
                    )
                    raise AssertionError(
                        "Step 2 failed: Retry did not restore the interactive shell.\n"
                        f"Observed shell state:\n{json.dumps(shell_observation, indent=2)}",
                    )
                switcher_ready, switcher_observation = poll_until(
                    probe=lambda: _open_workspace_switcher(page),
                    is_satisfied=_switcher_populated_with_multiple_rows,
                    timeout_seconds=SWITCHER_TIMEOUT_SECONDS,
                    interval_seconds=1,
                )
                result["workspace_switcher_after_retry"] = _switcher_payload(
                    switcher_observation,
                )
                if not switcher_ready:
                    record_step(
                        result,
                        step=2,
                        status="failed",
                        action=REQUEST_STEPS[1],
                        observed=(
                            "Retry restored the shell, but the workspace switcher never "
                            "showed at least two saved workspace rows.\n"
                            f"Observed switcher state: "
                            f"{json.dumps(_switcher_payload(switcher_observation), indent=2)}"
                        ),
                    )
                    record_not_reached_steps(
                        result,
                        starting_step=3,
                        request_steps=REQUEST_STEPS,
                    )
                    raise AssertionError(
                        "Step 2 failed: the workspace list did not populate with at least two "
                        "saved workspaces after Retry.\n"
                        f"Observed switcher state:\n"
                        f"{json.dumps(_switcher_payload(switcher_observation), indent=2)}",
                    )

                recovered_row_names = _row_names(switcher_observation)
                record_step(
                    result,
                    step=2,
                    status="passed",
                    action=REQUEST_STEPS[1],
                    observed=(
                        f"shell_ready={shell_observation.get('shell_ready')!r}; "
                        f"successful_retry_request_count={len(runtime.successful_retry_requests)}; "
                        f"row_count={switcher_observation.row_count}; "
                        f"row_names={recovered_row_names!r}"
                    ),
                )
                record_human_verification(
                    result,
                    check=(
                        "Opened the recovered workspace switcher and read the visible saved "
                        "workspace entries the same way a user would after Retry completed."
                    ),
                    observed=(
                        f"row_names={recovered_row_names!r}; "
                        f"text_excerpt={snippet(switcher_observation.switcher_text)!r}"
                    ),
                )

                add_workspace_button = page.observe_switcher_button_state(
                    "Add workspace",
                    timeout_ms=SURFACE_TIMEOUT_MS,
                )
                save_button_before = page.observe_switcher_button_state(
                    "Save and switch",
                    timeout_ms=SURFACE_TIMEOUT_MS,
                )
                result["footer_buttons_before_selection"] = {
                    "add_workspace": _button_payload(add_workspace_button),
                    "save_and_switch": _button_payload(save_button_before),
                }
                _assert_visible_footer_controls(
                    add_workspace_button=add_workspace_button,
                    save_button=save_button_before,
                )
                _assert_save_button_disabled(save_button_before)
                current_row = _current_row(switcher_observation)
                target_row = _different_workspace_row(
                    switcher_observation,
                    current_row=current_row,
                )
                result["current_workspace_before_selection"] = _row_payload(current_row)
                result["target_workspace_for_selection"] = _row_payload(target_row)
                record_step(
                    result,
                    step=3,
                    status="passed",
                    action=REQUEST_STEPS[2],
                    observed=(
                        f"add_workspace_visible_text={add_workspace_button.visible_text!r}; "
                        f"save_and_switch_visible_text={save_button_before.visible_text!r}; "
                        f"save_and_switch_aria_disabled={save_button_before.aria_disabled!r}; "
                        f"save_and_switch_disabled={save_button_before.disabled}; "
                        f"current_workspace={current_row.display_name!r}; "
                        f"selection_target={target_row.display_name!r}"
                    ),
                )
                record_human_verification(
                    result,
                    check=(
                        "Viewed the footer after recovery and confirmed both footer controls "
                        "were visible in the correct place before changing the workspace "
                        "selection."
                    ),
                    observed=(
                        f"add_workspace_html={_compact_html(add_workspace_button.outer_html)!r}; "
                        f"save_and_switch_html={_compact_html(save_button_before.outer_html)!r}"
                    ),
                )

                enabled_observation: dict[str, Any] = {}
                transition_monitor = None
                page.start_transition_monitor()
                try:
                    click_observation = page.click_saved_workspace_row_surface(
                        target_row.display_name,
                        timeout_ms=SURFACE_TIMEOUT_MS,
                    )
                    result["row_click_observation"] = _row_click_payload(click_observation)
                    _assert_clicked_different_workspace(
                        click_observation=click_observation,
                        target_row=target_row,
                        current_row=current_row,
                    )
                    enabled_ready, enabled_observation = poll_until(
                        probe=lambda: _observe_save_button_after_selection(page),
                        is_satisfied=lambda observation: bool(observation["button_enabled"]),
                        timeout_seconds=BUTTON_ENABLE_TIMEOUT_SECONDS,
                        interval_seconds=1,
                    )
                    transition_monitor = _try_read_transition_monitor(page)
                    result["transition_monitor_after_selection"] = (
                        _transition_monitor_payload(transition_monitor)
                        if transition_monitor is not None
                        else {}
                    )
                    result["save_button_after_selection"] = enabled_observation
                    if not enabled_ready:
                        raise AssertionError(
                            "Step 4 failed: selecting a different saved workspace row did not "
                            "enable Save and switch.\n"
                            f"Observed post-selection state:\n"
                            f"{json.dumps(enabled_observation, indent=2)}",
                        )
                except Exception as error:
                    transition_monitor = _try_read_transition_monitor(page)
                    result["transition_monitor_after_selection"] = (
                        _transition_monitor_payload(transition_monitor)
                        if transition_monitor is not None
                        else {}
                    )
                    if not enabled_observation:
                        enabled_observation = _observe_save_button_after_selection(page)
                    result["save_button_after_selection"] = enabled_observation
                    record_step(
                        result,
                        step=4,
                        status="failed",
                        action=REQUEST_STEPS[3],
                        observed=(
                            f"clicked_workspace={target_row.display_name!r}; "
                            f"row_click_observation={json.dumps(result.get('row_click_observation', {}), indent=2)}\n"
                            f"{error}\n"
                            f"Observed post-selection state: {json.dumps(enabled_observation, indent=2)}"
                        ),
                    )
                    raise
                finally:
                    _try_stop_transition_monitor(page)

                record_step(
                    result,
                    step=4,
                    status="passed",
                    action=REQUEST_STEPS[3],
                    observed=(
                        f"clicked_workspace={target_row.display_name!r}; "
                        f"save_and_switch_label={enabled_observation['save_button']['label']!r}; "
                        f"save_and_switch_aria_disabled={enabled_observation['save_button']['aria_disabled']!r}; "
                        f"save_and_switch_disabled={enabled_observation['save_button']['disabled']}; "
                        f"monitor_hidden_after_visible="
                        f"{result['transition_monitor_after_selection'].get('ever_hidden_after_visible')!r}"
                    ),
                )
                record_human_verification(
                    result,
                    check=(
                        "Selected a different recovered workspace row and checked that the "
                        "footer button state updated from disabled to enabled."
                    ),
                    observed=(
                        f"clicked_workspace={target_row.display_name!r}; "
                        f"save_button_visible_text={enabled_observation['save_button']['visible_text']!r}; "
                        f"save_button_enabled={enabled_observation['button_enabled']}; "
                        f"switcher_text_excerpt={snippet(enabled_observation['switcher']['switcher_text'])!r}"
                    ),
                )

                tracker_page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
                _write_pass_outputs(result)
                print(f"{TICKET_KEY} passed")
                return
            except Exception:
                tracker_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                raise
    except Exception as error:
        if not result.get("steps"):
            record_not_reached_steps(
                result,
                starting_step=1,
                request_steps=REQUEST_STEPS,
            )
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        result.setdefault(
            "blocked_requests_before_retry",
            [asdict(request) for request in runtime.blocked_requests],
        )
        result.setdefault(
            "successful_retry_requests",
            [asdict(request) for request in runtime.successful_retry_requests],
        )
        _write_failure_outputs(result)
        raise


def _workspace_profile_ids(repository: str) -> tuple[str, ...]:
    first_id = f"hosted:{repository.lower()}@{DEFAULT_BRANCH}"
    second_id = f"hosted:{repository.lower()}@{DEFAULT_BRANCH}:{SECOND_WORKSPACE_WRITE_BRANCH}"
    return (first_id, second_id)


def _workspace_state(repository: str) -> dict[str, object]:
    first_id, second_id = _workspace_profile_ids(repository)
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
                "lastOpenedAt": "2026-05-24T00:10:00.000Z",
                "hostedAccessMode": "attachmentRestricted",
            },
            {
                "id": second_id,
                "displayName": SECOND_WORKSPACE_DISPLAY_NAME,
                "customDisplayName": SECOND_WORKSPACE_DISPLAY_NAME,
                "targetType": "hosted",
                "target": repository,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": SECOND_WORKSPACE_WRITE_BRANCH,
                "lastOpenedAt": "2026-05-24T00:00:00.000Z",
                "hostedAccessMode": "attachmentRestricted",
            },
        ],
    }


def _open_workspace_switcher(
    page: LiveWorkspaceSwitcherPage,
) -> WorkspaceSwitcherObservation:
    try:
        return page.observe_open_switcher(timeout_ms=2_000)
    except (AssertionError, WebAppTimeoutError):
        return page.open_and_observe(timeout_ms=30_000)


def _switcher_populated_with_multiple_rows(observation: object) -> bool:
    return isinstance(observation, WorkspaceSwitcherObservation) and len(
        [row for row in observation.rows if row.display_name],
    ) >= 2


def _row_names(observation: WorkspaceSwitcherObservation) -> list[str]:
    return [row.display_name for row in observation.rows if row.display_name]


def _current_row(observation: WorkspaceSwitcherObservation) -> WorkspaceSwitcherRowObservation:
    current_rows = [row for row in observation.rows if row.selected and row.display_name]
    if len(current_rows) != 1:
        raise AssertionError(
            "Step 3 failed: the recovered workspace switcher did not expose exactly one "
            "current workspace row before selecting a new workspace.\n"
            f"Observed rows:\n{json.dumps(_switcher_payload(observation), indent=2)}",
        )
    return current_rows[0]


def _different_workspace_row(
    observation: WorkspaceSwitcherObservation,
    *,
    current_row: WorkspaceSwitcherRowObservation,
) -> WorkspaceSwitcherRowObservation:
    candidates = [
        row
        for row in observation.rows
        if row.display_name and row.display_name != current_row.display_name
    ]
    if not candidates:
        raise AssertionError(
            "Step 3 failed: the recovered workspace switcher did not expose a second saved "
            "workspace row to select.\n"
            f"Observed rows:\n{json.dumps(_switcher_payload(observation), indent=2)}",
        )
    return candidates[0]


def _assert_visible_footer_controls(
    *,
    add_workspace_button: WorkspaceSwitcherButtonStateObservation,
    save_button: WorkspaceSwitcherButtonStateObservation,
) -> None:
    failures: list[str] = []
    if add_workspace_button.visible_text != "Add workspace" and add_workspace_button.label != "Add workspace":
        failures.append(
            f'Add workspace visible label was {add_workspace_button.visible_text!r} / {add_workspace_button.label!r}.',
        )
    if save_button.visible_text != "Save and switch" and save_button.label != "Save and switch":
        failures.append(
            f'Save and switch visible label was {save_button.visible_text!r} / {save_button.label!r}.',
        )
    if failures:
        raise AssertionError(
            "Step 3 failed: the recovered workspace switcher footer did not expose the "
            "expected visible controls.\n"
            + "\n".join(f"- {failure}" for failure in failures)
        )


def _assert_save_button_disabled(
    observation: WorkspaceSwitcherButtonStateObservation,
) -> None:
    if observation.aria_disabled == "true" or observation.disabled:
        return
    raise AssertionError(
        "Step 3 failed: Save and switch was visible after recovery but it was not disabled "
        "before selecting a different workspace row.\n"
        f"Observed aria-disabled={observation.aria_disabled!r}\n"
        f"Observed disabled={observation.disabled}\n"
        f"Observed outer HTML={observation.outer_html!r}",
    )


def _assert_clicked_different_workspace(
    *,
    click_observation: Any,
    target_row: WorkspaceSwitcherRowObservation,
    current_row: WorkspaceSwitcherRowObservation,
) -> None:
    failures: list[str] = []
    if click_observation.display_name != target_row.display_name:
        failures.append(
            f"clicked display_name was {click_observation.display_name!r} instead of {target_row.display_name!r}",
        )
    if target_row.display_name == current_row.display_name:
        failures.append("the chosen target row matched the current workspace row")
    if click_observation.click_x <= 0 or click_observation.click_y <= 0:
        failures.append("the resolved row click coordinates were invalid")
    if failures:
        raise AssertionError(
            "Step 4 failed: the test did not click a valid different workspace row.\n"
            + "\n".join(f"- {failure}" for failure in failures)
            + "\n"
            + f"Observed click target: {json.dumps(_row_click_payload(click_observation), indent=2)}"
        )


def _observe_save_button_after_selection(
    page: LiveWorkspaceSwitcherPage,
) -> dict[str, Any]:
    state: dict[str, Any] = {
        "button_enabled": False,
        "switcher": {},
        "save_button": {},
        "body_text": "",
        "error": None,
        "transition_hidden_after_visible": None,
    }
    try:
        switcher = _open_workspace_switcher(page)
        save_button = page.observe_switcher_button_state(
            "Save and switch",
            timeout_ms=2_000,
        )
        transition_monitor = _try_read_transition_monitor(page)
        state["switcher"] = _switcher_payload(switcher)
        state["save_button"] = _button_payload(save_button)
        state["button_enabled"] = _button_is_enabled(save_button)
        state["transition_hidden_after_visible"] = (
            transition_monitor.ever_hidden_after_visible
            if transition_monitor is not None
            else None
        )
        return state
    except Exception as error:
        state["body_text"] = page.current_body_text()
        state["error"] = f"{type(error).__name__}: {error}"
        return state


def _button_is_enabled(observation: WorkspaceSwitcherButtonStateObservation) -> bool:
    return not observation.disabled and observation.aria_disabled != "true"


def _recovery_surface_payload(
    observation: StartupRecoverySurfaceObservation,
) -> dict[str, object]:
    return {
        "body_text": observation.body_text,
        "surface_text": observation.surface_text,
        "visible_buttons": list(observation.visible_button_labels),
        "visible_action_label": observation.visible_action_label,
        "connect_github_visible": observation.connect_github_visible,
        "container_tag_name": observation.container_tag_name,
        "container_role": observation.container_role,
    }


def _switcher_payload(switcher: WorkspaceSwitcherObservation) -> dict[str, object]:
    return {
        "body_text": switcher.body_text,
        "switcher_text": switcher.switcher_text,
        "row_count": switcher.row_count,
        "rows": [_row_payload(row) for row in switcher.rows],
    }


def _row_payload(row: WorkspaceSwitcherRowObservation) -> dict[str, object]:
    return {
        "display_name": row.display_name,
        "target_type_label": row.target_type_label,
        "state_label": row.state_label,
        "detail_text": row.detail_text,
        "visible_text": row.visible_text,
        "selected": row.selected,
        "action_labels": list(row.action_labels),
        "button_labels": list(row.button_labels),
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


def _row_click_payload(observation: Any) -> dict[str, object]:
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


def _transition_monitor_payload(observation: Any) -> dict[str, object]:
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


def _try_read_transition_monitor(page: LiveWorkspaceSwitcherPage) -> Any | None:
    try:
        return page.read_transition_monitor(clear=False)
    except (AssertionError, WebAppTimeoutError):
        return None


def _try_stop_transition_monitor(page: LiveWorkspaceSwitcherPage | None) -> None:
    if page is None:
        return
    try:
        page.stop_transition_monitor()
    except (AssertionError, WebAppTimeoutError):
        return


def _write_pass_outputs(result: dict[str, Any]) -> None:
    BUG_DESCRIPTION_PATH.unlink(missing_ok=True)
    write_test_automation_result(RESULT_PATH, passed=True)
    JIRA_COMMENT_PATH.write_text(_jira_comment(result, passed=True), encoding="utf-8")
    PR_BODY_PATH.write_text(_pr_body(result, passed=True), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_summary(result, passed=True), encoding="utf-8")


def _write_failure_outputs(result: dict[str, Any]) -> None:
    error = str(result.get("error", "AssertionError: TS-1023 failed"))
    write_test_automation_result(RESULT_PATH, passed=False, error=error)
    JIRA_COMMENT_PATH.write_text(_jira_comment(result, passed=False), encoding="utf-8")
    PR_BODY_PATH.write_text(_pr_body(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_summary(result, passed=False), encoding="utf-8")
    if _is_product_failure(result):
        BUG_DESCRIPTION_PATH.write_text(_bug_description(result), encoding="utf-8")
    else:
        BUG_DESCRIPTION_PATH.unlink(missing_ok=True)


def _is_product_failure(result: dict[str, Any]) -> bool:
    error = str(result.get("error", ""))
    if not error:
        return False
    return not error.startswith(INFRASTRUCTURE_ERROR_PREFIXES)


def _environment_summary(result: dict[str, Any]) -> str:
    return (
        f"URL={result.get('app_url')} | Browser={result.get('browser')} | "
        f"OS={result.get('os')} | Viewport={DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}"
    )


def _result_summary(result: dict[str, Any], *, passed: bool) -> str:
    if passed:
        current_workspace = result.get("current_workspace_before_selection", {})
        target_workspace = result.get("target_workspace_for_selection", {})
        save_after = result.get("save_button_after_selection", {})
        save_state = save_after.get("save_button", {}) if isinstance(save_after, dict) else {}
        return (
            "Retry recovered the live workspace switcher footer. "
            f"Current workspace before selection={current_workspace.get('display_name')!r}; "
            f"clicked workspace={target_workspace.get('display_name')!r}; "
            f"Save and switch visible after recovery and enabled after selection "
            f"(aria-disabled={save_state.get('aria_disabled')!r}, disabled={save_state.get('disabled')!r})."
        )
    return (
        "The live deployment did not satisfy the retry recovery footer reactivity "
        "expected by TS-1023. See the failed step annotations and captured DOM "
        "observations for the exact break point."
    )


def _actual_failure_summary(result: dict[str, Any]) -> str:
    save_after = result.get("save_button_after_selection", {})
    if isinstance(save_after, dict):
        save_button = save_after.get("save_button", {})
        switcher = save_after.get("switcher", {})
        rows = switcher.get("rows", []) if isinstance(switcher, dict) else []
        selected_row = next(
            (
                row.get("display_name")
                for row in rows
                if isinstance(row, dict) and bool(row.get("selected"))
            ),
            None,
        )
        target_workspace = result.get("target_workspace_for_selection", {})
        if isinstance(save_button, dict):
            return (
                f"*Actual*: After clicking "
                f"{target_workspace.get('display_name', '<unknown>')!r}, "
                f"the active workspace remained {selected_row!r} and *Save and switch* "
                f"stayed disabled with {{code}}aria-disabled={save_button.get('aria_disabled')!r}{{code}} "
                f"and {{code}}disabled={save_button.get('disabled')!r}{{code}}."
            )
    return (
        "*Actual*: The live retry recovery flow did not restore the workspace "
        "switcher footer and reactive Save and switch behavior exactly as the "
        "ticket requires."
    )


def _jira_comment(result: dict[str, Any], *, passed: bool) -> str:
    status = "✅ PASSED" if passed else "❌ FAILED"
    lines = [
        "h3. Test Automation Result",
        "",
        f"*Ticket:* {TICKET_KEY}",
        f"*Status:* {status}",
        f"*Test case:* {TEST_CASE_TITLE}",
        f"*Expected result:* {EXPECTED_RESULT}",
        f"*Environment:* {{code}}{_environment_summary(result)}{{code}}",
        f"*Linked bugs covered:* {', '.join(result.get('linked_bugs', []))}",
        (
            f"*Blocked startup path:* {{code}}{result.get('blocked_bootstrap_path')}{{code}} | "
            f"*Run command:* {{code}}{RUN_COMMAND}{{code}}"
        ),
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
    if not passed:
        lines.extend(
            [
                "",
                "h4. Failure details",
                f"*Error:* {{code}}{result.get('error', '')}{{code}}",
            ],
        )
    return "\n".join(lines) + "\n"


def _pr_body(result: dict[str, Any], *, passed: bool) -> str:
    status = "PASSED" if passed else "FAILED"
    lines = [
        f"## {status} - {TICKET_KEY}",
        "",
        f"**Test case:** {TEST_CASE_TITLE}",
        f"**Expected result:** {EXPECTED_RESULT}",
        f"**Environment:** {_environment_summary(result).replace(' | ', ' · ')}",
        f"**Linked bugs covered:** {', '.join(result.get('linked_bugs', []))}",
        f"**Blocked startup path:** `{result.get('blocked_bootstrap_path')}`",
        "",
        "### Automated verification",
        *format_step_lines(result, jira=False),
        "",
        "### Real user-style verification",
        *format_human_lines(result, jira=False),
        "",
        "### Observed result",
        "",
        _result_summary(result, passed=passed),
    ]
    screenshot = result.get("screenshot")
    if screenshot:
        lines.extend(["", f"**Screenshot:** `{screenshot}`"])
    if not passed:
        lines.extend(
            [
                "",
                "### Failure details",
                "",
                "```text",
                str(result.get("error", "")),
                "```",
            ],
        )
    return "\n".join(lines) + "\n"


def _response_summary(result: dict[str, Any], *, passed: bool) -> str:
    return _pr_body(result, passed=passed)


def _bug_description(result: dict[str, Any]) -> str:
    lines = [
        f"h2. {TICKET_KEY} automated regression failure",
        "",
        "h3. Steps to reproduce",
        *build_annotated_steps(result, request_steps=REQUEST_STEPS),
        "",
        "h3. Exact error message / assertion failure",
        "{code}",
        str(result.get("traceback", result.get("error", ""))),
        "{code}",
        "",
        "h3. Actual vs Expected",
        f"*Expected*: {EXPECTED_RESULT}",
        _actual_failure_summary(result),
        "",
        "h3. Environment",
        f"* URL: {result.get('app_url')}",
        f"* Browser: {result.get('browser')}",
        f"* OS: {result.get('os')}",
        f"* Viewport: {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
        f"* Repository: {result.get('repository')} @ {result.get('repository_ref')}",
        f"* Blocked startup path: {result.get('blocked_bootstrap_path')}",
        "",
        "h3. Logs / screenshots",
        f"* Screenshot: {result.get('screenshot', '')}",
        "{code}",
        json.dumps(
            {
                "blocked_requests_before_retry": result.get("blocked_requests_before_retry", []),
                "successful_retry_requests": result.get("successful_retry_requests", []),
                "recovery_surface_before_retry": result.get("recovery_surface_before_retry", {}),
                "shell_observation_after_retry": result.get("shell_observation_after_retry", {}),
                "workspace_switcher_after_retry": result.get("workspace_switcher_after_retry", {}),
                "footer_buttons_before_selection": result.get(
                    "footer_buttons_before_selection",
                    {},
                ),
                "current_workspace_before_selection": result.get(
                    "current_workspace_before_selection",
                    {},
                ),
                "target_workspace_for_selection": result.get(
                    "target_workspace_for_selection",
                    {},
                ),
                "row_click_observation": result.get("row_click_observation", {}),
                "save_button_after_selection": result.get("save_button_after_selection", {}),
                "transition_monitor_after_selection": result.get(
                    "transition_monitor_after_selection",
                    {},
                ),
            },
            indent=2,
        ),
        "{code}",
    ]
    return "\n".join(lines) + "\n"


def _compact_html(value: str, *, limit: int = 240) -> str:
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


if __name__ == "__main__":
    main()
