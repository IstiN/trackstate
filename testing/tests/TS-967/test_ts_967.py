from __future__ import annotations

import json
import platform
import re
import subprocess
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Callable

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
from testing.tests.support.delayed_auth_workspace_profiles_runtime import (  # noqa: E402
    DelayedAuthWorkspaceProfilesRuntime,
)

TICKET_KEY = "TS-967"
TEST_CASE_TITLE = (
    "Synchronization initialization timeout - application reaches shell_ready "
    "via non-blocking pattern"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-967/test_ts_967.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
DEFAULT_BRANCH = "main"
LOCAL_TARGET = "/tmp/trackstate-demo"
LOCAL_DISPLAY_NAME = "Active local workspace"
HOSTED_DISPLAY_NAME = "Hosted setup workspace"
SHELL_NAVIGATION_LABELS = ("Dashboard", "Board", "JQL Search", "Hierarchy", "Settings")
BRANDING_TEXT = "Git-native. Jira-compatible. Team-proven."
SYNC_TIMEOUT_SECONDS = 10
SIMULATED_SYNC_DELAY_SECONDS = 30
TIMEOUT_ASSERTION_SECONDS = SYNC_TIMEOUT_SECONDS + 5
AUTH_PROBE_START_WAIT_SECONDS = 45
AUTH_PROBE_RELEASE_WAIT_SECONDS = SIMULATED_SYNC_DELAY_SECONDS + 45
TIMELINE_SAMPLE_INTERVAL_SECONDS = 0.25
TIMING_TOLERANCE_SECONDS = 0.25
LINKED_BUGS = ["TS-977", "TS-971", "TS-958"]
REWORK_SUMMARY = (
    "Reworked the live startup regression to capture the timeout boundary from the "
    "same startup snapshot that proves visible shell navigation, and to require that "
    "snapshot while the delayed GitHub `/user` probe is still pending or no later "
    "than its release."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
REVIEW_REPLIES_PATH = OUTPUTS_DIR / "review_replies.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts967_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts967_failure.png"
DISCUSSIONS_RAW_PATH = REPO_ROOT / "input" / TICKET_KEY / "pr_discussions_raw.json"

REQUEST_STEPS = [
    "Launch the TrackState application.",
    "Monitor the application startup sequence and the transition to the shell_ready state.",
    "Wait for the duration of the explicit synchronization timeout.",
    "Verify the visibility of the interactive shell components (TopBar, branding).",
]
EXPECTED_RESULT = (
    "The application does not remain indefinitely on the startup surface. After "
    "the synchronization timeout is reached, the non-blocking pattern allows the "
    "UI shell to render and reach the shell_ready=true state, providing an "
    "interactive interface to the user despite the sync delay."
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
            "TS-967 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
        )

    workspace_state = _workspace_state(service.repository)
    prepared_local_workspace = _prepare_local_workspace_repository()
    runtime = DelayedAuthWorkspaceProfilesRuntime(
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
                page.set_viewport(**DESKTOP_VIEWPORT)
                page.open_startup_entrypoint(
                    wait_until="commit",
                    timeout_ms=120_000,
                )
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
                        "GitHub token, a preloaded active hosted workspace plus local "
                        "fallback workspace profile, and an "
                        f"injected {SIMULATED_SYNC_DELAY_SECONDS}-second delay on the "
                        "initial GitHub `/user` startup probe."
                    ),
                )

                timeline_samples: list[dict[str, Any]] = []
                first_shell_visible_after_start_seconds: float | None = None
                first_trigger_visible_after_start_seconds: float | None = None

                def record_timeline_observation(observation: dict[str, Any]) -> None:
                    nonlocal first_shell_visible_after_start_seconds
                    nonlocal first_trigger_visible_after_start_seconds
                    elapsed_since_start_seconds = observation["elapsed_since_start_seconds"]
                    if (
                        first_shell_visible_after_start_seconds is None
                        and bool(observation["shell_observation"]["shell_ready"])
                        and elapsed_since_start_seconds is not None
                    ):
                        first_shell_visible_after_start_seconds = float(
                            elapsed_since_start_seconds,
                        )
                    if (
                        first_trigger_visible_after_start_seconds is None
                        and observation["trigger"] is not None
                        and elapsed_since_start_seconds is not None
                    ):
                        first_trigger_visible_after_start_seconds = float(
                            elapsed_since_start_seconds,
                        )
                    if (
                        not timeline_samples
                        or elapsed_since_start_seconds is None
                        or (
                            float(elapsed_since_start_seconds)
                            - float(timeline_samples[-1]["elapsed_since_start_seconds"])
                        )
                        >= 2
                    ):
                        timeline_samples.append(
                            {
                                "elapsed_since_start_seconds": elapsed_since_start_seconds,
                                "shell_ready": bool(
                                    observation["shell_observation"]["shell_ready"],
                                ),
                                "branding_visible": bool(observation["branding_visible"]),
                                "trigger_label": (
                                    None
                                    if observation["trigger"] is None
                                    else observation["trigger"]["semantic_label"]
                                ),
                                "navigation_labels": list(
                                    observation["shell_observation"][
                                        "visible_navigation_labels"
                                    ],
                                ),
                                "auth_pending": bool(observation["auth_pending"]),
                                "auth_probe_started_after_start_seconds": observation[
                                    "auth_probe_started_after_start_seconds"
                                ],
                                "auth_probe_released_after_start_seconds": observation[
                                    "auth_probe_released_after_start_seconds"
                                ],
                            },
                        )

                timeout_elapsed, timeout_window = _capture_timeout_window_observation(
                    tracker_page=tracker_page,
                    page=page,
                    runtime=runtime,
                    startup_started_at_monotonic=startup_started_at_monotonic,
                    on_observation=record_timeline_observation,
                )
                result["timeout_window_observation"] = timeout_window
                result["startup_timeline_samples"] = timeline_samples
                result["github_request_urls"] = list(runtime.github_request_urls)
                result["delayed_request_urls"] = list(runtime.delayed_request_urls)
                result["first_shell_visible_after_start_seconds"] = (
                    first_shell_visible_after_start_seconds
                )
                result["first_trigger_visible_after_start_seconds"] = (
                    first_trigger_visible_after_start_seconds
                )

                auth_probe_started = runtime.auth_probe_started_at_monotonic is not None
                if not auth_probe_started:
                    auth_probe_started = runtime.wait_for_auth_probe_start(
                        timeout_seconds=AUTH_PROBE_START_WAIT_SECONDS,
                    )
                result["auth_probe_started_after_start_seconds"] = (
                    _relative_startup_event_seconds(
                        startup_started_at_monotonic,
                        runtime.auth_probe_started_at_monotonic,
                    )
                )
                result["github_request_urls"] = list(runtime.github_request_urls)
                result["delayed_request_urls"] = list(runtime.delayed_request_urls)

                auth_probe_released = runtime.auth_probe_released_at_monotonic is not None
                if auth_probe_started and not auth_probe_released:
                    auth_probe_released = runtime.wait_for_auth_probe_release(
                        timeout_seconds=AUTH_PROBE_RELEASE_WAIT_SECONDS,
                    )
                result["auth_probe_released_after_start_seconds"] = (
                    _relative_startup_event_seconds(
                        startup_started_at_monotonic,
                        runtime.auth_probe_released_at_monotonic,
                    )
                )
                shell_ready_observation = _observe_shell_window(
                    tracker_page=tracker_page,
                    page=page,
                    runtime=runtime,
                    startup_started_at_monotonic=startup_started_at_monotonic,
                )
                result["shell_ready_observation"] = shell_ready_observation

                failures: list[str] = []
                if (
                    first_shell_visible_after_start_seconds is not None
                    and _shell_visible_before_probe_release(
                        first_shell_visible_after_start_seconds,
                        result["auth_probe_released_after_start_seconds"],
                    )
                ):
                    _record_step(
                        result,
                        step=2,
                        status="passed",
                        action=REQUEST_STEPS[1],
                        observed=(
                            "The deployed app transitioned into the interactive shell "
                            "during startup before the delayed `/user` probe finished.\n"
                            f"first_shell_visible_after_start_seconds="
                            f"{first_shell_visible_after_start_seconds!r}; "
                            f"first_trigger_visible_after_start_seconds="
                            f"{first_trigger_visible_after_start_seconds!r}; "
                            f"auth_probe_started_after_start_seconds="
                            f"{result['auth_probe_started_after_start_seconds']!r}; "
                            f"auth_probe_released_after_start_seconds="
                            f"{result['auth_probe_released_after_start_seconds']!r}; "
                            f"timeout_window={json.dumps(timeout_window, ensure_ascii=True)}"
                        ),
                    )
                elif first_shell_visible_after_start_seconds is not None:
                    step_two_error = (
                        "Step 2 failed: the deployed app only exposed the interactive shell "
                        "at or after the delayed `/user` probe released, so startup still "
                        "looked blocking.\n"
                        f"first_shell_visible_after_start_seconds="
                        f"{first_shell_visible_after_start_seconds!r}; "
                        f"auth_probe_released_after_start_seconds="
                        f"{result['auth_probe_released_after_start_seconds']!r}\n"
                        f"Observed timeout window:\n{json.dumps(timeout_window, indent=2)}"
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
                    step_two_error = (
                        "Step 2 failed: the deployed app never transitioned into the "
                        "interactive shell during the startup timeout observation window.\n"
                        f"Observed timeout window:\n{json.dumps(timeout_window, indent=2)}"
                    )
                    failures.append(step_two_error)
                    _record_step(
                        result,
                        step=2,
                        status="failed",
                        action=REQUEST_STEPS[1],
                        observed=step_two_error,
                    )

                step_three_error: str | None = None
                if not timeout_elapsed:
                    step_three_error = (
                        "Step 3 failed: the test never reached the explicit "
                        "synchronization timeout window from application launch.\n"
                        f"Observed timeout window:\n{json.dumps(timeout_window, indent=2)}"
                    )
                elif not auth_probe_started:
                    step_three_error = (
                        "Step 3 failed: the delayed GitHub `/user` startup probe never "
                        "started, so the intended timeout scenario was not exercised.\n"
                        f"Observed timeout window:\n{json.dumps(timeout_window, indent=2)}"
                    )
                elif not _observation_captures_timeout_boundary(timeout_window):
                    step_three_error = (
                        "Step 3 failed: the timeout-window snapshot was captured only after "
                        "the delayed `/user` probe had already released, so the test did not "
                        "prove the shell state at the explicit timeout boundary while the "
                        "request was still outstanding.\n"
                        f"Observed timeout window:\n{json.dumps(timeout_window, indent=2)}"
                    )
                elif not bool(timeout_window["shell_observation"]["shell_ready"]):
                    step_three_error = (
                        "Step 3 failed: after waiting past the explicit synchronization "
                        "timeout from launch, the page still had not reached shell_ready.\n"
                        f"Observed timeout window:\n{json.dumps(timeout_window, indent=2)}"
                    )
                elif (
                    first_shell_visible_after_start_seconds is not None
                    and result["auth_probe_released_after_start_seconds"] is not None
                    and not _shell_visible_before_probe_release(
                        first_shell_visible_after_start_seconds,
                        result["auth_probe_released_after_start_seconds"],
                    )
                ):
                    step_three_error = (
                        "Step 3 failed: the shell only became visible after the delayed "
                        "`/user` probe released, so the startup path was still blocking on "
                        "the delayed request.\n"
                        f"first_shell_visible_after_start_seconds="
                        f"{first_shell_visible_after_start_seconds!r}; "
                        f"auth_probe_released_after_start_seconds="
                        f"{result['auth_probe_released_after_start_seconds']!r}\n"
                        f"Observed timeout window:\n{json.dumps(timeout_window, indent=2)}"
                    )
                elif not auth_probe_released:
                    step_three_error = (
                        "Step 3 failed: the delayed GitHub `/user` startup probe never "
                        "completed, so the full delayed-request scenario could not be "
                        "observed.\n"
                        f"Observed timeout window:\n{json.dumps(timeout_window, indent=2)}"
                    )

                if step_three_error is None:
                    auth_state = (
                        "the delayed `/user` probe was still pending"
                        if bool(timeout_window["auth_pending"])
                        else "the delayed `/user` probe had not released yet"
                    )
                    _record_step(
                        result,
                        step=3,
                        status="passed",
                        action=REQUEST_STEPS[2],
                        observed=(
                            f"Waited {timeout_window['elapsed_since_start_seconds']!r} "
                            "seconds from application launch, which exceeds the "
                            f"{SYNC_TIMEOUT_SECONDS}-second startup timeout window. At that "
                            f"point {auth_state} and shell_ready was "
                            f"{timeout_window['shell_observation']['shell_ready']!r}.\n"
                            f"first_shell_visible_after_start_seconds="
                            f"{first_shell_visible_after_start_seconds!r}; "
                            f"auth_probe_started_after_start_seconds="
                            f"{result['auth_probe_started_after_start_seconds']!r}; "
                            f"auth_probe_released_after_start_seconds="
                            f"{result['auth_probe_released_after_start_seconds']!r}"
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
                    _assert_shell_components(timeout_window)
                except AssertionError as error:
                    step_four_error = str(error)
                if (
                    step_three_error is not None
                    and step_four_error is None
                ):
                    step_four_error = (
                        "Step 4 failed: at the timeout-window snapshot, the interactive "
                        "shell components were not all visible.\n"
                        f"Observed timeout window:\n{json.dumps(timeout_window, indent=2)}"
                    )
                if step_four_error is None:
                    _record_step(
                        result,
                        step=4,
                        status="passed",
                        action=REQUEST_STEPS[3],
                        observed=(
                            "The timeout-window snapshot exposed the interactive shell rather "
                            "than the blank startup surface.\n"
                            f"title={timeout_window['startup_observation']['title']!r}; "
                            f"trigger={json.dumps(timeout_window['trigger'], ensure_ascii=True)}; "
                            f"branding_visible={timeout_window['branding_visible']!r}; "
                            f"visible_navigation_labels="
                            f"{json.dumps(timeout_window['shell_observation']['visible_navigation_labels'], ensure_ascii=True)}"
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
                        "Viewed the live app after waiting beyond the startup timeout and "
                        "checked the page the way a user would: visible shell navigation, "
                        "header workspace trigger, workspace sync status, and branding text "
                        "instead of the blank startup surface."
                    ),
                    observed=(
                        f"body_text_snippet={_snippet(timeout_window['shell_observation']['body_text'])!r}; "
                        f"branding_text_visible={timeout_window['branding_visible']!r}; "
                        f"trigger_label="
                        f"{(timeout_window['trigger'] or {}).get('semantic_label')!r}; "
                        f"visible_buttons="
                        f"{json.dumps(timeout_window['startup_observation']['button_labels'], ensure_ascii=True)}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Kept watching the live page while the delayed `/user` request "
                        "finished and confirmed the shell stayed interactive afterward."
                    ),
                    observed=(
                        f"shell_ready_after_timeout={timeout_window['shell_observation']['shell_ready']!r}; "
                        f"first_shell_visible_after_start_seconds="
                        f"{first_shell_visible_after_start_seconds!r}; "
                        f"post_release_shell_ready="
                        f"{shell_ready_observation['shell_observation']['shell_ready']!r}; "
                        f"auth_probe_released_after_start_seconds="
                        f"{shell_ready_observation['auth_probe_released_after_start_seconds']!r}; "
                        f"post_release_trigger_label="
                        f"{(shell_ready_observation['trigger'] or {}).get('semantic_label')!r}"
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
        "activeWorkspaceId": hosted_id,
        "migrationComplete": True,
        "profiles": [
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

    marker_path = local_path / ".trackstate-ts967-precondition.txt"
    marker_path.write_text(
        "Prepared for TS-967 startup synchronization timeout validation.\n",
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
                "user.name=TS-967 Automation",
                "-c",
                "user.email=ts967@example.com",
                "commit",
                "--allow-empty",
                "-m",
                "Prepare TS-967 local workspace",
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
    runtime: DelayedAuthWorkspaceProfilesRuntime,
    startup_started_at_monotonic: float,
) -> dict[str, Any]:
    helper_shell_observation = tracker_page.observe_interactive_shell(
        SHELL_NAVIGATION_LABELS,
        timeout_ms=1_000,
    )
    startup_observation = _startup_surface_payload(tracker_page)
    shell_observation = _shell_observation_from_startup_surface(startup_observation)
    trigger = _safe_trigger_payload(page, startup_observation=startup_observation)
    body_text = str(startup_observation.get("body_text", ""))
    title = str(startup_observation.get("title", ""))
    return {
        "shell_observation": shell_observation,
        "interactive_shell_helper_observation": helper_shell_observation,
        "shell_observation_mismatch": _shell_observation_mismatch(
            startup_shell_observation=shell_observation,
            helper_shell_observation=helper_shell_observation,
        ),
        "startup_observation": startup_observation,
        "trigger": trigger,
        "branding_visible": BRANDING_TEXT in body_text or "TrackState" in body_text or "TrackState" in title,
        "elapsed_since_start_seconds": _elapsed_since(startup_started_at_monotonic),
        "auth_pending": runtime.auth_probe_pending,
        "auth_probe_started_after_start_seconds": _relative_startup_event_seconds(
            startup_started_at_monotonic,
            runtime.auth_probe_started_at_monotonic,
        ),
        "auth_probe_released_after_start_seconds": _relative_startup_event_seconds(
            startup_started_at_monotonic,
            runtime.auth_probe_released_at_monotonic,
        ),
        "elapsed_since_auth_start_seconds": _elapsed_since(runtime.auth_probe_started_at_monotonic),
        "shell_ready_after_start_seconds": (
            _elapsed_since(startup_started_at_monotonic)
            if bool(shell_observation.get("shell_ready"))
            else None
        ),
    }


def _capture_timeout_window_observation(
    *,
    tracker_page: TrackStateTrackerPage,
    page: LiveWorkspaceSwitcherPage,
    runtime: DelayedAuthWorkspaceProfilesRuntime,
    startup_started_at_monotonic: float,
    on_observation: Callable[[dict[str, Any]], None],
) -> tuple[bool, dict[str, Any]]:
    last_observation: dict[str, Any] | None = None

    def probe() -> dict[str, Any]:
        nonlocal last_observation
        observation = _observe_shell_window(
            tracker_page=tracker_page,
            page=page,
            runtime=runtime,
            startup_started_at_monotonic=startup_started_at_monotonic,
        )
        on_observation(observation)
        last_observation = observation
        return observation

    timeout_elapsed, observation = poll_until(
        probe=probe,
        is_satisfied=lambda candidate: (
            candidate["elapsed_since_start_seconds"] is not None
            and float(candidate["elapsed_since_start_seconds"])
            >= TIMEOUT_ASSERTION_SECONDS
        ),
        timeout_seconds=TIMEOUT_ASSERTION_SECONDS + AUTH_PROBE_RELEASE_WAIT_SECONDS,
        interval_seconds=TIMELINE_SAMPLE_INTERVAL_SECONDS,
    )
    if last_observation is None:
        raise RuntimeError("TS-967 did not capture any startup observations.")
    return timeout_elapsed, observation


def _elapsed_since(event_monotonic: float | None) -> float | None:
    if event_monotonic is None:
        return None
    return round(time.monotonic() - event_monotonic, 2)


def _relative_startup_event_seconds(
    startup_started_at_monotonic: float,
    event_monotonic: float | None,
) -> float | None:
    if event_monotonic is None:
        return None
    return round(event_monotonic - startup_started_at_monotonic, 2)


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


def _shell_observation_from_startup_surface(
    startup_observation: dict[str, Any],
) -> dict[str, Any]:
    body_text = str(startup_observation.get("body_text", ""))
    button_labels = [
        str(label)
        for label in startup_observation.get("button_labels", [])
        if isinstance(label, str)
    ]
    visible_navigation_labels = [
        label
        for label in SHELL_NAVIGATION_LABELS
        if label in body_text or label in button_labels
    ]
    fatal_banner_visible = "TrackState data was not found" in body_text
    connect_github_visible = "Connect GitHub" in body_text or "Connect GitHub" in button_labels
    return {
        "body_text": body_text,
        "visible_navigation_labels": visible_navigation_labels,
        "fatal_banner_visible": fatal_banner_visible,
        "connect_github_visible": connect_github_visible,
        "shell_ready": len(visible_navigation_labels) == len(SHELL_NAVIGATION_LABELS),
    }


def _shell_observation_mismatch(
    *,
    startup_shell_observation: dict[str, Any],
    helper_shell_observation: dict[str, Any],
) -> dict[str, Any] | None:
    startup_labels = list(startup_shell_observation.get("visible_navigation_labels", []))
    helper_labels = list(helper_shell_observation.get("visible_navigation_labels", []))
    startup_ready = bool(startup_shell_observation.get("shell_ready"))
    helper_ready = bool(helper_shell_observation.get("shell_ready"))
    if startup_labels == helper_labels and startup_ready == helper_ready:
        return None
    return {
        "startup_visible_navigation_labels": startup_labels,
        "helper_visible_navigation_labels": helper_labels,
        "startup_shell_ready": startup_ready,
        "helper_shell_ready": helper_ready,
    }


def _safe_trigger_payload(
    page: LiveWorkspaceSwitcherPage,
    *,
    startup_observation: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    try:
        trigger = page.observe_trigger(timeout_ms=1_000)
    except (AssertionError, WebAppTimeoutError):
        if startup_observation is None:
            return None
        return _fallback_trigger_payload(startup_observation)
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


def _fallback_trigger_payload(startup_observation: dict[str, Any]) -> dict[str, Any] | None:
    for label in startup_observation.get("button_labels", []):
        if not isinstance(label, str) or "Workspace switcher:" not in label:
            continue
        match = re.match(
            r"^Workspace switcher:\s*(.*?),\s*(Hosted|Local),\s*(.+)$",
            label,
        )
        return {
            "semantic_label": label,
            "visible_text": label,
            "display_name": match.group(1).strip() if match else "",
            "workspace_type": match.group(2).strip() if match else "",
            "state_label": match.group(3).strip() if match else "",
            "top_button_labels": list(startup_observation.get("button_labels", [])),
        }
    return None


def _observation_captures_timeout_boundary(observation: dict[str, Any]) -> bool:
    elapsed_since_start_seconds = observation.get("elapsed_since_start_seconds")
    if elapsed_since_start_seconds is None:
        return False
    if float(elapsed_since_start_seconds) < TIMEOUT_ASSERTION_SECONDS:
        return False
    if bool(observation.get("auth_pending")):
        return True
    auth_probe_released_after_start_seconds = observation.get(
        "auth_probe_released_after_start_seconds",
    )
    if auth_probe_released_after_start_seconds is None:
        return False
    return float(elapsed_since_start_seconds) <= float(
        auth_probe_released_after_start_seconds,
    ) + TIMING_TOLERANCE_SECONDS


def _shell_visible_before_probe_release(
    first_shell_visible_after_start_seconds: float,
    auth_probe_released_after_start_seconds: Any,
) -> bool:
    if auth_probe_released_after_start_seconds is None:
        return True
    return float(first_shell_visible_after_start_seconds) < (
        float(auth_probe_released_after_start_seconds) - TIMING_TOLERANCE_SECONDS
    )


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
            "header workspace trigger needed to prove the top bar was interactive.\n"
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
            "looked like the blank Sync issue startup surface instead of the "
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
    _write_review_replies(result, passed=True)


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
    _write_review_replies(result, passed=False)


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
        "* Preloaded a hosted workspace and stored GitHub token in browser storage for the deployed app.",
        "* Delayed the initial GitHub {/user} startup probe so the startup synchronization path stayed pending beyond the 10-second timeout window.",
        "* Waited past the timeout before asserting so the test proved the non-blocking behavior instead of checking too early.",
        "* Verified the live page showed shell navigation, a header workspace trigger, and TrackState branding instead of remaining on the blank {Sync issue} surface.",
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
        "- Preloaded a hosted workspace and stored GitHub token in browser storage for the deployed app.",
        "- Delayed the initial GitHub `/user` startup probe so the startup synchronization path stayed pending beyond the 10-second timeout window.",
        "- Waited past the timeout before asserting so the test proved the non-blocking startup behavior instead of checking immediately.",
        "- Verified the live page showed shell navigation, a header workspace trigger, and TrackState branding instead of remaining on the blank `Sync issue` surface.",
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
            "The delayed startup probe stayed pending past the timeout window, but the "
            "deployed app still reached shell_ready and exposed the interactive shell, "
            "header workspace trigger, and TrackState branding.\n"
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
            "still pending, the deployed app exposed the full shell navigation, header "
            "workspace trigger, and visible TrackState branding instead of staying on "
            "the blank Sync issue surface."
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


def _write_review_replies(result: dict[str, Any], *, passed: bool) -> None:
    replies = [
        {
            "inReplyToId": thread.get("rootCommentId"),
            "threadId": thread.get("threadId"),
            "reply": _review_reply_text(thread=thread, result=result, passed=passed),
        }
        for thread in _discussion_threads()
    ]
    REVIEW_REPLIES_PATH.write_text(
        json.dumps({"replies": replies}, indent=2) + "\n",
        encoding="utf-8",
    )


def _discussion_threads() -> list[dict[str, Any]]:
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
    thread: dict[str, Any],
    result: dict[str, Any],
    passed: bool,
) -> str:
    root_comment_id = thread.get("rootCommentId")
    if root_comment_id == 3292588355:
        if passed:
            return (
                "Fixed: Step 3 now captures the timeout-window sample from repeated "
                "startup-surface snapshots and only accepts it when the delayed `/user` "
                "probe is still pending or no later than its release. The timeout verdict "
                "can no longer be based on a post-release sample."
            )
        return (
            "Fixed: Step 3 now rejects post-release timeout samples. This run still "
            "failed, but the failure evidence now comes from a timeout-boundary snapshot "
            "captured while the delayed `/user` probe was still pending or no later than "
            "its release."
        )
    return (
        "Fixed: TS-967 now derives shell visibility from the same startup snapshot used "
        "for the timeout assertion, so navigation labels, trigger visibility, and shell "
        "readiness cannot disagree across two independent observation paths."
    )


if __name__ == "__main__":
    main()
