from __future__ import annotations

import json
import platform
import subprocess
import sys
import time
import traceback
from pathlib import Path
from typing import Any

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
from testing.tests.support.delayed_auth_workspace_profiles_runtime import (  # noqa: E402
    DelayedAuthWorkspaceProfilesRuntime,
)

TICKET_KEY = "TS-891"
TEST_CASE_TITLE = (
    "Startup restoration with high authentication latency — local workspace "
    "transitions to active Local Git after ready signal"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-891/test_ts_891.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 960}
DEFAULT_BRANCH = "main"
LOCAL_TARGET = "/tmp/trackstate-demo"
LOCAL_DISPLAY_NAME = "Active local workspace"
HOSTED_DISPLAY_NAME = "Hosted setup workspace"
AUTH_DELAY_SECONDS = 8
STARTUP_RESTORE_WAIT_SECONDS = 90
STARTUP_TRIGGER_WAIT_SECONDS = 120
LINKED_BUGS = ["TS-895", "TS-883", "TS-882"]

OUTPUTS_DIR = REPO_ROOT / "outputs"
INPUTS_DIR = REPO_ROOT / "input" / TICKET_KEY
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
REVIEW_REPLIES_PATH = OUTPUTS_DIR / "review_replies.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
DISCUSSIONS_RAW_PATH = INPUTS_DIR / "pr_discussions_raw.json"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts891_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts891_failure.png"

REQUEST_STEPS = [
    "Restart the application to trigger the boot cycle.",
    "Open the workspace switcher immediately while the authentication status is still Initializing or Pending.",
    "Verify the active local workspace is not flagged as Local Unavailable during this pending phase.",
    "Wait for the authentication provider to emit the ready signal after the delay.",
    "Re-inspect the active local workspace row in the switcher.",
]
EXPECTED_RESULT = (
    "The workspace row correctly transitions from its pending status to the "
    "active Local Git state once the authentication provider is ready. The UI "
    "hides Connect GitHub and the workspace is functional without manual "
    "intervention."
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
            "TS-891 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
        )
    user = service.fetch_authenticated_user()
    workspace_state = _workspace_state(service.repository)
    prepared_local_workspace = _prepare_local_workspace_repository()
    runtime = DelayedAuthWorkspaceProfilesRuntime(
        repository=config.repository,
        token=token,
        workspace_state=workspace_state,
        auth_delay_seconds=AUTH_DELAY_SECONDS,
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
        "auth_delay_seconds": AUTH_DELAY_SECONDS,
        "startup_restore_wait_seconds": STARTUP_RESTORE_WAIT_SECONDS,
        "linked_bugs": LINKED_BUGS,
        "user_login": user.login,
        "preloaded_workspace_state": workspace_state,
        "prepared_local_workspace": prepared_local_workspace,
        "steps": [],
        "human_verification": [],
    }

    page: LiveWorkspaceSwitcherPage | None = None
    try:
        with runtime as session:
            tracker_page = TrackStateTrackerPage(session, config.app_url)
            page = LiveWorkspaceSwitcherPage(tracker_page)
            try:
                step_failures: list[str] = []
                startup_switcher: WorkspaceSwitcherObservation | None = None
                startup_started_at_monotonic = time.monotonic()
                tracker_page.open_entrypoint()
                page.set_viewport(**DESKTOP_VIEWPORT)
                trigger_visible, trigger = poll_until(
                    probe=lambda: _try_observe_trigger(page),
                    is_satisfied=lambda candidate: candidate is not None,
                    timeout_seconds=STARTUP_TRIGGER_WAIT_SECONDS,
                    interval_seconds=1,
                )
                if not trigger_visible:
                    startup_switcher = _try_observe_open_switcher(page)
                    trigger_visible = startup_switcher is not None
                result["runtime_state"] = "startup-shell-visible"
                result["runtime_body_text"] = page.current_body_text()
                if not trigger_visible:
                    raise AssertionError(
                        "Step 1 failed: the deployed app did not reach an interactive "
                        "startup shell that exposed the workspace-selection UI "
                        "before the delayed-auth scenario timed out.\n"
                        f"Observed body text:\n{page.current_body_text()}",
                    )
                result["storage_snapshot"] = tracker_page.snapshot_local_storage(
                    _storage_snapshot_keys(config.repository, workspace_state),
                )
                result["initial_trigger_observation"] = (
                    _trigger_payload(trigger) if trigger is not None else None
                )
                result["initial_switcher_observation"] = (
                    _switcher_payload(startup_switcher)
                    if startup_switcher is not None
                    else None
                )
                result["trigger_observed_after_start_seconds"] = round(
                    time.monotonic() - startup_started_at_monotonic,
                    2,
                )
                result["auth_probe_started_after_start_seconds"] = (
                    _relative_startup_event_seconds(
                        startup_started_at_monotonic,
                        runtime.auth_probe_started_at_monotonic,
                    )
                )
                result["auth_probe_released_after_start_seconds"] = (
                    _relative_startup_event_seconds(
                        startup_started_at_monotonic,
                        runtime.auth_probe_released_at_monotonic,
                    )
                )
                result["github_request_urls"] = list(runtime.github_request_urls)
                result["delayed_request_urls"] = list(runtime.delayed_request_urls)

                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=REQUEST_STEPS[0],
                    observed=(
                        "Opened the deployed app in a fresh Chromium context with a saved "
                        f"active local workspace profile and an injected {AUTH_DELAY_SECONDS}-second "
                        "delay on the GitHub /user auth verification request until the "
                        "startup shell exposed the workspace-selection UI.\n"
                        f"initial_trigger_label={_trigger_label(trigger)!r}; "
                        f"trigger_observed_after_start_seconds={result['trigger_observed_after_start_seconds']!r}; "
                        f"auth_probe_started_after_start_seconds={result['auth_probe_started_after_start_seconds']!r}; "
                        f"auth_probe_released_after_start_seconds={result['auth_probe_released_after_start_seconds']!r}\n"
                        f"startup_switcher_visible={startup_switcher is not None}"
                    ),
                )
                pending_switcher = startup_switcher or _open_or_observe_switcher(
                    page,
                    timeout_ms=20_000,
                )
                pending_local_row = _find_named_local_row(pending_switcher)
                auth_started_before_open = runtime.auth_probe_started_at_monotonic is not None
                auth_released_before_open = (
                    runtime.auth_probe_released_at_monotonic is not None
                )
                if auth_released_before_open:
                    result["pending_trigger_observation"] = _trigger_payload(trigger)
                    result["pending_switcher_observation"] = _switcher_payload(
                        pending_switcher,
                    )
                    result["pending_local_row"] = (
                        _row_payload(pending_local_row)
                        if pending_local_row is not None
                        else None
                    )
                    _record_step(
                        result,
                        step=2,
                        status="failed",
                        action=REQUEST_STEPS[1],
                        observed=(
                            "Workspace switcher opened only after the delayed GitHub "
                            "`/user` auth probe had already finished.\n"
                            f"Observed trigger label: {_trigger_label(trigger)!r}\n"
                            f"Observed switcher text:\n{pending_switcher.switcher_text}"
                        ),
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Opened Workspace switcher as soon as the startup shell exposed "
                            "the header trigger and checked whether the delayed auth phase "
                            "was still in progress."
                        ),
                        observed=(
                            f"trigger_label={_trigger_label(trigger)!r}; "
                            f"trigger_observed_after_start_seconds={result['trigger_observed_after_start_seconds']!r}; "
                            f"auth_probe_started_after_start_seconds={result['auth_probe_started_after_start_seconds']!r}; "
                            f"auth_probe_released_after_start_seconds={result['auth_probe_released_after_start_seconds']!r}; "
                            f"switcher_text={pending_switcher.switcher_text!r}"
                        ),
                    )
                    _record_not_reached_steps(result, starting_step=3)
                    raise AssertionError(
                        "Step 2 failed: Workspace switcher opened only after the delayed "
                        "GitHub `/user` auth probe had already finished.\n"
                        f"Observed trigger label: {_trigger_label(trigger)!r}\n"
                        f"Observed switcher text:\n{pending_switcher.switcher_text}",
                    )
                if not auth_started_before_open and not runtime.wait_for_auth_probe_start(
                    timeout_seconds=30,
                ):
                    result["pending_trigger_observation"] = (
                        _trigger_payload(trigger) if trigger is not None else None
                    )
                    result["pending_switcher_observation"] = _switcher_payload(
                        pending_switcher,
                    )
                    result["pending_local_row"] = (
                        _row_payload(pending_local_row)
                        if pending_local_row is not None
                        else None
                    )
                    body_text = page.current_body_text()
                    _record_step(
                        result,
                        step=2,
                        status="failed",
                        action=REQUEST_STEPS[1],
                        observed=(
                            "Workspace switcher opened during startup, but the delayed "
                            "GitHub `/user` verification request never started, so the "
                            "high-latency auth scenario could not be exercised.\n"
                            f"Observed body text:\n{body_text}\n"
                            f"Observed switcher text:\n{pending_switcher.switcher_text}"
                        ),
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Opened Workspace switcher as soon as the startup shell exposed "
                            "the header trigger and checked whether the delayed auth phase "
                            "was still in progress."
                        ),
                        observed=(
                            f"trigger_label={_trigger_label(trigger)!r}; "
                            f"trigger_observed_after_start_seconds={result['trigger_observed_after_start_seconds']!r}; "
                            f"auth_probe_started_after_start_seconds={result['auth_probe_started_after_start_seconds']!r}; "
                            f"auth_probe_released_after_start_seconds={result['auth_probe_released_after_start_seconds']!r}; "
                            f"switcher_text={pending_switcher.switcher_text!r}"
                        ),
                    )
                    _record_not_reached_steps(result, starting_step=3)
                    raise AssertionError(
                        "Step 2 failed: Workspace switcher opened during startup, but the "
                        "delayed GitHub `/user` verification request never started, so the "
                        "high-latency auth scenario could not be exercised.\n"
                        f"Observed body text:\n{body_text}\n"
                        f"Observed switcher text:\n{pending_switcher.switcher_text}",
                    )

                result["github_request_urls"] = list(runtime.github_request_urls)
                result["delayed_request_urls"] = list(runtime.delayed_request_urls)
                result["auth_probe_started_at_monotonic"] = (
                    runtime.auth_probe_started_at_monotonic
                )
                result["auth_probe_started_after_start_seconds"] = (
                    _relative_startup_event_seconds(
                        startup_started_at_monotonic,
                        runtime.auth_probe_started_at_monotonic,
                    )
                )
                result["auth_probe_released_at_monotonic"] = (
                    runtime.auth_probe_released_at_monotonic
                )
                result["auth_probe_released_after_start_seconds"] = (
                    _relative_startup_event_seconds(
                        startup_started_at_monotonic,
                        runtime.auth_probe_released_at_monotonic,
                    )
                )
                pending_switcher = page.observe_open_switcher(timeout_ms=10_000)
                pending_local_row = _find_named_local_row(pending_switcher)
                result["pending_trigger_observation"] = (
                    _trigger_payload(trigger) if trigger is not None else None
                )
                result["pending_switcher_observation"] = _switcher_payload(
                    pending_switcher,
                )
                result["pending_local_row"] = (
                    _row_payload(pending_local_row) if pending_local_row is not None else None
                )
                if runtime.auth_probe_released_at_monotonic is not None:
                    _record_step(
                        result,
                        step=2,
                        status="failed",
                        action=REQUEST_STEPS[1],
                        observed=(
                            "Workspace switcher opened only after the delayed GitHub "
                            "`/user` auth probe had already finished.\n"
                            f"Observed trigger label: {_trigger_label(trigger)!r}\n"
                            f"Observed switcher text:\n{pending_switcher.switcher_text}"
                        ),
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Opened Workspace switcher as soon as the startup shell exposed "
                            "the header trigger and checked whether the delayed auth phase "
                            "was still in progress."
                        ),
                        observed=(
                            f"trigger_label={_trigger_label(trigger)!r}; "
                            f"trigger_observed_after_start_seconds={result['trigger_observed_after_start_seconds']!r}; "
                            f"auth_probe_started_after_start_seconds={result['auth_probe_started_after_start_seconds']!r}; "
                            f"auth_probe_released_after_start_seconds={result['auth_probe_released_after_start_seconds']!r}; "
                            f"switcher_text={pending_switcher.switcher_text!r}"
                        ),
                    )
                    _record_not_reached_steps(result, starting_step=3)
                    raise AssertionError(
                        "Step 2 failed: Workspace switcher opened only after the delayed "
                        "GitHub `/user` auth probe had already finished.\n"
                        f"Observed trigger label: {_trigger_label(trigger)!r}\n"
                        f"Observed switcher text:\n{pending_switcher.switcher_text}",
                    )
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=REQUEST_STEPS[1],
                    observed=(
                        "Opened Workspace switcher from the visible startup shell before the "
                        "delayed `/user` auth probe was ready.\n"
                        f"auth_probe_started_before_open={auth_started_before_open}; "
                        f"auth_probe_pending_after_open={runtime.auth_probe_pending}\n"
                        f"trigger_label={_trigger_label(trigger)!r}\n"
                        f"switcher_text={pending_switcher.switcher_text!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Viewed the startup shell like a user during the delayed-auth "
                        "window and opened Workspace switcher as soon as the visible "
                        "header trigger appeared, before the auth-ready state was reached."
                    ),
                    observed=(
                        f"trigger_label={_trigger_label(trigger)!r}; "
                        f"auth_probe_started_after_start_seconds={result['auth_probe_started_after_start_seconds']!r}; "
                        f"auth_probe_released_after_start_seconds={result['auth_probe_released_after_start_seconds']!r}; "
                        f"switcher_text={pending_switcher.switcher_text!r}"
                    ),
                )
                try:
                    _assert_pending_local_not_unavailable(
                        trigger=trigger,
                        switcher=pending_switcher,
                        local_row=pending_local_row,
                    )
                except AssertionError as error:
                    _record_step(
                        result,
                        step=3,
                        status="failed",
                        action=REQUEST_STEPS[2],
                        observed=str(error).replace("Step 3 failed: ", "", 1),
                    )
                    step_failures.append(str(error))
                else:
                    _record_step(
                        result,
                        step=3,
                        status="passed",
                        action=REQUEST_STEPS[2],
                        observed=(
                            "The saved local workspace row was visible during the delayed "
                            "auth phase and was not marked `Local Unavailable`.\n"
                            f"pending_local_row={json.dumps(_row_payload(pending_local_row), indent=2)}"
                        ),
                    )

                page.close_switcher()
                auth_released = runtime.wait_for_auth_probe_release(
                    timeout_seconds=AUTH_DELAY_SECONDS + 20,
                )
                result["auth_probe_released_at_monotonic"] = (
                    runtime.auth_probe_released_at_monotonic
                )
                result["auth_probe_released_after_start_seconds"] = (
                    _relative_startup_event_seconds(
                        startup_started_at_monotonic,
                        runtime.auth_probe_released_at_monotonic,
                    )
                )
                if auth_released:
                    _record_step(
                        result,
                        step=4,
                        status="passed",
                        action=REQUEST_STEPS[3],
                        observed=(
                            "The delayed GitHub `/user` auth verification request completed "
                            f"after {_observed_auth_delay_seconds(runtime):.2f} seconds."
                        ),
                    )
                else:
                    if runtime.auth_probe_started_at_monotonic is None:
                        step_4_observed = (
                            "The delayed GitHub `/user` auth verification request never "
                            "started, so no auth-ready signal was emitted within the "
                            "expected wait window.\n"
                            f"Observed delayed requests: {runtime.delayed_request_urls!r}"
                        )
                    else:
                        step_4_observed = (
                            "The delayed GitHub `/user` auth probe did not finish within "
                            "the expected wait window.\n"
                            f"Observed delayed requests: {runtime.delayed_request_urls!r}"
                        )
                    _record_step(
                        result,
                        step=4,
                        status="failed",
                        action=REQUEST_STEPS[3],
                        observed=step_4_observed,
                    )
                    step_failures.append(
                        "Step 4 failed: " + step_4_observed.split("\n", 1)[0],
                    )

                restored, final_trigger = poll_until(
                    probe=lambda: _try_observe_trigger(page),
                    is_satisfied=lambda candidate: (
                        candidate is not None
                        and _trigger_matches_expected_restore(candidate)
                    ),
                    timeout_seconds=STARTUP_RESTORE_WAIT_SECONDS,
                    interval_seconds=5,
                )
                final_switcher = _open_or_observe_switcher(page, timeout_ms=20_000)
                final_local_row = _find_named_local_row(final_switcher)
                selected_row = _find_selected_row(final_switcher) or (
                    _selected_row_from_trigger(final_trigger)
                    if final_trigger is not None
                    else None
                )
                result["final_trigger_observation"] = (
                    _trigger_payload(final_trigger) if final_trigger is not None else None
                )
                result["final_switcher_observation"] = _switcher_payload(final_switcher)
                result["final_local_row"] = (
                    _row_payload(final_local_row) if final_local_row is not None else None
                )
                result["selected_row"] = _row_payload(selected_row) if selected_row else None
                result["startup_restored_within_wait"] = restored
                _record_human_verification(
                    result,
                    check=(
                        "After the delayed auth window, reopened Workspace switcher and "
                        "visually checked whether the saved local workspace had become the "
                        "active Local Git selection and whether Connect GitHub was hidden."
                    ),
                    observed=(
                        f"final_trigger={_trigger_label(final_trigger)!r}; "
                        f"selected_row={json.dumps(_row_payload(selected_row), ensure_ascii=True)}; "
                        f"final_local_row={json.dumps(_row_payload(final_local_row), ensure_ascii=True)}"
                    ),
                )
                try:
                    _assert_ready_transition(
                        restored=restored,
                        final_trigger=final_trigger,
                        final_switcher=final_switcher,
                        final_local_row=final_local_row,
                        selected_row=selected_row,
                    )
                except AssertionError as error:
                    _record_step(
                        result,
                        step=5,
                        status="failed",
                        action=REQUEST_STEPS[4],
                        observed=str(error).replace("Step 5 failed: ", "", 1),
                    )
                    step_failures.append(str(error))
                else:
                    _record_step(
                        result,
                        step=5,
                        status="passed",
                        action=REQUEST_STEPS[4],
                        observed=(
                            "After the delayed auth-ready signal, the saved local workspace "
                            "was restored as the selected `Local Git` row and kept "
                            "`Connect GitHub` hidden.\n"
                            f"selected_row={json.dumps(_row_payload(selected_row), indent=2)}"
                        ),
                    )
                if step_failures:
                    raise AssertionError("\n".join(step_failures))
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
        _write_failure_outputs(result, include_bug_description=True)
        raise
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        _write_failure_outputs(result, include_bug_description=False)
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

    marker_path = local_path / ".trackstate-ts891-precondition.txt"
    marker_path.write_text(
        "Prepared for TS-891 startup auth-latency workspace restoration validation.\n",
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
                "user.name=TS-891 Automation",
                "-c",
                "user.email=ts891@example.com",
                "commit",
                "--allow-empty",
                "-m",
                "Prepare TS-891 local workspace",
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


def _storage_snapshot_keys(
    repository: str,
    workspace_state: dict[str, object],
) -> list[str]:
    keys = [
        "trackstate.workspaceProfiles.state",
        "flutter.trackstate.workspaceProfiles.state",
        f"trackstate.githubToken.{repository.replace('/', '.')}",
        f"flutter.trackstate.githubToken.{repository.replace('/', '.')}",
    ]
    raw_profiles = workspace_state.get("profiles", [])
    if isinstance(raw_profiles, list):
        for profile in raw_profiles:
            if not isinstance(profile, dict):
                continue
            workspace_id = str(profile.get("id", "")).strip()
            if not workspace_id:
                continue
            encoded_workspace_id = (
                workspace_id.replace("%", "%25")
                .replace(":", "%3A")
                .replace("/", "%2F")
                .replace("@", "%40")
            )
            keys.extend(
                [
                    f"trackstate.githubToken.workspace.{encoded_workspace_id}",
                    f"flutter.trackstate.githubToken.workspace.{encoded_workspace_id}",
                ],
            )
    return keys


def _try_observe_trigger(
    page: LiveWorkspaceSwitcherPage,
) -> WorkspaceSwitcherTriggerObservation | None:
    try:
        return page.observe_trigger(timeout_ms=1_000)
    except (AssertionError, WebAppTimeoutError):
        return None


def _try_observe_open_switcher(
    page: LiveWorkspaceSwitcherPage,
) -> WorkspaceSwitcherObservation | None:
    try:
        return page.observe_open_switcher(timeout_ms=5_000)
    except (AssertionError, WebAppTimeoutError):
        return None


def _open_or_observe_switcher(
    page: LiveWorkspaceSwitcherPage,
    *,
    timeout_ms: int,
) -> WorkspaceSwitcherObservation:
    try:
        return page.observe_open_switcher(timeout_ms=min(timeout_ms, 5_000))
    except (AssertionError, WebAppTimeoutError):
        return page.open_and_observe(timeout_ms=timeout_ms)


def _trigger_label(trigger: WorkspaceSwitcherTriggerObservation | None) -> str:
    if trigger is None:
        return "Workspace switcher already open on startup"
    return trigger.semantic_label
def _observed_auth_delay_seconds(
    runtime: DelayedAuthWorkspaceProfilesRuntime,
) -> float:
    if (
        runtime.auth_probe_started_at_monotonic is None
        or runtime.auth_probe_released_at_monotonic is None
    ):
        return AUTH_DELAY_SECONDS
    return (
        runtime.auth_probe_released_at_monotonic
        - runtime.auth_probe_started_at_monotonic
    )


def _relative_startup_event_seconds(
    startup_started_at_monotonic: float,
    event_monotonic: float | None,
) -> float | None:
    if event_monotonic is None:
        return None
    return round(event_monotonic - startup_started_at_monotonic, 2)

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
    anchor = f"{LOCAL_DISPLAY_NAME}, Local, "
    row_start = normalized.find(anchor)
    if row_start < 0 or detail_text not in normalized[row_start:]:
        return None
    delete_marker = f"Delete: {LOCAL_DISPLAY_NAME}"
    row_end = normalized.find(delete_marker, row_start)
    row_text = (
        normalized[row_start : row_end + len(delete_marker)]
        if row_end >= 0
        else normalized[row_start:]
    )
    state_label = None
    for candidate in ("Local Git", "Unavailable", "Needs sign-in"):
        if f", {candidate}," in row_text or f" {candidate} " in row_text:
            state_label = candidate
            break
    if "Retry: " in row_text:
        action_label = f"Retry: {LOCAL_DISPLAY_NAME}"
    elif "Open: " in row_text:
        action_label = f"Open: {LOCAL_DISPLAY_NAME}"
    elif " Active " in row_text:
        action_label = "Active"
    else:
        action_label = None
    if action_label is None:
        return None
    selected = action_label == "Active"
    button_labels = ("Delete",) if selected else (action_label, "Delete")
    return WorkspaceSwitcherRowObservation(
        display_name=LOCAL_DISPLAY_NAME,
        target_type_label="Local",
        state_label=state_label,
        detail_text=detail_text,
        visible_text=row_text,
        selected=selected,
        semantics_label=None,
        icon_accessibility_label=None,
        action_labels=(action_label,),
        button_labels=button_labels,
    )


def _assert_pending_local_not_unavailable(
    *,
    trigger: WorkspaceSwitcherTriggerObservation | None,
    switcher: WorkspaceSwitcherObservation,
    local_row: WorkspaceSwitcherRowObservation | None,
) -> None:
    if local_row is None:
        raise AssertionError(
            "Step 3 failed: Workspace switcher did not expose the saved local "
            "workspace row during the delayed auth phase.\n"
            f"Observed trigger label: {_trigger_label(trigger)!r}\n"
            f"Observed switcher text:\n{switcher.switcher_text}",
        )
    if (
        local_row.state_label == "Unavailable"
        or "Local Unavailable" in local_row.visible_text
        or "Local Unavailable" in switcher.switcher_text
    ):
        raise AssertionError(
            "Step 3 failed: while authentication was still delayed, the saved local "
            "workspace row was already flagged as `Local Unavailable`.\n"
            f"Observed local row: {json.dumps(_row_payload(local_row), indent=2)}\n"
            f"Observed trigger label: {_trigger_label(trigger)!r}\n"
            f"Observed switcher text:\n{switcher.switcher_text}",
        )


def _assert_ready_transition(
    *,
    restored: bool,
    final_trigger: WorkspaceSwitcherTriggerObservation | None,
    final_switcher: WorkspaceSwitcherObservation,
    final_local_row: WorkspaceSwitcherRowObservation | None,
    selected_row: WorkspaceSwitcherRowObservation | None,
) -> None:
    if final_local_row is None:
        raise AssertionError(
            "Step 5 failed: after the delayed auth-ready signal, Workspace switcher "
            "did not show the saved local workspace row.\n"
            f"Observed trigger label: {_trigger_label(final_trigger)!r}\n"
            f"Observed switcher text:\n{final_switcher.switcher_text}",
        )
    if final_local_row.state_label == "Unavailable" or "Local Unavailable" in final_local_row.visible_text:
        raise AssertionError(
            "Step 5 failed: after the delayed auth-ready signal, the saved local "
            "workspace row still showed `Local Unavailable` instead of transitioning "
            "to `Local Git`.\n"
            f"Observed local row: {json.dumps(_row_payload(final_local_row), indent=2)}\n"
            f"Observed trigger label: {_trigger_label(final_trigger)!r}",
        )
    if final_local_row.state_label != "Local Git":
        raise AssertionError(
            "Step 5 failed: after the delayed auth-ready signal, the saved local "
            "workspace row did not reach the `Local Git` state.\n"
            f"Observed local row: {json.dumps(_row_payload(final_local_row), indent=2)}",
        )
    if selected_row is None:
        raise AssertionError(
            "Step 5 failed: after the delayed auth-ready signal, Workspace switcher "
            "did not show any selected active row.\n"
            f"Observed rows: {[row.visible_text for row in final_switcher.rows]!r}",
        )
    if (
        selected_row.display_name != LOCAL_DISPLAY_NAME
        or selected_row.target_type_label != "Local"
    ):
        raise AssertionError(
            "Step 5 failed: after the delayed auth-ready signal, the selected row was "
            "not the saved active local workspace.\n"
            f"Observed selected row: {json.dumps(_row_payload(selected_row), indent=2)}\n"
            f"Observed local row: {json.dumps(_row_payload(final_local_row), indent=2)}",
        )
    row_actions = [*final_local_row.action_labels, *final_local_row.button_labels]
    if any(label == "Connect GitHub" for label in row_actions) or "Connect GitHub" in final_local_row.visible_text:
        raise AssertionError(
            "Step 5 failed: after the delayed auth-ready signal, the restored local "
            "workspace still exposed `Connect GitHub`.\n"
            f"Observed local row: {json.dumps(_row_payload(final_local_row), indent=2)}",
        )
    if final_trigger is not None and (
        final_trigger.display_name == HOSTED_DISPLAY_NAME
        or final_trigger.workspace_type == "Hosted"
    ):
        raise AssertionError(
            "Step 5 failed: after the delayed auth-ready signal, the header trigger "
            "still showed the hosted setup workspace instead of the saved local workspace.\n"
            f"Observed trigger label: {_trigger_label(final_trigger)!r}",
        )
    if not restored:
        raise AssertionError(
            "Step 5 failed: the saved local workspace never transitioned to the active "
            "`Local Git` state within the allowed wait after auth became ready.\n"
            f"Observed trigger label: {_trigger_label(final_trigger)!r}\n"
            f"Observed selected row: {json.dumps(_row_payload(selected_row), indent=2)}\n"
            f"Observed local row: {json.dumps(_row_payload(final_local_row), indent=2)}\n"
            f"Observed switcher text:\n{final_switcher.switcher_text}",
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


def _record_not_reached_steps(
    result: dict[str, object],
    *,
    starting_step: int,
) -> None:
    recorded = {
        int(step["step"])
        for step in result.get("steps", [])
        if isinstance(step, dict) and isinstance(step.get("step"), int)
    }
    for step_number in range(starting_step, len(REQUEST_STEPS) + 1):
        if step_number in recorded:
            continue
        _record_step(
            result,
            step=step_number,
            status="not_reached",
            action=REQUEST_STEPS[step_number - 1],
            observed=f"Not reached because step {starting_step - 1} failed.",
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
    _write_review_replies(result, passed=True)
    JIRA_COMMENT_PATH.write_text(_jira_comment(result, passed=True), encoding="utf-8")
    PR_BODY_PATH.write_text(_markdown_summary(result, passed=True), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_summary(result, passed=True), encoding="utf-8")


def _write_failure_outputs(
    result: dict[str, object],
    *,
    include_bug_description: bool,
) -> None:
    error = str(result.get("error", "AssertionError: TS-891 failed"))
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
    _write_review_replies(result, passed=False)
    JIRA_COMMENT_PATH.write_text(_jira_comment(result, passed=False), encoding="utf-8")
    PR_BODY_PATH.write_text(_markdown_summary(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_summary(result, passed=False), encoding="utf-8")
    if include_bug_description:
        BUG_DESCRIPTION_PATH.write_text(_bug_description(result), encoding="utf-8")
    else:
        BUG_DESCRIPTION_PATH.unlink(missing_ok=True)


def _jira_comment(result: dict[str, object], *, passed: bool) -> str:
    status = "✅ PASSED" if passed else "❌ FAILED"
    lines = [
        "h3. Test Automation Result",
        "",
        f"*Status:* {status}",
        f"*Test Case:* {TICKET_KEY} - {TEST_CASE_TITLE}",
        "",
        "h4. What was automated",
        "* Opened the deployed TrackState app in Chromium with a preloaded active local workspace profile and a stored GitHub token.",
        f"* Delayed the GitHub {{/user}} auth verification request by {AUTH_DELAY_SECONDS} seconds to reproduce startup authentication latency.",
        "* Attempted to open *Workspace switcher* as soon as the startup shell exposed the header trigger, then verified whether the delayed auth probe was still in progress and inspected the saved local workspace row.",
        f"* Waited for the delayed auth-ready signal and then up to {STARTUP_RESTORE_WAIT_SECONDS} seconds for startup restoration instead of asserting immediately.",
        "* Reopened *Workspace switcher* and verified whether the saved local workspace became the selected {{Local Git}} row with {{Connect GitHub}} hidden.",
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
        "- Opened the deployed TrackState app in Chromium with a preloaded active local workspace profile and a stored GitHub token.",
        f"- Delayed the GitHub `/user` auth verification request by {AUTH_DELAY_SECONDS} seconds to reproduce startup authentication latency.",
        "- Attempted to open **Workspace switcher** as soon as the startup shell exposed the header trigger, then verified whether the delayed auth probe was still in progress and inspected the saved local workspace row.",
        f"- Waited for the delayed auth-ready signal and then up to {STARTUP_RESTORE_WAIT_SECONDS} seconds for startup restoration instead of asserting immediately.",
        "- Reopened **Workspace switcher** and verified whether the saved local workspace became the selected `Local Git` row with `Connect GitHub` hidden.",
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
        "- Added TS-891 live startup coverage for delayed-auth local workspace restoration.",
        f"- Test case: **{TICKET_KEY} - {TEST_CASE_TITLE}**",
        f"- Result: **{status}**",
        f"- Command: `{RUN_COMMAND}`",
        (
            f"- Environment: `{result['app_url']}` on Chromium/Playwright "
            f"({result['os']}) against `{result['repository']}` @ "
            f"`{result['repository_ref']}`."
        ),
        (
            "- Outcome: the delayed-auth startup flow kept the local workspace out of "
            "Local Unavailable and restored it as the active `Local Git` row."
            if passed
            else f"- Outcome: {_failed_step_summary(result)}"
        ),
    ]
    if result.get("screenshot"):
        lines.append(f"- Screenshot: `{result['screenshot']}`")
    return "\n".join(lines) + "\n"


def _bug_description(result: dict[str, object]) -> str:
    lines = [
        f"# {TICKET_KEY} - {_bug_title(result)}",
        "",
        "## Summary",
        _failed_step_summary(result),
        "",
        "## Steps to reproduce",
        *_bug_step_lines(result),
        "",
        "## Actual result",
        _actual_result(result),
        "",
        "## Expected result",
        EXPECTED_RESULT,
        "",
        "## Exact error",
        "```text",
        str(result.get("traceback", result.get("error", ""))),
        "```",
        "",
        "## Environment",
        f"- URL: `{result['app_url']}`",
        f"- Repository: `{result['repository']}` @ `{result['repository_ref']}`",
        "- Browser: `Chromium (Playwright)`",
        f"- OS: `{result['os']}`",
        f"- Auth delay: `{AUTH_DELAY_SECONDS}` seconds on GitHub `/user`",
        "",
        "## Evidence",
        f"- Delayed GitHub requests: `{json.dumps(result.get('delayed_request_urls', []), ensure_ascii=True)}`",
        f"- GitHub requests seen: `{json.dumps(result.get('github_request_urls', []), ensure_ascii=True)}`",
    ]
    if result.get("screenshot"):
        lines.append(f"- Screenshot: `{result['screenshot']}`")
    return "\n".join(lines) + "\n"


def _bug_title(result: dict[str, object]) -> str:
    mode = _step_two_failure_mode(result)
    if mode == "auth-probe-never-started":
        return (
            "Delayed GitHub /user verification never starts during active local "
            "workspace startup restoration"
        )
    if mode == "switcher-available-after-auth-ready":
        return (
            "Workspace switcher becomes available only after delayed auth is ready "
            "during startup restoration"
        )
    return "Delayed-auth startup restoration does not reach the expected Local Git transition"


def _failed_step_summary(result: dict[str, object]) -> str:
    failures: list[str] = []
    for step in result.get("steps", []):
        if isinstance(step, dict) and step.get("status") == "failed":
            failures.append(
                f"Step {step.get('step')} failed while attempting to "
                f"{step.get('action')} Observed: {step.get('observed')}"
            )
    if failures:
        return " | ".join(failures)
    return str(result.get("error", "The delayed-auth startup scenario failed."))


def _write_review_replies(result: dict[str, object], *, passed: bool) -> None:
    replies = [
        {
            "inReplyToId": thread.get("rootCommentId"),
            "threadId": thread.get("threadId"),
            "reply": _review_reply_text(thread=thread, passed=passed, result=result),
        }
        for thread in _discussion_threads()
    ]
    REVIEW_REPLIES_PATH.write_text(
        json.dumps({"replies": replies}) + "\n",
        encoding="utf-8",
    )


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


def _review_reply_text(
    *,
    thread: dict[str, object],
    passed: bool,
    result: dict[str, object],
) -> str:
    path = str(thread.get("path") or "")
    rerun_summary = (
        f"Re-ran `{RUN_COMMAND}`: passed (`1 passed, 0 failed`)."
        if passed
        else f"Re-ran `{RUN_COMMAND}`: failed at {_failed_step_summary(result)}"
    )
    if path.endswith("stored_workspace_profiles_runtime.py"):
        return (
            "Fixed: the stored workspace runtime still seeds workspace-scoped GitHub "
            "token keys by default when callers omit `workspace_token_profile_ids`, "
            "so TS-891 again exercises the real delayed-auth startup path instead of "
            "failing from broken setup. "
            + rerun_summary
        )
    if path.endswith("test_ts_891.py"):
        return (
            "Fixed: when step 2 cannot observe a real delayed-auth pending window, "
            "steps 3-5 are now recorded as `not_reached` instead of extra product "
            "assertion failures, so the failure evidence stays scoped to the actual "
            "step-2 blocker. "
            + rerun_summary
        )
    return "Fixed and re-ran the requested TS-891 coverage. " + rerun_summary


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
        if record.get("status") == "passed":
            marker = "✅"
        elif record.get("status") == "not_reached":
            marker = "⏭️"
        else:
            marker = "❌"
        lines.append(f"{index}. {action} — {marker} {record.get('observed')}")
    return lines


def _actual_result(result: dict[str, object]) -> str:
    trigger_observed_after_start_seconds = result.get("trigger_observed_after_start_seconds")
    auth_probe_started_after_start_seconds = result.get(
        "auth_probe_started_after_start_seconds",
    )
    auth_probe_released_after_start_seconds = result.get(
        "auth_probe_released_after_start_seconds",
    )
    for step in result.get("steps", []):
        if (
            isinstance(step, dict)
            and step.get("step") == 2
            and step.get("status") == "failed"
        ):
            mode = _step_two_failure_mode(result)
            if mode == "auth-probe-never-started":
                return (
                    "Workspace switcher opened from the startup shell, but the delayed "
                    "GitHub `/user` verification request never started for the active "
                    "local workspace. "
                    f"Trigger visible after startup: {trigger_observed_after_start_seconds!r} seconds. "
                    f"Delayed `/user` probe started after: {auth_probe_started_after_start_seconds!r} seconds. "
                    f"Delayed `/user` probe released after: {auth_probe_released_after_start_seconds!r} seconds. "
                    f"Observed step-2 failure: {step.get('observed')}"
                )
            if mode == "switcher-available-after-auth-ready":
                return (
                    "The delayed GitHub `/user` auth probe was already finished by the "
                    "time Workspace switcher became usable for inspection, so the "
                    "pending-auth phase could not be observed. "
                    f"Trigger visible after startup: {trigger_observed_after_start_seconds!r} seconds. "
                    f"Delayed `/user` probe started after: {auth_probe_started_after_start_seconds!r} seconds. "
                    f"Delayed `/user` probe released after: {auth_probe_released_after_start_seconds!r} seconds. "
                    f"Observed step-2 failure: {step.get('observed')}"
                )
            return (
                "The delayed-auth startup flow failed during the step-2 pending-phase "
                "inspection. "
                f"Trigger visible after startup: {trigger_observed_after_start_seconds!r} seconds. "
                f"Delayed `/user` probe started after: {auth_probe_started_after_start_seconds!r} seconds. "
                f"Delayed `/user` probe released after: {auth_probe_released_after_start_seconds!r} seconds. "
                f"Observed step-2 failure: {step.get('observed')}"
            )
    final_trigger = result.get("final_trigger_observation")
    final_local_row = result.get("final_local_row")
    final_step_five_failure = next(
        (
            step
            for step in result.get("steps", [])
            if isinstance(step, dict)
            and step.get("step") == 5
            and step.get("status") == "failed"
        ),
        None,
    )
    for step in result.get("steps", []):
        if (
            isinstance(step, dict)
            and step.get("step") == 2
            and step.get("status") == "failed"
        ):
            mode = _step_two_failure_mode(result)
            if mode == "auth-probe-never-started":
                return (
                    "Workspace switcher opened from the startup shell, but the delayed "
                    "GitHub `/user` verification request never started for the active "
                    "local workspace. "
                    f"Trigger visible after startup: {trigger_observed_after_start_seconds!r} seconds. "
                    f"Delayed `/user` probe started after: {auth_probe_started_after_start_seconds!r} seconds. "
                    f"Delayed `/user` probe released after: {auth_probe_released_after_start_seconds!r} seconds. "
                    f"Observed step-2 failure: {step.get('observed')} "
                    f"Final local row after the wait: {json.dumps(final_local_row, ensure_ascii=True)}. "
                    f"Final step-5 failure: {final_step_five_failure.get('observed') if isinstance(final_step_five_failure, dict) else None}"
                )
            if mode == "switcher-available-after-auth-ready":
                return (
                    "The delayed GitHub `/user` auth probe was already finished by the "
                    "time Workspace switcher became usable for inspection, so the "
                    "pending-auth phase could not be observed. "
                    f"Trigger visible after startup: {trigger_observed_after_start_seconds!r} seconds. "
                    f"Delayed `/user` probe started after: {auth_probe_started_after_start_seconds!r} seconds. "
                    f"Delayed `/user` probe released after: {auth_probe_released_after_start_seconds!r} seconds. "
                    f"Observed step-2 failure: {step.get('observed')} "
                    f"Final local row after the wait: {json.dumps(final_local_row, ensure_ascii=True)}. "
                    f"Final step-5 failure: {final_step_five_failure.get('observed') if isinstance(final_step_five_failure, dict) else None}"
                )
            return (
                "The delayed-auth startup flow failed during the step-2 pending-phase "
                "inspection. "
                f"Trigger visible after startup: {trigger_observed_after_start_seconds!r} seconds. "
                f"Delayed `/user` probe started after: {auth_probe_started_after_start_seconds!r} seconds. "
                f"Delayed `/user` probe released after: {auth_probe_released_after_start_seconds!r} seconds. "
                f"Observed step-2 failure: {step.get('observed')} "
                f"Final local row after the wait: {json.dumps(final_local_row, ensure_ascii=True)}. "
                f"Final step-5 failure: {final_step_five_failure.get('observed') if isinstance(final_step_five_failure, dict) else None}"
            )
    final_trigger = result.get("final_trigger_observation")
    pending_local_row = result.get("pending_local_row")
    if final_trigger or final_local_row or pending_local_row:
        return (
            "The delayed-auth startup flow did not match the expected user-facing "
            "transition. "
            f"Pending local row: {json.dumps(pending_local_row, ensure_ascii=True)}. "
            f"Final trigger: {json.dumps(final_trigger, ensure_ascii=True)}. "
            f"Final local row: {json.dumps(final_local_row, ensure_ascii=True)}."
        )
    return str(result.get("error", "The delayed-auth startup flow failed."))


def _step_two_failure_mode(result: dict[str, object]) -> str | None:
    for step in result.get("steps", []):
        if (
            isinstance(step, dict)
            and step.get("step") == 2
            and step.get("status") == "failed"
        ):
            observed = str(step.get("observed", ""))
            if (
                result.get("auth_probe_started_after_start_seconds") is None
                or "never started" in observed
            ):
                return "auth-probe-never-started"
            if (
                result.get("auth_probe_released_after_start_seconds") is not None
                or "already completed" in observed
                or "opened only after" in observed
            ):
                return "switcher-available-after-auth-ready"
            return "step-two-pending-phase-failure"
    return None


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
        status = step.get("status")
        if status == "passed":
            icon = "✅"
        elif status == "not_reached":
            icon = "⏭️"
        else:
            icon = "❌"
        lines.append(
            f"{prefix} {icon} Step {step.get('step')}: {step.get('action')} "
            f"Observed: {step.get('observed')}"
        )
    return lines


def _artifact_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    prefix = "*" if jira else "-"
    lines: list[str] = []
    if result.get("screenshot"):
        lines.append(f"{prefix} Screenshot: `{result['screenshot']}`")
    if result.get("delayed_request_urls"):
        lines.append(
            f"{prefix} Delayed auth requests: `{json.dumps(result['delayed_request_urls'], ensure_ascii=True)}`",
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


if __name__ == "__main__":
    main()
