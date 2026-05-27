from __future__ import annotations

from dataclasses import asdict
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
from testing.components.services.startup_state_machine_validator import (  # noqa: E402
    StartupStateMachineReachabilityValidator,
    StartupStateSample,
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
    write_test_automation_result,
)
from testing.tests.support.ts1032_startup_state_machine_runtime import (  # noqa: E402
    Ts1032StartupStateMachineRuntime,
)
from testing.tests.support.ts984_delayed_auth_probe_runtime import (  # noqa: E402
    Ts984DelayedAuthProbeRuntime,
)

TICKET_KEY = "TS-1032"
TEST_CASE_TITLE = (
    "Startup state machine - validator confirms reachability of bootstrap and pending phases"
)
TEST_FILE_PATH = "testing/tests/TS-1032/test_ts_1032.py"
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-1032/test_ts_1032.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
DEFAULT_BRANCH = "main"
LOCAL_TARGET = "/tmp/trackstate-ts1032-local"
LOCAL_DISPLAY_NAME = "TS-1032 local workspace"
HOSTED_DISPLAY_NAME = "Hosted setup workspace"
SHELL_NAVIGATION_LABELS = ("Dashboard", "Board", "JQL Search", "Hierarchy", "Settings")
BRANDING_TEXTS = ("Git-native. Jira-compatible. Team-proven.", "TrackState.AI")
SIMULATED_PROBE_DELAY_SECONDS = 5
AUTH_PROBE_START_WAIT_SECONDS = 60
RESOLUTION_WAIT_SECONDS = 30
POLL_INTERVAL_SECONDS = 0.25
MIN_PENDING_SAMPLE_COUNT = 5
MIN_PENDING_OBSERVATION_SECONDS = 2.0
PENDING_SAMPLE_WINDOW_TOLERANCE_SECONDS = 0.25
LINKED_BUGS = ("TS-1029", "TS-1027")
LINKED_BUG_NOTES = (
    "Reviewed TS-1029 and TS-1027. Their merged fixes restored the delayed GitHub "
    "`/user` startup probe path, so this test waits through a real delayed probe "
    "window instead of asserting immediately and validates the live bootstrap -> "
    "pending -> resolved sequence with phase sampling."
)
REQUEST_STEPS = [
    "Access the state machine validator utility for the application startup sequence.",
    "Execute the validation check against the initialization logic map.",
    "Confirm that a valid transition path exists from the bootstrap phase to the pending probe phase and subsequently to the resolved phase.",
]
EXPECTED_RESULT = (
    "The validator confirms all startup phases are reachable and correctly sequenced "
    "(bootstrap -> pending -> resolved), ensuring no missing transitions exist in "
    "the initialization state machine."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
BOOTSTRAP_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1032_bootstrap.png"
PENDING_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1032_pending.png"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1032_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1032_failure.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    BOOTSTRAP_SCREENSHOT_PATH.unlink(missing_ok=True)
    PENDING_SCREENSHOT_PATH.unlink(missing_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-1032 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
        )

    workspace_state = _workspace_state(service.repository)
    prepared_local_workspace = _prepare_local_workspace_repository()
    validator = StartupStateMachineReachabilityValidator(
        required_navigation_labels=SHELL_NAVIGATION_LABELS,
        application_title="TrackState.AI",
    )
    runtime = Ts1032StartupStateMachineRuntime(
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
        "simulated_probe_delay_seconds": SIMULATED_PROBE_DELAY_SECONDS,
        "linked_bugs": list(LINKED_BUGS),
        "linked_bug_notes": LINKED_BUG_NOTES,
        "logic_map": validator.logic_map,
        "preloaded_workspace_state": workspace_state,
        "prepared_local_workspace": prepared_local_workspace,
        "steps": [],
        "human_verification": [],
    }

    try:
        with runtime as session:
            tracker_page = TrackStateTrackerPage(session, config.app_url)
            page = LiveWorkspaceSwitcherPage(tracker_page)
            transition_tracker = ShellReadyTransitionTracker()
            latest_window: dict[str, Any] | None = None

            try:
                page.set_viewport(**DESKTOP_VIEWPORT)
                startup_started_at_monotonic = time.monotonic()
                page.open_startup_entrypoint(wait_until="commit", timeout_ms=120_000)

                initial_window = _observe_shell_window(
                    tracker_page=tracker_page,
                    page=page,
                    runtime=runtime,
                    startup_started_at_monotonic=startup_started_at_monotonic,
                    transition_tracker=transition_tracker,
                )
                latest_window = initial_window
                initial_sample = _sample_from_window(initial_window)
                samples = [initial_sample]
                result["startup_observation_initial"] = initial_window["startup_observation"]
                tracker_page.screenshot(str(BOOTSTRAP_SCREENSHOT_PATH))
                result["bootstrap_screenshot"] = str(BOOTSTRAP_SCREENSHOT_PATH)

                auth_probe_started = runtime.wait_for_auth_probe_start(
                    timeout_seconds=AUTH_PROBE_START_WAIT_SECONDS,
                )
                result["github_request_urls"] = list(runtime.github_request_urls)
                result["delayed_request_urls"] = list(runtime.delayed_request_urls)
                if not auth_probe_started or runtime.auth_probe_started_at_monotonic is None:
                    observed = (
                        "The live app never started the delayed GitHub `/user` startup "
                        "probe, so the pending startup phase was never reachable.\n"
                        f"Initial startup observation:\n"
                        f"{json.dumps(result['startup_observation_initial'], indent=2)}\n"
                        f"GitHub requests seen:\n{json.dumps(result['github_request_urls'], indent=2)}\n"
                        f"Delayed requests seen:\n{json.dumps(result['delayed_request_urls'], indent=2)}"
                    )
                    _record_step(
                        result,
                        step=1,
                        status="failed",
                        action=REQUEST_STEPS[0],
                        observed=observed,
                    )
                    _record_not_reached_steps(result, starting_step=2)
                    raise AssertionError(f"Step 1 failed: {observed}")

                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=REQUEST_STEPS[0],
                    observed=(
                        "Instantiated the startup state-machine validator utility and opened "
                        "the deployed TrackState app with a delayed GitHub `/user` startup "
                        "probe to capture live phase samples.\n"
                        f"logic_map={json.dumps(validator.logic_map, indent=2)}\n"
                        f"initial_sample={_sample_payload(initial_sample)}\n"
                        f"delayed_request_urls={runtime.delayed_request_urls!r}"
                    ),
                )

                tracker_page.screenshot(str(PENDING_SCREENSHOT_PATH))
                result["pending_screenshot"] = str(PENDING_SCREENSHOT_PATH)

                resolved_window = _wait_for_resolved_window(
                    tracker_page=tracker_page,
                    page=page,
                    runtime=runtime,
                    startup_started_at_monotonic=startup_started_at_monotonic,
                    transition_tracker=transition_tracker,
                )
                latest_window = resolved_window if resolved_window is not None else latest_window
                pending_probe_state = runtime.read_pending_shell_probe_state()
                result["pending_probe_state"] = pending_probe_state
                auth_probe_started_after_start_seconds = (
                    None
                    if resolved_window is None
                    else resolved_window.get("auth_probe_started_after_start_seconds")
                )
                auth_probe_released_after_start_seconds = (
                    None
                    if resolved_window is None
                    else resolved_window.get("auth_probe_released_after_start_seconds")
                )
                pending_samples = _pending_samples_from_probe_state(
                    pending_probe_state=pending_probe_state,
                    auth_probe_started_after_start_seconds=auth_probe_started_after_start_seconds,
                    auth_probe_released_after_start_seconds=auth_probe_released_after_start_seconds,
                )
                samples.extend(pending_samples)
                if resolved_window is not None:
                    samples.append(_sample_from_window(resolved_window))
                result["startup_samples"] = [_sample_payload(sample) for sample in samples]

                pending_window_duration_seconds = _pending_window_duration_seconds(
                    pending_samples,
                )
                result["pending_sample_count"] = len(pending_samples)
                result["pending_window_duration_seconds"] = pending_window_duration_seconds

                validation_result = validator.validate(samples)
                result["validation_result"] = _validation_result_payload(validation_result)
                result["phase_path"] = list(validation_result.phase_path)

                execution_failures = _validation_execution_failures(
                    samples=samples,
                    pending_samples=pending_samples,
                    pending_window_duration_seconds=pending_window_duration_seconds,
                )
                if execution_failures:
                    observed = (
                        "The validator did not receive enough live startup evidence to "
                        "evaluate the initialization logic map reliably.\n"
                        f"sample_count={len(samples)!r}; "
                        f"pending_sample_count={len(pending_samples)!r}; "
                        f"pending_window_duration_seconds={pending_window_duration_seconds!r}; "
                        f"phase_path={list(validation_result.phase_path)!r}\n"
                        + "\n".join(execution_failures)
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
                        "Executed the startup state-machine validator against the observed "
                        "live initialization logic map.\n"
                        f"sample_count={len(samples)!r}; "
                        f"pending_sample_count={len(pending_samples)!r}; "
                        f"pending_window_duration_seconds={pending_window_duration_seconds!r}; "
                        f"validation_result={json.dumps(result['validation_result'], indent=2)}"
                    ),
                )

                phase_failures = list(validation_result.failures)
                if resolved_window is None:
                    phase_failures.append(
                        "The live app never reached a resolved startup sample with the full "
                        "interactive shell.",
                    )
                else:
                    phase_failures.extend(_interactive_shell_failures(resolved_window))

                if phase_failures:
                    observed = (
                        "The validator did not confirm a complete bootstrap -> pending -> "
                        "resolved startup path in the live app.\n"
                        f"phase_path={list(validation_result.phase_path)!r}; "
                        f"phase_matches={json.dumps(result['validation_result']['phase_matches'], indent=2)}\n"
                        + "\n".join(phase_failures)
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
                        "The validator confirmed that the observed startup path reached "
                        "bootstrap, pending, and resolved in order, and the resolved sample "
                        "exposed the interactive shell only after the delayed probe phase.\n"
                        f"phase_path={list(validation_result.phase_path)!r}; "
                        f"phase_matches={json.dumps(result['validation_result']['phase_matches'], indent=2)}"
                    ),
                )

                _record_human_verification(
                    result,
                    check=(
                        "Watched the live page like a user right after launch and confirmed "
                        "the startup surface showed the app title without the interactive "
                        "shell."
                    ),
                    observed=(
                        f"bootstrap_sample={_sample_payload(initial_sample)!r}; "
                        f"bootstrap_screenshot={str(BOOTSTRAP_SCREENSHOT_PATH)!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Watched the delayed startup window and confirmed the app remained "
                        "on the loading surface while the GitHub `/user` probe was pending."
                    ),
                    observed=(
                        f"pending_sample_count={len(pending_samples)!r}; "
                        f"pending_window_duration_seconds={pending_window_duration_seconds!r}; "
                        f"pending_screenshot={str(PENDING_SCREENSHOT_PATH)!r}"
                    ),
                )
                if resolved_window is not None:
                    _record_human_verification(
                        result,
                        check=(
                            "Watched the page after resolution and confirmed the visible "
                            "Dashboard, Board, JQL Search, Hierarchy, Settings, workspace "
                            "switcher trigger, and TrackState branding appeared."
                        ),
                        observed=(
                            f"resolved_sample={_sample_payload(_sample_from_window(resolved_window))!r}; "
                            f"trigger={(resolved_window['trigger'] or {}).get('semantic_label')!r}; "
                            f"branding_visible={resolved_window['branding_visible']!r}"
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
        marker_filename=".trackstate-ts1032-precondition.txt",
        marker_contents="Prepared for TS-1032 startup state-machine validation.\n",
        commit_author_name="TS-1032 Automation",
        commit_author_email="ts1032@example.com",
        commit_message="Prepare TS-1032 local workspace",
    )


def _observe_shell_window(
    *,
    tracker_page: TrackStateTrackerPage,
    page: LiveWorkspaceSwitcherPage,
    runtime: Ts984DelayedAuthProbeRuntime,
    startup_started_at_monotonic: float,
    transition_tracker: ShellReadyTransitionTracker | None = None,
    poll_timeout_ms: int = 250,
) -> dict[str, Any]:
    shell_window = observe_live_startup_shell_window(
        tracker_page=tracker_page,
        page=page,
        runtime=runtime,
        startup_started_at_monotonic=startup_started_at_monotonic,
        shell_navigation_labels=SHELL_NAVIGATION_LABELS,
        branding_texts=BRANDING_TEXTS,
        transition_tracker=transition_tracker,
        poll_timeout_ms=poll_timeout_ms,
    )
    shell_window["elapsed_since_start_seconds"] = round(
        time.monotonic() - startup_started_at_monotonic,
        2,
    )
    shell_window["shell_probe_state"] = runtime.read_shell_probe_state()
    shell_window["probe_recorded_shell_ready_after_start_seconds"] = shell_window[
        "shell_probe_state"
    ].get("first_shell_ready_after_launch_seconds")
    return shell_window


def _sample_from_window(window: dict[str, Any]) -> StartupStateSample:
    shell_observation = window["shell_observation"]
    startup_observation = window["startup_observation"]
    trigger = window.get("trigger") or {}
    trigger_label = trigger.get("semantic_label")
    return StartupStateSample(
        observed_after_start_seconds=float(window["elapsed_since_start_seconds"]),
        auth_pending=bool(window["auth_pending"]),
        shell_ready=bool(shell_observation["shell_ready"]),
        visible_navigation_labels=tuple(
            str(label) for label in shell_observation["visible_navigation_labels"]
        ),
        startup_button_labels=tuple(
            str(label) for label in startup_observation["button_labels"]
        ),
        startup_body_text=str(startup_observation["body_text"]),
        shell_body_text=str(shell_observation["body_text"]),
        branding_visible=bool(window["branding_visible"]),
        trigger_label=None if trigger_label in (None, "") else str(trigger_label),
    )


def _sample_payload(sample: StartupStateSample) -> dict[str, Any]:
    return {
        "observed_after_start_seconds": round(sample.observed_after_start_seconds, 2),
        "auth_pending": sample.auth_pending,
        "shell_ready": sample.shell_ready,
        "visible_navigation_labels": list(sample.visible_navigation_labels),
        "startup_button_labels": list(sample.startup_button_labels),
        "startup_body_excerpt": _snippet(sample.startup_body_text),
        "shell_body_excerpt": _snippet(sample.shell_body_text),
        "branding_visible": sample.branding_visible,
        "trigger_label": sample.trigger_label,
    }


def _wait_for_resolved_window(
    *,
    tracker_page: TrackStateTrackerPage,
    page: LiveWorkspaceSwitcherPage,
    runtime: Ts1032StartupStateMachineRuntime,
    startup_started_at_monotonic: float,
    transition_tracker: ShellReadyTransitionTracker,
    poll_timeout_ms: int = 250,
) -> dict[str, Any] | None:
    found, resolved_window = poll_until(
        probe=lambda: _observe_shell_window(
            tracker_page=tracker_page,
            page=page,
            runtime=runtime,
            startup_started_at_monotonic=startup_started_at_monotonic,
            transition_tracker=transition_tracker,
            poll_timeout_ms=poll_timeout_ms,
        ),
        is_satisfied=lambda window: (
            not bool(window["auth_pending"])
            and bool(window["shell_observation"]["shell_ready"])
        ),
        timeout_seconds=RESOLUTION_WAIT_SECONDS,
        interval_seconds=POLL_INTERVAL_SECONDS,
    )
    return resolved_window if found else None


def _pending_window_duration_seconds(
    pending_samples: list[StartupStateSample],
) -> float | None:
    if not pending_samples:
        return None
    if len(pending_samples) == 1:
        return 0.0
    return round(
        pending_samples[-1].observed_after_start_seconds
        - pending_samples[0].observed_after_start_seconds,
        2,
    )


def _pending_samples_from_probe_state(
    *,
    pending_probe_state: dict[str, Any],
    auth_probe_started_after_start_seconds: float | None,
    auth_probe_released_after_start_seconds: float | None,
) -> list[StartupStateSample]:
    samples = pending_probe_state.get("samples", [])
    if not isinstance(samples, list):
        return []

    pending_samples: list[StartupStateSample] = []
    for sample in samples:
        if not isinstance(sample, dict):
            continue
        observed_after_launch_seconds = sample.get("observed_after_launch_seconds")
        if not isinstance(observed_after_launch_seconds, (int, float)):
            continue
        if (
            auth_probe_started_after_start_seconds is not None
            and float(observed_after_launch_seconds)
            < float(auth_probe_started_after_start_seconds)
            - PENDING_SAMPLE_WINDOW_TOLERANCE_SECONDS
        ):
            continue
        if (
            auth_probe_released_after_start_seconds is not None
            and float(observed_after_launch_seconds)
            > float(auth_probe_released_after_start_seconds)
            + PENDING_SAMPLE_WINDOW_TOLERANCE_SECONDS
        ):
            continue
        pending_samples.append(
            StartupStateSample(
                observed_after_start_seconds=round(float(observed_after_launch_seconds), 2),
                auth_pending=True,
                shell_ready=bool(sample.get("shell_ready")),
                visible_navigation_labels=tuple(
                    str(label) for label in sample.get("visible_navigation_labels", [])
                ),
                startup_button_labels=(),
                startup_body_text=str(sample.get("body_excerpt", "")),
                shell_body_text=str(sample.get("body_excerpt", "")),
                branding_visible=bool(sample.get("branding_visible")),
                trigger_label=(
                    str(sample.get("trigger_label"))
                    if sample.get("trigger_label")
                    else None
                ),
            ),
        )
    return pending_samples


def _validation_execution_failures(
    *,
    samples: list[StartupStateSample],
    pending_samples: list[StartupStateSample],
    pending_window_duration_seconds: float | None,
) -> list[str]:
    failures: list[str] = []
    if len(samples) < 3:
        failures.append(
            "Fewer than three startup samples were captured, so the validator could not "
            "compare bootstrap, pending, and resolved evidence.",
        )
    if len(pending_samples) < MIN_PENDING_SAMPLE_COUNT:
        failures.append(
            "The delayed pending phase was not observed for enough live samples. "
            f"Expected at least {MIN_PENDING_SAMPLE_COUNT} pending samples but captured "
            f"{len(pending_samples)}.",
        )
    if (
        pending_window_duration_seconds is None
        or pending_window_duration_seconds < MIN_PENDING_OBSERVATION_SECONDS
    ):
        failures.append(
            "The delayed pending phase was not observed for long enough to prove the "
            "phase was reachable and stable. "
            f"Expected at least {MIN_PENDING_OBSERVATION_SECONDS} seconds but captured "
            f"{pending_window_duration_seconds!r}.",
        )
    return failures


def _interactive_shell_failures(observation: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    shell = observation["shell_observation"]
    missing_navigation = [
        label
        for label in SHELL_NAVIGATION_LABELS
        if label not in shell["visible_navigation_labels"]
    ]
    if missing_navigation:
        failures.append(
            "The resolved startup sample did not expose the full interactive shell "
            f"navigation. Missing labels: {missing_navigation}",
        )
    if observation["trigger"] is None:
        failures.append(
            "The resolved startup sample did not expose the workspace switcher trigger.",
        )
    if not bool(observation["branding_visible"]):
        failures.append(
            "The resolved startup sample did not expose visible TrackState branding.",
        )
    return failures


def _validation_result_payload(result: Any) -> dict[str, Any]:
    return {
        "logic_map": result.logic_map,
        "phase_path": list(result.phase_path),
        "phase_matches": [asdict(match) for match in result.phase_matches],
        "failures": list(result.failures),
    }


def _snippet(text: str, *, limit: int = 220) -> str:
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
        f"*Test Case:* {TICKET_KEY} - {TEST_CASE_TITLE}",
        "",
        "h4. What was tested",
        f"* Live deployed app at {{{result.get('app_url')}}} in {result.get('browser')} on {result.get('os')}",
        f"* Desktop viewport {{{DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}}}",
        f"* Validator logic map: bootstrap -> pending -> resolved",
        f"* Delayed GitHub {{/user}} startup probe held for {SIMULATED_PROBE_DELAY_SECONDS} seconds",
        f"* Linked bug review: {LINKED_BUG_NOTES}",
        "",
        "h4. Result",
        "* Opened the deployed TrackState app in Chromium with preloaded workspace state and a delayed GitHub startup probe.",
        "* Sampled the live startup window instead of asserting immediately so the pending phase was observable.",
        "* Executed the validator utility against the observed startup logic map.",
        "* Confirmed the user-visible shell only became interactive after the resolved phase."
        if passed
        else f"* Failed while validating the requested startup path. Actual issue: {_actual_result_summary(result, passed=False)}",
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
    for key, label in (
        ("bootstrap_screenshot", "*Bootstrap screenshot*"),
        ("pending_screenshot", "*Pending screenshot*"),
        ("screenshot", "*Final screenshot*"),
    ):
        if result.get(key):
            lines.extend(["", f"{label}: {result[key]}"])
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
        f"**Test Case:** {TICKET_KEY} - {TEST_CASE_TITLE}",
        "",
        "## What was automated",
        f"- Ran the live deployed app at `{result.get('app_url')}` in {result.get('browser')} on {result.get('os')}.",
        f"- Used the desktop viewport `{DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}`.",
        f"- Delayed the GitHub `/user` startup probe by `{SIMULATED_PROBE_DELAY_SECONDS}` seconds so the pending phase was observable.",
        "- Executed a validator utility against the observed startup logic map to confirm `bootstrap -> pending -> resolved` reachability.",
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
    for key, label in (
        ("bootstrap_screenshot", "Bootstrap screenshot"),
        ("pending_screenshot", "Pending screenshot"),
        ("screenshot", "Final screenshot"),
    ):
        if result.get(key):
            lines.extend(["", f"- **{label}:** `{result[key]}`"])
    lines.extend(["", "## Run command", "", "```bash", RUN_COMMAND, "```"])
    if not passed:
        lines.extend(
            [
                "",
                "## Assertion / error",
                "",
                "```text",
                str(result.get("traceback", result.get("error", ""))),
                "```",
            ],
        )
    return "\n".join(lines) + "\n"


def _build_response_summary(result: dict[str, Any], *, passed: bool) -> str:
    status = "PASSED" if passed else "FAILED"
    lines = [
        f"# {TICKET_KEY} {status}",
        "",
        f"**Test case:** {TEST_CASE_TITLE}",
        f"**Status:** {'passed' if passed else 'failed'}",
        f"**App URL:** `{result.get('app_url')}`",
        "",
        "## Summary",
        _actual_result_summary(result, passed=passed),
        "",
        "## Automation checks",
        *format_step_lines(result, jira=False),
        "",
        "## Real user-style verification",
        *format_human_lines(result, jira=False),
    ]
    if not passed:
        lines.extend(
            [
                "",
                "## Assertion / error",
                "",
                "```text",
                str(result.get("traceback", result.get("error", ""))),
                "```",
            ],
        )
    return "\n".join(lines) + "\n"


def _build_bug_description(result: dict[str, Any]) -> str:
    lines = [
        f"# Bug Report - {TICKET_KEY}",
        "",
        f"**Summary:** {_actual_result_summary(result, passed=False)}",
        "",
        "## Steps to reproduce",
        *build_annotated_steps(result, request_steps=REQUEST_STEPS),
        "",
        "## Expected result",
        EXPECTED_RESULT,
        "",
        "## Actual result",
        _actual_result_summary(result, passed=False),
        "",
        "## Exact assertion / error",
        "```text",
        str(result.get("traceback", result.get("error", ""))),
        "```",
        "",
        "## Environment",
        f"- URL: `{result.get('app_url')}`",
        f"- Browser: {result.get('browser')}",
        f"- OS: {result.get('os')}",
        f"- Viewport: `{DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}`",
        f"- Delayed GitHub `/user` probe: `{SIMULATED_PROBE_DELAY_SECONDS}` seconds",
        "",
        "## Logs and screenshots",
    ]
    for key, label in (
        ("bootstrap_screenshot", "Bootstrap screenshot"),
        ("pending_screenshot", "Pending screenshot"),
        ("screenshot", "Failure screenshot"),
    ):
        if result.get(key):
            lines.append(f"- {label}: `{result[key]}`")
    if result.get("validation_result"):
        lines.extend(
            [
                "- Validation result:",
                "```json",
                json.dumps(result["validation_result"], indent=2),
                "```",
            ],
        )
    return "\n".join(lines) + "\n"


def _actual_result_summary(result: dict[str, Any], *, passed: bool) -> str:
    validation_result = result.get("validation_result", {})
    phase_matches = validation_result.get("phase_matches", [])
    phase_path = validation_result.get("phase_path", result.get("phase_path", []))
    if passed:
        return (
            "The live validator observed a complete bootstrap -> pending -> resolved "
            f"path and the resolved sample exposed the interactive shell. phase_path="
            f"{phase_path!r}; phase_matches={phase_matches!r}"
        )
    error = result.get("error", "")
    if error:
        return (
            "The startup validator could not confirm the required bootstrap -> pending "
            f"-> resolved path. phase_path={phase_path!r}; error={error}"
        )
    return (
        "The startup validator could not confirm the required bootstrap -> pending -> "
        f"resolved path. phase_path={phase_path!r}; phase_matches={phase_matches!r}"
    )


if __name__ == "__main__":
    main()
