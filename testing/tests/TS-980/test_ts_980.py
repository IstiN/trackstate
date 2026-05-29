from __future__ import annotations

import base64
import json
import platform
import re
import shutil
import subprocess
import sys
import traceback
from pathlib import Path

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
from testing.tests.support.live_tracker_app_factory import create_live_tracker_app  # noqa: E402
from testing.tests.support.ts980_restore_persistence_runtime import (  # noqa: E402
    Ts980RestorePersistenceRuntime,
    install_restorable_directory_picker,
    read_manual_reauth_probe,
    read_restorable_directory_picker_state,
)

TICKET_KEY = "TS-980"
TEST_CASE_TITLE = (
    "Refresh application after manual restoration keeps the workspace in Local Git"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-980/test_ts_980.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
DEFAULT_BRANCH = "main"
LOCAL_TARGET = "/tmp/trackstate-ts980-workspace"
LOCAL_DISPLAY_NAME = "Restorable local workspace"
HOSTED_DISPLAY_NAME = "Hosted setup workspace"
LINKED_BUGS = ["TS-994", "TS-993", "TS-976", "TS-972"]
SHELL_NAVIGATION_LABELS = ("Dashboard", "Board", "JQL Search", "Hierarchy", "Settings")
STARTUP_TRIGGER_WAIT_SECONDS = 60
POST_RELOAD_RESTORE_WAIT_SECONDS = 45

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
REVIEW_REPLIES_PATH = OUTPUTS_DIR / "review_replies.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts980_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts980_failure.png"
DISCUSSIONS_RAW_PATH = REPO_ROOT / "input" / TICKET_KEY / "pr_discussions_raw.json"

REQUEST_STEPS = [
    "Refresh the browser tab or perform a hard reload of the application.",
    "Open the Workspace switcher from the application header.",
    "Observe the status label and branch information for the previously restored workspace.",
]
EXPECTED_RESULT = (
    "The workspace status remains 'Local Git'. The application does not revert "
    "the workspace to 'Local Unavailable', confirming that the file system "
    "handle permissions were successfully persisted."
)
MANUAL_REAUTH_CALLBACK_WAIT_SECONDS = 15
RESTORE_COMPLETION_WAIT_SECONDS = 45
REWORK_SUMMARY = (
    "Resolved the TS-980 merge with main while preserving the approved "
    "repo-backed manual-restore flow and the post-reload product-gap "
    "assertions for the restored local workspace."
)


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)
    _remove_local_workspace_repository()

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-980 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
        )

    workspace_state = _workspace_state(service.repository)
    local_workspace_id = f"local:{LOCAL_TARGET}@{DEFAULT_BRANCH}"
    hosted_workspace_id = f"hosted:{service.repository.lower()}@{DEFAULT_BRANCH}"
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
        "preloaded_workspace_state": workspace_state,
        "precondition_established": False,
        "steps": [],
        "human_verification": [],
    }

    page: LiveWorkspaceSwitcherPage | None = None
    runtime_context: Ts980RestorePersistenceRuntime | None = None

    try:
        runtime_context = Ts980RestorePersistenceRuntime(
            repository=config.repository,
            token=token,
            workspace_state=workspace_state,
            workspace_token_profile_ids=(hosted_workspace_id,),
        )
        with create_live_tracker_app(
            config,
            runtime_factory=lambda: runtime_context,
        ) as tracker_page:
            page = LiveWorkspaceSwitcherPage(tracker_page)
            try:
                tracker_page.open_entrypoint()
                page.set_viewport(**DESKTOP_VIEWPORT)
                trigger_visible, initial_trigger = poll_until(
                    probe=lambda: _try_observe_trigger(page),
                    is_satisfied=lambda candidate: candidate is not None,
                    timeout_seconds=STARTUP_TRIGGER_WAIT_SECONDS,
                    interval_seconds=1,
                )
                result["runtime_state"] = (
                    "workspace-trigger-visible"
                    if trigger_visible and initial_trigger is not None
                    else "startup-trigger-timeout"
                )
                result["runtime_body_text"] = page.current_body_text()
                if not trigger_visible or initial_trigger is None:
                    _raise_startup_failure(
                        result=result,
                        tracker_page=tracker_page,
                        runtime_context=runtime_context,
                        reason=(
                            "The deployed app never exposed the visible Workspace switcher "
                            "trigger required to establish the restored-workspace precondition "
                            "for TS-980."
                        ),
                    )

                shell_observation = tracker_page.observe_interactive_shell(
                    SHELL_NAVIGATION_LABELS,
                    timeout_ms=10_000,
                )
                result["shell_observation_before_restore"] = shell_observation

                try:
                    page.dismiss_connection_banner()
                except (AssertionError, WebAppTimeoutError):
                    pass

                result["trigger_before_restore"] = _trigger_payload(initial_trigger)
                _record_human_verification(
                    result,
                    check=(
                        "Viewed the live shell before restoring the local workspace to confirm "
                        "the hosted workspace was currently active."
                    ),
                    observed=(
                        f"trigger_label={initial_trigger.semantic_label!r}; "
                        f"trigger_text={initial_trigger.visible_text!r}"
                    ),
                )

                switcher_before = page.open_and_observe(timeout_ms=20_000)
                result["switcher_before_restore"] = _switcher_payload(switcher_before)
                saved_rows_before = page.observe_saved_workspace_rows(timeout_ms=20_000)
                saved_local_row_before = _find_named_saved_local_row(saved_rows_before)
                result["saved_local_row_before_restore"] = (
                    _saved_row_payload(saved_local_row_before)
                    if saved_local_row_before is not None
                    else None
                )
                local_row_before = _find_named_local_row(switcher_before)
                hosted_row_before = _find_named_hosted_row(switcher_before)
                selected_row_before = _find_selected_row(switcher_before)
                result["local_row_before_restore"] = (
                    _row_payload(local_row_before) if local_row_before is not None else None
                )
                result["hosted_row_before_restore"] = (
                    _row_payload(hosted_row_before)
                    if hosted_row_before is not None
                    else None
                )
                result["selected_row_before_restore"] = (
                    _row_payload(selected_row_before)
                    if selected_row_before is not None
                    else None
                )

                try:
                    _assert_unavailable_local_row(
                        local_row=local_row_before,
                        selected_row=selected_row_before,
                        trigger=initial_trigger,
                        switcher=switcher_before,
                    )
                except AssertionError as error:
                    _record_request_steps_precondition_failure(result, str(error))
                    raise AssertionError(
                        "Precondition failed: the saved local workspace did not render as the "
                        "expected `Unavailable` row before the reload scenario could begin.\n"
                        f"{error}"
                    ) from error

                _record_human_verification(
                    result,
                    check=(
                        "Opened the switcher and visually confirmed the saved local workspace "
                        "row still showed the unavailable state before the manual restore action."
                    ),
                    observed=(
                        f"local_row={json.dumps(_row_payload(local_row_before), ensure_ascii=True)}; "
                        f"selected_row={json.dumps(_row_payload(selected_row_before), ensure_ascii=True) if selected_row_before else 'null'}"
                    ),
                )

                restored_local_workspace = _prepare_local_workspace_repository()
                result["restored_local_workspace"] = restored_local_workspace
                workspace_directory_snapshot = _workspace_directory_snapshot(
                    Path(restored_local_workspace["path"]),
                )
                install_restorable_directory_picker(
                    tracker_page=tracker_page,
                    directory_snapshot=workspace_directory_snapshot,
                )
                result["manual_directory_picker_fixture"] = _workspace_directory_snapshot_summary(
                    workspace_directory_snapshot,
                )
                result["manual_reauth_probe_before_action"] = read_manual_reauth_probe(
                    tracker_page,
                )
                result["manual_directory_picker_state_before_action"] = (
                    read_restorable_directory_picker_state(tracker_page)
                )
                exact_action_label = _saved_workspace_action_label(saved_local_row_before)
                result["manual_restore_action_label"] = exact_action_label

                try:
                    page.click_saved_workspace_action_button(
                        exact_action_label,
                        timeout_ms=10_000,
                    )
                except AssertionError as error:
                    message = (
                        "The saved local workspace directory was recreated before the manual "
                        "restore attempt, but activating the unavailable row failed.\n"
                        f"restored_local_workspace={json.dumps(restored_local_workspace, indent=2)}\n"
                        f"{error}"
                    )
                    _record_request_steps_precondition_failure(result, message)
                    raise AssertionError(f"Precondition failed: {message}") from error

                callback_observed, restore_attempt_observation = poll_until(
                    probe=lambda: _observe_manual_restore_attempt(
                        tracker_page=tracker_page,
                        page=page,
                    ),
                    is_satisfied=lambda observation: observation[
                        "directory_access_callback_observed"
                    ]
                    or observation["failure_message"] is not None,
                    timeout_seconds=MANUAL_REAUTH_CALLBACK_WAIT_SECONDS,
                    interval_seconds=1,
                )
                result["manual_restore_attempt_observation"] = restore_attempt_observation
                result["manual_reauth_probe_after_action"] = restore_attempt_observation[
                    "probe"
                ]
                result["manual_directory_picker_state_after_action"] = (
                    restore_attempt_observation["directory_picker_state"]
                )
                if not callback_observed:
                    message = (
                        "The manual unavailable-workspace action never triggered a "
                        "directory-access callback and never restored the workspace.\n"
                        f"Observed action label: {exact_action_label!r}\n"
                        f"Observed probe state:\n{json.dumps(restore_attempt_observation['probe'], indent=2)}\n"
                        "Observed injected picker state:\n"
                        f"{json.dumps(restore_attempt_observation['directory_picker_state'], indent=2)}\n"
                        f"Observed body text:\n{restore_attempt_observation['body_text']}"
                    )
                    _record_request_steps_precondition_failure(result, message)
                    raise AssertionError(f"Precondition failed: {message}")
                if restore_attempt_observation["failure_message"] is not None:
                    message = (
                        "The closest production-visible manual restore action "
                        "did not open a directory-access prompt and instead failed in the "
                        "deployed app.\n"
                        f"Observed action label: {exact_action_label!r}\n"
                        f"Observed failure message: {restore_attempt_observation['failure_message']}\n"
                        f"Observed probe state:\n{json.dumps(restore_attempt_observation['probe'], indent=2)}\n"
                        "Observed injected picker state:\n"
                        f"{json.dumps(restore_attempt_observation['directory_picker_state'], indent=2)}\n"
                        f"Observed body text:\n{restore_attempt_observation['body_text']}"
                    )
                    _record_request_steps_precondition_failure(result, message)
                    raise AssertionError(f"Precondition failed: {message}")

                restored, restored_observation = poll_until(
                    probe=lambda: _observe_restored_local_workspace(
                        tracker_page=tracker_page,
                        page=page,
                        expected_local_workspace_id=local_workspace_id,
                    ),
                    is_satisfied=lambda observation: observation["restored"],
                    timeout_seconds=RESTORE_COMPLETION_WAIT_SECONDS,
                    interval_seconds=2,
                )
                result["restored_workspace_observation"] = restored_observation
                if not restored:
                    message = (
                        "The directory-access callback was observed, but the workspace never "
                        "completed the Local Git restore flow.\n"
                        f"Observed restore observation:\n{json.dumps(restored_observation, indent=2)}\n"
                        "Observed injected picker state:\n"
                        f"{json.dumps(read_restorable_directory_picker_state(tracker_page), indent=2)}"
                    )
                    _record_request_steps_precondition_failure(result, message)
                    raise AssertionError(f"Precondition failed: {message}")

                trigger_after_restore = restored_observation["trigger"]
                shell_after_restore = restored_observation["shell_observation"]
                persisted_workspace_state = restored_observation["persisted_workspace_state"]
                switcher_after = restored_observation["switcher"]
                local_row_after = restored_observation["local_row"]
                hosted_row_after = restored_observation["hosted_row"]
                selected_row_after = restored_observation["selected_row"]
                result["trigger_after_restore"] = trigger_after_restore
                result["shell_observation_after_restore"] = shell_after_restore
                result["persisted_workspace_state"] = persisted_workspace_state
                result["switcher_after_restore"] = switcher_after
                result["local_row_after_restore"] = local_row_after
                result["hosted_row_after_restore"] = hosted_row_after
                result["selected_row_after_restore"] = selected_row_after

                try:
                    _assert_restored_local_workspace(
                        trigger=_trigger_from_payload(trigger_after_restore),
                        switcher=_switcher_from_payload(switcher_after),
                        local_row=_row_from_payload(local_row_after),
                        selected_row=_row_from_payload(selected_row_after),
                        shell_observation=shell_after_restore,
                        persisted_workspace_state=persisted_workspace_state,
                        expected_local_workspace_id=local_workspace_id,
                    )
                except AssertionError as error:
                    _record_request_steps_precondition_failure(result, str(error))
                    raise AssertionError(
                        "Precondition failed: the manual restore action never produced the "
                        "required active `Local Git` workspace before the reload scenario.\n"
                        f"{error}"
                    ) from error

                result["precondition_established"] = True

                _record_human_verification(
                    result,
                    check=(
                        "Viewed the header trigger and reopened the switcher after the manual "
                        "restore action to confirm the same workspace was active as `Local Git` "
                        "before the reload."
                    ),
                    observed=(
                        f"trigger_after_restore={json.dumps(trigger_after_restore, ensure_ascii=True)}; "
                        f"local_row_after_restore={json.dumps(local_row_after, ensure_ascii=True) if local_row_after else 'null'}"
                    ),
                )

                tracker_page.open_entrypoint()
                page.set_viewport(**DESKTOP_VIEWPORT)
                reloaded_surface_ready, reloaded_state = poll_until(
                    probe=lambda: _observe_reloaded_workspace_surface(
                        tracker_page=tracker_page,
                        page=page,
                    ),
                    is_satisfied=lambda observation: bool(observation["surface_ready"]),
                    timeout_seconds=POST_RELOAD_RESTORE_WAIT_SECONDS,
                    interval_seconds=2,
                )
                result["post_reload_state"] = reloaded_state
                if not reloaded_surface_ready:
                    _record_step(
                        result,
                        step=1,
                        status="failed",
                        action=REQUEST_STEPS[0],
                        observed=(
                            "After the hard reload, the deployed app never returned to a stable "
                            "interactive surface that exposed the workspace trigger and "
                            "persisted workspace state needed for TS-980.\n"
                            f"post_reload_state={json.dumps(reloaded_state, indent=2)}"
                        ),
                    )
                    _record_step(
                        result,
                        step=2,
                        status="failed",
                        action=REQUEST_STEPS[1],
                        observed=(
                            "Not reached because the application did not return to the restored "
                            "local workspace state after the hard reload."
                        ),
                    )
                    _record_step(
                        result,
                        step=3,
                        status="failed",
                        action=REQUEST_STEPS[2],
                        observed=(
                            "Not reached because the application did not return to the restored "
                            "local workspace state after the hard reload."
                        ),
                    )
                    raise AssertionError(
                        "Step 1 failed: after the hard reload, the deployed app never returned "
                        "to a stable interactive surface that exposed the workspace trigger and "
                        "persisted workspace state needed for TS-980.\n"
                        f"Observed post-reload state:\n{json.dumps(reloaded_state, indent=2)}"
                    )

                result["trigger_after_reload"] = reloaded_state["trigger"]
                result["shell_observation_after_reload"] = reloaded_state["shell_observation"]
                result["persisted_workspace_state_after_reload"] = reloaded_state[
                    "persisted_workspace_state"
                ]
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=REQUEST_STEPS[0],
                    observed=(
                        "Reloaded the deployed app and waited for the post-reload surface to "
                        "settle before opening the Workspace switcher.\n"
                        f"trigger_after_reload={json.dumps(reloaded_state['trigger'], indent=2)}\n"
                        f"persisted_workspace_state_after_reload={json.dumps(reloaded_state['persisted_workspace_state'], indent=2)}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Viewed the header workspace trigger immediately after the reload wait "
                        "window to confirm the restored local workspace was still active."
                    ),
                    observed=(
                        f"trigger_after_reload={json.dumps(reloaded_state['trigger'], ensure_ascii=True)}"
                    ),
                )

                switcher_after_reload = page.open_and_observe(timeout_ms=20_000)
                local_row_after_reload = _find_named_local_row(switcher_after_reload)
                hosted_row_after_reload = _find_named_hosted_row(switcher_after_reload)
                selected_row_after_reload = _find_selected_row(switcher_after_reload)
                result["switcher_after_reload"] = _switcher_payload(switcher_after_reload)
                result["local_row_after_reload"] = _row_payload(local_row_after_reload)
                result["hosted_row_after_reload"] = _row_payload(hosted_row_after_reload)
                result["selected_row_after_reload"] = _row_payload(selected_row_after_reload)
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=REQUEST_STEPS[1],
                    observed=(
                        "Opened the Workspace switcher after the hard reload.\n"
                        f"row_count={switcher_after_reload.row_count}; "
                        f"switcher_text={switcher_after_reload.switcher_text!r}"
                    ),
                )

                try:
                    _assert_reloaded_local_workspace(
                        trigger=_trigger_from_payload(reloaded_state["trigger"]),
                        switcher=switcher_after_reload,
                        local_row=local_row_after_reload,
                        selected_row=selected_row_after_reload,
                        shell_observation=reloaded_state["shell_observation"],
                        persisted_workspace_state=reloaded_state["persisted_workspace_state"],
                        expected_local_workspace_id=local_workspace_id,
                    )
                except AssertionError as error:
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
                        "After the hard reload, the same workspace still rendered as `Local Git` "
                        "with the expected branch information.\n"
                        f"local_row_after_reload={json.dumps(_row_payload(local_row_after_reload), indent=2)}\n"
                        f"selected_row_after_reload={json.dumps(_row_payload(selected_row_after_reload), indent=2)}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Opened the Workspace switcher after the reload and visually checked "
                        "the restored local workspace row, status label, and branch details."
                    ),
                    observed=(
                        f"local_row_after_reload={json.dumps(_row_payload(local_row_after_reload), ensure_ascii=True)}; "
                        f"selected_row_after_reload={json.dumps(_row_payload(selected_row_after_reload), ensure_ascii=True)}"
                    ),
                )

            except Exception:
                if page is not None:
                    try:
                        if not FAILURE_SCREENSHOT_PATH.exists():
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
    finally:
        if runtime_context is not None:
            result["console_events"] = list(runtime_context.console_events)
            result["page_errors"] = list(runtime_context.page_errors)
        _remove_local_workspace_repository()

    _write_pass_outputs(result)
    print(f"{TICKET_KEY} passed")


def _workspace_state(repository: str) -> dict[str, object]:
    local_id = f"local:{LOCAL_TARGET}@{DEFAULT_BRANCH}"
    hosted_id = f"hosted:{repository.lower()}@{DEFAULT_BRANCH}"
    return {
        "activeWorkspaceId": hosted_id,
        "migrationComplete": True,
        "profiles": [
            {
                "id": local_id,
                "displayName": LOCAL_DISPLAY_NAME,
                "customDisplayName": LOCAL_DISPLAY_NAME,
                "targetType": "local",
                "target": LOCAL_TARGET,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": DEFAULT_BRANCH,
                "lastOpenedAt": "2026-05-22T00:00:00.000Z",
            },
            {
                "id": hosted_id,
                "displayName": HOSTED_DISPLAY_NAME,
                "customDisplayName": HOSTED_DISPLAY_NAME,
                "targetType": "hosted",
                "target": repository,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": DEFAULT_BRANCH,
                "lastOpenedAt": "2026-05-21T23:55:00.000Z",
            },
        ],
    }


def _prepare_local_workspace_repository() -> dict[str, object]:
    local_path = Path(LOCAL_TARGET)
    local_path.mkdir(parents=True, exist_ok=True)

    git_dir = local_path / ".git"
    if not git_dir.exists():
        subprocess.run(
            ["git", "init", "--initial-branch", DEFAULT_BRANCH, str(local_path)],
            check=True,
            capture_output=True,
            text=True,
        )

    marker_path = local_path / ".trackstate-ts980-precondition.txt"
    marker_path.write_text(
        "Prepared for TS-980 unavailable local workspace manual restore validation.\n",
        encoding="utf-8",
    )

    seeded_paths = [marker_path.name]
    for relative_path, content in _restorable_workspace_fixture_files().items():
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
                "user.name=TS-980 Automation",
                "-c",
                "user.email=ts980@example.com",
                "commit",
                "--allow-empty",
                "-m",
                "Prepare TS-980 local workspace",
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


def _remove_local_workspace_repository() -> None:
    shutil.rmtree(LOCAL_TARGET, ignore_errors=True)


def _restorable_workspace_fixture_files() -> dict[str, str]:
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
                "summary: TS-980 seeded local workspace issue",
                "assignee: ts980-user",
                "reporter: ts980-user",
                "updated: 2026-05-22T00:00:00Z",
                "---",
                "",
                "# Description",
                "",
                "Seeded local workspace content for TS-980 restore validation.",
                "",
            ],
        ),
    }


def _workspace_directory_snapshot(local_path: Path) -> dict[str, object]:
    relative_paths = [
        ".git/HEAD",
        ".git/config",
        ".trackstate-ts980-precondition.txt",
        *sorted(_restorable_workspace_fixture_files()),
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


def _workspace_directory_snapshot_summary(
    snapshot: dict[str, object],
) -> dict[str, object]:
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


def _find_named_local_row(
    switcher: WorkspaceSwitcherObservation,
) -> WorkspaceSwitcherRowObservation | None:
    for row in switcher.rows:
        if (
            row.display_name == LOCAL_DISPLAY_NAME
            and row.target_type_label == "Local"
            and LOCAL_TARGET in row.detail_text
        ):
            return row
    return None


def _find_named_hosted_row(
    switcher: WorkspaceSwitcherObservation,
) -> WorkspaceSwitcherRowObservation | None:
    for row in switcher.rows:
        if row.display_name == HOSTED_DISPLAY_NAME and row.target_type_label == "Hosted":
            return row
    return None


def _find_named_saved_local_row(
    rows: tuple[WorkspaceSwitcherSavedWorkspaceRowObservation, ...],
) -> WorkspaceSwitcherSavedWorkspaceRowObservation | None:
    for row in rows:
        if (
            row.display_name == LOCAL_DISPLAY_NAME
            and row.target_type_label == "Local"
            and LOCAL_TARGET in row.detail_text
        ):
            return row
    return None


def _find_selected_row(
    switcher: WorkspaceSwitcherObservation,
) -> WorkspaceSwitcherRowObservation | None:
    return next((row for row in switcher.rows if row.selected), None)


def _assert_unavailable_local_row(
    *,
    local_row: WorkspaceSwitcherRowObservation | None,
    selected_row: WorkspaceSwitcherRowObservation | None,
    trigger: WorkspaceSwitcherTriggerObservation,
    switcher: WorkspaceSwitcherObservation,
) -> None:
    if local_row is None:
        raise AssertionError(
            "Step 2 failed: the Workspace switcher did not expose the saved local workspace row.\n"
            f"Observed trigger label: {trigger.semantic_label!r}\n"
            f"Observed rows: {[row.visible_text for row in switcher.rows]!r}\n"
            f"Observed switcher text:\n{switcher.switcher_text}"
        )
    if local_row.state_label != "Unavailable":
        raise AssertionError(
            "Step 2 failed: the saved local workspace row was not shown in the expected "
            "`Unavailable` state before the manual restore action.\n"
            f"Observed local row: {json.dumps(_row_payload(local_row), indent=2)}"
        )
    if selected_row is not None and selected_row.display_name == LOCAL_DISPLAY_NAME:
        raise AssertionError(
            "Step 2 failed: the unavailable local workspace was already selected before "
            "the manual restore action.\n"
            f"Observed selected row: {json.dumps(_row_payload(selected_row), indent=2)}"
        )


def _assert_restored_local_workspace(
    *,
    trigger: WorkspaceSwitcherTriggerObservation,
    switcher: WorkspaceSwitcherObservation,
    local_row: WorkspaceSwitcherRowObservation | None,
    selected_row: WorkspaceSwitcherRowObservation | None,
    shell_observation: dict[str, object],
    persisted_workspace_state: dict[str, object] | None,
    expected_local_workspace_id: str,
) -> None:
    if trigger.display_name != LOCAL_DISPLAY_NAME:
        raise AssertionError(
            "Step 4 failed: the header trigger did not switch to the restored local "
            "workspace after the manual action.\n"
            f"Observed trigger: {json.dumps(_trigger_payload(trigger), indent=2)}"
        )
    if trigger.workspace_type != "Local" or trigger.state_label != "Local Git":
        raise AssertionError(
            "Step 4 failed: the header trigger did not report the restored workspace "
            "as `Local Git`.\n"
            f"Observed trigger: {json.dumps(_trigger_payload(trigger), indent=2)}"
        )
    summary_visible = _switcher_contains_workspace_summary(
        switcher=switcher,
        display_name=LOCAL_DISPLAY_NAME,
        target_type="Local",
        state_label="Local Git",
    )
    if local_row is None and not summary_visible:
        raise AssertionError(
            "Step 4 failed: reopening the switcher after restore no longer showed the "
            "restored workspace in the expected `Local Git` state.\n"
            f"Observed switcher text:\n{switcher.switcher_text}"
        )
    if local_row is not None and local_row.state_label != "Local Git":
        raise AssertionError(
            "Step 4 failed: the restored local workspace row did not show the `Local Git` "
            "state after the manual action.\n"
            f"Observed local row: {json.dumps(_row_payload(local_row), indent=2)}"
        )
    if (
        selected_row is not None
        and selected_row.display_name != LOCAL_DISPLAY_NAME
        and not summary_visible
    ):
        raise AssertionError(
            "Step 4 failed: the restored local workspace did not appear as the active "
            "workspace after the manual action.\n"
            f"Observed selected row: {json.dumps(_row_payload(selected_row), indent=2)}\n"
            f"Observed switcher text:\n{switcher.switcher_text}"
        )
    if not bool(shell_observation.get("shell_ready")):
        raise AssertionError(
            "Step 4 failed: the app shell did not stay interactive after the restored "
            "local workspace became active.\n"
            f"Observed shell state:\n{json.dumps(shell_observation, indent=2)}"
        )
    if bool(shell_observation.get("fatal_banner_visible")):
        raise AssertionError(
            "Step 4 failed: the restored local workspace still showed a fatal tracker "
            "load banner instead of a loaded shell.\n"
            f"Observed shell state:\n{json.dumps(shell_observation, indent=2)}"
        )
    if not _shell_shows_repository_branch(
        shell_observation=shell_observation,
        repository_label=LOCAL_TARGET,
        branch_name=DEFAULT_BRANCH,
    ):
        raise AssertionError(
            "Step 4 failed: the restored local workspace did not surface the expected "
            "repository and branch details after the manual action.\n"
            f"Observed shell state:\n{json.dumps(shell_observation, indent=2)}"
        )
    if persisted_workspace_state is None:
        raise AssertionError(
            "Step 4 failed: the workspace profile state could not be read from local storage "
            "after the restore action.",
        )
    if persisted_workspace_state.get("activeWorkspaceId") != expected_local_workspace_id:
        raise AssertionError(
            "Step 4 failed: the persisted active workspace did not update to the restored "
            "local workspace.\n"
            f"Observed persisted state:\n{json.dumps(persisted_workspace_state, indent=2)}"
        )


def _assert_reloaded_local_workspace(
    *,
    trigger: WorkspaceSwitcherTriggerObservation,
    switcher: WorkspaceSwitcherObservation,
    local_row: WorkspaceSwitcherRowObservation | None,
    selected_row: WorkspaceSwitcherRowObservation | None,
    shell_observation: dict[str, object],
    persisted_workspace_state: dict[str, object] | None,
    expected_local_workspace_id: str,
) -> None:
    summary_visible = _switcher_contains_workspace_summary(
        switcher=switcher,
        display_name=LOCAL_DISPLAY_NAME,
        target_type="Local",
        state_label="Local Git",
    )
    if trigger.display_name != LOCAL_DISPLAY_NAME:
        raise AssertionError(
            "Step 3 failed: the header trigger did not return to the restored local workspace "
            "after the hard reload.\n"
            f"Observed trigger: {json.dumps(_trigger_payload(trigger), indent=2)}"
        )
    if trigger.workspace_type != "Local" or trigger.state_label != "Local Git":
        raise AssertionError(
            "Step 3 failed: the header trigger did not report the restored workspace as "
            "`Local Git` after the hard reload.\n"
            f"Observed trigger: {json.dumps(_trigger_payload(trigger), indent=2)}"
        )
    if local_row is None and not summary_visible:
        raise AssertionError(
            "Step 3 failed: reopening the Workspace switcher after the hard reload no longer "
            "showed the restored local workspace in the expected `Local Git` state.\n"
            f"Observed switcher text:\n{switcher.switcher_text}"
        )
    if local_row is not None and local_row.state_label != "Local Git":
        raise AssertionError(
            "Step 3 failed: the restored local workspace row reverted away from `Local Git` "
            "after the hard reload.\n"
            f"Observed local row: {json.dumps(_row_payload(local_row), indent=2)}"
        )
    if selected_row is not None and selected_row.display_name != LOCAL_DISPLAY_NAME:
        raise AssertionError(
            "Step 3 failed: the restored local workspace row did not remain the active "
            "selection after the hard reload.\n"
            f"Observed selected row: {json.dumps(_row_payload(selected_row), indent=2)}"
        )
    detail_visible = (
        local_row is not None
        and LOCAL_TARGET in local_row.detail_text
        and f"Branch: {DEFAULT_BRANCH}" in local_row.detail_text
    ) or _switcher_contains_workspace_detail(
        switcher=switcher,
        display_name=LOCAL_DISPLAY_NAME,
        target_type="Local",
        state_label="Local Git",
        detail_contains=LOCAL_TARGET,
        branch_name=DEFAULT_BRANCH,
    )
    if not detail_visible:
        raise AssertionError(
            "Step 3 failed: the restored local workspace did not keep the expected branch "
            "information after the hard reload.\n"
            f"Observed switcher text:\n{switcher.body_text}"
        )
    if not bool(shell_observation.get("shell_ready")):
        raise AssertionError(
            "Step 3 failed: the app shell was not interactive after the hard reload.\n"
            f"Observed shell state:\n{json.dumps(shell_observation, indent=2)}"
        )
    if bool(shell_observation.get("fatal_banner_visible")):
        raise AssertionError(
            "Step 3 failed: the app showed a fatal tracker load banner after the hard reload.\n"
            f"Observed shell state:\n{json.dumps(shell_observation, indent=2)}"
        )
    if not _shell_shows_repository_branch(
        shell_observation=shell_observation,
        repository_label=LOCAL_TARGET,
        branch_name=DEFAULT_BRANCH,
    ):
        raise AssertionError(
            "Step 3 failed: the app shell no longer surfaced the restored local workspace "
            "repository and branch details after the hard reload.\n"
            f"Observed shell state:\n{json.dumps(shell_observation, indent=2)}"
        )
    if persisted_workspace_state is None:
        raise AssertionError(
            "Step 3 failed: the workspace profile state could not be read from local storage "
            "after the hard reload.",
        )
    if persisted_workspace_state.get("activeWorkspaceId") != expected_local_workspace_id:
        raise AssertionError(
            "Step 3 failed: the persisted active workspace reverted away from the restored "
            "local workspace after the hard reload.\n"
            f"Observed persisted state:\n{json.dumps(persisted_workspace_state, indent=2)}"
        )


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
        left=float(payload.get("left", 0.0)),
        top=float(payload.get("top", 0.0)),
        width=float(payload.get("width", 0.0)),
        height=float(payload.get("height", 0.0)),
        top_button_labels=tuple(str(label) for label in payload["top_button_labels"]),
    )


def _row_from_payload(
    payload: dict[str, object] | None,
) -> WorkspaceSwitcherRowObservation | None:
    if payload is None:
        return None
    return WorkspaceSwitcherRowObservation(
        display_name=(
            None if payload.get("display_name") is None else str(payload["display_name"])
        ),
        target_type_label=(
            None
            if payload.get("target_type_label") is None
            else str(payload["target_type_label"])
        ),
        state_label=None if payload.get("state_label") is None else str(payload["state_label"]),
        detail_text=str(payload["detail_text"]),
        visible_text=str(payload["visible_text"]),
        selected=bool(payload["selected"]),
        semantics_label=(
            None if payload.get("semantics_label") is None else str(payload["semantics_label"])
        ),
        icon_accessibility_label=(
            None
            if payload.get("icon_accessibility_label") is None
            else str(payload["icon_accessibility_label"])
        ),
        action_labels=tuple(str(label) for label in payload["action_labels"]),
        button_labels=tuple(str(label) for label in payload["button_labels"]),
    )


def _switcher_from_payload(payload: dict[str, object]) -> WorkspaceSwitcherObservation:
    rows = tuple(
        row
        for row in (
            _row_from_payload(row_payload)
            for row_payload in payload.get("rows", [])
            if isinstance(row_payload, dict)
        )
        if row is not None
    )
    return WorkspaceSwitcherObservation(
        body_text=str(payload["body_text"]),
        switcher_text=str(payload["switcher_text"]),
        row_count=int(payload["row_count"]),
        rows=rows,
    )


def _decode_workspace_state(storage_snapshot: dict[str, str | None]) -> dict[str, object] | None:
    for value in storage_snapshot.values():
        if value is None:
            continue
        parsed = json.loads(value)
        if isinstance(parsed, str):
            parsed = json.loads(parsed)
        if isinstance(parsed, dict):
            return parsed
    return None


def _try_observe_trigger(
    page: LiveWorkspaceSwitcherPage,
) -> WorkspaceSwitcherTriggerObservation | None:
    try:
        return page.observe_trigger(timeout_ms=1_000)
    except (AssertionError, WebAppTimeoutError):
        return None


def _observe_startup_surface(
    tracker_page: TrackStateTrackerPage,
) -> dict[str, object]:
    payload = tracker_page.session.evaluate(
        """
        () => {
          const normalize = (value) => (value || '').replace(/\\s+/g, ' ').trim();
          const isVisible = (element) => {
            if (!element) {
              return false;
            }
            const rect = element.getBoundingClientRect();
            const style = window.getComputedStyle(element);
            return rect.width > 0
              && rect.height > 0
              && style.visibility !== 'hidden'
              && style.display !== 'none';
          };
          const buttonLabels = Array.from(
            document.querySelectorAll('button, flt-semantics[role="button"], [role="button"]'),
          )
            .filter(isVisible)
            .map((element) =>
              normalize(
                element.getAttribute('aria-label')
                || element.innerText
                || element.textContent
                || '',
              ),
            )
            .filter((label) => label.length > 0);
          return {
            title: document.title || '',
            locationHref: window.location.href,
            locationHash: window.location.hash,
            locationPathname: window.location.pathname,
            bodyText: document.body?.innerText || document.body?.textContent || '',
            buttonLabels,
          };
        }
        """,
    )
    if not isinstance(payload, dict):
        return {
            "title": "",
            "location_href": "",
            "location_hash": "",
            "location_pathname": "",
            "body_text": tracker_page.body_text(),
            "button_labels": [],
        }
    return {
        "title": str(payload.get("title", "")),
        "location_href": str(payload.get("locationHref", "")),
        "location_hash": str(payload.get("locationHash", "")),
        "location_pathname": str(payload.get("locationPathname", "")),
        "body_text": str(payload.get("bodyText", "")),
        "button_labels": [str(label) for label in payload.get("buttonLabels", [])],
    }


def _raise_startup_failure(
    *,
    result: dict[str, object],
    tracker_page: TrackStateTrackerPage,
    runtime_context: Ts980RestorePersistenceRuntime,
    reason: str,
) -> None:
    startup_observation = _observe_startup_surface(tracker_page)
    result["runtime_state"] = "startup-failed"
    result["startup_observation"] = startup_observation
    result["runtime_body_text"] = startup_observation["body_text"]
    result["console_events"] = list(runtime_context.console_events)
    result["page_errors"] = list(runtime_context.page_errors)
    observed = (
        "The deployed app never exposed the Workspace switcher entry point needed to begin "
        "the TS-980 reload-persistence scenario.\n"
        f"Reason: {reason}\n"
        f"Startup observation: {json.dumps(startup_observation, indent=2)}\n"
        f"Console events: {json.dumps(result['console_events'], indent=2)}\n"
        f"Page errors: {json.dumps(result['page_errors'], indent=2)}"
    )
    _record_step(
        result,
        step=1,
        status="failed",
        action=REQUEST_STEPS[0],
        observed=observed,
    )
    for step_number in (2, 3):
        _record_step(
            result,
            step=step_number,
            status="failed",
            action=REQUEST_STEPS[step_number - 1],
            observed=(
                "Not reached because the deployed app never exposed the Workspace switcher "
                "trigger required to establish the restored workspace precondition."
            ),
        )
    _record_human_verification(
        result,
        check=(
            "Loaded the deployed app at the ticket viewport and waited for the header "
            "Workspace switcher trigger to appear before attempting TS-980."
        ),
        observed=(
            f"title={startup_observation['title']!r}; "
            f"url={startup_observation['location_href']!r}; "
            f"visible_buttons={json.dumps(startup_observation['button_labels'], ensure_ascii=True)}; "
            f"body_text={startup_observation['body_text']!r}"
        ),
    )
    raise AssertionError(
        "Step 1 failed: the deployed app never exposed the Workspace switcher trigger, so "
        "this run never reached the TS-980 reload-persistence scenario.\n"
        f"Observed startup surface:\n{json.dumps(startup_observation, indent=2)}\n"
        f"Console events:\n{json.dumps(result['console_events'], indent=2)}\n"
        f"Page errors:\n{json.dumps(result['page_errors'], indent=2)}",
    )


def _saved_workspace_action_label(
    row: WorkspaceSwitcherSavedWorkspaceRowObservation | None,
) -> str:
    if row is None:
        raise AssertionError(
            "Step 3 failed: the open workspace switcher did not expose a saved local "
            "workspace row with an actionable control.",
        )
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
            "Step 3 failed: the unavailable local workspace row did not expose any "
            "visible manual action.\n"
            f"Observed saved row: {json.dumps(_saved_row_payload(row), indent=2)}"
        )
    return action_label


def _observe_manual_restore_attempt(
    *,
    tracker_page,
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


def _observe_restored_local_workspace(
    *,
    tracker_page,
    page: LiveWorkspaceSwitcherPage,
    expected_local_workspace_id: str,
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
    trigger_is_restored = (
        trigger is not None
        and trigger["display_name"] == LOCAL_DISPLAY_NAME
        and trigger["workspace_type"] == "Local"
        and trigger["state_label"] == "Local Git"
    )
    storage_matches = (
        persisted_workspace_state is not None
        and persisted_workspace_state.get("activeWorkspaceId") == expected_local_workspace_id
    )
    restored = trigger_is_restored and bool(shell_observation.get("shell_ready")) and storage_matches
    if not restored:
        return {
            "restored": False,
            "trigger": trigger,
            "shell_observation": shell_observation,
            "persisted_workspace_state": persisted_workspace_state,
            "body_text": tracker_page.body_text(),
        }

    switcher_after = page.open_and_observe(timeout_ms=20_000)
    local_row_after = _find_named_local_row(switcher_after)
    hosted_row_after = _find_named_hosted_row(switcher_after)
    selected_row_after = _find_selected_row(switcher_after)
    return {
        "restored": True,
        "trigger": trigger,
        "shell_observation": shell_observation,
        "persisted_workspace_state": persisted_workspace_state,
        "switcher": _switcher_payload(switcher_after),
        "local_row": _row_payload(local_row_after),
        "hosted_row": _row_payload(hosted_row_after),
        "selected_row": _row_payload(selected_row_after),
    }


def _safe_trigger_payload(page: LiveWorkspaceSwitcherPage) -> dict[str, object] | None:
    try:
        return _trigger_payload(page.observe_trigger(timeout_ms=2_000))
    except AssertionError:
        return None


def _extract_workspace_open_failure_message(body_text: str) -> str | None:
    match = re.search(
        rf"Could not open {re.escape(LOCAL_DISPLAY_NAME)}\.\s*[^\n]+",
        body_text,
    )
    if match is None:
        return None
    return match.group(0).strip()


def _record_step(
    result: dict[str, object],
    *,
    step: int,
    status: str,
    action: str,
    observed: str,
) -> None:
    steps = result.setdefault("steps", [])
    if not isinstance(steps, list):
        raise TypeError("result['steps'] must be a list")
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
    verifications = result.setdefault("human_verification", [])
    if not isinstance(verifications, list):
        raise TypeError("result['human_verification'] must be a list")
    verifications.append({"check": check, "observed": observed})


def _record_request_steps_precondition_failure(
    result: dict[str, object],
    message: str,
) -> None:
    if result.get("steps"):
        return
    _record_step(
        result,
        step=1,
        status="failed",
        action=REQUEST_STEPS[0],
        observed=(
            "Not reached because the required precondition could not be established: the "
            "manual restore to `Local Git` failed before the reload could be performed.\n"
            f"{message}"
        ),
    )
    for step_number in (2, 3):
        _record_step(
            result,
            step=step_number,
            status="failed",
            action=REQUEST_STEPS[step_number - 1],
            observed=(
                "Not reached because the workspace never completed the required manual "
                "restore to `Local Git` before the reload scenario."
            ),
        )


def _observe_reloaded_workspace_surface(
    *,
    tracker_page,
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
    surface_ready = (
        trigger is not None
        and bool(shell_observation.get("shell_ready"))
        and persisted_workspace_state is not None
    )
    return {
        "surface_ready": surface_ready,
        "trigger": trigger,
        "shell_observation": shell_observation,
        "persisted_workspace_state": persisted_workspace_state,
        "body_text": tracker_page.body_text(),
    }


def _normalized_lines(text: str) -> tuple[str, ...]:
    return tuple(" ".join(line.split()).strip() for line in text.splitlines() if line.strip())


def _switcher_contains_workspace_summary(
    *,
    switcher: WorkspaceSwitcherObservation,
    display_name: str,
    target_type: str,
    state_label: str,
) -> bool:
    expected = f"{display_name} · {target_type} · {state_label}"
    return any(line == expected for line in _normalized_lines(switcher.body_text))


def _switcher_contains_workspace_detail(
    *,
    switcher: WorkspaceSwitcherObservation,
    display_name: str,
    target_type: str,
    state_label: str,
    detail_contains: str,
    branch_name: str,
) -> bool:
    return any(
        display_name in line
        and target_type in line
        and state_label in line
        and detail_contains in line
        and f"Branch: {branch_name}" in line
        for line in _normalized_lines(switcher.body_text)
    )


def _shell_shows_repository_branch(
    *,
    shell_observation: dict[str, object],
    repository_label: str,
    branch_name: str,
) -> bool:
    body_text = str(shell_observation.get("body_text", ""))
    normalized_body = " ".join(body_text.split())
    return repository_label in normalized_body and f"Branch {branch_name}" in normalized_body


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
    jira_comment = _build_jira_comment(result, passed=True)
    pr_body = _build_pr_body(result, passed=True)
    response = _build_response_summary(result, passed=True)
    review_replies = _build_review_replies(result, passed=True)
    JIRA_COMMENT_PATH.write_text(jira_comment, encoding="utf-8")
    PR_BODY_PATH.write_text(pr_body, encoding="utf-8")
    RESPONSE_PATH.write_text(response, encoding="utf-8")
    REVIEW_REPLIES_PATH.write_text(review_replies, encoding="utf-8")


def _write_failure_outputs(result: dict[str, object]) -> None:
    error = _exact_error_summary(result)
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
    jira_comment = _build_jira_comment(result, passed=False)
    pr_body = _build_pr_body(result, passed=False)
    response = _build_response_summary(result, passed=False)
    review_replies = _build_review_replies(result, passed=False)
    bug_description = _build_bug_description(result)
    JIRA_COMMENT_PATH.write_text(jira_comment, encoding="utf-8")
    PR_BODY_PATH.write_text(pr_body, encoding="utf-8")
    RESPONSE_PATH.write_text(response, encoding="utf-8")
    REVIEW_REPLIES_PATH.write_text(review_replies, encoding="utf-8")
    BUG_DESCRIPTION_PATH.write_text(bug_description, encoding="utf-8")


def _build_jira_comment(result: dict[str, object], *, passed: bool) -> str:
    status_icon = "✅" if passed else "❌"
    status_word = "PASSED" if passed else "FAILED"
    steps = result.get("steps", [])
    step_lines = [
        f"# Step {step['step']} *{step['status'].upper()}*: {step['action']}\n"
        f"Observed: {{{{code}}}}{step['observed']}{{{{code}}}}"
        for step in steps
        if isinstance(step, dict)
    ]
    verifications = result.get("human_verification", [])
    verification_lines = [
        f"* {item['check']} Observed: {{{{code}}}}{item['observed']}{{{{code}}}}"
        for item in verifications
        if isinstance(item, dict)
    ]
    lines = [
        f"h3. {status_icon} Automated test {status_word} — {TICKET_KEY}",
        "",
        f"*Test case*: {TEST_CASE_TITLE}",
        f"*Environment*: URL={result.get('app_url')} | Browser={result.get('browser')} | OS={result.get('os')}",
        f"*Viewport*: {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
        f"*Linked bugs considered*: {', '.join(LINKED_BUGS)}",
        "",
        "h4. Automation checks",
        *step_lines,
        "",
        "h4. Real user-style verification",
        *verification_lines,
        "",
        "h4. Expected result",
        EXPECTED_RESULT,
        "",
        "h4. Actual result",
        (
            "The workspace was manually restored to `Local Git`, the app was reloaded, and "
            "the same workspace remained active as `Local Git` with the expected branch "
            "details visible in the Workspace switcher."
            if passed
            else str(
                result.get(
                    "error",
                    "The reloaded app did not preserve the restored local workspace as `Local Git`.",
                ),
            )
        ),
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


def _build_pr_body(result: dict[str, object], *, passed: bool) -> str:
    steps = result.get("steps", [])
    verifications = result.get("human_verification", [])
    lines = [
        f"## {TICKET_KEY} {'passed' if passed else 'failed'}",
        "",
        "## Rework summary",
        f"- {REWORK_SUMMARY}",
        "",
        f"**Test case:** {TEST_CASE_TITLE}",
        f"**Environment:** `{result.get('app_url')}` · {result.get('browser')} · {result.get('os')}",
        f"**Viewport:** `{DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}`",
        f"**Linked bugs considered:** {', '.join(LINKED_BUGS)}",
        "",
        "## Automation checks",
    ]
    for step in steps:
        if not isinstance(step, dict):
            continue
        lines.append(
            f"- Step {step['step']} **{step['status']}** — {step['action']}  \n"
            f"  Observed: `{step['observed']}`"
        )
    lines.extend(["", "## Real user-style verification"])
    for item in verifications:
        if not isinstance(item, dict):
            continue
        lines.append(f"- **{item['check']}** Observed: `{item['observed']}`")
    lines.extend(
        [
            "",
            "## Expected result",
            EXPECTED_RESULT,
            "",
            "## Actual result",
            (
                "The restored local workspace remained the active `Local Git` workspace after "
                "the hard reload, and the Workspace switcher still showed the expected branch "
                "details."
                if passed
                else str(
                    result.get(
                        "error",
                        "The reloaded app did not preserve the restored local workspace as `Local Git`.",
                    ),
                )
            ),
        ],
    )
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


def _build_response_summary(result: dict[str, object], *, passed: bool) -> str:
    lines = [
        "## Issues/Notes",
        (
            "- Rerun passed after the manual restore used the prepared workspace snapshot."
            if passed
            else "- Rerun still failed with a product-visible gap after the repo-backed restore shim: "
            f"{_exact_error_summary(result)}"
        ),
        "",
        "## Approach",
        f"- {REWORK_SUMMARY}",
        "",
        "## Files Modified",
        "- `testing/tests/TS-980/test_ts_980.py`",
        "",
        "## Test Coverage",
        "- Manual Retry/Re-authenticate restore of the unavailable saved workspace using the prepared local repo shape.",
        "- Post-restore reload persistence for the same workspace label, `Local Git` status, and branch details.",
    ]
    return "\n".join(lines) + "\n"


def _build_bug_description(result: dict[str, object]) -> str:
    steps = result.get("steps", [])
    screenshot = result.get("screenshot")
    annotated_steps: list[str] = []
    for index, action in enumerate(REQUEST_STEPS, start=1):
        matching = next(
            (
                step
                for step in steps
                if isinstance(step, dict) and int(step.get("step", -1)) == index
            ),
            None,
        )
        if matching is None:
            annotated_steps.append(f"{index}. ⏭️ {action} Not reached.")
            continue
        status = str(matching.get("status", "failed")).lower()
        icon = "✅" if status == "passed" else "❌"
        annotated_steps.append(
            f"{index}. {icon} {action} Observed: {matching.get('observed', '')}"
        )

    actual_result = str(
        result.get(
            "error",
            "The reloaded app did not preserve the restored local workspace as `Local Git`.",
        ),
    )
    trigger_before = result.get("trigger_before_restore")
    trigger_after = result.get("trigger_after_restore")
    local_before = result.get("local_row_before_restore")
    local_after = result.get("local_row_after_restore")
    trigger_after_reload = result.get("trigger_after_reload")
    local_after_reload = result.get("local_row_after_reload")
    selected_after_reload = result.get("selected_row_after_reload")
    post_reload_state = result.get("post_reload_state")
    probe_after_action = result.get("manual_reauth_probe_after_action")
    manual_action_label = result.get("manual_restore_action_label")
    startup_observation = result.get("startup_observation")
    precondition_established = bool(result.get("precondition_established"))
    missing_capability = (
        "The deployed web build never exposed the Workspace switcher trigger needed to start "
        "the TS-980 reload-persistence scenario during this run. This failure happened before "
        "the workspace restore precondition was visible."
        if startup_observation and not precondition_established
        else (
            "The deployed web build did not complete the required manual restore to `Local Git`, "
            "so the reload scenario could not start."
            if not precondition_established
            else "The deployed web build restored the workspace once, but after the hard reload "
            "it no longer preserved the restored local workspace as the active `Local Git` state."
        )
    )
    lines = [
        f"h3. {TICKET_KEY}: Refresh application after manual restoration leaves the workspace outside Local Git",
        "",
        "h4. Environment",
        f"- URL: {result.get('app_url')}",
        f"- Browser: {result.get('browser')}",
        f"- OS: {result.get('os')}",
        f"- Viewport: {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
        f"- Local workspace target: {LOCAL_TARGET}",
        "",
        "h4. Steps to Reproduce",
        *annotated_steps,
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
        "h4. Notes",
        (
            "Automation used the visible Retry/Re-authenticate action and returned a "
            "repo-backed directory handle built from the prepared `/tmp/trackstate-ts980-workspace` "
            "contents, so this rerun exercised the same saved workspace identity and file tree "
            "instead of an unrelated OPFS-only mirror."
        ),
        f"- Missing or broken production capability: {missing_capability}",
        f"- Startup observation: `{json.dumps(startup_observation, ensure_ascii=True)}`",
        f"- Trigger before restore: `{json.dumps(trigger_before, ensure_ascii=True)}`",
        f"- Local row before restore: `{json.dumps(local_before, ensure_ascii=True)}`",
        f"- Trigger after restore: `{json.dumps(trigger_after, ensure_ascii=True)}`",
        f"- Local row after restore: `{json.dumps(local_after, ensure_ascii=True)}`",
        f"- Trigger after reload: `{json.dumps(trigger_after_reload, ensure_ascii=True)}`",
        f"- Local row after reload: `{json.dumps(local_after_reload, ensure_ascii=True)}`",
        f"- Selected row after reload: `{json.dumps(selected_after_reload, ensure_ascii=True)}`",
        f"- Post reload state: `{json.dumps(post_reload_state, ensure_ascii=True)}`",
        f"- Manual action label: `{manual_action_label}`",
        f"- Manual re-auth probe after action: `{json.dumps(probe_after_action, ensure_ascii=True)}`",
    ]
    if screenshot:
        lines.append(f"- Screenshot: `{screenshot}`")
    return "\n".join(lines) + "\n"


def _build_review_replies(result: dict[str, object], *, passed: bool) -> str:
    replies = [
        {
            "inReplyToId": thread["rootCommentId"],
            "threadId": thread["threadId"],
            "reply": _review_reply_text(result=result, passed=passed),
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


def _review_reply_text(result: dict[str, object], *, passed: bool) -> str:
    rerun_summary = (
        "Re-ran the current TS-980 test and it passed (`1 passed, 0 failed`)."
        if passed
        else "Re-ran the current TS-980 test and it still failed: "
        f"{_exact_error_summary(result)}"
    )
    return (
        "Fixed: the TS-980-specific runtime and repo-backed directory-handle shim were "
        "moved out of `testing/tests/TS-980/test_ts_980.py` into "
        "`testing/tests/support/ts980_restore_persistence_runtime.py`, so the test "
        "now stays focused on the ticket flow while the shared helper still prepares "
        "the real `/tmp/trackstate-ts980-workspace` repo snapshot and injects the "
        "manual Retry/Re-authenticate picker handle for that saved workspace. "
        f"{rerun_summary}"
    )


def _exact_error_summary(result: dict[str, object]) -> str:
    traceback_text = str(result.get("traceback", "")).strip()
    if traceback_text:
        for line in reversed(traceback_text.splitlines()):
            candidate = line.strip()
            if candidate.startswith("AssertionError:"):
                return candidate
        for line in reversed(traceback_text.splitlines()):
            candidate = line.strip()
            if candidate:
                return candidate
    error = str(result.get("error", "")).strip()
    if error:
        first_line = error.splitlines()[0].strip()
        return first_line if ":" in first_line else f"AssertionError: {first_line}"
    return f"AssertionError: {TICKET_KEY} failed"


if __name__ == "__main__":
    main()
