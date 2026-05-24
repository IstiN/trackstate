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

from testing.components.pages.live_create_issue_gate_page import LiveCreateIssueGatePage  # noqa: E402
from testing.components.pages.live_workspace_switcher_page import (  # noqa: E402
    LiveWorkspaceSwitcherPage,
    WorkspaceSwitcherTriggerObservation,
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
    build_annotated_steps,
    build_workspace_state,
    format_human_lines,
    format_step_lines,
    record_human_verification,
    record_not_reached_steps,
    record_step,
    relative_startup_event_seconds,
    safe_trigger_payload,
    snippet,
    startup_surface_payload,
    trigger_payload,
    write_test_automation_result,
)
from testing.tests.support.ts1001_delayed_auth_session_probe_factory import (  # noqa: E402
    create_ts1001_delayed_auth_session_probe,
)

TICKET_KEY = "TS-1001"
TEST_CASE_TITLE = "Fallback state session — capabilities are restricted after 11s startup timeout"
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-1001/test_ts_1001.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
DEFAULT_BRANCH = "main"
LOCAL_TARGET = "/tmp/trackstate-ts1001-local"
LOCAL_DISPLAY_NAME = "Active local workspace"
HOSTED_DISPLAY_NAME = "Hosted setup workspace"
SHELL_NAVIGATION_LABELS = ("Dashboard", "Board", "JQL Search", "Hierarchy", "Settings")
BRANDING_TEXT = "Git-native. Jira-compatible. Team-proven."
SYNC_TIMEOUT_SECONDS = 11
TIMEOUT_ASSERTION_SECONDS = 12
SIMULATED_PROBE_DELAY_SECONDS = 30
STARTUP_WAIT_SECONDS = 120
POLL_INTERVAL_SECONDS = 0.5
LINKED_BUGS = ["TS-1022", "TS-1014", "TS-1013", "TS-1012", "TS-996", "TS-992"]
LINKED_BUG_NOTES = (
    "Reviewed the linked startup bugs and kept the async wait explicit: the live browser "
    "flow waits beyond the 11-second startup window, and the real production provider "
    "probe delays GitHub `/user` by 30 seconds before asserting the restricted session flags."
)

REQUEST_STEPS = [
    "Launch the TrackState application.",
    "Wait for the 11-second synchronization timeout to expire and the UI shell to render (shell_ready=true).",
    "Access the session metadata or inspect the state of a write-enabled action (e.g., 'Save' or 'Create Branch').",
    "Verify the 'canWrite' and 'canCreateBranch' flags are set to false.",
]
EXPECTED_RESULT = (
    "The application enters the shell_ready state, but the session reflects the "
    "default fallback state with restricted capabilities, ensuring data integrity "
    "is maintained while the authentication remains unresolved."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
REVIEW_REPLIES_PATH = OUTPUTS_DIR / "review_replies.json"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1001_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1001_failure.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-1001 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
        )

    workspace_state = _workspace_state(service.repository)
    runtime = DelayedAuthWorkspaceProfilesRuntime(
        repository=config.repository,
        token=token,
        workspace_state=workspace_state,
        auth_delay_seconds=SIMULATED_PROBE_DELAY_SECONDS,
        delayed_paths=("/user",),
    )
    delayed_auth_probe = create_ts1001_delayed_auth_session_probe(REPO_ROOT)

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
        "preloaded_workspace_state": workspace_state,
        "steps": [],
        "human_verification": [],
        "product_failure": False,
    }

    tracker_page: TrackStateTrackerPage | None = None
    try:
        with runtime as session:
            tracker_page = TrackStateTrackerPage(session, config.app_url)
            switcher_page = LiveWorkspaceSwitcherPage(tracker_page)
            create_gate_page = LiveCreateIssueGatePage(tracker_page)

            switcher_page.set_viewport(**DESKTOP_VIEWPORT)
            startup_started_at_monotonic = time.monotonic()
            tracker_page.open_entrypoint()
            result["startup_observation_initial"] = startup_surface_payload(tracker_page)

            shell_ready, shell_observation = poll_until(
                probe=lambda: _observe_live_shell(tracker_page, switcher_page),
                is_satisfied=_is_interactive_shell_observation,
                timeout_seconds=STARTUP_WAIT_SECONDS,
                interval_seconds=POLL_INTERVAL_SECONDS,
            )
            result["shell_ready_observation"] = _shell_payload(shell_observation)
            if not shell_ready:
                step_one_error = (
                    "Step 1 failed: the deployed app never exposed the interactive shell "
                    "needed for TS-1001.\n"
                    f"Observed shell snapshot:\n{json.dumps(_shell_payload(shell_observation), indent=2)}"
                )
                result["product_failure"] = True
                tracker_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                _record_step(
                    result,
                    step=1,
                    status="failed",
                    action=REQUEST_STEPS[0],
                    observed=step_one_error,
                )
                _record_human_verification(
                    result,
                    check=(
                        "Viewed the deployed page during startup and checked whether it "
                        "rendered the full hosted shell with visible navigation."
                    ),
                    observed=(
                        f"shell_snapshot={json.dumps(_shell_payload(shell_observation), ensure_ascii=True)}; "
                        f"screenshot={result['screenshot']!r}"
                    ),
                )
                _record_not_reached_steps(result, starting_step=2, request_steps=REQUEST_STEPS)
                raise AssertionError(step_one_error)

            result["auth_probe_started_after_start_seconds"] = relative_startup_event_seconds(
                startup_started_at_monotonic,
                runtime.auth_probe_started_at_monotonic,
            )
            _record_step(
                result,
                step=1,
                status="passed",
                action=REQUEST_STEPS[0],
                observed=(
                    "Opened the deployed TrackState app in the hosted workspace with a "
                    "stored GitHub token and a 30-second delayed `/user` interception.\n"
                    f"shell_snapshot={json.dumps(_shell_payload(shell_observation), ensure_ascii=True)}; "
                    f"auth_probe_started_after_start_seconds={result['auth_probe_started_after_start_seconds']!r}"
                ),
            )

            timeout_reached, timeout_observation = poll_until(
                probe=lambda: _observe_live_shell(tracker_page, switcher_page, startup_started_at_monotonic),
                is_satisfied=lambda observation: observation["elapsed_since_start_seconds"]
                >= TIMEOUT_ASSERTION_SECONDS,
                timeout_seconds=STARTUP_WAIT_SECONDS,
                interval_seconds=POLL_INTERVAL_SECONDS,
            )
            result["timeout_observation"] = _shell_payload(timeout_observation)
            result["github_request_urls"] = list(runtime.github_request_urls)
            result["delayed_request_urls"] = list(runtime.delayed_request_urls)

            if not timeout_reached:
                step_two_error = (
                    "Step 2 failed: the test never reached the post-timeout observation "
                    "window on the deployed app.\n"
                    f"Observed timeout snapshot:\n{json.dumps(_shell_payload(timeout_observation), indent=2)}"
                )
                result["product_failure"] = True
                _record_step(
                    result,
                    step=2,
                    status="failed",
                    action=REQUEST_STEPS[1],
                    observed=step_two_error,
                )
                _record_not_reached_steps(result, starting_step=3, request_steps=REQUEST_STEPS)
                raise AssertionError(step_two_error)

            try:
                _assert_timeout_fallback_shell(timeout_observation)
            except AssertionError as error:
                result["product_failure"] = True
                _record_step(
                    result,
                    step=2,
                    status="failed",
                    action=REQUEST_STEPS[1],
                    observed=str(error),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Viewed the hosted shell after waiting past the 11-second window "
                        "and compared the visible workspace state with the expected fallback."
                    ),
                    observed=(
                        f"timeout_snapshot={json.dumps(_shell_payload(timeout_observation), ensure_ascii=True)}; "
                        f"github_request_urls={json.dumps(result['github_request_urls'], ensure_ascii=True)}; "
                        f"delayed_request_urls={json.dumps(result['delayed_request_urls'], ensure_ascii=True)}"
                    ),
                )
                _record_not_reached_steps(result, starting_step=3, request_steps=REQUEST_STEPS)
                raise

            _record_step(
                result,
                step=2,
                status="passed",
                action=REQUEST_STEPS[1],
                observed=(
                    f"Waited {timeout_observation['elapsed_since_start_seconds']!r} seconds "
                    "after launch. The hosted shell stayed interactive, the workspace "
                    "trigger still showed `Needs sign-in`, and the delayed auth request "
                    f"remained non-blocking for the visible shell. delayed_request_urls={runtime.delayed_request_urls!r}"
                ),
            )

            restricted_write_surface = _observe_restricted_write_surface(
                tracker_page,
                create_gate_page,
            )
            result["restricted_write_surface_observation"] = restricted_write_surface
            try:
                _assert_restricted_write_surface(restricted_write_surface)
            except AssertionError as error:
                result["product_failure"] = True
                _record_step(
                    result,
                    step=3,
                    status="failed",
                    action=REQUEST_STEPS[2],
                    observed=str(error),
                )
                raise

            _record_step(
                result,
                step=3,
                status="passed",
                action=REQUEST_STEPS[2],
                observed=(
                    "Opened the visible `Create issue` action and inspected the user-facing "
                    "restricted write surface instead of an unrestricted write form.\n"
                    f"surface={json.dumps(restricted_write_surface, ensure_ascii=True)}"
                ),
            )

            probe_result = delayed_auth_probe.inspect(
                repository=service.repository,
                branch=DEFAULT_BRANCH,
                token=token,
                auth_delay_seconds=SIMULATED_PROBE_DELAY_SECONDS,
                timeout_assertion_seconds=TIMEOUT_ASSERTION_SECONDS,
            )
            result["delayed_auth_probe_analyze_output"] = probe_result.analyze_output
            result["delayed_auth_probe_run_output"] = probe_result.run_output
            result["delayed_auth_probe_observation"] = probe_result.observation_payload

            try:
                _assert_delayed_auth_probe(probe_result.observation_payload, probe_result.succeeded)
            except AssertionError as error:
                observation = probe_result.observation_payload or {}
                if observation.get("failureType") == "product":
                    result["product_failure"] = True
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
                    "Ran a production delayed-auth provider probe that used the real "
                    "GitHub provider and live GitHub API responses while delaying `/user` "
                    f"for {SIMULATED_PROBE_DELAY_SECONDS} seconds. At the "
                    f"{TIMEOUT_ASSERTION_SECONDS}-second checkpoint, the session metadata "
                    "still reported `canWrite=false` and `canCreateBranch=false`.\n"
                    f"probe_observation={json.dumps(probe_result.observation_payload, ensure_ascii=True)}"
                ),
            )

            _record_human_verification(
                result,
                check=(
                    "Viewed the deployed hosted workspace like a user and confirmed the "
                    "visible state labels, branding, and primary navigation after waiting "
                    "past the startup timeout."
                ),
                observed=(
                    f"timeout_snapshot={json.dumps(_shell_payload(timeout_observation), ensure_ascii=True)}; "
                    f"screenshot={str(SUCCESS_SCREENSHOT_PATH)!r}"
                ),
            )
            _record_human_verification(
                result,
                check=(
                    "Opened the visible Create issue action and confirmed the user sees "
                    "the exact restricted recovery surface instead of an editable write flow."
                ),
                observed=(
                    f"surface_body_excerpt={_snippet(str(restricted_write_surface.get('body_text', '')))!r}; "
                    f"open_settings_button_count={restricted_write_surface.get('open_settings_button_count')!r}; "
                    f"close_button_count={restricted_write_surface.get('close_button_count')!r}; "
                    f"save_button_count={restricted_write_surface.get('save_button_count')!r}"
                ),
            )

            tracker_page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
            result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
            _write_pass_outputs(result)
            print(f"{TICKET_KEY} passed")
            return
    except AssertionError as error:
        if tracker_page is not None:
            try:
                tracker_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
            except Exception as screenshot_error:  # pragma: no cover - diagnostics only
                result["screenshot_error"] = (
                    f"{type(screenshot_error).__name__}: {screenshot_error}"
                )
        result["error"] = f"AssertionError: {error}"
        result["traceback"] = traceback.format_exc()
        _write_failure_outputs(result)
        raise
    except Exception as error:
        if tracker_page is not None:
            try:
                tracker_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
            except Exception as screenshot_error:  # pragma: no cover - diagnostics only
                result["screenshot_error"] = (
                    f"{type(screenshot_error).__name__}: {screenshot_error}"
                )
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


def _observe_live_shell(
    tracker_page: TrackStateTrackerPage,
    switcher_page: LiveWorkspaceSwitcherPage,
    startup_started_at_monotonic: float | None = None,
) -> dict[str, Any]:
    shell = tracker_page.observe_interactive_shell(SHELL_NAVIGATION_LABELS, timeout_ms=1_000)
    trigger = safe_trigger_payload(switcher_page)
    body_text = str(shell.get("body_text") or tracker_page.body_text())
    return {
        "shell_observation": {
            **shell,
            "body_text": body_text,
        },
        "trigger": trigger,
        "branding_visible": BRANDING_TEXT in body_text or "TrackState.AI" in body_text,
        "elapsed_since_start_seconds": (
            round(time.monotonic() - startup_started_at_monotonic, 2)
            if startup_started_at_monotonic is not None
            else None
        ),
    }


def _is_interactive_shell_observation(observation: dict[str, Any]) -> bool:
    shell = observation["shell_observation"]
    return (
        observation["trigger"] is not None
        and observation["branding_visible"]
        and all(label in shell["visible_navigation_labels"] for label in SHELL_NAVIGATION_LABELS)
    )


def _assert_timeout_fallback_shell(observation: dict[str, Any]) -> None:
    shell = observation["shell_observation"]
    missing_navigation = [
        label
        for label in SHELL_NAVIGATION_LABELS
        if label not in shell["visible_navigation_labels"]
    ]
    if missing_navigation:
        raise AssertionError(
            "Step 2 failed: after waiting beyond the 11-second timeout, the live shell "
            f"was missing navigation labels {missing_navigation}.\n"
            f"Observed timeout snapshot:\n{json.dumps(_shell_payload(observation), indent=2)}"
        )
    if not observation["branding_visible"]:
        raise AssertionError(
            "Step 2 failed: after waiting beyond the 11-second timeout, the live shell "
            "did not show the TrackState branding.\n"
            f"Observed timeout snapshot:\n{json.dumps(_shell_payload(observation), indent=2)}"
        )
    trigger = observation["trigger"]
    if trigger is None:
        raise AssertionError(
            "Step 2 failed: the header workspace trigger was missing after the timeout "
            "window.\n"
            f"Observed timeout snapshot:\n{json.dumps(_shell_payload(observation), indent=2)}"
        )
    if trigger.get("workspace_type") != "Hosted":
        raise AssertionError(
            "Step 2 failed: the active workspace was not the hosted workspace expected "
            f"by the ticket. Observed trigger: {json.dumps(trigger, indent=2)}"
        )
    if trigger.get("state_label") != "Needs sign-in":
        raise AssertionError(
            "Step 2 failed: after waiting beyond the 11-second timeout, the active "
            "workspace did not expose the expected `Needs sign-in` fallback state.\n"
            f"Observed trigger: {json.dumps(trigger, indent=2)}"
        )


def _observe_restricted_write_surface(
    tracker_page: TrackStateTrackerPage,
    create_gate_page: LiveCreateIssueGatePage,
) -> dict[str, Any]:
    create_gate_page.wait_for_create_trigger(timeout_ms=20_000)
    create_gate_page.open_create_issue(timeout_ms=20_000)
    observed, surface = poll_until(
        probe=lambda: _restricted_write_surface_payload(tracker_page),
        is_satisfied=lambda observation: (
            (
                observation["open_settings_button_count"] >= 1
                and "GitHub write access is not connected" in observation["body_text"]
            )
            or (
                "fell back to startup-safe repository defaults so the shell could open"
                in observation["body_text"]
                and "after 11 seconds" in observation["body_text"]
                and observation["close_button_count"] >= 1
            )
        ),
        timeout_seconds=20,
        interval_seconds=0.5,
    )
    if not observed:
        raise AssertionError(
            "Step 3 failed: the Create issue surface never exposed the expected "
            "restricted recovery surface.\n"
            f"Observed surface snapshot:\n{json.dumps(surface, indent=2)}"
        )
    return surface


def _restricted_write_surface_payload(tracker_page: TrackStateTrackerPage) -> dict[str, Any]:
    body_text = tracker_page.body_text()
    return {
        "body_text": body_text,
        "body_excerpt": _snippet(body_text),
        "open_settings_button_count": tracker_page.session.count(
            TrackStateTrackerPage.BUTTON_SELECTOR,
            has_text="Open settings",
        ),
        "save_button_count": tracker_page.session.count(
            TrackStateTrackerPage.BUTTON_SELECTOR,
            has_text=TrackStateTrackerPage.SAVE_LABEL,
        ),
        "close_button_count": tracker_page.session.count(
            TrackStateTrackerPage.BUTTON_SELECTOR,
            has_text="Close",
        ),
    }


def _assert_restricted_write_surface(surface: dict[str, Any]) -> None:
    body_text = str(surface.get("body_text", ""))
    open_settings_button_count = int(surface.get("open_settings_button_count", 0))
    if "GitHub write access is not connected" in body_text:
        if open_settings_button_count < 1:
            raise AssertionError(
                "Step 3 failed: the repository-access recovery surface was visible, but "
                "it did not expose a visible `Open settings` action.\n"
                f"Observed surface:\n{json.dumps(surface, indent=2)}"
            )
        if (
            "Create, edit, comment, and status changes stay read-only"
            not in body_text
        ):
            raise AssertionError(
                "Step 3 failed: the repository-access recovery surface was visible, but "
                "its read-only restriction copy was missing.\n"
                f"Observed surface:\n{json.dumps(surface, indent=2)}"
            )
        return
    if (
        "fell back to startup-safe repository defaults so the shell could open"
        not in body_text
        or "Hosted startup deferred" not in body_text
        or "after 11 seconds" not in body_text
    ):
        raise AssertionError(
            "Step 3 failed: the Create issue action did not expose either the repository "
            "access restriction copy or the startup-safe recovery callout expected after "
            "the timeout fallback.\n"
            f"Observed surface:\n{json.dumps(surface, indent=2)}"
        )
    if int(surface.get("close_button_count", 0)) < 1:
        raise AssertionError(
            "Step 3 failed: the startup-safe recovery callout was visible, but it did not "
            "expose the visible `Close` dismissal action.\n"
            f"Observed surface:\n{json.dumps(surface, indent=2)}"
        )


def _assert_delayed_auth_probe(
    observation: dict[str, Any] | None,
    execution_succeeded: bool,
) -> None:
    if not execution_succeeded:
        raise AssertionError(
            "Step 4 failed: the delayed-auth provider probe could not be analyzed or run, "
            "so the session metadata contract was not verified."
        )
    if not isinstance(observation, dict):
        raise AssertionError(
            "Step 4 failed: the delayed-auth provider probe did not return a structured "
            "observation payload."
        )
    if observation.get("status") != "passed":
        raise AssertionError(
            "Step 4 failed: the delayed-auth provider probe did not confirm the "
            "restricted session flags.\n"
            f"Probe observation:\n{json.dumps(observation, indent=2)}"
        )
    checkpoint_session = observation.get("checkpointSession")
    if not isinstance(checkpoint_session, dict):
        raise AssertionError(
            "Step 4 failed: the delayed-auth provider probe did not expose the "
            "checkpoint session payload.\n"
            f"Probe observation:\n{json.dumps(observation, indent=2)}"
        )
    if checkpoint_session.get("connectionState") != "ProviderConnectionState.connecting":
        raise AssertionError(
            "Step 4 failed: the checkpoint session was not still connecting while `/user` "
            "was delayed.\n"
            f"Probe observation:\n{json.dumps(observation, indent=2)}"
        )
    if checkpoint_session.get("canWrite") is not False:
        raise AssertionError(
            "Step 4 failed: `canWrite` was not false at the delayed-auth checkpoint.\n"
            f"Probe observation:\n{json.dumps(observation, indent=2)}"
        )
    if checkpoint_session.get("canCreateBranch") is not False:
        raise AssertionError(
            "Step 4 failed: `canCreateBranch` was not false at the delayed-auth checkpoint.\n"
            f"Probe observation:\n{json.dumps(observation, indent=2)}"
        )
    if observation.get("userRequestPendingAtCheckpoint") is not True:
        raise AssertionError(
            "Step 4 failed: the delayed `/user` probe was not still pending at the "
            "checkpoint when session metadata was sampled.\n"
            f"Probe observation:\n{json.dumps(observation, indent=2)}"
        )


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


def _shell_payload(observation: dict[str, Any]) -> dict[str, Any]:
    shell = observation.get("shell_observation", {})
    return {
        "elapsed_since_start_seconds": observation.get("elapsed_since_start_seconds"),
        "branding_visible": observation.get("branding_visible"),
        "visible_navigation_labels": list(shell.get("visible_navigation_labels", [])),
        "trigger": observation.get("trigger"),
        "body_excerpt": _snippet(str(shell.get("body_text", ""))),
    }


def _snippet(text: str, *, limit: int = 240) -> str:
    return snippet(text, limit=limit)


def _write_pass_outputs(result: dict[str, Any]) -> None:
    BUG_DESCRIPTION_PATH.unlink(missing_ok=True)
    REVIEW_REPLIES_PATH.unlink(missing_ok=True)
    write_test_automation_result(RESULT_PATH, passed=True)
    JIRA_COMMENT_PATH.write_text(_build_jira_comment(result, passed=True), encoding="utf-8")
    PR_BODY_PATH.write_text(_build_pr_body(result, passed=True), encoding="utf-8")
    RESPONSE_PATH.write_text(_build_response_summary(result, passed=True), encoding="utf-8")


def _write_failure_outputs(result: dict[str, Any]) -> None:
    REVIEW_REPLIES_PATH.unlink(missing_ok=True)
    error = str(result.get("error", f"AssertionError: {TICKET_KEY} failed"))
    write_test_automation_result(RESULT_PATH, passed=False, error=error)
    JIRA_COMMENT_PATH.write_text(_build_jira_comment(result, passed=False), encoding="utf-8")
    PR_BODY_PATH.write_text(_build_pr_body(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_build_response_summary(result, passed=False), encoding="utf-8")
    if _should_write_bug_description(result):
        BUG_DESCRIPTION_PATH.write_text(_build_bug_description(result), encoding="utf-8")
    else:
        BUG_DESCRIPTION_PATH.unlink(missing_ok=True)


def _build_jira_comment(result: dict[str, Any], *, passed: bool) -> str:
    status_text = "✅ PASSED" if passed else "❌ FAILED"
    lines = [
        "h3. Test Automation Result",
        "",
        f"*Status:* {status_text}",
        f"*Test Case:* {TICKET_KEY} — {TEST_CASE_TITLE}",
        f"*Environment:* URL={result.get('app_url')} | Browser={result.get('browser')} | OS={result.get('os')}",
        f"*Viewport:* {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
        f"*Linked Bugs Considered:* {', '.join(LINKED_BUGS)}",
        "",
        "h4. What was tested",
        "* Opened the deployed hosted workspace in Chromium and waited beyond the 11-second startup window before asserting the visible fallback state.",
        "* Checked the live shell, workspace switcher label, and the user-facing restricted recovery surface that appears after activating Create issue on the deployed app.",
        "* Ran a production delayed-auth provider probe that used the real GitHub provider and delayed {/user} for 30 seconds before sampling session metadata.",
        "",
        "h4. Result",
        f"* {_actual_result_summary(result, passed=passed)}",
        *_step_lines(result, jira=True),
        "",
        "h4. Real user-style verification",
        *format_human_lines(result, jira=True),
        "",
        "h4. Test file",
        "{code}",
        "testing/tests/TS-1001/test_ts_1001.py",
        "{code}",
        "",
        "h4. Run command",
        "{code:bash}",
        RUN_COMMAND,
        "{code}",
    ]
    if result.get("screenshot"):
        lines.extend(["", f"*Screenshot:* {result['screenshot']}"])
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
    status_text = "✅ PASSED" if passed else "❌ FAILED"
    lines = [
        "## Test Automation Result",
        "",
        f"**Status:** {status_text}",
        f"**Test Case:** {TICKET_KEY} — {TEST_CASE_TITLE}",
        f"**Environment:** `{result.get('app_url')}` · {result.get('browser')} · {result.get('os')}",
        f"**Viewport:** `{DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}`",
        f"**Linked Bugs Considered:** {', '.join(LINKED_BUGS)}",
        "",
        "## What was automated",
        "- Waited beyond the 11-second startup window on the deployed hosted workspace before asserting the visible fallback shell.",
        "- Verified the active hosted workspace still showed `Needs sign-in` and the `Create issue` action opened a restricted recovery surface instead of an editable write flow.",
        "- Verified hidden session metadata with a production delayed-auth provider probe instead of a fixture-authored capability state.",
        "",
        "## Result",
        f"- {_actual_result_summary(result, passed=passed)}",
        *_step_lines(result, jira=False),
        "",
        "## Real user-style verification",
        *format_human_lines(result, jira=False),
        "",
        "## How to run",
        "```bash",
        RUN_COMMAND,
        "```",
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
    lines = [
        "h3. Latest result",
        "",
        f"*Status:* {'✅ PASSED' if passed else '❌ FAILED'}",
        f"*Test Case:* {TICKET_KEY} — {TEST_CASE_TITLE}",
        f"*Run command:* {{code:bash}}{RUN_COMMAND}{{code}}",
        f"*Summary:* {'1 passed, 0 failed' if passed else '0 passed, 1 failed'}",
        f"*Observed:* {_actual_result_summary(result, passed=passed)}",
        "",
    ]
    if not passed:
        lines.extend(
            [
                "h4. Error",
                "{code}",
                str(result.get("error", "")),
                "{code}",
                "",
            ],
        )
    return "\n".join(lines) + "\n"


def _should_write_bug_description(result: dict[str, Any]) -> bool:
    error = str(result.get("error", ""))
    if error.startswith("RuntimeError: TS-1001 requires GH_TOKEN or GITHUB_TOKEN"):
        return False
    if error.startswith("ModuleNotFoundError:"):
        return False
    return bool(result.get("product_failure"))


def _build_bug_description(result: dict[str, Any]) -> str:
    probe_observation = result.get("delayed_auth_probe_observation")
    lines = [
        f"# {TICKET_KEY} bug report",
        "",
        "## Steps to reproduce",
        *build_annotated_steps(result, request_steps=REQUEST_STEPS),
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
        f"- Simulated delayed auth probe: GitHub `/user` delayed by {SIMULATED_PROBE_DELAY_SECONDS} seconds",
        "",
        "## Screenshots or logs",
        f"- Screenshot: `{result.get('screenshot')}`",
        f"- GitHub requests seen in live browser: `{json.dumps(result.get('github_request_urls', []), ensure_ascii=True)}`",
        f"- Delayed requests seen in live browser: `{json.dumps(result.get('delayed_request_urls', []), ensure_ascii=True)}`",
        f"- Timeout observation: `{json.dumps(result.get('timeout_observation'), ensure_ascii=True)}`",
        f"- Restricted write surface observation: `{json.dumps(result.get('restricted_write_surface_observation'), ensure_ascii=True)}`",
        f"- Delayed auth probe observation: `{json.dumps(probe_observation, ensure_ascii=True)}`",
    ]
    return "\n".join(lines) + "\n"


def _actual_result_summary(result: dict[str, Any], *, passed: bool) -> str:
    if passed:
        return (
            "After waiting beyond the 11-second startup window, the deployed hosted shell "
            "stayed interactive, the workspace trigger still showed `Needs sign-in`, the "
            "Create issue flow surfaced the startup-safe recovery callout instead of an "
            "editable form, and the production delayed-auth provider probe confirmed "
            "`canWrite=false` plus `canCreateBranch=false` while `/user` was still delayed."
        )
    return str(
        result.get(
            "error",
            "The deployed app or the production delayed-auth provider session did not "
            "match the restricted fallback state expected after the startup timeout.",
        ),
    )


def _step_lines(result: dict[str, Any], *, jira: bool) -> list[str]:
    return format_step_lines(result, jira=jira)


if __name__ == "__main__":
    main()
