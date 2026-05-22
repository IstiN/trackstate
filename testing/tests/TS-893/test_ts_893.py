from __future__ import annotations

from dataclasses import dataclass
import json
import os
import platform
import stat
import subprocess
import sys
import threading
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
    WorkspaceSwitcherTriggerObservation,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.utils.polling import poll_until  # noqa: E402
from testing.tests.support.live_tracker_app_factory import create_live_tracker_app  # noqa: E402
from testing.tests.support.ts723_workspace_restore_runtime import (  # noqa: E402
    Ts723WorkspaceRestoreRuntime,
)

TICKET_KEY = "TS-893"
TEST_CASE_TITLE = (
    "Startup with transiently busy file system handle — workspace restored as "
    "Local Git via retry"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-893/test_ts_893.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
DEFAULT_BRANCH = "main"
LOCAL_TARGET = "/tmp/trackstate-demo"
LOCAL_DISPLAY_NAME = "Active local workspace"
HOSTED_DISPLAY_NAME = "Hosted setup workspace"
TRIGGER_WAIT_SECONDS = 90
PRE_RELEASE_TRIGGER_TIMEOUT_SECONDS = 15
STARTUP_RETRY_OVERLAP_WINDOW_SECONDS = 12
PRE_RELEASE_RESTORE_MESSAGE_TIMEOUT_MS = 250
LINKED_BUGS = ["TS-882", "TS-896"]
RESTORE_MESSAGE_WAIT_SECONDS = 20

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
REVIEW_REPLIES_PATH = OUTPUTS_DIR / "review_replies.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts893_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts893_failure.png"
DISCUSSIONS_RAW_PATH = REPO_ROOT / "input" / TICKET_KEY / "pr_discussions_raw.json"
WEB_LOCAL_GIT_RUNTIME_STUB_PATH = (
    REPO_ROOT / "lib" / "data" / "repositories" / "trackstate_repository_factory_stub.dart"
)
WEB_LOCAL_GIT_RUNTIME_STUB_MESSAGE = (
    "The local Git runtime is not available in web builds. Use the hosted GitHub runtime."
)

REQUEST_STEPS = [
    "Refresh the browser to trigger the application startup.",
    "Release the directory lock or busy state while the application is in its initialization/retry phase.",
    "Wait for the application shell to become interactive.",
    "Open the Workspace switcher.",
]
EXPECTED_RESULT = (
    "The application successfully retries the handle revalidation and restores "
    "the local workspace as the active `Local Git` row. The user does not see "
    "`Local Unavailable` or a fallback to `Hosted setup workspace` once the "
    "handle becomes available."
)


@dataclass
class _TransientBusyWorkspaceBlocker:
    path: Path
    release_after_seconds: float | None = None

    def __post_init__(self) -> None:
        self.original_mode: int | None = None
        self.blocked_mode = 0
        self.blocked_at_monotonic: float | None = None
        self.released_at_monotonic: float | None = None
        self.release_error: str | None = None
        self._released = threading.Event()
        self._thread: threading.Thread | None = None

    def __enter__(self) -> "_TransientBusyWorkspaceBlocker":
        self.original_mode = stat.S_IMODE(os.stat(self.path).st_mode)
        os.chmod(self.path, self.blocked_mode)
        self.blocked_at_monotonic = time.monotonic()
        if self.release_after_seconds is not None:
            self._thread = threading.Thread(target=self._delayed_release, daemon=True)
            self._thread.start()
        return self

    def __exit__(self, exc_type, exc, exc_tb) -> None:
        self._restore_now()
        if self._thread is not None:
            self._thread.join(timeout=1)
        return None

    def _delayed_release(self) -> None:
        try:
            time.sleep(self.release_after_seconds)
            self._restore_now()
        except Exception as error:  # pragma: no cover - defensive bookkeeping
            self.release_error = f"{type(error).__name__}: {error}"
            self._released.set()

    def _restore_now(self) -> None:
        if self.original_mode is None or self._released.is_set():
            return
        os.chmod(self.path, self.original_mode)
        self.released_at_monotonic = time.monotonic()
        self._released.set()

    def wait_for_release(self, *, timeout_seconds: float) -> bool:
        return self._released.wait(timeout_seconds)

    def release(self) -> None:
        self._restore_now()

    def snapshot(self) -> dict[str, object]:
        current_mode = stat.S_IMODE(os.stat(self.path).st_mode)
        return {
            "path": str(self.path),
            "release_after_seconds": self.release_after_seconds,
            "original_mode_octal": (
                oct(self.original_mode) if self.original_mode is not None else None
            ),
            "current_mode_octal": oct(current_mode),
            "blocked_mode_octal": oct(self.blocked_mode),
            "blocked_at_monotonic": self.blocked_at_monotonic,
            "released_at_monotonic": self.released_at_monotonic,
            "release_error": self.release_error,
            "released": self._released.is_set(),
        }


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-893 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
        )
    user = service.fetch_authenticated_user()
    workspace_state = _workspace_state(service.repository)
    prepared_local_workspace = _prepare_local_workspace_repository()
    blocker = _TransientBusyWorkspaceBlocker(
        path=Path(LOCAL_TARGET),
    )

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
        "user_login": user.login,
        "preloaded_workspace_state": workspace_state,
        "prepared_local_workspace": prepared_local_workspace,
        "trigger_wait_seconds": TRIGGER_WAIT_SECONDS,
        "pre_release_trigger_timeout_seconds": PRE_RELEASE_TRIGGER_TIMEOUT_SECONDS,
        "startup_retry_overlap_window_seconds": STARTUP_RETRY_OVERLAP_WINDOW_SECONDS,
        "pre_release_restore_message_timeout_ms": PRE_RELEASE_RESTORE_MESSAGE_TIMEOUT_MS,
        "restore_message_wait_seconds": RESTORE_MESSAGE_WAIT_SECONDS,
        "steps": [],
        "human_verification": [],
    }

    page: LiveWorkspaceSwitcherPage | None = None
    try:
        runtime = Ts723WorkspaceRestoreRuntime(
            repository=config.repository,
            token=token,
            workspace_state=workspace_state,
        )
        with blocker:
            result["busy_blocker_initial"] = blocker.snapshot()
            with create_live_tracker_app(
                config,
                runtime_factory=lambda: runtime,
            ) as tracker_page:
                page = LiveWorkspaceSwitcherPage(tracker_page)
                try:
                    failure_message: str | None = None
                    runtime_observation = tracker_page.open()
                    result["runtime_state"] = runtime_observation.kind
                    result["runtime_body_text"] = runtime_observation.body_text
                    if runtime_observation.kind != "ready":
                        raise AssertionError(
                            "Precondition failed: the deployed app did not reach the "
                            "interactive shell with the signed-in active-local workspace "
                            "preload.\n"
                            f"Observed runtime state: {runtime_observation.kind}\n"
                            f"Observed body text:\n{runtime_observation.body_text}",
                        )

                    page.dismiss_connection_banner()
                    page.set_viewport(**DESKTOP_VIEWPORT)
                    _record_step(
                        result,
                        step=1,
                        status="passed",
                        action=REQUEST_STEPS[0],
                        observed=(
                            "Opened the deployed app in Chromium with a stored signed-in "
                            "GitHub session, preloaded the active local workspace in "
                            "browser storage, and kept access revoked for the "
                            f"prepared local git folder at {LOCAL_TARGET!r} to simulate a transient busy state."
                        ),
                    )

                    pre_release_trigger = page.observe_trigger(
                        timeout_ms=int(PRE_RELEASE_TRIGGER_TIMEOUT_SECONDS * 1000),
                    )
                    result["pre_release_trigger_observation"] = _trigger_payload(
                        pre_release_trigger,
                    )
                    pre_release_body_text = page.current_body_text()
                    overlap_captured, overlap_state = poll_until(
                        probe=lambda: _collect_pre_release_overlap_state(
                            page=page,
                            tracker_page=tracker_page,
                            runtime=runtime,
                        ),
                        is_satisfied=lambda state: bool(
                            isinstance(state, dict)
                            and state.get("overlap_proof_sources")
                        ),
                        timeout_seconds=STARTUP_RETRY_OVERLAP_WINDOW_SECONDS,
                        interval_seconds=0.5,
                    )
                    result["pre_release_body_text"] = pre_release_body_text
                    result["pre_release_overlap_captured"] = overlap_captured
                    result["pre_release_activity_captured"] = bool(
                        overlap_state["pre_release_activity_captured"],
                    )
                    result["pre_release_all_activity_events"] = list(
                        overlap_state["pre_release_all_activity_events"],
                    )
                    result["pre_release_activity_events"] = list(
                        overlap_state["pre_release_activity_events"],
                    )
                    result["pre_release_activity"] = overlap_state["pre_release_activity"]
                    result["pre_release_runtime_probe_captured"] = bool(
                        overlap_state["pre_release_runtime_probe_captured"],
                    )
                    result["pre_release_runtime_probe"] = overlap_state[
                        "pre_release_runtime_probe"
                    ]
                    result["pre_release_runtime_probe_events"] = list(
                        overlap_state["pre_release_runtime_probe_events"],
                    )
                    result["pre_release_public_overlap_observed"] = bool(
                        overlap_state["pre_release_public_overlap_observed"],
                    )
                    result["pre_release_public_overlap_state"] = overlap_state[
                        "pre_release_public_overlap_state"
                    ]
                    result["pre_release_restore_message"] = overlap_state[
                        "pre_release_restore_message"
                    ]
                    overlap_proof_sources = list(overlap_state["overlap_proof_sources"])
                    result["pre_release_overlap_proved"] = bool(overlap_proof_sources)
                    result["pre_release_overlap_proof_sources"] = overlap_proof_sources
                    result["busy_blocker_before_release"] = blocker.snapshot()
                    blocker.release()
                    released = blocker.wait_for_release(timeout_seconds=5)
                    result["busy_blocker_final"] = blocker.snapshot()
                    result["busy_state_released"] = released
                    if blocker.release_error is not None:
                        raise AssertionError(
                            "Step 2 failed: the test could not restore access to the "
                            "prepared local workspace during the retry phase.\n"
                            f"{blocker.release_error}"
                        )
                    if not released:
                        raise AssertionError(
                            "Step 2 failed: the simulated busy state was not released "
                            "within the expected retry window.",
                        )
                    if overlap_proof_sources:
                        step_2_summary = (
                            "Kept the local workspace blocked until the header workspace "
                            "trigger was already observable, captured restore-specific "
                            "blocked-window diagnostics before release, then restored "
                            "access during startup recovery."
                        )
                    else:
                        step_2_summary = (
                            "Kept the local workspace blocked until the header workspace "
                            "trigger was already observable, then restored access during "
                            "startup recovery. While access was still blocked, the "
                            "deployed web surface exposed no restore-specific blocked-window "
                            "diagnostics for the saved local workspace handle before "
                            "release, so the test continued into the ticket's post-release "
                            "`Local Git` assertions and retained the missing overlap as "
                            "diagnostic evidence instead of failing Step 2 synthetically."
                        )
                    step_2_observed = (
                        step_2_summary
                        + "\npre_release_overlap_proof_sources="
                        + f"{json.dumps(overlap_proof_sources, indent=2)}\n"
                        + f"pre_release_trigger={json.dumps(_trigger_payload(pre_release_trigger), indent=2)}\n"
                        + f"pre_release_body_text={pre_release_body_text!r}\n"
                        + "pre_release_public_overlap_state="
                        + f"{json.dumps(result['pre_release_public_overlap_state'], indent=2)}\n"
                        + "pre_release_public_overlap_observed="
                        + f"{result['pre_release_public_overlap_observed']}\n"
                        + "pre_release_activity="
                        + f"{json.dumps(result['pre_release_activity'], indent=2)}\n"
                        + "pre_release_all_activity_events="
                        + f"{json.dumps(result['pre_release_all_activity_events'], indent=2)}\n"
                        + "pre_release_activity_events="
                        + f"{json.dumps(result['pre_release_activity_events'], indent=2)}\n"
                        + "pre_release_activity_captured="
                        + f"{result['pre_release_activity_captured']}\n"
                        + (
                            "pre_release_runtime_probe="
                            f"{json.dumps(result['pre_release_runtime_probe'], indent=2)}\n"
                            if result["pre_release_runtime_probe"] is not None
                            else "pre_release_runtime_probe=<not observed before release>\n"
                        )
                        + "pre_release_runtime_probe_events="
                        + f"{json.dumps(result['pre_release_runtime_probe_events'], indent=2)}\n"
                        + "pre_release_runtime_probe_captured="
                        + f"{result['pre_release_runtime_probe_captured']}\n"
                        + f"pre_release_restore_message={result['pre_release_restore_message']!r}\n"
                        + f"startup_retry_overlap_window_seconds={STARTUP_RETRY_OVERLAP_WINDOW_SECONDS}\n"
                        f"busy_blocker={json.dumps(blocker.snapshot(), indent=2)}"
                    )
                    _record_step(
                        result,
                        step=2,
                        status="passed",
                        action=REQUEST_STEPS[1],
                        observed=step_2_observed,
                    )

                    restore_message = _observe_restore_message(
                        tracker_page,
                        timeout_ms=int(RESTORE_MESSAGE_WAIT_SECONDS * 1000),
                    )
                    result["restore_message"] = restore_message
                    restored, trigger = poll_until(
                        probe=lambda: page.observe_trigger(timeout_ms=10_000),
                        is_satisfied=_trigger_matches_expected_restore,
                        timeout_seconds=TRIGGER_WAIT_SECONDS,
                        interval_seconds=5,
                    )
                    result["trigger_observation"] = _trigger_payload(trigger)
                    result["startup_restored_within_wait"] = restored
                    if restored:
                        _record_step(
                            result,
                            step=3,
                            status="passed",
                            action=REQUEST_STEPS[2],
                            observed=(
                                "After the busy state was released, the application shell "
                                "restored the prepared local workspace in the workspace "
                                "switcher trigger "
                                f"within {TRIGGER_WAIT_SECONDS} seconds. "
                                "Observed pre_release_overlap_proof_sources="
                                f"{json.dumps(overlap_proof_sources, ensure_ascii=True)}; "
                                "Observed pre_release_public_overlap_state="
                                f"{json.dumps(result['pre_release_public_overlap_state'], ensure_ascii=True)}; "
                                "Observed pre_release_activity="
                                f"{json.dumps(result['pre_release_activity'], ensure_ascii=True)}; "
                                "Observed pre_release_runtime_probe="
                                f"{json.dumps(result['pre_release_runtime_probe'], ensure_ascii=True)}; "
                                "Observed pre_release_restore_message="
                                f"{result['pre_release_restore_message']!r}; "
                                f"Observed pre_release_trigger={pre_release_trigger.semantic_label!r}; "
                                f"restore_message={restore_message!r}; "
                                f"trigger label={trigger.semantic_label!r}; "
                                f"trigger_text={trigger.visible_text!r}"
                            ),
                        )
                    else:
                        _record_step(
                            result,
                            step=3,
                            status="failed",
                            action=REQUEST_STEPS[2],
                            observed=(
                                "After the busy state was released, the application shell "
                                "never restored the prepared local workspace in the "
                                "workspace switcher trigger "
                                f"within {TRIGGER_WAIT_SECONDS} seconds. "
                                "Observed pre_release_overlap_proof_sources="
                                f"{json.dumps(overlap_proof_sources, ensure_ascii=True)}; "
                                "Observed pre_release_public_overlap_state="
                                f"{json.dumps(result['pre_release_public_overlap_state'], ensure_ascii=True)}; "
                                "Observed pre_release_activity="
                                f"{json.dumps(result['pre_release_activity'], ensure_ascii=True)}; "
                                "Observed pre_release_runtime_probe="
                                f"{json.dumps(result['pre_release_runtime_probe'], ensure_ascii=True)}; "
                                "Observed pre_release_restore_message="
                                f"{result['pre_release_restore_message']!r}; "
                                f"Observed pre_release_trigger={pre_release_trigger.semantic_label!r}; "
                                f"restore_message={restore_message!r}; "
                                f"trigger label={trigger.semantic_label!r}; "
                                f"trigger_text={trigger.visible_text!r}"
                            ),
                        )

                    switcher_opened = False
                    try:
                        switcher = page.open_and_observe(timeout_ms=15_000)
                        switcher_opened = True
                    except Exception as error:
                        result["switcher_open_error"] = f"{type(error).__name__}: {error}"
                        _record_step(
                            result,
                            step=4,
                            status="failed",
                            action=REQUEST_STEPS[3],
                            observed=(
                                "The application shell exposed the header trigger, but "
                                "opening Workspace switcher failed.\n"
                                f"{type(error).__name__}: {error}"
                            ),
                        )
                        raise

                    result["switcher_observation"] = _switcher_payload(switcher)
                    local_row = _find_named_local_row(switcher)
                    selected_row = _find_selected_row(switcher) or _selected_row_from_trigger(
                        trigger,
                    )
                    result["active_local_row"] = (
                        _row_payload(local_row) if local_row is not None else None
                    )
                    result["selected_row"] = (
                        _row_payload(selected_row) if selected_row is not None else None
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Viewed the header workspace trigger while the local workspace "
                            "was still blocked, recorded any tracked File System Access "
                            "activity and TS-893 runtime failure probe before releasing "
                            "access as diagnostic evidence, then checked the restored "
                            "trigger again after recovery."
                        ),
                        observed=(
                            "pre_release_activity="
                            f"{json.dumps(result['pre_release_activity'], ensure_ascii=True)}; "
                            "pre_release_all_activity_events="
                            f"{json.dumps(result['pre_release_all_activity_events'], ensure_ascii=True)}; "
                            "pre_release_activity_events="
                            f"{json.dumps(result['pre_release_activity_events'], ensure_ascii=True)}; "
                            "pre_release_overlap_proof_sources="
                            f"{json.dumps(overlap_proof_sources, ensure_ascii=True)}; "
                            "pre_release_runtime_probe="
                            f"{json.dumps(result['pre_release_runtime_probe'], ensure_ascii=True)}; "
                            "pre_release_runtime_probe_events="
                            f"{json.dumps(result['pre_release_runtime_probe_events'], ensure_ascii=True)}; "
                            "pre_release_restore_message="
                            f"{result['pre_release_restore_message']!r}; "
                            f"pre_release_trigger={pre_release_trigger.semantic_label!r}; "
                            f"restore_message={restore_message!r}; "
                            f"busy_blocker={json.dumps(blocker.snapshot(), ensure_ascii=True)}"
                        ),
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Viewed the startup result from the header trigger exactly as a "
                            "user would after the busy-state release and startup recovery window."
                        ),
                        observed=(
                            f"trigger_label={trigger.semantic_label!r}; "
                            f"trigger_text={trigger.visible_text!r}"
                        ),
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Opened Workspace switcher and visually inspected which row was "
                            "selected and what state labels were shown for the saved local workspace."
                        ),
                        observed=(
                            f"selected_row={json.dumps(_row_payload(selected_row), ensure_ascii=True)}; "
                            f"active_local_row={json.dumps(_row_payload(local_row), ensure_ascii=True)}"
                        ),
                    )
                    result["console_events"] = [
                        {"level": event.level, "text": event.text}
                        for event in runtime.console_events
                    ]
                    result["runtime_activity_events"] = [
                        _console_event_payload(event)
                        for event in runtime.activity_console_events
                    ]
                    result["tracked_runtime_activity_events"] = [
                        _console_event_payload(event)
                        for event in runtime.tracked_activity_console_events
                    ]
                    result["runtime_probe_events"] = [
                        _console_event_payload(event) for event in runtime.probe_console_events
                    ]
                    result["tracked_runtime_probe_events"] = [
                        _console_event_payload(event)
                        for event in runtime.tracked_probe_console_events
                    ]
                    result["page_errors"] = list(runtime.page_errors)

                    try:
                        _assert_active_local_restore(
                            trigger=trigger,
                            switcher=switcher,
                            local_row=local_row,
                            selected_row=selected_row,
                        )
                    except AssertionError as error:
                        _record_step(
                            result,
                            step=4,
                            status="failed",
                            action=REQUEST_STEPS[3],
                            observed=str(error),
                        )
                        failure_message = str(error)
                    else:
                        result["final_restore_verified"] = True
                        _record_step(
                            result,
                            step=4,
                            status="passed",
                            action=REQUEST_STEPS[3],
                            observed=(
                                "Opened Workspace switcher and confirmed the prepared local "
                                "workspace row remained selected in the visible `Local Git` "
                                "state after the busy-state release.\n"
                                f"selected_row={json.dumps(_row_payload(selected_row), indent=2)}"
                            ),
                        )

                    if not restored:
                        failure_message = (
                            "Step 3 failed: startup did not restore the prepared "
                            "active local workspace into the trigger after the "
                            "temporary busy state was released within the allowed "
                            "wait window.\n"
                            f"Observed trigger label: {trigger.semantic_label!r}\n"
                            "Observed selected row: "
                            f"{json.dumps(_row_payload(selected_row), indent=2)}\n"
                            "Observed active local row: "
                            f"{json.dumps(_row_payload(local_row), indent=2)}\n"
                            f"Observed switcher text:\n{switcher.switcher_text}"
                        )
                    if (
                        failure_message is None
                        and result.get("final_restore_verified") is True
                        and not result["runtime_activity_events"]
                        and not result["runtime_probe_events"]
                    ):
                        result["failure_reason"] = (
                            "missing_saved_handle_revalidation_capability"
                        )
                        failure_message = (
                            "The deployed web startup flow never invoked any File System "
                            "Access handle methods for the saved local workspace while "
                            "TS-893 kept the repository blocked and then released it. "
                            "The header trigger and workspace switcher already showed "
                            "`Local Git` before release and remained there afterward, "
                            "so this surface did not exercise the transient busy saved-"
                            "handle revalidation path required by TS-893."
                        )
                    if failure_message is not None:
                        raise AssertionError(failure_message)

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
                "lastOpenedAt": "2026-05-21T17:10:00.000Z",
            },
            {
                "id": hosted_id,
                "displayName": HOSTED_DISPLAY_NAME,
                "customDisplayName": HOSTED_DISPLAY_NAME,
                "targetType": "hosted",
                "target": repository,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": DEFAULT_BRANCH,
                "lastOpenedAt": "2026-05-21T17:00:00.000Z",
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

    marker_path = local_path / ".trackstate-ts893-precondition.txt"
    marker_path.write_text(
        "Prepared for TS-893 transient busy startup workspace restoration validation.\n",
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
                "user.name=TS-893 Automation",
                "-c",
                "user.email=ts893@example.com",
                "commit",
                "--allow-empty",
                "-m",
                "Prepare TS-893 local workspace",
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
        "mode_octal": oct(stat.S_IMODE(os.stat(local_path).st_mode)),
    }


def _trigger_matches_expected_restore(
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
    return _fallback_local_row_from_switcher_text(switcher.switcher_text)


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
        button_labels=("Delete",),
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


def _assert_active_local_restore(
    *,
    trigger: WorkspaceSwitcherTriggerObservation,
    switcher: WorkspaceSwitcherObservation,
    local_row: WorkspaceSwitcherRowObservation | None,
    selected_row: WorkspaceSwitcherRowObservation | None,
) -> None:
    if local_row is None:
        raise AssertionError(
            "Step 4 failed: Workspace switcher did not show the prepared local "
            "workspace row after the busy-state release.\n"
            f"Observed trigger label: {trigger.semantic_label!r}\n"
            f"Observed rows: {[row.visible_text for row in switcher.rows]!r}\n"
            f"Observed switcher text:\n{switcher.switcher_text}"
        )
    if local_row.state_label == "Unavailable" or "Local Unavailable" in local_row.visible_text:
        raise AssertionError(
            "Step 4 failed: the prepared local workspace row was visible after the "
            "busy-state release but rendered as `Local Unavailable` instead of "
            "`Local Git`.\n"
            f"Observed local row: {json.dumps(_row_payload(local_row), indent=2)}\n"
            f"Observed trigger label: {trigger.semantic_label!r}"
        )
    if local_row.state_label != "Local Git":
        raise AssertionError(
            "Step 4 failed: the prepared local workspace row did not reach the "
            "`Local Git` state after the busy-state release.\n"
            f"Observed local row: {json.dumps(_row_payload(local_row), indent=2)}"
        )
    if selected_row is None:
        raise AssertionError(
            "Step 4 failed: Workspace switcher did not show any selected active row.\n"
            f"Observed rows: {[row.visible_text for row in switcher.rows]!r}"
        )
    if selected_row.display_name != LOCAL_DISPLAY_NAME or selected_row.target_type_label != "Local":
        raise AssertionError(
            "Step 4 failed: the selected active row was not the prepared active local "
            "workspace after the busy-state release.\n"
            f"Observed selected row: {json.dumps(_row_payload(selected_row), indent=2)}\n"
            f"Observed local row: {json.dumps(_row_payload(local_row), indent=2)}"
        )
    if trigger.display_name == HOSTED_DISPLAY_NAME or trigger.workspace_type == "Hosted":
        raise AssertionError(
            "Step 4 failed: the header trigger still defaulted to the hosted setup "
            "workspace instead of the prepared active local workspace after the "
            "busy-state release.\n"
            f"Observed trigger label: {trigger.semantic_label!r}"
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


def _update_step_result(
    result: dict[str, object],
    *,
    step: int,
    status: str,
    observed: str,
) -> None:
    steps = result.get("steps", [])
    if not isinstance(steps, list):
        return
    for entry in steps:
        if not isinstance(entry, dict) or entry.get("step") != step:
            continue
        entry["status"] = status
        entry["observed"] = observed
        return


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
    REVIEW_REPLIES_PATH.write_text(
        _review_replies_payload(result, passed=True),
        encoding="utf-8",
    )


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
    JIRA_COMMENT_PATH.write_text(_jira_comment(result, passed=False), encoding="utf-8")
    PR_BODY_PATH.write_text(_markdown_summary(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_summary(result, passed=False), encoding="utf-8")
    REVIEW_REPLIES_PATH.write_text(
        _review_replies_payload(result, passed=False),
        encoding="utf-8",
    )
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
        "* Opened the deployed TrackState app in Chromium with a stored signed-in GitHub session and a preloaded active local workspace profile.",
        "* Kept access to the prepared local workspace blocked through the startup retry overlap window before releasing access.",
        "* Recorded any restore-specific blocked-window diagnostics before release from tracked File System Access activity, a TS-893 runtime probe event, the visible restore skip banner, or another public pre-release non-restored state.",
        f"* Waited up to {TRIGGER_WAIT_SECONDS} seconds after the busy-state release for the header workspace switcher trigger to restore the local workspace instead of asserting immediately.",
        "* Opened *Workspace switcher* and inspected the selected active row plus the prepared local row.",
        "* Verified the selected row reached {{Local Git}} and did not remain on {{Hosted setup workspace}} or {{Local Unavailable}}.",
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
        "- Opened the deployed TrackState app in Chromium with a stored signed-in GitHub session and a preloaded active local workspace profile.",
        "- Kept access to the prepared local workspace blocked through the startup retry overlap window before releasing access.",
        "- Recorded any restore-specific blocked-window diagnostics before release from tracked File System Access activity, a TS-893 runtime probe event, the visible restore skip banner, or another public pre-release non-restored state.",
        f"- Waited up to {TRIGGER_WAIT_SECONDS} seconds after the busy-state release for the header workspace switcher trigger to restore the local workspace instead of asserting immediately.",
        "- Opened **Workspace switcher** and inspected the selected active row plus the prepared local row.",
        "- Verified the selected row reached `Local Git` and did not remain on `Hosted setup workspace` or `Local Unavailable`.",
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
    overlap_summary = (
        "Restore-specific overlap diagnostics were captured before release."
        if result.get("pre_release_overlap_proved") is True
        else "No restore-specific blocked-window overlap diagnostics were observed before release."
    )
    outcome = (
        "Startup restored the prepared local workspace as the active `Local Git` "
        f"selection after the transient busy state cleared. {overlap_summary}"
        if passed
        else (
            _exact_error_summary(result)
        )
    )
    lines = [
        "## Rework Summary",
        "",
        "### Fixed Issues",
        "- Realigned TS-893 to the ticket's actual contract: the required product outcome is the post-release `Local Git` restore state, while blocked-window overlap probes are retained as diagnostic evidence.",
        "- Changed the failure path so the test only reports a product gap when the public restore state regresses or when the deployed web surface never exercises saved local handle revalidation at all.",
        "",
        "### Test Status",
        f"- Re-ran `{RUN_COMMAND}`",
        f"- Result: **{status}**",
        f"- Outcome: {outcome}",
    ]
    return "\n".join(lines) + "\n"


def _bug_description(result: dict[str, object]) -> str:
    trigger = result.get("trigger_observation") or result.get(
        "pre_release_trigger_observation",
    )
    pre_release_public_overlap_state = result.get("pre_release_public_overlap_state")
    switcher = result.get("switcher_observation")
    active_local_row = result.get("active_local_row")
    selected_row = result.get("selected_row")
    blocker_final = (
        result.get("busy_blocker_final")
        or result.get("busy_blocker_before_release")
        or result.get("busy_blocker_initial")
    )
    activity = result.get("pre_release_activity")
    all_activity_events = result.get("pre_release_all_activity_events")
    activity_events = result.get("pre_release_activity_events")
    runtime_probe = result.get("pre_release_runtime_probe")
    overlap_proof_sources = result.get("pre_release_overlap_proof_sources")
    restore_message = result.get("restore_message")
    return "\n".join(
        [
            f"# {_bug_title(result)}",
            "",
            "## Exact steps to reproduce",
            _annotated_step_line(result, 1, REQUEST_STEPS[0]),
            _annotated_step_line(result, 2, REQUEST_STEPS[1]),
            _annotated_step_line(result, 3, REQUEST_STEPS[2]),
            _annotated_step_line(result, 4, REQUEST_STEPS[3]),
            "",
            "## Exact error message or assertion failure",
            "```text",
            str(result.get("traceback", result.get("error", ""))),
            "```",
            "",
            "## Actual vs Expected",
            f"- **Expected:** {_bug_expected_result(result)}",
            f"- **Actual:** {_bug_actual_result(result)}",
            (
                f"- **Observed trigger:** `{_safe_dict_get(trigger, 'semantic_label')}`"
                if isinstance(trigger, dict)
                else "- **Observed trigger:** `<missing>`"
            ),
            (
                f"- **Observed selected row:** `{json.dumps(selected_row, ensure_ascii=True)}`"
                if selected_row is not None
                else "- **Observed selected row:** `<missing>`"
            ),
            (
                f"- **Observed active local row:** `{json.dumps(active_local_row, ensure_ascii=True)}`"
                if active_local_row is not None
                else "- **Observed active local row:** `<missing>`"
            ),
            (
                f"- **Observed busy-state release:** `{json.dumps(blocker_final, ensure_ascii=True)}`"
                if blocker_final is not None
                else "- **Observed busy-state release:** `<missing>`"
            ),
            (
                f"- **Observed raw pre-release activity events:** `{json.dumps(all_activity_events, ensure_ascii=True)}`"
                if all_activity_events is not None
                else "- **Observed raw pre-release activity events:** `<missing>`"
            ),
            (
                f"- **Observed pre-release activity:** `{json.dumps(activity, ensure_ascii=True)}`"
                if activity is not None
                else "- **Observed pre-release activity:** `<missing>`"
            ),
            (
                f"- **Observed pre-release activity events:** `{json.dumps(activity_events, ensure_ascii=True)}`"
                if activity_events is not None
                else "- **Observed pre-release activity events:** `<missing>`"
            ),
            (
                f"- **Observed pre-release public overlap state:** `{json.dumps(pre_release_public_overlap_state, ensure_ascii=True)}`"
                if pre_release_public_overlap_state is not None
                else "- **Observed pre-release public overlap state:** `<missing>`"
            ),
            (
                f"- **Observed overlap proof sources:** `{json.dumps(overlap_proof_sources, ensure_ascii=True)}`"
                if overlap_proof_sources is not None
                else "- **Observed overlap proof sources:** `<missing>`"
            ),
            (
                f"- **Observed runtime probe:** `{json.dumps(runtime_probe, ensure_ascii=True)}`"
                if runtime_probe is not None
                else "- **Observed runtime probe:** `<missing>`"
            ),
            (
                f"- **Observed restore message:** `{restore_message}`"
                if restore_message
                else "- **Observed restore message:** `<missing>`"
            ),
            f"- **Missing or broken capability:** {_bug_missing_capability(result)}",
            "",
            "## Environment details",
            f"- **URL:** {result.get('app_url')}",
            (
                f"- **Repository:** {result.get('repository')} @ "
                f"{result.get('repository_ref')}"
            ),
            f"- **Browser:** {result.get('browser')}",
            f"- **OS:** {result.get('os')}",
            f"- **Viewport:** {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
            f"- **Run command:** {RUN_COMMAND}",
            f"- **Prepared local workspace:** `{LOCAL_TARGET}`",
            "",
            "## Screenshots or logs",
            f"- **Screenshot:** {result.get('screenshot', '<no screenshot recorded>')}",
            "```json",
            json.dumps(
                {
                    "prepared_local_workspace": result.get("prepared_local_workspace"),
                    "preloaded_workspace_state": result.get("preloaded_workspace_state"),
                    "busy_blocker_initial": result.get("busy_blocker_initial"),
                    "busy_blocker_final": result.get("busy_blocker_final"),
                    "pre_release_activity": activity,
                    "pre_release_all_activity_events": all_activity_events,
                    "pre_release_activity_events": activity_events,
                    "pre_release_overlap_proof_sources": overlap_proof_sources,
                    "pre_release_public_overlap_state": pre_release_public_overlap_state,
                    "pre_release_runtime_probe": runtime_probe,
                    "restore_message": restore_message,
                    "trigger_observation": trigger,
                    "switcher_observation": switcher,
                    "active_local_row": active_local_row,
                    "selected_row": selected_row,
                },
                indent=2,
            ),
            "```",
        ],
    ) + "\n"


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for step in result.get("steps", []):
        assert isinstance(step, dict)
        prefix = "*" if jira else "-"
        status = "passed" if step.get("status") == "passed" else "failed"
        lines.append(
            f"{prefix} Step {step.get('step')} ({status}): {step.get('action')} "
            f"Observed: {step.get('observed')}"
        )
    return lines


def _human_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for check in result.get("human_verification", []):
        assert isinstance(check, dict)
        prefix = "*" if jira else "-"
        lines.append(
            f"{prefix} {check.get('check')} Observed: {check.get('observed')}"
        )
    if not lines:
        prefix = "*" if jira else "-"
        lines.append(
            f"{prefix} Human-style verification was limited to the observed startup trigger and workspace switcher evidence captured in the step results."
        )
    return lines


def _artifact_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    screenshot = result.get("screenshot")
    lines = ["", "h4. Screenshot" if jira else "## Screenshot"]
    lines.append(str(screenshot) if screenshot else "<no screenshot recorded>")
    lines.extend(
        [
            "",
            "h4. How to run" if jira else "## How to run",
            "{code:bash}" if jira else "```bash",
            RUN_COMMAND,
            "{code}" if jira else "```",
        ],
    )
    return lines


def _failed_step_summary(result: dict[str, object]) -> str:
    for step in result.get("steps", []):
        if isinstance(step, dict) and step.get("status") == "failed":
            observed = str(step.get("observed", ""))
            prefix = f"Step {step.get('step')} failed:"
            if observed.startswith(prefix):
                return observed
            return f"{prefix} {observed}"
    return str(result.get("error", "The scenario failed without recorded step details."))


def _review_replies_payload(result: dict[str, object], *, passed: bool) -> str:
    replies = [
        {
            "inReplyToId": thread.get("rootCommentId"),
            "threadId": thread.get("threadId"),
            "reply": _review_reply_text(passed=passed, result=result),
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
    return [
        thread
        for thread in threads
        if isinstance(thread, dict)
        and thread.get("rootCommentId") is not None
        and thread.get("threadId") is not None
    ]


def _review_reply_text(*, passed: bool, result: dict[str, object]) -> str:
    if passed:
        return (
            "Updated TS-893 to keep blocked-window overlap capture as diagnostic "
            "evidence, realigned the verdict to the ticket's post-release `Local Git` "
            "contract, and reserved failure for either a real restore regression or a "
            "live-surface capability gap where saved local handle revalidation never runs. "
            f"Re-ran `{RUN_COMMAND}`: passed (`1 passed, 0 failed`)."
        )
    return (
        "Updated TS-893 to keep blocked-window overlap capture as diagnostic "
        "evidence, realigned the verdict to the ticket's post-release `Local Git` "
        "contract, and reserved failure for either a real restore regression or a "
        "live-surface capability gap where saved local handle revalidation never runs. Re-ran "
        f"`{RUN_COMMAND}`: still failing. Current failure: {_exact_error_summary(result)}"
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
    return "AssertionError: TS-893 failed"


def _failed_due_to_release_error(result: dict[str, object]) -> bool:
    return (
        _failed_step_number(result) == 2
        and result.get("busy_state_released") is not True
    )


def _observe_restore_message(
    tracker_page,
    *,
    timeout_ms: int,
) -> str | None:
    try:
        observation = tracker_page.observe_workspace_restore_message(
            workspace_name=LOCAL_DISPLAY_NAME,
            timeout_ms=timeout_ms,
        )
    except Exception:
        return None
    return observation.message_text


def _collect_pre_release_overlap_state(
    *,
    page: LiveWorkspaceSwitcherPage,
    tracker_page,
    runtime: Ts723WorkspaceRestoreRuntime,
) -> dict[str, object]:
    raw_activity_events = tuple(runtime.activity_console_events)
    activity_events = tuple(runtime.tracked_activity_console_events)
    runtime_probe_events = tuple(runtime.tracked_probe_console_events)
    public_overlap_state = _observe_pre_release_public_overlap(page)
    pre_release_restore_message = _observe_restore_message(
        tracker_page,
        timeout_ms=PRE_RELEASE_RESTORE_MESSAGE_TIMEOUT_MS,
    )

    overlap_proof_sources: list[str] = []
    if activity_events:
        overlap_proof_sources.append(
            "tracked File System Access activity on the saved local workspace lineage",
        )
    if runtime_probe_events:
        overlap_proof_sources.append(
            "tracked TS-893 runtime probe from a blocked saved-workspace handle operation",
        )
    if pre_release_restore_message:
        overlap_proof_sources.append(
            f"visible restore skip banner while blocked: {pre_release_restore_message}",
        )
    if public_overlap_state.get("public_overlap_observed") is True:
        public_overlap_reason = public_overlap_state.get("public_overlap_reason")
        overlap_proof_sources.append(
            "public pre-release non-restored state"
            + (
                f": {public_overlap_reason}"
                if isinstance(public_overlap_reason, str) and public_overlap_reason
                else ""
            ),
        )

    return {
        "pre_release_activity_captured": bool(activity_events),
        "pre_release_all_activity_events": [
            _console_event_payload(event) for event in raw_activity_events
        ],
        "pre_release_activity_events": [
            _console_event_payload(event) for event in activity_events
        ],
        "pre_release_activity": _console_event_payload(
            activity_events[-1] if activity_events else None,
        ),
        "pre_release_runtime_probe_captured": bool(runtime_probe_events),
        "pre_release_runtime_probe": _console_event_payload(
            runtime_probe_events[-1] if runtime_probe_events else None,
        ),
        "pre_release_runtime_probe_events": [
            _console_event_payload(event) for event in runtime_probe_events
        ],
        "pre_release_restore_message": pre_release_restore_message,
        "pre_release_public_overlap_observed": bool(
            public_overlap_state.get("public_overlap_observed"),
        ),
        "pre_release_public_overlap_state": public_overlap_state,
        "overlap_proof_sources": overlap_proof_sources,
    }


def _console_event_payload(event: object) -> dict[str, object] | None:
    if event is None:
        return None
    level = getattr(event, "level", None)
    text = getattr(event, "text", None)
    payload: dict[str, object] = {
        "level": None if level is None else str(level),
        "text": None if text is None else str(text),
    }
    if isinstance(text, str):
        for prefix in (
            Ts723WorkspaceRestoreRuntime.RUNTIME_ACTIVITY_PREFIX,
            Ts723WorkspaceRestoreRuntime.RUNTIME_PROBE_PREFIX,
        ):
            if not text.startswith(prefix):
                continue
            payload["prefix"] = prefix
            raw_details = text[len(prefix) :].strip()
            if not raw_details:
                break
            try:
                parsed_details = json.loads(raw_details)
            except json.JSONDecodeError:
                payload["details_parse_error"] = raw_details
                break
            payload["details"] = parsed_details
            if isinstance(parsed_details, dict):
                for key in ("tracked", "handleName", "handleKind", "handleLineage", "method", "stage", "error"):
                    if key in parsed_details:
                        payload[key] = parsed_details[key]
            break
    return payload


def _annotated_step_line(result: dict[str, object], step_number: int, action: str) -> str:
    step = _step_by_number(result, step_number)
    status = "PASSED ✅" if step and step.get("status") == "passed" else "FAILED ❌"
    observed = step.get("observed") if step else "<missing>"
    return f"{step_number}. {action}\n   - Result: {status}\n   - Actual: {observed}"


def _step_by_number(result: dict[str, object], step_number: int) -> dict[str, object] | None:
    for step in result.get("steps", []):
        if isinstance(step, dict) and step.get("step") == step_number:
            return step
    return None


def _step_passed(result: dict[str, object], step_number: int) -> bool:
    step = _step_by_number(result, step_number)
    return step is not None and step.get("status") == "passed"


def _failed_step_number(result: dict[str, object]) -> int | None:
    for step in result.get("steps", []):
        if isinstance(step, dict) and step.get("status") == "failed":
            step_number = step.get("step")
            if isinstance(step_number, int):
                return step_number
    return None


def _bug_title(result: dict[str, object]) -> str:
    if _failed_due_to_release_error(result):
        return (
            f"{TICKET_KEY} - Test automation could not release the transient busy "
            "workspace during startup"
        )
    if _failed_due_to_missing_saved_handle_revalidation_capability(result):
        return (
            f"{TICKET_KEY} - Deployed web startup never revalidates the saved "
            "local workspace handle"
        )
    return (
        f"{TICKET_KEY} - Startup retry does not restore the local workspace "
        "after transient busy access clears"
    )


def _bug_expected_result(result: dict[str, object]) -> str:
    if _failed_due_to_release_error(result):
        return (
            "The automation should release the temporary busy-state simulation so "
            "startup can continue into the post-release restore assertions."
        )
    if _failed_due_to_missing_saved_handle_revalidation_capability(result):
        return (
            "On the deployed web surface, startup should actually revalidate the "
            "saved local workspace handle while the repository is temporarily "
            "busy, then restore the workspace as the selected `Local Git` row "
            "once access becomes available again."
        )
    return EXPECTED_RESULT


def _bug_actual_result(result: dict[str, object]) -> str:
    if _failed_due_to_release_error(result):
        return (
            "The automation could not restore access to the prepared local "
            "workspace during the simulated transient busy window, so the live "
            "post-release restore assertions did not run."
        )
    if _failed_due_to_missing_saved_handle_revalidation_capability(result):
        return (
            "While the workspace remained blocked and after access was released, "
            "the deployed app never invoked any File System Access handle methods "
            "for the saved local workspace. The trigger and switcher already "
            "showed the final `Local Git` state before release, so the transient "
            "busy startup-revalidation path never ran on this surface."
        )
    if not _step_passed(result, 4):
        return (
            "After the temporary busy state was released and the test waited "
            f"{TRIGGER_WAIT_SECONDS} seconds for startup recovery, the header trigger "
            "still showed the hosted fallback and the prepared local workspace did "
            "not become the selected `Local Git` workspace."
        )
    return "The active local workspace restored correctly."


def _bug_missing_capability(result: dict[str, object]) -> str:
    if _failed_due_to_release_error(result):
        return (
            "The transient busy-state simulation could not be released by the test "
            "automation."
        )
    if _failed_due_to_missing_saved_handle_revalidation_capability(result):
        return (
            "The deployed web build never executes saved local workspace handle "
            "revalidation during startup. Repository evidence: "
            f"`{WEB_LOCAL_GIT_RUNTIME_STUB_PATH.relative_to(REPO_ROOT)}` throws "
            f"`UnsupportedError('{WEB_LOCAL_GIT_RUNTIME_STUB_MESSAGE}')` for local "
            "Git in web builds, so TS-893 cannot exercise the transient busy "
            "startup restore path on that surface."
        )
    return (
        "Startup retry did not restore the prepared local workspace as the active "
        "`Local Git` selection after transient busy access cleared."
    )


def _failed_due_to_missing_saved_handle_revalidation_capability(
    result: dict[str, object],
) -> bool:
    return (
        result.get("failure_reason")
        == "missing_saved_handle_revalidation_capability"
        and _step_passed(result, 4)
    )


def _observe_pre_release_public_overlap(
    page: LiveWorkspaceSwitcherPage,
) -> dict[str, object]:
    trigger = page.observe_trigger(timeout_ms=5_000)
    switcher: WorkspaceSwitcherObservation | None = None
    local_row: WorkspaceSwitcherRowObservation | None = None
    selected_row: WorkspaceSwitcherRowObservation | None = None
    switcher_error: str | None = None
    switcher_opened = False
    try:
        switcher = page.open_and_observe(timeout_ms=5_000)
        switcher_opened = True
        local_row = _find_named_local_row(switcher)
        selected_row = _find_selected_row(switcher)
    except Exception as error:
        switcher_error = f"{type(error).__name__}: {error}"
    finally:
        if switcher_opened:
            try:
                page.wait_for_escape_dismissal(timeout_ms=5_000)
            except Exception as error:
                dismiss_error = f"{type(error).__name__}: {error}"
                switcher_error = (
                    f"{switcher_error}; dismiss_error={dismiss_error}"
                    if switcher_error
                    else f"dismiss_error={dismiss_error}"
                )
    public_overlap_reason = _pre_release_public_overlap_reason(
        trigger=trigger,
        local_row=local_row,
        selected_row=selected_row,
    )
    return {
        "public_overlap_observed": public_overlap_reason is not None,
        "public_overlap_reason": public_overlap_reason,
        "trigger": _trigger_payload(trigger),
        "switcher": _switcher_payload(switcher) if switcher is not None else None,
        "local_row": _row_payload(local_row),
        "selected_row": _row_payload(selected_row),
        "switcher_error": switcher_error,
    }


def _pre_release_public_overlap_reason(
    *,
    trigger: WorkspaceSwitcherTriggerObservation,
    local_row: WorkspaceSwitcherRowObservation | None,
    selected_row: WorkspaceSwitcherRowObservation | None,
) -> str | None:
    if trigger.display_name == HOSTED_DISPLAY_NAME or trigger.workspace_type == "Hosted":
        return "header trigger showed the hosted fallback while the local workspace was blocked"
    if local_row is not None and (
        local_row.state_label != "Local Git" or "Local Unavailable" in local_row.visible_text
    ):
        return (
            "workspace switcher showed the saved local workspace in a non-restored "
            f"state while blocked: {local_row.state_label!r}"
        )
    if selected_row is not None and (
        selected_row.display_name != LOCAL_DISPLAY_NAME
        or selected_row.target_type_label != "Local"
    ):
        return "workspace switcher selected a non-local or hosted workspace while the local workspace was blocked"
    return None


def _trigger_payload(observation: WorkspaceSwitcherTriggerObservation) -> dict[str, object]:
    return {
        "semantic_label": observation.semantic_label,
        "visible_text": observation.visible_text,
        "raw_text_lines": list(observation.raw_text_lines),
        "display_name": observation.display_name,
        "workspace_type": observation.workspace_type,
        "state_label": observation.state_label,
        "top_button_labels": list(observation.top_button_labels),
    }


def _row_payload(
    observation: WorkspaceSwitcherRowObservation | None,
) -> dict[str, object] | None:
    if observation is None:
        return None
    return {
        "display_name": observation.display_name,
        "target_type_label": observation.target_type_label,
        "state_label": observation.state_label,
        "detail_text": observation.detail_text,
        "visible_text": observation.visible_text,
        "selected": observation.selected,
        "semantics_label": observation.semantics_label,
        "icon_accessibility_label": observation.icon_accessibility_label,
        "action_labels": list(observation.action_labels),
        "button_labels": list(observation.button_labels),
    }


def _switcher_payload(observation: WorkspaceSwitcherObservation) -> dict[str, object]:
    return {
        "body_text": observation.body_text,
        "switcher_text": observation.switcher_text,
        "row_count": observation.row_count,
        "rows": [_row_payload(row) for row in observation.rows],
    }


def _safe_dict_get(value: object, key: str) -> object:
    if isinstance(value, dict):
        return value.get(key)
    return None


if __name__ == "__main__":
    main()
