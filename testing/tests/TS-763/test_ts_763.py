from __future__ import annotations

from dataclasses import asdict
import json
import platform
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_startup_recovery_page import (  # noqa: E402
    LiveStartupRecoveryPage,
    StartupRecoveryShellObservation,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.utils.polling import poll_until  # noqa: E402
from testing.tests.support.live_tracker_app_factory import create_live_tracker_app  # noqa: E402

TICKET_KEY = "TS-763"
TEST_CASE_TITLE = (
    "Navigation guard - direct Dashboard URL access with no workspaces redirects to Settings"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-763/test_ts_763.py"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts763_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts763_failure.png"
WORKSPACE_STORAGE_KEYS = (
    "trackstate.workspaceProfiles.state",
    "flutter.trackstate.workspaceProfiles.state",
)
REQUEST_STEPS = [
    "Open the browser and navigate directly to the application's dashboard URL (e.g., /#/dashboard).",
    "Wait for the application to finish the startup and initialization sequence.",
]
EXPECTED_RESULT = (
    "The navigation guard identifies the lack of configured workspaces and "
    "automatically redirects the user to the Project Settings screen instead of "
    "allowing access to the Dashboard shell."
)
TARGET_ROUTE = "/dashboard"
TARGET_ROUTE_HASH = "#/dashboard"
_SETTINGS_TEXT = (
    "Project Settings",
    "Project settings administration",
)
_DASHBOARD_TEXT = (
    "Workspace switcher:",
    "Open Issues",
    "Create issue",
)


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "test_case_title": TEST_CASE_TITLE,
        "app_url": config.app_url,
        "repository": config.repository,
        "repository_ref": config.ref,
        "browser": "Chromium (Playwright)",
        "os": platform.platform(),
        "run_command": RUN_COMMAND,
        "expected_result": EXPECTED_RESULT,
        "target_route": TARGET_ROUTE_HASH,
        "steps": [],
        "human_verification": [],
    }

    try:
        with create_live_tracker_app(config) as tracker_page:
            page = LiveStartupRecoveryPage(tracker_page)
            try:
                requested_url = page.open_route(TARGET_ROUTE)
                result["requested_url"] = requested_url
                storage_snapshot = tracker_page.snapshot_local_storage(
                    WORKSPACE_STORAGE_KEYS,
                )
                result["storage_snapshot"] = storage_snapshot
                result["normalized_workspace_state"] = _decode_workspace_state(
                    storage_snapshot,
                )
                _assert_empty_workspace_store(storage_snapshot)
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=REQUEST_STEPS[0],
                    observed=(
                        "Opened the deployed app in a fresh Chromium browser context and "
                        f"navigated directly to {requested_url}. Confirmed the browser "
                        "started with no saved workspaces configured, allowing either "
                        "absent storage keys or an empty normalized workspace-state "
                        "payload after startup repair. "
                        f"Observed storage snapshot={json.dumps(storage_snapshot, indent=2)}; "
                        f"normalized_workspace_state={json.dumps(result['normalized_workspace_state'], indent=2)}"
                    ),
                )

                shell_observation = _wait_for_post_startup_surface(page)
                result["shell_observation"] = _shell_payload(shell_observation)
                result["final_body_text"] = page.current_body_text()

                try:
                    _assert_redirected_to_settings(shell_observation)
                    _record_step(
                        result,
                        step=2,
                        status="passed",
                        action=REQUEST_STEPS[1],
                        observed=(
                            "Startup dismissed the splash screen, blocked direct dashboard "
                            "access, and routed to Project Settings. "
                            f"final_hash={shell_observation.location_hash!r}; "
                            f"final_pathname={shell_observation.location_pathname!r}; "
                            f"selected_buttons={shell_observation.selected_button_labels}; "
                            f"visible_navigation_labels={shell_observation.visible_navigation_labels}"
                        ),
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Viewed the final landing screen as a new user opening the "
                            "dashboard URL directly and checked the visible route outcome."
                        ),
                        observed=(
                            "Project Settings title and administration heading were visible "
                            "instead of dashboard content, Settings was the selected "
                            f"navigation item, and the app no longer remained on {TARGET_ROUTE_HASH}. "
                            f"Observed location={shell_observation.location_href!r}"
                        ),
                    )
                    page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                    result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
                    _write_pass_outputs(result)
                    print("TS-763 passed")
                    return
                except Exception as error:
                    current_body = page.current_body_text()
                    dashboard_clues = [
                        text for text in _DASHBOARD_TEXT if text in current_body
                    ]
                    missing_settings_text = [
                        text for text in _SETTINGS_TEXT if text not in current_body
                    ]
                    _record_step(
                        result,
                        step=2,
                        status="failed",
                        action=REQUEST_STEPS[1],
                        observed=(
                            "Startup initialization completed, but the navigation guard "
                            "did not finish on Project Settings after direct dashboard "
                            "navigation. "
                            f"Final hash={shell_observation.location_hash!r}. "
                            f"Final pathname={shell_observation.location_pathname!r}. "
                            f"Missing settings text={missing_settings_text!r}. "
                            f"Observed dashboard clues={dashboard_clues!r}. "
                            f"Observed shell state={_shell_payload(shell_observation)}. "
                            f"Visible body text: {current_body!r}"
                        ),
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Viewed the final landing screen exactly as a user would after "
                            "opening the dashboard URL directly."
                        ),
                        observed=(
                            f"The app ended at location {shell_observation.location_href!r}. "
                            "The visible screen did not present a clean Project Settings "
                            "landing experience for an empty-workspace user. "
                            f"Visible body text: {current_body!r}"
                        ),
                    )
                    if not FAILURE_SCREENSHOT_PATH.exists():
                        page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                    result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                    raise AssertionError(
                        "Step 2 failed: direct dashboard navigation with no saved "
                        "workspaces did not redirect cleanly to the Settings screen.\n"
                        f"Requested URL: {requested_url}\n"
                        f"Observed location: {shell_observation.location_href!r}\n"
                        f"Observed shell state: {_shell_payload(shell_observation)}\n"
                        f"Observed body text: {current_body!r}\n"
                        f"Observed storage snapshot: {json.dumps(storage_snapshot, indent=2)}"
                    ) from error
            except Exception as error:
                result.setdefault("error", _format_error(error))
                result.setdefault("traceback", traceback.format_exc())
                if not FAILURE_SCREENSHOT_PATH.exists():
                    page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                raise
    except Exception as error:
        result.setdefault("error", _format_error(error))
        result.setdefault("traceback", traceback.format_exc())
        _write_failure_outputs(result)
        raise


def _decode_workspace_state(
    storage_snapshot: dict[str, str | None],
) -> dict[str, object] | None:
    for key in WORKSPACE_STORAGE_KEYS:
        value = storage_snapshot.get(key)
        if value is None:
            continue
        try:
            decoded = json.loads(value)
            if isinstance(decoded, str):
                decoded = json.loads(decoded)
        except (TypeError, json.JSONDecodeError):
            continue
        if isinstance(decoded, dict):
            return decoded
    return None


def _assert_empty_workspace_store(storage_snapshot: dict[str, str | None]) -> None:
    decoded_state = _decode_workspace_state(storage_snapshot)
    if decoded_state is None:
        return
    profiles = decoded_state.get("profiles", [])
    if not isinstance(profiles, list):
        raise AssertionError(
            "Precondition failed: startup serialized workspace state, but it was not "
            "a semantically empty saved-workspace configuration.\n"
            f"Observed storage snapshot: {json.dumps(storage_snapshot, indent=2)}\n"
            f"Observed normalized workspace state: {json.dumps(decoded_state, indent=2)}",
        )
    active_workspace_id = decoded_state.get("activeWorkspaceId")
    has_active_workspace = (
        isinstance(active_workspace_id, str) and active_workspace_id.strip() != ""
    )
    if profiles or has_active_workspace:
        raise AssertionError(
            "Precondition failed: the test did not start from an empty saved-workspace "
            "configuration.\n"
            f"Observed storage snapshot: {json.dumps(storage_snapshot, indent=2)}\n"
            f"Observed normalized workspace state: {json.dumps(decoded_state, indent=2)}",
        )


def _wait_for_post_startup_surface(
    page: LiveStartupRecoveryPage,
    *,
    timeout_seconds: int = 90,
) -> StartupRecoveryShellObservation:
    resolved, observation = poll_until(
        probe=page.observe_shell,
        is_satisfied=_startup_surface_resolved,
        timeout_seconds=timeout_seconds,
        interval_seconds=2,
    )
    if resolved:
        return observation
    raise AssertionError(
        "Step 2 failed: startup never resolved past the splash screen into either "
        "Project Settings or a usable tracker shell.\n"
        f"Observed shell state: {_shell_payload(observation)}\n"
        f"Visible body text: {page.current_body_text()!r}",
    )


def _startup_surface_resolved(observation: StartupRecoveryShellObservation) -> bool:
    if _matches_settings_expectation(observation):
        return True
    return any(text in observation.body_text for text in _DASHBOARD_TEXT)


def _matches_settings_expectation(
    observation: StartupRecoveryShellObservation,
) -> bool:
    return (
        observation.settings_selected
        and observation.topbar_title_visible
        and observation.settings_heading_visible
        and observation.location_hash != TARGET_ROUTE_HASH
    )


def _assert_redirected_to_settings(
    observation: StartupRecoveryShellObservation,
) -> None:
    if _matches_settings_expectation(observation):
        return
    raise AssertionError(
        "Expected Result failed: direct dashboard navigation did not land on the "
        "Settings screen.\n"
        f"Observed location: {observation.location_href!r}\n"
        f"Observed selected buttons: {observation.selected_button_labels}\n"
        f"Observed visible navigation labels: {observation.visible_navigation_labels}\n"
        f"Observed body text:\n{observation.body_text}",
    )


def _shell_payload(
    observation: StartupRecoveryShellObservation,
) -> dict[str, object]:
    return asdict(observation)


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
    JIRA_COMMENT_PATH.write_text(_jira_comment(result, passed=True), encoding="utf-8")
    PR_BODY_PATH.write_text(_markdown_summary(result, passed=True), encoding="utf-8")
    RESPONSE_PATH.write_text(_markdown_summary(result, passed=True), encoding="utf-8")


def _write_failure_outputs(result: dict[str, object]) -> None:
    error = str(result.get("error", "AssertionError: TS-763 failed"))
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
    JIRA_COMMENT_PATH.write_text(_jira_comment(result, passed=False), encoding="utf-8")
    PR_BODY_PATH.write_text(_markdown_summary(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_markdown_summary(result, passed=False), encoding="utf-8")
    BUG_DESCRIPTION_PATH.write_text(_bug_description(result), encoding="utf-8")


def _jira_comment(result: dict[str, object], *, passed: bool) -> str:
    lines = [
        "h3. Test Automation Result",
        f"*Ticket:* {TICKET_KEY}",
        f"*Title:* {TEST_CASE_TITLE}",
        f"*Status:* {'PASSED' if passed else 'FAILED'}",
        f"*Environment:* {result.get('app_url')} | Chromium (Playwright) | {result.get('os')}",
        f"*Requested route:* {result.get('target_route')}",
        "",
        "h4. Automation checks",
    ]
    for step in result.get("steps", []):
        assert isinstance(step, dict)
        emoji = "(/)" if step.get("status") == "passed" else "(x)"
        lines.append(
            f"{emoji} *Step {step.get('step')}* {step.get('action')}\n"
            f"Observed: {step.get('observed')}"
        )
    lines.extend(("", "h4. Human-style verification"))
    for check in result.get("human_verification", []):
        assert isinstance(check, dict)
        lines.append(f"* {check.get('check')}\nObserved: {check.get('observed')}")
    if not passed:
        lines.extend(
            [
                "",
                "h4. Failure details",
                f"*Error:* {result.get('error')}",
                f"*Screenshot:* {result.get('screenshot')}",
            ],
        )
    return "\n".join(lines).strip() + "\n"


def _markdown_summary(result: dict[str, object], *, passed: bool) -> str:
    lines = [
        f"# {TICKET_KEY} {'Passed' if passed else 'Failed'}",
        "",
        f"**Title:** {TEST_CASE_TITLE}",
        f"**Environment:** {result.get('app_url')} | Chromium (Playwright) | {result.get('os')}",
        f"**Requested route:** {result.get('target_route')}",
        f"**Status:** {'passed' if passed else 'failed'}",
        "",
        "## Automation checks",
    ]
    for step in result.get("steps", []):
        assert isinstance(step, dict)
        status = "passed" if step.get("status") == "passed" else "failed"
        lines.append(
            f"- **Step {step.get('step')} ({status})** {step.get('action')}  \n"
            f"  Observed: {step.get('observed')}"
        )
    lines.extend(("", "## Human-style verification"))
    for check in result.get("human_verification", []):
        assert isinstance(check, dict)
        lines.append(f"- **Check:** {check.get('check')}  \n  Observed: {check.get('observed')}")
    if not passed:
        lines.extend(
            [
                "",
                "## Failure details",
                f"- **Error:** {result.get('error')}",
                f"- **Screenshot:** `{result.get('screenshot')}`",
            ],
        )
    return "\n".join(lines).strip() + "\n"


def _bug_description(result: dict[str, object]) -> str:
    steps = result.get("steps", [])
    step_map = {
        int(step["step"]): step
        for step in steps
        if isinstance(step, dict) and isinstance(step.get("step"), int)
    }
    return (
        f"# {TICKET_KEY} - Direct dashboard URL bypass does not redirect empty-workspace users to Settings\n\n"
        "## Steps to reproduce\n"
        f"1. {REQUEST_STEPS[0]}  \n"
        f"   - Actual: {step_map.get(1, {}).get('observed', '<missing>')}\n"
        f"   - Result: {'PASSED ✅' if step_map.get(1, {}).get('status') == 'passed' else 'FAILED ❌'}\n"
        f"2. {REQUEST_STEPS[1]}  \n"
        f"   - Actual: {step_map.get(2, {}).get('observed', '<missing>')}\n"
        "   - Result: FAILED ❌\n\n"
        "## Exact error message or assertion failure\n"
        "```text\n"
        f"{result.get('traceback', result.get('error', '<missing>'))}"
        "```\n\n"
        "## Actual vs Expected\n"
        f"- **Expected:** {EXPECTED_RESULT}\n"
        "- **Actual:** Opening the app directly at the dashboard URL in a fresh "
        "browser context did not complete with a clean redirect to Project "
        "Settings for an empty-workspace user.\n\n"
        "## Environment details\n"
        f"- **URL:** {result.get('app_url')}\n"
        f"- **Requested route:** {result.get('requested_url')}\n"
        "- **Browser:** Chromium via Playwright\n"
        f"- **OS:** {result.get('os')}\n"
        f"- **Repository:** {result.get('repository')} @ {result.get('repository_ref')}\n"
        f"- **Workspace storage snapshot:** {json.dumps(result.get('storage_snapshot'), indent=2)}\n\n"
        "## Screenshots and logs\n"
        f"- **Screenshot:** `{result.get('screenshot')}`\n"
        f"- **Observed shell state:** {json.dumps(result.get('shell_observation'), indent=2)}\n"
        f"- **Visible body text at failure:** {result.get('final_body_text')!r}\n"
    )


def _format_error(error: BaseException) -> str:
    return f"{type(error).__name__}: {error}"


if __name__ == "__main__":
    main()
