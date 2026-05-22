from __future__ import annotations

import json
import platform
import re
import shutil
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
from testing.core.utils.polling import poll_until  # noqa: E402
from testing.tests.support.live_tracker_app_factory import create_live_tracker_app  # noqa: E402
from testing.tests.support.stored_workspace_profiles_runtime import (  # noqa: E402
    StoredWorkspaceProfilesRuntime,
)

TICKET_KEY = "TS-921"
TEST_CASE_TITLE = (
    "Manual re-authentication with non-workspace directory keeps Local Unavailable state"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-921/test_ts_921.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
DEFAULT_BRANCH = "main"
LOCAL_TARGET = "/tmp/trackstate-ts921-workspace"
LOCAL_DISPLAY_NAME = "Restorable local workspace"
HOSTED_DISPLAY_NAME = "Hosted setup workspace"
WRONG_DIRECTORY_NAME = "ts921-wrong-directory"
LINKED_BUGS = ["TS-915"]
SHELL_NAVIGATION_LABELS = ("Dashboard", "Board", "JQL Search", "Hierarchy", "Settings")
MANUAL_REAUTH_CALLBACK_WAIT_SECONDS = 15
FAILURE_SETTLE_WAIT_SECONDS = 15
REWORK_SUMMARY = (
    "Added TS-921 live wrong-directory retry coverage and updated the shared "
    "workspace-switcher trigger helper to support real HTML buttons rendered by the "
    "deployed web app."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts921_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts921_failure.png"

REQUEST_STEPS = [
    "Open the Workspace switcher from the application header.",
    "Click the 'Re-authenticate' or 'Retry' button for the unavailable workspace.",
    (
        "In the browser directory picker, select a folder that is valid at the OS level "
        "but does not contain the specific repository expected for this workspace."
    ),
    "Grant permissions in the browser prompt.",
]
EXPECTED_RESULT = (
    "The application displays an error message indicating that the directory does not "
    "match the workspace configuration. The workspace status remains 'Local Unavailable' "
    "and is not restored to 'Local Git'."
)


class Ts921WrongDirectoryRuntime(StoredWorkspaceProfilesRuntime):
    def __init__(
        self,
        *,
        repository: str,
        token: str,
        workspace_state: dict[str, object],
        workspace_token_profile_ids: tuple[str, ...] = (),
    ) -> None:
        super().__init__(
            repository=repository,
            token=token,
            workspace_state=workspace_state,
            workspace_token_profile_ids=workspace_token_profile_ids,
        )
        self.console_events: list[dict[str, str]] = []
        self.page_errors: list[str] = []

    def __enter__(self):
        session = super().__enter__()
        if self._context is None or self._page is None:
            raise RuntimeError("TS-921 expected a browser context and page.")
        self._context.add_init_script(script=_manual_reauth_probe_script())
        self._context.add_init_script(script=_wrong_directory_picker_script())
        self._page.on("console", self._record_console_event)
        self._page.on("pageerror", self._record_page_error)
        return session

    def _record_console_event(self, message) -> None:
        self.console_events.append(
            {
                "level": str(message.type),
                "text": str(message.text),
            },
        )

    def _record_page_error(self, error: object) -> None:
        self.page_errors.append(str(error))


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)
    _cleanup_local_workspace()

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-921 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
        )

    workspace_state = _workspace_state(service.repository)
    hosted_workspace_id = f"hosted:{service.repository.lower()}@{DEFAULT_BRANCH}"
    local_workspace_id = f"local:{LOCAL_TARGET}@{DEFAULT_BRANCH}"
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
        "wrong_directory_name": WRONG_DIRECTORY_NAME,
        "preloaded_workspace_state": workspace_state,
        "steps": [],
        "human_verification": [],
    }

    runtime_context = Ts921WrongDirectoryRuntime(
        repository=config.repository,
        token=token,
        workspace_state=workspace_state,
        workspace_token_profile_ids=(hosted_workspace_id,),
    )
    page: LiveWorkspaceSwitcherPage | None = None

    try:
        with create_live_tracker_app(
            config,
            runtime_factory=lambda: runtime_context,
        ) as tracker_page:
            page = LiveWorkspaceSwitcherPage(tracker_page)
            try:
                runtime_observation = tracker_page.open()
                page.set_viewport(**DESKTOP_VIEWPORT)
                result["runtime_state"] = runtime_observation.kind
                result["runtime_body_text"] = runtime_observation.body_text
                shell_observation = tracker_page.observe_interactive_shell(
                    SHELL_NAVIGATION_LABELS,
                )
                result["shell_observation_before"] = shell_observation
                if runtime_observation.kind != "ready" or not bool(
                    shell_observation.get("shell_ready"),
                ):
                    raise AssertionError(
                        "Precondition failed: the deployed app did not reach the "
                        "interactive shell before the TS-921 workspace retry scenario.\n"
                        f"Observed runtime state: {runtime_observation.kind}\n"
                        f"Observed shell state:\n{json.dumps(shell_observation, indent=2)}",
                    )
                try:
                    page.dismiss_connection_banner()
                except Exception:
                    pass

                trigger_before = page.observe_trigger(timeout_ms=30_000)
                result["trigger_before"] = _trigger_payload(trigger_before)
                _record_human_verification(
                    result,
                    check=(
                        "Viewed the header workspace switcher control in the live deployed shell "
                        "before opening the switcher."
                    ),
                    observed=(
                        f"trigger_label={trigger_before.semantic_label!r}; "
                        f"trigger_text={trigger_before.visible_text!r}"
                    ),
                )

                switcher_before = page.open_and_observe(timeout_ms=30_000)
                result["switcher_before"] = _switcher_payload(switcher_before)
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=REQUEST_STEPS[0],
                    observed=(
                        "Opened the Workspace switcher from the application header.\n"
                        f"switcher_text={switcher_before.switcher_text!r}"
                    ),
                )

                saved_rows_before: tuple[WorkspaceSwitcherSavedWorkspaceRowObservation, ...] = ()
                saved_row_error: str | None = None
                try:
                    saved_rows_before = page.observe_saved_workspace_rows(timeout_ms=20_000)
                    result["saved_rows_before"] = [
                        _saved_row_payload(row) for row in saved_rows_before
                    ]
                except AssertionError as error:
                    saved_row_error = str(error)
                    result["saved_rows_before_error"] = saved_row_error

                local_row_before = _find_named_local_row(switcher_before)
                saved_local_row_before = _find_named_saved_local_row(saved_rows_before)
                selected_row_before = _find_selected_row(switcher_before)
                result["local_row_before"] = (
                    _row_payload(local_row_before) if local_row_before is not None else None
                )
                result["saved_local_row_before"] = (
                    _saved_row_payload(saved_local_row_before)
                    if saved_local_row_before is not None
                    else None
                )
                result["selected_row_before"] = (
                    _row_payload(selected_row_before)
                    if selected_row_before is not None
                    else None
                )
                _record_human_verification(
                    result,
                    check=(
                        "Opened the workspace switcher and inspected the visible saved workspace "
                        "entries where the unavailable local workspace should appear."
                    ),
                    observed=(
                        f"rows={json.dumps([_row_payload(row) for row in switcher_before.rows], ensure_ascii=True)}; "
                        f"saved_rows={json.dumps(result.get('saved_rows_before', []), ensure_ascii=True)}"
                    ),
                )

                try:
                    _assert_unavailable_local_row_visible(
                        trigger=trigger_before,
                        switcher=switcher_before,
                        local_row=local_row_before,
                        saved_local_row=saved_local_row_before,
                        saved_row_error=saved_row_error,
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
                        observed=(
                            "Not reached because the unavailable local workspace row was not "
                            "visible in step 2."
                        ),
                    )
                    _record_step(
                        result,
                        step=4,
                        status="failed",
                        action=REQUEST_STEPS[3],
                        observed=(
                            "Not reached because the unavailable local workspace row was not "
                            "visible in step 2."
                        ),
                    )
                    raise

                action_label = _saved_workspace_action_label(saved_local_row_before)
                result["manual_retry_action_label"] = action_label
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=REQUEST_STEPS[1],
                    observed=(
                        "Located the unavailable local workspace row and the visible manual retry "
                        f"action {action_label!r}.\n"
                        f"saved_local_row={json.dumps(_saved_row_payload(saved_local_row_before), indent=2)}"
                    ),
                )

                result["manual_reauth_probe_before"] = _read_manual_reauth_probe(
                    tracker_page,
                )
                result["wrong_picker_before"] = _read_wrong_picker_state(tracker_page)
                page.click_saved_workspace_action_button(action_label, timeout_ms=10_000)
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action=REQUEST_STEPS[2],
                    observed=(
                        "Activated the unavailable-workspace retry action while the browser "
                        "directory picker override returned the wrong directory handle.\n"
                        f"wrong_picker_before={json.dumps(result['wrong_picker_before'], indent=2)}"
                    ),
                )

                callback_observed, callback_observation = poll_until(
                    probe=lambda: _observe_retry_callback(tracker_page),
                    is_satisfied=lambda observation: observation[
                        "directory_access_callback_observed"
                    ],
                    timeout_seconds=MANUAL_REAUTH_CALLBACK_WAIT_SECONDS,
                    interval_seconds=1,
                )
                result["callback_observation"] = callback_observation
                result["manual_reauth_probe_after_click"] = callback_observation["probe"]
                result["wrong_picker_after_click"] = callback_observation["wrong_picker"]
                if not callback_observed:
                    _record_step(
                        result,
                        step=4,
                        status="failed",
                        action=REQUEST_STEPS[3],
                        observed=(
                            "The manual retry action never triggered the browser directory "
                            "picker callback for the wrong-directory selection.\n"
                            f"callback_observation={json.dumps(callback_observation, indent=2)}"
                        ),
                    )
                    raise AssertionError(
                        "Step 4 failed: the unavailable-workspace retry action never triggered "
                        "the browser directory picker callback.\n"
                        f"Observed callback state:\n{json.dumps(callback_observation, indent=2)}"
                    )

                settled, settled_observation = poll_until(
                    probe=lambda: _observe_post_retry_state(
                        tracker_page=tracker_page,
                        page=page,
                        expected_local_workspace_id=local_workspace_id,
                    ),
                    is_satisfied=lambda observation: bool(
                        observation["user_visible_error"]
                        or observation["local_row"] is not None
                        or observation["selected_row"] is not None
                    ),
                    timeout_seconds=FAILURE_SETTLE_WAIT_SECONDS,
                    interval_seconds=1,
                )
                result["post_retry_observation"] = settled_observation
                result["console_events"] = list(runtime_context.console_events)
                result["page_errors"] = list(runtime_context.page_errors)
                result["persisted_workspace_state"] = settled_observation[
                    "persisted_workspace_state"
                ]
                _record_human_verification(
                    result,
                    check=(
                        "After selecting the wrong directory, looked for the visible failure "
                        "message and re-checked the workspace row state in the switcher."
                    ),
                    observed=(
                        f"user_visible_error={settled_observation['user_visible_error']!r}; "
                        f"trigger={json.dumps(settled_observation['trigger'], ensure_ascii=True)}; "
                        f"local_row={json.dumps(settled_observation['local_row'], ensure_ascii=True)}"
                    ),
                )

                try:
                    _assert_wrong_directory_rejected(
                        settled=settled,
                        observation=settled_observation,
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
                        "The wrong-directory retry produced a visible failure and the local "
                        "workspace remained unavailable instead of switching to Local Git.\n"
                        f"post_retry_observation={json.dumps(settled_observation, indent=2)}"
                    ),
                )
            except Exception as error:
                try:
                    page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                    result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                except Exception as screenshot_error:
                    result["screenshot_error"] = (
                        f"{type(screenshot_error).__name__}: {screenshot_error}"
                    )
                raise error

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


def _cleanup_local_workspace() -> None:
    shutil.rmtree(LOCAL_TARGET, ignore_errors=True)


def _manual_reauth_probe_script() -> str:
    return """
    (() => {
      const state = window.__ts921ManualReauthProbe = {
        showDirectoryPickerCalls: [],
        requestPermissionCalls: [],
        queryPermissionCalls: [],
        wrapErrors: [],
      };
      const serialize = (value) => {
        try {
          return JSON.parse(JSON.stringify(value));
        } catch (error) {
          state.wrapErrors.push(String(error));
          return String(value);
        }
      };
      const wrap = (target, key, bucket) => {
        if (!target || typeof target[key] !== 'function') {
          return;
        }
        const original = target[key];
        target[key] = async function(...args) {
          state[bucket].push({
            callNumber: state[bucket].length + 1,
            args: serialize(args),
          });
          return await original.apply(this, args);
        };
      };
      wrap(window, 'showDirectoryPicker', 'showDirectoryPickerCalls');
      const fileSystemHandleProto = window.FileSystemHandle && window.FileSystemHandle.prototype;
      wrap(fileSystemHandleProto, 'requestPermission', 'requestPermissionCalls');
      wrap(fileSystemHandleProto, 'queryPermission', 'queryPermissionCalls');
    })();
    """


def _wrong_directory_picker_script() -> str:
    return f"""
    (() => {{
      const state = window.__ts921WrongPickerState = {{
        calls: [],
        selectedDirectoryName: null,
      }};
      const normalizeArgs = (args) => {{
        try {{
          return JSON.parse(JSON.stringify(args));
        }} catch (_) {{
          return Array.from(args, (value) => String(value));
        }}
      }};
      const createWrongDirectory = async () => {{
        const root = await navigator.storage.getDirectory();
        const wrong = await root.getDirectoryHandle({json.dumps(WRONG_DIRECTORY_NAME)}, {{ create: true }});
        const readme = await wrong.getFileHandle('README.txt', {{ create: true }});
        const writable = await readme.createWritable();
        await writable.write('Wrong directory chosen for TS-921.\\n');
        await writable.close();
        state.selectedDirectoryName = wrong.name || null;
        return wrong;
      }};
      const originalShowDirectoryPicker = globalThis.showDirectoryPicker?.bind(globalThis);
      if (typeof originalShowDirectoryPicker === 'function') {{
        globalThis.showDirectoryPicker = async (...args) => {{
          state.calls.push({{
            callNumber: state.calls.length + 1,
            args: normalizeArgs(args),
          }});
          return await createWrongDirectory();
        }};
      }}
    }})();
    """


def _read_manual_reauth_probe(tracker_page: TrackStateTrackerPage) -> dict[str, object]:
    payload = tracker_page.session.evaluate(
        """
        () => {
          const probe = window.__ts921ManualReauthProbe || {};
          return {
            showDirectoryPickerCalls: Array.isArray(probe.showDirectoryPickerCalls)
              ? probe.showDirectoryPickerCalls
              : [],
            requestPermissionCalls: Array.isArray(probe.requestPermissionCalls)
              ? probe.requestPermissionCalls
              : [],
            queryPermissionCalls: Array.isArray(probe.queryPermissionCalls)
              ? probe.queryPermissionCalls
              : [],
            wrapErrors: Array.isArray(probe.wrapErrors) ? probe.wrapErrors : [],
          };
        }
        """,
    )
    if not isinstance(payload, dict):
        return {
            "showDirectoryPickerCalls": [],
            "requestPermissionCalls": [],
            "queryPermissionCalls": [],
            "wrapErrors": [],
        }
    return {
        "showDirectoryPickerCalls": list(payload.get("showDirectoryPickerCalls", [])),
        "requestPermissionCalls": list(payload.get("requestPermissionCalls", [])),
        "queryPermissionCalls": list(payload.get("queryPermissionCalls", [])),
        "wrapErrors": list(payload.get("wrapErrors", [])),
    }


def _read_wrong_picker_state(tracker_page: TrackStateTrackerPage) -> dict[str, object]:
    payload = tracker_page.session.evaluate(
        """
        () => {
          const state = window.__ts921WrongPickerState || {};
          return {
            calls: Array.isArray(state.calls) ? state.calls : [],
            selectedDirectoryName:
              typeof state.selectedDirectoryName === 'string'
                ? state.selectedDirectoryName
                : null,
          };
        }
        """,
    )
    if not isinstance(payload, dict):
        return {"calls": [], "selectedDirectoryName": None}
    return {
        "calls": list(payload.get("calls", [])),
        "selectedDirectoryName": payload.get("selectedDirectoryName"),
    }


def _observe_retry_callback(tracker_page: TrackStateTrackerPage) -> dict[str, object]:
    probe = _read_manual_reauth_probe(tracker_page)
    wrong_picker = _read_wrong_picker_state(tracker_page)
    return {
        "probe": probe,
        "wrong_picker": wrong_picker,
        "body_text": tracker_page.body_text(),
        "directory_access_callback_observed": bool(probe["showDirectoryPickerCalls"]),
    }


def _observe_post_retry_state(
    *,
    tracker_page: TrackStateTrackerPage,
    page: LiveWorkspaceSwitcherPage,
    expected_local_workspace_id: str,
) -> dict[str, object]:
    body_text = tracker_page.body_text()
    trigger = _safe_trigger_payload(page)
    persisted_workspace_state = _decode_workspace_state(
        tracker_page.snapshot_local_storage(
            [
                "trackstate.workspaceProfiles.state",
                "flutter.trackstate.workspaceProfiles.state",
            ],
        ),
    )
    switcher: WorkspaceSwitcherObservation | None = None
    try:
        page.open_switcher(timeout_ms=5_000)
        switcher = page.observe_open_switcher(timeout_ms=5_000)
    except Exception:
        switcher = None
    local_row = _find_named_local_row(switcher) if switcher is not None else None
    selected_row = _find_selected_row(switcher) if switcher is not None else None
    user_visible_error = _extract_user_visible_error(
        tracker_page=tracker_page,
        body_text=body_text,
    )
    return {
        "body_text": body_text,
        "trigger": trigger,
        "switcher": _switcher_payload(switcher) if switcher is not None else None,
        "local_row": _row_payload(local_row) if local_row is not None else None,
        "selected_row": _row_payload(selected_row) if selected_row is not None else None,
        "persisted_workspace_state": persisted_workspace_state,
        "user_visible_error": user_visible_error,
        "active_workspace_id": (
            persisted_workspace_state.get("activeWorkspaceId")
            if persisted_workspace_state is not None
            else None
        ),
        "active_workspace_is_local": (
            persisted_workspace_state is not None
            and persisted_workspace_state.get("activeWorkspaceId") == expected_local_workspace_id
        ),
    }


def _extract_user_visible_error(
    *,
    tracker_page: TrackStateTrackerPage,
    body_text: str,
) -> str | None:
    direct_match = re.search(
        rf"Could not open {re.escape(LOCAL_DISPLAY_NAME)}\.\s*[^\n]+",
        body_text,
    )
    if direct_match is not None:
        return direct_match.group(0).strip()
    try:
        observation = tracker_page.observe_workspace_restore_message(
            workspace_name=LOCAL_DISPLAY_NAME,
            timeout_ms=1_000,
        )
    except Exception:
        return None
    return observation.message_text.strip() or None


def _assert_unavailable_local_row_visible(
    *,
    trigger: WorkspaceSwitcherTriggerObservation,
    switcher: WorkspaceSwitcherObservation,
    local_row: WorkspaceSwitcherRowObservation | None,
    saved_local_row: WorkspaceSwitcherSavedWorkspaceRowObservation | None,
    saved_row_error: str | None,
) -> None:
    if saved_local_row is None and local_row is None:
        raise AssertionError(
            "Step 2 failed: the Workspace switcher did not expose the unavailable saved local "
            "workspace row needed for manual re-authentication.\n"
            f"Observed trigger label: {trigger.semantic_label!r}\n"
            f"Observed switcher text: {switcher.switcher_text!r}\n"
            f"Observed parsed rows: {json.dumps([_row_payload(row) for row in switcher.rows], indent=2)}\n"
            + (
                f"Saved row parsing error: {saved_row_error}"
                if saved_row_error
                else "Saved row parsing error: <none>"
            )
        )
    candidate_state = None
    if saved_local_row is not None:
        candidate_state = saved_local_row.state_label
    elif local_row is not None:
        candidate_state = local_row.state_label
    if candidate_state != "Unavailable" and not (
        local_row is not None and "Local Unavailable" in local_row.visible_text
    ):
        raise AssertionError(
            "Step 2 failed: the saved local workspace row was visible, but it did not render "
            "the expected unavailable state before retry.\n"
            f"Observed local row: {json.dumps(_row_payload(local_row), indent=2)}\n"
            f"Observed saved local row: {json.dumps(_saved_row_payload(saved_local_row), indent=2)}"
        )


def _assert_wrong_directory_rejected(
    *,
    settled: bool,
    observation: dict[str, object],
    expected_local_workspace_id: str,
) -> None:
    del settled
    user_visible_error = str(observation.get("user_visible_error") or "").strip()
    if not user_visible_error:
        raise AssertionError(
            "Step 4 failed: selecting the wrong directory did not leave any visible user-facing "
            "error or restore message explaining the rejection.\n"
            f"Observed post-retry state: {json.dumps(observation, indent=2)}"
        )
    if not re.search(r"(match|directory|repository|path|workspace)", user_visible_error, re.I):
        raise AssertionError(
            "Step 4 failed: the visible user-facing failure did not explain the directory / "
            "workspace mismatch clearly enough.\n"
            f"Observed message: {user_visible_error!r}\n"
            f"Observed post-retry state: {json.dumps(observation, indent=2)}"
        )
    local_row_payload = observation.get("local_row")
    if not isinstance(local_row_payload, dict):
        raise AssertionError(
            "Step 4 failed: the local workspace row was no longer visible after the wrong "
            "directory retry.\n"
            f"Observed post-retry state: {json.dumps(observation, indent=2)}"
        )
    local_state = str(local_row_payload.get("state_label") or "")
    local_visible_text = str(local_row_payload.get("visible_text") or "")
    if local_state == "Local Git" or "Local Git" in local_visible_text:
        raise AssertionError(
            "Step 4 failed: the wrong-directory retry incorrectly promoted the local "
            "workspace to `Local Git`.\n"
            f"Observed local row: {json.dumps(local_row_payload, indent=2)}"
        )
    trigger = observation.get("trigger")
    if isinstance(trigger, dict) and (
        trigger.get("display_name") == LOCAL_DISPLAY_NAME
        and trigger.get("state_label") == "Local Git"
    ):
        raise AssertionError(
            "Step 4 failed: the header workspace trigger switched to the local workspace as "
            "`Local Git` after the wrong-directory retry.\n"
            f"Observed trigger: {json.dumps(trigger, indent=2)}"
        )
    persisted_workspace_state = observation.get("persisted_workspace_state")
    if isinstance(persisted_workspace_state, dict) and (
        persisted_workspace_state.get("activeWorkspaceId") == expected_local_workspace_id
    ):
        raise AssertionError(
            "Step 4 failed: browser storage marked the wrong directory as the active restored "
            "local workspace.\n"
            f"Observed persisted state: {json.dumps(persisted_workspace_state, indent=2)}"
        )


def _find_named_local_row(
    switcher: WorkspaceSwitcherObservation | None,
) -> WorkspaceSwitcherRowObservation | None:
    if switcher is None:
        return None
    for row in switcher.rows:
        if row.target_type_label == "Local" and LOCAL_TARGET in row.detail_text:
            return row
    return None


def _find_named_saved_local_row(
    rows: tuple[WorkspaceSwitcherSavedWorkspaceRowObservation, ...],
) -> WorkspaceSwitcherSavedWorkspaceRowObservation | None:
    for row in rows:
        if row.target_type_label == "Local" and LOCAL_TARGET in row.detail_text:
            return row
    return None


def _find_selected_row(
    switcher: WorkspaceSwitcherObservation | None,
) -> WorkspaceSwitcherRowObservation | None:
    if switcher is None:
        return None
    return next((row for row in switcher.rows if row.selected), None)


def _saved_workspace_action_label(
    row: WorkspaceSwitcherSavedWorkspaceRowObservation | None,
) -> str:
    if row is None:
        raise AssertionError(
            "Step 2 failed: the unavailable local workspace row did not expose a saved "
            "workspace action control.",
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
            "Step 2 failed: the unavailable local workspace row did not expose any visible "
            "retry / re-authentication action.\n"
            f"Observed row: {json.dumps(_saved_row_payload(row), indent=2)}"
        )
    return action_label


def _trigger_payload(
    trigger: WorkspaceSwitcherTriggerObservation,
) -> dict[str, object]:
    return {
        "semantic_label": trigger.semantic_label,
        "visible_text": trigger.visible_text,
        "display_name": trigger.display_name,
        "workspace_type": trigger.workspace_type,
        "state_label": trigger.state_label,
        "top_button_labels": list(trigger.top_button_labels),
    }


def _safe_trigger_payload(
    page: LiveWorkspaceSwitcherPage,
) -> dict[str, object] | None:
    try:
        return _trigger_payload(page.observe_trigger(timeout_ms=3_000))
    except Exception:
        return None


def _switcher_payload(
    switcher: WorkspaceSwitcherObservation | None,
) -> dict[str, object] | None:
    if switcher is None:
        return None
    return {
        "body_text": switcher.body_text,
        "switcher_text": switcher.switcher_text,
        "row_count": switcher.row_count,
        "rows": [_row_payload(row) for row in switcher.rows],
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
        "bounds": {
            "left": row.left,
            "top": row.top,
            "width": row.width,
            "height": row.height,
        },
    }


def _decode_workspace_state(
    storage_snapshot: dict[str, str | None],
) -> dict[str, object] | None:
    for key in (
        "flutter.trackstate.workspaceProfiles.state",
        "trackstate.workspaceProfiles.state",
    ):
        raw_value = storage_snapshot.get(key)
        if raw_value is None:
            continue
        candidate = raw_value
        for _ in range(2):
            if not isinstance(candidate, str):
                break
            try:
                decoded = json.loads(candidate)
            except json.JSONDecodeError:
                break
            candidate = decoded
        if isinstance(candidate, dict):
            return candidate
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
    entries = result.setdefault("human_verification", [])
    if not isinstance(entries, list):
        raise TypeError("result['human_verification'] must be a list")
    entries.append({"check": check, "observed": observed})


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
    JIRA_COMMENT_PATH.write_text(_build_jira_comment(result, passed=True), encoding="utf-8")
    PR_BODY_PATH.write_text(_build_pr_body(result, passed=True), encoding="utf-8")
    RESPONSE_PATH.write_text(_build_response_summary(result, passed=True), encoding="utf-8")


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
    JIRA_COMMENT_PATH.write_text(_build_jira_comment(result, passed=False), encoding="utf-8")
    PR_BODY_PATH.write_text(_build_pr_body(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_build_response_summary(result, passed=False), encoding="utf-8")
    BUG_DESCRIPTION_PATH.write_text(_build_bug_description(result), encoding="utf-8")


def _build_jira_comment(result: dict[str, object], *, passed: bool) -> str:
    status_icon = "✅" if passed else "❌"
    status_word = "PASSED" if passed else "FAILED"
    lines = [
        f"h3. {status_icon} Automated test {status_word} — {TICKET_KEY}",
        "",
        f"*Test case*: {TEST_CASE_TITLE}",
        f"*Environment*: URL={result.get('app_url')} | Browser={result.get('browser')} | OS={result.get('os')}",
        f"*Viewport*: {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
        f"*Linked bugs considered*: {', '.join(LINKED_BUGS)}",
        "",
        "h4. What was automated",
        "* Preloaded a hosted workspace plus the saved local workspace targeted by the ticket.",
        "* Opened the deployed Workspace switcher and checked for the unavailable local row a user must retry.",
        (
            f"* When the row is available, the automation forces the browser directory picker to "
            f"return a different directory handle named {{{{code}}}}{WRONG_DIRECTORY_NAME}{{{{code}}}} "
            "and waits for the post-click async effects."
        ),
        "* Verifies the visible error/message plus final workspace state instead of trusting the callback alone.",
        "",
        "h4. Automation checks",
        *_step_lines(result, jira=True),
        "",
        "h4. Real user-style verification",
        *_human_lines(result, jira=True),
        "",
        "h4. Expected result",
        EXPECTED_RESULT,
        "",
        "h4. Actual result",
        (
            "The wrong-directory retry showed a visible rejection and the local workspace stayed unavailable."
            if passed
            else str(result.get("error", "The wrong-directory retry did not match the expected result."))
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
        "## What was automated",
        "- Preloaded the hosted/local workspace state needed for the manual re-authentication scenario.",
        "- Opened the live Workspace switcher and verified the unavailable local row through the visible UI.",
        (
            f"- When available, forced the browser picker callback to choose the wrong directory "
            f"`{WRONG_DIRECTORY_NAME}` and waited for the async post-click state."
        ),
        "- Verified the visible failure text and final workspace state from the user's perspective.",
        "",
        "## Automation checks",
        *_step_lines(result, jira=False),
        "",
        "## Real user-style verification",
        *_human_lines(result, jira=False),
        "",
        "## Expected result",
        EXPECTED_RESULT,
        "",
        "## Actual result",
        (
            "The wrong-directory retry showed a visible rejection and the local workspace stayed unavailable."
            if passed
            else str(result.get("error", "The wrong-directory retry did not match the expected result."))
        ),
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


def _build_response_summary(result: dict[str, object], *, passed: bool) -> str:
    if passed:
        return (
            f"{TICKET_KEY} passed.\n\n"
            f"{REWORK_SUMMARY}\n\n"
            "The wrong-directory retry stayed visible to the user as a failure and did not "
            "promote the workspace to Local Git.\n"
        )
    return (
        f"{TICKET_KEY} failed.\n\n"
        f"{REWORK_SUMMARY}\n\n"
        f"{result.get('error', 'The wrong-directory retry did not match the expected result.')}\n"
    )


def _build_bug_description(result: dict[str, object]) -> str:
    annotated_steps: list[str] = []
    steps = result.get("steps", [])
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
        icon = "✅" if str(matching.get("status")) == "passed" else "❌"
        annotated_steps.append(
            f"{index}. {icon} {action} Observed: {matching.get('observed', '')}"
        )

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
        str(result.get("error", "The wrong-directory retry did not match the expected result.")),
        "",
        "## Expected result",
        EXPECTED_RESULT,
        "",
        "## Environment details",
        f"- URL: {result.get('app_url')}",
        f"- Browser: {result.get('browser')}",
        f"- OS: {result.get('os')}",
        f"- Viewport: {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
        f"- Wrong directory handle returned by test: {WRONG_DIRECTORY_NAME}",
        f"- Run command: `{RUN_COMMAND}`",
        "",
        "## Observed state",
        f"- Trigger before action: `{json.dumps(result.get('trigger_before'), ensure_ascii=True)}`",
        f"- Switcher before action: `{json.dumps(result.get('switcher_before'), ensure_ascii=True)}`",
        f"- Saved local row before action: `{json.dumps(result.get('saved_local_row_before'), ensure_ascii=True)}`",
        f"- Callback observation: `{json.dumps(result.get('callback_observation'), ensure_ascii=True)}`",
        f"- Post-retry observation: `{json.dumps(result.get('post_retry_observation'), ensure_ascii=True)}`",
        f"- Console events: `{json.dumps(result.get('console_events'), ensure_ascii=True)}`",
        f"- Page errors: `{json.dumps(result.get('page_errors'), ensure_ascii=True)}`",
    ]
    if result.get("screenshot"):
        lines.extend(["", "## Screenshots or logs", f"- Screenshot: `{result['screenshot']}`"])
    return "\n".join(lines) + "\n"


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for step in result.get("steps", []):
        if not isinstance(step, dict):
            continue
        if jira:
            lines.append(
                f"# Step {step['step']} *{str(step['status']).upper()}*: {step['action']}\n"
                f"Observed: {{{{code}}}}{step['observed']}{{{{code}}}}",
            )
        else:
            lines.append(
                f"- Step {step['step']} **{step['status']}** — {step['action']}  \n"
                f"  Observed: `{step['observed']}`",
            )
    return lines


def _human_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for entry in result.get("human_verification", []):
        if not isinstance(entry, dict):
            continue
        if jira:
            lines.append(
                f"* {entry['check']} Observed: {{{{code}}}}{entry['observed']}{{{{code}}}}",
            )
        else:
            lines.append(f"- **{entry['check']}** Observed: `{entry['observed']}`")
    return lines


if __name__ == "__main__":
    main()
