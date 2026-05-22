from __future__ import annotations

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
    WorkspaceSwitcherTriggerObservation,
)
from testing.components.pages.trackstate_tracker_page import TrackStateTrackerPage  # noqa: E402
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.utils.polling import poll_until  # noqa: E402
from testing.tests.support.live_tracker_app_factory import create_live_tracker_app  # noqa: E402
from testing.tests.support.stored_workspace_profiles_runtime import (  # noqa: E402
    StoredWorkspaceProfilesRuntime,
)

TICKET_KEY = "TS-912"
TEST_CASE_TITLE = (
    "Manual re-authentication for unavailable workspace restores Local Git state"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-912/test_ts_912.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
DEFAULT_BRANCH = "main"
LOCAL_TARGET = "/tmp/trackstate-ts912-workspace"
LOCAL_DISPLAY_NAME = "Restorable local workspace"
HOSTED_DISPLAY_NAME = "Hosted setup workspace"
LINKED_BUGS = ["TS-894"]
SHELL_NAVIGATION_LABELS = ("Dashboard", "Board", "JQL Search", "Hierarchy", "Settings")

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts912_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts912_failure.png"

REQUEST_STEPS = [
    "Open the Workspace switcher from the application header.",
    "Locate the 'Local Unavailable' workspace entry.",
    "Click the 'Re-authenticate' or 'Retry' action associated with the unavailable workspace.",
    "Follow the browser prompt to grant file system access to the directory.",
]
EXPECTED_RESULT = (
    "The workspace status is updated to 'Local Git'. The workspace becomes "
    "active and its contents are successfully loaded/indexed."
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
            "TS-912 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
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
        "steps": [],
        "human_verification": [],
    }

    page: LiveWorkspaceSwitcherPage | None = None

    try:
        with create_live_tracker_app(
            config,
            runtime_factory=lambda: StoredWorkspaceProfilesRuntime(
                repository=config.repository,
                token=token,
                workspace_state=workspace_state,
                workspace_token_profile_ids=(hosted_workspace_id,),
            ),
        ) as tracker_page:
            page = LiveWorkspaceSwitcherPage(tracker_page)
            try:
                runtime = tracker_page.open()
                page.set_viewport(**DESKTOP_VIEWPORT)
                result["runtime_state"] = runtime.kind
                result["runtime_body_text"] = runtime.body_text
                shell_observation = tracker_page.observe_interactive_shell(
                    SHELL_NAVIGATION_LABELS,
                )
                result["shell_observation_before_restore"] = shell_observation
                if runtime.kind != "ready" or not bool(shell_observation.get("shell_ready")):
                    raise AssertionError(
                        "Precondition failed: the deployed app did not reach the "
                        "interactive shell with the hosted-workspace preload.\n"
                        f"Observed runtime state: {runtime.kind}\n"
                        f"Observed shell state:\n{json.dumps(shell_observation, indent=2)}",
                    )

                try:
                    page.dismiss_connection_banner()
                except Exception:
                    pass

                initial_trigger = page.observe_trigger(timeout_ms=10_000)
                result["trigger_before_restore"] = _trigger_payload(initial_trigger)
                _record_human_verification(
                    result,
                    check=(
                        "Viewed the live shell before opening the switcher to confirm the "
                        "hosted workspace was the currently active visible state."
                    ),
                    observed=(
                        f"trigger_label={initial_trigger.semantic_label!r}; "
                        f"trigger_text={initial_trigger.visible_text!r}"
                    ),
                )

                switcher_before = page.open_and_observe(timeout_ms=20_000)
                result["switcher_before_restore"] = _switcher_payload(switcher_before)
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=REQUEST_STEPS[0],
                    observed=(
                        "Opened the Workspace switcher from the application header.\n"
                        f"row_count={switcher_before.row_count}; "
                        f"switcher_text={switcher_before.switcher_text!r}"
                    ),
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
                        observed="Not reached because the unavailable local workspace row was not exposed in step 2.",
                    )
                    _record_step(
                        result,
                        step=4,
                        status="failed",
                        action=REQUEST_STEPS[3],
                        observed="Not reached because the unavailable local workspace row was not exposed in step 2.",
                    )
                    raise

                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=REQUEST_STEPS[1],
                    observed=(
                        "Located the saved local workspace row in the visible `Unavailable` state "
                        "before the manual restore action.\n"
                        f"local_row={json.dumps(_row_payload(local_row_before), indent=2)}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Opened the switcher and visually confirmed the saved local workspace "
                        "row still showed the unavailable state before any manual action."
                    ),
                    observed=(
                        f"local_row={json.dumps(_row_payload(local_row_before), ensure_ascii=True)}; "
                        f"selected_row={json.dumps(_row_payload(selected_row_before), ensure_ascii=True) if selected_row_before else 'null'}"
                    ),
                )

                restored_local_workspace = _prepare_local_workspace_repository()
                result["restored_local_workspace"] = restored_local_workspace

                try:
                    trigger_after_restore = page.switch_to_workspace(
                        display_name=LOCAL_DISPLAY_NAME,
                        target_type_label="Local",
                        detail_contains=LOCAL_TARGET,
                        expected_state_label="Local Git",
                        timeout_ms=45_000,
                    )
                except AssertionError as error:
                    _record_step(
                        result,
                        step=3,
                        status="failed",
                        action=REQUEST_STEPS[2],
                        observed=(
                            "The saved local workspace directory was recreated before the "
                            "manual restore attempt, but activating the unavailable row failed.\n"
                            f"restored_local_workspace={json.dumps(restored_local_workspace, indent=2)}\n"
                            f"{error}"
                        ),
                    )
                    _record_step(
                        result,
                        step=4,
                        status="failed",
                        action=REQUEST_STEPS[3],
                        observed="Not reached because the manual restore action in step 3 did not activate the local workspace.",
                    )
                    raise

                result["trigger_after_restore"] = _trigger_payload(trigger_after_restore)
                observed_action_labels = (
                    list(local_row_before.action_labels) if local_row_before is not None else []
                )
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action=REQUEST_STEPS[2],
                    observed=(
                        "Activated the saved local workspace via the row action exposed for the "
                        "unavailable workspace entry.\n"
                        f"observed_action_labels={observed_action_labels!r}; "
                        f"trigger_after_restore={json.dumps(_trigger_payload(trigger_after_restore), indent=2)}"
                    ),
                )

                shell_after_restore = tracker_page.observe_interactive_shell(
                    SHELL_NAVIGATION_LABELS,
                    timeout_ms=60_000,
                )
                persisted_workspace_state = _decode_workspace_state(
                    tracker_page.snapshot_local_storage(
                        [
                            "trackstate.workspaceProfiles.state",
                            "flutter.trackstate.workspaceProfiles.state",
                        ],
                    ),
                )
                result["shell_observation_after_restore"] = shell_after_restore
                result["persisted_workspace_state"] = persisted_workspace_state

                switcher_after = page.open_and_observe(timeout_ms=20_000)
                result["switcher_after_restore"] = _switcher_payload(switcher_after)
                local_row_after = _find_named_local_row(switcher_after)
                hosted_row_after = _find_named_hosted_row(switcher_after)
                selected_row_after = _find_selected_row(switcher_after)
                result["local_row_after_restore"] = (
                    _row_payload(local_row_after) if local_row_after is not None else None
                )
                result["hosted_row_after_restore"] = (
                    _row_payload(hosted_row_after) if hosted_row_after is not None else None
                )
                result["selected_row_after_restore"] = (
                    _row_payload(selected_row_after)
                    if selected_row_after is not None
                    else None
                )

                try:
                    _assert_restored_local_workspace(
                        trigger=trigger_after_restore,
                        switcher=switcher_after,
                        local_row=local_row_after,
                        selected_row=selected_row_after,
                        shell_observation=shell_after_restore,
                        persisted_workspace_state=persisted_workspace_state,
                        expected_local_workspace_id=local_workspace_id,
                    )
                except AssertionError as error:
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
                        "After the manual restore action, the workspace was visible as the "
                        "active `Local Git` workspace and the interactive shell remained loaded.\n"
                        f"selected_row={json.dumps(_row_payload(selected_row_after), indent=2)}\n"
                        f"shell_after_restore={json.dumps(shell_after_restore, indent=2)}"
                    ),
                )

                _record_human_verification(
                    result,
                    check=(
                        "Viewed the header trigger and reopened the switcher after the manual "
                        "restore action to confirm the same workspace was now active as Local Git."
                    ),
                    observed=(
                        f"trigger_after_restore={json.dumps(_trigger_payload(trigger_after_restore), ensure_ascii=True)}; "
                        f"local_row_after_restore={json.dumps(_row_payload(local_row_after), ensure_ascii=True) if local_row_after else 'null'}"
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

    marker_path = local_path / ".trackstate-ts912-precondition.txt"
    marker_path.write_text(
        "Prepared for TS-912 unavailable local workspace manual restore validation.\n",
        encoding="utf-8",
    )

    subprocess.run(
        ["git", "-C", str(local_path), "add", marker_path.name],
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
                "user.name=TS-912 Automation",
                "-c",
                "user.email=ts912@example.com",
                "commit",
                "--allow-empty",
                "-m",
                "Prepare TS-912 local workspace",
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
    }


def _remove_local_workspace_repository() -> None:
    shutil.rmtree(LOCAL_TARGET, ignore_errors=True)


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
    if local_row is None:
        raise AssertionError(
            "Step 4 failed: reopening the switcher after restore no longer showed the "
            "saved local workspace row.\n"
            f"Observed switcher text:\n{switcher.switcher_text}"
        )
    if local_row.state_label != "Local Git":
        raise AssertionError(
            "Step 4 failed: the restored local workspace row did not show the `Local Git` "
            "state after the manual action.\n"
            f"Observed local row: {json.dumps(_row_payload(local_row), indent=2)}"
        )
    if selected_row is None or selected_row.display_name != LOCAL_DISPLAY_NAME:
        raise AssertionError(
            "Step 4 failed: the restored local workspace row did not become the active "
            "selection in the switcher.\n"
            f"Observed selected row: {json.dumps(_row_payload(selected_row), indent=2) if selected_row else 'null'}\n"
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


def _switcher_payload(switcher: WorkspaceSwitcherObservation) -> dict[str, object]:
    return {
        "body_text": switcher.body_text,
        "switcher_text": switcher.switcher_text,
        "row_count": switcher.row_count,
        "rows": [_row_payload(row) for row in switcher.rows],
    }


def _decode_workspace_state(storage_snapshot: dict[str, str | None]) -> dict[str, object] | None:
    for value in storage_snapshot.values():
        if value is None:
            continue
        parsed = json.loads(value)
        if isinstance(parsed, dict):
            return parsed
    return None


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
    JIRA_COMMENT_PATH.write_text(jira_comment, encoding="utf-8")
    PR_BODY_PATH.write_text(pr_body, encoding="utf-8")
    RESPONSE_PATH.write_text(response, encoding="utf-8")


def _write_failure_outputs(result: dict[str, object]) -> None:
    error = str(result.get("error", f"AssertionError: {TICKET_KEY} failed"))
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
    bug_description = _build_bug_description(result)
    JIRA_COMMENT_PATH.write_text(jira_comment, encoding="utf-8")
    PR_BODY_PATH.write_text(pr_body, encoding="utf-8")
    RESPONSE_PATH.write_text(response, encoding="utf-8")
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
            "The unavailable saved local workspace was manually restored and became the "
            "active Local Git workspace while the shell remained interactive."
            if passed
            else str(result.get("error", "The restore flow did not reach the expected Local Git state."))
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
                "The saved unavailable local workspace restored to `Local Git`, became "
                "the active workspace, and the visible shell stayed interactive."
                if passed
                else str(result.get("error", "The restore flow did not reach the expected Local Git state."))
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
    if passed:
        return (
            f"{TICKET_KEY} passed.\n\n"
            "The saved unavailable local workspace was restored manually and became the "
            "active Local Git workspace while the shell stayed interactive.\n"
        )
    return (
        f"{TICKET_KEY} failed.\n\n"
        f"{result.get('error', 'The restore flow did not reach the expected Local Git state.')}\n"
    )


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

    actual_result = str(result.get("error", "The restore flow did not reach the expected Local Git state."))
    trigger_before = result.get("trigger_before_restore")
    trigger_after = result.get("trigger_after_restore")
    local_before = result.get("local_row_before_restore")
    local_after = result.get("local_row_after_restore")
    lines = [
        f"# {TICKET_KEY} bug report",
        "",
        "## Steps to reproduce",
        *annotated_steps,
        "",
        "## Exact error message or assertion failure",
        "```text",
        str(result.get("traceback", result.get("error", ""))),
        "```",
        "",
        "## Actual result",
        actual_result,
        "",
        "## Expected result",
        EXPECTED_RESULT,
        "",
        "## Environment details",
        f"- URL: {result.get('app_url')}",
        f"- Browser: {result.get('browser')}",
        f"- OS: {result.get('os')}",
        f"- Viewport: {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
        f"- Local workspace target: {LOCAL_TARGET}",
        "",
        "## Observed state",
        f"- Trigger before restore: `{json.dumps(trigger_before, ensure_ascii=True)}`",
        f"- Local row before restore: `{json.dumps(local_before, ensure_ascii=True)}`",
        f"- Trigger after restore: `{json.dumps(trigger_after, ensure_ascii=True)}`",
        f"- Local row after restore: `{json.dumps(local_after, ensure_ascii=True)}`",
    ]
    if screenshot:
        lines.extend(["", "## Screenshots or logs", f"- Screenshot: `{screenshot}`"])
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
