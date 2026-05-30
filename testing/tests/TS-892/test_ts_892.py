from __future__ import annotations

from dataclasses import dataclass
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
    WorkspaceSwitcherTriggerObservation,
)
from testing.components.pages.trackstate_tracker_page import TrackStateTrackerPage  # noqa: E402
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.interfaces.web_app_session import WebAppTimeoutError  # noqa: E402
from testing.core.utils.polling import poll_until  # noqa: E402
from testing.tests.support.ts723_workspace_restore_runtime import (  # noqa: E402
    Ts723WorkspaceRestoreRuntime,
    WorkspaceRestoreConsoleEvent,
)

TICKET_KEY = "TS-892"
TEST_CASE_TITLE = (
    "Startup with permanent file system error — local workspace remains "
    "Local Unavailable"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-892/test_ts_892.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
DEFAULT_BRANCH = "main"
LOCAL_TARGET = "/tmp/trackstate-ts892-workspace"
LOCAL_DISPLAY_NAME = "Deleted local workspace"
HOSTED_DISPLAY_NAME = "Hosted setup workspace"
STARTUP_RETRY_WAIT_SECONDS = 15
STARTUP_SURFACE_WAIT_SECONDS = 120
LINKED_BUGS = ["TS-882", "TS-894", "TS-896"]

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts892_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts892_failure.png"

REQUEST_STEPS = [
    "Restart the application or refresh the browser to trigger the initialization logic.",
    "Wait for the startup sequence to complete and the retry mechanism to exhaust.",
    "Open the Workspace switcher from the application header.",
    "Inspect the status label for the local workspace and the active workspace selection.",
]
EXPECTED_RESULT = (
    "The local workspace is marked as 'Local Unavailable'. The application does "
    "not attempt to restore it to 'Local Git' after retries fail, and it does "
    "not incorrectly default to selecting the 'Hosted setup workspace' if the "
    "local configuration is still present."
)


@dataclass(frozen=True)
class StartupWorkspaceSurfaceObservation:
    kind: str
    body_text: str
    trigger: WorkspaceSwitcherTriggerObservation | None = None
    switcher: WorkspaceSwitcherObservation | None = None


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-892 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
        )

    workspace_state = _workspace_state(service.repository)
    prepared_local_workspace = _prepare_and_delete_local_workspace_repository()
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
        "startup_retry_wait_seconds": STARTUP_RETRY_WAIT_SECONDS,
        "preloaded_workspace_state": workspace_state,
        "prepared_local_workspace": prepared_local_workspace,
        "steps": [],
        "human_verification": [],
    }

    runtime = Ts723WorkspaceRestoreRuntime(
        repository=config.repository,
        token=token,
        workspace_state=workspace_state,
    )
    page: LiveWorkspaceSwitcherPage | None = None

    try:
        with runtime as session:
            tracker_page = TrackStateTrackerPage(session, config.app_url)
            page = LiveWorkspaceSwitcherPage(tracker_page)
            try:
                tracker_page.open_entrypoint()
                page.set_viewport(**DESKTOP_VIEWPORT)
                startup_surface = _wait_for_startup_workspace_surface(
                    page=page,
                    tracker_page=tracker_page,
                    timeout_seconds=STARTUP_SURFACE_WAIT_SECONDS,
                )
                result["runtime_state"] = startup_surface.kind
                result["runtime_body_text"] = startup_surface.body_text
                result["startup_surface"] = _startup_surface_payload(startup_surface)
                if startup_surface.kind == "data-load-failed":
                    raise AssertionError(
                        "Step 1 failed: the deployed app reached a visible TrackState data "
                        "load error instead of the startup workspace recovery surface for "
                        "the permanent local-workspace failure scenario.\n"
                        f"Observed body text:\n{startup_surface.body_text}",
                    )
                try:
                    page.dismiss_connection_banner()
                except (AssertionError, WebAppTimeoutError):
                    pass
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=REQUEST_STEPS[0],
                    observed=(
                        "Opened the deployed app in Chromium with a saved active local "
                        "workspace profile, then reproduced permanent access loss by "
                        f"deleting the prepared repository at {LOCAL_TARGET!r} before startup. "
                        "The runtime reached the workspace recovery UI rather than timing "
                        f"out. initial_surface_kind={startup_surface.kind!r}"
                    ),
                )

                surface_samples: list[dict[str, object]] = []

                def sample_surface() -> StartupWorkspaceSurfaceObservation:
                    surface = _observe_startup_workspace_surface(
                        page=page,
                        tracker_page=tracker_page,
                        timeout_ms=10_000,
                    )
                    surface_samples.append(_startup_surface_payload(surface))
                    return surface

                _, final_surface = poll_until(
                    probe=sample_surface,
                    is_satisfied=lambda _: False,
                    timeout_seconds=STARTUP_RETRY_WAIT_SECONDS,
                    interval_seconds=5,
                )
                final_trigger = final_surface.trigger
                result["surface_samples"] = surface_samples
                result["final_surface_observation"] = _startup_surface_payload(final_surface)
                result["final_trigger_observation"] = (
                    _trigger_payload(final_trigger) if final_trigger is not None else None
                )
                restore_message = _observe_restore_message(tracker_page)
                if restore_message is not None:
                    result["restore_message"] = restore_message
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=REQUEST_STEPS[1],
                    observed=(
                        "Waited beyond the startup local-workspace revalidation window "
                        f"({STARTUP_RETRY_WAIT_SECONDS} seconds) before asserting the final state. "
                        f"Observed final surface kind={final_surface.kind!r}"
                        + (
                            f"; final_trigger_label={final_trigger.semantic_label!r}"
                            if final_trigger is not None
                            else ""
                        )
                        + (
                            f"; restore_message={restore_message!r}"
                            if restore_message
                            else ""
                        )
                    ),
                )

                if final_surface.switcher is not None:
                    switcher = final_surface.switcher
                    step_3_observed = (
                        "The workspace recovery surface was already open after the startup "
                        "wait window, so the visible Workspace switcher was inspected "
                        "directly.\n"
                        f"row_count={switcher.row_count}; "
                        f"switcher_text={switcher.switcher_text!r}"
                    )
                else:
                    switcher = page.open_and_observe(timeout_ms=20_000)
                    step_3_observed = (
                        "Opened Workspace switcher from the header after the startup wait "
                        "window.\n"
                        f"row_count={switcher.row_count}; "
                        f"switcher_text={switcher.switcher_text!r}"
                    )
                result["switcher_observation"] = _switcher_payload(switcher)
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action=REQUEST_STEPS[2],
                    observed=step_3_observed,
                )

                local_row = _find_named_local_row(switcher)
                selected_row = _find_selected_row(switcher)
                if selected_row is None and final_trigger is not None:
                    selected_row = _selected_row_from_trigger(final_trigger)
                result["local_row"] = _row_payload(local_row) if local_row else None
                result["selected_row"] = (
                    _row_payload(selected_row) if selected_row is not None else None
                )
                result["persisted_workspace_state"] = _decode_workspace_state(
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
                        "Viewed the header workspace switcher trigger after waiting for "
                        "startup retries to finish."
                    ),
                    observed=(
                        (
                            f"trigger_label={final_trigger.semantic_label!r}; "
                            f"trigger_text={final_trigger.visible_text!r}"
                        )
                        if final_trigger is not None
                        else "The workspace recovery surface remained open, so no separate "
                        "header trigger label was visible before inspection."
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Opened Workspace switcher and visually inspected the deleted local "
                        "workspace row plus whichever workspace remained selected."
                    ),
                    observed=(
                        f"selected_row={json.dumps(_row_payload(selected_row), ensure_ascii=True)}; "
                        f"local_row={json.dumps(_row_payload(local_row), ensure_ascii=True)}"
                    ),
                )

                try:
                    _assert_permanent_error_state(
                        trigger=final_trigger,
                        switcher=switcher,
                        local_row=local_row,
                        selected_row=selected_row,
                        persisted_workspace_state=result["persisted_workspace_state"],  # type: ignore[arg-type]
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
                        "The deleted local workspace row remained visible as `Local "
                        "Unavailable`, it did not recover to `Local Git`, and the app did "
                        "not keep the hosted workspace selected as the active fallback.\n"
                        f"selected_row={json.dumps(_row_payload(selected_row), indent=2)}"
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
        result["error"] = f"AssertionError: {error}"
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


def _prepare_and_delete_local_workspace_repository() -> dict[str, object]:
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
    marker_path = local_path / ".trackstate-ts892-precondition.txt"
    marker_path.write_text(
        "Prepared for TS-892 permanent local-workspace failure validation.\n",
        encoding="utf-8",
    )
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
            "user.name=TS-892 Automation",
            "-c",
            "user.email=ts892@example.com",
            "commit",
            "--allow-empty",
            "-m",
            "Prepare TS-892 local workspace",
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
    shutil.rmtree(local_path)
    return {
        "path": str(local_path),
        "head_before_delete": head.stdout.strip(),
        "marker_path": str(marker_path),
        "deleted_before_startup": True,
    }


def _observe_restore_message(tracker_page: TrackStateTrackerPage) -> str | None:
    try:
        observation = tracker_page.observe_workspace_restore_message(
            workspace_name=LOCAL_DISPLAY_NAME,
            timeout_ms=5_000,
        )
    except (AssertionError, WebAppTimeoutError):
        return None
    return observation.message_text


def _wait_for_startup_workspace_surface(
    *,
    page: LiveWorkspaceSwitcherPage,
    tracker_page: TrackStateTrackerPage,
    timeout_seconds: float,
) -> StartupWorkspaceSurfaceObservation:
    observed, surface = poll_until(
        probe=lambda: _observe_startup_workspace_surface(
            page=page,
            tracker_page=tracker_page,
            timeout_ms=1_000,
        ),
        is_satisfied=lambda candidate: candidate.kind != "loading",
        timeout_seconds=timeout_seconds,
        interval_seconds=1,
    )
    if not observed:
        raise AssertionError(
            "Step 1 failed: the deployed app never reached a visible workspace "
            "recovery surface for the permanent local-workspace failure scenario.\n"
            f"Observed body text:\n{tracker_page.body_text()}",
        )
    return surface


def _observe_startup_workspace_surface(
    *,
    page: LiveWorkspaceSwitcherPage,
    tracker_page: TrackStateTrackerPage,
    timeout_ms: int,
) -> StartupWorkspaceSurfaceObservation:
    body_text = tracker_page.body_text()
    if any(
        error_text in body_text
        for error_text in TrackStateTrackerPage.LOAD_ERROR_TEXT_VARIANTS
    ):
        return StartupWorkspaceSurfaceObservation(
            kind="data-load-failed",
            body_text=body_text,
        )
    try:
        trigger = page.observe_trigger(timeout_ms=timeout_ms)
        return StartupWorkspaceSurfaceObservation(
            kind="trigger",
            body_text=tracker_page.body_text(),
            trigger=trigger,
        )
    except (AssertionError, WebAppTimeoutError):
        pass
    try:
        switcher = page.observe_open_switcher(timeout_ms=timeout_ms)
        return StartupWorkspaceSurfaceObservation(
            kind="switcher",
            body_text=tracker_page.body_text(),
            switcher=switcher,
        )
    except (AssertionError, WebAppTimeoutError):
        return StartupWorkspaceSurfaceObservation(kind="loading", body_text=body_text)


def _find_named_local_row(
    switcher: WorkspaceSwitcherObservation,
) -> WorkspaceSwitcherRowObservation | None:
    for row in switcher.rows:
        if row.target_type_label == "Local" and LOCAL_TARGET in row.detail_text:
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
        button_labels=(),
    )


def _fallback_local_row_from_switcher_text(
    switcher_text: str,
) -> WorkspaceSwitcherRowObservation | None:
    normalized = " ".join(switcher_text.split())
    detail_text = f"{LOCAL_TARGET} • Branch: {DEFAULT_BRANCH}"
    match = re.search(
        rf"{re.escape(LOCAL_DISPLAY_NAME)}, Local, (?P<state>[^,]+), "
        rf"{re.escape(detail_text)}(?P<tail>.*?)(?: Hosted setup workspace| Add workspace|$)",
        normalized,
    )
    if match is None:
        return None
    state_label = match.group("state").strip() or None
    action_tail = match.group("tail").strip()
    action_match = re.search(
        r"(Active|Retry: .*?|Re-authenticate: .*?|Open: .*?) Delete:",
        action_tail,
    )
    action_label = action_match.group(1).strip() if action_match is not None else None
    if action_label is None:
        return None
    selected = action_label == "Active"
    button_labels = ("Delete",) if selected else (action_label, "Delete")
    return WorkspaceSwitcherRowObservation(
        display_name=LOCAL_DISPLAY_NAME,
        target_type_label="Local",
        state_label=state_label,
        detail_text=detail_text,
        visible_text=match.group(0).strip(),
        selected=selected,
        semantics_label=None,
        icon_accessibility_label=None,
        action_labels=(action_label,),
        button_labels=button_labels,
    )


def _assert_permanent_error_state(
    *,
    trigger: WorkspaceSwitcherTriggerObservation | None,
    switcher: WorkspaceSwitcherObservation,
    local_row: WorkspaceSwitcherRowObservation | None,
    selected_row: WorkspaceSwitcherRowObservation | None,
    persisted_workspace_state: dict[str, object],
) -> None:
    if local_row is None:
        raise AssertionError(
            "Step 4 failed: Workspace switcher did not show the deleted local workspace row.\n"
            f"Observed trigger label: {trigger.semantic_label!r}\n"
            if trigger is not None
            else "Step 4 failed: Workspace switcher did not show the deleted local workspace row.\n"
            + "Observed trigger label: <workspace recovery surface remained open>\n"
            + f"Observed switcher text:\n{switcher.switcher_text}"
        )
    failures: list[str] = []
    if local_row.state_label != "Unavailable" and "Local Unavailable" not in local_row.visible_text:
        failures.append(
            "the deleted local workspace row did not remain in the `Local Unavailable` "
            "state after startup retries were exhausted.",
        )
    if local_row.state_label == "Local Git" or "Local Git" in local_row.visible_text:
        failures.append(
            "the deleted local workspace row recovered to `Local Git` instead of "
            "remaining unavailable.",
        )
    if selected_row is not None and _is_hosted_workspace_selection(selected_row):
        hosted_name = _workspace_display_name(selected_row)
        failures.append(
            "the application kept "
            f"`{hosted_name}` selected as the active hosted workspace even though "
            "the saved deleted local workspace row was still present.",
        )
    if trigger is not None and (
        trigger.display_name == HOSTED_DISPLAY_NAME or trigger.workspace_type == "Hosted"
    ):
        hosted_name = trigger.display_name or HOSTED_DISPLAY_NAME
        failures.append(
            "the header trigger still defaulted to the hosted workspace "
            f"`{hosted_name}` after the permanent local failure.",
        )
    if failures:
        details = [
            f"Step 4 failed: {failures[0]}",
            *[f"Also observed: {failure}" for failure in failures[1:]],
            (
                f"Observed trigger label: {trigger.semantic_label!r}"
                if trigger is not None
                else "Observed trigger label: <workspace recovery surface remained open>"
            ),
            f"Observed selected row: {json.dumps(_row_payload(selected_row), indent=2)}",
            f"Observed local row: {json.dumps(_row_payload(local_row), indent=2)}",
            f"Observed activeWorkspaceId: {persisted_workspace_state.get('activeWorkspaceId')!r}",
        ]
        raise AssertionError("\n".join(details))


def _startup_surface_payload(
    surface: StartupWorkspaceSurfaceObservation,
) -> dict[str, object]:
    return {
        "kind": surface.kind,
        "body_text": surface.body_text,
        "trigger": (
            _trigger_payload(surface.trigger) if surface.trigger is not None else None
        ),
        "switcher": (
            _switcher_payload(surface.switcher) if surface.switcher is not None else None
        ),
    }


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
    error = str(result.get("error", "AssertionError: TS-892 failed"))
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
        "* Opened the deployed TrackState app in Chromium with a preloaded active local workspace profile and one hosted workspace.",
        "* Reproduced a permanent local access failure by preparing the saved local repository and deleting it before startup.",
        f"* Waited {STARTUP_RETRY_WAIT_SECONDS} seconds after launch so startup revalidation retries had time to exhaust before asserting.",
        "* Opened *Workspace switcher* and inspected both the deleted local workspace row state and the active workspace selection.",
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
    if result.get("restore_message"):
        lines.extend(
            [
                "",
                "h4. Visible restore message",
                str(result["restore_message"]),
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
        "- Opened the deployed TrackState app in Chromium with a preloaded active local workspace profile and one hosted workspace.",
        "- Reproduced a permanent local access failure by preparing the saved local repository and deleting it before startup.",
        f"- Waited {STARTUP_RETRY_WAIT_SECONDS} seconds after launch so startup revalidation retries had time to exhaust before asserting.",
        "- Opened **Workspace switcher** and inspected both the deleted local workspace row state and the active workspace selection.",
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
    if result.get("restore_message"):
        lines.extend(
            [
                "",
                "## Visible restore message",
                f"`{result['restore_message']}`",
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
        "- Added TS-892 live startup coverage for a permanently unavailable local workspace.",
        f"- Test case: **{TICKET_KEY} - {TEST_CASE_TITLE}**",
        f"- Result: **{status}**",
        f"- Command: `{RUN_COMMAND}`",
        (
            f"- Environment: `{result['app_url']}` on Chromium/Playwright "
            f"({result['os']}) against `{result['repository']}` @ "
            f"`{result['repository_ref']}`."
        ),
        (
            "- Outcome: the deleted local workspace stayed unavailable without switching the active selection to hosted."
            if passed
            else f"- Outcome: {_failed_step_summary(result)}"
        ),
    ]
    if result.get("screenshot"):
        lines.append(f"- Screenshot: `{result['screenshot']}`")
    return "\n".join(lines) + "\n"


def _bug_description(result: dict[str, object]) -> str:
    actual_summary = _actual_behavior_summary(result)
    lines = [
        f"# {TICKET_KEY} - {actual_summary}",
        "",
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
        f"- **Actual:** {_actual_behavior_detail(result)}",
        (
            f"- **Observed trigger:** `{_safe_dict_get(result.get('final_trigger_observation'), 'semantic_label')}`"
        ),
        (
            f"- **Observed selected row:** `{json.dumps(result.get('selected_row'), ensure_ascii=True)}`"
        ),
        (
            f"- **Observed local row:** `{json.dumps(result.get('local_row'), ensure_ascii=True)}`"
        ),
        (
            f"- **Observed persisted workspace state:** `{json.dumps(result.get('persisted_workspace_state'), ensure_ascii=True)}`"
        ),
        "",
        "## Environment details",
        f"- **URL:** {result.get('app_url')}",
        f"- **Repository:** {result.get('repository')} @ {result.get('repository_ref')}",
        f"- **Browser:** {result.get('browser')}",
        f"- **OS:** {result.get('os')}",
        f"- **Viewport:** {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
        f"- **Run command:** {RUN_COMMAND}",
        f"- **Startup wait:** {STARTUP_RETRY_WAIT_SECONDS} seconds",
        f"- **Prepared local workspace:** `{LOCAL_TARGET}` (deleted before startup)",
        "",
        "## Screenshots or logs",
        f"- **Screenshot:** {result.get('screenshot', '<no screenshot recorded>')}",
    ]
    if result.get("restore_message"):
        lines.append(f"- **Visible restore message:** `{result['restore_message']}`")
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
    for step in result.get("steps", []):
        if isinstance(step, dict) and step.get("status") == "failed":
            return (
                f"Step {step.get('step')} failed while attempting to "
                f"{step.get('action')} Observed: {step.get('observed')}"
            )
    return str(result.get("error", "The permanent local-workspace scenario failed."))


def _actual_behavior_summary(result: dict[str, object]) -> str:
    selected_row = result.get("selected_row")
    if isinstance(selected_row, dict) and _is_hosted_workspace_result(selected_row):
        return "Permanent local workspace failure falls back to hosted selection"
    local_row = result.get("local_row")
    if isinstance(local_row, dict):
        state_label = str(local_row.get("state_label") or "").strip()
        if state_label == "Local Git":
            return "Permanent local workspace failure keeps deleted workspace active as Local Git"
        if state_label:
            return (
                "Permanent local workspace failure leaves deleted workspace in "
                f"unexpected state {state_label}"
            )
    return "Permanent local workspace failure does not match the expected unavailable state"


def _actual_behavior_detail(result: dict[str, object]) -> str:
    selected_row = result.get("selected_row")
    if isinstance(selected_row, dict) and _is_hosted_workspace_result(selected_row):
        display_name = _workspace_display_name_from_result(selected_row)
        return (
            f"The application kept hosted workspace `{display_name}` selected as "
            "the active workspace instead of leaving the deleted local workspace "
            "unavailable."
        )
    local_row = result.get("local_row")
    if isinstance(local_row, dict):
        state_label = str(local_row.get("state_label") or "").strip()
        display_name = str(local_row.get("display_name") or "").strip()
        if state_label == "Local Git":
            return (
                f"The deleted local workspace row for `{display_name}` stayed selected and "
                "rendered as `Local Git` instead of `Local Unavailable` after startup "
                "retries were exhausted."
            )
        if state_label:
            return (
                f"The deleted local workspace row for `{display_name}` rendered as "
                f"`{state_label}` instead of `Local Unavailable` after startup retries "
                "were exhausted."
            )
    return str(result.get("error", "The observed behavior did not match the expected unavailable state."))


def _is_hosted_workspace_selection(
    row: WorkspaceSwitcherRowObservation,
) -> bool:
    return row.target_type_label == "Hosted" or row.display_name == HOSTED_DISPLAY_NAME


def _is_hosted_workspace_result(row: dict[str, object]) -> bool:
    return (
        str(row.get("target_type_label") or "").strip() == "Hosted"
        or str(row.get("display_name") or "").strip() == HOSTED_DISPLAY_NAME
    )


def _workspace_display_name(row: WorkspaceSwitcherRowObservation) -> str:
    display_name = (row.display_name or "").strip()
    return display_name or HOSTED_DISPLAY_NAME


def _workspace_display_name_from_result(row: dict[str, object]) -> str:
    display_name = str(row.get("display_name") or "").strip()
    return display_name or HOSTED_DISPLAY_NAME


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
    if result.get("surface_samples"):
        lines.extend(
            [
                "",
                "h4. Surface samples" if jira else "## Surface samples",
                "{code}" if jira else "```json",
                json.dumps(result["surface_samples"], indent=2),
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
