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
from testing.tests.support.delayed_auth_workspace_profiles_runtime import (  # noqa: E402
    DelayedAuthWorkspaceProfilesRuntime,
)
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
    relative_startup_event_seconds,
    safe_trigger_payload,
    snippet,
    startup_surface_payload,
    trigger_payload,
    try_observe_trigger,
    write_test_automation_result,
)

TICKET_KEY = "TS-990"
TEST_CASE_TITLE = (
    "Startup synchronization probe resolves after timeout - application UI state "
    "remains stable"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-990/test_ts_990.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
DEFAULT_BRANCH = "main"
LOCAL_TARGET = "/tmp/trackstate-demo"
LOCAL_DISPLAY_NAME = "Active local workspace"
HOSTED_DISPLAY_NAME = "Hosted setup workspace"
SHELL_NAVIGATION_LABELS = ("Dashboard", "Board", "JQL Search", "Hierarchy", "Settings")
BRANDING_TEXT = "Git-native. Jira-compatible. Team-proven."
SYNC_TIMEOUT_SECONDS = 11
SIMULATED_PROBE_DELAY_SECONDS = 30
TIMEOUT_ASSERTION_SECONDS = SYNC_TIMEOUT_SECONDS + 1
POST_RELEASE_STABILITY_SECONDS = 2
AUTH_PROBE_START_WAIT_SECONDS = 60
STARTUP_RENDER_WAIT_SECONDS = 60
OBSERVATION_TIMEOUT_SECONDS = SIMULATED_PROBE_DELAY_SECONDS + POST_RELEASE_STABILITY_SECONDS + 20
POLL_INTERVAL_SECONDS = 0.5
LINKED_BUGS = ["TS-996", "TS-992", "TS-971"]
LINKED_BUG_NOTES = (
    "Reviewed TS-996, TS-992, and TS-971. Their fixes require the startup GitHub "
    "`/user` probe to begin normally, the shell to remain interactive once the "
    "11-second timeout fallback is available, and the late probe resolution to "
    "avoid resetting visible hosted-workspace state. This test therefore waits "
    "past the timeout and continues observing through the delayed release."
)
REWORK_SUMMARY = (
    "Added a live Playwright startup regression that delays the initial GitHub "
    "`/user` probe beyond the 11-second synchronization window and verifies the "
    "visible shell stays stable when the late probe finally resolves."
)
REWORK_FIXES = (
    "Made the hosted workspace the active startup workspace and seeded its "
    "workspace-scoped GitHub token.",
    "Applied the required 1440x900 viewport before opening the app so startup "
    "runs under the ticket dimensions.",
    "Only write `bug_description.md` for confirmed product failures and emit "
    "per-thread review replies.",
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
DISCUSSIONS_RAW_PATH = REPO_ROOT / "input" / TICKET_KEY / "pr_discussions_raw.json"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
REVIEW_REPLIES_PATH = OUTPUTS_DIR / "review_replies.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts990_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts990_failure.png"

REQUEST_STEPS = [
    "Launch the TrackState application.",
    "Wait for the 11-second timeout to expire and verify the shell is interactive (`shell_ready=true`).",
    "Continue monitoring the application for another 10 seconds until the probe finally resolves.",
    "Observe the UI for any flickers, navigation resets, or duplicate state updates in the TopBar and branding.",
]
EXPECTED_RESULT = (
    "The application remains stable and interactive. The late resolution of the "
    "synchronization probe does not interrupt the user's session or reset the "
    "rendered shell components, confirming the race condition is handled cleanly."
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
            "TS-990 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
        )

    workspace_state = _workspace_state(service.repository)
    hosted_workspace_id = f"hosted:{service.repository.lower()}@{DEFAULT_BRANCH}"
    prepared_local_workspace = _prepare_local_workspace_repository()
    runtime = DelayedAuthWorkspaceProfilesRuntime(
        repository=config.repository,
        token=token,
        workspace_state=workspace_state,
        auth_delay_seconds=SIMULATED_PROBE_DELAY_SECONDS,
        delayed_paths=("/user",),
        workspace_token_profile_ids=(hosted_workspace_id,),
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
        "linked_bug_notes": LINKED_BUG_NOTES,
        "sync_timeout_seconds": SYNC_TIMEOUT_SECONDS,
        "timeout_assertion_seconds": TIMEOUT_ASSERTION_SECONDS,
        "simulated_probe_delay_seconds": SIMULATED_PROBE_DELAY_SECONDS,
        "post_release_stability_seconds": POST_RELEASE_STABILITY_SECONDS,
        "preloaded_workspace_state": workspace_state,
        "hosted_workspace_id": hosted_workspace_id,
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
                tracker_page.open_entrypoint()
                result["startup_observation_initial"] = startup_surface_payload(
                    tracker_page,
                )
                startup_rendered, startup_surface = poll_until(
                    probe=lambda: _startup_surface_payload(tracker_page),
                    is_satisfied=_startup_surface_loaded,
                    timeout_seconds=STARTUP_RENDER_WAIT_SECONDS,
                    interval_seconds=POLL_INTERVAL_SECONDS,
                )
                result["startup_observation_after_render"] = startup_surface
                if not startup_rendered:
                    _record_step(
                        result,
                        step=1,
                        status="failed",
                        action=REQUEST_STEPS[0],
                        observed=(
                            "The deployed app never rendered beyond the bare startup title, "
                            "so the delayed synchronization scenario could not begin.\n"
                            f"Observed startup surface:\n{json.dumps(startup_surface, indent=2)}"
                        ),
                    )
                    _record_not_reached_steps(result, starting_step=2)
                    raise AssertionError(
                        "Step 1 failed: the deployed app never rendered beyond the bare "
                        "startup title before the synchronization scenario began.\n"
                        f"Observed startup surface:\n{json.dumps(startup_surface, indent=2)}",
                    )

                if not runtime.wait_for_auth_probe_start(
                    timeout_seconds=AUTH_PROBE_START_WAIT_SECONDS,
                ):
                    _record_step(
                        result,
                        step=1,
                        status="failed",
                        action=REQUEST_STEPS[0],
                        observed=(
                            "The deployed app never started the delayed GitHub `/user` "
                            "startup probe, so the timeout-plus-late-resolution scenario "
                            "was not exercised.\n"
                            f"Observed body text:\n{tracker_page.body_text()}"
                        ),
                    )
                    _record_not_reached_steps(result, starting_step=2)
                    raise AssertionError(
                        "Step 1 failed: the delayed GitHub `/user` startup probe never "
                        f"started for {TICKET_KEY}.\nObserved body text:\n"
                        f"{tracker_page.body_text()}",
                    )

                auth_probe_started_after_start_seconds = relative_startup_event_seconds(
                    startup_started_at_monotonic,
                    runtime.auth_probe_started_at_monotonic,
                )
                result["auth_probe_started_after_start_seconds"] = (
                    auth_probe_started_after_start_seconds
                )
                initial_trigger = _try_observe_trigger(page)
                result["initial_trigger_observation"] = (
                    _trigger_payload(initial_trigger) if initial_trigger is not None else None
                )
                initial_shell_interactive = _startup_surface_shows_interactive_shell(
                    startup_surface,
                    initial_trigger=initial_trigger,
                )
                result["initial_shell_interactive"] = initial_shell_interactive
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
                        f"startup_surface={json.dumps(startup_surface, ensure_ascii=True)}; "
                        f"auth_probe_started_after_start_seconds="
                        f"{auth_probe_started_after_start_seconds!r}; "
                        f"initial_trigger={json.dumps(result['initial_trigger_observation'], ensure_ascii=True)}; "
                        f"delayed_request_urls={runtime.delayed_request_urls!r}"
                    ),
                )

                transition_tracker = ShellReadyTransitionTracker()
                timeout_reached, timeout_window = poll_until(
                    probe=lambda: _observe_shell_window(
                        tracker_page=tracker_page,
                        page=page,
                        runtime=runtime,
                        startup_started_at_monotonic=startup_started_at_monotonic,
                        transition_tracker=transition_tracker,
                    ),
                    is_satisfied=lambda observation: (
                        observation["elapsed_since_auth_start_seconds"] is not None
                        and float(observation["elapsed_since_auth_start_seconds"])
                        >= TIMEOUT_ASSERTION_SECONDS
                    ),
                    timeout_seconds=SIMULATED_PROBE_DELAY_SECONDS + 10,
                    interval_seconds=POLL_INTERVAL_SECONDS,
                )
                result["timeout_window_observation"] = _sample_payload(timeout_window)
                result["github_request_urls"] = list(runtime.github_request_urls)
                result["delayed_request_urls"] = list(runtime.delayed_request_urls)

                failures: list[str] = []
                step_two_error: str | None = None
                startup_shell_ready_before_timeout = (
                    initial_shell_interactive
                    and auth_probe_started_after_start_seconds is not None
                    and float(auth_probe_started_after_start_seconds)
                    < TIMEOUT_ASSERTION_SECONDS
                )
                if not timeout_reached:
                    step_two_error = (
                        "Step 2 failed: the test never reached the post-timeout "
                        "observation window while watching the delayed startup probe.\n"
                        f"Observed timeout window:\n{json.dumps(_sample_payload(timeout_window), indent=2)}"
                    )
                elif startup_shell_ready_before_timeout:
                    _record_step(
                        result,
                        step=2,
                        status="passed",
                        action=REQUEST_STEPS[1],
                        observed=(
                            "The hosted shell was already interactive before the delayed "
                            "GitHub `/user` probe fully resolved, so the user-visible app "
                            "had reached the timeout-ready state well before the 11-second "
                            "window elapsed.\n"
                            f"auth_probe_started_after_start_seconds="
                            f"{auth_probe_started_after_start_seconds!r}; "
                            f"initial_trigger={json.dumps(result['initial_trigger_observation'], ensure_ascii=True)}; "
                            f"initial_startup_buttons={startup_surface.get('button_labels', [])!r}; "
                            f"late_window_shell_ready={timeout_window['shell_observation']['shell_ready']!r}"
                        ),
                    )
                elif (
                    not bool(timeout_window["auth_pending"])
                    and timeout_window["shell_ready_after_start_seconds"] is not None
                    and timeout_window["auth_probe_released_after_start_seconds"] is not None
                    and float(timeout_window["shell_ready_after_start_seconds"])
                    > TIMEOUT_ASSERTION_SECONDS
                    and float(timeout_window["shell_ready_after_probe_release_seconds"] or 0)
                    <= 1.0
                ):
                    step_two_error = (
                        "Step 2 failed: the shell did not become interactive within the "
                        f"{SYNC_TIMEOUT_SECONDS}-second timeout window. It only reported "
                        "shell_ready after the delayed GitHub `/user` probe released.\n"
                        f"Observed timeout window:\n{json.dumps(_sample_payload(timeout_window), indent=2)}"
                    )
                elif not bool(timeout_window["auth_pending"]):
                    step_two_error = (
                        "Step 2 failed: by the time the timeout assertion ran, the delayed "
                        "startup probe was no longer pending, so the ticket's late-resolution "
                        "precondition was not observed.\n"
                        f"Observed timeout window:\n{json.dumps(_sample_payload(timeout_window), indent=2)}"
                    )
                elif not bool(timeout_window["shell_observation"]["shell_ready"]):
                    step_two_error = (
                        "Step 2 failed: after waiting past the 11-second synchronization "
                        "window, the page still had not reached shell_ready.\n"
                        f"Observed timeout window:\n{json.dumps(_sample_payload(timeout_window), indent=2)}"
                    )
                else:
                    try:
                        _assert_interactive_shell(timeout_window)
                    except AssertionError as error:
                        step_two_error = f"Step 2 failed: {error}"

                if step_two_error is None and not startup_shell_ready_before_timeout:
                    _record_step(
                        result,
                        step=2,
                        status="passed",
                        action=REQUEST_STEPS[1],
                        observed=(
                            f"Waited {timeout_window['elapsed_since_auth_start_seconds']!r} "
                            "seconds from the delayed `/user` probe start, which is beyond "
                            f"the {SYNC_TIMEOUT_SECONDS}-second synchronization window. The "
                            "probe was still pending and the live app already exposed the "
                            "interactive shell.\n"
                            f"shell_ready_after_start_seconds="
                            f"{timeout_window['shell_ready_after_start_seconds']!r}; "
                            f"trigger_label={(timeout_window['trigger'] or {}).get('semantic_label')!r}; "
                            f"branding_visible={timeout_window['branding_visible']!r}; "
                            "visible_navigation_labels="
                            f"{timeout_window['shell_observation']['visible_navigation_labels']!r}"
                        ),
                    )
                elif step_two_error is not None:
                    failures.append(step_two_error)
                    _record_step(
                        result,
                        step=2,
                        status="failed",
                        action=REQUEST_STEPS[1],
                        observed=step_two_error,
                    )

                stability_samples: list[dict[str, Any]] = [timeout_window]
                release_observed, final_window = poll_until(
                    probe=lambda: _collect_stability_sample(
                        tracker_page=tracker_page,
                        page=page,
                        runtime=runtime,
                        startup_started_at_monotonic=startup_started_at_monotonic,
                        transition_tracker=transition_tracker,
                        samples=stability_samples,
                    ),
                    is_satisfied=lambda observation: (
                        runtime.auth_probe_released_at_monotonic is not None
                        and (time.monotonic() - runtime.auth_probe_released_at_monotonic)
                        >= POST_RELEASE_STABILITY_SECONDS
                    ),
                    timeout_seconds=OBSERVATION_TIMEOUT_SECONDS,
                    interval_seconds=POLL_INTERVAL_SECONDS,
                )
                result["final_stability_observation"] = _sample_payload(final_window)
                result["stability_sample_count"] = len(stability_samples)
                result["stability_samples"] = [
                    _sample_payload(sample) for sample in stability_samples
                ]

                step_three_error: str | None = None
                release_after_start_seconds = final_window["auth_probe_released_after_start_seconds"]
                if not release_observed:
                    step_three_error = (
                        "Step 3 failed: the delayed startup probe never resolved within the "
                        "observation window, so the late-resolution behavior was not fully "
                        "observed.\n"
                        f"Latest stability sample:\n{json.dumps(_sample_payload(final_window), indent=2)}"
                    )
                elif release_after_start_seconds is None:
                    step_three_error = (
                        "Step 3 failed: the delayed startup probe appeared to finish, but the "
                        "release time was not recorded in the collected stability window.\n"
                        f"Latest stability sample:\n{json.dumps(_sample_payload(final_window), indent=2)}"
                    )
                elif float(release_after_start_seconds) <= TIMEOUT_ASSERTION_SECONDS:
                    step_three_error = (
                        "Step 3 failed: the delayed startup probe resolved before the "
                        "post-timeout monitoring window, so the ticket's late-resolution "
                        "scenario was not reproduced.\n"
                        f"auth_probe_released_after_start_seconds={release_after_start_seconds!r}; "
                        f"timeout_assertion_seconds={TIMEOUT_ASSERTION_SECONDS!r}"
                    )

                if step_three_error is None:
                    post_timeout_duration = round(
                        float(release_after_start_seconds) - TIMEOUT_ASSERTION_SECONDS,
                        2,
                    )
                    _record_step(
                        result,
                        step=3,
                        status="passed",
                        action=REQUEST_STEPS[2],
                        observed=(
                            "Continued sampling the live page until the delayed probe "
                            "resolved and a short post-release settle window elapsed.\n"
                            f"auth_probe_released_after_start_seconds={release_after_start_seconds!r}; "
                            f"post_timeout_monitor_seconds={post_timeout_duration!r}; "
                            f"post_release_stability_seconds={POST_RELEASE_STABILITY_SECONDS!r}; "
                            f"stability_sample_count={len(stability_samples)!r}"
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

                step_four_failures = _stability_failures(
                    stability_samples=stability_samples,
                    required_navigation_labels=SHELL_NAVIGATION_LABELS,
                    initial_trigger_signature=_trigger_signature(
                        {"trigger": result.get("initial_trigger_observation")},
                    ),
                )
                if step_two_error is not None and not step_four_failures:
                    step_four_failures.append(
                        "The timeout snapshot never proved an interactive shell, so UI "
                        "stability after timeout could not be confirmed."
                    )
                if step_three_error is not None and not step_four_failures:
                    step_four_failures.append(
                        "The delayed probe did not complete cleanly during observation, so "
                        "the late-resolution stability check could not be fully confirmed."
                    )

                if step_four_failures:
                    step_four_error = (
                        "Step 4 failed: the late probe resolution did not keep the visible "
                        "shell stable.\n"
                        + "\n".join(step_four_failures)
                    )
                    failures.append(step_four_error)
                    _record_step(
                        result,
                        step=4,
                        status="failed",
                        action=REQUEST_STEPS[3],
                        observed=step_four_error,
                    )
                else:
                    stable_trigger = final_window["trigger"] or timeout_window["trigger"] or {}
                    observed_routes = _observed_routes(stability_samples)
                    _record_step(
                        result,
                        step=4,
                        status="passed",
                        action=REQUEST_STEPS[3],
                        observed=(
                            "Across the post-timeout monitoring window, the visible shell "
                            "never dropped out of shell_ready, the top-bar workspace trigger "
                            "and branding stayed visible, and the route stayed stable.\n"
                            f"observed_routes={observed_routes!r}; "
                            f"stable_trigger={json.dumps(stable_trigger, ensure_ascii=True)}; "
                            f"stability_sample_count={len(stability_samples)!r}"
                        ),
                    )

                _record_human_verification(
                    result,
                    check=(
                        "Viewed the hosted shell as soon as the app rendered and confirmed "
                        "the user-facing navigation, branding, and workspace trigger were "
                        "visible before the delayed probe finished."
                    ),
                    observed=(
                        f"initial_body_excerpt={_snippet(str(startup_surface.get('body_text', '')))!r}; "
                        f"initial_trigger_label={(result.get('initial_trigger_observation') or {}).get('semantic_label')!r}; "
                        f"initial_shell_interactive={initial_shell_interactive!r}; "
                        f"auth_probe_started_after_start_seconds={auth_probe_started_after_start_seconds!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Kept watching the live page through the delayed probe release and "
                        "checked whether the hosted-workspace state stayed the same from the "
                        "user's perspective."
                    ),
                    observed=(
                        f"final_route={_route_signature(final_window)!r}; "
                        f"initial_trigger_signature={_trigger_signature({'trigger': result.get('initial_trigger_observation')})!r}; "
                        f"stable_trigger_signature={_trigger_signature(final_window)!r}; "
                        f"shell_ready_after_start_seconds={final_window['shell_ready_after_start_seconds']!r}; "
                        f"auth_probe_released_after_start_seconds={release_after_start_seconds!r}; "
                        f"stability_sample_count={len(stability_samples)!r}"
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
        result["error"] = f"AssertionError: {error}"
        result["traceback"] = traceback.format_exc()
        _write_failure_outputs(result)
        raise
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        _write_failure_outputs(result)
        raise


def _workspace_state(repository: str) -> dict[str, object]:
    return build_workspace_state(
        repository,
        local_target=LOCAL_TARGET,
        default_branch=DEFAULT_BRANCH,
        local_display_name=LOCAL_DISPLAY_NAME,
        hosted_display_name=HOSTED_DISPLAY_NAME,
        active_workspace="hosted",
    )


def _prepare_local_workspace_repository() -> dict[str, object]:
    return prepare_local_workspace_repository(
        local_target=LOCAL_TARGET,
        default_branch=DEFAULT_BRANCH,
        marker_filename=".trackstate-ts990-precondition.txt",
        marker_contents="Prepared for TS-990 late startup probe stability validation.\n",
        commit_author_name="TS-990 Automation",
        commit_author_email="ts990@example.com",
        commit_message="Prepare TS-990 local workspace",
    )


def _observe_shell_window(
    *,
    tracker_page: TrackStateTrackerPage,
    page: LiveWorkspaceSwitcherPage,
    runtime: DelayedAuthWorkspaceProfilesRuntime,
    startup_started_at_monotonic: float,
    transition_tracker: ShellReadyTransitionTracker,
) -> dict[str, Any]:
    return observe_live_startup_shell_window(
        tracker_page=tracker_page,
        page=page,
        runtime=runtime,
        startup_started_at_monotonic=startup_started_at_monotonic,
        shell_navigation_labels=SHELL_NAVIGATION_LABELS,
        branding_texts=(BRANDING_TEXT, "TrackState.AI"),
        transition_tracker=transition_tracker,
    )


def _collect_stability_sample(
    *,
    tracker_page: TrackStateTrackerPage,
    page: LiveWorkspaceSwitcherPage,
    runtime: DelayedAuthWorkspaceProfilesRuntime,
    startup_started_at_monotonic: float,
    transition_tracker: ShellReadyTransitionTracker,
    samples: list[dict[str, Any]],
) -> dict[str, Any]:
    observation = _observe_shell_window(
        tracker_page=tracker_page,
        page=page,
        runtime=runtime,
        startup_started_at_monotonic=startup_started_at_monotonic,
        transition_tracker=transition_tracker,
    )
    samples.append(observation)
    return observation


def _assert_interactive_shell(observation: dict[str, Any]) -> None:
    shell = observation["shell_observation"]
    missing_navigation = [
        label
        for label in SHELL_NAVIGATION_LABELS
        if label not in shell["visible_navigation_labels"]
    ]
    if missing_navigation:
        raise AssertionError(
            "The timeout-window snapshot did not expose the full interactive shell "
            "navigation.\n"
            f"Missing labels: {missing_navigation}\n"
            f"Observed sample:\n{json.dumps(_sample_payload(observation), indent=2)}",
        )
    if observation["trigger"] is None:
        raise AssertionError(
            "The timeout-window snapshot did not expose the header workspace trigger "
            "needed to prove the TopBar stayed interactive.\n"
            f"Observed sample:\n{json.dumps(_sample_payload(observation), indent=2)}",
        )
    if not bool(observation["branding_visible"]):
        raise AssertionError(
            "The timeout-window snapshot did not expose visible TrackState branding.\n"
            f"Observed sample:\n{json.dumps(_sample_payload(observation), indent=2)}",
        )
    startup_buttons = set(observation["startup_observation"]["button_labels"])
    if startup_buttons == {"Sync issue"}:
        raise AssertionError(
            "The page still looked like the startup Sync issue surface instead of the "
            "interactive shell when the timeout snapshot was taken.\n"
            f"Observed sample:\n{json.dumps(_sample_payload(observation), indent=2)}",
        )


def _stability_failures(
    *,
    stability_samples: list[dict[str, Any]],
    required_navigation_labels: tuple[str, ...],
    initial_trigger_signature: tuple[str, str, str, str] | None = None,
) -> list[str]:
    failures: list[str] = []
    if len(stability_samples) < 3:
        failures.append(
            "The stability monitor captured too few samples after the timeout window "
            f"({len(stability_samples)} samples).",
        )
        return failures

    first_unready = next(
        (
            sample
            for sample in stability_samples
            if not bool(sample["shell_observation"]["shell_ready"])
        ),
        None,
    )
    if first_unready is not None:
        failures.append(
            "The shell stopped reporting shell_ready during post-timeout monitoring.\n"
            f"Observed sample: {json.dumps(_sample_payload(first_unready), indent=2)}",
        )

    first_missing_trigger = next(
        (sample for sample in stability_samples if sample["trigger"] is None),
        None,
    )
    if first_missing_trigger is not None:
        failures.append(
            "The TopBar workspace trigger disappeared during post-timeout monitoring.\n"
            f"Observed sample: {json.dumps(_sample_payload(first_missing_trigger), indent=2)}",
        )

    first_missing_branding = next(
        (sample for sample in stability_samples if not bool(sample["branding_visible"])),
        None,
    )
    if first_missing_branding is not None:
        failures.append(
            "TrackState branding was no longer visible during post-timeout monitoring.\n"
            f"Observed sample: {json.dumps(_sample_payload(first_missing_branding), indent=2)}",
        )

    missing_navigation_samples = []
    for sample in stability_samples:
        missing = [
            label
            for label in required_navigation_labels
            if label not in sample["shell_observation"]["visible_navigation_labels"]
        ]
        if missing:
            missing_navigation_samples.append(
                {
                    "missing_navigation": missing,
                    "sample": _sample_payload(sample),
                },
            )
            break
    if missing_navigation_samples:
        failures.append(
            "Shell navigation labels dropped out during post-timeout monitoring.\n"
            f"Observed sample: {json.dumps(missing_navigation_samples[0], indent=2)}",
        )

    route_signatures = {_route_signature(sample) for sample in stability_samples}
    if len(route_signatures) > 1:
        failures.append(
            "The visible route changed during post-timeout monitoring, indicating a "
            f"navigation reset. Observed routes: {sorted(route_signatures)!r}",
        )

    trigger_signatures = {
        signature
        for signature in (_trigger_signature(sample) for sample in stability_samples)
        if signature is not None
    }
    if initial_trigger_signature is not None:
        trigger_signatures.add(initial_trigger_signature)
    if len(trigger_signatures) > 1:
        failures.append(
            "The visible TopBar workspace trigger changed during post-timeout monitoring, "
            f"suggesting a duplicate or reset state update. Observed trigger states: "
            f"{sorted(trigger_signatures)!r}",
        )

    sync_issue_return = next(
        (
            sample
            for sample in stability_samples
            if set(sample["startup_observation"]["button_labels"]) == {"Sync issue"}
        ),
        None,
    )
    if sync_issue_return is not None:
        failures.append(
            "The page regressed back to a visible Sync issue-only startup surface during "
            "post-timeout monitoring.\n"
            f"Observed sample: {json.dumps(_sample_payload(sync_issue_return), indent=2)}",
        )

    return failures


def _sample_payload(observation: dict[str, Any]) -> dict[str, Any]:
    trigger = observation.get("trigger")
    startup = observation.get("startup_observation", {})
    shell = observation.get("shell_observation", {})
    return {
        "auth_pending": observation.get("auth_pending"),
        "elapsed_since_auth_start_seconds": observation.get("elapsed_since_auth_start_seconds"),
        "auth_probe_started_after_start_seconds": observation.get(
            "auth_probe_started_after_start_seconds",
        ),
        "auth_probe_released_after_start_seconds": observation.get(
            "auth_probe_released_after_start_seconds",
        ),
        "shell_ready_after_start_seconds": observation.get("shell_ready_after_start_seconds"),
        "shell_ready_after_probe_release_seconds": observation.get(
            "shell_ready_after_probe_release_seconds",
        ),
        "shell_ready_observed_while_auth_pending": observation.get(
            "shell_ready_observed_while_auth_pending",
        ),
        "branding_visible": observation.get("branding_visible"),
        "location_pathname": startup.get("location_pathname"),
        "location_hash": startup.get("location_hash"),
        "title": startup.get("title"),
        "button_labels": list(startup.get("button_labels", [])),
        "visible_navigation_labels": list(shell.get("visible_navigation_labels", [])),
        "shell_ready": shell.get("shell_ready"),
        "fatal_banner_visible": shell.get("fatal_banner_visible"),
        "connect_github_visible": shell.get("connect_github_visible"),
        "trigger": trigger,
        "body_excerpt": _snippet(str(shell.get("body_text", ""))),
    }


def _route_signature(observation: dict[str, Any]) -> tuple[str | None, str | None]:
    startup = observation["startup_observation"]
    return (
        startup.get("location_pathname"),
        startup.get("location_hash"),
    )


def _observed_routes(stability_samples: list[dict[str, Any]]) -> list[tuple[str | None, str | None]]:
    return sorted({_route_signature(sample) for sample in stability_samples})


def _trigger_signature(observation: dict[str, Any]) -> tuple[str, str, str, str] | None:
    trigger = observation.get("trigger")
    if not isinstance(trigger, dict):
        return None
    return (
        str(trigger.get("semantic_label")),
        str(trigger.get("display_name")),
        str(trigger.get("workspace_type")),
        str(trigger.get("state_label")),
    )


def _startup_surface_payload(tracker_page: TrackStateTrackerPage) -> dict[str, Any]:
    return startup_surface_payload(tracker_page)


def _startup_surface_loaded(observation: dict[str, Any]) -> bool:
    body_text = str(observation.get("body_text", "")).strip()
    title = str(observation.get("title", "")).strip()
    button_labels = observation.get("button_labels", [])
    return bool(button_labels) or (len(body_text) > len(title) and body_text != title)


def _startup_surface_shows_interactive_shell(
    observation: dict[str, Any],
    *,
    initial_trigger: Any | None,
) -> bool:
    body_text = str(observation.get("body_text", ""))
    button_labels = {str(label) for label in observation.get("button_labels", [])}
    return (
        all(label in body_text for label in SHELL_NAVIGATION_LABELS)
        and BRANDING_TEXT in body_text
        and initial_trigger is not None
        and "Connect GitHub" not in button_labels
    )


def _safe_trigger_payload(
    page: LiveWorkspaceSwitcherPage,
) -> dict[str, Any] | None:
    return safe_trigger_payload(page)


def _try_observe_trigger(
    page: LiveWorkspaceSwitcherPage,
) -> Any | None:
    return try_observe_trigger(page)


def _trigger_payload(trigger: Any) -> dict[str, Any]:
    return trigger_payload(trigger)


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
    _write_review_replies(result, passed=True)


def _write_failure_outputs(result: dict[str, Any]) -> None:
    error = str(result.get("error", f"AssertionError: {TICKET_KEY} failed"))
    write_test_automation_result(RESULT_PATH, passed=False, error=error)
    JIRA_COMMENT_PATH.write_text(_build_jira_comment(result, passed=False), encoding="utf-8")
    PR_BODY_PATH.write_text(_build_pr_body(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_build_response_summary(result, passed=False), encoding="utf-8")
    _write_review_replies(result, passed=False)
    if _should_write_bug_description(result):
        BUG_DESCRIPTION_PATH.write_text(_build_bug_description(result), encoding="utf-8")
    else:
        BUG_DESCRIPTION_PATH.unlink(missing_ok=True)


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
        f"*Linked bug review*: {LINKED_BUG_NOTES}",
        f"*Startup probe setup*: delayed GitHub {{/user}} probe by {SIMULATED_PROBE_DELAY_SECONDS} seconds",
        f"*Timeout check*: interactive shell stays available after the {SYNC_TIMEOUT_SECONDS}-second window and through late probe resolution",
        "",
        "h4. What was automated",
        "* Opened the deployed TrackState app in Chromium with a stored GitHub token and preloaded workspace state.",
        "* Delayed the live GitHub {/user} startup probe beyond the 11-second synchronization window and waited past the timeout before asserting.",
        "* Continued sampling the deployed shell until the delayed probe resolved instead of asserting only once.",
        "* Verified the visible shell navigation, top-bar workspace trigger, route, and TrackState branding stayed stable from the user's perspective.",
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
        *[f"- {item}" for item in REWORK_FIXES],
        "",
        f"**Test case:** {TEST_CASE_TITLE}",
        f"**Environment:** `{result.get('app_url')}` · {result.get('browser')} · {result.get('os')}",
        f"**Viewport:** `{DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}`",
        f"**Linked bugs considered:** {', '.join(LINKED_BUGS)}",
        f"**Linked bug review:** {LINKED_BUG_NOTES}",
        f"**Startup probe setup:** delayed GitHub `/user` probe by `{SIMULATED_PROBE_DELAY_SECONDS}` seconds",
        f"**Timeout check:** interactive shell stays available after the `{SYNC_TIMEOUT_SECONDS}`-second window and through late probe resolution",
        "",
        "## What was automated",
        "- Opened the deployed TrackState app in Chromium with a stored GitHub token and preloaded workspace state.",
        "- Delayed the live GitHub `/user` startup probe beyond the 11-second synchronization window and waited past the timeout before asserting.",
        "- Continued sampling the deployed shell until the delayed probe resolved instead of asserting only once.",
        "- Verified the visible shell navigation, top-bar workspace trigger, route, and TrackState branding stayed stable from the user's perspective.",
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
        final_sample = result.get("final_stability_observation", {})
        return "\n".join(
            [
                "h3. PR Rework Result",
                "",
                (
                    "*Fixed:* Made the hosted workspace active for startup, applied the "
                    "1440x900 viewport before opening the app, and only emit "
                    "`bug_description.md` for confirmed product failures."
                ),
                f"*Test Run:* `{RUN_COMMAND}`",
                "*Result:* ✅ PASSED",
                "*Summary:* 1 passed, 0 failed.",
                (
                    "*Observed:* "
                    f"shell_ready_after_start_seconds={final_sample.get('shell_ready_after_start_seconds')!r}; "
                    f"auth_probe_released_after_start_seconds={final_sample.get('auth_probe_released_after_start_seconds')!r}."
                ),
                "",
            ],
        )
    return "\n".join(
        [
            "h3. PR Rework Result",
            "",
            (
                "*Fixed:* Made the hosted workspace active for startup, applied the "
                "1440x900 viewport before opening the app, and only emit "
                "`bug_description.md` for confirmed product failures."
            ),
            f"*Test Run:* `{RUN_COMMAND}`",
            "*Result:* ❌ FAILED",
            "*Summary:* 0 passed, 1 failed.",
            f"*Error:* {_error_summary(result)}",
            "",
        ],
    )


def _write_review_replies(result: dict[str, Any], *, passed: bool) -> None:
    replies = [
        {
            "inReplyToId": thread["rootCommentId"],
            "threadId": thread["threadId"],
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
        and thread.get("resolved") is False
        and thread.get("rootCommentId") is not None
        and thread.get("threadId") is not None
    ]


def _review_reply_text(
    *,
    thread: dict[str, Any],
    result: dict[str, Any],
    passed: bool,
) -> str:
    rerun_summary = (
        f"Re-ran `{RUN_COMMAND}`: passed (`1 passed, 0 failed`)."
        if passed
        else f"Re-ran `{RUN_COMMAND}`: failed with `{_error_summary(result)}`."
    )
    comment_id = thread.get("rootCommentId")
    if comment_id == 3292430524:
        return (
            "Fixed: TS-990 now seeds the hosted workspace as the active startup "
            "workspace, so launch goes through the hosted GitHub auth path that starts "
            f"the delayed `/user` probe. {rerun_summary}"
        )
    if comment_id == 3292430549:
        return (
            "Fixed: TS-990 now applies the required `1440x900` viewport before "
            "calling `open_entrypoint()`, so the entire startup sequence runs under "
            f"the ticket dimensions. {rerun_summary}"
        )
    if comment_id == 3292430577:
        return (
            "Fixed: TS-990 now writes `bug_description.md` only for confirmed product "
            "failures and removes any stale bug artifact for test/setup failures, so "
            f"rework-only regressions do not create false downstream bugs. {rerun_summary}"
        )
    if comment_id == 3292445901:
        return (
            "Fixed: `_should_write_bug_description()` no longer defaults to `True` for "
            "generic assertion/setup failures. TS-990 now emits `bug_description.md` only "
            "for confirmed product-visible failures (for example, the hosted shell landing "
            "in `Needs sign-in` / `Connect GitHub`, missing the post-timeout interactive "
            "shell, never resolving the delayed probe, or destabilizing the shell after the "
            f"late release). {rerun_summary}"
        )
    return (
        "Fixed: updated TS-990 to start from the hosted workspace, set the required "
        "viewport before launch, gate `bug_description.md` to confirmed product "
        f"failures, and emit per-thread review replies. {rerun_summary}"
    )


def _should_write_bug_description(result: dict[str, Any]) -> bool:
    return _bug_description_reason(result) is not None


def _bug_description_reason(result: dict[str, Any]) -> str | None:
    error = str(result.get("error", ""))
    if error.startswith("RuntimeError: TS-990 requires GH_TOKEN or GITHUB_TOKEN"):
        return None
    if error.startswith("ModuleNotFoundError:"):
        return None

    failed_steps = {
        int(step.get("step")): step
        for step in result.get("steps", [])
        if isinstance(step, dict) and step.get("status") == "failed"
    }
    step_one_observed = str(failed_steps.get(1, {}).get("observed", ""))
    step_two_observed = str(failed_steps.get(2, {}).get("observed", ""))
    step_three_observed = str(failed_steps.get(3, {}).get("observed", ""))
    step_four_observed = str(failed_steps.get(4, {}).get("observed", ""))

    if "never rendered beyond the bare startup title" in step_one_observed:
        return "startup-surface-never-rendered"
    if (
        "never started the delayed GitHub `/user` startup probe" in step_one_observed
        and _hosted_sign_in_gap_visible(result)
    ):
        return "hosted-workspace-auth-probe-missing"
    if (
        "still had not reached shell_ready" in step_two_observed
        or "did not expose the full interactive shell navigation" in step_two_observed
        or "did not expose the header workspace trigger" in step_two_observed
        or "did not expose visible TrackState branding" in step_two_observed
        or "still looked like the startup Sync issue surface" in step_two_observed
    ):
        return "shell-not-interactive-after-timeout"
    if "never resolved within the observation window" in step_three_observed:
        return "startup-probe-never-resolved"
    if step_four_observed and not step_four_observed.startswith("Not reached because step "):
        return "late-probe-resolution-destabilized-shell"
    return None


def _hosted_sign_in_gap_visible(result: dict[str, Any]) -> bool:
    observed_fragments = [
        str(result.get("error", "")),
        str(result.get("startup_observation_after_render", "")),
        str(result.get("startup_observation_initial", "")),
        str(result.get("timeout_window_observation", "")),
        str(result.get("final_stability_observation", "")),
    ]
    observed_fragments.extend(
        str(step.get("observed", ""))
        for step in result.get("steps", [])
        if isinstance(step, dict)
    )
    combined_text = "\n".join(observed_fragments)
    return "Needs sign-in" in combined_text and "Connect GitHub" in combined_text


def _error_summary(result: dict[str, Any]) -> str:
    error = str(result.get("error", "unknown error")).strip()
    return error.splitlines()[0] if error else "unknown error"


def _build_bug_description(result: dict[str, Any]) -> str:
    annotated_steps = build_annotated_steps(result, request_steps=REQUEST_STEPS)
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
        "## Missing or broken production capability",
        _missing_capability_summary(result),
        "",
        "## Environment details",
        f"- URL: {result.get('app_url')}",
        f"- Browser: {result.get('browser')}",
        f"- OS: {result.get('os')}",
        f"- Viewport: {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
        f"- Repository: {result.get('repository')} @ {result.get('repository_ref')}",
        f"- Run command: `{RUN_COMMAND}`",
        f"- Simulated delayed startup probe: GitHub `/user` delayed by {SIMULATED_PROBE_DELAY_SECONDS} seconds",
        f"- Timeout assertion window: {TIMEOUT_ASSERTION_SECONDS} seconds",
        f"- Post-release stability window: {POST_RELEASE_STABILITY_SECONDS} seconds",
        "",
        "## Failing command/output",
        f"- Command: `{RUN_COMMAND}`",
        f"- Error summary: `{_error_summary(result)}`",
        "",
        "## Screenshots or logs",
        f"- GitHub requests seen: `{json.dumps(result.get('github_request_urls', []), ensure_ascii=True)}`",
        f"- Delayed requests seen: `{json.dumps(result.get('delayed_request_urls', []), ensure_ascii=True)}`",
        f"- Timeout window observation: `{json.dumps(result.get('timeout_window_observation'), ensure_ascii=True)}`",
        f"- Final stability observation: `{json.dumps(result.get('final_stability_observation'), ensure_ascii=True)}`",
        f"- Stability samples: `{json.dumps(result.get('stability_samples', []), ensure_ascii=True)}`",
    ]
    if result.get("screenshot"):
        lines.append(f"- Screenshot: `{result['screenshot']}`")
    return "\n".join(lines) + "\n"


def _missing_capability_summary(result: dict[str, Any]) -> str:
    error = str(result.get("error", ""))
    if (
        "delayed GitHub `/user` startup probe never started" in error
        and "Needs sign-in" in error
    ):
        return (
            "The deployed app does not restore the valid stored GitHub token into an "
            "active hosted workspace during startup. The UI renders the hosted shell in "
            "`Needs sign-in` state, shows `Connect GitHub`, and never issues the GitHub "
            "`/user` auth probe that this startup path is supposed to run."
        )
    return (
        "The deployed app did not expose the production-visible startup behavior "
        "required to complete this test scenario."
    )


def _actual_result_summary(result: dict[str, Any], *, passed: bool) -> str:
    if passed:
        final_sample = result.get("final_stability_observation", {})
        return (
            "After the synchronization timeout elapsed while the delayed `/user` probe "
            "was still pending, the deployed app remained on the interactive shell and "
            "the late probe resolution did not reset the visible TopBar, branding, or "
            "route.\n"
            f"shell_ready_after_start_seconds={final_sample.get('shell_ready_after_start_seconds')!r}; "
            f"auth_probe_released_after_start_seconds="
            f"{final_sample.get('auth_probe_released_after_start_seconds')!r}; "
            f"trigger={final_sample.get('trigger')!r}"
        )
    return str(
        result.get(
            "error",
            "The deployed app did not keep the interactive shell stable through the "
            "late delayed-probe resolution.",
        ),
    )


def _step_lines(result: dict[str, Any], *, jira: bool) -> list[str]:
    return format_step_lines(result, jira=jira)


def _human_lines(result: dict[str, Any], *, jira: bool) -> list[str]:
    return format_human_lines(result, jira=jira)


if __name__ == "__main__":
    main()
