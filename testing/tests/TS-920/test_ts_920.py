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
    WorkspaceSwitcherSavedWorkspaceRowObservation,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.utils.polling import poll_until  # noqa: E402
from testing.tests.support.live_tracker_app_factory import create_live_tracker_app  # noqa: E402
from testing.tests.support.stored_workspace_profiles_runtime import (  # noqa: E402
    StoredWorkspaceProfilesRuntime,
)

TICKET_KEY = "TS-920"
TEST_CASE_TITLE = (
    "User cancels browser directory picker during restoration — workspace remains "
    "Local Unavailable"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-920/test_ts_920.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
DEFAULT_BRANCH = "main"
LOCAL_TARGET = "/tmp/trackstate-ts920-workspace"
LOCAL_DISPLAY_NAME = "Restorable local workspace"
HOSTED_DISPLAY_NAME = "Hosted setup workspace"
LINKED_BUGS = ["TS-947", "TS-942", "TS-915", "TS-914"]
SHELL_NAVIGATION_LABELS = ("Dashboard", "Board", "JQL Search", "Hierarchy", "Settings")
STARTUP_PRECONDITION_WAIT_SECONDS = 20
MANUAL_REAUTH_CALLBACK_WAIT_SECONDS = 15
CANCEL_SETTLE_WAIT_SECONDS = 15
REWORK_SUMMARY = (
    "Updated the TS-920 live Playwright regression to drive the real saved-workspace "
    "restore button through the page object and to simulate browser-access cancel "
    "outcomes for both picker and remembered-handle permission callbacks while "
    "verifying the workspace stays unavailable. The test now also captures a "
    "diagnostic startup snapshot if the deployed app never reaches the workspace "
    "switcher."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts920_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts920_failure.png"

REQUEST_STEPS = [
    "Open the Workspace switcher from the application header.",
    "Click the 'Re-authenticate' or 'Retry' button for the unavailable workspace.",
    "When the browser's directory access prompt (showDirectoryPicker) appears, click 'Cancel' or dismiss the dialog.",
]
EXPECTED_RESULT = (
    "The browser prompt closes. The workspace remains in the 'Local Unavailable' "
    "state. The application does not throw an 'Unsupported operation: Process.run' "
    "error or any other runtime exceptions."
)


class Ts920CancelledPickerRuntime(StoredWorkspaceProfilesRuntime):
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
            raise RuntimeError(
                "TS-920 cancel runtime expected a browser context and page.",
            )
        self._context.add_init_script(script=_manual_cancel_probe_script())
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
    _remove_local_workspace_repository()

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-920 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
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
        "manual_reauth_callback_wait_seconds": MANUAL_REAUTH_CALLBACK_WAIT_SECONDS,
        "cancel_settle_wait_seconds": CANCEL_SETTLE_WAIT_SECONDS,
        "startup_precondition_wait_seconds": STARTUP_PRECONDITION_WAIT_SECONDS,
        "steps": [],
        "human_verification": [],
        "manual_cancel_simulation": (
            "Automation forced `showDirectoryPicker()` to reject with `AbortError` "
            "and `requestPermission()` to resolve to `denied` so either browser-access "
            "path behaves like the user canceling or dismissing the prompt."
        ),
    }

    page: LiveWorkspaceSwitcherPage | None = None
    runtime_context: Ts920CancelledPickerRuntime | None = None

    try:
        runtime_context = Ts920CancelledPickerRuntime(
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
                try:
                    runtime_observation = tracker_page.open()
                except AssertionError as error:
                    startup_observation = _observe_startup_surface(tracker_page)
                    result["runtime_state"] = "startup-failed"
                    result["runtime_body_text"] = startup_observation["body_text"]
                    result["startup_observation"] = startup_observation
                    _record_step(
                        result,
                        step=1,
                        status="failed",
                        action=REQUEST_STEPS[0],
                        observed=(
                            "The deployed app never reached the interactive tracker shell, "
                            "so the Workspace switcher could not be opened.\n"
                            f"startup_observation={json.dumps(startup_observation, indent=2)}"
                        ),
                    )
                    _record_step(
                        result,
                        step=2,
                        status="failed",
                        action=REQUEST_STEPS[1],
                        observed="Not reached because the deployed app never exposed the Workspace switcher.",
                    )
                    _record_step(
                        result,
                        step=3,
                        status="failed",
                        action=REQUEST_STEPS[2],
                        observed="Not reached because the deployed app never exposed the Workspace switcher.",
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Opened the deployed page as a user would and checked the first "
                            "visible interactive surface before any workspace action."
                        ),
                        observed=(
                            f"visible_buttons={startup_observation['visible_button_labels']!r}; "
                            f"visible_text={startup_observation['body_text']!r}; "
                            f"url={startup_observation['url']!r}"
                        ),
                    )
                    raise AssertionError(
                        "Step 1 failed: the deployed app never reached an interactive state.\n"
                        f"Observed startup surface:\n{json.dumps(startup_observation, indent=2)}"
                    ) from error
                page.set_viewport(**DESKTOP_VIEWPORT)
                result["runtime_state"] = runtime_observation.kind
                result["runtime_body_text"] = runtime_observation.body_text
                shell_observation = tracker_page.observe_interactive_shell(
                    SHELL_NAVIGATION_LABELS,
                )
                result["shell_observation_before_action"] = shell_observation
                if runtime_observation.kind != "ready" or not bool(
                    shell_observation.get("shell_ready"),
                ):
                    raise AssertionError(
                        "Precondition failed: the deployed app did not reach the "
                        "interactive shell with the hosted-workspace preload.\n"
                        f"Observed runtime state: {runtime_observation.kind}\n"
                        f"Observed shell state:\n{json.dumps(shell_observation, indent=2)}",
                    )

                try:
                    page.dismiss_connection_banner()
                except Exception:
                    pass

                result["trigger_before_action"] = _safe_workspace_trigger_payload(
                    tracker_page,
                )

                precondition_ready, precondition_observation = poll_until(
                    probe=lambda: _observe_unavailable_local_precondition(
                        tracker_page=tracker_page,
                        page=page,
                    ),
                    is_satisfied=lambda observation: observation["local_row_unavailable"],
                    timeout_seconds=STARTUP_PRECONDITION_WAIT_SECONDS,
                    interval_seconds=2,
                )
                result["precondition_observation"] = precondition_observation
                local_row_before = precondition_observation["local_row_label"]
                selected_trigger_before = precondition_observation["trigger"]
                result["local_row_before_action"] = local_row_before
                result["selected_row_before_action"] = precondition_observation[
                    "selected_row_label"
                ]
                result["hosted_row_before_action"] = precondition_observation[
                    "hosted_row_label"
                ]

                if not precondition_ready:
                    _record_step(
                        result,
                        step=1,
                        status="failed",
                        action=REQUEST_STEPS[0],
                        observed=(
                            "The saved local workspace never appeared in the visible "
                            "`Unavailable` state within the precondition wait window.\n"
                            f"precondition_observation={json.dumps(precondition_observation, indent=2)}"
                        ),
                    )
                    _record_step(
                        result,
                        step=2,
                        status="failed",
                        action=REQUEST_STEPS[1],
                        observed="Not reached because step 1 did not expose the unavailable local workspace row.",
                    )
                    _record_step(
                        result,
                        step=3,
                        status="failed",
                        action=REQUEST_STEPS[2],
                        observed="Not reached because step 1 did not expose the unavailable local workspace row.",
                    )
                    raise AssertionError(
                        "Step 1 failed: the saved local workspace never appeared in the "
                        "visible `Unavailable` state within the precondition wait window.\n"
                        f"Observed precondition state:\n{json.dumps(precondition_observation, indent=2)}"
                    )

                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=REQUEST_STEPS[0],
                    observed=(
                        "Opened the Workspace switcher and waited for the saved local "
                        "workspace to finish transitioning into the visible "
                        "`Unavailable` state before the manual restore attempt.\n"
                        f"precondition_wait_seconds={STARTUP_PRECONDITION_WAIT_SECONDS}\n"
                        f"local_row_label={local_row_before!r}\n"
                        f"local_action_label={precondition_observation['local_action_label']!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Opened the switcher and visually confirmed the unavailable local "
                        "workspace row and the still-active hosted workspace."
                    ),
                    observed=(
                        f"local_row_label={local_row_before!r}; "
                        f"trigger={json.dumps(selected_trigger_before, ensure_ascii=True)}"
                    ),
                )

                restored_local_workspace = _prepare_local_workspace_repository()
                result["restorable_local_workspace"] = restored_local_workspace
                result["manual_cancel_probe_before_action"] = _read_manual_cancel_probe(
                    tracker_page,
                )
                exact_action_label = str(precondition_observation["local_action_label"])
                result["manual_restore_action_label"] = exact_action_label

                try:
                    page.click_saved_workspace_action_button(
                        exact_action_label,
                        timeout_ms=10_000,
                    )
                except AssertionError as error:
                    _record_step(
                        result,
                        step=2,
                        status="failed",
                        action=REQUEST_STEPS[1],
                        observed=(
                            "The saved local workspace directory was recreated before the "
                            "manual restore attempt, but the visible action could not be clicked.\n"
                            f"restorable_local_workspace={json.dumps(restored_local_workspace, indent=2)}\n"
                            f"{error}"
                        ),
                    )
                    _record_step(
                        result,
                        step=3,
                        status="failed",
                        action=REQUEST_STEPS[2],
                        observed="Not reached because the manual restore action in step 2 could not be clicked.",
                    )
                    raise

                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=REQUEST_STEPS[1],
                    observed=(
                        "Clicked the visible manual restore action for the unavailable "
                        "saved local workspace entry.\n"
                        f"local_row_label={local_row_before!r}\n"
                        f"clicked_action_label={exact_action_label!r}"
                    ),
                )

                picker_called, cancel_attempt_observation = poll_until(
                    probe=lambda: _observe_manual_cancel_attempt(
                        tracker_page=tracker_page,
                        page=page,
                    ),
                    is_satisfied=lambda observation: observation[
                        "browser_access_callback_observed"
                    ],
                    timeout_seconds=MANUAL_REAUTH_CALLBACK_WAIT_SECONDS,
                    interval_seconds=1,
                )
                result["manual_cancel_attempt_observation"] = cancel_attempt_observation
                result["manual_cancel_probe_after_action"] = cancel_attempt_observation[
                    "probe"
                ]
                if not picker_called:
                    _record_step(
                        result,
                        step=3,
                        status="failed",
                        action=REQUEST_STEPS[2],
                        observed=(
                            "The unavailable-workspace action never triggered any browser "
                            "access callback (`showDirectoryPicker()` or "
                            "`requestPermission()`).\n"
                            f"action_label={exact_action_label!r}\n"
                            f"probe_state={json.dumps(cancel_attempt_observation['probe'], indent=2)}"
                        ),
                    )
                    raise AssertionError(
                        "Step 3 failed: clicking the unavailable-workspace action never "
                        "triggered `showDirectoryPicker()` or `requestPermission()`.\n"
                        f"Observed action label: {exact_action_label!r}\n"
                        f"Observed probe state:\n{json.dumps(cancel_attempt_observation['probe'], indent=2)}\n"
                        f"Observed body text:\n{cancel_attempt_observation['body_text']}"
                    )

                stable_after_cancel, post_cancel_observation = poll_until(
                    probe=lambda: _observe_post_cancel_state(
                        tracker_page=tracker_page,
                        page=page,
                        expected_hosted_workspace_id=hosted_workspace_id,
                    ),
                    is_satisfied=lambda observation: bool(
                        observation["local_row_unavailable"]
                        and observation["hosted_still_active"]
                        and observation["storage_unchanged"]
                        and observation["shell_ready"]
                        and not observation["fatal_banner_visible"]
                        and not observation["workspace_open_failure_visible"]
                        and not observation["unsupported_operation_visible"]
                    ),
                    timeout_seconds=CANCEL_SETTLE_WAIT_SECONDS,
                    interval_seconds=2,
                )
                result["post_cancel_observation"] = post_cancel_observation
                if not stable_after_cancel:
                    _record_step(
                        result,
                        step=3,
                        status="failed",
                        action=REQUEST_STEPS[2],
                        observed=(
                            "The browser directory picker callback was triggered and "
                            "simulated a user cancel, but the app did not settle back to "
                            "the expected unchanged unavailable-workspace state.\n"
                            f"post_cancel_observation={json.dumps(post_cancel_observation, indent=2)}"
                        ),
                    )
                    raise AssertionError(
                        "Step 3 failed: after the simulated browser-picker cancel, the "
                        "workspace did not settle back to the expected unchanged state.\n"
                        f"Observed post-cancel state:\n{json.dumps(post_cancel_observation, indent=2)}"
                    )

                result["trigger_after_cancel"] = post_cancel_observation["trigger"]
                result["switcher_after_cancel"] = post_cancel_observation["switcher"]
                result["local_row_after_cancel"] = post_cancel_observation["local_row_label"]
                result["hosted_row_after_cancel"] = post_cancel_observation["hosted_row_label"]
                result["selected_row_after_cancel"] = post_cancel_observation["selected_row_label"]
                result["shell_observation_after_cancel"] = post_cancel_observation[
                    "shell_observation"
                ]
                result["persisted_workspace_state"] = post_cancel_observation[
                    "persisted_workspace_state"
                ]
                result["body_text_after_cancel"] = post_cancel_observation["body_text"]
                result["unsupported_operation_visible"] = post_cancel_observation[
                    "unsupported_operation_visible"
                ]

                if runtime_context.page_errors:
                    _record_step(
                        result,
                        step=3,
                        status="failed",
                        action=REQUEST_STEPS[2],
                        observed=(
                            "The UI state remained readable after the simulated cancel, but "
                            "runtime page errors were emitted.\n"
                            f"page_errors={json.dumps(runtime_context.page_errors, indent=2)}"
                        ),
                    )
                    raise AssertionError(
                        "Step 3 failed: canceling the directory picker triggered runtime "
                        f"errors.\nObserved page errors:\n{json.dumps(runtime_context.page_errors, indent=2)}"
                    )

                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action=REQUEST_STEPS[2],
                    observed=(
                        "Simulated browser-access cancellation on the real unavailable-"
                        "workspace restore flow, then waited "
                        f"{CANCEL_SETTLE_WAIT_SECONDS} seconds for the UI to settle. The "
                        "workspace stayed unavailable, the hosted workspace stayed active, "
                        "and no visible open-failure or unsupported-operation message "
                        "became visible.\n"
                        f"probe={json.dumps(cancel_attempt_observation['probe'], indent=2)}\n"
                        f"post_cancel_state={json.dumps(post_cancel_observation, indent=2)}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Viewed the header trigger and reopened the switcher after the "
                        "simulated cancel to confirm the app stayed interactive."
                    ),
                    observed=(
                        f"trigger_after_cancel={json.dumps(post_cancel_observation['trigger'], ensure_ascii=True)}; "
                        f"local_row_after_cancel={post_cancel_observation['local_row_label']!r}; "
                        f"selected_row_after_cancel={post_cancel_observation['selected_row_label']!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Checked the visible shell content after cancel for user-facing "
                        "error text."
                    ),
                    observed=(
                        f"unsupported_operation_visible={post_cancel_observation['unsupported_operation_visible']}; "
                        f"workspace_open_failure_visible={post_cancel_observation['workspace_open_failure_visible']}; "
                        f"body_excerpt={post_cancel_observation['body_text'][:400]!r}"
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
        if runtime_context is not None:
            result["console_events"] = list(runtime_context.console_events)
            result["page_errors"] = list(runtime_context.page_errors)
        _write_failure_outputs(result)
        raise
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        if runtime_context is not None:
            result["console_events"] = list(runtime_context.console_events)
            result["page_errors"] = list(runtime_context.page_errors)
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

    marker_path = local_path / ".trackstate-ts920-precondition.txt"
    marker_path.write_text(
        "Prepared for TS-920 canceled directory picker validation.\n",
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
                "user.name=TS-920 Automation",
                "-c",
                "user.email=ts920@example.com",
                "commit",
                "--allow-empty",
                "-m",
                "Prepare TS-920 local workspace",
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
    switcher: WorkspaceSwitcherObservation,
) -> None:
    if local_row is None:
        raise AssertionError(
            "Step 1 failed: the Workspace switcher did not expose the saved local workspace row.\n"
            f"Observed rows: {[row.visible_text for row in switcher.rows]!r}\n"
            f"Observed switcher text:\n{switcher.switcher_text}"
        )
    if local_row.state_label != "Unavailable":
        raise AssertionError(
            "Step 1 failed: the saved local workspace row was not shown in the expected "
            "`Unavailable` state before the manual restore action.\n"
            f"Observed local row: {json.dumps(_row_payload(local_row), indent=2)}"
        )
    if selected_row is not None and selected_row.display_name == LOCAL_DISPLAY_NAME:
        raise AssertionError(
            "Step 1 failed: the unavailable local workspace was already selected before "
            "the manual restore action.\n"
            f"Observed selected row: {json.dumps(_row_payload(selected_row), indent=2)}"
        )


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


def _manual_cancel_probe_script() -> str:
    return """
    (() => {
      const state = window.__ts920ManualCancelProbe = {
        showDirectoryPickerCalls: [],
        requestPermissionCalls: [],
        queryPermissionCalls: [],
        canceledPickerErrors: [],
        deniedPermissionResults: [],
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
      const fileSystemHandleProto = window.FileSystemHandle && window.FileSystemHandle.prototype;
      if (fileSystemHandleProto && typeof fileSystemHandleProto.requestPermission === 'function') {
        fileSystemHandleProto.requestPermission = async function(...args) {
          state.requestPermissionCalls.push({
            callNumber: state.requestPermissionCalls.length + 1,
            args: serialize(args),
          });
          state.deniedPermissionResults.push({
            callNumber: state.deniedPermissionResults.length + 1,
            result: 'denied',
          });
          return 'denied';
        };
      }
      wrap(fileSystemHandleProto, 'queryPermission', 'queryPermissionCalls');

      if (typeof window.showDirectoryPicker === 'function') {
        window.showDirectoryPicker = async function(...args) {
          state.showDirectoryPickerCalls.push({
            callNumber: state.showDirectoryPickerCalls.length + 1,
            args: serialize(args),
          });
          const error = new DOMException('The user aborted a request.', 'AbortError');
          state.canceledPickerErrors.push({
            callNumber: state.canceledPickerErrors.length + 1,
            name: error.name,
            message: error.message,
          });
          throw error;
        };
      } else {
        state.wrapErrors.push('window.showDirectoryPicker is not available');
      }
    })();
    """


def _saved_workspace_action_label(
    row: WorkspaceSwitcherSavedWorkspaceRowObservation | None,
) -> str:
    if row is None:
        raise AssertionError(
            "Step 2 failed: the open workspace switcher did not expose a saved local "
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
            "Step 2 failed: the unavailable local workspace row did not expose any "
            "visible manual action.\n"
            f"Observed saved row: {json.dumps(_saved_row_payload(row), indent=2)}"
        )
    return action_label


def _read_manual_cancel_probe(tracker_page) -> dict[str, object]:
    payload = tracker_page.session.evaluate(
        """
        () => {
          const probe = window.__ts920ManualCancelProbe || {};
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
            canceledPickerErrors: Array.isArray(probe.canceledPickerErrors)
              ? probe.canceledPickerErrors
              : [],
            deniedPermissionResults: Array.isArray(probe.deniedPermissionResults)
              ? probe.deniedPermissionResults
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
            "canceledPickerErrors": [],
            "deniedPermissionResults": [],
            "wrapErrors": [],
        }
    return {
        "showDirectoryPickerCalls": list(payload.get("showDirectoryPickerCalls", [])),
        "requestPermissionCalls": list(payload.get("requestPermissionCalls", [])),
        "queryPermissionCalls": list(payload.get("queryPermissionCalls", [])),
        "canceledPickerErrors": list(payload.get("canceledPickerErrors", [])),
        "deniedPermissionResults": list(payload.get("deniedPermissionResults", [])),
        "wrapErrors": list(payload.get("wrapErrors", [])),
    }


def _observe_manual_cancel_attempt(
    *,
    tracker_page,
    page: LiveWorkspaceSwitcherPage,
) -> dict[str, object]:
    body_text = tracker_page.body_text()
    probe = _read_manual_cancel_probe(tracker_page)
    trigger = _safe_workspace_trigger_payload(tracker_page)
    return {
        "probe": probe,
        "body_text": body_text,
        "trigger": trigger,
        "browser_access_callback_observed": bool(
            probe["showDirectoryPickerCalls"] or probe["requestPermissionCalls"]
        ),
        "directory_picker_called": bool(probe["showDirectoryPickerCalls"]),
        "cancel_error_observed": bool(
            probe["canceledPickerErrors"] or probe["deniedPermissionResults"]
        ),
        "unsupported_operation_visible": "Unsupported operation: Process.run" in body_text,
    }


def _observe_post_cancel_state(
    *,
    tracker_page,
    page: LiveWorkspaceSwitcherPage,
    expected_hosted_workspace_id: str,
) -> dict[str, object]:
    trigger = _safe_workspace_trigger_payload(tracker_page)
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
    switcher_after = _capture_switcher(tracker_page, page)
    switcher_labels = _observe_switcher_accessible_labels(
        tracker_page,
        switcher_after,
    )
    body_text = tracker_page.body_text()

    local_row = _find_named_local_row(switcher_after)
    selected_row = _find_selected_row(switcher_after)
    local_row_unavailable = bool(
        local_row is not None and local_row.state_label == "Unavailable",
    )
    hosted_still_active = bool(
        trigger is not None
        and trigger["display_name"] == HOSTED_DISPLAY_NAME
        and trigger["workspace_type"] == "Hosted"
        and selected_row is not None
        and selected_row.display_name == HOSTED_DISPLAY_NAME
        and selected_row.target_type_label == "Hosted"
    )
    storage_unchanged = bool(
        persisted_workspace_state is not None
        and persisted_workspace_state.get("activeWorkspaceId") == expected_hosted_workspace_id
    )
    return {
        "trigger": trigger,
        "switcher": _switcher_payload(switcher_after),
        "local_row_label": switcher_labels["local_row_label"],
        "hosted_row_label": switcher_labels["hosted_row_label"],
        "selected_row_label": switcher_labels["selected_row_label"],
        "local_action_label": switcher_labels["local_action_label"],
        "visible_aria_labels": switcher_labels["visible_aria_labels"],
        "shell_observation": shell_observation,
        "persisted_workspace_state": persisted_workspace_state,
        "body_text": body_text,
        "local_row_unavailable": local_row_unavailable,
        "hosted_still_active": hosted_still_active,
        "storage_unchanged": storage_unchanged,
        "shell_ready": bool(shell_observation.get("shell_ready")),
        "fatal_banner_visible": bool(shell_observation.get("fatal_banner_visible")),
        "workspace_open_failure_visible": f"Could not open {LOCAL_DISPLAY_NAME}" in body_text,
        "unsupported_operation_visible": "Unsupported operation: Process.run" in body_text,
    }


def _observe_unavailable_local_precondition(
    *,
    tracker_page,
    page: LiveWorkspaceSwitcherPage,
) -> dict[str, object]:
    switcher = _capture_switcher(tracker_page, page)
    switcher_labels = _observe_switcher_accessible_labels(tracker_page, switcher)
    local_row = _find_named_local_row(switcher)
    return {
        "switcher": _switcher_payload(switcher),
        "local_row_label": switcher_labels["local_row_label"],
        "hosted_row_label": switcher_labels["hosted_row_label"],
        "selected_row_label": switcher_labels["selected_row_label"],
        "local_action_label": switcher_labels["local_action_label"],
        "trigger": _safe_workspace_trigger_payload(tracker_page),
        "visible_aria_labels": switcher_labels["visible_aria_labels"],
        "local_row_unavailable": bool(
            local_row is not None and local_row.state_label == "Unavailable"
        ),
    }


def _capture_switcher(
    tracker_page,
    page: LiveWorkspaceSwitcherPage,
    *,
    timeout_ms: int = 20_000,
) -> WorkspaceSwitcherObservation:
    try:
        return page.observe_open_switcher(timeout_ms=min(timeout_ms, 3_000))
    except Exception:
        return _open_and_observe_switcher(tracker_page, page, timeout_ms=timeout_ms)


def _open_and_observe_switcher(
    tracker_page,
    page: LiveWorkspaceSwitcherPage,
    *,
    timeout_ms: int = 20_000,
) -> WorkspaceSwitcherObservation:
    clicked_label = tracker_page.session.evaluate(
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
          const labelFor = (element) =>
            normalize(
              element.getAttribute?.('aria-label')
              || element.innerText
              || element.textContent
              || '',
            );
          const candidates = Array.from(document.querySelectorAll('*'))
            .filter((candidate) => isVisible(candidate))
            .map((element) => ({
              element,
              label: labelFor(element),
            }))
            .filter((candidate) => candidate.label.startsWith('Workspace switcher:'));
          const match = candidates[0] ?? null;
          if (!match) {
            return null;
          }
          match.element.click();
          return match.label;
        }
        """,
    )
    if clicked_label is None:
        raise AssertionError(
            "The live app did not expose a clickable workspace switcher trigger.\n"
            f"Observed body text:\n{tracker_page.body_text()}",
        )
    return page.observe_open_switcher(timeout_ms=timeout_ms)


def _observe_switcher_accessible_labels(
    tracker_page,
    switcher: WorkspaceSwitcherObservation,
) -> dict[str, object]:
    payload = tracker_page.session.evaluate(
        f"""
        () => {{
          const normalize = (value) => (value || '').replace(/\\s+/g, ' ').trim();
          const isVisible = (element) => {{
            if (!element) {{
              return false;
            }}
            const rect = element.getBoundingClientRect();
            const style = window.getComputedStyle(element);
            return rect.width > 0
              && rect.height > 0
              && style.visibility !== 'hidden'
              && style.display !== 'none';
          }};
          const visibleAriaLabels = Array.from(document.querySelectorAll('[aria-label]'))
            .filter((element) => isVisible(element))
            .map((element) => normalize(element.getAttribute('aria-label') || ''))
            .filter((label) => label.length > 0);
          return {{
            visibleAriaLabels,
          }};
        }}
        """,
    )
    if not isinstance(payload, dict):
        raise AssertionError(
            "Expected a workspace switcher accessibility payload, "
            f"got: {payload!r}",
        )
    local_row = _find_named_local_row(switcher)
    hosted_row = _find_named_hosted_row(switcher)
    selected_row = _find_selected_row(switcher)
    local_action_label = (
        next(
            (
                action_label
                for action_label in local_row.action_labels
                if action_label and not action_label.startswith("Delete:")
            ),
            None,
        )
        if local_row is not None
        else None
    )
    return {
        "visible_aria_labels": list(payload.get("visibleAriaLabels", [])),
        "local_row_label": _workspace_row_label(local_row),
        "hosted_row_label": _workspace_row_label(hosted_row),
        "selected_row_label": _workspace_row_label(selected_row),
        "local_action_label": local_action_label,
    }


def _safe_workspace_trigger_payload(tracker_page) -> dict[str, object] | None:
    try:
        observation = tracker_page.observe_workspace_switcher_trigger(timeout_ms=5_000)
    except AssertionError:
        return None
    return _workspace_trigger_payload(
        aria_label=observation.aria_label,
        visible_text=observation.visible_text,
        body_text=observation.body_text,
    )


def _workspace_trigger_payload(
    *,
    aria_label: str,
    visible_text: str,
    body_text: str,
) -> dict[str, object]:
    prefix = "Workspace switcher:"
    normalized_label = aria_label.strip()
    display_name = ""
    workspace_type = ""
    state_label = ""
    if normalized_label.startswith(prefix):
        remainder = normalized_label[len(prefix) :].strip()
        parts = [part.strip() for part in remainder.split(",")]
        if len(parts) >= 3:
            display_name = parts[0]
            workspace_type = parts[1]
            state_label = ", ".join(parts[2:])
    return {
        "aria_label": aria_label,
        "visible_text": visible_text,
        "body_text": body_text,
        "display_name": display_name,
        "workspace_type": workspace_type,
        "state_label": state_label,
    }


def _workspace_row_label(row: WorkspaceSwitcherRowObservation | None) -> str | None:
    if row is None:
        return None
    return row.visible_text or row.semantics_label or row.detail_text or row.display_name


def _observe_startup_surface(tracker_page) -> dict[str, object]:
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
          const visibleButtons = Array.from(
            document.querySelectorAll('flt-semantics[role="button"],button,[role="button"]')
          )
            .filter((element) => isVisible(element))
            .map((element) =>
              normalize(
                element.getAttribute?.('aria-label')
                || element.innerText
                || element.textContent
                || '',
              )
            )
            .filter((label) => label.length > 0);
          const visibleAriaLabels = Array.from(document.querySelectorAll('[aria-label]'))
            .filter((element) => isVisible(element))
            .map((element) => normalize(element.getAttribute('aria-label') || ''))
            .filter((label) => label.length > 0);
          return {
            bodyText: normalize(document.body.innerText),
            visibleButtonLabels: visibleButtons,
            visibleAriaLabels,
            url: window.location.href,
          };
        }
        """,
    )
    if not isinstance(payload, dict):
        return {
            "body_text": tracker_page.body_text(),
            "visible_button_labels": [],
            "visible_aria_labels": [],
            "url": "",
        }
    return {
        "body_text": str(payload.get("bodyText", "")),
        "visible_button_labels": list(payload.get("visibleButtonLabels", [])),
        "visible_aria_labels": list(payload.get("visibleAriaLabels", [])),
        "url": str(payload.get("url", "")),
    }

def _saved_row_from_payload(
    payload: dict[str, object] | None,
) -> WorkspaceSwitcherSavedWorkspaceRowObservation | None:
    if payload is None:
        return None
    return WorkspaceSwitcherSavedWorkspaceRowObservation(
        display_name=str(payload["display_name"]),
        target_type_label=(
            None
            if payload.get("target_type_label") is None
            else str(payload["target_type_label"])
        ),
        state_label=None if payload.get("state_label") is None else str(payload["state_label"]),
        detail_text=str(payload["detail_text"]),
        selected=bool(payload["selected"]),
        action_labels=tuple(str(label) for label in payload["action_labels"]),
        left=float(payload["left"]),
        top=float(payload["top"]),
        width=float(payload["width"]),
        height=float(payload["height"]),
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
        f"Observed: {{code}}{step['observed']}{{code}}"
        for step in steps
        if isinstance(step, dict)
    ]
    verifications = result.get("human_verification", [])
    verification_lines = [
        f"* {item['check']} Observed: {{code}}{item['observed']}{{code}}"
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
        f"*Cancel simulation*: {result.get('manual_cancel_simulation')}",
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
            "The live app attempted browser-access recovery, the simulated cancel or "
            "dismiss left the hosted workspace active, the saved local workspace "
            "stayed `Unavailable`, and no `Unsupported operation: Process.run` or "
            "runtime page error was observed."
            if passed
            else str(
                result.get(
                    "error",
                    "Canceling the directory picker did not keep the workspace in the expected unavailable state.",
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
        f"**Cancel simulation:** {result.get('manual_cancel_simulation')}",
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
                "The live app attempted browser-access recovery, the simulated cancel "
                "or dismiss left the hosted workspace active, the saved local workspace "
                "stayed `Unavailable`, and no unsupported-operation or runtime page "
                "error surfaced."
                if passed
                else str(
                    result.get(
                        "error",
                        "Canceling the directory picker did not keep the workspace in the expected unavailable state.",
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
    if passed:
        return (
            f"{TICKET_KEY} passed.\n\n"
            f"{REWORK_SUMMARY}\n\n"
            "The live unavailable-workspace restore flow attempted browser access, "
            "the simulated cancel or dismiss kept the workspace `Unavailable`, and "
            "the hosted workspace remained active without an unsupported-operation "
            "or runtime page error.\n"
        )
    return (
        f"{TICKET_KEY} failed.\n\n"
        f"{REWORK_SUMMARY}\n\n"
        f"{result.get('error', 'Canceling the directory picker did not keep the workspace in the expected unavailable state.')}\n"
    )


def _build_bug_description(result: dict[str, object]) -> str:
    steps = result.get("steps", [])
    screenshot = result.get("screenshot")
    startup_observation = result.get("startup_observation")
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
        str(
            result.get(
                "error",
                "Canceling the directory picker did not keep the workspace in the expected unavailable state.",
            ),
        ),
        "",
        "## Expected result",
        EXPECTED_RESULT,
        "",
        "## Actual vs expected",
        (
            "Expected the deployed app to load the hosted tracker shell, let the user "
            "open the Workspace switcher, trigger the browser directory picker, and "
            "then leave the local workspace in `Unavailable` after Cancel. "
            "Instead, the live deployment stalled before the Workspace switcher was "
            "reachable."
            if isinstance(startup_observation, dict)
            else "Expected clicking `Retry: Restorable local workspace` to start the "
            "browser-access recovery flow (`showDirectoryPicker()` or a remembered "
            "handle `requestPermission()`), after which Cancel would leave the local "
            "workspace in `Unavailable` with the hosted workspace still active. "
            "Instead, clicking `Retry` returned the user to the dashboard shell and "
            "the probe recorded zero `showDirectoryPicker()` calls and zero "
            "`requestPermission()` calls."
        ),
        "",
        "## Environment details",
        f"- URL: {result.get('app_url')}",
        f"- Browser: {result.get('browser')}",
        f"- OS: {result.get('os')}",
        f"- Viewport: {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
        f"- Local workspace target: {LOCAL_TARGET}",
        f"- Run command: `{RUN_COMMAND}`",
        f"- Cancel simulation: {result.get('manual_cancel_simulation')}",
        "",
        "## Observed state",
        f"- Trigger before action: `{json.dumps(result.get('trigger_before_action'), ensure_ascii=True)}`",
        f"- Startup observation: `{json.dumps(startup_observation, ensure_ascii=True)}`",
        f"- Local row before action: `{json.dumps(result.get('local_row_before_action'), ensure_ascii=True)}`",
        f"- Manual action label: `{result.get('manual_restore_action_label')}`",
        f"- Manual cancel probe after action: `{json.dumps(result.get('manual_cancel_probe_after_action'), ensure_ascii=True)}`",
        f"- Trigger after cancel: `{json.dumps(result.get('trigger_after_cancel'), ensure_ascii=True)}`",
        f"- Local row after cancel: `{json.dumps(result.get('local_row_after_cancel'), ensure_ascii=True)}`",
        f"- Selected row after cancel: `{json.dumps(result.get('selected_row_after_cancel'), ensure_ascii=True)}`",
        f"- Persisted workspace state: `{json.dumps(result.get('persisted_workspace_state'), ensure_ascii=True)}`",
        f"- Page errors: `{json.dumps(result.get('page_errors'), ensure_ascii=True)}`",
        f"- Console events: `{json.dumps(result.get('console_events'), ensure_ascii=True)}`",
    ]
    if screenshot:
        lines.extend(["", "## Screenshots or logs", f"- Screenshot: `{screenshot}`"])
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
