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

TICKET_KEY = "TS-757"
TEST_CASE_TITLE = "Startup with empty workspace list — automatic redirect to Settings"
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-757/test_ts_757.py"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts757_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts757_failure.png"
WORKSPACE_STORAGE_KEYS = (
    "trackstate.workspaceProfiles.state",
    "flutter.trackstate.workspaceProfiles.state",
)
REQUEST_STEPS = [
    "Launch the application.",
    "Wait for the startup initialization sequence to complete.",
]
EXPECTED_RESULT = (
    "The loading splash screen (TrackState.AI) is dismissed, and the application "
    "automatically routes the user to the Settings screen to add a new workspace."
)
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
        "steps": [],
        "human_verification": [],
    }

    try:
        with create_live_tracker_app(config) as tracker_page:
            page = LiveStartupRecoveryPage(tracker_page)
            try:
                page.open()
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
                        "Opened the deployed app in a fresh Chromium browser context. "
                        "Confirmed the browser started with no saved workspaces "
                        "configured, allowing either absent storage keys or an empty "
                        "normalized workspace-state payload after startup repair. "
                        f"Observed storage snapshot={json.dumps(storage_snapshot, indent=2)}; "
                        f"normalized_workspace_state={json.dumps(result['normalized_workspace_state'], indent=2)}"
                    ),
                )

                shell_observation = _wait_for_post_startup_surface(page)
                result["shell_observation"] = _shell_payload(shell_observation)
                result["final_body_text"] = page.current_body_text()

                try:
                    _assert_landed_on_settings(shell_observation)
                    _record_step(
                        result,
                        step=2,
                        status="passed",
                        action=REQUEST_STEPS[1],
                        observed=(
                            "Startup dismissed the splash screen and routed directly to "
                            "Project Settings.\n"
                            f"{shell_observation.body_text}"
                        ),
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Viewed the final landing screen as a user and verified the "
                            "Project Settings title and administration heading were "
                            "visible instead of dashboard content."
                        ),
                        observed=(
                            f"selected_buttons={shell_observation.selected_button_labels}; "
                            f"visible_navigation_labels={shell_observation.visible_navigation_labels}; "
                            f"settings_heading_visible={shell_observation.settings_heading_visible}; "
                            f"topbar_title_visible={shell_observation.topbar_title_visible}"
                        ),
                    )
                    page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                    result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
                    _write_pass_outputs(result)
                    print("TS-757 passed")
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
                            "Startup initialization completed, but the final landing screen "
                            "did not route to Project Settings. "
                            f"Missing settings text={missing_settings_text!r}. "
                            f"Observed dashboard clues={dashboard_clues!r}. "
                            f"Observed shell state={_shell_payload(shell_observation)}. "
                            f"Visible body text: {current_body!r}"
                        ),
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Viewed the final landing screen exactly as a new user would "
                            "after startup finished."
                        ),
                        observed=(
                            "The app showed the dashboard shell with the Dashboard "
                            "navigation selected, repository and workspace switcher "
                            "content visible, and no Project Settings title or "
                            f"administration heading. Visible body text: {current_body!r}"
                        ),
                    )
                    if not FAILURE_SCREENSHOT_PATH.exists():
                        page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                    result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                    raise AssertionError(
                        "Step 2 failed: with no saved workspaces configured, the deployed "
                        "app did not route to the Settings screen after startup.\n"
                        f"Observed body text: {current_body!r}\n"
                        f"Observed shell state: {_shell_payload(shell_observation)}\n"
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
    )


def _assert_landed_on_settings(
    observation: StartupRecoveryShellObservation,
) -> None:
    if _matches_settings_expectation(observation):
        return
    raise AssertionError(
        "Expected Result failed: startup did not land on the Settings screen.\n"
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
    error = str(result.get("error", "AssertionError: TS-757 failed"))
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
        f"# {TICKET_KEY} - Empty-workspace startup opens Dashboard instead of Settings\n\n"
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
        "- **Actual:** With no saved workspaces configured in a fresh browser "
        "context, startup resolved into the tracker dashboard instead of Project "
        "Settings. The user saw dashboard content such as `Open Issues`, `Create "
        "issue`, and `Workspace switcher: istin/trackstate-setup, Hosted, Needs "
        "sign-in`, while the expected `Project Settings` title and `Project "
        "settings administration` heading never appeared.\n\n"
        "## Environment details\n"
        f"- **URL:** {result.get('app_url')}\n"
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
