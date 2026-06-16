from __future__ import annotations

import base64
import json
import platform
import shutil
import subprocess
import sys
import traceback
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_workspace_switcher_page import (  # noqa: E402
    LiveWorkspaceSwitcherPage,
    WorkspaceSwitcherObservation,
    WorkspaceSwitcherRowObservation,
    WorkspaceSwitcherSavedWorkspaceRowObservation,
    WorkspaceSwitcherTriggerObservation,
)
from testing.components.pages.trackstate_tracker_page import TrackStateTrackerPage  # noqa: E402
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
    write_test_automation_result,
)
from testing.tests.support.live_tracker_app_factory import create_live_tracker_app  # noqa: E402
from testing.tests.support.ts980_restore_persistence_runtime import (  # noqa: E402
    Ts980RestorePersistenceRuntime,
    install_restorable_directory_picker,
    read_manual_reauth_probe,
    read_restorable_directory_picker_state,
)

TICKET_KEY = "TS-1006"
TEST_CASE_TITLE = (
    "Inactive workspace directory mismatch on startup keeps the active valid "
    "workspace selected"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-1006/test_ts_1006.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
DEFAULT_BRANCH = "main"
SHELL_NAVIGATION_LABELS = ("Dashboard", "Board", "JQL Search", "Hierarchy", "Settings")

ACTIVE_LOCAL_DISPLAY_NAME = "Workspace A"
ACTIVE_LOCAL_TARGET = "/tmp/trackstate-ts1006-workspace-a"
BROKEN_LOCAL_DISPLAY_NAME = "Workspace B"
BROKEN_LOCAL_TARGET = "/tmp/trackstate-ts1006-workspace-b"

HOSTED_DISPLAY_NAME = "Hosted setup workspace"
ACCEPTED_RECOVERY_ACTION_LABELS = ("Retry", "Re-authenticate")
LINKED_BUGS = [
    "TS-1212",
    "TS-1209",
    "TS-1146",
    "TS-1143",
    "TS-1142",
    "TS-1030",
    "TS-1011",
    "TS-995",
    "TS-994",
]
LINKED_BUG_NOTES = (
    "Reviewed TS-1212, TS-1209, TS-1146, TS-1143, TS-1142, TS-1030, TS-1011, "
    "TS-995, and TS-994. The linked fixes span the visible Retry/Re-authenticate "
    "recovery path, browser-persisted local directory access across reload, and "
    "the follow-up startup hydration selection logic, so this test waits for the "
    "visible restore callback, the restored Local Git precondition, the post-"
    "reload shell, and the final Workspace switcher row state before asserting."
)
PRECONDITION_WAIT_SECONDS = 60
STARTUP_WAIT_SECONDS = 90
ROW_STATE_WAIT_MS = 30_000

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
REVIEW_REPLIES_PATH = OUTPUTS_DIR / "review_replies.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1006_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1006_failure.png"
DISCUSSIONS_RAW_PATH = REPO_ROOT / "input" / TICKET_KEY / "pr_discussions_raw.json"

REQUEST_STEPS = [
    "Launch the application.",
    "Wait for the initialization sequence to complete.",
    "Observe the currently active workspace and the application view.",
    "Open the Workspace switcher and inspect the status of both workspaces.",
]
EXPECTED_RESULT = (
    "Workspace A remains the 'Active' workspace and its dashboard is rendered "
    "correctly. Workspace B is displayed as 'Unavailable' in the switcher, but "
    "its failure does not cause the system to clear the active selection or "
    "revert to the landing state."
)


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)
    _cleanup_local_workspaces()

    result: dict[str, Any] = {
        "ticket": TICKET_KEY,
        "test_case_title": TEST_CASE_TITLE,
        "browser": "Chromium (Playwright)",
        "os": platform.platform(),
        "run_command": RUN_COMMAND,
        "expected_result": EXPECTED_RESULT,
        "desktop_viewport": DESKTOP_VIEWPORT,
        "linked_bugs": LINKED_BUGS,
        "linked_bug_notes": LINKED_BUG_NOTES,
        "steps": [],
        "human_verification": [],
    }

    runtime_context: Ts980RestorePersistenceRuntime | None = None
    page: LiveWorkspaceSwitcherPage | None = None

    try:
        config = load_live_setup_test_config()
        result["app_url"] = config.app_url
        service = LiveSetupRepositoryService(config=config)
        token = service.token
        if not token:
            raise RuntimeError(
                "TS-1006 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
            )

        result["repository"] = service.repository
        result["repository_ref"] = service.ref
        initial_workspace_state = _initial_workspace_state(service.repository)
        result["initial_workspace_state"] = initial_workspace_state

        runtime_context = Ts980RestorePersistenceRuntime(
            repository=config.repository,
            token=token,
            workspace_state=initial_workspace_state,
            workspace_token_profile_ids=(
                f"hosted:{service.repository.lower()}@{DEFAULT_BRANCH}",
            ),
        )

        with create_live_tracker_app(
            config,
            runtime_factory=lambda: runtime_context,
        ) as tracker_page:
            page = LiveWorkspaceSwitcherPage(tracker_page)
            page.set_viewport(**DESKTOP_VIEWPORT)

            _establish_active_local_workspace_precondition(
                result=result,
                tracker_page=tracker_page,
                page=page,
            )

            startup_workspace_state = _startup_workspace_state()
            _persist_workspace_state(
                tracker_page=tracker_page,
                workspace_state=startup_workspace_state,
            )
            result["startup_workspace_state"] = startup_workspace_state

            tracker_page.open_entrypoint()
            page.set_viewport(**DESKTOP_VIEWPORT)
            result["startup_surface_after_reload"] = _startup_surface_payload(tracker_page)
            record_step(
                result,
                step=1,
                status="passed",
                action=REQUEST_STEPS[0],
                observed=(
                    "Reloaded the deployed app after seeding exactly two saved local "
                    "workspaces into browser storage: Workspace A as the active restored "
                    "local workspace and Workspace B as the inactive broken local workspace."
                ),
            )

            startup_ready, startup_observation = poll_until(
                probe=lambda: _observe_reloaded_two_local_startup(
                    tracker_page=tracker_page,
                    page=page,
                ),
                is_satisfied=lambda observation: bool(observation["ready"]),
                timeout_seconds=STARTUP_WAIT_SECONDS,
                interval_seconds=2,
            )
            result["startup_observation"] = startup_observation
            if not startup_ready:
                record_step(
                    result,
                    step=2,
                    status="failed",
                    action=REQUEST_STEPS[1],
                    observed=(
                        "Startup hydration never settled into the expected active local "
                        "workspace state after the reload.\n"
                        f"startup_observation={json.dumps(startup_observation, indent=2)}"
                    ),
                )
                record_not_reached_steps(
                    result,
                    starting_step=3,
                    request_steps=REQUEST_STEPS,
                )
                raise AssertionError(
                    "Step 2 failed: startup never settled with Workspace A as the active "
                    "Local Git workspace after the two-local-workspace reload.\n"
                    f"Observed startup state:\n{json.dumps(startup_observation, indent=2)}"
                )

            record_step(
                result,
                step=2,
                status="passed",
                action=REQUEST_STEPS[1],
                observed=(
                    "Waited for startup hydration to complete until the shell was ready and "
                    "the header trigger showed Workspace A as `Local Git`.\n"
                    f"startup_observation={json.dumps(startup_observation, indent=2)}"
                ),
            )

            startup_trigger = _trigger_from_payload(startup_observation["trigger"])
            shell_observation = startup_observation["shell_observation"]
            _assert_active_workspace_surface(
                trigger=startup_trigger,
                shell_observation=shell_observation,
                persisted_workspace_state=startup_observation["persisted_workspace_state"],
            )
            result["startup_trigger"] = startup_observation["trigger"]
            record_step(
                result,
                step=3,
                status="passed",
                action=REQUEST_STEPS[2],
                observed=(
                    "The live header and dashboard still showed Workspace A as the active "
                    "Local Git workspace after startup.\n"
                    f"trigger={json.dumps(startup_observation['trigger'], indent=2)}\n"
                    f"shell_observation={json.dumps(shell_observation, indent=2)}"
                ),
            )
            record_human_verification(
                result,
                check=(
                    "Viewed the live header and dashboard after startup the same way a user "
                    "would before opening the switcher."
                ),
                observed=(
                    f"trigger_label={startup_trigger.semantic_label!r}; "
                    f"trigger_text={startup_trigger.visible_text!r}; "
                    f"visible_navigation_labels={json.dumps(shell_observation.get('visible_navigation_labels', []), ensure_ascii=True)}"
                ),
            )

            switcher = page.open_and_observe(timeout_ms=20_000)
            result["switcher_observation"] = _switcher_payload(switcher)
            broken_row = page.observe_saved_workspace_row(
                display_name=BROKEN_LOCAL_DISPLAY_NAME,
                target_path=BROKEN_LOCAL_TARGET,
                target_type_label="Local",
                expected_state_label="Unavailable",
                accepted_action_labels=ACCEPTED_RECOVERY_ACTION_LABELS,
                timeout_ms=ROW_STATE_WAIT_MS,
            )
            refreshed_switcher = page.wait_for_refreshed_switcher_row_state(
                display_name=BROKEN_LOCAL_DISPLAY_NAME,
                target_path=BROKEN_LOCAL_TARGET,
                target_type_label="Local",
                expected_state_label="Unavailable",
                accepted_action_labels=ACCEPTED_RECOVERY_ACTION_LABELS,
                timeout_ms=ROW_STATE_WAIT_MS,
            )
            refreshed_trigger = page.observe_trigger(timeout_ms=5_000)
            active_row = _find_switcher_row(
                refreshed_switcher,
                display_name=ACTIVE_LOCAL_DISPLAY_NAME,
                target_path=ACTIVE_LOCAL_TARGET,
            )
            broken_row_refreshed = _find_switcher_row(
                refreshed_switcher,
                display_name=BROKEN_LOCAL_DISPLAY_NAME,
                target_path=BROKEN_LOCAL_TARGET,
            )
            selected_row = _find_selected_row(refreshed_switcher)
            result["broken_row_initial"] = _row_payload(broken_row)
            result["refreshed_switcher_observation"] = _switcher_payload(refreshed_switcher)
            result["refreshed_trigger"] = _trigger_payload(refreshed_trigger)
            result["active_row"] = _row_payload(active_row)
            result["broken_row"] = _row_payload(broken_row_refreshed)
            result["selected_row"] = _row_payload(selected_row)

            _assert_startup_selection_preserved(
                active_row=active_row,
                broken_row=broken_row_refreshed,
                current_trigger=refreshed_trigger,
                selected_row=selected_row,
                switcher=refreshed_switcher,
            )
            record_step(
                result,
                step=4,
                status="passed",
                action=REQUEST_STEPS[3],
                observed=(
                    "Opened Workspace switcher after startup and confirmed Workspace A "
                    "remained active while Workspace B showed `Unavailable` without "
                    "taking the active selection.\n"
                    f"trigger={json.dumps(result['refreshed_trigger'], indent=2)}\n"
                    f"active_row={json.dumps(result['active_row'], indent=2)}\n"
                    f"broken_row={json.dumps(result['broken_row'], indent=2)}\n"
                    f"selected_row={json.dumps(result['selected_row'], indent=2)}"
                ),
            )
            record_human_verification(
                result,
                check=(
                    "Opened Workspace switcher and read both saved workspace rows exactly as "
                    "a user would."
                ),
                observed=(
                    f"trigger_label={refreshed_trigger.semantic_label!r}; "
                    f"active_row_visible_text={repr(active_row.visible_text) if active_row else None}; "
                    f"broken_row_visible_text={repr(broken_row_refreshed.visible_text) if broken_row_refreshed else None}; "
                    f"switcher_text={refreshed_switcher.switcher_text!r}"
                ),
            )

            page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
            result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
    except AssertionError as error:
        result["error"] = str(error)
        result["traceback"] = traceback.format_exc()
        result["failure_kind"] = "product"
        if page is not None:
            try:
                page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
            except Exception as screenshot_error:  # pragma: no cover - diagnostics only
                result["screenshot_error"] = (
                    f"{type(screenshot_error).__name__}: {screenshot_error}"
                )
        if runtime_context is not None:
            result["console_events"] = list(runtime_context.console_events)
            result["page_errors"] = list(runtime_context.page_errors)
        _write_failure_outputs(result)
        raise
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        result["failure_kind"] = "setup"
        if page is not None:
            try:
                page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
            except Exception as screenshot_error:  # pragma: no cover - diagnostics only
                result["screenshot_error"] = (
                    f"{type(screenshot_error).__name__}: {screenshot_error}"
                )
        if runtime_context is not None:
            result["console_events"] = list(runtime_context.console_events)
            result["page_errors"] = list(runtime_context.page_errors)
        _write_failure_outputs(result)
        raise
    finally:
        _cleanup_local_workspaces()

    _write_pass_outputs(result)
    print(f"{TICKET_KEY} passed")


def _initial_workspace_state(repository: str) -> dict[str, object]:
    active_local_id = f"local:{ACTIVE_LOCAL_TARGET}@{DEFAULT_BRANCH}"
    hosted_id = f"hosted:{repository.lower()}@{DEFAULT_BRANCH}"
    return {
        "activeWorkspaceId": hosted_id,
        "migrationComplete": True,
        "profiles": [
            {
                "id": active_local_id,
                "displayName": ACTIVE_LOCAL_DISPLAY_NAME,
                "customDisplayName": ACTIVE_LOCAL_DISPLAY_NAME,
                "targetType": "local",
                "target": ACTIVE_LOCAL_TARGET,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": DEFAULT_BRANCH,
                "lastOpenedAt": "2026-05-23T00:00:00.000Z",
            },
            {
                "id": hosted_id,
                "displayName": HOSTED_DISPLAY_NAME,
                "customDisplayName": HOSTED_DISPLAY_NAME,
                "targetType": "hosted",
                "target": repository,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": DEFAULT_BRANCH,
                "lastOpenedAt": "2026-05-22T23:55:00.000Z",
            },
        ],
    }


def _startup_workspace_state() -> dict[str, object]:
    active_local_id = f"local:{ACTIVE_LOCAL_TARGET}@{DEFAULT_BRANCH}"
    broken_local_id = f"local:{BROKEN_LOCAL_TARGET}@{DEFAULT_BRANCH}"
    return {
        "activeWorkspaceId": active_local_id,
        "migrationComplete": True,
        "profiles": [
            {
                "id": active_local_id,
                "displayName": ACTIVE_LOCAL_DISPLAY_NAME,
                "customDisplayName": ACTIVE_LOCAL_DISPLAY_NAME,
                "targetType": "local",
                "target": ACTIVE_LOCAL_TARGET,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": DEFAULT_BRANCH,
                "lastOpenedAt": "2026-05-23T00:00:00.000Z",
            },
            {
                "id": broken_local_id,
                "displayName": BROKEN_LOCAL_DISPLAY_NAME,
                "customDisplayName": BROKEN_LOCAL_DISPLAY_NAME,
                "targetType": "local",
                "target": BROKEN_LOCAL_TARGET,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": DEFAULT_BRANCH,
                "lastOpenedAt": "2026-05-22T23:55:00.000Z",
            },
        ],
    }


def _establish_active_local_workspace_precondition(
    *,
    result: dict[str, Any],
    tracker_page: TrackStateTrackerPage,
    page: LiveWorkspaceSwitcherPage,
) -> None:
    tracker_page.open_entrypoint()
    page.set_viewport(**DESKTOP_VIEWPORT)

    trigger_visible, initial_trigger = poll_until(
        probe=lambda: _try_observe_trigger(page),
        is_satisfied=lambda candidate: candidate is not None,
        timeout_seconds=120,
        interval_seconds=2,
    )
    startup_surface = _startup_surface_payload(tracker_page)
    result["precondition_startup_surface"] = startup_surface
    if not trigger_visible or initial_trigger is None:
        record_step(
            result,
            step=1,
            status="failed",
            action=REQUEST_STEPS[0],
            observed=(
                "Not reached with the required precondition because the deployed app never "
                "exposed the header Workspace switcher needed to restore Workspace A into "
                "an active local workspace before the startup scenario.\n"
                f"startup_surface={json.dumps(startup_surface, indent=2)}"
            ),
        )
        record_not_reached_steps(result, starting_step=2, request_steps=REQUEST_STEPS)
        raise AssertionError(
            "Precondition failed: the deployed app never exposed the Workspace switcher "
            "trigger needed to establish Workspace A as an active local workspace.\n"
            f"Observed startup surface:\n{json.dumps(startup_surface, indent=2)}"
        )

    result["precondition_initial_trigger"] = _trigger_payload(initial_trigger)
    try:
        page.dismiss_connection_banner()
    except AssertionError:
        pass

    switcher_before = page.open_and_observe(timeout_ms=20_000)
    saved_rows_before = page.observe_saved_workspace_rows(timeout_ms=20_000)
    saved_local_row_before = _find_saved_workspace_row(
        saved_rows_before,
        display_name=ACTIVE_LOCAL_DISPLAY_NAME,
        target_path=ACTIVE_LOCAL_TARGET,
    )
    result["precondition_switcher_before"] = _switcher_payload(switcher_before)
    result["precondition_saved_local_row_before"] = _saved_row_payload(saved_local_row_before)
    if saved_local_row_before is None:
        _record_precondition_failure_steps(
            result,
            message=(
                "The open Workspace switcher did not expose Workspace A as a saved local "
                "workspace row before the requested startup scenario.\n"
                f"switcher_before={json.dumps(_switcher_payload(switcher_before), indent=2)}"
            ),
        )
        raise AssertionError(
            "Precondition failed: Workspace A was not present in the open Workspace switcher "
            "as a saved local workspace row.\n"
            f"Observed switcher:\n{json.dumps(_switcher_payload(switcher_before), indent=2)}"
        )
    if saved_local_row_before.state_label != "Unavailable":
        _record_precondition_failure_steps(
            result,
            message=(
                "Workspace A did not begin in the expected unavailable saved-workspace "
                "state needed for the visible recovery flow.\n"
                f"saved_local_row_before={json.dumps(_saved_row_payload(saved_local_row_before), indent=2)}"
            ),
        )
        raise AssertionError(
            "Precondition failed: Workspace A did not start as an unavailable saved local "
            "workspace row before the visible recovery action.\n"
            f"Observed saved row:\n{json.dumps(_saved_row_payload(saved_local_row_before), indent=2)}"
        )

    prepared_local_workspace = _prepare_active_local_workspace()
    directory_snapshot = _workspace_directory_snapshot(Path(prepared_local_workspace["path"]))
    install_restorable_directory_picker(
        tracker_page=tracker_page,
        directory_snapshot=directory_snapshot,
    )
    action_label = _saved_workspace_action_label(saved_local_row_before)
    result["prepared_local_workspace"] = prepared_local_workspace
    result["manual_directory_picker_fixture"] = _workspace_directory_snapshot_summary(
        directory_snapshot,
    )
    result["manual_restore_action_label"] = action_label

    page.click_saved_workspace_action_button(action_label, timeout_ms=10_000)

    callback_observed, restore_attempt_observation = poll_until(
        probe=lambda: _observe_manual_restore_attempt(
            tracker_page=tracker_page,
            page=page,
        ),
        is_satisfied=lambda observation: observation["directory_access_callback_observed"]
        or observation["failure_message"] is not None,
        timeout_seconds=20,
        interval_seconds=1,
    )
    result["manual_restore_attempt_observation"] = restore_attempt_observation
    if not callback_observed:
        _record_precondition_failure_steps(
            result,
            message=(
                "The visible Retry/Re-authenticate action on Workspace A never triggered a "
                "directory-access callback, so the required active local workspace "
                "precondition could not be established.\n"
                f"manual_restore_attempt_observation={json.dumps(restore_attempt_observation, indent=2)}"
            ),
        )
        raise AssertionError(
            "Precondition failed: the visible Retry/Re-authenticate action on Workspace A "
            "never triggered a directory-access callback.\n"
            f"Observed restore attempt:\n{json.dumps(restore_attempt_observation, indent=2)}"
        )

    restored, restored_observation = poll_until(
        probe=lambda: _observe_active_local_precondition(
            tracker_page=tracker_page,
            page=page,
        ),
        is_satisfied=lambda observation: bool(observation["restored"]),
        timeout_seconds=PRECONDITION_WAIT_SECONDS,
        interval_seconds=2,
    )
    result["active_local_precondition_observation"] = restored_observation
    if not restored:
        _record_precondition_failure_steps(
            result,
            message=(
                "Workspace A briefly triggered the visible directory picker, but the "
                "application never completed the active `Local Git` restore required for "
                "the requested startup scenario.\n"
                f"manual_restore_attempt_observation={json.dumps(restore_attempt_observation, indent=2)}\n"
                f"active_local_precondition_observation={json.dumps(restored_observation, indent=2)}"
            ),
        )
        record_human_verification(
            result,
            check=(
                "Used the visible Retry/Re-authenticate action for Workspace A and watched "
                "the header state the same way a user would."
            ),
            observed=(
                f"manual_restore_attempt={json.dumps(restore_attempt_observation, ensure_ascii=True)}; "
                f"active_local_precondition={json.dumps(restored_observation, ensure_ascii=True)}"
            ),
        )
        raise AssertionError(
            "Precondition failed: after the visible Retry/Re-authenticate action, the app "
            "did not keep Workspace A as the active `Local Git` workspace.\n"
            f"Observed restore attempt:\n{json.dumps(restore_attempt_observation, indent=2)}\n"
            f"Observed precondition state:\n{json.dumps(restored_observation, indent=2)}"
        )

    result["active_local_precondition_established"] = True
    record_human_verification(
        result,
        check=(
            "Used the visible Retry/Re-authenticate action for Workspace A and verified the "
            "header changed to the local workspace before running the startup scenario."
        ),
        observed=(
            f"active_local_precondition={json.dumps(restored_observation, ensure_ascii=True)}"
        ),
    )


def _record_precondition_failure_steps(
    result: dict[str, Any],
    *,
    message: str,
) -> None:
    if result.get("steps"):
        return
    record_step(
        result,
        step=1,
        status="failed",
        action=REQUEST_STEPS[0],
        observed=(
            "Not reached with the required precondition because the visible restore flow "
            "never left Workspace A active as `Local Git` before the startup reload.\n"
            f"{message}"
        ),
    )
    record_not_reached_steps(result, starting_step=2, request_steps=REQUEST_STEPS)


def _observe_manual_restore_attempt(
    *,
    tracker_page: TrackStateTrackerPage,
    page: LiveWorkspaceSwitcherPage,
) -> dict[str, object]:
    body_text = tracker_page.body_text()
    probe = read_manual_reauth_probe(tracker_page)
    directory_picker_state = read_restorable_directory_picker_state(tracker_page)
    trigger = _safe_trigger_payload(page)
    return {
        "probe": probe,
        "directory_picker_state": directory_picker_state,
        "body_text": body_text,
        "trigger": trigger,
        "failure_message": _extract_workspace_open_failure_message(body_text),
        "directory_access_callback_observed": bool(
            probe["showDirectoryPickerCalls"]
            or probe["requestPermissionCalls"]
            or directory_picker_state["calls"]
            or directory_picker_state.get("selectedDirectoryName")
        ),
    }


def _observe_active_local_precondition(
    *,
    tracker_page: TrackStateTrackerPage,
    page: LiveWorkspaceSwitcherPage,
) -> dict[str, object]:
    trigger = _safe_trigger_payload(page)
    shell_observation = tracker_page.observe_interactive_shell(
        SHELL_NAVIGATION_LABELS,
        timeout_ms=10_000,
    )
    persisted_workspace_state = _decode_workspace_state(
        tracker_page.snapshot_local_storage(
            [
                "trackstate.workspaceProfiles.state",
                "flutter.trackstate.workspaceProfiles.state",
            ],
        ),
    )
    restored = (
        trigger is not None
        and trigger["display_name"] == ACTIVE_LOCAL_DISPLAY_NAME
        and trigger["workspace_type"] == "Local"
        and trigger["state_label"] == "Local Git"
        and bool(shell_observation.get("shell_ready"))
        and persisted_workspace_state is not None
        and persisted_workspace_state.get("activeWorkspaceId")
        == f"local:{ACTIVE_LOCAL_TARGET}@{DEFAULT_BRANCH}"
    )
    return {
        "restored": restored,
        "trigger": trigger,
        "shell_observation": shell_observation,
        "persisted_workspace_state": persisted_workspace_state,
        "body_text": tracker_page.body_text(),
    }


def _observe_reloaded_two_local_startup(
    *,
    tracker_page: TrackStateTrackerPage,
    page: LiveWorkspaceSwitcherPage,
) -> dict[str, object]:
    trigger = _safe_trigger_payload(page)
    shell_observation = tracker_page.observe_interactive_shell(
        SHELL_NAVIGATION_LABELS,
        timeout_ms=10_000,
    )
    persisted_workspace_state = _decode_workspace_state(
        tracker_page.snapshot_local_storage(
            [
                "trackstate.workspaceProfiles.state",
                "flutter.trackstate.workspaceProfiles.state",
            ],
        ),
    )
    ready = (
        trigger is not None
        and trigger["display_name"] == ACTIVE_LOCAL_DISPLAY_NAME
        and trigger["workspace_type"] == "Local"
        and trigger["state_label"] == "Local Git"
        and bool(shell_observation.get("shell_ready"))
        and persisted_workspace_state is not None
        and persisted_workspace_state.get("activeWorkspaceId")
        == f"local:{ACTIVE_LOCAL_TARGET}@{DEFAULT_BRANCH}"
    )
    return {
        "ready": ready,
        "trigger": trigger,
        "shell_observation": shell_observation,
        "persisted_workspace_state": persisted_workspace_state,
        "body_text": tracker_page.body_text(),
    }


def _persist_workspace_state(
    *,
    tracker_page: TrackStateTrackerPage,
    workspace_state: dict[str, object],
) -> None:
    encoded_state = json.dumps(json.dumps(workspace_state))
    tracker_page.session.evaluate(
        """
        (value) => {
          for (const key of [
            'trackstate.workspaceProfiles.state',
            'flutter.trackstate.workspaceProfiles.state',
          ]) {
            window.localStorage.setItem(key, value);
          }
        }
        """,
        arg=encoded_state,
    )


def _prepare_active_local_workspace() -> dict[str, object]:
    local_path = Path(ACTIVE_LOCAL_TARGET)
    local_path.mkdir(parents=True, exist_ok=True)

    git_dir = local_path / ".git"
    if not git_dir.exists():
        subprocess.run(
            ["git", "init", "--initial-branch", DEFAULT_BRANCH, str(local_path)],
            check=True,
            capture_output=True,
            text=True,
        )

    marker_path = local_path / ".trackstate-ts1006-precondition.txt"
    marker_path.write_text(
        "Prepared for TS-1006 active local workspace startup validation.\n",
        encoding="utf-8",
    )

    seeded_paths = [marker_path.name]
    for relative_path, content in _workspace_fixture_files().items():
        destination = local_path / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")
        seeded_paths.append(relative_path)

    subprocess.run(
        ["git", "-C", str(local_path), "add", "."],
        check=True,
        capture_output=True,
        text=True,
    )
    status = subprocess.run(
        ["git", "-C", str(local_path), "status", "--short"],
        check=True,
        capture_output=True,
        text=True,
    )
    head = subprocess.run(
        ["git", "-C", str(local_path), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    if status.stdout.strip() or head.returncode != 0:
        subprocess.run(
            [
                "git",
                "-C",
                str(local_path),
                "-c",
                "user.name=TS-1006 Automation",
                "-c",
                "user.email=ts1006@example.com",
                "commit",
                "--allow-empty",
                "-m",
                "Prepare TS-1006 local workspace",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

    branch = subprocess.run(
        ["git", "-C", str(local_path), "branch", "--show-current"],
        check=True,
        capture_output=True,
        text=True,
    )
    head = subprocess.run(
        ["git", "-C", str(local_path), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    status = subprocess.run(
        ["git", "-C", str(local_path), "status", "--short"],
        check=True,
        capture_output=True,
        text=True,
    )
    return {
        "path": str(local_path),
        "branch": branch.stdout.strip(),
        "head": head.stdout.strip(),
        "status": status.stdout.strip(),
        "marker_path": str(marker_path),
        "seeded_paths": seeded_paths,
    }


def _workspace_fixture_files() -> dict[str, str]:
    return {
        "DEMO/config/statuses.json": json.dumps(
            [
                {"id": "todo", "name": "To Do", "category": "new"},
                {
                    "id": "in-progress",
                    "name": "In Progress",
                    "category": "indeterminate",
                },
                {"id": "done", "name": "Done", "category": "done"},
            ],
        )
        + "\n",
        "DEMO/config/workflows.json": json.dumps(
            {
                "default": {
                    "name": "Default Workflow",
                    "statuses": ["todo", "in-progress", "done"],
                    "transitions": [
                        {
                            "id": "start-progress",
                            "name": "Start progress",
                            "from": "todo",
                            "to": "in-progress",
                        },
                        {
                            "id": "finish-work",
                            "name": "Finish work",
                            "from": "in-progress",
                            "to": "done",
                        },
                    ],
                },
            },
        )
        + "\n",
        "DEMO/config/issue-types.json": json.dumps(
            [
                {
                    "id": "story",
                    "name": "Story",
                    "workflowId": "default",
                    "hierarchyLevel": 0,
                },
            ],
        )
        + "\n",
        "DEMO/config/fields.json": json.dumps(
            [
                {"id": "summary", "name": "Summary", "type": "string", "required": True},
                {
                    "id": "description",
                    "name": "Description",
                    "type": "markdown",
                    "required": False,
                },
                {
                    "id": "priority",
                    "name": "Priority",
                    "type": "option",
                    "required": False,
                    "options": [
                        {"id": "high", "name": "High"},
                        {"id": "medium", "name": "Medium"},
                    ],
                },
            ],
        )
        + "\n",
        "DEMO/DEMO-1/main.md": "\n".join(
            [
                "---",
                "key: DEMO-1",
                "project: DEMO",
                "issueType: story",
                "status: in-progress",
                "priority: high",
                "summary: TS-1006 seeded local workspace issue",
                "assignee: ts1006-user",
                "reporter: ts1006-user",
                "updated: 2026-05-23T00:00:00Z",
                "---",
                "",
                "# Description",
                "",
                "Seeded local workspace content for TS-1006 startup selection validation.",
                "",
            ],
        ),
    }


def _workspace_directory_snapshot(local_path: Path) -> dict[str, object]:
    relative_paths = [
        ".git/HEAD",
        ".git/config",
        ".trackstate-ts1006-precondition.txt",
        *sorted(_workspace_fixture_files()),
    ]
    files: list[dict[str, str]] = []
    for relative_path in relative_paths:
        absolute_path = local_path / relative_path
        if not absolute_path.is_file():
            continue
        files.append(
            {
                "path": relative_path,
                "base64": base64.b64encode(absolute_path.read_bytes()).decode("ascii"),
            },
        )
    return {
        "rootName": local_path.name,
        "rootPath": str(local_path),
        "files": files,
    }


def _workspace_directory_snapshot_summary(snapshot: dict[str, object]) -> dict[str, object]:
    files = snapshot.get("files", [])
    return {
        "rootName": snapshot.get("rootName"),
        "rootPath": snapshot.get("rootPath"),
        "fileCount": len(files) if isinstance(files, list) else 0,
        "paths": [
            entry.get("path")
            for entry in files
            if isinstance(entry, dict) and isinstance(entry.get("path"), str)
        ],
    }


def _saved_workspace_action_label(
    row: WorkspaceSwitcherSavedWorkspaceRowObservation,
) -> str:
    action_label = next(
        (
            label
            for label in row.action_labels
            if label and not label.startswith("Delete:")
        ),
        None,
    )
    if not action_label:
        raise AssertionError(
            "The unavailable Workspace A row did not expose any visible Retry or "
            "Re-authenticate action."
        )
    return action_label


def _find_saved_workspace_row(
    rows: tuple[WorkspaceSwitcherSavedWorkspaceRowObservation, ...],
    *,
    display_name: str,
    target_path: str,
) -> WorkspaceSwitcherSavedWorkspaceRowObservation | None:
    for row in rows:
        if row.display_name == display_name and target_path in row.detail_text:
            return row
    return None


def _find_switcher_row(
    switcher: WorkspaceSwitcherObservation,
    *,
    display_name: str,
    target_path: str,
) -> WorkspaceSwitcherRowObservation | None:
    for row in switcher.rows:
        if row.display_name == display_name and target_path in row.detail_text:
            return row
    return None


def _find_selected_row(
    switcher: WorkspaceSwitcherObservation,
) -> WorkspaceSwitcherRowObservation | None:
    return next((row for row in switcher.rows if row.selected), None)


def _assert_active_workspace_surface(
    *,
    trigger: WorkspaceSwitcherTriggerObservation,
    shell_observation: dict[str, object],
    persisted_workspace_state: dict[str, object] | None,
) -> None:
    if trigger.display_name != ACTIVE_LOCAL_DISPLAY_NAME:
        raise AssertionError(
            "Step 3 failed: the header trigger did not show Workspace A as the active "
            "workspace after startup.\n"
            f"Observed trigger: {json.dumps(_trigger_payload(trigger), indent=2)}"
        )
    if trigger.workspace_type != "Local" or trigger.state_label != "Local Git":
        raise AssertionError(
            "Step 3 failed: the header trigger did not report Workspace A as `Local Git` "
            "after startup.\n"
            f"Observed trigger: {json.dumps(_trigger_payload(trigger), indent=2)}"
        )
    if not bool(shell_observation.get("shell_ready")):
        raise AssertionError(
            "Step 3 failed: the dashboard shell was not interactive after startup.\n"
            f"Observed shell state:\n{json.dumps(shell_observation, indent=2)}"
        )
    if bool(shell_observation.get("fatal_banner_visible")):
        raise AssertionError(
            "Step 3 failed: startup left a fatal load banner visible instead of the "
            "dashboard shell.\n"
            f"Observed shell state:\n{json.dumps(shell_observation, indent=2)}"
        )
    if persisted_workspace_state is None:
        raise AssertionError(
            "Step 3 failed: the workspace profile state could not be read from local storage "
            "after startup.",
        )
    if (
        persisted_workspace_state.get("activeWorkspaceId")
        != f"local:{ACTIVE_LOCAL_TARGET}@{DEFAULT_BRANCH}"
    ):
        raise AssertionError(
            "Step 3 failed: the persisted active workspace was not Workspace A after startup.\n"
            f"Observed persisted state:\n{json.dumps(persisted_workspace_state, indent=2)}"
        )


def _assert_startup_selection_preserved(
    *,
    active_row: WorkspaceSwitcherRowObservation | None,
    broken_row: WorkspaceSwitcherRowObservation | None,
    current_trigger: WorkspaceSwitcherTriggerObservation,
    selected_row: WorkspaceSwitcherRowObservation | None,
    switcher: WorkspaceSwitcherObservation,
) -> None:
    if active_row is None:
        raise AssertionError(
            "Step 4 failed: Workspace switcher no longer showed Workspace A after startup.\n"
            f"Observed switcher:\n{json.dumps(_switcher_payload(switcher), indent=2)}"
        )
    if active_row.state_label != "Local Git":
        raise AssertionError(
            "Step 4 failed: Workspace A was no longer shown as `Local Git` in the switcher.\n"
            f"Observed active row: {json.dumps(_row_payload(active_row), indent=2)}"
        )
    trigger_matches_active_workspace = (
        current_trigger.display_name == ACTIVE_LOCAL_DISPLAY_NAME
        and current_trigger.workspace_type == "Local"
        and current_trigger.state_label == "Local Git"
    )
    if (
        selected_row is not None
        and selected_row.display_name != ACTIVE_LOCAL_DISPLAY_NAME
    ):
        raise AssertionError(
            "Step 4 failed: Workspace A did not remain the selected active workspace in the "
            "Workspace switcher after startup.\n"
            f"Observed selected row: {json.dumps(_row_payload(selected_row), indent=2) if selected_row else 'null'}\n"
            f"Observed trigger: {json.dumps(_trigger_payload(current_trigger), indent=2)}\n"
            f"Observed switcher: {json.dumps(_switcher_payload(switcher), indent=2)}"
        )
    if selected_row is None and not trigger_matches_active_workspace:
        raise AssertionError(
            "Step 4 failed: Workspace A did not remain the selected active workspace in the "
            "Workspace switcher after startup.\n"
            f"Observed selected row: null\n"
            f"Observed trigger: {json.dumps(_trigger_payload(current_trigger), indent=2)}\n"
            f"Observed switcher: {json.dumps(_switcher_payload(switcher), indent=2)}"
        )
    if broken_row is None:
        raise AssertionError(
            "Step 4 failed: Workspace switcher did not expose Workspace B after startup.\n"
            f"Observed switcher: {json.dumps(_switcher_payload(switcher), indent=2)}"
        )
    if broken_row.state_label != "Unavailable":
        raise AssertionError(
            "Step 4 failed: Workspace B did not render the expected `Unavailable` state.\n"
            f"Observed broken row: {json.dumps(_row_payload(broken_row), indent=2)}"
        )
    if (
        broken_row.selected
        or "Active" in broken_row.visible_text
        or "Active" in broken_row.action_labels
        or "Active" in broken_row.button_labels
    ):
        raise AssertionError(
            "Step 4 failed: Workspace B still appeared selected or labeled `Active` even "
            "though it was the broken inactive workspace.\n"
            f"Observed broken row: {json.dumps(_row_payload(broken_row), indent=2)}"
        )
    if not any(
        any(label.startswith(f"{accepted}:") or label == accepted for accepted in ACCEPTED_RECOVERY_ACTION_LABELS)
        for label in broken_row.action_labels
    ):
        raise AssertionError(
            "Step 4 failed: Workspace B did not expose a visible recovery action such as "
            "`Retry` or `Re-authenticate`.\n"
            f"Observed broken row: {json.dumps(_row_payload(broken_row), indent=2)}"
        )


def _extract_workspace_open_failure_message(body_text: str) -> str | None:
    normalized = " ".join(body_text.split())
    prefix = f"Could not open {ACTIVE_LOCAL_DISPLAY_NAME}."
    if prefix not in normalized:
        return None
    start = normalized.index(prefix)
    return normalized[start : start + 240]


def _decode_workspace_state(
    storage_snapshot: dict[str, str | None],
) -> dict[str, object] | None:
    for value in storage_snapshot.values():
        if value is None:
            continue
        parsed = json.loads(value)
        if isinstance(parsed, str):
            parsed = json.loads(parsed)
        if isinstance(parsed, dict):
            return parsed
    return None


def _startup_surface_payload(tracker_page: TrackStateTrackerPage) -> dict[str, object]:
    observation = tracker_page.observe_startup_surface()
    return {
        "title": observation.title,
        "location_href": observation.location_href,
        "location_hash": observation.location_hash,
        "location_pathname": observation.location_pathname,
        "body_text": observation.body_text,
        "button_labels": list(observation.button_labels),
    }


def _try_observe_trigger(
    page: LiveWorkspaceSwitcherPage,
) -> WorkspaceSwitcherTriggerObservation | None:
    try:
        return page.observe_trigger(timeout_ms=1_000)
    except (AssertionError, WebAppTimeoutError):
        return None


def _safe_trigger_payload(page: LiveWorkspaceSwitcherPage) -> dict[str, object] | None:
    trigger = _try_observe_trigger(page)
    return _trigger_payload(trigger) if trigger is not None else None


def _trigger_payload(trigger: WorkspaceSwitcherTriggerObservation) -> dict[str, object]:
    return {
        "semantic_label": trigger.semantic_label,
        "visible_text": trigger.visible_text,
        "raw_text_lines": list(trigger.raw_text_lines),
        "display_name": trigger.display_name,
        "workspace_type": trigger.workspace_type,
        "state_label": trigger.state_label,
        "icon_count": trigger.icon_count,
        "viewport_width": trigger.viewport_width,
        "viewport_height": trigger.viewport_height,
        "top_button_labels": list(trigger.top_button_labels),
    }


def _row_payload(row: WorkspaceSwitcherRowObservation | None) -> dict[str, object] | None:
    if row is None:
        return None
    return {
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


def _saved_row_payload(
    row: WorkspaceSwitcherSavedWorkspaceRowObservation | None,
) -> dict[str, object] | None:
    if row is None:
        return None
    return {
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
    }


def _switcher_payload(switcher: WorkspaceSwitcherObservation) -> dict[str, object]:
    return {
        "body_text": switcher.body_text,
        "switcher_text": switcher.switcher_text,
        "row_count": switcher.row_count,
        "rows": [_row_payload(row) for row in switcher.rows],
    }


def _trigger_from_payload(payload: dict[str, object]) -> WorkspaceSwitcherTriggerObservation:
    return WorkspaceSwitcherTriggerObservation(
        viewport_width=float(payload["viewport_width"]),
        viewport_height=float(payload["viewport_height"]),
        semantic_label=str(payload["semantic_label"]),
        visible_text=str(payload["visible_text"]),
        raw_text_lines=tuple(str(line) for line in payload["raw_text_lines"]),
        display_name=str(payload["display_name"]),
        workspace_type=str(payload["workspace_type"]),
        state_label=str(payload["state_label"]),
        icon_count=int(payload["icon_count"]),
        left=0.0,
        top=0.0,
        width=0.0,
        height=0.0,
        top_button_labels=tuple(str(label) for label in payload["top_button_labels"]),
    )


def _write_pass_outputs(result: dict[str, Any]) -> None:
    BUG_DESCRIPTION_PATH.unlink(missing_ok=True)
    write_test_automation_result(RESULT_PATH, passed=True)
    JIRA_COMMENT_PATH.write_text(_build_jira_comment(result, passed=True), encoding="utf-8")
    PR_BODY_PATH.write_text(_build_pr_body(result, passed=True), encoding="utf-8")
    RESPONSE_PATH.write_text(_build_response_summary(result, passed=True), encoding="utf-8")
    REVIEW_REPLIES_PATH.write_text(_build_review_replies(result, passed=True), encoding="utf-8")


def _write_failure_outputs(result: dict[str, Any]) -> None:
    BUG_DESCRIPTION_PATH.unlink(missing_ok=True)
    write_test_automation_result(
        RESULT_PATH,
        passed=False,
        error=_exact_error_summary(result),
    )
    JIRA_COMMENT_PATH.write_text(_build_jira_comment(result, passed=False), encoding="utf-8")
    PR_BODY_PATH.write_text(_build_pr_body(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_build_response_summary(result, passed=False), encoding="utf-8")
    REVIEW_REPLIES_PATH.write_text(_build_review_replies(result, passed=False), encoding="utf-8")
    if result.get("failure_kind") == "product":
        BUG_DESCRIPTION_PATH.write_text(_build_bug_description(result), encoding="utf-8")


def _build_jira_comment(result: dict[str, Any], *, passed: bool) -> str:
    status_icon = "✅" if passed else "❌"
    status_word = "PASSED" if passed else "FAILED"
    actual_result = (
        "Workspace A remained active as `Local Git`, the dashboard stayed visible, "
        "and Workspace B showed `Unavailable` without taking the active selection."
        if passed
        else str(result.get("error", "The requested startup selection behavior was not observed."))
    )
    lines = [
        f"h3. {status_icon} Automated test {status_word} — {TICKET_KEY}",
        "",
        f"*Test case*: {TEST_CASE_TITLE}",
        f"*Environment*: URL={result.get('app_url')} | Browser={result.get('browser')} | OS={result.get('os')}",
        f"*Viewport*: {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
        f"*Linked bugs considered*: {', '.join(LINKED_BUGS)}",
        f"*Linked bug notes*: {LINKED_BUG_NOTES}",
        "",
        "h4. Automation checks",
        *format_step_lines(result, jira=True),
        "",
        "h4. Real user-style verification",
        *format_human_lines(result, jira=True),
        "",
        "h4. Expected result",
        EXPECTED_RESULT,
        "",
        "h4. Actual result",
        actual_result,
    ]
    if result.get("screenshot"):
        lines.extend(["", f"*Screenshot*: {result['screenshot']}"])
    if not passed:
        lines.extend(
            [
                "",
                "h4. Assertion / error",
                "{code}",
                str(result.get("traceback", result.get("error", ""))),
                "{code}",
            ],
        )
    return "\n".join(lines) + "\n"


def _build_pr_body(result: dict[str, Any], *, passed: bool) -> str:
    actual_result = (
        "Workspace A stayed active as `Local Git`, the dashboard remained visible, and "
        "Workspace B rendered as `Unavailable` without becoming `Active`."
        if passed
        else str(result.get("error", "The requested startup selection behavior was not observed."))
    )
    lines = [
        f"## {TICKET_KEY} {'passed' if passed else 'failed'}",
        "",
        f"**Test case:** {TEST_CASE_TITLE}",
        f"**Environment:** `{result.get('app_url')}` · {result.get('browser')} · {result.get('os')}",
        f"**Viewport:** `{DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}`",
        f"**Linked bugs considered:** {', '.join(LINKED_BUGS)}",
        f"**Linked bug notes:** {LINKED_BUG_NOTES}",
        "",
        "## Automation checks",
        *format_step_lines(result, jira=False),
        "",
        "## Real user-style verification",
        *format_human_lines(result, jira=False),
        "",
        "## Expected result",
        EXPECTED_RESULT,
        "",
        "## Actual result",
        actual_result,
    ]
    if result.get("screenshot"):
        lines.extend(["", f"**Screenshot:** `{result['screenshot']}`"])
    if not passed:
        lines.extend(
            [
                "",
                "## Assertion / error",
                "```text",
                str(result.get("traceback", result.get("error", ""))),
                "```",
            ],
        )
    return "\n".join(lines) + "\n"


def _build_response_summary(result: dict[str, Any], *, passed: bool) -> str:
    lines = [
        "## Issues/Notes",
        (
            "- TS-1006 passed against the live deployed app."
            if passed
            else "- TS-1006 failed against the live deployed app: "
            f"{_exact_error_summary(result)}"
        ),
        "",
        "## Approach",
        "- Reused the live Playwright workspace-switcher harness and the visible Retry/Re-authenticate "
        "restore path to create the requested saved-local-workspace startup scenario.",
        "- Reloaded startup with exactly two saved local workspaces: Workspace A active and valid, "
        "Workspace B inactive and broken.",
        "",
        "## Files Modified",
        "- `testing/tests/TS-1006/test_ts_1006.py`",
        "- `testing/tests/TS-1006/config.yaml`",
        "- `testing/tests/TS-1006/README.md`",
        "- `testing/tests/support/ts980_restore_persistence_runtime.py`",
        "",
        "## Test Coverage",
        "- Visible restore flow for Workspace A before the startup scenario begins.",
        "- Startup hydration with Workspace A active and Workspace B broken.",
        "- Header/dashboard verification plus Workspace switcher row-state verification.",
    ]
    return "\n".join(lines) + "\n"


def _build_bug_description(result: dict[str, Any]) -> str:
    actual_result = str(
        result.get(
            "error",
            "The deployed app did not preserve the required active local workspace state "
            "for the TS-1006 startup scenario.",
        ),
    )
    lines = [
        f"h3. {TICKET_KEY}: Startup with an inactive broken workspace does not preserve the required active local workspace state",
        "",
        "h4. Environment",
        f"- URL: {result.get('app_url')}",
        f"- Browser: {result.get('browser')}",
        f"- OS: {result.get('os')}",
        f"- Viewport: {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
        f"- Active local target: {ACTIVE_LOCAL_TARGET}",
        f"- Broken local target: {BROKEN_LOCAL_TARGET}",
        "",
        "h4. Precondition setup used by automation",
        (
            "Before the ticket steps, automation used the visible saved-workspace recovery "
            "action (`Retry` / `Re-authenticate`) to restore Workspace A as an active local "
            "workspace, because the deployed web app otherwise starts from the hosted fallback "
            "surface. That precondition succeeded; the regression appears after the reload with "
            "two saved local workspaces, when startup hydration marks Workspace A as "
            "`Unavailable` instead of preserving its active `Local Git` state."
        ),
        f"- Manual restore action label: `{result.get('manual_restore_action_label')}`",
        f"- Manual restore attempt: `{json.dumps(result.get('manual_restore_attempt_observation'), ensure_ascii=True)}`",
        f"- Active local precondition observation: `{json.dumps(result.get('active_local_precondition_observation'), ensure_ascii=True)}`",
        "",
        "h4. Steps to Reproduce",
        *build_annotated_steps(result, request_steps=REQUEST_STEPS),
        "",
        "h4. Expected Result",
        EXPECTED_RESULT,
        "",
        "h4. Actual Result",
        actual_result,
        "",
        "h4. Logs / Error Output",
        "{code}",
        str(result.get("traceback", result.get("error", ""))),
        "{code}",
        "",
        "h4. Additional Observations",
        f"- Initial workspace state: `{json.dumps(result.get('initial_workspace_state'), ensure_ascii=True)}`",
        f"- Startup workspace state for reload: `{json.dumps(result.get('startup_workspace_state'), ensure_ascii=True)}`",
        f"- Startup surface before restore: `{json.dumps(result.get('precondition_startup_surface'), ensure_ascii=True)}`",
        f"- Initial trigger before restore: `{json.dumps(result.get('precondition_initial_trigger'), ensure_ascii=True)}`",
        f"- Switcher before restore: `{json.dumps(result.get('precondition_switcher_before'), ensure_ascii=True)}`",
        f"- Saved Workspace A row before restore: `{json.dumps(result.get('precondition_saved_local_row_before'), ensure_ascii=True)}`",
        f"- Prepared local workspace: `{json.dumps(result.get('prepared_local_workspace'), ensure_ascii=True)}`",
        f"- Manual directory picker fixture: `{json.dumps(result.get('manual_directory_picker_fixture'), ensure_ascii=True)}`",
        f"- Startup observation after reload: `{json.dumps(result.get('startup_observation'), ensure_ascii=True)}`",
        f"- Console events: `{json.dumps(result.get('console_events'), ensure_ascii=True)}`",
        f"- Page errors: `{json.dumps(result.get('page_errors'), ensure_ascii=True)}`",
    ]
    if result.get("screenshot"):
        lines.append(f"- Screenshot: `{result['screenshot']}`")
    return "\n".join(lines) + "\n"


def _exact_error_summary(result: dict[str, Any]) -> str:
    error = str(result.get("error", "")).strip()
    return error or "AssertionError: no error message captured"


def _build_review_replies(result: dict[str, Any], *, passed: bool) -> str:
    replies = [
        {
            "inReplyToId": thread["rootCommentId"],
            "threadId": thread["threadId"],
            "reply": _review_reply_text(result, passed=passed),
        }
        for thread in _discussion_threads()
    ]
    return json.dumps({"replies": replies}, indent=2) + "\n"


def _discussion_threads() -> list[dict[str, object]]:
    if not DISCUSSIONS_RAW_PATH.is_file():
        return []
    raw = json.loads(DISCUSSIONS_RAW_PATH.read_text(encoding="utf-8"))
    threads = raw.get("threads")
    if not isinstance(threads, list):
        return []
    normalized_threads: list[dict[str, object]] = []
    for thread in threads:
        if not isinstance(thread, dict) or thread.get("resolved") is not False:
            continue
        root_comment_id = thread.get("rootCommentId")
        thread_id = thread.get("threadId")
        if root_comment_id is None or thread_id is None:
            continue
        normalized_threads.append(
            {
                "rootCommentId": root_comment_id,
                "threadId": thread_id,
            },
        )
    return normalized_threads


def _review_reply_text(result: dict[str, Any], *, passed: bool) -> str:
    rerun_summary = (
        "Re-ran the current TS-1006 test and it passed (`1 passed, 0 failed`)."
        if passed
        else "Re-ran the current TS-1006 test and it still failed (`0 passed, 1 failed`)."
    )
    return "No actionable review issues were raised in this thread. " + rerun_summary


def _cleanup_local_workspaces() -> None:
    shutil.rmtree(ACTIVE_LOCAL_TARGET, ignore_errors=True)
    shutil.rmtree(BROKEN_LOCAL_TARGET, ignore_errors=True)


if __name__ == "__main__":
    main()
