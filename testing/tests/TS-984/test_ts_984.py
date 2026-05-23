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
    WorkspaceSwitcherTriggerObservation,
)
from testing.components.pages.trackstate_tracker_page import TrackStateTrackerPage  # noqa: E402
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.interfaces.web_app_session import WebAppTimeoutError  # noqa: E402
from testing.core.utils.polling import poll_until  # noqa: E402
from testing.tests.support.ts984_delayed_auth_probe_runtime import (  # noqa: E402
    Ts984DelayedAuthProbeRuntime,
)

TICKET_KEY = "TS-984"
TEST_CASE_TITLE = (
    "Application startup with hanging synchronization probe — UI shell renders "
    "after 11s timeout"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-984/test_ts_984.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
DEFAULT_BRANCH = "main"
LOCAL_TARGET = "/tmp/trackstate-demo"
LOCAL_DISPLAY_NAME = "Active local workspace"
HOSTED_DISPLAY_NAME = "Hosted setup workspace"
SHELL_NAVIGATION_LABELS = ("Dashboard", "Board", "JQL Search", "Hierarchy", "Settings")
BRANDING_TEXT = "Git-native. Jira-compatible. Team-proven."
SYNC_TIMEOUT_SECONDS = 11
SIMULATED_SYNC_DELAY_SECONDS = 31
TIMEOUT_ASSERTION_SECONDS = SYNC_TIMEOUT_SECONDS
LINKED_BUGS = ["TS-996", "TS-973", "TS-971"]
REWORK_SUMMARY = (
    "Added a live startup regression for TS-984 that delays the initial GitHub "
    "`/user` probe beyond 30 seconds and verifies the deployed app still reaches "
    "shell_ready and renders the user-visible shell once the explicit 11-second "
    "timeout path takes over."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts984_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts984_failure.png"

REQUEST_STEPS = [
    "Launch the TrackState application.",
    "Monitor the application startup sequence and the transition to the shell_ready state.",
    "Wait for the duration of the explicit 11-second synchronization timeout.",
    "Verify the visibility of interactive shell components such as the TopBar and branding.",
]
EXPECTED_RESULT = (
    "The application UI shell (TopBar, branding) becomes visible and interactive "
    "within the 11-second timeout window, confirming that the shell_ready state "
    "was triggered by the timeout fallback path rather than waiting for the "
    "hanging probe to complete."
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
            "TS-984 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
        )

    workspace_state = _workspace_state(service.repository)
    prepared_local_workspace = _prepare_local_workspace_repository()
    runtime = Ts984DelayedAuthProbeRuntime(
        repository=config.repository,
        token=token,
        workspace_state=workspace_state,
        auth_delay_seconds=SIMULATED_SYNC_DELAY_SECONDS,
        delayed_paths=("/user",),
    )

    result: dict[str, Any] = {
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
        "sync_timeout_seconds": SYNC_TIMEOUT_SECONDS,
        "simulated_sync_delay_seconds": SIMULATED_SYNC_DELAY_SECONDS,
        "timeout_assertion_seconds": TIMEOUT_ASSERTION_SECONDS,
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
                startup_started_at_monotonic = time.monotonic()
                tracker_page.open_entrypoint()
                page.set_viewport(**DESKTOP_VIEWPORT)
                result["startup_observation_initial"] = _startup_surface_payload(
                    tracker_page,
                )
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=REQUEST_STEPS[0],
                    observed=(
                        "Opened the deployed TrackState app in Chromium with a stored "
                        "GitHub token, a preloaded active local workspace plus hosted "
                        "fallback workspace profile, and an "
                        f"injected {SIMULATED_SYNC_DELAY_SECONDS}-second delay on the "
                        "initial GitHub `/user` startup probe."
                    ),
                )

                trigger_visible, initial_trigger = poll_until(
                    probe=lambda: _try_observe_trigger(page),
                    is_satisfied=lambda candidate: candidate is not None,
                    timeout_seconds=120,
                    interval_seconds=0.5,
                )
                result["runtime_state"] = "startup-shell-visible" if trigger_visible else "startup-pending"
                result["runtime_body_text"] = page.current_body_text()
                result["initial_trigger_observation"] = (
                    _trigger_payload(initial_trigger) if initial_trigger is not None else None
                )
                if not trigger_visible or initial_trigger is None:
                    _record_step(
                        result,
                        step=2,
                        status="failed",
                        action=REQUEST_STEPS[1],
                        observed=(
                            "The deployed app never exposed the interactive shell trigger "
                            "needed to confirm the shell_ready transition.\n"
                            f"Observed body text:\n{tracker_page.body_text()}"
                        ),
                    )
                    _record_not_reached_steps(result, starting_step=3)
                    raise AssertionError(
                        "Step 2 failed: the deployed app never exposed the interactive "
                        "shell trigger needed to confirm the shell_ready transition.\n"
                        f"Observed body text:\n{tracker_page.body_text()}",
                    )

                if not runtime.wait_for_auth_probe_start(timeout_seconds=30):
                    _record_step(
                        result,
                        step=2,
                        status="failed",
                        action=REQUEST_STEPS[1],
                        observed=(
                            "The shell trigger became visible, but the delayed GitHub "
                            "`/user` startup probe never began, so the timeout-driven "
                            "synchronization scenario was not exercised.\n"
                            f"Observed trigger: {json.dumps(_trigger_payload(initial_trigger), indent=2)}\n"
                            f"Observed shell probe state: {json.dumps(runtime.read_shell_probe_state(), indent=2)}\n"
                            f"Observed body text:\n{tracker_page.body_text()}"
                        ),
                    )
                    _record_not_reached_steps(result, starting_step=3)
                    raise AssertionError(
                        "Step 2 failed: the shell trigger became visible, but the delayed "
                        "GitHub `/user` startup probe never began, so the synchronization-"
                        "timeout scenario was not exercised.\n"
                        f"Observed trigger: {json.dumps(_trigger_payload(initial_trigger), indent=2)}\n"
                        f"Observed shell probe state: {json.dumps(runtime.read_shell_probe_state(), indent=2)}\n"
                        f"Observed body text:\n{tracker_page.body_text()}",
                    )

                auth_released = runtime.wait_for_auth_probe_release(
                    timeout_seconds=SIMULATED_SYNC_DELAY_SECONDS + 20,
                )
                shell_ready_observed = runtime.wait_for_shell_ready_observation(
                    timeout_seconds=5,
                )
                final_shell_window = _observe_shell_window(
                    tracker_page=tracker_page,
                    page=page,
                    runtime=runtime,
                    startup_started_at_monotonic=startup_started_at_monotonic,
                )
                result["timeout_window_observation"] = final_shell_window
                result["github_request_urls"] = list(runtime.github_request_urls)
                result["delayed_request_urls"] = list(runtime.delayed_request_urls)

                failures: list[str] = []
                first_shell_ready_after_start_seconds = final_shell_window[
                    "first_shell_ready_after_start_seconds"
                ]
                auth_probe_released_after_start_seconds = final_shell_window[
                    "auth_probe_released_after_start_seconds"
                ]
                auth_probe_release_after_auth_start_seconds = final_shell_window[
                    "auth_probe_release_after_auth_start_seconds"
                ]
                if not shell_ready_observed or first_shell_ready_after_start_seconds is None:
                    step_two_error = (
                        "Step 2 failed: the deployed app never reached shell_ready during "
                        "the delayed startup-probe scenario.\n"
                        f"Observed shell window:\n{json.dumps(final_shell_window, indent=2)}"
                    )
                    failures.append(step_two_error)
                    _record_step(
                        result,
                        step=2,
                        status="failed",
                        action=REQUEST_STEPS[1],
                        observed=step_two_error,
                    )
                elif (
                    first_shell_ready_after_start_seconds is not None
                    and first_shell_ready_after_start_seconds > TIMEOUT_ASSERTION_SECONDS
                ):
                    step_two_error = (
                        "Step 2 failed: the deployed app first exposed shell_ready only "
                        f"after {first_shell_ready_after_start_seconds!r} seconds from launch, "
                        f"which exceeds the {TIMEOUT_ASSERTION_SECONDS}-second timeout window.\n"
                        f"Observed shell window:\n{json.dumps(final_shell_window, indent=2)}"
                    )
                    failures.append(step_two_error)
                    _record_step(
                        result,
                        step=2,
                        status="failed",
                        action=REQUEST_STEPS[1],
                        observed=step_two_error,
                    )
                else:
                    _record_step(
                        result,
                        step=2,
                        status="passed",
                        action=REQUEST_STEPS[1],
                        observed=(
                            "The deployed app exposed shell_ready during the delayed `/user` "
                            "startup probe sequence and did so before the 11-second timeout "
                            "window expired.\n"
                            f"initial_trigger={json.dumps(_trigger_payload(initial_trigger), ensure_ascii=True)}; "
                            f"first_shell_ready_after_start_seconds="
                            f"{first_shell_ready_after_start_seconds!r}; "
                            f"auth_probe_started_after_start_seconds="
                            f"{final_shell_window['auth_probe_started_after_start_seconds']!r}; "
                            f"auth_probe_released_after_start_seconds="
                            f"{auth_probe_released_after_start_seconds!r}"
                        ),
                    )

                step_three_error: str | None = None
                if not auth_released or auth_probe_released_after_start_seconds is None:
                    step_three_error = (
                        "Step 3 failed: the delayed `/user` startup probe never completed, "
                        "so the test could not compare the shell-ready timestamp against the "
                        "delayed probe release.\n"
                        f"Observed shell window:\n{json.dumps(final_shell_window, indent=2)}"
                    )
                elif auth_probe_released_after_start_seconds <= TIMEOUT_ASSERTION_SECONDS:
                    step_three_error = (
                        "Step 3 failed: the delayed `/user` probe did not remain hanging "
                        "past the explicit 11-second timeout window.\n"
                        f"Observed auth_probe_released_after_start_seconds="
                        f"{auth_probe_released_after_start_seconds!r}; "
                        f"first_shell_ready_after_start_seconds="
                        f"{first_shell_ready_after_start_seconds!r}\n"
                        f"Observed shell window:\n{json.dumps(final_shell_window, indent=2)}"
                    )
                elif first_shell_ready_after_start_seconds > TIMEOUT_ASSERTION_SECONDS:
                    step_three_error = (
                        "Step 3 failed: shell_ready was first observed only after the "
                        f"{TIMEOUT_ASSERTION_SECONDS}-second timeout window.\n"
                        f"Observed first_shell_ready_after_start_seconds="
                        f"{first_shell_ready_after_start_seconds!r}; "
                        f"auth_probe_started_after_start_seconds="
                        f"{final_shell_window['auth_probe_started_after_start_seconds']!r}\n"
                        f"Observed shell window:\n{json.dumps(final_shell_window, indent=2)}"
                    )
                elif (
                    auth_probe_released_after_start_seconds is not None
                    and first_shell_ready_after_start_seconds >= auth_probe_released_after_start_seconds
                ):
                    step_three_error = (
                        "Step 3 failed: the shell became observable only after the delayed "
                        "`/user` probe released, so the timeout fallback path did not prove "
                        "the shell was available during the hanging startup request.\n"
                        f"Observed first_shell_ready_after_start_seconds="
                        f"{first_shell_ready_after_start_seconds!r}; "
                        f"auth_probe_released_after_start_seconds="
                        f"{auth_probe_released_after_start_seconds!r}; "
                        f"auth_probe_release_after_auth_start_seconds="
                        f"{auth_probe_release_after_auth_start_seconds!r}\n"
                        f"Observed shell window:\n{json.dumps(final_shell_window, indent=2)}"
                    )

                if step_three_error is None:
                    _record_step(
                        result,
                        step=3,
                        status="passed",
                        action=REQUEST_STEPS[2],
                        observed=(
                            f"Recorded first_shell_ready_after_start_seconds="
                            f"{first_shell_ready_after_start_seconds!r}; "
                            f"auth_probe_released_after_start_seconds="
                            f"{auth_probe_released_after_start_seconds!r}; "
                            f"auth_probe_release_after_auth_start_seconds="
                            f"{auth_probe_release_after_auth_start_seconds!r}. "
                            "This shows the shell became available within 11 seconds from "
                            "launch while the delayed `/user` probe remained unresolved."
                        ),
                    )
                else:
                    failures.append(step_three_error)
                    _record_step(
                        result,
                        step=3,
                        status="failed",
                        action=REQUEST_STEPS[2],
                        observed=step_three_error,
                    )

                step_four_error: str | None = None
                try:
                    _assert_shell_components(final_shell_window)
                except AssertionError as error:
                    step_four_error = str(error)
                if (
                    step_three_error is not None
                    and step_four_error is None
                    and first_shell_ready_after_start_seconds is not None
                    and float(first_shell_ready_after_start_seconds) > TIMEOUT_ASSERTION_SECONDS
                ):
                    step_four_error = (
                        "Step 4 failed: the top bar and branding were only observable after "
                        "the expected "
                        f"{TIMEOUT_ASSERTION_SECONDS}-second timeout window.\n"
                        f"Observed first_shell_ready_after_start_seconds="
                        f"{first_shell_ready_after_start_seconds!r}; "
                        f"auth_probe_released_after_start_seconds="
                        f"{auth_probe_released_after_start_seconds!r}\n"
                        f"Observed shell window:\n{json.dumps(final_shell_window, indent=2)}"
                    )
                elif step_three_error is not None and step_four_error is None:
                    step_four_error = (
                        "Step 4 failed: at the timeout-window snapshot, the interactive "
                        "shell components were not all visible because the page had not "
                        "reached shell_ready.\n"
                        f"Observed shell window:\n{json.dumps(final_shell_window, indent=2)}"
                    )
                if step_four_error is None:
                    _record_step(
                        result,
                        step=4,
                        status="passed",
                        action=REQUEST_STEPS[3],
                        observed=(
                            "The final live page exposed the interactive shell with the "
                            "expected navigation, TopBar workspace trigger, and branding.\n"
                            f"title={final_shell_window['startup_observation']['title']!r}; "
                            f"trigger={json.dumps(final_shell_window['trigger'], ensure_ascii=True)}; "
                            f"branding_visible={final_shell_window['branding_visible']!r}; "
                            f"visible_navigation_labels="
                            f"{json.dumps(final_shell_window['shell_observation']['visible_navigation_labels'], ensure_ascii=True)}"
                        ),
                    )
                else:
                    failures.append(step_four_error)
                    _record_step(
                        result,
                        step=4,
                        status="failed",
                        action=REQUEST_STEPS[3],
                        observed=step_four_error,
                    )

                _record_human_verification(
                    result,
                    check=(
                        "Viewed the live app after the delayed `/user` probe completed and "
                        "checked the page the way a user would: visible shell navigation, a "
                        "TopBar workspace trigger, and branding text instead of a stalled "
                        "startup surface."
                    ),
                    observed=(
                        f"body_text_snippet={_snippet(final_shell_window['shell_observation']['body_text'])!r}; "
                        f"branding_text_visible={final_shell_window['branding_visible']!r}; "
                        f"trigger_label="
                        f"{(final_shell_window['trigger'] or {}).get('semantic_label')!r}; "
                        f"visible_buttons="
                        f"{json.dumps(final_shell_window['startup_observation']['button_labels'], ensure_ascii=True)}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Compared the recorded shell-ready timestamp against the delayed "
                        "GitHub `/user` release timing to confirm the shell became visible "
                        "before the hanging startup probe finished."
                    ),
                    observed=(
                        f"auth_released={auth_released!r}; "
                        f"first_shell_ready_after_start_seconds="
                        f"{first_shell_ready_after_start_seconds!r}; "
                        f"auth_probe_released_after_start_seconds="
                        f"{auth_probe_released_after_start_seconds!r}; "
                        f"delayed_request_urls={json.dumps(result['delayed_request_urls'], ensure_ascii=True)}"
                    ),
                )

                if failures:
                    raise AssertionError("\n\n".join(failures))

                page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
                _write_pass_outputs(result)
                print(f"{TICKET_KEY} passed")
                return
            except Exception:
                try:
                    tracker_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                    result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                except Exception as screenshot_error:  # pragma: no cover - diagnostics only
                    result["screenshot_error"] = (
                        f"{type(screenshot_error).__name__}: {screenshot_error}"
                    )
                raise
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
                "lastOpenedAt": "2026-05-23T00:00:00.000Z",
            },
            {
                "id": hosted_id,
                "displayName": HOSTED_DISPLAY_NAME,
                "customDisplayName": HOSTED_DISPLAY_NAME,
                "targetType": "hosted",
                "target": repository,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": DEFAULT_BRANCH,
                "lastOpenedAt": "2026-05-23T00:00:00.000Z",
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

    marker_path = local_path / ".trackstate-ts984-precondition.txt"
    marker_path.write_text(
        "Prepared for TS-984 startup synchronization timeout validation.\n",
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
                "user.name=TS-984 Automation",
                "-c",
                "user.email=ts984@example.com",
                "commit",
                "--allow-empty",
                "-m",
                "Prepare TS-984 local workspace",
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


def _observe_shell_window(
    *,
    tracker_page: TrackStateTrackerPage,
    page: LiveWorkspaceSwitcherPage,
    runtime: Ts984DelayedAuthProbeRuntime,
    startup_started_at_monotonic: float,
) -> dict[str, Any]:
    shell_probe_state = runtime.read_shell_probe_state()
    shell_observation = tracker_page.observe_interactive_shell(
        SHELL_NAVIGATION_LABELS,
        timeout_ms=1_000,
    )
    startup_observation = _startup_surface_payload(tracker_page)
    trigger = _safe_trigger_payload(page)
    body_text = str(shell_observation.get("body_text", ""))
    visible_shell_text = "\n".join(
        text
        for text in (
            body_text,
            str(startup_observation.get("body_text", "")),
        )
        if text
    )
    first_shell_ready_after_start_seconds = shell_probe_state[
        "first_shell_ready_after_launch_seconds"
    ]
    return {
        "shell_probe_state": shell_probe_state,
        "shell_observation": shell_observation,
        "startup_observation": startup_observation,
        "trigger": trigger,
        "branding_visible": any(
            branding_text in visible_shell_text
            for branding_text in (BRANDING_TEXT, "TrackState.AI")
        ),
        "auth_pending": runtime.auth_probe_pending,
        "auth_probe_started_after_start_seconds": _relative_startup_event_seconds(
            startup_started_at_monotonic,
            runtime.auth_probe_started_at_monotonic,
        ),
        "auth_probe_released_after_start_seconds": _relative_startup_event_seconds(
            startup_started_at_monotonic,
            runtime.auth_probe_released_at_monotonic,
        ),
        "auth_probe_release_after_auth_start_seconds": _relative_event_seconds(
            runtime.auth_probe_started_at_monotonic,
            runtime.auth_probe_released_at_monotonic,
        ),
        "first_shell_ready_after_start_seconds": first_shell_ready_after_start_seconds,
    }


def _relative_startup_event_seconds(
    startup_started_at_monotonic: float,
    event_monotonic: float | None,
) -> float | None:
    if event_monotonic is None:
        return None
    return round(event_monotonic - startup_started_at_monotonic, 2)


def _relative_event_seconds(
    started_at_monotonic: float | None,
    event_monotonic: float | None,
) -> float | None:
    if started_at_monotonic is None or event_monotonic is None:
        return None
    return round(event_monotonic - started_at_monotonic, 2)


def _startup_surface_payload(tracker_page: TrackStateTrackerPage) -> dict[str, Any]:
    observation = tracker_page.observe_startup_surface()
    return {
        "title": observation.title,
        "location_href": observation.location_href,
        "location_hash": observation.location_hash,
        "location_pathname": observation.location_pathname,
        "body_text": observation.body_text,
        "button_labels": list(observation.button_labels),
    }


def _safe_trigger_payload(
    page: LiveWorkspaceSwitcherPage,
) -> dict[str, Any] | None:
    try:
        trigger = page.observe_trigger(timeout_ms=1_000)
    except (AssertionError, WebAppTimeoutError):
        return None
    return _trigger_payload(trigger)


def _try_observe_trigger(
    page: LiveWorkspaceSwitcherPage,
) -> WorkspaceSwitcherTriggerObservation | None:
    try:
        return page.observe_trigger(timeout_ms=1_000)
    except (AssertionError, WebAppTimeoutError):
        return None


def _trigger_payload(trigger: WorkspaceSwitcherTriggerObservation) -> dict[str, Any]:
    return {
        "semantic_label": trigger.semantic_label,
        "visible_text": trigger.visible_text,
        "display_name": trigger.display_name,
        "workspace_type": trigger.workspace_type,
        "state_label": trigger.state_label,
        "top_button_labels": list(trigger.top_button_labels),
    }


def _assert_shell_components(observation: dict[str, Any]) -> None:
    shell = observation["shell_observation"]
    missing_navigation = [
        label
        for label in SHELL_NAVIGATION_LABELS
        if label not in shell["visible_navigation_labels"]
    ]
    if missing_navigation:
        raise AssertionError(
            "Step 4 failed: the timeout-window shell snapshot did not expose the full "
            "interactive navigation.\n"
            f"Missing labels: {missing_navigation}\n"
            f"Observed shell window:\n{json.dumps(observation, indent=2)}",
        )
    if observation["trigger"] is None:
        raise AssertionError(
            "Step 4 failed: the timeout-window shell snapshot did not expose the "
            "TopBar workspace trigger needed to prove the top bar was interactive.\n"
            f"Observed shell window:\n{json.dumps(observation, indent=2)}",
        )
    if not bool(observation["branding_visible"]):
        raise AssertionError(
            "Step 4 failed: the timeout-window shell snapshot did not expose the "
            "visible TrackState branding text.\n"
            f"Observed shell window:\n{json.dumps(observation, indent=2)}",
        )
    startup_buttons = set(observation["startup_observation"]["button_labels"])
    if startup_buttons == {"Sync issue"}:
        raise AssertionError(
            "Step 4 failed: after waiting past the startup timeout, the page still "
            "looked like the startup loading surface instead of the "
            "interactive shell.\n"
            f"Observed shell window:\n{json.dumps(observation, indent=2)}",
        )


def _snippet(text: str, *, limit: int = 240) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit].rstrip()}..."


def _record_step(
    result: dict[str, Any],
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
    result: dict[str, Any],
    *,
    check: str,
    observed: str,
) -> None:
    checks = result.setdefault("human_verification", [])
    assert isinstance(checks, list)
    checks.append({"check": check, "observed": observed})


def _record_not_reached_steps(
    result: dict[str, Any],
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
            status="failed",
            action=REQUEST_STEPS[step_number - 1],
            observed=f"Not reached because step {starting_step - 1} failed.",
        )


def _write_pass_outputs(result: dict[str, Any]) -> None:
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


def _write_failure_outputs(result: dict[str, Any]) -> None:
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


def _build_jira_comment(result: dict[str, Any], *, passed: bool) -> str:
    status_icon = "✅" if passed else "❌"
    status_word = "PASSED" if passed else "FAILED"
    lines = [
        f"h3. {status_icon} Automated test {status_word} — {TICKET_KEY}",
        "",
        f"*Test case*: {TEST_CASE_TITLE}",
        f"*Environment*: URL={result.get('app_url')} | Browser={result.get('browser')} | OS={result.get('os')}",
        f"*Viewport*: {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
        f"*Linked bugs considered*: {', '.join(LINKED_BUGS)}",
        f"*Observed timeout window*: {TIMEOUT_ASSERTION_SECONDS} seconds against a synthetic {SIMULATED_SYNC_DELAY_SECONDS}-second delayed `/user` startup probe",
        "",
        "h4. What was automated",
        "* Preloaded local and hosted workspace profiles plus a stored GitHub token for the deployed app.",
        "* Delayed the initial GitHub {/user} startup probe for 31 seconds so the startup synchronization path stayed pending beyond the explicit 11-second timeout.",
        "* Waited through the 11-second timeout before asserting so the test proved the deployed fallback behavior instead of checking too early.",
        "* Verified the live page showed shell navigation, a TopBar workspace trigger, and TrackState branding instead of remaining on the startup loading surface.",
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


def _build_pr_body(result: dict[str, Any], *, passed: bool) -> str:
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
        f"**Observed timeout window:** `{TIMEOUT_ASSERTION_SECONDS}` seconds against a synthetic `{SIMULATED_SYNC_DELAY_SECONDS}`-second delayed `/user` startup probe",
        "",
        "## What was automated",
        "- Preloaded local and hosted workspace profiles plus a stored GitHub token for the deployed app.",
        "- Delayed the initial GitHub `/user` startup probe for 31 seconds so the startup synchronization path stayed pending beyond the explicit 11-second timeout.",
        "- Waited through the 11-second timeout before asserting so the test proved the deployed fallback behavior instead of checking immediately.",
        "- Verified the live page showed shell navigation, a TopBar workspace trigger, and TrackState branding instead of remaining on the startup loading surface.",
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


def _build_response_summary(result: dict[str, Any], *, passed: bool) -> str:
    if passed:
        return (
            f"{TICKET_KEY} passed.\n\n"
            f"{REWORK_SUMMARY}\n\n"
            "The delayed startup probe stayed pending past the 11-second timeout, but "
            "the deployed app still reached shell_ready and exposed the interactive "
            "shell, TopBar workspace trigger, and TrackState branding.\n"
        )
    return (
        f"{TICKET_KEY} failed.\n\n"
        f"{REWORK_SUMMARY}\n\n"
        f"{result.get('error', 'The deployed app did not prove the non-blocking startup timeout behavior.')}\n"
    )


def _build_bug_description(result: dict[str, Any]) -> str:
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
        "## Actual vs Expected",
        f"- **Expected:** {EXPECTED_RESULT}",
        f"- **Actual:** {_actual_result_summary(result, passed=False)}",
        "",
        "## Environment details",
        f"- URL: {result.get('app_url')}",
        f"- Browser: {result.get('browser')}",
        f"- OS: {result.get('os')}",
        f"- Viewport: {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
        f"- Repository: {result.get('repository')} @ {result.get('repository_ref')}",
        f"- Run command: `{RUN_COMMAND}`",
        f"- Simulated delayed startup probe: GitHub `/user` delayed by {SIMULATED_SYNC_DELAY_SECONDS} seconds",
        f"- Timeout assertion window: {TIMEOUT_ASSERTION_SECONDS} seconds",
        "",
        "## Screenshots or logs",
        f"- GitHub requests seen: `{json.dumps(result.get('github_request_urls', []), ensure_ascii=True)}`",
        f"- Delayed requests seen: `{json.dumps(result.get('delayed_request_urls', []), ensure_ascii=True)}`",
        f"- Timeout window observation: `{json.dumps(result.get('timeout_window_observation'), ensure_ascii=True)}`",
    ]
    if result.get("screenshot"):
        lines.append(f"- Screenshot: `{result['screenshot']}`")
    return "\n".join(lines) + "\n"


def _actual_result_summary(result: dict[str, Any], *, passed: bool) -> str:
    if passed:
        return (
            "After waiting past the startup timeout while the delayed `/user` probe was "
            "still pending, the deployed app exposed the full shell navigation, "
            "TopBar workspace trigger, and visible TrackState branding instead of "
            "staying on the startup loading surface."
        )
    return str(
        result.get(
            "error",
            "The deployed app did not prove the non-blocking startup timeout behavior.",
        ),
    )


def _step_lines(result: dict[str, Any], *, jira: bool) -> list[str]:
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


def _human_lines(result: dict[str, Any], *, jira: bool) -> list[str]:
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
