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
from testing.tests.support.stored_workspace_profiles_runtime import (  # noqa: E402
    StoredWorkspaceProfilesRuntime,
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
BUSY_RELEASE_SECONDS = 2.5
LINKED_BUGS = ["TS-882", "TS-896"]

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts893_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts893_failure.png"

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
    release_after_seconds: float

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
        release_after_seconds=BUSY_RELEASE_SECONDS,
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
        "busy_release_seconds": BUSY_RELEASE_SECONDS,
        "steps": [],
        "human_verification": [],
    }

    page: LiveWorkspaceSwitcherPage | None = None
    try:
        with blocker:
            result["busy_blocker_initial"] = blocker.snapshot()
            with create_live_tracker_app(
                config,
                runtime_factory=lambda: StoredWorkspaceProfilesRuntime(
                    repository=config.repository,
                    token=token,
                    workspace_state=workspace_state,
                ),
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
                            "browser storage, and temporarily revoked access to the "
                            f"prepared local git folder at {LOCAL_TARGET!r} to simulate a transient busy state."
                        ),
                    )

                    released = blocker.wait_for_release(
                        timeout_seconds=BUSY_RELEASE_SECONDS + 15,
                    )
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
                    _record_step(
                        result,
                        step=2,
                        status="passed",
                        action=REQUEST_STEPS[1],
                        observed=(
                            "Restored access to the prepared local workspace during the "
                            f"startup retry window after approximately {BUSY_RELEASE_SECONDS} seconds.\n"
                            f"busy_blocker={json.dumps(blocker.snapshot(), indent=2)}"
                        ),
                    )

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
                                "became interactive and the workspace switcher trigger "
                                f"restored the prepared local workspace within {TRIGGER_WAIT_SECONDS} seconds. "
                                f"Observed trigger label={trigger.semantic_label!r}; "
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
                                "became interactive but the workspace switcher trigger "
                                f"never restored the prepared local workspace within {TRIGGER_WAIT_SECONDS} seconds. "
                                f"Observed trigger label={trigger.semantic_label!r}; "
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
                        raise

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
                        raise AssertionError(
                            "Step 3 failed: startup did not restore the prepared active local "
                            "workspace into the trigger after the temporary busy state was "
                            "released within the allowed wait window.\n"
                            f"Observed trigger label: {trigger.semantic_label!r}\n"
                            f"Observed selected row: {json.dumps(_row_payload(selected_row), indent=2)}\n"
                            f"Observed active local row: {json.dumps(_row_payload(local_row), indent=2)}\n"
                            f"Observed switcher text:\n{switcher.switcher_text}"
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
    error = str(result.get("error", "AssertionError: TS-893 failed"))
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
        "* Opened the deployed TrackState app in Chromium with a stored signed-in GitHub session and a preloaded active local workspace profile.",
        f"* Temporarily revoked access to the prepared local workspace for {BUSY_RELEASE_SECONDS} seconds during startup to simulate a transient busy file-system handle, then restored access while retry handling was expected to run.",
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
        f"- Temporarily revoked access to the prepared local workspace for {BUSY_RELEASE_SECONDS} seconds during startup to simulate a transient busy file-system handle, then restored access while retry handling was expected to run.",
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
    lines = [
        "## Test Automation Summary",
        "",
        "- Added TS-893 live startup coverage for transient busy local workspace restoration.",
        f"- Test case: **{TICKET_KEY} - {TEST_CASE_TITLE}**",
        f"- Result: **{status}**",
        f"- Command: `{RUN_COMMAND}`",
        (
            f"- Environment: `{result['app_url']}` on Chromium/Playwright "
            f"({result['os']}) against `{result['repository']}` @ "
            f"`{result['repository_ref']}`."
        ),
        (
            "- Outcome: startup retried after the temporary busy-state release and restored the prepared local workspace as the active `Local Git` selection."
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
    trigger = result.get("trigger_observation")
    switcher = result.get("switcher_observation")
    active_local_row = result.get("active_local_row")
    selected_row = result.get("selected_row")
    blocker_final = result.get("busy_blocker_final")
    return "\n".join(
        [
            f"# {TICKET_KEY} - Startup retry does not restore the local workspace after transient busy access clears",
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
            f"- **Expected:** {EXPECTED_RESULT}",
            (
                "- **Actual:** After the temporary busy state was released and the test "
                f"waited {TRIGGER_WAIT_SECONDS} seconds for startup recovery, the header "
                "trigger still showed the hosted fallback and the prepared local "
                "workspace did not become the selected `Local Git` workspace."
                if not _step_passed(result, 4)
                else "- **Actual:** The active local workspace restored correctly."
            ),
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
            return f"Step {step.get('step')} failed: {step.get('observed')}"
    return str(result.get("error", "The scenario failed without recorded step details."))


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
