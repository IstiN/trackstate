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

from support.ts1042_priority_queue_runtime import (  # noqa: E402
    Ts1042StartupPriorityObservation,
    Ts1042StartupPriorityQueueRuntime,
)
from testing.components.pages.trackstate_tracker_page import TrackStateTrackerPage  # noqa: E402
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.utils.polling import poll_until  # noqa: E402
from testing.tests.support.live_startup_case_support import (  # noqa: E402
    build_annotated_steps,
    build_workspace_state,
    format_human_lines,
    format_step_lines,
    prepare_local_workspace_repository,
    record_human_verification,
    record_not_reached_steps,
    record_step,
    snippet,
    startup_surface_payload,
    write_test_automation_result,
)

TICKET_KEY = "TS-1042"
TEST_CASE_TITLE = (
    "Startup priority queue dispatches the GitHub /user probe within 2000ms "
    "despite secondary repository latency"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-1042/test_ts_1042.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
DEFAULT_BRANCH = "main"
LOCAL_TARGET = "/tmp/trackstate-ts1042-demo"
LOCAL_DISPLAY_NAME = "Active local workspace"
HOSTED_DISPLAY_NAME = "Hosted setup workspace"
SHELL_NAVIGATION_LABELS = ("Dashboard", "Board", "JQL Search", "Hierarchy", "Settings")
PRIMARY_AUTH_PATH = "/user"
SECONDARY_PROBE_PATH = "DEMO/project.json"
SECONDARY_PROBE_URL_FRAGMENT = "git/trees/main?recursive=1"
PRIMARY_AUTH_DISPATCH_DEADLINE_SECONDS = 2.0
LINKED_BUG_AUTH_WINDOW_SECONDS = 5.0
AUTH_DELAY_SECONDS = 1.0
SECONDARY_PROBE_DELAY_SECONDS = 10.0
SECONDARY_PROBE_START_WAIT_SECONDS = 30.0
EVENTUAL_SHELL_WAIT_SECONDS = 20.0
POLL_INTERVAL_SECONDS = 0.1
LINKED_BUGS = ["TS-1038"]
LINKED_BUG_NOTES = (
    "Reviewed input/TS-1042/linked_bugs.md before writing the test. TS-1038 is "
    "marked Done and requires the deployed startup flow to dispatch the prompt "
    "GitHub `/user` probe early even while secondary bootstrap work such as "
    "repository bootstrap discovery remains delayed. The current deployment "
    "issues `git/trees/main?recursive=1` during startup before any direct "
    "`project.json` content fetch, so the latency injection targets that live "
    "secondary bootstrap request."
)
REWORK_SUMMARY = (
    "Reused the approved live-startup Playwright pattern from TS-1002, tightened "
    "the success criterion to the ticket's 2000ms `/user` dispatch deadline, and "
    "delayed the live `git/trees/main` repository bootstrap request so the "
    "assertion still runs against the real priority-queue startup path."
)

REQUEST_STEPS = [
    "Launch the TrackState application.",
    "Start a high-resolution timer immediately upon application initialization.",
    "Monitor network traffic specifically for the GitHub '/user' authentication probe.",
    "Record the timestamp when the '/user' request is initiated.",
    "Calculate the delta between application start and the probe initiation.",
]
EXPECTED_RESULT = (
    "The GitHub '/user' probe is initiated within 2000ms of the application "
    "start, confirming that the authentication lifecycle is no longer gated "
    "behind the resolution of secondary repository configuration requests."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1042_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1042_failure.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-1042 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
        )

    workspace_state = _workspace_state(service.repository)
    prepared_local_workspace = _prepare_local_workspace_repository()
    observation = Ts1042StartupPriorityObservation(repository=service.repository)
    runtime = Ts1042StartupPriorityQueueRuntime(
        repository=config.repository,
        token=token,
        workspace_state=workspace_state,
        observation=observation,
        auth_delay_seconds=AUTH_DELAY_SECONDS,
        secondary_delay_seconds=SECONDARY_PROBE_DELAY_SECONDS,
        secondary_paths=(SECONDARY_PROBE_URL_FRAGMENT,),
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
        "primary_auth_path": PRIMARY_AUTH_PATH,
        "secondary_probe_path": SECONDARY_PROBE_PATH,
        "secondary_probe_url_fragment": SECONDARY_PROBE_URL_FRAGMENT,
        "primary_auth_dispatch_deadline_seconds": PRIMARY_AUTH_DISPATCH_DEADLINE_SECONDS,
        "linked_bug_auth_window_seconds": LINKED_BUG_AUTH_WINDOW_SECONDS,
        "armed_auth_delay_seconds": AUTH_DELAY_SECONDS,
        "secondary_probe_delay_seconds": SECONDARY_PROBE_DELAY_SECONDS,
        "preloaded_workspace_state": workspace_state,
        "prepared_local_workspace": prepared_local_workspace,
        "steps": [],
        "human_verification": [],
        "is_product_failure": False,
    }

    try:
        with runtime as session:
            tracker_page = TrackStateTrackerPage(session, config.app_url)
            tracker_page.session.set_viewport_size(**DESKTOP_VIEWPORT)

            startup_started_at_monotonic = time.monotonic()
            tracker_page.open_entrypoint()
            _, initial_startup_observation = poll_until(
                probe=lambda: startup_surface_payload(tracker_page),
                is_satisfied=lambda snapshot: (
                    "TrackState.AI" in str(snapshot.get("body_text", ""))
                    or len(snapshot.get("button_labels", [])) > 0
                ),
                timeout_seconds=5.0,
                interval_seconds=0.25,
            )
            result["startup_observation_initial"] = initial_startup_observation
            result["startup_started_at_monotonic"] = round(startup_started_at_monotonic, 3)
            record_step(
                result,
                step=1,
                status="passed",
                action=REQUEST_STEPS[0],
                observed=(
                    "Opened the deployed TrackState app in Chromium with a preloaded "
                    "local plus hosted workspace profile state and an active 10-second "
                    f"delay on the secondary bootstrap request matching "
                    f"`{SECONDARY_PROBE_URL_FRAGMENT}`.\n"
                    f"initial_body_text={snippet(str(initial_startup_observation.get('body_text', '')))!r}"
                ),
            )

            secondary_probe_started, secondary_probe_snapshot = poll_until(
                probe=lambda: {
                    "secondary_probe_started_at_monotonic": (
                        observation.secondary_probe_started_at_monotonic
                    ),
                    "github_request_urls": list(observation.github_request_urls),
                },
                is_satisfied=lambda snapshot: (
                    snapshot["secondary_probe_started_at_monotonic"] is not None
                ),
                timeout_seconds=SECONDARY_PROBE_START_WAIT_SECONDS,
                interval_seconds=POLL_INTERVAL_SECONDS,
            )
            result["secondary_probe_started_after_start_seconds"] = _relative_seconds(
                startup_started_at_monotonic,
                observation.secondary_probe_started_at_monotonic,
            )
            result["secondary_probe_released_after_start_seconds"] = _relative_seconds(
                startup_started_at_monotonic,
                observation.secondary_probe_released_at_monotonic,
            )
            result["github_request_urls"] = list(observation.github_request_urls)
            result["delayed_request_urls"] = list(observation.delayed_request_urls)
            result["delayed_secondary_request_urls"] = list(
                observation.delayed_secondary_request_urls
            )

            if secondary_probe_started:
                record_step(
                    result,
                    step=2,
                    status="passed",
                    action=REQUEST_STEPS[1],
                    observed=(
                        "Started a monotonic timer immediately before app launch and "
                        "captured the delayed secondary bootstrap request "
                        f"matching `{SECONDARY_PROBE_URL_FRAGMENT}` "
                        f"{result['secondary_probe_started_after_start_seconds']!r} seconds "
                        "after startup began."
                    ),
                )
            else:
                step_two_error = (
                    "Step 2 failed: the delayed secondary startup request matching "
                    f"`{SECONDARY_PROBE_URL_FRAGMENT}` was never observed, so the requested "
                    "priority-queue scenario was not exercised.\n"
                    f"Observed GitHub requests: {json.dumps(secondary_probe_snapshot['github_request_urls'], ensure_ascii=True)}"
                )
                record_step(
                    result,
                    step=2,
                    status="failed",
                    action=REQUEST_STEPS[1],
                    observed=step_two_error,
                )
                record_not_reached_steps(
                    result,
                    starting_step=3,
                    request_steps=REQUEST_STEPS,
                )
                result["error"] = step_two_error
                result["traceback"] = step_two_error
                result["is_product_failure"] = True
                _write_failure_outputs(result)
                raise AssertionError(step_two_error)

            auth_probe_started_early, _ = poll_until(
                probe=lambda: {
                    "auth_probe_started_at_monotonic": observation.auth_probe_started_at_monotonic,
                },
                is_satisfied=lambda snapshot: (
                    snapshot["auth_probe_started_at_monotonic"] is not None
                ),
                timeout_seconds=PRIMARY_AUTH_DISPATCH_DEADLINE_SECONDS,
                interval_seconds=POLL_INTERVAL_SECONDS,
            )
            if auth_probe_started_early:
                auth_probe_started_in_window = True
            else:
                remaining_window = max(
                    0.0,
                    LINKED_BUG_AUTH_WINDOW_SECONDS
                    - (time.monotonic() - startup_started_at_monotonic),
                )
                auth_probe_started_in_window, _ = poll_until(
                    probe=lambda: {
                        "auth_probe_started_at_monotonic": observation.auth_probe_started_at_monotonic,
                    },
                    is_satisfied=lambda snapshot: (
                        snapshot["auth_probe_started_at_monotonic"] is not None
                    ),
                    timeout_seconds=remaining_window,
                    interval_seconds=POLL_INTERVAL_SECONDS,
                )

            result["auth_probe_started_after_start_seconds"] = _relative_seconds(
                startup_started_at_monotonic,
                observation.auth_probe_started_at_monotonic,
            )
            result["auth_probe_released_after_start_seconds"] = _relative_seconds(
                startup_started_at_monotonic,
                observation.auth_probe_released_at_monotonic,
            )
            result["delayed_auth_request_urls"] = list(observation.delayed_auth_request_urls)
            result["secondary_pending_when_auth_started"] = _secondary_pending_when_auth_started(
                observation
            )

            step_three_passed = auth_probe_started_in_window
            step_three_observed = (
                "Observed GitHub `/user` traffic during startup.\n"
                f"auth_probe_started_after_start_seconds={result['auth_probe_started_after_start_seconds']!r}; "
                f"delayed_auth_request_urls={json.dumps(result['delayed_auth_request_urls'], ensure_ascii=True)}"
                if step_three_passed
                else "Step 3 failed: no GitHub `/user` request was observed within the "
                f"{LINKED_BUG_AUTH_WINDOW_SECONDS}-second linked-bug observation window.\n"
                f"Observed GitHub requests: {json.dumps(result['github_request_urls'], ensure_ascii=True)}"
            )
            record_step(
                result,
                step=3,
                status="passed" if step_three_passed else "failed",
                action=REQUEST_STEPS[2],
                observed=step_three_observed,
            )

            step_four_passed = (
                observation.auth_probe_started_at_monotonic is not None
                and bool(result["secondary_pending_when_auth_started"])
            )
            if step_four_passed:
                step_four_observed = (
                    "Recorded the `/user` request initiation timestamp while the delayed "
                    f"secondary bootstrap request matching `{SECONDARY_PROBE_URL_FRAGMENT}` "
                    "was still pending.\n"
                    f"auth_probe_started_after_start_seconds={result['auth_probe_started_after_start_seconds']!r}; "
                    f"secondary_pending_when_auth_started={result['secondary_pending_when_auth_started']!r}"
                )
            elif observation.auth_probe_started_at_monotonic is None:
                step_four_observed = (
                    "Step 4 failed: the test could not record a `/user` initiation "
                    "timestamp because the request never appeared.\n"
                    f"Observed GitHub requests: {json.dumps(result['github_request_urls'], ensure_ascii=True)}"
                )
            else:
                step_four_observed = (
                    "Step 4 failed: the `/user` request was only seen after the delayed "
                    f"secondary request matching `{SECONDARY_PROBE_URL_FRAGMENT}` had already cleared, so the live "
                    "result did not demonstrate the intended overlapping-latency scenario.\n"
                    f"auth_probe_started_after_start_seconds={result['auth_probe_started_after_start_seconds']!r}; "
                    f"secondary_probe_released_after_start_seconds={result['secondary_probe_released_after_start_seconds']!r}"
                )
            record_step(
                result,
                step=4,
                status="passed" if step_four_passed else "failed",
                action=REQUEST_STEPS[3],
                observed=step_four_observed,
            )

            dispatch_delta_seconds = _raw_relative_seconds(
                startup_started_at_monotonic,
                observation.auth_probe_started_at_monotonic,
            )
            result["auth_probe_dispatch_delta_seconds"] = (
                round(dispatch_delta_seconds, 3)
                if dispatch_delta_seconds is not None
                else None
            )
            step_five_passed = (
                dispatch_delta_seconds is not None
                and dispatch_delta_seconds <= PRIMARY_AUTH_DISPATCH_DEADLINE_SECONDS
            )
            if step_five_passed:
                step_five_observed = (
                    "Calculated the startup-to-`/user` dispatch delta and confirmed it met "
                    f"the ticket requirement.\n"
                    f"dispatch_delta_seconds={result['auth_probe_dispatch_delta_seconds']!r}; "
                    f"deadline_seconds={PRIMARY_AUTH_DISPATCH_DEADLINE_SECONDS!r}"
                )
            else:
                step_five_observed = (
                    "Step 5 failed: the GitHub `/user` probe was not initiated within the "
                    "required 2000ms startup window.\n"
                    f"dispatch_delta_seconds={result['auth_probe_dispatch_delta_seconds']!r}; "
                    f"deadline_seconds={PRIMARY_AUTH_DISPATCH_DEADLINE_SECONDS!r}; "
                    f"auth_probe_started_after_start_seconds={result['auth_probe_started_after_start_seconds']!r}"
                )
            record_step(
                result,
                step=5,
                status="passed" if step_five_passed else "failed",
                action=REQUEST_STEPS[4],
                observed=step_five_observed,
            )

            eventual_shell_ready, shell_observation = poll_until(
                probe=lambda: tracker_page.observe_interactive_shell(
                    SHELL_NAVIGATION_LABELS,
                    timeout_ms=1_000,
                ),
                is_satisfied=lambda snapshot: bool(snapshot.get("shell_ready")),
                timeout_seconds=EVENTUAL_SHELL_WAIT_SECONDS,
                interval_seconds=0.5,
            )
            result["eventual_shell_observation"] = shell_observation
            record_human_verification(
                result,
                check=(
                    "Viewed the startup UI immediately after launch to confirm the user saw "
                    "the TrackState.AI startup surface while the delayed secondary request "
                    "was still in flight."
                ),
                observed=(
                    f"initial_body_text={snippet(str((result['startup_observation_initial'] or {}).get('body_text', '')))!r}; "
                    f"button_labels={json.dumps((result['startup_observation_initial'] or {}).get('button_labels', []), ensure_ascii=True)}"
                ),
            )
            record_human_verification(
                result,
                check=(
                    "Kept watching the live app after the `/user` probe was captured to see "
                    "whether the desktop shell became visible from a user perspective."
                ),
                observed=(
                    f"eventual_shell_ready={eventual_shell_ready!r}; "
                    f"visible_navigation_labels={json.dumps(shell_observation.get('visible_navigation_labels', []), ensure_ascii=True)}; "
                    f"shell_body_text={snippet(str(shell_observation.get('body_text', '')))!r}"
                ),
            )

            if not step_three_passed or not step_four_passed or not step_five_passed:
                failure_messages = [
                    step["observed"]
                    for step in result.get("steps", [])
                    if isinstance(step, dict) and step.get("status") == "failed"
                ]
                result["error"] = "\n\n".join(str(message) for message in failure_messages)
                result["traceback"] = result["error"]
                result["is_product_failure"] = True
                try:
                    tracker_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                    result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                except Exception as screenshot_error:  # pragma: no cover - diagnostics only
                    result["screenshot_error"] = (
                        f"{type(screenshot_error).__name__}: {screenshot_error}"
                    )
                _write_failure_outputs(result)
                raise AssertionError(str(result["error"]))

            tracker_page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
            result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
            _write_pass_outputs(result)
            print(f"{TICKET_KEY} passed")
    except AssertionError:
        raise
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        result["is_product_failure"] = False
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
        marker_filename=".trackstate-ts1042-precondition.txt",
        marker_contents="Prepared for TS-1042 startup priority queue validation.\n",
        commit_author_name="TS-1042 Automation",
        commit_author_email="ts1042@example.com",
        commit_message="Prepare TS-1042 local workspace",
    )


def _raw_relative_seconds(
    startup_started_at_monotonic: float,
    event_monotonic: float | None,
) -> float | None:
    if event_monotonic is None:
        return None
    return event_monotonic - startup_started_at_monotonic


def _relative_seconds(
    startup_started_at_monotonic: float,
    event_monotonic: float | None,
) -> float | None:
    raw = _raw_relative_seconds(startup_started_at_monotonic, event_monotonic)
    return None if raw is None else round(raw, 3)


def _secondary_pending_when_auth_started(
    observation: Ts1042StartupPriorityObservation,
) -> bool | None:
    if observation.auth_probe_started_at_monotonic is None:
        return None
    if observation.secondary_probe_started_at_monotonic is None:
        return False
    if observation.secondary_probe_released_at_monotonic is None:
        return True
    return (
        observation.auth_probe_started_at_monotonic
        <= observation.secondary_probe_released_at_monotonic
    )


def _write_pass_outputs(result: dict[str, Any]) -> None:
    BUG_DESCRIPTION_PATH.unlink(missing_ok=True)
    write_test_automation_result(RESULT_PATH, passed=True)
    JIRA_COMMENT_PATH.write_text(_build_jira_comment(result, passed=True), encoding="utf-8")
    PR_BODY_PATH.write_text(_build_pr_body(result, passed=True), encoding="utf-8")
    RESPONSE_PATH.write_text(_build_response_summary(result, passed=True), encoding="utf-8")


def _write_failure_outputs(result: dict[str, Any]) -> None:
    error = str(result.get("error", f"AssertionError: {TICKET_KEY} failed"))
    if result.get("is_product_failure"):
        write_test_automation_result(RESULT_PATH, passed=False, error=error)
        BUG_DESCRIPTION_PATH.write_text(_build_bug_description(result), encoding="utf-8")
    else:
        write_test_automation_result(RESULT_PATH, passed=False, error=error)
        BUG_DESCRIPTION_PATH.unlink(missing_ok=True)
    JIRA_COMMENT_PATH.write_text(_build_jira_comment(result, passed=False), encoding="utf-8")
    PR_BODY_PATH.write_text(_build_pr_body(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_build_response_summary(result, passed=False), encoding="utf-8")


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
        (
            "*Timing applied from linked bug*: delayed "
        f"`{SECONDARY_PROBE_URL_FRAGMENT}` for {SECONDARY_PROBE_DELAY_SECONDS} seconds and "
            f"waited up to {LINKED_BUG_AUTH_WINDOW_SECONDS} seconds to observe the "
            "prompt `/user` startup path"
        ),
        "",
        "h4. What was automated",
        "* Preloaded the deployed app with local plus hosted workspace profiles and stored token state.",
        f"* Delayed the live repository bootstrap request {{{{code}}}}{SECONDARY_PROBE_URL_FRAGMENT}{{{{code}}}} by {SECONDARY_PROBE_DELAY_SECONDS} seconds.",
        "* Captured the GitHub `/user` initiation timestamp from the Playwright route layer and compared it to the launch-time monotonic timer.",
        "* Verified the visible startup surface immediately after launch and recorded the later shell state for human-style confirmation.",
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
        (
            f"**Timing applied from linked bug:** delayed `{SECONDARY_PROBE_URL_FRAGMENT}` for "
            f"`{SECONDARY_PROBE_DELAY_SECONDS}` seconds and allowed a "
            f"`{LINKED_BUG_AUTH_WINDOW_SECONDS}`-second observation window for the prompt `/user` path"
        ),
        "",
        "## What was automated",
        "- Preloaded the deployed app with local plus hosted workspace profiles and stored token state.",
        f"- Delayed the live repository bootstrap request matching `{SECONDARY_PROBE_URL_FRAGMENT}` by `{SECONDARY_PROBE_DELAY_SECONDS}` seconds so the secondary-latency startup scenario was exercised on the current deployment.",
        "- Captured the GitHub `/user` initiation timestamp from Playwright route interception and compared it to the startup timer.",
        "- Recorded both the immediate startup surface and the later shell state for user-perspective verification.",
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
            f"The live deployment initiated `/user` "
            f"{result.get('auth_probe_dispatch_delta_seconds')!r} seconds after launch "
            f"while the delayed request matching `{SECONDARY_PROBE_URL_FRAGMENT}` remained in flight.\n"
        )
    return (
        f"{TICKET_KEY} failed.\n\n"
        f"{REWORK_SUMMARY}\n\n"
        f"{result.get('error', 'The deployed app did not dispatch the /user probe within 2000ms under secondary latency.')}\n"
    )


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
        (
            "- **Missing or broken production capability:** the live startup priority "
            "queue must dispatch the GitHub `/user` probe within 2000ms even while "
            f"the secondary bootstrap request matching `{SECONDARY_PROBE_URL_FRAGMENT}` is still delayed."
        ),
        "",
        "## Environment details",
        f"- URL: {result.get('app_url')}",
        f"- Browser: {result.get('browser')}",
        f"- OS: {result.get('os')}",
        f"- Viewport: {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
        f"- Repository: {result.get('repository')} @ {result.get('repository_ref')}",
        f"- Run command: `{RUN_COMMAND}`",
        f"- Delayed secondary startup probe: `{SECONDARY_PROBE_URL_FRAGMENT}` delayed by {SECONDARY_PROBE_DELAY_SECONDS} seconds",
        f"- Linked-bug observation window: {LINKED_BUG_AUTH_WINDOW_SECONDS} seconds",
        "",
        "## Screenshots or logs",
        f"- GitHub requests seen: `{json.dumps(result.get('github_request_urls', []), ensure_ascii=True)}`",
        f"- Delayed auth requests seen: `{json.dumps(result.get('delayed_auth_request_urls', []), ensure_ascii=True)}`",
        f"- Delayed secondary requests seen: `{json.dumps(result.get('delayed_secondary_request_urls', []), ensure_ascii=True)}`",
        f"- Initial startup observation: `{json.dumps(result.get('startup_observation_initial'), ensure_ascii=True)}`",
        f"- Eventual shell observation: `{json.dumps(result.get('eventual_shell_observation'), ensure_ascii=True)}`",
    ]
    if result.get("screenshot"):
        lines.append(f"- Screenshot: `{result['screenshot']}`")
    return "\n".join(lines) + "\n"


def _actual_result_summary(result: dict[str, Any], *, passed: bool) -> str:
    if passed:
        return (
            f"The live deployment initiated `/user` "
            f"{result.get('auth_probe_dispatch_delta_seconds')!r} seconds after launch, "
            f"with `secondary_pending_when_auth_started`="
            f"{result.get('secondary_pending_when_auth_started')!r}, while "
            f"the request matching `{SECONDARY_PROBE_URL_FRAGMENT}` was delayed for {SECONDARY_PROBE_DELAY_SECONDS} seconds."
        )
    return (
        f"The live deployment recorded `/user` at "
        f"{result.get('auth_probe_dispatch_delta_seconds')!r} seconds after launch "
        f"(deadline {PRIMARY_AUTH_DISPATCH_DEADLINE_SECONDS!r}) with "
        f"`secondary_pending_when_auth_started`="
        f"{result.get('secondary_pending_when_auth_started')!r}. "
        f"Observed GitHub requests: {json.dumps(result.get('github_request_urls', []), ensure_ascii=True)}"
    )


if __name__ == "__main__":
    main()
