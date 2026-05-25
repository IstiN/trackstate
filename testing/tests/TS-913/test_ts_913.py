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
from testing.tests.support.ts723_workspace_restore_runtime import (  # noqa: E402
    Ts723WorkspaceRestoreRuntime,
)

TICKET_KEY = "TS-913"
TEST_CASE_TITLE = (
    "Workspace state machine guard — Local Unavailable status persists "
    "without manual action"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-913/test_ts_913.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
DEFAULT_BRANCH = "main"
LOCAL_TARGET = "/tmp/trackstate-ts913-workspace"
LOCAL_DISPLAY_NAME = "Guarded local workspace"
HOSTED_DISPLAY_NAME = "Hosted setup workspace"
STARTUP_RETRY_WAIT_SECONDS = 15
LINKED_BUGS = ["TS-915", "TS-914", "TS-894"]
SHELL_NAVIGATION_LABELS = ("Dashboard", "Board", "JQL Search", "Hierarchy", "Settings")

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts913_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts913_failure.png"

REQUEST_STEPS = [
    "Refresh the application browser tab to trigger the initialization logic.",
    "Wait for the startup sequence and retries to finish.",
    "Open the Workspace switcher.",
    "Observe the status label for the local workspace.",
]
EXPECTED_RESULT = (
    "The workspace remains in 'Local Unavailable' status. The application does "
    "not automatically restore it to 'Local Git' despite the file system being "
    "technically accessible, ensuring state consistency until a manual "
    "re-authentication is performed."
)


class Ts913WorkspaceStateGuardRuntime(Ts723WorkspaceRestoreRuntime):
    """Preserve the phase-one workspace state across the manual refresh."""

    def __init__(
        self,
        *,
        repository: str,
        token: str,
        workspace_state: dict[str, object],
    ) -> None:
        super().__init__(
            repository=repository,
            token=token,
            workspace_state=workspace_state,
            viewport=DESKTOP_VIEWPORT,
        )
    def _build_preload_script(self) -> str:
        serialized_workspace_state = json.dumps(self._workspace_state)
        return "".join(
            [
                "(() => {",
                f"const repositoryStorageKey = {json.dumps(self._repository_storage_key)};",
                f"const token = {json.dumps(self._token)};",
                f"const workspaceState = {json.dumps(serialized_workspace_state)};",
                "for (const key of [",
                "  'trackstate.workspaceProfiles.state',",
                "  'flutter.trackstate.workspaceProfiles.state',",
                "]) {",
                "  if (window.localStorage.getItem(key) === null) {",
                "    window.localStorage.setItem(key, workspaceState);",
                "  }",
                "}",
                "for (const key of [",
                "  `trackstate.githubToken.${repositoryStorageKey}`,",
                "  `flutter.trackstate.githubToken.${repositoryStorageKey}`,",
                "]) {",
                "  if (window.localStorage.getItem(key) === null) {",
                "    window.localStorage.setItem(key, token);",
                "  }",
                "}",
                "})();",
            ],
        )


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)
    _cleanup_local_workspace()
    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "test_case_title": TEST_CASE_TITLE,
        "app_url": "",
        "repository": "",
        "repository_ref": "",
        "browser": "Chromium (Playwright)",
        "os": platform.platform(),
        "run_command": RUN_COMMAND,
        "expected_result": EXPECTED_RESULT,
        "desktop_viewport": DESKTOP_VIEWPORT,
        "linked_bugs": LINKED_BUGS,
        "steps": [],
        "human_verification": [],
    }
    page: LiveWorkspaceSwitcherPage | None = None

    try:
        config = load_live_setup_test_config()
        result["app_url"] = config.app_url

        service = LiveSetupRepositoryService(config=config)
        result["repository"] = service.repository
        result["repository_ref"] = service.ref

        token = service.token
        if not token:
            raise RuntimeError(
                "TS-913 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
            )

        workspace_state = _workspace_state(service.repository)
        deleted_local_workspace = _prepare_deleted_local_workspace_repository()
        result["startup_retry_wait_seconds"] = STARTUP_RETRY_WAIT_SECONDS
        result["preloaded_workspace_state"] = workspace_state
        result["deleted_local_workspace"] = deleted_local_workspace

        runtime = Ts913WorkspaceStateGuardRuntime(
            repository=config.repository,
            token=token,
            workspace_state=workspace_state,
        )
        with runtime as session:
            tracker_page = TrackStateTrackerPage(session, config.app_url)
            page = LiveWorkspaceSwitcherPage(tracker_page)
            try:
                _open_ready_shell(
                    tracker_page,
                    page,
                    result=result,
                    runtime_key="initial_runtime_state",
                    shell_key="initial_shell_observation",
                    failure_step_label="the Local Unavailable precondition scenario",
                )
                result["precondition_summary"] = (
                    "Preloaded a hosted workspace as active while keeping the saved local "
                    "workspace marked unavailable in persisted browser state, then opened "
                    "the deployed app with the local path still missing."
                )

                initial_trigger_samples: list[dict[str, object]] = []

                def sample_initial_trigger() -> WorkspaceSwitcherTriggerObservation:
                    trigger = page.observe_trigger(timeout_ms=10_000)
                    initial_trigger_samples.append(_trigger_payload(trigger))
                    return trigger

                _, initial_trigger = poll_until(
                    probe=sample_initial_trigger,
                    is_satisfied=lambda _: False,
                    timeout_seconds=STARTUP_RETRY_WAIT_SECONDS,
                    interval_seconds=5,
                )
                result["initial_trigger_samples"] = initial_trigger_samples
                result["initial_trigger_observation"] = _trigger_payload(initial_trigger)
                initial_restore_message = _observe_restore_message(tracker_page)
                if initial_restore_message is not None:
                    result["initial_restore_message"] = initial_restore_message

                initial_switcher = page.open_and_observe(timeout_ms=20_000)
                initial_saved_rows = page.observe_accessible_saved_workspace_rows(
                    timeout_ms=20_000,
                )
                initial_local_row = _find_named_local_row_in_rows(initial_saved_rows)
                initial_selected_row = _find_selected_row(initial_switcher) or _selected_row_from_trigger(
                    initial_trigger,
                )
                result["initial_switcher_observation"] = _switcher_payload(initial_switcher)
                result["initial_accessible_saved_rows"] = [
                    _row_payload(row) for row in initial_saved_rows
                ]
                result["initial_local_row"] = _row_payload(initial_local_row)
                result["initial_selected_row"] = _row_payload(initial_selected_row)
                result["pre_refresh_persisted_workspace_state"] = _decode_workspace_state(
                    tracker_page.snapshot_local_storage(
                        [
                            "trackstate.workspaceProfiles.state",
                            "flutter.trackstate.workspaceProfiles.state",
                        ],
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Opened Workspace switcher before restoring the folder and "
                        "visually inspected the saved local workspace row to confirm "
                        "the ticket precondition."
                    ),
                    observed=(
                        f"trigger_label={initial_trigger.semantic_label!r}; "
                        f"local_row={json.dumps(_row_payload(initial_local_row), ensure_ascii=True)}; "
                        f"selected_row={json.dumps(_row_payload(initial_selected_row), ensure_ascii=True)}"
                    ),
                )
                try:
                    _assert_local_unavailable_precondition(
                        trigger=initial_trigger,
                        switcher=initial_switcher,
                        local_row=initial_local_row,
                    )
                except AssertionError as error:
                    result["precondition_failure"] = str(error)
                    raise
                result["precondition_established"] = True

                restored_local_workspace = _prepare_local_workspace_repository(
                    marker_text=(
                        "Restored for TS-913 after the app had already entered the "
                        "Local Unavailable state.\n"
                    ),
                )
                result["restored_local_workspace"] = restored_local_workspace

                _open_ready_shell(
                    tracker_page,
                    page,
                    result=result,
                    runtime_key="refresh_runtime_state",
                    shell_key="refresh_shell_observation",
                    failure_step_label="the refreshed state-guard scenario",
                )
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=REQUEST_STEPS[0],
                    observed=(
                        "Restored the saved local workspace path outside the app at "
                        f"{LOCAL_TARGET!r}, then refreshed the deployed browser tab "
                        "without any manual workspace gesture."
                    ),
                )

                final_trigger_samples: list[dict[str, object]] = []

                def sample_final_trigger() -> WorkspaceSwitcherTriggerObservation:
                    trigger = page.observe_trigger(timeout_ms=10_000)
                    final_trigger_samples.append(_trigger_payload(trigger))
                    return trigger

                _, final_trigger = poll_until(
                    probe=sample_final_trigger,
                    is_satisfied=lambda _: False,
                    timeout_seconds=STARTUP_RETRY_WAIT_SECONDS,
                    interval_seconds=5,
                )
                result["final_trigger_samples"] = final_trigger_samples
                result["final_trigger_observation"] = _trigger_payload(final_trigger)
                final_restore_message = _observe_restore_message(tracker_page)
                if final_restore_message is not None:
                    result["final_restore_message"] = final_restore_message
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=REQUEST_STEPS[1],
                    observed=(
                        "Waited beyond the startup revalidation window after the refresh "
                        f"({STARTUP_RETRY_WAIT_SECONDS} seconds) before asserting the final state. "
                        f"Observed final trigger label={final_trigger.semantic_label!r}"
                        + (
                            f"; restore_message={final_restore_message!r}"
                            if final_restore_message
                            else ""
                        )
                    ),
                )

                final_switcher = page.open_and_observe(timeout_ms=20_000)
                final_saved_rows = page.observe_accessible_saved_workspace_rows(
                    timeout_ms=20_000,
                )
                result["final_switcher_observation"] = _switcher_payload(final_switcher)
                result["final_accessible_saved_rows"] = [
                    _row_payload(row) for row in final_saved_rows
                ]
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action=REQUEST_STEPS[2],
                    observed=(
                        "Opened Workspace switcher after the refresh wait window.\n"
                        f"row_count={final_switcher.row_count}; "
                        f"accessible_saved_row_count={len(final_saved_rows)}; "
                        f"switcher_text={final_switcher.switcher_text!r}"
                    ),
                )

                final_local_row = _find_named_local_row_in_rows(final_saved_rows)
                final_selected_row = _find_selected_row(final_switcher) or _selected_row_from_trigger(
                    final_trigger,
                )
                result["final_local_row"] = _row_payload(final_local_row)
                result["final_selected_row"] = _row_payload(final_selected_row)
                result["post_refresh_persisted_workspace_state"] = _decode_workspace_state(
                    tracker_page.snapshot_local_storage(
                        [
                            "trackstate.workspaceProfiles.state",
                            "flutter.trackstate.workspaceProfiles.state",
                        ],
                    ),
                )
                result["console_events"] = [
                    {"level": event.level, "text": event.text}
                    for event in runtime.console_events
                ]
                result["page_errors"] = list(runtime.page_errors)
                _record_human_verification(
                    result,
                    check=(
                        "Viewed the header workspace switcher trigger after restoring the "
                        "folder on disk and refreshing the browser tab."
                    ),
                    observed=(
                        f"trigger_label={final_trigger.semantic_label!r}; "
                        f"trigger_text={final_trigger.visible_text!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Opened Workspace switcher after the refresh and visually "
                        "inspected the saved local workspace row where a user would look "
                        "for the status label."
                    ),
                    observed=(
                        f"local_row={json.dumps(_row_payload(final_local_row), ensure_ascii=True)}; "
                        f"selected_row={json.dumps(_row_payload(final_selected_row), ensure_ascii=True)}"
                    ),
                )

                try:
                    _assert_guard_persists_without_manual_action(
                        trigger=final_trigger,
                        switcher=final_switcher,
                        local_row=final_local_row,
                        selected_row=final_selected_row,
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
                        "The saved local workspace row still showed `Local Unavailable` "
                        "after the folder was restored and the app was refreshed without "
                        "any manual re-authentication.\n"
                        f"local_row={json.dumps(_row_payload(final_local_row), indent=2)}"
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
        _cleanup_local_workspace()

    _write_pass_outputs(result)
    print(f"{TICKET_KEY} passed")


def _open_ready_shell(
    tracker_page: TrackStateTrackerPage,
    page: LiveWorkspaceSwitcherPage,
    *,
    result: dict[str, object],
    runtime_key: str,
    shell_key: str,
    failure_step_label: str,
) -> None:
    runtime_observation = tracker_page.open()
    page.set_viewport(**DESKTOP_VIEWPORT)
    result[runtime_key] = {
        "kind": runtime_observation.kind,
        "body_text": runtime_observation.body_text,
    }
    shell_observation = tracker_page.observe_interactive_shell(
        SHELL_NAVIGATION_LABELS,
    )
    result[shell_key] = shell_observation
    if runtime_observation.kind != "ready" or not bool(shell_observation.get("shell_ready")):
        raise AssertionError(
            "The deployed app did not reach the interactive shell for "
            f"{failure_step_label}.\n"
            f"Observed runtime state: {runtime_observation.kind}\n"
            f"Observed shell state:\n{json.dumps(shell_observation, indent=2)}",
        )
    try:
        page.dismiss_connection_banner()
    except Exception:
        pass


def _workspace_state(repository: str) -> dict[str, object]:
    local_id = f"local:{LOCAL_TARGET}@{DEFAULT_BRANCH}"
    hosted_id = f"hosted:{repository.lower()}@{DEFAULT_BRANCH}"
    return {
        "activeWorkspaceId": hosted_id,
        "migrationComplete": True,
        "unavailableLocalWorkspaceIds": [local_id],
        "profiles": [
            {
                "id": local_id,
                "displayName": LOCAL_DISPLAY_NAME,
                "customDisplayName": LOCAL_DISPLAY_NAME,
                "targetType": "local",
                "target": LOCAL_TARGET,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": DEFAULT_BRANCH,
                "lastOpenedAt": "2026-05-21T12:00:00.000Z",
            },
            {
                "id": hosted_id,
                "displayName": HOSTED_DISPLAY_NAME,
                "customDisplayName": HOSTED_DISPLAY_NAME,
                "targetType": "hosted",
                "target": repository,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": DEFAULT_BRANCH,
                "lastOpenedAt": "2026-05-21T11:50:00.000Z",
            },
        ],
    }


def _prepare_deleted_local_workspace_repository() -> dict[str, object]:
    prepared = _prepare_local_workspace_repository(
        marker_text="Prepared for TS-913 Local Unavailable guard validation.\n",
    )
    _cleanup_local_workspace()
    prepared["deleted_before_startup"] = True
    return prepared


def _prepare_local_workspace_repository(*, marker_text: str) -> dict[str, object]:
    local_path = Path(LOCAL_TARGET)
    if local_path.exists():
        shutil.rmtree(local_path)
    local_path.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        ["git", "init", "--initial-branch", DEFAULT_BRANCH, str(local_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    marker_path = local_path / ".trackstate-ts913-marker.txt"
    marker_path.write_text(marker_text, encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(local_path), "add", marker_path.name],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        [
            "git",
            "-C",
            str(local_path),
            "-c",
            "user.name=TS-913 Automation",
            "-c",
            "user.email=ts913@example.com",
            "commit",
            "--allow-empty",
            "-m",
            "Prepare TS-913 local workspace",
        ],
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
    return {
        "path": str(local_path),
        "head": head.stdout.strip(),
        "marker_path": str(marker_path),
    }


def _cleanup_local_workspace() -> None:
    local_path = Path(LOCAL_TARGET)
    if local_path.exists():
        shutil.rmtree(local_path)


def _observe_restore_message(tracker_page: TrackStateTrackerPage) -> str | None:
    try:
        observation = tracker_page.observe_workspace_restore_message(
            workspace_name=LOCAL_DISPLAY_NAME,
            timeout_ms=5_000,
        )
    except Exception:
        return None
    return observation.message_text


def _find_named_local_row(
    switcher: WorkspaceSwitcherObservation,
) -> WorkspaceSwitcherRowObservation | None:
    row = _find_named_local_row_in_rows(switcher.rows)
    return row or _fallback_local_row_from_switcher_text(switcher.switcher_text)


def _find_named_local_row_in_rows(
    rows: tuple[WorkspaceSwitcherRowObservation, ...] | list[WorkspaceSwitcherRowObservation],
) -> WorkspaceSwitcherRowObservation | None:
    for row in rows:
        if (
            row.target_type_label == "Local"
            and (
                row.display_name == LOCAL_DISPLAY_NAME
                or LOCAL_TARGET in row.detail_text
                or LOCAL_TARGET in row.visible_text
            )
        ):
            return row
    return None


def _find_selected_row(
    switcher: WorkspaceSwitcherObservation,
) -> WorkspaceSwitcherRowObservation | None:
    for row in switcher.rows:
        if row.selected:
            return row
    return None


def _selected_row_from_trigger(
    trigger: WorkspaceSwitcherTriggerObservation,
) -> WorkspaceSwitcherRowObservation:
    return WorkspaceSwitcherRowObservation(
        display_name=trigger.display_name or None,
        target_type_label=trigger.workspace_type or None,
        state_label=trigger.state_label or None,
        detail_text="",
        visible_text=trigger.semantic_label,
        selected=True,
        semantics_label=trigger.semantic_label,
        icon_accessibility_label=None,
        action_labels=("Active",),
        button_labels=(),
    )


def _fallback_local_row_from_switcher_text(
    switcher_text: str,
) -> WorkspaceSwitcherRowObservation | None:
    normalized = " ".join(switcher_text.split())
    detail_text = f"{LOCAL_TARGET} • Branch: {DEFAULT_BRANCH}"
    anchor = f"{LOCAL_DISPLAY_NAME} {detail_text} Local "
    if anchor not in normalized:
        return None

    tail = normalized.split(anchor, 1)[1]
    state_label = None
    for candidate in (
        "Local Git",
        "Unavailable",
        "Needs sign-in",
        "Connected",
        "Read-only",
        "Attachments limited",
    ):
        if tail.startswith(candidate):
            state_label = candidate
            tail = tail[len(candidate) :].strip()
            break
    if state_label is None:
        return None

    action = "Active" if tail.startswith("Active") else "Open" if tail.startswith("Open") else None
    if action is None:
        return None

    visible_text = f"{LOCAL_DISPLAY_NAME} {detail_text} Local {state_label} {tail}".strip()
    return WorkspaceSwitcherRowObservation(
        display_name=LOCAL_DISPLAY_NAME,
        target_type_label="Local",
        state_label=state_label,
        detail_text=detail_text,
        visible_text=visible_text,
        selected=action == "Active",
        semantics_label=None,
        icon_accessibility_label=None,
        action_labels=((action,) if action else ()),
        button_labels=("Delete",) if action == "Active" else ((action, "Delete") if action else ()),
    )


def _assert_local_unavailable_precondition(
    *,
    trigger: WorkspaceSwitcherTriggerObservation,
    switcher: WorkspaceSwitcherObservation,
    local_row: WorkspaceSwitcherRowObservation | None,
) -> None:
    if local_row is None:
        raise AssertionError(
            "Precondition failed: Workspace switcher did not show the saved local "
            "workspace row before the refresh.\n"
            f"Observed trigger label: {trigger.semantic_label!r}\n"
            f"Observed switcher text:\n{switcher.switcher_text}",
        )
    if local_row.state_label != "Unavailable" and "Local Unavailable" not in local_row.visible_text:
        raise AssertionError(
            "Precondition failed: the saved local workspace row did not reach "
            "`Local Unavailable` before the refresh.\n"
            f"Observed local row: {json.dumps(_row_payload(local_row), indent=2)}",
        )
    if local_row.state_label == "Local Git" or "Local Git" in local_row.visible_text:
        raise AssertionError(
            "Precondition failed: the saved local workspace row recovered to "
            "`Local Git` before the refresh, so the Local Unavailable guard state "
            "was never established.\n"
            f"Observed local row: {json.dumps(_row_payload(local_row), indent=2)}",
        )


def _assert_guard_persists_without_manual_action(
    *,
    trigger: WorkspaceSwitcherTriggerObservation,
    switcher: WorkspaceSwitcherObservation,
    local_row: WorkspaceSwitcherRowObservation | None,
    selected_row: WorkspaceSwitcherRowObservation | None,
) -> None:
    if local_row is None:
        raise AssertionError(
            "Step 4 failed: Workspace switcher did not show the saved local workspace row "
            "after the refresh.\n"
            f"Observed trigger label: {trigger.semantic_label!r}\n"
            f"Observed switcher text:\n{switcher.switcher_text}",
        )
    if local_row.state_label != "Unavailable" and "Local Unavailable" not in local_row.visible_text:
        raise AssertionError(
            "Step 4 failed: the saved local workspace row did not remain in the "
            "`Local Unavailable` state after the folder was restored and the app "
            "was refreshed.\n"
            f"Observed local row: {json.dumps(_row_payload(local_row), indent=2)}",
        )
    if local_row.state_label == "Local Git" or "Local Git" in local_row.visible_text:
        raise AssertionError(
            "Step 4 failed: the saved local workspace row recovered to `Local Git` "
            "without a manual recovery action.\n"
            f"Observed local row: {json.dumps(_row_payload(local_row), indent=2)}",
        )
    if (
        trigger.display_name == LOCAL_DISPLAY_NAME
        and trigger.workspace_type == "Local"
        and trigger.state_label == "Local Git"
    ):
        raise AssertionError(
            "Step 4 failed: the header workspace switcher trigger showed the local "
            "workspace as `Local Git` after refresh even though no manual recovery "
            "gesture was performed.\n"
            f"Observed trigger label: {trigger.semantic_label!r}",
        )
    if selected_row is not None and selected_row.display_name == LOCAL_DISPLAY_NAME and (
        selected_row.state_label == "Local Git" or "Local Git" in selected_row.visible_text
    ):
        raise AssertionError(
            "Step 4 failed: Workspace switcher showed the local workspace as the "
            "selected active `Local Git` row after refresh without a manual "
            "re-authentication gesture.\n"
            f"Observed selected row: {json.dumps(_row_payload(selected_row), indent=2)}\n"
            f"Observed local row: {json.dumps(_row_payload(local_row), indent=2)}",
        )


def _decode_workspace_state(storage_snapshot: dict[str, str | None]) -> dict[str, object]:
    prefixed_value = storage_snapshot.get("flutter.trackstate.workspaceProfiles.state")
    raw_value = prefixed_value or storage_snapshot.get("trackstate.workspaceProfiles.state")
    if raw_value is None:
        return {}
    decoded: object = json.loads(raw_value)
    if isinstance(decoded, str):
        decoded = json.loads(decoded)
    return decoded if isinstance(decoded, dict) else {}


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


def _write_failure_outputs(result: dict[str, object]) -> None:
    error = str(result.get("error", "AssertionError: TS-913 failed"))
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
        "",
        "h4. What was automated",
        "* Opened the deployed TrackState app in Chromium with the hosted workspace active and a saved local workspace preloaded in browser state.",
        "* Established the ticket precondition by preloading the saved local workspace in the persisted {{Local Unavailable}} state and verifying the unavailable row was visible before the refresh.",
        "* Restored the same local repository on disk outside the app and refreshed the browser tab without any manual workspace interaction.",
        f"* Waited {STARTUP_RETRY_WAIT_SECONDS} seconds after the refresh so startup revalidation had time to finish before asserting.",
        "* Opened *Workspace switcher* and inspected the visible local workspace status label the same way a user would.",
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
    ]
    if result.get("precondition_failure"):
        lines.extend(
            [
                "",
                "h4. Precondition failure",
                f"* {result['precondition_failure']}",
            ],
        )
    lines.extend(
        [
            "",
            "h4. Step results",
            *_step_lines(result, jira=True),
        ],
    )
    if result.get("final_restore_message"):
        lines.extend(
            [
                "",
                "h4. Visible restore message",
                str(result["final_restore_message"]),
            ],
        )
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
        "- Opened the deployed TrackState app in Chromium with the hosted workspace active and a saved local workspace preloaded in browser state.",
        "- Established the ticket precondition by preloading the saved local workspace in the persisted `Local Unavailable` state and verifying the unavailable row was visible before the refresh.",
        "- Restored the same local repository on disk outside the app and refreshed the browser tab without any manual workspace interaction.",
        f"- Waited {STARTUP_RETRY_WAIT_SECONDS} seconds after the refresh so startup revalidation had time to finish before asserting.",
        "- Opened **Workspace switcher** and inspected the visible local workspace status label the same way a user would.",
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
    ]
    if result.get("precondition_failure"):
        lines.extend(
            [
                "",
                "## Precondition failure",
                f"- {result['precondition_failure']}",
            ],
        )
    lines.extend(
        [
            "",
            "## Step results",
            *_step_lines(result, jira=False),
            "",
            "## How to run",
            "```bash",
            RUN_COMMAND,
            "```",
        ],
    )
    if result.get("final_restore_message"):
        lines.extend(
            [
                "",
                "## Visible restore message",
                f"`{result['final_restore_message']}`",
            ],
        )
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
        "- Added TS-913 live startup coverage for the Local Unavailable state machine guard.",
        f"- Test case: **{TICKET_KEY} - {TEST_CASE_TITLE}**",
        f"- Result: **{status}**",
        f"- Command: `{RUN_COMMAND}`",
        (
            f"- Environment: `{result['app_url']}` on Chromium/Playwright "
            f"({result['os']}) against `{result['repository']}` @ "
            f"`{result['repository_ref']}`."
        ),
        (
            "- Outcome: after the local folder was restored and the app was refreshed, the saved local workspace still showed `Local Unavailable` until manual recovery."
            if passed
            else f"- Outcome: {_failed_step_summary(result)}"
        ),
    ]
    if result.get("screenshot"):
        lines.append(f"- Screenshot: `{result['screenshot']}`")
    return "\n".join(lines) + "\n"


def _bug_description(result: dict[str, object]) -> str:
    lines = [
        f"# {TICKET_KEY} - Local Unavailable state does not persist across refresh without manual action",
        "",
    ]
    if result.get("precondition_failure"):
        lines.extend(
            [
                "## Precondition setup",
                f"- {result['precondition_failure']}",
                "",
            ],
        )
    lines.extend(
        [
            "## Exact steps to reproduce",
            *_bug_step_lines(result),
            "",
            "## Exact error message or assertion failure",
            "```text",
            str(result.get("traceback", result.get("error", ""))),
            "```",
            "",
            "## Actual vs Expected",
            f"- **Expected:** {EXPECTED_RESULT}",
            (
                "- **Actual:** After the local folder was restored on disk and the app was "
                "refreshed without any manual recovery gesture, the local workspace no "
                "longer remained in `Local Unavailable`."
            ),
            (
                f"- **Observed final trigger:** `{_safe_dict_get(result.get('final_trigger_observation'), 'semantic_label')}`"
            ),
            (
                f"- **Observed final local row:** `{json.dumps(result.get('final_local_row'), ensure_ascii=True)}`"
            ),
            (
                f"- **Observed final selected row:** `{json.dumps(result.get('final_selected_row'), ensure_ascii=True)}`"
            ),
            (
                f"- **Observed persisted workspace state after refresh:** `{json.dumps(result.get('post_refresh_persisted_workspace_state'), ensure_ascii=True)}`"
            ),
            "",
            "## Environment details",
            f"- **URL:** {result.get('app_url')}",
            f"- **Repository:** {result.get('repository')} @ {result.get('repository_ref')}",
            f"- **Browser:** {result.get('browser')}",
            f"- **OS:** {result.get('os')}",
            f"- **Viewport:** {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
            f"- **Run command:** {RUN_COMMAND}",
            f"- **Startup wait after refresh:** {STARTUP_RETRY_WAIT_SECONDS} seconds",
            f"- **Local workspace path:** `{LOCAL_TARGET}`",
            "",
            "## Screenshots or logs",
            f"- **Screenshot:** {result.get('screenshot', '<no screenshot recorded>')}",
        ],
    )
    if result.get("final_restore_message"):
        lines.append(f"- **Visible restore message:** `{result['final_restore_message']}`")
    lines.extend(
        [
            "- **Console events:**",
            "```json",
            json.dumps(result.get("console_events", []), indent=2),
            "```",
            "- **Page errors:**",
            "```json",
            json.dumps(result.get("page_errors", []), indent=2),
            "```",
        ],
    )
    return "\n".join(lines) + "\n"


def _bug_step_lines(result: dict[str, object]) -> list[str]:
    recorded_steps = {
        int(step["step"]): step
        for step in result.get("steps", [])
        if isinstance(step, dict) and isinstance(step.get("step"), int)
    }
    lines: list[str] = []
    for index, action in enumerate(REQUEST_STEPS, start=1):
        record = recorded_steps.get(index)
        if record is None:
            lines.append(f"{index}. {action} — not reached.")
            continue
        marker = "✅" if record.get("status") == "passed" else "❌"
        lines.append(f"{index}. {action} — {marker} {record.get('observed')}")
    return lines


def _failed_step_summary(result: dict[str, object]) -> str:
    if result.get("precondition_failure"):
        return str(result["precondition_failure"])
    for step in result.get("steps", []):
        if isinstance(step, dict) and step.get("status") == "failed":
            return (
                f"Step {step.get('step')} failed while attempting to "
                f"{step.get('action')} Observed: {step.get('observed')}"
            )
    return str(result.get("error", "The Local Unavailable guard scenario failed."))


def _human_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    prefix = "*" if jira else "-"
    checks = result.get("human_verification", [])
    if not isinstance(checks, list) or not checks:
        return [f"{prefix} No additional human-style observations were recorded."]
    return [
        f"{prefix} {check['check']} Observed: {check['observed']}"
        for check in checks
        if isinstance(check, dict)
    ]


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    steps = result.get("steps", [])
    if not isinstance(steps, list):
        return []
    prefix = "*" if jira else "-"
    lines: list[str] = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        icon = "✅" if step.get("status") == "passed" else "❌"
        lines.append(
            f"{prefix} {icon} Step {step.get('step')}: {step.get('action')} "
            f"Observed: {step.get('observed')}"
        )
    return lines


def _artifact_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    prefix = "*" if jira else "-"
    lines: list[str] = []
    if result.get("screenshot"):
        lines.extend(
            [
                "",
                "h4. Screenshot" if jira else "## Screenshot",
                str(result["screenshot"]),
            ],
        )
    for key, heading in (
        ("initial_trigger_samples", "Initial trigger samples"),
        ("final_trigger_samples", "Final trigger samples"),
    ):
        if result.get(key):
            lines.extend(
                [
                    "",
                    f"h4. {heading}" if jira else f"## {heading}",
                    "{code}" if jira else "```json",
                    json.dumps(result[key], indent=2),
                    "{code}" if jira else "```",
                ],
            )
    if result.get("console_events"):
        lines.append(
            f"{prefix} Console events captured: `{len(result['console_events'])}`",
        )
    return lines


def _trigger_payload(trigger: WorkspaceSwitcherTriggerObservation) -> dict[str, object]:
    return {
        "semantic_label": trigger.semantic_label,
        "visible_text": trigger.visible_text,
        "raw_text_lines": list(trigger.raw_text_lines),
        "display_name": trigger.display_name,
        "workspace_type": trigger.workspace_type,
        "state_label": trigger.state_label,
        "icon_count": trigger.icon_count,
        "top_button_labels": list(trigger.top_button_labels),
    }


def _switcher_payload(switcher: WorkspaceSwitcherObservation) -> dict[str, object]:
    return {
        "body_text": switcher.body_text,
        "switcher_text": switcher.switcher_text,
        "row_count": switcher.row_count,
        "rows": [_row_payload(row) for row in switcher.rows],
    }


def _row_payload(
    row: WorkspaceSwitcherRowObservation | None,
) -> dict[str, object] | None:
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


def _safe_dict_get(value: object, key: str) -> str:
    if isinstance(value, dict):
        raw = value.get(key)
        return "<missing>" if raw is None else str(raw)
    return "<missing>"


if __name__ == "__main__":
    main()
