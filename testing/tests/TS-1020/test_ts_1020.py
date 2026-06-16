from __future__ import annotations

import json
import platform
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
)
from testing.components.pages.trackstate_tracker_page import TrackStateTrackerPage  # noqa: E402
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.utils.polling import poll_until  # noqa: E402
from testing.tests.support.live_startup_case_support import (  # noqa: E402
    ShellReadyTransitionTracker,
    build_annotated_steps,
    build_workspace_state,
    format_human_lines,
    format_step_lines,
    observe_live_startup_shell_window,
    prepare_local_workspace_repository,
    record_human_verification,
    record_not_reached_steps,
    record_step,
    snippet,
    startup_surface_payload,
    write_test_automation_result,
)
from testing.tests.support.ts984_delayed_auth_probe_runtime import (  # noqa: E402
    Ts984DelayedAuthProbeRuntime,
)

TICKET_KEY = "TS-1020"
TEST_CASE_TITLE = (
    "Application state machine — Interactive transition waits for startup guards"
)
TEST_FILE_PATH = "testing/tests/TS-1020/test_ts_1020.py"
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-1020/test_ts_1020.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
DEFAULT_BRANCH = "main"
LOCAL_TARGET = "/tmp/trackstate-ts1020-demo"
LOCAL_DISPLAY_NAME = "Guarded local workspace"
HOSTED_DISPLAY_NAME = "Hosted setup workspace"
SHELL_NAVIGATION_LABELS = ("Dashboard", "Board", "JQL Search", "Hierarchy", "Settings")
BRANDING_TEXT = "Git-native. Jira-compatible. Team-proven."
FULL_SYNC_TIMEOUT_SECONDS = 11
SIMULATED_PROBE_DELAY_SECONDS = 5
AUTH_PROBE_START_WAIT_SECONDS = 30
SHELL_READY_WAIT_SECONDS = FULL_SYNC_TIMEOUT_SECONDS + SIMULATED_PROBE_DELAY_SECONDS + 8
MAX_READY_AFTER_RELEASE_SECONDS = 4.0
POLL_INTERVAL_SECONDS = 0.25
LINKED_BUG_KEYS = ("TS-1014",)
LINKED_BUG_NOTES = (
    "Reviewed TS-1014. The fix restored the successful delayed GitHub `/user` "
    "startup-probe path, so this test keeps the probe pending for 5 seconds and "
    "waits through that full window before asserting the app can enter the "
    "interactive shell."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
PENDING_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1020_pending.png"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1020_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1020_failure.png"

REQUEST_STEPS = [
    "Launch the TrackState application.",
    "Monitor the application lifecycle state or `shell_ready` flag immediately after the bundle loads.",
    "Observe the state transition timing relative to the probe resolution.",
]
EXPECTED_RESULT = (
    "The application state remains in `Initializing` or `Loading` and does not "
    "transition to `Interactive` (`shell_ready=true`) until the startup probe "
    "successfully returns, confirming the state machine enforces the lifecycle guards."
)


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    PENDING_SCREENSHOT_PATH.unlink(missing_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-1020 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
        )

    workspace_state = _workspace_state(service.repository)
    prepared_local_workspace = _prepare_local_workspace_repository()
    runtime = Ts984DelayedAuthProbeRuntime(
        repository=config.repository,
        token=token,
        workspace_state=workspace_state,
        auth_delay_seconds=SIMULATED_PROBE_DELAY_SECONDS,
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
        "full_sync_timeout_seconds": FULL_SYNC_TIMEOUT_SECONDS,
        "simulated_probe_delay_seconds": SIMULATED_PROBE_DELAY_SECONDS,
        "max_ready_after_release_seconds": MAX_READY_AFTER_RELEASE_SECONDS,
        "linked_bug_notes": LINKED_BUG_NOTES,
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
                tracker_page.screenshot(str(PENDING_SCREENSHOT_PATH))
                result["pending_screenshot"] = str(PENDING_SCREENSHOT_PATH)

                transition_tracker = ShellReadyTransitionTracker()
                auth_probe_started = runtime.wait_for_auth_probe_start(
                    timeout_seconds=AUTH_PROBE_START_WAIT_SECONDS,
                )
                if not auth_probe_started:
                    _record_step(
                        result,
                        step=1,
                        status="failed",
                        action=REQUEST_STEPS[0],
                        observed=(
                            "The deployed app never started the delayed GitHub `/user` "
                            "startup probe required to observe the guarded startup path.\n"
                            f"Observed body text:\n{tracker_page.body_text()}"
                        ),
                    )
                    _record_not_reached_steps(result, starting_step=2)
                    raise AssertionError(
                        "Step 1 failed: the deployed app never started the delayed "
                        "GitHub `/user` startup probe needed for TS-1020.\n"
                        f"Observed body text:\n{tracker_page.body_text()}",
                    )

                result["initial_shell_probe_state"] = runtime.read_shell_probe_state()
                result["github_request_urls"] = list(runtime.github_request_urls)
                result["delayed_request_urls"] = list(runtime.delayed_request_urls)

                shell_ready, shell_window = poll_until(
                    probe=lambda: _observe_shell_window(
                        tracker_page=tracker_page,
                        page=page,
                        runtime=runtime,
                        startup_started_at_monotonic=startup_started_at_monotonic,
                        transition_tracker=transition_tracker,
                        poll_timeout_ms=250,
                    ),
                    is_satisfied=lambda observation: (
                        observation["auth_probe_started_after_start_seconds"] is not None
                        and observation["auth_probe_released_after_start_seconds"] is not None
                        and observation["shell_ready_after_start_seconds"] is not None
                        and not bool(observation["auth_pending"])
                    ),
                    timeout_seconds=SHELL_READY_WAIT_SECONDS,
                    interval_seconds=POLL_INTERVAL_SECONDS,
                )
                result["shell_window_observation"] = shell_window
                auth_probe_started_after_start_seconds = shell_window[
                    "auth_probe_started_after_start_seconds"
                ]
                auth_probe_released_after_start_seconds = shell_window[
                    "auth_probe_released_after_start_seconds"
                ]
                shell_ready_after_start_seconds = shell_window["shell_ready_after_start_seconds"]
                probe_recorded_shell_ready_after_start_seconds = shell_window[
                    "probe_recorded_shell_ready_after_start_seconds"
                ]
                authoritative_shell_ready_after_start_seconds = (
                    probe_recorded_shell_ready_after_start_seconds
                    if probe_recorded_shell_ready_after_start_seconds is not None
                    else shell_ready_after_start_seconds
                )
                authoritative_shell_ready_after_probe_release_seconds = (
                    None
                    if (
                        authoritative_shell_ready_after_start_seconds is None
                        or auth_probe_released_after_start_seconds is None
                    )
                    else round(
                        authoritative_shell_ready_after_start_seconds
                        - auth_probe_released_after_start_seconds,
                        2,
                    )
                )
                result["authoritative_shell_ready_after_start_seconds"] = (
                    authoritative_shell_ready_after_start_seconds
                )
                result["authoritative_shell_ready_after_probe_release_seconds"] = (
                    authoritative_shell_ready_after_probe_release_seconds
                )

                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=REQUEST_STEPS[0],
                    observed=(
                        "Opened the deployed TrackState app in Chromium with a stored "
                        "GitHub token, preloaded workspace state, and a synthetic "
                        f"{SIMULATED_PROBE_DELAY_SECONDS}-second delay on the GitHub "
                        "`/user` startup probe.\n"
                        f"auth_probe_started_after_start_seconds="
                        f"{auth_probe_started_after_start_seconds!r}; "
                        f"auth_probe_released_after_start_seconds="
                        f"{auth_probe_released_after_start_seconds!r}; "
                        f"delayed_request_urls={runtime.delayed_request_urls!r}"
                    ),
                )

                guard_failures = _guard_failures(
                    startup_observation_initial=result["startup_observation_initial"],
                    initial_shell_probe_state=result["initial_shell_probe_state"],
                    shell_window=shell_window,
                    auth_probe_released_after_start_seconds=auth_probe_released_after_start_seconds,
                    authoritative_shell_ready_after_start_seconds=(
                        authoritative_shell_ready_after_start_seconds
                    ),
                )
                if guard_failures:
                    observed = (
                        "The live startup guard did not keep the app out of the interactive "
                        "shell until the delayed probe resolved.\n"
                        f"initial_startup_body_excerpt="
                        f"{_snippet(result['startup_observation_initial']['body_text'])!r}; "
                        f"initial_button_labels="
                        f"{result['startup_observation_initial']['button_labels']!r}; "
                        f"initial_shell_probe_state="
                        f"{json.dumps(result['initial_shell_probe_state'], indent=2)}; "
                        f"authoritative_shell_ready_after_start_seconds="
                        f"{authoritative_shell_ready_after_start_seconds!r}; "
                        f"auth_probe_released_after_start_seconds="
                        f"{auth_probe_released_after_start_seconds!r}; "
                        f"visible_navigation_labels="
                        f"{shell_window['shell_observation']['visible_navigation_labels']!r}\n"
                        + "\n".join(guard_failures)
                    )
                    _record_step(
                        result,
                        step=2,
                        status="failed",
                        action=REQUEST_STEPS[1],
                        observed=observed,
                    )
                    _record_not_reached_steps(result, starting_step=3)
                    raise AssertionError(f"Step 2 failed: {observed}")

                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=REQUEST_STEPS[1],
                    observed=(
                        "The shell_ready probe stayed blocked through the guarded startup "
                        "window and did not report the interactive shell until after the "
                        "delayed startup probe resolved.\n"
                        f"initial_startup_body_excerpt="
                        f"{_snippet(result['startup_observation_initial']['body_text'])!r}; "
                        f"initial_button_labels="
                        f"{result['startup_observation_initial']['button_labels']!r}; "
                        f"first_shell_ready_after_start_seconds="
                        f"{authoritative_shell_ready_after_start_seconds!r}; "
                        f"auth_probe_released_after_start_seconds="
                        f"{auth_probe_released_after_start_seconds!r}"
                    ),
                )

                if not shell_ready:
                    observed = (
                        "The live app never exposed the interactive shell after the delayed "
                        "startup probe completed.\n"
                        f"Observed shell window:\n{json.dumps(shell_window, indent=2)}"
                    )
                    _record_step(
                        result,
                        step=3,
                        status="failed",
                        action=REQUEST_STEPS[2],
                        observed=observed,
                    )
                    raise AssertionError(f"Step 3 failed: {observed}")

                _assert_interactive_shell(shell_window)
                timing_failures = _timing_failures(
                    shell_window=shell_window,
                    auth_probe_released_after_start_seconds=auth_probe_released_after_start_seconds,
                    authoritative_shell_ready_after_start_seconds=(
                        authoritative_shell_ready_after_start_seconds
                    ),
                    authoritative_shell_ready_after_probe_release_seconds=(
                        authoritative_shell_ready_after_probe_release_seconds
                    ),
                )
                if timing_failures:
                    observed = (
                        "The startup guards eventually resolved, but the live app did not "
                        "prove the expected guarded transition into the interactive shell.\n"
                        f"shell_ready_after_start_seconds={shell_ready_after_start_seconds!r}; "
                        f"probe_recorded_shell_ready_after_start_seconds="
                        f"{probe_recorded_shell_ready_after_start_seconds!r}; "
                        f"authoritative_shell_ready_after_start_seconds="
                        f"{authoritative_shell_ready_after_start_seconds!r}; "
                        f"auth_probe_released_after_start_seconds="
                        f"{auth_probe_released_after_start_seconds!r}; "
                        f"authoritative_shell_ready_after_probe_release_seconds="
                        f"{authoritative_shell_ready_after_probe_release_seconds!r}; "
                        f"shell_ready_observed_while_auth_pending="
                        f"{shell_window['shell_ready_observed_while_auth_pending']!r}; "
                        f"visible_navigation_labels="
                        f"{shell_window['shell_observation']['visible_navigation_labels']!r}; "
                        f"trigger={(shell_window['trigger'] or {}).get('semantic_label')!r}; "
                        f"branding_visible={shell_window['branding_visible']!r}\n"
                        + "\n".join(timing_failures)
                    )
                    _record_step(
                        result,
                        step=3,
                        status="failed",
                        action=REQUEST_STEPS[2],
                        observed=observed,
                    )
                    raise AssertionError(f"Step 3 failed: {observed}")

                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action=REQUEST_STEPS[2],
                    observed=(
                        "The live app entered the interactive shell only after the delayed "
                        "startup probe resolved.\n"
                        f"authoritative_shell_ready_after_start_seconds="
                        f"{authoritative_shell_ready_after_start_seconds!r}; "
                        f"auth_probe_released_after_start_seconds="
                        f"{auth_probe_released_after_start_seconds!r}; "
                        f"authoritative_shell_ready_after_probe_release_seconds="
                        f"{authoritative_shell_ready_after_probe_release_seconds!r}; "
                        f"visible_navigation_labels="
                        f"{shell_window['shell_observation']['visible_navigation_labels']!r}; "
                        f"trigger={(shell_window['trigger'] or {}).get('semantic_label')!r}; "
                        f"branding_visible={shell_window['branding_visible']!r}"
                    ),
                )

                _record_human_verification(
                    result,
                    check=(
                        "Watched the live startup screen like a user and confirmed the app "
                        "did not start in the interactive shell before the delayed guard "
                        "finished."
                    ),
                    observed=(
                        f"body_excerpt={_snippet(result['startup_observation_initial']['body_text'])!r}; "
                        f"startup_button_labels="
                        f"{result['startup_observation_initial']['button_labels']!r}; "
                        f"first_shell_ready_after_start_seconds="
                        f"{authoritative_shell_ready_after_start_seconds!r}; "
                        f"auth_probe_released_after_start_seconds="
                        f"{auth_probe_released_after_start_seconds!r}; "
                        f"pending_screenshot={str(PENDING_SCREENSHOT_PATH)!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Watched the live page after the guard resolved and confirmed the "
                        "visible header, navigation, and TrackState branding appeared only "
                        "after the delayed probe completed."
                    ),
                    observed=(
                        f"body_excerpt={_snippet(shell_window['shell_observation']['body_text'])!r}; "
                        f"visible_navigation_labels="
                        f"{shell_window['shell_observation']['visible_navigation_labels']!r}; "
                        f"trigger_label={(shell_window['trigger'] or {}).get('semantic_label')!r}; "
                        f"branding_visible={shell_window['branding_visible']!r}"
                    ),
                )

                tracker_page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
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
        result["error"] = f"AssertionError: {error}"
        result["traceback"] = traceback.format_exc()
        _write_failure_outputs(result, product_bug=True)
        raise
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        _write_failure_outputs(result, product_bug=False)
        raise


def _workspace_state(repository: str) -> dict[str, object]:
    return build_workspace_state(
        repository,
        local_target=LOCAL_TARGET,
        default_branch=DEFAULT_BRANCH,
        local_display_name=LOCAL_DISPLAY_NAME,
        hosted_display_name=HOSTED_DISPLAY_NAME,
    )


def _prepare_local_workspace_repository() -> dict[str, object]:
    return prepare_local_workspace_repository(
        local_target=LOCAL_TARGET,
        default_branch=DEFAULT_BRANCH,
        marker_filename=".trackstate-ts1020-precondition.txt",
        marker_contents="Prepared for TS-1020 startup guard validation.\n",
        commit_author_name="TS-1020 Automation",
        commit_author_email="ts1020@example.com",
        commit_message="Prepare TS-1020 local workspace",
    )


def _observe_shell_window(
    *,
    tracker_page: TrackStateTrackerPage,
    page: LiveWorkspaceSwitcherPage,
    runtime: Ts984DelayedAuthProbeRuntime,
    startup_started_at_monotonic: float,
    transition_tracker: ShellReadyTransitionTracker | None = None,
    poll_timeout_ms: int = 1_000,
) -> dict[str, Any]:
    shell_window = observe_live_startup_shell_window(
        tracker_page=tracker_page,
        page=page,
        runtime=runtime,
        startup_started_at_monotonic=startup_started_at_monotonic,
        shell_navigation_labels=SHELL_NAVIGATION_LABELS,
        branding_texts=(BRANDING_TEXT, "TrackState.AI"),
        transition_tracker=transition_tracker,
        poll_timeout_ms=poll_timeout_ms,
    )
    shell_probe_state = runtime.read_shell_probe_state()
    shell_window["shell_probe_state"] = shell_probe_state
    shell_window["probe_recorded_shell_ready_after_start_seconds"] = shell_probe_state[
        "first_shell_ready_after_launch_seconds"
    ]
    return shell_window


def _guard_failures(
    *,
    startup_observation_initial: dict[str, Any],
    initial_shell_probe_state: dict[str, Any],
    shell_window: dict[str, Any],
    auth_probe_released_after_start_seconds: float | None,
    authoritative_shell_ready_after_start_seconds: float | None,
) -> list[str]:
    failures: list[str] = []
    initial_body_text = str(startup_observation_initial.get("body_text", ""))
    initial_navigation_visible = all(
        label in initial_body_text for label in SHELL_NAVIGATION_LABELS
    ) and "TrackState.AI" in initial_body_text
    if initial_navigation_visible:
        failures.append(
            "The initial startup snapshot already contained the full interactive shell "
            "immediately after launch."
        )
    if initial_shell_probe_state.get("first_shell_ready_after_launch_seconds") is not None:
        failures.append(
            "The page-side shell_ready probe had already recorded the interactive shell "
            "in the initial post-launch snapshot."
        )
    if authoritative_shell_ready_after_start_seconds is None:
        failures.append("The first authoritative shell_ready transition time was not recorded.")
    if auth_probe_released_after_start_seconds is None:
        failures.append("The delayed startup probe release time was not recorded.")
    if (
        authoritative_shell_ready_after_start_seconds is not None
        and auth_probe_released_after_start_seconds is not None
        and authoritative_shell_ready_after_start_seconds
        < auth_probe_released_after_start_seconds
    ):
        failures.append(
            "The first authoritative shell_ready transition happened before the delayed "
            "startup probe was released."
        )
    if bool(shell_window.get("shell_ready_observed_while_auth_pending")):
        failures.append(
            "The Python observer recorded shell_ready while the delayed startup guard "
            "was still pending."
        )
    return failures


def _timing_failures(
    *,
    shell_window: dict[str, Any],
    auth_probe_released_after_start_seconds: float | None,
    authoritative_shell_ready_after_start_seconds: float | None,
    authoritative_shell_ready_after_probe_release_seconds: float | None,
) -> list[str]:
    failures: list[str] = []
    auth_probe_release_after_auth_start_seconds = shell_window[
        "auth_probe_release_after_auth_start_seconds"
    ]
    if auth_probe_released_after_start_seconds is None:
        failures.append("The delayed startup probe release time could not be measured.")
    if authoritative_shell_ready_after_start_seconds is None:
        failures.append("The shell_ready transition time could not be measured.")
    if (
        auth_probe_release_after_auth_start_seconds is None
        or auth_probe_release_after_auth_start_seconds < SIMULATED_PROBE_DELAY_SECONDS - 0.5
    ):
        failures.append(
            "The delayed startup probe did not stay pending long enough to prove the "
            "guarded startup path.\n"
            f"Observed auth_probe_release_after_auth_start_seconds="
            f"{auth_probe_release_after_auth_start_seconds!r}; expected about "
            f"{SIMULATED_PROBE_DELAY_SECONDS} seconds."
        )
    if (
        authoritative_shell_ready_after_start_seconds is not None
        and auth_probe_released_after_start_seconds is not None
        and authoritative_shell_ready_after_start_seconds
        < auth_probe_released_after_start_seconds
    ):
        failures.append(
            "The first authoritative shell_ready transition happened before the delayed "
            "startup probe was released."
        )
    if authoritative_shell_ready_after_start_seconds is not None and (
        authoritative_shell_ready_after_start_seconds >= FULL_SYNC_TIMEOUT_SECONDS
    ):
        failures.append(
            f"The app waited until {authoritative_shell_ready_after_start_seconds!r} "
            f"seconds from launch, which reaches the full {FULL_SYNC_TIMEOUT_SECONDS}-second "
            "timeout window instead of transitioning when the successful probe completed."
        )
    if bool(shell_window["shell_ready_observed_while_auth_pending"]):
        failures.append(
            "The first observed shell_ready transition happened while the delayed "
            "startup probe was still pending."
        )
    if (
        authoritative_shell_ready_after_probe_release_seconds is not None
        and authoritative_shell_ready_after_probe_release_seconds
        > MAX_READY_AFTER_RELEASE_SECONDS
    ):
        failures.append(
            "The shell did not become interactive soon enough after the delayed probe "
            f"completed. Observed delay after release: "
            f"{authoritative_shell_ready_after_probe_release_seconds!r} seconds; allowed "
            f"threshold: {MAX_READY_AFTER_RELEASE_SECONDS} seconds."
        )
    return failures


def _assert_interactive_shell(observation: dict[str, Any]) -> None:
    shell = observation["shell_observation"]
    missing_navigation = [
        label
        for label in SHELL_NAVIGATION_LABELS
        if label not in shell["visible_navigation_labels"]
    ]
    if missing_navigation:
        raise AssertionError(
            "The shell_ready snapshot did not expose the full interactive shell navigation.\n"
            f"Missing labels: {missing_navigation}\n"
            f"Observed shell window:\n{json.dumps(observation, indent=2)}",
        )
    if observation["trigger"] is None:
        raise AssertionError(
            "The shell_ready snapshot did not expose the header workspace trigger needed "
            "to prove the top bar became interactive.\n"
            f"Observed shell window:\n{json.dumps(observation, indent=2)}",
        )
    if not bool(observation["branding_visible"]):
        raise AssertionError(
            "The shell_ready snapshot did not expose visible TrackState branding.\n"
            f"Observed shell window:\n{json.dumps(observation, indent=2)}",
        )


def _startup_surface_payload(tracker_page: TrackStateTrackerPage) -> dict[str, Any]:
    return startup_surface_payload(tracker_page)


def _snippet(text: str, *, limit: int = 240) -> str:
    return snippet(text, limit=limit)


def _record_step(
    result: dict[str, Any],
    *,
    step: int,
    status: str,
    action: str,
    observed: str,
) -> None:
    record_step(result, step=step, status=status, action=action, observed=observed)


def _record_human_verification(
    result: dict[str, Any],
    *,
    check: str,
    observed: str,
) -> None:
    record_human_verification(result, check=check, observed=observed)


def _record_not_reached_steps(
    result: dict[str, Any],
    *,
    starting_step: int,
) -> None:
    record_not_reached_steps(result, starting_step=starting_step, request_steps=REQUEST_STEPS)


def _write_pass_outputs(result: dict[str, Any]) -> None:
    BUG_DESCRIPTION_PATH.unlink(missing_ok=True)
    write_test_automation_result(RESULT_PATH, passed=True)
    JIRA_COMMENT_PATH.write_text(_build_jira_comment(result, passed=True), encoding="utf-8")
    PR_BODY_PATH.write_text(_build_pr_body(result, passed=True), encoding="utf-8")
    RESPONSE_PATH.write_text(_build_response_summary(result, passed=True), encoding="utf-8")


def _write_failure_outputs(result: dict[str, Any], *, product_bug: bool) -> None:
    error = str(result.get("error", f"AssertionError: {TICKET_KEY} failed"))
    write_test_automation_result(RESULT_PATH, passed=False, error=error)
    JIRA_COMMENT_PATH.write_text(_build_jira_comment(result, passed=False), encoding="utf-8")
    PR_BODY_PATH.write_text(_build_pr_body(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_build_response_summary(result, passed=False), encoding="utf-8")
    if product_bug:
        BUG_DESCRIPTION_PATH.write_text(_build_bug_description(result), encoding="utf-8")
    else:
        BUG_DESCRIPTION_PATH.unlink(missing_ok=True)


def _build_jira_comment(result: dict[str, Any], *, passed: bool) -> str:
    status_icon = "✅" if passed else "❌"
    status_word = "PASSED" if passed else "FAILED"
    lines = [
        "h3. Test Automation Result",
        "",
        f"*Status:* {status_icon} {status_word}",
        f"*Test Case:* {TICKET_KEY} — {TEST_CASE_TITLE}",
        "",
        "h4. What was tested",
        f"* Live deployed app at {{ {result.get('app_url')} }} in {result.get('browser')} on {result.get('os')}",
        f"* Desktop viewport {{ {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']} }}",
        f"* Delayed GitHub {{/user}} startup probe held for {SIMULATED_PROBE_DELAY_SECONDS} seconds before release",
        f"* Linked bug review: {LINKED_BUG_NOTES}",
        "",
        "h4. Result",
        "* Opened the deployed TrackState app in Chromium with a stored GitHub token and preloaded workspace state.",
        "* Monitored the live startup window while the delayed GitHub {/user} probe was still pending instead of asserting immediately.",
        "* Verified the app stayed out of the interactive shell until the delayed startup guard resolved.",
        "* Confirmed the visible page exposed shell navigation, the top-bar workspace trigger, and TrackState branding only after the guard completed.",
        "",
        "* Expected result matched."
        if passed
        else f"* Failed while checking the requested startup-guard behavior. Actual issue: {_actual_result_summary(result, passed=False)}",
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
    if result.get("pending_screenshot"):
        lines.extend(["", f"*Pending-state screenshot*: {result['pending_screenshot']}"])
    if result.get("screenshot"):
        lines.extend(["", f"*Final screenshot*: {result['screenshot']}"])
    lines.extend(
        [
            "",
            "h4. Test file",
            "{code}",
            TEST_FILE_PATH,
            "{code}",
            "",
            "h4. Run command",
            "{code:bash}",
            RUN_COMMAND,
            "{code}",
        ],
    )
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
        "## Test Automation Result",
        "",
        f"**Status:** {'✅ PASSED' if passed else '❌ FAILED'}",
        f"**Test Case:** {TICKET_KEY} — {TEST_CASE_TITLE}",
        "",
        "## What was automated",
        f"- Ran the live deployed app at `{result.get('app_url')}` in {result.get('browser')} on {result.get('os')}.",
        f"- Used the desktop viewport `{DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}`.",
        f"- Delayed the live GitHub `/user` startup probe by `{SIMULATED_PROBE_DELAY_SECONDS}` seconds and waited through the pending guard window before asserting.",
        f"- Considered linked bug {', '.join(LINKED_BUG_KEYS)} and kept the timing assertions coupled to the delayed probe completion.",
        "- Checked the user-visible startup surface before guard release and the user-visible shell after release.",
        "",
        "## Result",
        "- Confirmed the app stayed outside the interactive shell while the delayed startup guard was pending."
        if passed
        else f"- Failed while verifying the guarded startup behavior: {_actual_result_summary(result, passed=False)}",
        "- Confirmed the page exposed shell navigation, the top-bar workspace trigger, and TrackState branding only after the guard completed."
        if passed
        else "",
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
    if result.get("pending_screenshot"):
        lines.extend(["", f"**Pending-state screenshot:** `{result['pending_screenshot']}`"])
    if result.get("screenshot"):
        lines.extend(["", f"**Final screenshot:** `{result['screenshot']}`"])
    lines.extend(
        [
            "",
            "## Test file",
            "```text",
            TEST_FILE_PATH,
            "```",
            "",
            "## How to run",
            "```bash",
            RUN_COMMAND,
            "```",
        ],
    )
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
    return "\n".join(line for line in lines if line != "") + "\n"


def _build_response_summary(result: dict[str, Any], *, passed: bool) -> str:
    if passed:
        return (
            f"{TICKET_KEY} passed.\n\n"
            "Added a live Playwright startup regression that delays the initial GitHub "
            "`/user` probe by 5 seconds and proves the deployed app stays out of the "
            "interactive shell until that startup guard resolves.\n\n"
            "The live page remained non-interactive during the delayed guard window, "
            "then exposed shell navigation, the top-bar workspace trigger, and "
            "TrackState branding only after the probe succeeded.\n"
        )
    return (
        f"{TICKET_KEY} failed.\n\n"
        "Added a live Playwright startup regression that delays the initial GitHub "
        "`/user` probe by 5 seconds and checks whether `shell_ready` stays blocked "
        "until the startup guard resolves.\n\n"
        f"{result.get('error', 'The deployed app did not prove the guarded startup transition.')}\n"
    )


def _build_bug_description(result: dict[str, Any]) -> str:
    annotated_steps = build_annotated_steps(result, request_steps=REQUEST_STEPS)
    lines = [
        f"h3. Bug report — {TICKET_KEY}",
        "",
        "h4. Environment",
        f"* URL: {result.get('app_url')}",
        f"* Browser: {result.get('browser')}",
        f"* OS: {result.get('os')}",
        f"* Viewport: {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
        f"* Repository: {result.get('repository')} @ {result.get('repository_ref')}",
        f"* Run command: {{code:bash}}{RUN_COMMAND}{{code}}",
        f"* Delayed startup probe: GitHub {{/user}} delayed by {SIMULATED_PROBE_DELAY_SECONDS} seconds",
        "",
        "h4. Steps to Reproduce",
        *annotated_steps,
        "",
        "h4. Expected Result",
        EXPECTED_RESULT,
        "",
        "h4. Actual Result",
        _actual_result_summary(result, passed=False),
        "",
        "h4. Logs / Error Output",
        "{code}",
        str(result.get("traceback", result.get("error", ""))),
        "{code}",
        "",
        "h4. Notes",
        f"* GitHub requests seen: {{code}}{json.dumps(result.get('github_request_urls', []), ensure_ascii=True)}{{code}}",
        f"* Delayed requests seen: {{code}}{json.dumps(result.get('delayed_request_urls', []), ensure_ascii=True)}{{code}}",
        f"* Initial startup observation: {{code}}{json.dumps(result.get('startup_observation_initial'), ensure_ascii=True)}{{code}}",
        f"* Initial shell probe state: {{code}}{json.dumps(result.get('initial_shell_probe_state'), ensure_ascii=True)}{{code}}",
        f"* Final shell window: {{code}}{json.dumps(result.get('shell_window_observation'), ensure_ascii=True)}{{code}}",
    ]
    if result.get("pending_screenshot"):
        lines.append(f"* Pending-state screenshot: {{code}}{result['pending_screenshot']}{{code}}")
    if result.get("screenshot"):
        lines.append(f"* Final screenshot: {{code}}{result['screenshot']}{{code}}")
    return "\n".join(lines) + "\n"


def _actual_result_summary(result: dict[str, Any], *, passed: bool) -> str:
    if passed:
        startup_observation_initial = result.get("startup_observation_initial", {})
        shell_window = result.get("shell_window_observation", {})
        return (
            "The deployed app did not expose the interactive shell in the initial "
            "startup snapshot, then reached shell_ready only after the delayed startup "
            "guard resolved. It reached shell_ready in "
            f"{result.get('authoritative_shell_ready_after_start_seconds')!r} seconds "
            "from launch and "
            f"{result.get('authoritative_shell_ready_after_probe_release_seconds')!r} seconds "
            "after probe release, then showed the interactive shell with navigation, "
            "workspace trigger, and TrackState branding.\n"
            f"Initial startup excerpt: {_snippet(str(startup_observation_initial.get('body_text', '')))!r}\n"
            f"Final window labels: {shell_window.get('shell_observation', {}).get('visible_navigation_labels')!r}"
        )
    return str(
        result.get(
            "error",
            "The deployed app did not prove that shell_ready stayed blocked until the startup guard resolved.",
        ),
    )


def _step_lines(result: dict[str, Any], *, jira: bool) -> list[str]:
    return format_step_lines(result, jira=jira)


def _human_lines(result: dict[str, Any], *, jira: bool) -> list[str]:
    return format_human_lines(result, jira=jira)


if __name__ == "__main__":
    main()
