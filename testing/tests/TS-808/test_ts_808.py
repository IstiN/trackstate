from __future__ import annotations

import base64
import json
import platform
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
from testing.components.pages.live_project_settings_page import (  # noqa: E402
    LiveProjectSettingsPage,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.utils.polling import poll_until  # noqa: E402
from testing.tests.support.live_tracker_app_factory import create_live_tracker_app  # noqa: E402
from testing.tests.support.ts980_restore_persistence_runtime import (  # noqa: E402
    Ts980RestorePersistenceRuntime,
    install_restorable_directory_picker,
    read_manual_reauth_probe,
    read_restorable_directory_picker_state,
)

TICKET_KEY = "TS-808"
TEST_CASE_TITLE = (
    "Active local workspace authenticated state - Connect GitHub control is hidden"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-808/test_ts_808.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 960}
DEFAULT_BRANCH = "main"
LOCAL_TARGET = "/tmp/trackstate-demo"
LOCAL_DISPLAY_NAME = "Active local workspace"
HOSTED_DISPLAY_NAME = "Hosted setup workspace"
TRIGGER_WAIT_SECONDS = 90

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
REVIEW_REPLIES_PATH = OUTPUTS_DIR / "review_replies.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts808_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts808_failure.png"

REQUEST_STEPS = [
    "Open the workspace switcher.",
    "Inspect the row representing the currently active local workspace.",
    "Verify that the 'Connect GitHub' control (button or action) is not visible.",
]
EXPECTED_RESULT = (
    "The 'Connect GitHub' control is hidden on the active local workspace row "
    "because a valid GitHub session is detected."
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
            "TS-808 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
        )
    user = service.fetch_authenticated_user()
    workspace_state = _workspace_state(service.repository)
    prepared_local_workspace = _prepare_local_workspace_repository()

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
        "user_login": user.login,
        "preloaded_workspace_state": workspace_state,
        "prepared_local_workspace": prepared_local_workspace,
        "trigger_wait_seconds": TRIGGER_WAIT_SECONDS,
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
        )
        with create_live_tracker_app(
            config,
            runtime_factory=lambda: runtime_context,
        ) as tracker_page:
            page = LiveWorkspaceSwitcherPage(tracker_page)
            try:
                runtime = tracker_page.open()
                result["runtime_state"] = runtime.kind
                result["runtime_body_text"] = runtime.body_text
                if runtime.kind != "ready":
                    raise AssertionError(
                        "Precondition failed: the deployed app did not reach the "
                        "interactive shell with the signed-in active-local workspace "
                        "preload.\n"
                        f"Observed runtime state: {runtime.kind}\n"
                        f"Observed body text:\n{runtime.body_text}",
                    )

                settings_page = LiveProjectSettingsPage(tracker_page)
                page.dismiss_connection_banner()
                page.set_viewport(**DESKTOP_VIEWPORT)
                initial_trigger = page.observe_trigger()
                result["trigger_observation"] = _trigger_payload(initial_trigger)
                _record_human_verification(
                    result,
                    check=(
                        "Viewed the live shell before the ticket steps and captured the "
                        "current workspace trigger state."
                    ),
                    observed=(
                        f"trigger_label={initial_trigger.semantic_label!r}; "
                        f"trigger_text={initial_trigger.visible_text!r}; "
                        f"top_buttons={list(initial_trigger.top_button_labels)!r}"
                    ),
                )
                try:
                    trigger = _ensure_active_local_precondition(
                        page=page,
                        tracker_page=tracker_page,
                        settings_page=settings_page,
                        token=token,
                        repository=service.repository,
                        user_login=user.login,
                        initial_trigger=initial_trigger,
                        result=result,
                    )
                except AssertionError as error:
                    _record_step(
                        result,
                        step=1,
                        status="failed",
                        action=REQUEST_STEPS[0],
                        observed=str(error),
                    )
                    _record_step(
                        result,
                        step=2,
                        status="failed",
                        action=REQUEST_STEPS[1],
                        observed="Not reached because the signed-in active-local precondition failed before step 1.",
                    )
                    _record_step(
                        result,
                        step=3,
                        status="failed",
                        action=REQUEST_STEPS[2],
                        observed="Not reached because the signed-in active-local precondition failed before step 1.",
                    )
                    raise
                result["trigger_observation"] = _trigger_payload(trigger)
                _record_human_verification(
                    result,
                    check=(
                        "Confirmed the active workspace already matched the signed-in "
                        "local precondition before opening the switcher."
                    ),
                    observed=(
                        f"trigger_label={trigger.semantic_label!r}; "
                        f"trigger_text={trigger.visible_text!r}; "
                        f"top_buttons={list(trigger.top_button_labels)!r}"
                    ),
                )

                switcher = page.open_and_observe()
                result["switcher_observation"] = _switcher_payload(switcher)
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=REQUEST_STEPS[0],
                    observed=(
                        f"Opened the workspace switcher from a signed-in session. "
                        f"trigger_label={trigger.semantic_label!r}; "
                        f"row_count={switcher.row_count}; "
                        f"switcher_text={switcher.switcher_text!r}"
                    ),
                )

                try:
                    active_local_row = _find_active_local_row(
                        switcher,
                        trigger=trigger,
                    )
                except AssertionError as error:
                    _record_step(
                        result,
                        step=2,
                        status="failed",
                        action=REQUEST_STEPS[1],
                        observed=str(error),
                    )
                    _record_step(
                        result,
                        step=3,
                        status="failed",
                        action=REQUEST_STEPS[2],
                        observed="Not reached because step 2 failed: no selected active local workspace row was available to inspect.",
                    )
                    raise
                result["active_local_row"] = _row_payload(active_local_row)
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=REQUEST_STEPS[1],
                    observed=(
                        f"Selected row display_name={active_local_row.display_name!r}; "
                        f"type={active_local_row.target_type_label!r}; "
                        f"state={active_local_row.state_label!r}; "
                        f"actions={list(active_local_row.action_labels)!r}; "
                        f"buttons={list(active_local_row.button_labels)!r}; "
                        f"visible_text={active_local_row.visible_text!r}"
                    ),
                )

                try:
                    _assert_connect_github_hidden(
                        active_local_row=active_local_row,
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
                        "The active local row did not expose any visible `Connect GitHub` "
                        "button, action label, or row text."
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Opened the workspace switcher and inspected the selected local row "
                        "the way a signed-in user would, looking specifically for any visible "
                        "`Connect GitHub` label or control."
                    ),
                    observed=(
                        f"selected_row_text={active_local_row.visible_text!r}; "
                        f"selected_row_actions={list(active_local_row.action_labels)!r}; "
                        f"selected_row_buttons={list(active_local_row.button_labels)!r}"
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
        "activeWorkspaceId": local_id,
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
                "lastOpenedAt": "2026-05-17T12:00:00.000Z",
            },
            {
                "id": hosted_id,
                "displayName": HOSTED_DISPLAY_NAME,
                "customDisplayName": HOSTED_DISPLAY_NAME,
                "targetType": "hosted",
                "target": repository,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": DEFAULT_BRANCH,
                "lastOpenedAt": "2026-05-16T12:00:00.000Z",
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

    marker_path = local_path / ".trackstate-ts808-precondition.txt"
    marker_path.write_text(
        "Prepared for TS-808 signed-in active local workspace validation.\n",
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
                "user.name=TS-808 Automation",
                "-c",
                "user.email=ts808@example.com",
                "commit",
                "--allow-empty",
                "-m",
                "Prepare TS-808 local workspace",
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


def _restorable_workspace_fixture_files() -> dict[str, str]:
    return {
        "project.json": json.dumps(
            {
                "key": "DEMO",
                "name": "TS-808 Demo",
                "repository": "local/ts-808-demo",
                "branch": DEFAULT_BRANCH,
                "defaultLocale": "en",
                "supportedLocales": ["en"],
            },
        )
        + "\n",
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
                "summary: TS-808 seeded local workspace issue",
                "assignee: ts808-user",
                "reporter: ts808-user",
                "updated: 2026-05-27T00:00:00Z",
                "---",
                "",
                "# Description",
                "",
                "Seeded local workspace content for TS-808 signed-in startup validation.",
                "",
            ],
        ),
    }


def _ensure_active_local_precondition(
    *,
    page: LiveWorkspaceSwitcherPage,
    tracker_page,
    settings_page: LiveProjectSettingsPage,
    token: str,
    repository: str,
    user_login: str,
    initial_trigger: WorkspaceSwitcherTriggerObservation,
    result: dict[str, object],
) -> WorkspaceSwitcherTriggerObservation:
    trigger = initial_trigger
    current_body_text = page.current_body_text()
    if "Connect GitHub" in current_body_text:
        connection_body_text = settings_page.ensure_connected(
            token=token,
            repository=repository,
            user_login=user_login,
        )
        result["precondition_connection_body_text"] = connection_body_text
        page.dismiss_connection_banner()
        trigger = page.observe_trigger()
        result["precondition_trigger_after_connect"] = _trigger_payload(trigger)

    restored, trigger = poll_until(
        probe=lambda: page.observe_trigger(timeout_ms=10_000),
        is_satisfied=_trigger_matches_active_local_precondition,
        timeout_seconds=TRIGGER_WAIT_SECONDS,
        interval_seconds=5,
    )
    result["precondition_trigger_after_wait"] = _trigger_payload(trigger)
    result["precondition_restored_within_wait"] = restored
    if _trigger_matches_active_local_precondition(trigger):
        return trigger

    switcher = page.open_and_observe()
    result["precondition_switcher_before_switch"] = _switcher_payload(switcher)
    local_row = _find_named_local_row(switcher)
    saved_rows = page.observe_saved_workspace_rows(timeout_ms=20_000)
    saved_local_row = _find_named_saved_local_row(saved_rows)
    local_row_summary = (
        _row_payload(local_row)
        if local_row is not None
        else {
                "matched_display_name": LOCAL_DISPLAY_NAME,
                "matched_target": LOCAL_TARGET,
                "available_rows": [_row_payload(row) for row in switcher.rows],
                "switcher_text": switcher.switcher_text,
            }
    )
    result["precondition_local_row_before_switch"] = local_row_summary
    result["precondition_saved_local_row_before_switch"] = _saved_row_payload(saved_local_row)
    _record_human_verification(
        result,
        check=(
            "Waited for startup restoration, then opened the workspace switcher to "
            "inspect the visible active workspace state before the ticket steps."
        ),
        observed=(
            f"trigger_label={trigger.semantic_label!r}; "
            f"local_row={json.dumps(local_row_summary, indent=2)}; "
            f"switcher_text={switcher.switcher_text!r}"
        ),
    )
    if local_row is not None and local_row.state_label == "Local Git":
        try:
            trigger = page.switch_to_workspace(
                display_name=LOCAL_DISPLAY_NAME,
                target_type_label="Local",
                detail_contains=LOCAL_TARGET,
                expected_state_label="Local Git",
            )
        except AssertionError as error:
            raise AssertionError(
                "Precondition failed before step 1: startup did not restore the prepared "
                f"active local workspace within {TRIGGER_WAIT_SECONDS} seconds, and the "
                "app could not activate the local workspace manually before the TS-808 "
                "checks began.\n"
                f"Observed trigger label after wait: {trigger.semantic_label!r}\n"
                f"Observed local row: {json.dumps(local_row_summary, indent=2)}\n"
                f"Observed switcher text:\n{switcher.switcher_text}\n"
                f"{error}"
            ) from error
        result["precondition_trigger_after_switch"] = _trigger_payload(trigger)
        if "Connect GitHub" in page.current_body_text():
            connection_body_text = settings_page.ensure_connected(
                token=token,
                repository=repository,
                user_login=user_login,
            )
            result["precondition_connection_body_text_after_switch"] = (
                connection_body_text
            )
            page.dismiss_connection_banner()
            trigger = page.observe_trigger()
            result["precondition_trigger_after_connect"] = _trigger_payload(trigger)
        if _trigger_matches_active_local_precondition(trigger):
            return trigger

    if local_row is not None and local_row.state_label == "Unavailable":
        trigger = _restore_unavailable_local_workspace(
            tracker_page=tracker_page,
            page=page,
            switcher=switcher,
            saved_local_row=saved_local_row,
            result=result,
        )
        if _trigger_matches_active_local_precondition(trigger):
            return trigger

    raise AssertionError(
        "Precondition failed before step 1: after waiting "
        f"{TRIGGER_WAIT_SECONDS} seconds for startup restoration, the app still could "
        "not reach the prepared signed-in active local workspace state required for "
        "TS-808.\n"
        f"Observed trigger label after wait: {trigger.semantic_label!r}\n"
        f"Observed local row: {json.dumps(local_row_summary, indent=2)}\n"
        f"Observed switcher text:\n{switcher.switcher_text}"
    )


def _restore_unavailable_local_workspace(
    *,
    tracker_page,
    page: LiveWorkspaceSwitcherPage,
    switcher: WorkspaceSwitcherObservation,
    saved_local_row: WorkspaceSwitcherSavedWorkspaceRowObservation | None,
    result: dict[str, object],
) -> WorkspaceSwitcherTriggerObservation:
    local_workspace_id = f"local:{LOCAL_TARGET}@{DEFAULT_BRANCH}"
    workspace_directory_snapshot = _workspace_directory_snapshot(Path(LOCAL_TARGET))
    install_restorable_directory_picker(
        tracker_page=tracker_page,
        directory_snapshot=workspace_directory_snapshot,
    )
    result["manual_directory_picker_fixture"] = _workspace_directory_snapshot_summary(
        workspace_directory_snapshot,
    )
    result["manual_reauth_probe_before_action"] = read_manual_reauth_probe(tracker_page)
    result["manual_directory_picker_state_before_action"] = (
        read_restorable_directory_picker_state(tracker_page)
    )
    exact_action_label = _saved_workspace_action_label(saved_local_row)
    result["manual_restore_action_label"] = exact_action_label

    page.click_saved_workspace_action_button(exact_action_label, timeout_ms=10_000)
    callback_observed, restore_attempt_observation = poll_until(
        probe=lambda: _observe_manual_restore_attempt(
            tracker_page=tracker_page,
            page=page,
        ),
        is_satisfied=lambda observation: observation["directory_access_callback_observed"]
        or observation["failure_message"] is not None,
        timeout_seconds=15,
        interval_seconds=1,
    )
    result["manual_restore_attempt_observation"] = restore_attempt_observation
    result["manual_reauth_probe_after_action"] = restore_attempt_observation["probe"]
    result["manual_directory_picker_state_after_action"] = restore_attempt_observation[
        "directory_picker_state"
    ]
    if not callback_observed:
        raise AssertionError(
            "Precondition failed before step 1: the visible saved-workspace retry action "
            "never triggered a browser directory-access callback and never restored the "
            "prepared local workspace.\n"
            f"Observed action label: {exact_action_label!r}\n"
            "Observed probe state:\n"
            f"{json.dumps(restore_attempt_observation['probe'], indent=2)}\n"
            "Observed injected picker state:\n"
            f"{json.dumps(restore_attempt_observation['directory_picker_state'], indent=2)}\n"
            f"Observed switcher text:\n{switcher.switcher_text}"
        )
    if restore_attempt_observation["failure_message"] is not None:
        raise AssertionError(
            "Precondition failed before step 1: the visible saved-workspace retry action "
            "failed in the deployed app before the active local workspace returned to "
            "`Local Git`.\n"
            f"Observed action label: {exact_action_label!r}\n"
            f"Observed failure message: {restore_attempt_observation['failure_message']}\n"
            "Observed probe state:\n"
            f"{json.dumps(restore_attempt_observation['probe'], indent=2)}\n"
            "Observed injected picker state:\n"
            f"{json.dumps(restore_attempt_observation['directory_picker_state'], indent=2)}"
        )

    restored, restored_observation = poll_until(
        probe=lambda: _observe_restored_local_workspace(
            tracker_page=tracker_page,
            page=page,
            expected_local_workspace_id=local_workspace_id,
        ),
        is_satisfied=lambda observation: observation["restored"],
        timeout_seconds=45,
        interval_seconds=2,
    )
    result["restored_workspace_observation"] = restored_observation
    if not restored:
        raise AssertionError(
            "Precondition failed before step 1: the directory-access callback was observed, "
            "but the deployed app never completed the Local Git restore flow for the "
            "prepared active local workspace.\n"
            f"Observed restore observation:\n{json.dumps(restored_observation, indent=2)}"
        )

    trigger_payload = restored_observation.get("trigger")
    if not isinstance(trigger_payload, dict):
        raise AssertionError(
            "Precondition failed before step 1: the manual restore finished without a "
            "readable workspace trigger observation.",
        )
    trigger = _trigger_from_payload(trigger_payload)
    result["precondition_trigger_after_manual_restore"] = _trigger_payload(trigger)
    result["switcher_observation_after_manual_restore"] = restored_observation.get("switcher")
    result["active_local_row_after_manual_restore"] = restored_observation.get("local_row")
    _record_human_verification(
        result,
        check=(
            "Used the visible saved-workspace retry action, completed the browser "
            "directory-access flow for the same prepared local repository, and checked "
            "that the header trigger returned to the active Local Git workspace before "
            "opening the ticket steps."
        ),
        observed=(
            f"trigger_after_restore={json.dumps(trigger_payload, ensure_ascii=True)}; "
            "local_row_after_restore="
            f"{json.dumps(restored_observation.get('local_row'), ensure_ascii=True)}"
        ),
    )
    return trigger


def _trigger_matches_active_local_precondition(
    trigger: WorkspaceSwitcherTriggerObservation,
) -> bool:
    return (
        trigger.display_name == LOCAL_DISPLAY_NAME
        and trigger.workspace_type == "Local"
        and trigger.state_label == "Local Git"
    )


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


def _find_active_local_row(
    switcher: WorkspaceSwitcherObservation,
    *,
    trigger: WorkspaceSwitcherTriggerObservation,
) -> WorkspaceSwitcherRowObservation:
    for row in switcher.rows:
        if (
            row.selected
            and row.target_type_label == "Local"
            and row.state_label == "Local Git"
        ):
            return row
    fallback_row = _active_local_row_from_visible_switcher_text(
        switcher=switcher,
        trigger=trigger,
    )
    if fallback_row is not None:
        return fallback_row
    raise AssertionError(
        "Step 2 failed: the workspace switcher did not show a selected active local "
        "workspace row in the `Local Git` state after startup.\n"
        f"Observed trigger label: {trigger.semantic_label!r}\n"
        f"Observed rows: {[row.visible_text for row in switcher.rows]!r}\n"
        f"Observed switcher text:\n{switcher.switcher_text}"
    )


def _active_local_row_from_visible_switcher_text(
    *,
    switcher: WorkspaceSwitcherObservation,
    trigger: WorkspaceSwitcherTriggerObservation,
) -> WorkspaceSwitcherRowObservation | None:
    if not _trigger_matches_active_local_precondition(trigger):
        return None
    summary = (
        f"{LOCAL_DISPLAY_NAME}, Local, Local Git, {LOCAL_TARGET} • Branch: {DEFAULT_BRANCH}"
    )
    if summary not in switcher.switcher_text:
        return None
    tail = switcher.switcher_text.split(summary, 1)[1]
    hosted_summary_prefix = f"{HOSTED_DISPLAY_NAME}, Hosted,"
    row_region = tail.split(hosted_summary_prefix, 1)[0]
    visible_actions: list[str] = []
    if "Connect GitHub" in row_region:
        visible_actions.append("Connect GitHub")
    return WorkspaceSwitcherRowObservation(
        display_name=LOCAL_DISPLAY_NAME,
        target_type_label="Local",
        state_label="Local Git",
        detail_text=f"{LOCAL_TARGET} • Branch: {DEFAULT_BRANCH}",
        visible_text=" ".join([summary, *visible_actions]).strip(),
        selected=True,
        semantics_label=summary,
        icon_accessibility_label=None,
        action_labels=tuple(visible_actions),
        button_labels=tuple(visible_actions),
    )


def _saved_workspace_action_label(
    row: WorkspaceSwitcherSavedWorkspaceRowObservation | None,
) -> str:
    if row is None:
        raise AssertionError(
            "Precondition failed before step 1: the open workspace switcher did not "
            "expose a saved local workspace row with a visible manual action.",
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
            "Precondition failed before step 1: the unavailable local workspace row "
            "did not expose any visible manual action.\n"
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
        ("Dashboard", "Board", "JQL Search", "Hierarchy", "Settings"),
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
    restored = (
        trigger_is_restored
        and bool(shell_observation.get("shell_ready"))
        and storage_matches
    )
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
    selected_row_after = next((row for row in switcher_after.rows if row.selected), None)
    return {
        "restored": True,
        "trigger": trigger,
        "shell_observation": shell_observation,
        "persisted_workspace_state": persisted_workspace_state,
        "switcher": _switcher_payload(switcher_after),
        "local_row": _row_payload(local_row_after) if local_row_after is not None else None,
        "selected_row": (
            _row_payload(selected_row_after) if selected_row_after is not None else None
        ),
    }


def _safe_trigger_payload(page: LiveWorkspaceSwitcherPage) -> dict[str, object] | None:
    try:
        return _trigger_payload(page.observe_trigger(timeout_ms=2_000))
    except AssertionError:
        return None


def _extract_workspace_open_failure_message(body_text: str) -> str | None:
    marker = f"Could not open {LOCAL_DISPLAY_NAME}."
    if marker not in body_text:
        return None
    for line in body_text.splitlines():
        normalized = " ".join(line.split())
        if marker in normalized:
            return normalized
    return marker


def _workspace_directory_snapshot(local_path: Path) -> dict[str, object]:
    relative_paths = [
        ".git/HEAD",
        ".git/config",
        ".trackstate-ts808-precondition.txt",
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


def _assert_connect_github_hidden(
    *,
    active_local_row: WorkspaceSwitcherRowObservation,
) -> None:
    row_actions = [*active_local_row.action_labels, *active_local_row.button_labels]
    if any(label == "Connect GitHub" for label in row_actions):
        raise AssertionError(
            "Step 3 failed: the active local workspace row still exposed a visible "
            "`Connect GitHub` action while the user was already signed in.\n"
            f"Observed row actions/buttons: {row_actions!r}\n"
            f"Observed row text: {active_local_row.visible_text!r}"
        )
    if "Connect GitHub" in active_local_row.visible_text:
        raise AssertionError(
            "Step 3 failed: the active local workspace row still rendered "
            "`Connect GitHub` in its visible text while the user was already signed in.\n"
            f"Observed row text: {active_local_row.visible_text!r}"
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
    REVIEW_REPLIES_PATH.write_text('{"replies":[]}\n', encoding="utf-8")
    JIRA_COMMENT_PATH.write_text(_jira_comment(result, passed=True), encoding="utf-8")
    PR_BODY_PATH.write_text(_markdown_summary(result, passed=True), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_summary(result, passed=True), encoding="utf-8")


def _write_failure_outputs(result: dict[str, object]) -> None:
    error = str(result.get("error", "AssertionError: TS-808 failed"))
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
    REVIEW_REPLIES_PATH.write_text('{"replies":[]}\n', encoding="utf-8")
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
        "h4. What was automated",
        "* Opened the deployed TrackState app in Chromium with a preloaded active local workspace profile and the configured GitHub credentials available for the signed-in precondition flow.",
        "* Opened *Workspace switcher* and verified the selected row represented the active local workspace in the visible {{Local Git}} state.",
        "* Verified the selected active local row did not expose any visible {{Connect GitHub}} action, button, or visible row text while signed in.",
        "",
        "h4. Human-style verification",
        *_human_lines(result, jira=True),
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
        "- Opened the deployed TrackState app in Chromium with a preloaded active local workspace profile and the configured GitHub credentials available for the signed-in precondition flow.",
        "- Opened **Workspace switcher** and verified the selected row represented the active local workspace in the visible `Local Git` state.",
        "- Verified the selected active local row did not expose any visible `Connect GitHub` action, button, or visible row text while signed in.",
        "",
        "## Human-style verification",
        *_human_lines(result, jira=False),
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
        "- Added TS-808 live workspace-switcher coverage for the signed-in active-local workspace state, including precondition handling that tries to switch to the prepared local workspace before the ticket steps.",
        f"- Test case: **{TICKET_KEY} - {TEST_CASE_TITLE}**",
        f"- Result: **{status}**",
        f"- Command: `{RUN_COMMAND}`",
        (
            f"- Environment: `{result['app_url']}` on Chromium/Playwright "
            f"({result['os']}) against `{result['repository']}` @ "
            f"`{result['repository_ref']}`."
        ),
        (
            "- Outcome: the signed-in active local workspace row kept `Connect GitHub` hidden."
            if passed
            else f"- Outcome: {_failed_step_summary(result)}"
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
            f"# {_bug_title(result)}",
            "",
            "## Preconditions used during the run",
            "- User was signed in to GitHub via a stored browser token.",
            f"- Browser storage was preloaded with an active local workspace (`{LOCAL_TARGET}`) and one hosted workspace.",
            (
                f"- The local workspace path was prepared as a git repository at "
                f"`{LOCAL_TARGET}` before opening the app."
            ),
            "",
            "## Exact steps to reproduce",
            _annotated_step_line(result, 1, REQUEST_STEPS[0]),
            _annotated_step_line(result, 2, REQUEST_STEPS[1]),
            _annotated_step_line(result, 3, REQUEST_STEPS[2]),
            "",
            "## Expected result",
            EXPECTED_RESULT,
            "",
            "## Actual result",
            str(result.get("error", "<missing error>")),
            "",
            "## Missing or broken production-visible capability",
            _bug_capability_gap(result),
            "",
            "## Exact error message or assertion failure",
            "```text",
            str(result.get("traceback", result.get("error", ""))),
            "```",
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
            "```json",
            json.dumps(
                {
                    "prepared_local_workspace": result.get("prepared_local_workspace"),
                    "trigger_observation": result.get("trigger_observation"),
                    "precondition_switcher_before_switch": result.get(
                        "precondition_switcher_before_switch"
                    ),
                    "precondition_local_row_before_switch": result.get(
                        "precondition_local_row_before_switch"
                    ),
                    "active_local_row": result.get("active_local_row"),
                    "switcher_observation": result.get("switcher_observation"),
                },
                indent=2,
            ),
            "```",
        ],
    ) + "\n"


def _annotated_step_line(
    result: dict[str, object],
    step_number: int,
    action: str,
) -> str:
    status = _step_status(result, step_number)
    marker = "✅" if status == "passed" else "❌"
    observation = _step_observation(result, step_number)
    if observation == "<no observation recorded>" and _has_prior_failed_step(
        result,
        step_number,
    ):
        observation = "Not reached because an earlier step failed."
    return (
        f"{step_number}. {marker} {action}\n"
        f"   Actual: {observation}"
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


def _failed_step_number(result: dict[str, object]) -> int | None:
    steps = result.get("steps", [])
    if isinstance(steps, list):
        for step in steps:
            if isinstance(step, dict) and step.get("status") != "passed":
                return int(step.get("step", -1))
    return None


def _bug_title(result: dict[str, object]) -> str:
    failed_step = _failed_step_number(result)
    error = str(result.get("error", ""))
    if failed_step == 3:
        return (
            f"{TICKET_KEY} - Active local workspace row still shows Connect GitHub "
            "while signed in"
        )
    if failed_step == 2:
        return (
            f"{TICKET_KEY} - Active local workspace row was not selected in the "
            "Local Git state"
        )
    if "Precondition failed before step 1" in error:
        return (
            f"{TICKET_KEY} - Startup did not restore the signed-in active local "
            "workspace before verification"
        )
    return (
        f"{TICKET_KEY} - Active local workspace did not meet the signed-in Local Git "
        "precondition"
    )


def _bug_capability_gap(result: dict[str, object]) -> str:
    failed_step = _failed_step_number(result)
    error = str(result.get("error", ""))
    if failed_step == 3:
        return (
            "While signed in to GitHub with the active local workspace row already "
            "selected, the row still exposed a visible `Connect GitHub` label or action "
            "instead of hiding it."
        )
    if failed_step == 2:
        return (
            "After opening Workspace switcher from the prepared signed-in session, the "
            "app did not render the selected active local workspace row in the expected "
            "`Local Git` state, so the TS-808 assertion target was unavailable."
        )
    if "Precondition failed before step 1" in error:
        return (
            "After waiting for startup restoration, the app still could not reach the "
            "signed-in active local workspace state needed for the TS-808 row-level "
            "visibility check. The trigger remained on the hosted workspace and the "
            "prepared local row did not become the active `Local Git` workspace."
        )
    return (
        "The TS-808 scenario could not reach the expected signed-in active local "
        "workspace state needed to verify the row-level `Connect GitHub` visibility."
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
    for step in steps:
        if isinstance(step, dict) and int(step.get("step", -1)) == step_number:
            return str(step.get("observed", "<no observation recorded>"))
    return "<no observation recorded>"


def _has_prior_failed_step(result: dict[str, object], step_number: int) -> bool:
    steps = result.get("steps", [])
    if not isinstance(steps, list):
        return False
    for step in steps:
        if not isinstance(step, dict):
            continue
        candidate_step = int(step.get("step", -1))
        if candidate_step < step_number and step.get("status") != "passed":
            return True
    return False


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


def _trigger_from_payload(payload: dict[str, object]) -> WorkspaceSwitcherTriggerObservation:
    bounds = payload.get("bounds", {})
    return WorkspaceSwitcherTriggerObservation(
        viewport_width=float(payload["viewport_width"]),
        viewport_height=float(payload["viewport_height"]),
        semantic_label=str(payload["semantic_label"]),
        visible_text=str(payload["visible_text"]),
        raw_text_lines=tuple(str(line) for line in payload["raw_text_lines"]),
        display_name=str(payload["display_name"]),
        workspace_type=str(payload["workspace_type"]),
        state_label=str(payload["state_label"]),
        icon_count=int(payload.get("icon_count", 0)),
        left=float(bounds.get("left", 0.0)) if isinstance(bounds, dict) else 0.0,
        top=float(bounds.get("top", 0.0)) if isinstance(bounds, dict) else 0.0,
        width=float(bounds.get("width", 0.0)) if isinstance(bounds, dict) else 0.0,
        height=float(bounds.get("height", 0.0)) if isinstance(bounds, dict) else 0.0,
        top_button_labels=tuple(str(label) for label in payload["top_button_labels"]),
    )


def _switcher_payload(switcher: WorkspaceSwitcherObservation) -> dict[str, object]:
    return {
        "row_count": switcher.row_count,
        "switcher_text": switcher.switcher_text,
        "rows": [_row_payload(row) for row in switcher.rows],
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


def _remove_local_workspace_repository() -> None:
    shutil.rmtree(LOCAL_TARGET, ignore_errors=True)


if __name__ == "__main__":
    main()
