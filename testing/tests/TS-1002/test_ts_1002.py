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
TEST_DIR = Path(__file__).resolve().parent
if str(TEST_DIR) not in sys.path:
    sys.path.insert(0, str(TEST_DIR))

from support.ts1002_secondary_probe_delay_runtime import (  # noqa: E402
    STARTUP_SAMPLE_GLOBAL,
    Ts1002SecondaryProbeDelayRuntime,
    Ts1002SecondaryProbeObservation,
)
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
    elapsed_since,
    format_human_lines,
    format_step_lines,
    observe_live_startup_shell_window,
    prepare_local_workspace_repository,
    record_human_verification,
    record_not_reached_steps,
    record_step,
    relative_event_seconds,
    relative_startup_event_seconds,
    safe_trigger_payload,
    snippet,
    startup_surface_payload,
    write_test_automation_result,
)

TICKET_KEY = "TS-1002"
TEST_CASE_TITLE = (
    "Global startup utility - shell renders despite hang in a secondary critical-path probe"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-1002/test_ts_1002.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
DEFAULT_BRANCH = "main"
LOCAL_TARGET = "/tmp/trackstate-demo"
LOCAL_DISPLAY_NAME = "Active local workspace"
HOSTED_DISPLAY_NAME = "Hosted setup workspace"
SHELL_NAVIGATION_LABELS = ("Dashboard", "Board", "JQL Search", "Hierarchy", "Settings")
BRANDING_TEXT = "Git-native. Jira-compatible. Team-proven."
PRIMARY_AUTH_PATH = "/user"
SECONDARY_PROBE_PATH = "DEMO/project.json"
SYNC_TIMEOUT_SECONDS = 11
TIMEOUT_ASSERTION_SECONDS = 12
AUTH_DELAY_SECONDS = 1
SECONDARY_PROBE_DELAY_SECONDS = 31
AUTH_OBSERVATION_WAIT_SECONDS = 5
SECONDARY_PROBE_START_WAIT_SECONDS = 60
EVENTUAL_SHELL_WAIT_SECONDS = SECONDARY_PROBE_DELAY_SECONDS + 90
POLL_INTERVAL_SECONDS = 0.5
LINKED_BUGS = [
    "TS-1149",
    "TS-1145",
    "TS-1046",
    "TS-1045",
    "TS-1014",
    "TS-1013",
    "TS-1012",
    "TS-996",
    "TS-992",
]
LINKED_BUG_NOTES = (
    "Reviewed the linked startup bug chain from input/TS-1002/linked_bugs.md. "
    "TS-996, TS-1013, TS-1045, and TS-1145 require the shell to become "
    "interactive by the global 11-second timeout, TS-1012 plus TS-1046 extend "
    "that guarantee to secondary critical-path probes such as "
    "`DEMO/project.json`, TS-992 and TS-1014 require the live startup flow to "
    "exercise the `/user` probe path promptly instead of skipping or deferring "
    "it, and TS-1149 confirms the fallback session must remain safely "
    "restricted once the timeout-driven shell is visible. This test therefore "
    "keeps the `/user` delay short, delays the secondary probe for 31 seconds, "
    "and samples the live page at the 12-second checkpoint while that "
    "secondary probe is still pending."
)
REWORK_SUMMARY = (
    "Reused the approved TS-1002 live startup regression, kept the timeout-window "
    "sampling inside the browser while `DEMO/project.json` was still pending, and "
    "now fail fast unless the live startup flow establishes the required prompt "
    "`/user` probe precondition before the secondary-probe assertion runs."
)
CHECKPOINT_SAMPLE_TOLERANCE_SECONDS = 1.0

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
TIMEOUT_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1002_timeout_window.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1002_failure.png"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1002_success.png"

REQUEST_STEPS = [
    "Launch the TrackState application.",
    "Monitor the application startup sequence for the transition to the shell_ready state.",
    "Wait for the duration of the 11-second synchronization timeout window.",
]
EXPECTED_RESULT = (
    "The UI shell (TopBar, branding) renders and becomes interactive within the "
    "11-second window, confirming that the timeout utility is applied globally to "
    "all critical-path probes and is not limited solely to the authentication probe."
)


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)
    TIMEOUT_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-1002 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
        )

    hosted_workspace_id = f"hosted:{service.repository.lower()}@{DEFAULT_BRANCH}"
    workspace_state = _workspace_state(service.repository)
    prepared_local_workspace = _prepare_local_workspace_repository()
    observation = Ts1002SecondaryProbeObservation(repository=service.repository)
    runtime = Ts1002SecondaryProbeDelayRuntime(
        repository=config.repository,
        token=token,
        workspace_state=workspace_state,
        observation=observation,
        auth_delay_seconds=AUTH_DELAY_SECONDS,
        secondary_delay_seconds=SECONDARY_PROBE_DELAY_SECONDS,
        secondary_paths=(SECONDARY_PROBE_PATH,),
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
        "armed_auth_delay_seconds": AUTH_DELAY_SECONDS,
        "secondary_probe_delay_seconds": SECONDARY_PROBE_DELAY_SECONDS,
        "secondary_probe_path": SECONDARY_PROBE_PATH,
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
                page.set_viewport(**DESKTOP_VIEWPORT)
                startup_started_at_epoch_seconds = time.time()
                startup_started_at_monotonic = time.monotonic()
                tracker_page.open_entrypoint()
                result["startup_observation_initial"] = startup_surface_payload(
                    tracker_page,
                )

                secondary_probe_started, secondary_probe_snapshot = poll_until(
                    probe=lambda: {
                        "secondary_probe_started_at_monotonic": (
                            observation.secondary_probe_started_at_monotonic
                        ),
                        "github_request_urls": list(observation.github_request_urls),
                        "body_text": tracker_page.body_text(),
                    },
                    is_satisfied=lambda snapshot: (
                        snapshot["secondary_probe_started_at_monotonic"] is not None
                    ),
                    timeout_seconds=SECONDARY_PROBE_START_WAIT_SECONDS,
                    interval_seconds=POLL_INTERVAL_SECONDS,
                )
                auth_probe_released_early, auth_probe_snapshot = poll_until(
                    probe=lambda: {
                        "auth_probe_started_at_monotonic": (
                            observation.auth_probe_started_at_monotonic
                        ),
                        "auth_probe_released_at_monotonic": (
                            observation.auth_probe_released_at_monotonic
                        ),
                    },
                    is_satisfied=lambda snapshot: (
                        snapshot["auth_probe_released_at_monotonic"] is not None
                    ),
                    timeout_seconds=AUTH_OBSERVATION_WAIT_SECONDS,
                    interval_seconds=POLL_INTERVAL_SECONDS,
                )
                auth_probe_started_early = (
                    auth_probe_snapshot["auth_probe_started_at_monotonic"] is not None
                )

                result["secondary_probe_started_after_start_seconds"] = (
                    relative_startup_event_seconds(
                        startup_started_at_monotonic,
                        observation.secondary_probe_started_at_monotonic,
                    )
                )
                result["secondary_probe_released_after_start_seconds"] = (
                    relative_startup_event_seconds(
                        startup_started_at_monotonic,
                        observation.secondary_probe_released_at_monotonic,
                    )
                )
                result["armed_auth_probe_started_after_start_seconds"] = (
                    relative_startup_event_seconds(
                        startup_started_at_monotonic,
                        observation.auth_probe_started_at_monotonic,
                    )
                )
                result["armed_auth_probe_released_after_start_seconds"] = (
                    relative_startup_event_seconds(
                        startup_started_at_monotonic,
                        observation.auth_probe_released_at_monotonic,
                    )
                )
                result["github_request_urls"] = list(observation.github_request_urls)
                result["delayed_request_urls"] = list(observation.delayed_request_urls)
                result["delayed_auth_request_urls"] = list(
                    observation.delayed_auth_request_urls,
                )
                result["delayed_secondary_request_urls"] = list(
                    observation.delayed_secondary_request_urls,
                )

                if not secondary_probe_started:
                    _record_step(
                        result,
                        step=1,
                        status="failed",
                        action=REQUEST_STEPS[0],
                        observed=(
                            "The deployed app opened, but it never requested the delayed "
                            f"secondary startup artifact `{SECONDARY_PROBE_PATH}` so the "
                            "global timeout scenario was not exercised.\n"
                            f"Observed GitHub requests: {json.dumps(secondary_probe_snapshot['github_request_urls'], ensure_ascii=True)}\n"
                            f"Observed body text:\n{secondary_probe_snapshot['body_text']}"
                        ),
                    )
                    _record_not_reached_steps(
                        result,
                        starting_step=2,
                    )
                    raise AssertionError(
                        "Step 1 failed: the delayed secondary startup probe was never "
                        f"requested for `{SECONDARY_PROBE_PATH}`.\n"
                        f"Observed GitHub requests: {json.dumps(secondary_probe_snapshot['github_request_urls'], ensure_ascii=True)}\n"
                        f"Observed body text:\n{secondary_probe_snapshot['body_text']}",
                    )
                if not auth_probe_started_early or not auth_probe_released_early:
                    auth_precondition_error = _build_auth_precondition_error(
                        result=result,
                        tracker_page=tracker_page,
                        auth_probe_started_early=auth_probe_started_early,
                        auth_probe_released_early=auth_probe_released_early,
                    )
                    result["precondition_failure"] = auth_precondition_error
                    _record_step(
                        result,
                        step=1,
                        status="failed",
                        action=REQUEST_STEPS[0],
                        observed=auth_precondition_error,
                    )
                    _record_not_reached_steps(
                        result,
                        starting_step=2,
                    )
                    raise AssertionError(auth_precondition_error)

                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=REQUEST_STEPS[0],
                    observed=(
                        "Opened the deployed TrackState app in Chromium with a preloaded "
                        "local plus hosted workspace profile state, a synthetic "
                        f"{SECONDARY_PROBE_DELAY_SECONDS}-second delay on `{SECONDARY_PROBE_PATH}`, "
                        f"an armed {AUTH_DELAY_SECONDS}-second `/user` probe, and a verified "
                        f"prompt `/user` startup-path precondition.\n"
                        f"secondary_probe_started_after_start_seconds="
                        f"{result['secondary_probe_started_after_start_seconds']!r}; "
                        f"auth_probe_started_within_{AUTH_OBSERVATION_WAIT_SECONDS}_seconds="
                        f"{auth_probe_started_early!r}; "
                        f"auth_probe_released_within_{AUTH_OBSERVATION_WAIT_SECONDS}_seconds="
                        f"{auth_probe_released_early!r}; "
                        f"initial_body_text={snippet(tracker_page.body_text())!r}"
                    ),
                )

                transition_tracker = ShellReadyTransitionTracker()
                secondary_probe_started_at = observation.secondary_probe_started_at_monotonic
                timeout_reached = secondary_probe_started_at is not None
                if secondary_probe_started_at is None:
                    timeout_window = _observe_timeout_checkpoint(
                        tracker_page=tracker_page,
                        page=page,
                        runtime=runtime,
                        startup_started_at_epoch_seconds=startup_started_at_epoch_seconds,
                        startup_started_at_monotonic=startup_started_at_monotonic,
                        checkpoint_target_epoch_seconds=None,
                    )
                else:
                    timeout_deadline = (
                        secondary_probe_started_at + TIMEOUT_ASSERTION_SECONDS
                    )
                    while True:
                        remaining = timeout_deadline - time.monotonic()
                        if remaining <= 0:
                            break
                        time.sleep(min(POLL_INTERVAL_SECONDS, remaining))
                    timeout_window = _observe_timeout_checkpoint(
                        tracker_page=tracker_page,
                        page=page,
                        runtime=runtime,
                        startup_started_at_epoch_seconds=startup_started_at_epoch_seconds,
                        startup_started_at_monotonic=startup_started_at_monotonic,
                        checkpoint_target_epoch_seconds=(
                            observation.secondary_probe_started_at_epoch_seconds
                            + TIMEOUT_ASSERTION_SECONDS
                            if observation.secondary_probe_started_at_epoch_seconds is not None
                            else None
                        ),
                    )
                result["timeout_window_observation"] = timeout_window

                eventual_shell_ready, shell_ready_observation = poll_until(
                    probe=lambda: _observe_secondary_shell_window(
                        tracker_page=tracker_page,
                        page=page,
                        runtime=runtime,
                        startup_started_at_monotonic=startup_started_at_monotonic,
                        transition_tracker=transition_tracker,
                    ),
                    is_satisfied=lambda snapshot: bool(
                        snapshot["shell_observation"]["shell_ready"],
                    ),
                    timeout_seconds=EVENTUAL_SHELL_WAIT_SECONDS,
                    interval_seconds=POLL_INTERVAL_SECONDS,
                )
                result["eventual_shell_ready_observation"] = shell_ready_observation
                result["github_request_urls"] = list(observation.github_request_urls)
                result["delayed_request_urls"] = list(observation.delayed_request_urls)
                result["delayed_auth_request_urls"] = list(
                    observation.delayed_auth_request_urls,
                )
                result["delayed_secondary_request_urls"] = list(
                    observation.delayed_secondary_request_urls,
                )
                result["secondary_probe_release_after_start_seconds"] = (
                    relative_event_seconds(
                        observation.secondary_probe_started_at_monotonic,
                        observation.secondary_probe_released_at_monotonic,
                    )
                )

                failures: list[str] = []

                if eventual_shell_ready:
                    _record_step(
                        result,
                        step=2,
                        status="passed",
                        action=REQUEST_STEPS[1],
                        observed=(
                            "The deployed app eventually transitioned into `shell_ready`, "
                            "but only after continuing past the delayed secondary startup "
                            "probe window.\n"
                            f"shell_ready_after_start_seconds="
                            f"{shell_ready_observation['shell_ready_after_start_seconds']!r}; "
                            f"secondary_probe_released_after_start_seconds="
                            f"{shell_ready_observation['secondary_probe_released_after_start_seconds']!r}; "
                            f"auth_probe_started_after_start_seconds="
                            f"{result['armed_auth_probe_started_after_start_seconds']!r}; "
                            f"trigger={json.dumps(shell_ready_observation['trigger'], ensure_ascii=True)}"
                        ),
                    )
                else:
                    step_two_error = (
                        "Step 2 failed: the deployed app never transitioned into "
                        "`shell_ready` during the delayed secondary startup-probe scenario.\n"
                        f"Observed shell window:\n{json.dumps(shell_ready_observation, indent=2)}"
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
                if not timeout_reached:
                    step_three_error = (
                        "Step 3 failed: the test never reached the 11-second timeout "
                        "checkpoint for the delayed secondary startup probe.\n"
                        f"Observed timeout window:\n{json.dumps(timeout_window, indent=2)}"
                    )
                elif timeout_window.get("checkpoint_source") != "page_sampler":
                    step_three_error = (
                        "Step 3 failed: the test could not recover a trustworthy timeout-"
                        "window snapshot from the live page while the delayed secondary "
                        "probe was pending.\n"
                        f"Observed timeout window:\n{json.dumps(timeout_window, indent=2)}"
                    )
                elif abs(
                    float(timeout_window.get("checkpoint_sample_offset_seconds", 0.0)),
                ) > CHECKPOINT_SAMPLE_TOLERANCE_SECONDS:
                    step_three_error = (
                        "Step 3 failed: the recovered timeout-window snapshot drifted too "
                        "far from the intended 11-second checkpoint to be trustworthy.\n"
                        f"Observed timeout window:\n{json.dumps(timeout_window, indent=2)}"
                    )
                elif not bool(timeout_window["secondary_probe_pending"]):
                    step_three_error = (
                        "Step 3 failed: the recovered timeout-window snapshot was taken "
                        "after the delayed secondary probe had already been released, so "
                        "it cannot prove the 11-second startup behavior.\n"
                        f"Observed timeout window:\n{json.dumps(timeout_window, indent=2)}"
                    )
                elif not bool(timeout_window["shell_observation"]["shell_ready"]):
                    step_three_error = (
                        "Step 3 failed: after waiting through the 11-second timeout window "
                        f"for the delayed `{SECONDARY_PROBE_PATH}` fetch, the page still "
                        "had not reached `shell_ready` and still showed only the startup "
                        "surface instead of the interactive shell.\n"
                        f"Observed timeout window:\n{json.dumps(timeout_window, indent=2)}"
                    )
                else:
                    try:
                        _assert_shell_components(timeout_window)
                    except AssertionError as error:
                        step_three_error = str(error)

                if step_three_error is None:
                    _record_step(
                        result,
                        step=3,
                        status="passed",
                        action=REQUEST_STEPS[2],
                        observed=(
                            f"Recovered a checkpoint sample "
                            f"{timeout_window['checkpoint_sample_offset_seconds']!r} seconds "
                            "from the intended 11-second mark and "
                            f"{timeout_window['elapsed_since_secondary_probe_start_seconds']!r} "
                            "seconds from the delayed secondary probe start. The probe was "
                            f"still pending and the shell already exposed "
                            f"{json.dumps(timeout_window['shell_observation']['visible_navigation_labels'], ensure_ascii=True)}."
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

                _record_human_verification(
                    result,
                    check=(
                        "Viewed the live page at the 11-second timeout checkpoint the way a "
                        "user would and checked whether the TopBar workspace trigger, shell "
                        "navigation, and TrackState branding were actually visible."
                    ),
                    observed=(
                        f"body_text_snippet={snippet(timeout_window['startup_observation']['body_text'])!r}; "
                        f"trigger_label={(timeout_window['trigger'] or {}).get('semantic_label')!r}; "
                        f"visible_navigation_labels="
                        f"{json.dumps(timeout_window['shell_observation']['visible_navigation_labels'], ensure_ascii=True)}; "
                        f"branding_visible={timeout_window['branding_visible']!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Kept watching the live app after the delayed bootstrap fetch was "
                        "released to see when the shell finally became usable."
                    ),
                    observed=(
                        f"eventual_shell_ready={eventual_shell_ready!r}; "
                        f"shell_ready_after_start_seconds="
                        f"{shell_ready_observation['shell_ready_after_start_seconds']!r}; "
                        f"secondary_probe_released_after_start_seconds="
                        f"{shell_ready_observation['secondary_probe_released_after_start_seconds']!r}; "
                        f"auth_probe_started_after_start_seconds="
                        f"{result['armed_auth_probe_started_after_start_seconds']!r}"
                    ),
                )

                if failures:
                    raise AssertionError("\n\n".join(failures))

                tracker_page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
                _write_pass_outputs(result)
                print(f"{TICKET_KEY} passed")
                return
            except Exception:
                if not TIMEOUT_SCREENSHOT_PATH.exists():
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
        marker_filename=".trackstate-ts1002-precondition.txt",
        marker_contents="Prepared for TS-1002 delayed secondary startup probe validation.\n",
        commit_author_name="TS-1002 Automation",
        commit_author_email="ts1002@example.com",
        commit_message="Prepare TS-1002 local workspace",
    )


def _observe_secondary_shell_window(
    *,
    tracker_page: TrackStateTrackerPage,
    page: LiveWorkspaceSwitcherPage,
    runtime: Ts1002SecondaryProbeDelayRuntime,
    startup_started_at_monotonic: float,
    transition_tracker: ShellReadyTransitionTracker,
) -> dict[str, Any]:
    observation = observe_live_startup_shell_window(
        tracker_page=tracker_page,
        page=page,
        runtime=runtime,
        startup_started_at_monotonic=startup_started_at_monotonic,
        shell_navigation_labels=SHELL_NAVIGATION_LABELS,
        branding_texts=(BRANDING_TEXT, "TrackState.AI"),
        transition_tracker=transition_tracker,
    )
    observation["actual_auth_probe_pending"] = runtime.auth_probe_pending
    observation["actual_auth_probe_started_after_start_seconds"] = (
        relative_startup_event_seconds(
            startup_started_at_monotonic,
            runtime.observation.auth_probe_started_at_monotonic,
        )
    )
    observation["actual_auth_probe_released_after_start_seconds"] = (
        relative_startup_event_seconds(
            startup_started_at_monotonic,
            runtime.observation.auth_probe_released_at_monotonic,
        )
    )
    observation["secondary_probe_pending"] = runtime.secondary_probe_pending
    observation["secondary_probe_started_after_start_seconds"] = (
        relative_startup_event_seconds(
            startup_started_at_monotonic,
            runtime.observation.secondary_probe_started_at_monotonic,
        )
    )
    observation["secondary_probe_released_after_start_seconds"] = (
        relative_startup_event_seconds(
            startup_started_at_monotonic,
            runtime.observation.secondary_probe_released_at_monotonic,
        )
    )
    observation["elapsed_since_secondary_probe_start_seconds"] = elapsed_since(
        runtime.observation.secondary_probe_started_at_monotonic,
    )
    return observation


def _observe_timeout_checkpoint(
    *,
    tracker_page: TrackStateTrackerPage,
    page: LiveWorkspaceSwitcherPage,
    runtime: Ts1002SecondaryProbeDelayRuntime,
    startup_started_at_epoch_seconds: float,
    startup_started_at_monotonic: float,
    checkpoint_target_epoch_seconds: float | None,
) -> dict[str, Any]:
    del page
    sample = _select_startup_sample(
        tracker_page,
        checkpoint_target_epoch_seconds=checkpoint_target_epoch_seconds,
    )
    if sample is None:
        body_text = tracker_page.body_text()
        checkpoint_source = "live_read"
        checkpoint_sample_epoch_seconds = None
        checkpoint_sample_offset_seconds = None
        title = "TrackState.AI"
        location_href = tracker_page.app_url
        location_hash = ""
        location_pathname = (
            "/trackstate-setup/" if "trackstate-setup" in tracker_page.app_url else "/"
        )
    else:
        body_text = str(sample.get("bodyText", ""))
        checkpoint_source = "page_sampler"
        checkpoint_sample_epoch_seconds = round(float(sample["epochMs"]) / 1_000, 2)
        checkpoint_sample_offset_seconds = (
            None
            if checkpoint_target_epoch_seconds is None
            else round(
                checkpoint_sample_epoch_seconds - checkpoint_target_epoch_seconds,
                2,
            )
        )
        title = str(sample.get("title", "TrackState.AI"))
        location_href = str(sample.get("locationHref", tracker_page.app_url))
        location_hash = str(sample.get("locationHash", ""))
        location_pathname = str(
            sample.get(
                "locationPathname",
                "/trackstate-setup/" if "trackstate-setup" in tracker_page.app_url else "/",
            ),
        )
    normalized_lines = [
        " ".join(line.split())
        for line in body_text.splitlines()
        if " ".join(line.split())
    ]
    trigger_line = next(
        (line for line in normalized_lines if line.startswith("Workspace switcher:")),
        None,
    )
    visible_navigation_labels = [
        label for label in SHELL_NAVIGATION_LABELS if label in body_text
    ]
    startup_observation = {
        "title": title,
        "location_href": location_href,
        "location_hash": location_hash,
        "location_pathname": location_pathname,
        "body_text": body_text,
        "button_labels": [
            label
            for label in (
                "Dashboard",
                "Board",
                "JQL Search",
                "Hierarchy",
                "Settings",
                "Connect GitHub",
                "Create issue",
            )
            if label in body_text
        ],
    }
    sample_epoch_seconds = checkpoint_sample_epoch_seconds
    return {
        "checkpoint_source": checkpoint_source,
        "checkpoint_target_epoch_seconds": (
            round(checkpoint_target_epoch_seconds, 2)
            if checkpoint_target_epoch_seconds is not None
            else None
        ),
        "checkpoint_sample_epoch_seconds": checkpoint_sample_epoch_seconds,
        "checkpoint_sample_offset_seconds": checkpoint_sample_offset_seconds,
        "shell_observation": {
            "body_text": body_text,
            "visible_navigation_labels": visible_navigation_labels,
            "fatal_banner_visible": "TrackState data was not found" in body_text,
            "connect_github_visible": "Connect GitHub" in body_text,
            "shell_ready": len(visible_navigation_labels) == len(SHELL_NAVIGATION_LABELS),
        },
        "startup_observation": startup_observation,
        "trigger": (
            {"semantic_label": trigger_line, "visible_text": trigger_line}
            if trigger_line is not None
            else None
        ),
        "branding_visible": BRANDING_TEXT in body_text or "TrackState.AI" in body_text,
        "auth_pending": _request_pending_at_epoch(
            started_at_epoch_seconds=runtime.observation.auth_probe_started_at_epoch_seconds,
            released_at_epoch_seconds=runtime.observation.auth_probe_released_at_epoch_seconds,
            sample_epoch_seconds=sample_epoch_seconds,
        ),
        "auth_probe_started_after_start_seconds": relative_startup_event_seconds(
            startup_started_at_monotonic,
            runtime.observation.auth_probe_started_at_monotonic,
        ),
        "auth_probe_released_after_start_seconds": relative_startup_event_seconds(
            startup_started_at_monotonic,
            runtime.observation.auth_probe_released_at_monotonic,
        ),
        "auth_probe_release_after_auth_start_seconds": relative_event_seconds(
            runtime.observation.auth_probe_started_at_monotonic,
            runtime.observation.auth_probe_released_at_monotonic,
        ),
        "elapsed_since_auth_start_seconds": _relative_epoch_seconds(
            runtime.observation.auth_probe_started_at_epoch_seconds,
            sample_epoch_seconds,
        ),
        "shell_ready_after_start_seconds": (
            _relative_epoch_seconds(
                startup_started_at_epoch_seconds,
                sample_epoch_seconds,
            )
            if sample_epoch_seconds is not None
            and len(visible_navigation_labels) == len(SHELL_NAVIGATION_LABELS)
            else None
        ),
        "shell_ready_after_probe_release_seconds": None,
        "observed_pending_shell_samples": None,
        "shell_ready_observed_while_auth_pending": None,
        "actual_auth_probe_pending": _request_pending_at_epoch(
            started_at_epoch_seconds=runtime.observation.auth_probe_started_at_epoch_seconds,
            released_at_epoch_seconds=runtime.observation.auth_probe_released_at_epoch_seconds,
            sample_epoch_seconds=sample_epoch_seconds,
        ),
        "actual_auth_probe_started_after_start_seconds": (
            relative_startup_event_seconds(
                startup_started_at_monotonic,
                runtime.observation.auth_probe_started_at_monotonic,
            )
        ),
        "actual_auth_probe_released_after_start_seconds": (
            relative_startup_event_seconds(
                startup_started_at_monotonic,
                runtime.observation.auth_probe_released_at_monotonic,
            )
        ),
        "secondary_probe_pending": _request_pending_at_epoch(
            started_at_epoch_seconds=(
                runtime.observation.secondary_probe_started_at_epoch_seconds
            ),
            released_at_epoch_seconds=(
                runtime.observation.secondary_probe_released_at_epoch_seconds
            ),
            sample_epoch_seconds=sample_epoch_seconds,
        ),
        "secondary_probe_started_after_start_seconds": (
            relative_startup_event_seconds(
                startup_started_at_monotonic,
                runtime.observation.secondary_probe_started_at_monotonic,
            )
        ),
        "secondary_probe_released_after_start_seconds": (
            relative_startup_event_seconds(
                startup_started_at_monotonic,
                runtime.observation.secondary_probe_released_at_monotonic,
            )
        ),
        "elapsed_since_secondary_probe_start_seconds": _relative_epoch_seconds(
            runtime.observation.secondary_probe_started_at_epoch_seconds,
            sample_epoch_seconds,
        ),
    }


def _select_startup_sample(
    tracker_page: TrackStateTrackerPage,
    *,
    checkpoint_target_epoch_seconds: float | None,
) -> dict[str, Any] | None:
    raw_samples = tracker_page.session.evaluate(
        "({ key }) => globalThis[key] || []",
        arg={"key": STARTUP_SAMPLE_GLOBAL},
    )
    if not isinstance(raw_samples, list):
        return None
    samples = [
        sample
        for sample in raw_samples
        if isinstance(sample, dict) and isinstance(sample.get("epochMs"), (int, float))
    ]
    if not samples:
        return None
    if checkpoint_target_epoch_seconds is None:
        return dict(samples[-1])
    return dict(
        min(
            samples,
            key=lambda sample: abs(
                (float(sample["epochMs"]) / 1_000) - checkpoint_target_epoch_seconds,
            ),
        ),
    )


def _relative_epoch_seconds(
    started_at_epoch_seconds: float | None,
    event_epoch_seconds: float | None,
) -> float | None:
    if started_at_epoch_seconds is None or event_epoch_seconds is None:
        return None
    return round(event_epoch_seconds - started_at_epoch_seconds, 2)


def _request_pending_at_epoch(
    *,
    started_at_epoch_seconds: float | None,
    released_at_epoch_seconds: float | None,
    sample_epoch_seconds: float | None,
) -> bool:
    if (
        started_at_epoch_seconds is None
        or sample_epoch_seconds is None
        or sample_epoch_seconds < started_at_epoch_seconds
    ):
        return False
    if released_at_epoch_seconds is None:
        return True
    return sample_epoch_seconds < released_at_epoch_seconds


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


def _record_not_reached_steps(result: dict[str, Any], *, starting_step: int) -> None:
    record_not_reached_steps(
        result,
        starting_step=starting_step,
        request_steps=REQUEST_STEPS,
    )


def _assert_shell_components(observation: dict[str, Any]) -> None:
    shell = observation["shell_observation"]
    missing_navigation = [
        label for label in SHELL_NAVIGATION_LABELS if label not in shell["visible_navigation_labels"]
    ]
    if missing_navigation:
        raise AssertionError(
            "Step 3 failed: after waiting past the 11-second timeout for the delayed "
            f"`{SECONDARY_PROBE_PATH}` fetch, the page still did not expose the full "
            "interactive shell.\n"
            f"Missing labels: {missing_navigation}\n"
            f"Observed timeout window:\n{json.dumps(observation, indent=2)}",
        )
    if observation["trigger"] is None:
        raise AssertionError(
            "Step 3 failed: the timeout-window snapshot did not expose the TopBar "
            "workspace trigger, so the shell was not interactively usable within the "
            "required 11-second window.\n"
            f"Observed timeout window:\n{json.dumps(observation, indent=2)}",
        )
    if not bool(observation["branding_visible"]):
        raise AssertionError(
            "Step 3 failed: the timeout-window snapshot did not expose the visible "
            "TrackState branding text.\n"
            f"Observed timeout window:\n{json.dumps(observation, indent=2)}",
        )


def _build_auth_precondition_error(
    *,
    result: dict[str, Any],
    tracker_page: TrackStateTrackerPage,
    auth_probe_started_early: bool,
    auth_probe_released_early: bool,
) -> str:
    return (
        "Step 1 failed: the live startup flow did not establish the required prompt "
        f"`{PRIMARY_AUTH_PATH}` probe precondition before the delayed "
        f"`{SECONDARY_PROBE_PATH}` timeout assertion.\n"
        f"Required within {AUTH_OBSERVATION_WAIT_SECONDS} seconds: "
        f"auth_probe_started=True and auth_probe_released=True.\n"
        f"Observed: auth_probe_started={auth_probe_started_early!r}; "
        f"auth_probe_released={auth_probe_released_early!r}; "
        f"auth_probe_started_after_start_seconds="
        f"{result.get('armed_auth_probe_started_after_start_seconds')!r}; "
        f"auth_probe_released_after_start_seconds="
        f"{result.get('armed_auth_probe_released_after_start_seconds')!r}; "
        f"secondary_probe_started_after_start_seconds="
        f"{result.get('secondary_probe_started_after_start_seconds')!r}.\n"
        f"Observed GitHub requests: {json.dumps(result.get('github_request_urls', []), ensure_ascii=True)}\n"
        f"Observed delayed auth requests: "
        f"{json.dumps(result.get('delayed_auth_request_urls', []), ensure_ascii=True)}\n"
        f"Observed body text:\n{tracker_page.body_text()}\n"
        "The test cannot attribute a later shell-timeout failure solely to the "
        "secondary critical-path probe until the deployed app exposes this prompt "
        "startup `/user` capability."
    )


def _write_pass_outputs(result: dict[str, Any]) -> None:
    BUG_DESCRIPTION_PATH.unlink(missing_ok=True)
    write_test_automation_result(RESULT_PATH, passed=True)
    JIRA_COMMENT_PATH.write_text(_build_jira_comment(result, passed=True), encoding="utf-8")
    PR_BODY_PATH.write_text(_build_pr_body(result, passed=True), encoding="utf-8")
    RESPONSE_PATH.write_text(_build_response_summary(result, passed=True), encoding="utf-8")


def _write_failure_outputs(result: dict[str, Any]) -> None:
    error = str(result.get("error", f"AssertionError: {TICKET_KEY} failed"))
    if not error.startswith(("AssertionError:", "RuntimeError:", "ValueError:")):
        traceback_text = str(result.get("traceback", ""))
        if "AssertionError:" in traceback_text:
            error = f"AssertionError: {error}"
    write_test_automation_result(RESULT_PATH, passed=False, error=error)
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
        f"*Timing applied from linked bug*: waited {TIMEOUT_ASSERTION_SECONDS} seconds against an 11-second timeout window while delaying `{SECONDARY_PROBE_PATH}` for {SECONDARY_PROBE_DELAY_SECONDS} seconds",
        "",
        "h4. What was automated",
        "* Preloaded the deployed app with local plus hosted workspace profiles and stored token state.",
        f"* Delayed the hosted startup bootstrap fetch for {{{{code}}}}{SECONDARY_PROBE_PATH}{{{{code}}}} by {SECONDARY_PROBE_DELAY_SECONDS} seconds and armed a 1-second GitHub {{{{code}}}}/user{{{{code}}}} probe if the live startup flow reached it.",
        "* Waited past the linked 11-second timeout window before asserting, so the check targeted the deployed non-auth startup behavior rather than an early frame.",
        "* Verified the user-visible shell navigation, TopBar workspace trigger, and TrackState branding at the timeout checkpoint and after any eventual late recovery.",
        "",
        "h4. Automation checks",
        *format_step_lines(result, jira=True),
        "",
        "h4. Real user-style verification",
        *format_human_lines(result, jira=True),
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
        f"**Timing applied from linked bug:** waited `{TIMEOUT_ASSERTION_SECONDS}` seconds against an 11-second timeout window while delaying `{SECONDARY_PROBE_PATH}` for `{SECONDARY_PROBE_DELAY_SECONDS}` seconds",
        "",
        "## What was automated",
        "- Preloaded the deployed app with local plus hosted workspace profiles and stored token state.",
        f"- Delayed the hosted startup bootstrap fetch for `{SECONDARY_PROBE_PATH}` by `{SECONDARY_PROBE_DELAY_SECONDS}` seconds and armed a 1-second GitHub `/user` probe if the live startup flow reached it.",
        "- Waited past the linked 11-second timeout window before asserting so the check targeted the deployed non-auth startup behavior instead of checking too early.",
        "- Verified the visible shell navigation, TopBar workspace trigger, and TrackState branding at the timeout checkpoint and after any eventual late recovery.",
        "",
        "## Automation checks",
        *format_step_lines(result, jira=False),
        "",
        "## Real user-style verification",
        *format_human_lines(result, jira=False),
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
            f"The deployed app rendered the shell within the 11-second timeout window "
            f"even while `{SECONDARY_PROBE_PATH}` remained delayed.\n"
        )
    return (
        f"{TICKET_KEY} failed.\n\n"
        f"{REWORK_SUMMARY}\n\n"
        f"{result.get('error', 'The deployed app did not prove the global non-blocking startup timeout behavior.')}\n"
    )


def _build_bug_description(result: dict[str, Any]) -> str:
    annotated_steps = build_annotated_steps(result, request_steps=REQUEST_STEPS)
    missing_capability = (
        "The deployed startup flow must issue and complete the GitHub `/user` probe "
        f"within {AUTH_OBSERVATION_WAIT_SECONDS} seconds before this ticket's delayed "
        f"`{SECONDARY_PROBE_PATH}` scenario can prove the global secondary-probe timeout "
        "behavior."
        if result.get("precondition_failure")
        else "The deployed app must render the interactive shell within the global "
        f"11-second timeout window even while `{SECONDARY_PROBE_PATH}` remains pending."
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
        f"- **Missing or broken production capability:** {missing_capability}",
        "",
        "## Environment details",
        f"- URL: {result.get('app_url')}",
        f"- Browser: {result.get('browser')}",
        f"- OS: {result.get('os')}",
        f"- Viewport: {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
        f"- Repository: {result.get('repository')} @ {result.get('repository_ref')}",
        f"- Run command: `{RUN_COMMAND}`",
        f"- Delayed secondary startup probe: `{SECONDARY_PROBE_PATH}` delayed by {SECONDARY_PROBE_DELAY_SECONDS} seconds",
        f"- Armed auth probe: `{PRIMARY_AUTH_PATH}` delayed by {AUTH_DELAY_SECONDS} second if reached",
        f"- Timeout assertion window: {TIMEOUT_ASSERTION_SECONDS} seconds",
        "",
        "## Screenshots or logs",
        f"- GitHub requests seen: `{json.dumps(result.get('github_request_urls', []), ensure_ascii=True)}`",
        f"- Delayed auth requests seen: `{json.dumps(result.get('delayed_auth_request_urls', []), ensure_ascii=True)}`",
        f"- Delayed secondary requests seen: `{json.dumps(result.get('delayed_secondary_request_urls', []), ensure_ascii=True)}`",
        f"- Timeout window observation: `{json.dumps(result.get('timeout_window_observation'), ensure_ascii=True)}`",
        f"- Eventual shell observation: `{json.dumps(result.get('eventual_shell_ready_observation'), ensure_ascii=True)}`",
    ]
    if result.get("screenshot"):
        lines.append(f"- Screenshot: `{result['screenshot']}`")
    return "\n".join(lines) + "\n"


def _actual_result_summary(result: dict[str, Any], *, passed: bool) -> str:
    if passed:
        return (
            f"At the {TIMEOUT_ASSERTION_SECONDS}-second checkpoint after the delayed "
            f"`{SECONDARY_PROBE_PATH}` request began, the deployed app already exposed "
            "the full shell navigation, the TopBar workspace trigger, and visible "
            "TrackState branding."
        )
    if result.get("precondition_failure"):
        return str(result["precondition_failure"])
    timeout_window = result.get("timeout_window_observation", {})
    eventual = result.get("eventual_shell_ready_observation", {})
    return (
        f"At the {TIMEOUT_ASSERTION_SECONDS}-second checkpoint after `{SECONDARY_PROBE_PATH}` "
        f"started, the page still had shell_ready="
        f"{(timeout_window.get('shell_observation') or {}).get('shell_ready')!r}, "
        f"trigger={(timeout_window.get('trigger') or {}).get('semantic_label')!r}, and "
        f"visible_navigation_labels="
        f"{json.dumps((timeout_window.get('shell_observation') or {}).get('visible_navigation_labels', []), ensure_ascii=True)}. "
        f"The full shell only appeared around "
        f"{eventual.get('shell_ready_after_start_seconds')!r} seconds after launch, after the "
        f"delayed `{SECONDARY_PROBE_PATH}` fetch released at "
        f"{eventual.get('secondary_probe_released_after_start_seconds')!r} seconds."
    )


if __name__ == "__main__":
    main()
