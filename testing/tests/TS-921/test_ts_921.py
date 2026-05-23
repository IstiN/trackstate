from __future__ import annotations

import json
import platform
import re
import shutil
import sys
import time
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
INPUT_DIR = REPO_ROOT / "input" / TICKET_KEY
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-921/test_ts_921.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
DEFAULT_BRANCH = "main"
LOCAL_TARGET = "/tmp/trackstate-ts921-workspace"
LOCAL_DISPLAY_NAME = "Restorable local workspace"
HOSTED_DISPLAY_NAME = "Hosted setup workspace"
WRONG_DIRECTORY_NAME = "ts921-wrong-directory"
LINKED_BUGS = ["TS-976", "TS-974", "TS-960", "TS-947", "TS-942", "TS-915", "TS-914"]
SHELL_NAVIGATION_LABELS = ("Dashboard", "Board", "JQL Search", "Hierarchy", "Settings")
MANUAL_REAUTH_CALLBACK_WAIT_SECONDS = 15
FAILURE_SETTLE_WAIT_SECONDS = 15
REWORK_SUMMARY = (
    "Resolved the TS-921 rework conflict, kept the wrong-directory assertion "
    "mismatch-specific, treated startup-shell outages as setup failures instead "
    "of TS-921 bug outcomes, and kept review replies driven by live thread metadata."
)
WRONG_DIRECTORY_REJECTION_VARIANTS = (
    "selected directory does not match the saved workspace configuration",
    "selected directory does not match the workspace configuration",
    "selected directory does not contain the expected repository for this workspace",
    "selected directory does not contain the repository configured for this workspace",
    "directory does not match the saved workspace configuration",
    "directory does not match the workspace configuration",
    "directory does not contain the expected repository for this workspace",
    "directory does not contain the repository configured for this workspace",
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
REVIEW_REPLIES_PATH = OUTPUTS_DIR / "review_replies.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
DISCUSSIONS_RAW_PATH = INPUT_DIR / "pr_discussions_raw.json"
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
                try:
                    runtime_observation = tracker_page.open()
                except AssertionError as error:
                    _raise_startup_failure(
                        result=result,
                        tracker_page=tracker_page,
                        runtime_context=runtime_context,
                        reason=str(error),
                    )
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
                    _raise_startup_failure(
                        result=result,
                        tracker_page=tracker_page,
                        runtime_context=runtime_context,
                        reason=(
                            "The deployed app did not reach the interactive shell before the "
                            "TS-921 workspace retry scenario.\n"
                            f"Observed runtime state: {runtime_observation.kind}\n"
                            f"Observed shell state:\n{json.dumps(shell_observation, indent=2)}"
                        ),
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
                callback_observed, callback_observation = poll_until(
                    probe=lambda: _observe_retry_callback(tracker_page),
                    is_satisfied=lambda observation: observation[
                        "browser_access_callback_observed"
                    ],
                    timeout_seconds=MANUAL_REAUTH_CALLBACK_WAIT_SECONDS,
                    interval_seconds=1,
                )
                result["callback_observation"] = callback_observation
                result["manual_reauth_probe_after_click"] = callback_observation["probe"]
                result["wrong_picker_after_click"] = callback_observation["wrong_picker"]
                result["wrong_directory_selected"] = callback_observation[
                    "wrong_picker"
                ].get("selectedDirectoryName")
                if not callback_observed:
                    _record_step(
                        result,
                        step=3,
                        status="failed",
                        action=REQUEST_STEPS[2],
                        observed=(
                            "The unavailable-workspace retry action never opened the browser "
                            "directory picker / access flow for the wrong-directory selection.\n"
                            f"callback_observation={json.dumps(callback_observation, indent=2)}"
                        ),
                    )
                    _record_step(
                        result,
                        step=4,
                        status="failed",
                        action=REQUEST_STEPS[3],
                        observed=(
                            "Not reached because step 3 never opened the browser directory "
                            "picker / access flow."
                        ),
                    )
                    raise AssertionError(
                        "Step 3 failed: the unavailable-workspace retry action never opened "
                        "the browser directory picker / access flow.\n"
                        f"Observed callback state:\n{json.dumps(callback_observation, indent=2)}"
                    )
                if result["wrong_directory_selected"] is None:
                    selection_confirmed, callback_observation = poll_until(
                        probe=lambda: _observe_retry_callback(tracker_page),
                        is_satisfied=lambda observation: (
                            observation["wrong_picker"].get("selectedDirectoryName")
                            is not None
                        ),
                        timeout_seconds=MANUAL_REAUTH_CALLBACK_WAIT_SECONDS,
                        interval_seconds=1,
                    )
                    result["callback_observation"] = callback_observation
                    result["manual_reauth_probe_after_click"] = callback_observation[
                        "probe"
                    ]
                    result["wrong_picker_after_click"] = callback_observation[
                        "wrong_picker"
                    ]
                    result["wrong_directory_selected"] = callback_observation[
                        "wrong_picker"
                    ].get("selectedDirectoryName")
                    if not selection_confirmed:
                        _record_step(
                            result,
                            step=3,
                            status="failed",
                            action=REQUEST_STEPS[2],
                            observed=(
                                "The unavailable-workspace retry action opened the browser "
                                "directory picker / access flow, but the follow-up poll never "
                                "confirmed that the wrong directory handle was selected.\n"
                                f"callback_observation={json.dumps(callback_observation, indent=2)}"
                            ),
                        )
                        _record_step(
                            result,
                            step=4,
                            status="failed",
                            action=REQUEST_STEPS[3],
                            observed=(
                                "Not reached because step 3 never confirmed the wrong directory "
                                "selection."
                            ),
                        )
                        raise AssertionError(
                            "Step 3 failed: the follow-up poll never confirmed "
                            "`wrong_picker.selectedDirectoryName` for the wrong-directory "
                            "selection.\n"
                            f"Observed callback state:\n{json.dumps(callback_observation, indent=2)}"
                        )
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action=REQUEST_STEPS[2],
                    observed=(
                        "The unavailable-workspace retry action opened the overridden browser "
                        "directory picker flow and selected the wrong directory handle.\n"
                        f"selected_directory={result['wrong_directory_selected']!r}\n"
                        f"callback_observation={json.dumps(callback_observation, indent=2)}"
                    ),
                )

                post_retry_started_at = time.monotonic()
                settled, settled_observation = poll_until(
probe=lambda: _observe_post_retry_state(
    tracker_page=tracker_page,
    page=page,
    expected_local_workspace_id=local_workspace_id,
    post_retry_started_at=post_retry_started_at,
),
is_satisfied=lambda observation: bool(
    observation.get("user_visible_error")
)
or bool(observation.get("active_workspace_is_local"))
or _local_row_promoted_to_local_git(
    observation.get("local_row"),
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
        "directory_access_callback_observed": bool(
            probe["showDirectoryPickerCalls"] or wrong_picker["calls"]
        ),
        "browser_access_callback_observed": bool(
            probe["showDirectoryPickerCalls"]
            or probe["requestPermissionCalls"]
            or wrong_picker["calls"]
            or wrong_picker.get("selectedDirectoryName")
        ),
    }


def _observe_post_retry_state(
    *,
    tracker_page: TrackStateTrackerPage,
    page: LiveWorkspaceSwitcherPage,
    expected_local_workspace_id: str,
    post_retry_started_at: float,
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
        "elapsed_seconds": round(time.monotonic() - post_retry_started_at, 3),
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
    if not settled:
        local_row_payload = observation.get("local_row")
        local_state = (
            str(local_row_payload.get("state_label") or "")
            if isinstance(local_row_payload, dict)
            else ""
        )
        local_visible_text = (
            str(local_row_payload.get("visible_text") or "")
            if isinstance(local_row_payload, dict)
            else ""
        )
        active_workspace_is_local = bool(observation.get("active_workspace_is_local"))
        if (
            isinstance(local_row_payload, dict)
            and not active_workspace_is_local
            and local_state != "Local Git"
            and "Local Git" not in local_visible_text
        ):
            raise AssertionError(
                "Step 4 failed: after selecting the wrong directory, the workspace stayed "
                "`Local Unavailable` and the hosted workspace remained active, but no "
                "visible directory/workspace mismatch error appeared within the allowed "
                "async wait window.\n"
                f"Observed post-retry state: {json.dumps(observation, indent=2)}"
            )
        raise AssertionError(
            "Step 4 failed: the wrong-directory retry never surfaced the expected "
            "mismatch rejection within the allowed async wait window.\n"
            f"Observed post-retry state: {json.dumps(observation, indent=2)}"
        )
    user_visible_error = str(observation.get("user_visible_error") or "").strip()
    body_text = str(observation.get("body_text") or "")
    if "Unsupported operation: Process.run" in user_visible_error or (
        "Unsupported operation: Process.run" in body_text
    ):
        raise AssertionError(
            "Step 4 failed: after selecting the wrong directory, the app showed "
            "`Unsupported operation: Process.run` instead of a directory/workspace "
            "mismatch error.\n"
            f"Observed message: {user_visible_error!r}\n"
            f"Observed post-retry state: {json.dumps(observation, indent=2)}"
        )
    if not user_visible_error:
        raise AssertionError(
            "Step 4 failed: selecting the wrong directory did not leave any visible user-facing "
            "error or restore message explaining the rejection.\n"
            f"Observed post-retry state: {json.dumps(observation, indent=2)}"
        )
    if not _is_expected_wrong_directory_rejection(user_visible_error):
        raise AssertionError(
            "Step 4 failed: the visible user-facing failure did not use an explicit "
            "wrong-directory / workspace-mismatch message.\n"
            f"Observed message: {user_visible_error!r}\n"
            f"Accepted mismatch variants: {json.dumps(list(WRONG_DIRECTORY_REJECTION_VARIANTS), indent=2)}\n"
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


def _is_expected_wrong_directory_rejection(message: str) -> bool:
    normalized = " ".join(message.split()).strip().lower()
    if not normalized:
        return False
    expected_prefix = f"could not open {LOCAL_DISPLAY_NAME.lower()}."
    if not normalized.startswith(expected_prefix):
        return False
    return any(
        variant in normalized for variant in WRONG_DIRECTORY_REJECTION_VARIANTS
    )


def _local_row_promoted_to_local_git(local_row_payload: object) -> bool:
    if not isinstance(local_row_payload, dict):
        return False
    local_state = str(local_row_payload.get("state_label") or "")
    local_visible_text = str(local_row_payload.get("visible_text") or "")
    return local_state == "Local Git" or "Local Git" in local_visible_text


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


def _observe_startup_surface(tracker_page: TrackStateTrackerPage) -> dict[str, object]:
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
                element.getAttribute?.('aria-label')
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
    runtime_context: Ts921WrongDirectoryRuntime,
    reason: str,
) -> None:
    startup_observation = _observe_startup_surface(tracker_page)
    result["runtime_state"] = "startup-failed"
    result["startup_observation"] = startup_observation
    result["runtime_body_text"] = startup_observation["body_text"]
    result["console_events"] = list(runtime_context.console_events)
    result["page_errors"] = list(runtime_context.page_errors)
    observed = (
        "The deployed app never exposed the interactive shell or workspace switcher needed "
        "to reach the TS-921 manual re-authentication flow.\n"
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
    for step_number in (2, 3, 4):
        _record_step(
            result,
            step=step_number,
            status="failed",
            action=REQUEST_STEPS[step_number - 1],
            observed=(
                "Not reached because the deployed app never showed the application header "
                "and Workspace switcher. The visible page remained on the startup `Sync issue` "
                "surface instead."
            ),
        )
    _record_human_verification(
        result,
        check=(
            "Loaded the deployed app at the required desktop viewport and waited for the "
            "workspace switcher entry point to appear."
        ),
        observed=(
            f"title={startup_observation['title']!r}; "
            f"url={startup_observation['location_href']!r}; "
            f"visible_buttons={json.dumps(startup_observation['button_labels'], ensure_ascii=True)}; "
            f"body_text={startup_observation['body_text']!r}"
        ),
    )
    _record_human_verification(
        result,
        check=(
            "Viewed the live page like a user after load to confirm what was actually rendered "
            "on screen."
        ),
        observed=(
            "The page showed only a top-left `Sync issue` control on an otherwise blank screen, "
            "with no dashboard, no navigation, and no workspace switcher trigger."
        ),
    )
    raise AssertionError(
        "Step 1 failed: the deployed app did not render the interactive shell, so "
        "TS-921 could not reach the Workspace switcher required by the ticket steps.\n"
        f"Observed startup surface:\n{json.dumps(startup_observation, indent=2)}\n"
        f"Console events:\n{json.dumps(result['console_events'], indent=2)}\n"
        f"Page errors:\n{json.dumps(result['page_errors'], indent=2)}",
    )


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
    REVIEW_REPLIES_PATH.write_text(
        _build_review_replies(result, passed=True),
        encoding="utf-8",
    )


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
    REVIEW_REPLIES_PATH.write_text(
        _build_review_replies(result, passed=False),
        encoding="utf-8",
    )
    if _is_startup_precondition_failure(result):
        BUG_DESCRIPTION_PATH.unlink(missing_ok=True)
    else:
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
        "* Verifies the visible mismatch rejection plus final workspace state instead of trusting the callback alone.",
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
        _actual_result_summary(result, passed=passed),
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
        f"## {TICKET_KEY} passed" if passed else f"## {TICKET_KEY} failed",
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
        "- Verified the visible mismatch rejection and final workspace state from the user's perspective.",
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
        _actual_result_summary(result, passed=passed),
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
    status = "passed" if passed else "failed"
    lines = [f"# {TICKET_KEY} {status}", ""]
    if not passed:
        failure_note = (
            "Re-run hit a setup/precondition failure before the TS-921 workspace-switcher "
            "steps could execute."
            if _is_startup_precondition_failure(result)
            else f"Re-run failed: {_failed_step_summary(result)}"
        )
        lines.extend(
            [
                "## Issues/Notes",
                f"- {failure_note}",
                "",
            ],
        )
    lines.extend(
        [
            "## Approach",
            f"- {REWORK_SUMMARY}",
            (
                "- Re-ran the live deployed workspace re-authentication flow and captured the "
                "current user-visible outcome after the wrong-directory selection."
            ),
            "",
            "## Files Modified",
            "- `testing/tests/TS-921/test_ts_921.py`",
            "",
            "## Test Coverage",
            f"- Test case: `{TICKET_KEY} - {TEST_CASE_TITLE}`",
            f"- Result: `{status}`",
            f"- Command: `{RUN_COMMAND}`",
            (
                f"- Environment: `{result.get('app_url')}` on Chromium/Playwright "
                f"({result.get('os')}) against `{result.get('repository')}` @ "
                f"`{result.get('repository_ref')}`."
            ),
            f"- Step results: {', '.join(_step_status_summary(result))}",
        ],
    )
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


def _build_review_replies(result: dict[str, object], *, passed: bool) -> str:
    replies = [
        {
            "inReplyToId": thread["rootCommentId"],
            "threadId": thread["threadId"],
            "reply": _review_reply_text(result, passed=passed),
        }
        for thread in _discussion_threads()
    ]
    return (
        json.dumps(
            {"replies": replies},
            indent=2,
        )
        + "\n"
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
        "h4. Environment",
        f"* URL: {result.get('app_url')}",
        f"* Browser: {result.get('browser')}",
        f"* OS: {result.get('os')}",
        f"* Repository: {result.get('repository')} @ {result.get('repository_ref')}",
        f"* Viewport: {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
        f"* Wrong directory handle returned by test: {WRONG_DIRECTORY_NAME}",
        "",
        "h4. Steps to Reproduce",
        *annotated_steps,
        "",
        "h4. Expected Result",
        EXPECTED_RESULT,
        "",
        "h4. Actual Result",
        str(result.get("error", "The wrong-directory retry did not match the expected result.")),
        "",
        "h4. Missing or Broken Production Capability",
        _missing_or_broken_capability(result),
        "",
        "h4. Logs / Error Output",
        "{code}",
        str(result.get("traceback", result.get("error", ""))),
        "{code}",
        "",
        "h4. Notes",
        f"* Run command: {RUN_COMMAND}",
        f"* Startup observation: {json.dumps(result.get('startup_observation'), ensure_ascii=True)}",
        f"* Trigger before action: {json.dumps(result.get('trigger_before'), ensure_ascii=True)}",
        f"* Switcher before action: {json.dumps(result.get('switcher_before'), ensure_ascii=True)}",
        f"* Saved local row before action: {json.dumps(result.get('saved_local_row_before'), ensure_ascii=True)}",
        f"* Callback observation: {json.dumps(result.get('callback_observation'), ensure_ascii=True)}",
        f"* Post-retry observation: {json.dumps(result.get('post_retry_observation'), ensure_ascii=True)}",
        f"* Console events: {json.dumps(result.get('console_events'), ensure_ascii=True)}",
        f"* Page errors: {json.dumps(result.get('page_errors'), ensure_ascii=True)}",
    ]
    if result.get("screenshot"):
        lines.append(f"* Screenshot: {result['screenshot']}")
    return "\n".join(lines) + "\n"


def _actual_result_summary(result: dict[str, object], *, passed: bool) -> str:
    if passed:
        return (
            "The wrong-directory retry showed a visible rejection and the local workspace "
            "stayed unavailable."
        )
    if _is_startup_precondition_failure(result):
        return (
            "The rerun failed before the ticket scenario started because the deployed app "
            "never rendered the interactive shell and Workspace switcher needed for the "
            "TS-921 precondition."
        )
    return str(
        result.get(
            "error",
            "The deployed app blocked the TS-921 scenario before the wrong-directory retry "
            "could run.",
        ),
    )


def _missing_or_broken_capability(result: dict[str, object]) -> str:
    error = str(result.get("error", ""))
    if "interactive shell" in error or "Workspace switcher required" in error:
        return (
            "The deployed web app never rendered the interactive shell or Workspace "
            "switcher needed to start manual re-authentication, so the TS-921 flow could "
            "not be reached."
        )
    if "never opened the browser directory picker / access flow" in error:
        return (
            "Clicking `Retry` on the unavailable local workspace did not open the browser "
            "directory picker / access flow, so the user could not continue manual "
            "re-authentication."
        )
    if "Unsupported operation: Process.run" in error:
        return (
            "After the user selected a wrong directory for manual re-authentication, the "
            "deployed web app surfaced `Unsupported operation: Process.run` instead of a "
            "clear directory/workspace mismatch message while keeping the workspace in "
            "`Local Unavailable`."
        )
    return (
        "The deployed web app did not produce the expected wrong-directory mismatch "
        "outcome required by TS-921."
    )


def _is_startup_precondition_failure(result: dict[str, object]) -> bool:
    return str(result.get("runtime_state", "")).strip() == "startup-failed"


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
        thread_id = thread.get("threadId") or thread.get("id")
        if root_comment_id is None or thread_id is None:
            continue
        normalized_threads.append(
            {
                "rootCommentId": root_comment_id,
                "threadId": thread_id,
                "body": thread.get("body"),
            },
        )
    return normalized_threads


def _review_reply_text(result: dict[str, object], *, passed: bool) -> str:
    rerun_summary = (
        "Re-ran the current TS-921 test and it passed (`1 passed, 0 failed`)."
        if passed
        else (
            "Re-ran the current TS-921 test and it still failed: "
            f"{_snippet(_current_failure_summary(result), limit=240)}"
        )
    )
    return (
        "Fixed: `review_replies.json` is now generated from the unresolved entries in "
        f"`{DISCUSSIONS_RAW_PATH.relative_to(REPO_ROOT)}` and the current rerun result, "
        "so it no longer hardcodes stale PR thread IDs or an outdated failure mode. "
        f"{rerun_summary}"
    )


def _failed_step_summary(result: dict[str, object]) -> str:
    failed_steps = [
        step
        for step in result.get("steps", [])
        if isinstance(step, dict) and step.get("status") == "failed"
    ]
    if not failed_steps:
        return str(result.get("error", "The test failed before step details were recorded."))
    first_failed_step = failed_steps[0]
    return (
        f"Step {first_failed_step.get('step')} failed. "
        f"{_snippet(str(first_failed_step.get('observed', '')), limit=500)}"
    )


def _current_failure_summary(result: dict[str, object]) -> str:
    error = str(result.get("error", "")).strip()
    if error:
        return error.splitlines()[0]
    return _failed_step_summary(result)


def _step_status_summary(result: dict[str, object]) -> list[str]:
    summaries: list[str] = []
    for step in result.get("steps", []):
        if not isinstance(step, dict):
            continue
        summaries.append(f"{step.get('step')}={step.get('status')}")
    return summaries or ["<no steps recorded>"]


def _snippet(text: str, *, limit: int) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3] + "..."


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
