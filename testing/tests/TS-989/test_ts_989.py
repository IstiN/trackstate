from __future__ import annotations

import json
import platform
import sys
import time
import traceback
from dataclasses import asdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
TEST_DIR = Path(__file__).resolve().parent
if str(TEST_DIR) not in sys.path:
    sys.path.insert(0, str(TEST_DIR))

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
    trigger_payload,
    try_observe_trigger,
    write_test_automation_result,
)
from support.ts989_startup_probe_failure_runtime import (  # noqa: E402
    Ts989StartupProbeFailureObservation,
    Ts989StartupProbeFailureRuntime,
)

TICKET_KEY = "TS-989"
TEST_CASE_TITLE = (
    "Startup synchronization probe immediate error — application shell renders via fallback"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-989/test_ts_989.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
DEFAULT_BRANCH = "main"
LOCAL_TARGET = "/tmp/trackstate-demo"
LOCAL_DISPLAY_NAME = "Active local workspace"
HOSTED_DISPLAY_NAME = "Hosted setup workspace"
SHELL_NAVIGATION_LABELS = ("Dashboard", "Board", "JQL Search", "Hierarchy", "Settings")
BRANDING_TEXT = "Git-native. Jira-compatible. Team-proven."
FULL_SYNC_TIMEOUT_SECONDS = 11
NON_BLOCKING_READY_THRESHOLD_SECONDS = 12
AUTH_PROBE_START_WAIT_SECONDS = 30
AUTH_PROBE_RELEASE_WAIT_SECONDS = 15
SHELL_READY_WAIT_SECONDS = FULL_SYNC_TIMEOUT_SECONDS + 10
POLL_INTERVAL_SECONDS = 0.25
LINKED_BUGS = ["TS-971"]
LINKED_BUG_NOTES = (
    "Reviewed input/TS-989/linked_bugs.md and found TS-971. Its fix established "
    "that startup must fall back to a non-blocking shell-ready path instead of "
    "waiting indefinitely on the GitHub startup probe, so this test allows the "
    f"live app up to {NON_BLOCKING_READY_THRESHOLD_SECONDS} seconds to prove the "
    "fallback shell after an immediate `/user` probe failure."
)
REWORK_SUMMARY = (
    "Added a live Playwright startup regression that aborts the initial GitHub "
    "`/user` synchronization probe immediately and verifies the deployed app still "
    "reaches shell_ready with a visible top bar and TrackState branding."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts989_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts989_failure.png"

REQUEST_STEPS = [
    "Launch the TrackState application.",
    "Observe the initialization sequence and the transition to the UI shell.",
    "Verify the visibility and interactivity of the UI shell components (TopBar, branding).",
]
EXPECTED_RESULT = (
    "The application does not block indefinitely or display a crash screen. It "
    "correctly handles the immediate startup probe rejection using the "
    "non-blocking initialization path and sets shell_ready=true so the UI shell "
    "remains interactive."
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
            "TS-989 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
        )

    workspace_state = _workspace_state(service.repository)
    prepared_local_workspace = _prepare_local_workspace_repository()
    failure_observation = Ts989StartupProbeFailureObservation()
    runtime = Ts989StartupProbeFailureRuntime(
        repository=config.repository,
        token=token,
        workspace_state=workspace_state,
        observation=failure_observation,
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
        "full_sync_timeout_seconds": FULL_SYNC_TIMEOUT_SECONDS,
        "non_blocking_ready_threshold_seconds": NON_BLOCKING_READY_THRESHOLD_SECONDS,
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
                        "GitHub token, preloaded local and hosted workspace state, and "
                        "a synthetic immediate failure on the first GitHub `/user` "
                        "startup probe."
                    ),
                )

                trigger_visible, initial_trigger = poll_until(
                    probe=lambda: _try_observe_trigger(page),
                    is_satisfied=lambda candidate: candidate is not None,
                    timeout_seconds=120,
                    interval_seconds=POLL_INTERVAL_SECONDS,
                )
                result["initial_trigger_observation"] = (
                    _trigger_payload(initial_trigger)
                    if trigger_visible and initial_trigger is not None
                    else None
                )
                if not trigger_visible or initial_trigger is None:
                    _record_step(
                        result,
                        step=2,
                        status="failed",
                        action=REQUEST_STEPS[1],
                        observed=(
                            "The deployed app never exposed the header workspace trigger "
                            "needed to observe the startup transition.\n"
                            f"Observed body text:\n{tracker_page.body_text()}"
                        ),
                    )
                    _record_not_reached_steps(result, starting_step=3)
                    raise AssertionError(
                        "Step 2 failed: the deployed app never exposed the header "
                        "workspace trigger needed to observe the startup transition.\n"
                        f"Observed body text:\n{tracker_page.body_text()}",
                    )

                if not runtime.wait_for_auth_probe_start(
                    timeout_seconds=AUTH_PROBE_START_WAIT_SECONDS,
                ):
                    _record_step(
                        result,
                        step=2,
                        status="failed",
                        action=REQUEST_STEPS[1],
                        observed=(
                            "The live app never started the GitHub `/user` startup probe, "
                            "so the immediate-rejection scenario was not exercised.\n"
                            f"Observed body text:\n{tracker_page.body_text()}"
                        ),
                    )
                    _record_not_reached_steps(result, starting_step=3)
                    raise AssertionError(
                        "Step 2 failed: the live app never started the GitHub `/user` "
                        "startup probe needed for TS-989.\n"
                        f"Observed body text:\n{tracker_page.body_text()}",
                    )

                if not runtime.wait_for_auth_probe_release(
                    timeout_seconds=AUTH_PROBE_RELEASE_WAIT_SECONDS,
                ):
                    _record_step(
                        result,
                        step=2,
                        status="failed",
                        action=REQUEST_STEPS[1],
                        observed=(
                            "The GitHub `/user` startup probe started, but the runtime "
                            "never observed the immediate failure/release event.\n"
                            f"Observed GitHub requests: {runtime.github_request_urls!r}"
                        ),
                    )
                    _record_not_reached_steps(result, starting_step=3)
                    raise AssertionError(
                        "Step 2 failed: the GitHub `/user` startup probe did not "
                        "settle after the synthetic immediate failure.\n"
                        f"Observed GitHub requests: {runtime.github_request_urls!r}",
                    )

                transition_tracker = ShellReadyTransitionTracker()
                shell_ready, shell_window = poll_until(
                    probe=lambda: observe_live_startup_shell_window(
                        tracker_page=tracker_page,
                        page=page,
                        runtime=runtime,
                        startup_started_at_monotonic=startup_started_at_monotonic,
                        shell_navigation_labels=SHELL_NAVIGATION_LABELS,
                        branding_texts=(BRANDING_TEXT, "TrackState.AI"),
                        transition_tracker=transition_tracker,
                    ),
                    is_satisfied=lambda observation: bool(
                        observation["shell_observation"]["shell_ready"]
                    )
                    and observation["auth_probe_released_after_start_seconds"] is not None,
                    timeout_seconds=SHELL_READY_WAIT_SECONDS,
                    interval_seconds=POLL_INTERVAL_SECONDS,
                )
                result["shell_window_observation"] = shell_window
                result["github_request_urls"] = list(runtime.github_request_urls)
                result["failed_request_urls"] = list(runtime.delayed_request_urls)
                result["failed_requests"] = [
                    asdict(request) for request in failure_observation.failed_requests
                ]

                shell_ready_after_start_seconds = shell_window["shell_ready_after_start_seconds"]
                auth_probe_released_after_start_seconds = shell_window[
                    "auth_probe_released_after_start_seconds"
                ]
                shell_ready_after_probe_release_seconds = shell_window[
                    "shell_ready_after_probe_release_seconds"
                ]
                pending_shell_samples = shell_window["observed_pending_shell_samples"]

                failures: list[str] = []
                if not failure_observation.failure_exercised:
                    failures.append(
                        "The synthetic immediate startup-probe failure was never exercised.",
                    )
                if not shell_ready:
                    failures.append(
                        "The live app never reached shell_ready after the immediate `/user` "
                        "startup probe failure.",
                    )
                if auth_probe_released_after_start_seconds is None:
                    failures.append(
                        "The startup probe failure time could not be measured.",
                    )
                if shell_ready_after_start_seconds is None:
                    failures.append(
                        "The shell_ready transition time could not be measured.",
                    )
                if (
                    shell_ready_after_start_seconds is not None
                    and shell_ready_after_start_seconds
                    > NON_BLOCKING_READY_THRESHOLD_SECONDS
                ):
                    failures.append(
                        "The shell became ready too slowly after the immediate startup "
                        f"probe failure. Observed {shell_ready_after_start_seconds!r} "
                        f"seconds from launch; allowed threshold "
                        f"{NON_BLOCKING_READY_THRESHOLD_SECONDS} seconds.",
                    )

                if failures:
                    observed = (
                        "The startup probe rejection was observed, but the deployed app did "
                        "not prove the non-blocking shell fallback.\n"
                        f"shell_ready_after_start_seconds={shell_ready_after_start_seconds!r}; "
                        f"auth_probe_released_after_start_seconds="
                        f"{auth_probe_released_after_start_seconds!r}; "
                        f"shell_ready_after_probe_release_seconds="
                        f"{shell_ready_after_probe_release_seconds!r}; "
                        f"observed_pending_shell_samples={pending_shell_samples!r}; "
                        f"failed_requests={json.dumps(result['failed_requests'], ensure_ascii=True)}\n"
                        + "\n".join(failures)
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

                trigger_visible, final_trigger = poll_until(
                    probe=lambda: _try_observe_trigger(page),
                    is_satisfied=lambda candidate: candidate is not None,
                    timeout_seconds=10,
                    interval_seconds=POLL_INTERVAL_SECONDS,
                )
                result["final_trigger_observation"] = (
                    _trigger_payload(final_trigger)
                    if trigger_visible and final_trigger is not None
                    else None
                )
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=REQUEST_STEPS[1],
                    observed=(
                        "The live app exercised the immediate GitHub `/user` startup probe "
                        "failure and still transitioned into shell_ready.\n"
                        f"shell_ready_after_start_seconds={shell_ready_after_start_seconds!r}; "
                        f"auth_probe_released_after_start_seconds="
                        f"{auth_probe_released_after_start_seconds!r}; "
                        f"shell_ready_after_probe_release_seconds="
                        f"{shell_ready_after_probe_release_seconds!r}; "
                        f"trigger={json.dumps(result['initial_trigger_observation'], ensure_ascii=True)}; "
                        f"failed_requests={json.dumps(result['failed_requests'], ensure_ascii=True)}"
                    ),
                )

                _assert_interactive_shell(shell_window)

                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action=REQUEST_STEPS[2],
                    observed=(
                        "The live shell snapshot after the startup probe failure exposed the "
                        "interactive shell rather than a crash or terminal startup surface.\n"
                        f"trigger={json.dumps(result['final_trigger_observation'], ensure_ascii=True)}; "
                        f"branding_visible={shell_window['branding_visible']!r}; "
                        f"visible_navigation_labels="
                        f"{json.dumps(shell_window['shell_observation']['visible_navigation_labels'], ensure_ascii=True)}; "
                        f"fatal_banner_visible={shell_window['shell_observation']['fatal_banner_visible']!r}"
                    ),
                )

                _record_human_verification(
                    result,
                    check=(
                        "Watched the live startup sequence like a user and confirmed the "
                        "page still transitioned into the real TrackState shell after the "
                        "immediate startup probe error."
                    ),
                    observed=(
                        f"shell_ready_after_start_seconds={shell_ready_after_start_seconds!r}; "
                        f"failed_request_urls={runtime.delayed_request_urls!r}; "
                        f"trigger_label={(result['final_trigger_observation'] or {}).get('semantic_label')!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Read the visible page content after recovery to confirm the user "
                        "saw top-bar navigation and TrackState branding instead of a crash "
                        "screen."
                    ),
                    observed=(
                        f"body_excerpt={_snippet(shell_window['shell_observation']['body_text'])!r}; "
                        f"visible_navigation_labels="
                        f"{shell_window['shell_observation']['visible_navigation_labels']!r}; "
                        f"branding_visible={shell_window['branding_visible']!r}; "
                        f"startup_buttons={shell_window['startup_observation']['button_labels']!r}"
                    ),
                )

                page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
                _write_pass_outputs(result)
                print(f"{TICKET_KEY} passed")
                return
            except Exception:
                if "screenshot" not in result:
                    page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                    result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                raise
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        result["github_request_urls"] = list(failure_observation.github_request_urls)
        result["failed_request_urls"] = list(failure_observation.failed_request_urls)
        result["failed_requests"] = [asdict(request) for request in failure_observation.failed_requests]
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
        marker_filename="TS-989-startup-probe-failure.txt",
        marker_contents=(
            "TS-989 local workspace marker for immediate startup probe failure fallback."
        ),
        commit_author_name="TS-989 Automation",
        commit_author_email="ts-989@example.com",
        commit_message="TS-989 local workspace seed",
    )


def _startup_surface_payload(tracker_page: TrackStateTrackerPage) -> dict[str, Any]:
    return startup_surface_payload(tracker_page)


def _try_observe_trigger(page: LiveWorkspaceSwitcherPage) -> Any | None:
    return try_observe_trigger(page)


def _trigger_payload(trigger: Any) -> dict[str, Any]:
    return trigger_payload(trigger)


def _assert_interactive_shell(observation: dict[str, Any]) -> None:
    shell = observation["shell_observation"]
    missing_navigation = [
        label
        for label in SHELL_NAVIGATION_LABELS
        if label not in shell["visible_navigation_labels"]
    ]
    if missing_navigation:
        raise AssertionError(
            "Step 3 failed: the shell snapshot after the startup probe failure did "
            "not expose the full interactive navigation.\n"
            f"Missing labels: {missing_navigation}\n"
            f"Observed shell window:\n{json.dumps(observation, indent=2)}",
        )
    if observation["trigger"] is None:
        raise AssertionError(
            "Step 3 failed: the shell snapshot did not expose the header workspace "
            "trigger needed to prove the TopBar was interactive.\n"
            f"Observed shell window:\n{json.dumps(observation, indent=2)}",
        )
    if not bool(observation["branding_visible"]):
        raise AssertionError(
            "Step 3 failed: the shell snapshot did not expose visible TrackState branding.\n"
            f"Observed shell window:\n{json.dumps(observation, indent=2)}",
        )
    if bool(shell["fatal_banner_visible"]):
        raise AssertionError(
            "Step 3 failed: the live page still exposed the fatal load banner instead "
            "of only the interactive shell.\n"
            f"Observed shell window:\n{json.dumps(observation, indent=2)}",
        )
    startup_buttons = set(observation["startup_observation"]["button_labels"])
    if startup_buttons == {"Sync issue"}:
        raise AssertionError(
            "Step 3 failed: the page still looked like the startup loading surface "
            "instead of the interactive shell when shell_ready was sampled.\n"
            f"Observed shell window:\n{json.dumps(observation, indent=2)}",
        )


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


def _write_failure_outputs(result: dict[str, Any]) -> None:
    error = str(result.get("error", f"AssertionError: {TICKET_KEY} failed"))
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
        "*Startup probe setup*: immediate abort of the first GitHub {/user} startup probe",
        f"*Non-blocking shell threshold checked*: {NON_BLOCKING_READY_THRESHOLD_SECONDS} seconds from launch",
        f"*Linked bug review*: {LINKED_BUG_NOTES}",
        "",
        "h4. What was automated",
        "* Opened the deployed TrackState app in Chromium with a stored GitHub token and preloaded local plus hosted workspace state.",
        "* Aborted the first GitHub {/user} startup probe immediately to simulate the initial synchronization handshake rejection from the ticket.",
        "* Waited for the live page to reach {shell_ready=true} instead of asserting immediately after launch.",
        "* Verified the visible page showed interactive shell navigation, the top-bar workspace trigger, and TrackState branding instead of a crash or terminal startup surface.",
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
        "**Startup probe setup:** immediate abort of the first GitHub `/user` startup probe",
        f"**Non-blocking shell threshold checked:** `{NON_BLOCKING_READY_THRESHOLD_SECONDS}` seconds from launch",
        f"**Linked bug review:** {LINKED_BUG_NOTES}",
        "",
        "## What was automated",
        "- Opened the deployed TrackState app in Chromium with a stored GitHub token and preloaded local plus hosted workspace state.",
        "- Aborted the first GitHub `/user` startup probe immediately to simulate the ticket's initial synchronization handshake rejection.",
        "- Waited for the live page to reach `shell_ready=true` instead of asserting immediately after launch.",
        "- Verified the visible page showed interactive shell navigation, the top-bar workspace trigger, and TrackState branding instead of a crash or terminal startup surface.",
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
            "The deployed app still reached shell_ready after the immediate startup "
            "probe failure and exposed navigation, the top-bar workspace trigger, "
            "and TrackState branding instead of a crash screen.\n"
        )
    return (
        f"{TICKET_KEY} failed.\n\n"
        f"{REWORK_SUMMARY}\n\n"
        f"{result.get('error', 'The deployed app did not prove the non-blocking startup fallback after an immediate probe failure.')}\n"
    )


def _build_bug_description(result: dict[str, Any]) -> str:
    annotated_steps = build_annotated_steps(result, request_steps=REQUEST_STEPS)
    shell_window = json.dumps(result.get("shell_window_observation"), ensure_ascii=True)
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
        "- Simulated startup probe failure: immediate abort of the first GitHub `/user` request",
        f"- Non-blocking shell threshold checked: {NON_BLOCKING_READY_THRESHOLD_SECONDS} seconds from launch",
        "",
        "## Screenshots or logs",
        f"- GitHub requests seen: `{json.dumps(result.get('github_request_urls', []), ensure_ascii=True)}`",
        f"- Failed request URLs: `{json.dumps(result.get('failed_request_urls', []), ensure_ascii=True)}`",
        f"- Failed request details: `{json.dumps(result.get('failed_requests', []), ensure_ascii=True)}`",
        f"- Shell observation: `{shell_window}`",
    ]
    if result.get("screenshot"):
        lines.append(f"- Screenshot: `{result['screenshot']}`")
    return "\n".join(lines) + "\n"


def _actual_result_summary(result: dict[str, Any], *, passed: bool) -> str:
    if passed:
        shell_window = result.get("shell_window_observation", {})
        return (
            "After the first GitHub `/user` startup probe failed immediately, the "
            "deployed app still reached shell_ready in "
            f"{shell_window.get('shell_ready_after_start_seconds')!r} seconds from "
            "launch and showed the interactive shell with visible navigation, the "
            "top-bar workspace trigger, and TrackState branding instead of a crash screen."
        )
    return str(
        result.get(
            "error",
            "The deployed app did not prove the non-blocking startup fallback after an immediate probe failure.",
        ),
    )


def _step_lines(result: dict[str, Any], *, jira: bool) -> list[str]:
    return format_step_lines(result, jira=jira)


def _human_lines(result: dict[str, Any], *, jira: bool) -> list[str]:
    return format_human_lines(result, jira=jira)


if __name__ == "__main__":
    main()
