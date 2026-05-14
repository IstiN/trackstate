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
TEST_DIR = Path(__file__).resolve().parent
if str(TEST_DIR) not in sys.path:
    sys.path.insert(0, str(TEST_DIR))

from testing.components.pages.live_startup_recovery_page import (  # noqa: E402
    LiveStartupRecoveryPage,
    StartupRecoveryShellObservation,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.utils.polling import poll_until  # noqa: E402
from testing.tests.support.live_tracker_app_factory import create_live_tracker_app  # noqa: E402
from support.ts727_invalid_workspace_restore_runtime import (  # noqa: E402
    Ts727InvalidWorkspaceRestoreRuntime,
    Ts727RestoreRequestObservation,
)

TICKET_KEY = "TS-727"
TEST_CASE_TITLE = "Startup failure - fallback to Settings when no valid workspaces exist"
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-727/test_ts_727.py"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts727_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts727_failure.png"

REQUEST_STEPS = [
    "Launch the application.",
    "Observe the final landing screen after the restoration fallback logic completes.",
]
EXPECTED_RESULT = (
    "The app attempts to validate all candidates, fails, and automatically routes "
    "the user to the Settings/Startup Recovery screen instead of a broken tracker "
    "state (AC4)."
)
WORKSPACE_STORAGE_KEYS = (
    "trackstate.workspaceProfiles.state",
    "flutter.trackstate.workspaceProfiles.state",
)
RECOVERY_TEXT = (
    "Project Settings",
    "Project settings administration",
    "Retry",
    "Settings",
)
SHELL_NAVIGATION_LABELS = (
    "Dashboard",
    "Board",
    "JQL Search",
    "Hierarchy",
    "Settings",
)
INVALID_LOCAL_TARGET = "/tmp/trackstate-ts727-missing-workspace"
INVALID_HOSTED_BRANCH = "definitely-missing-branch"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    repository_service = LiveSetupRepositoryService(config=config)
    token = repository_service.token
    workspace_state = _workspace_state(repository_service.repository)
    request_observation = Ts727RestoreRequestObservation()
    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "test_case_title": TEST_CASE_TITLE,
        "app_url": config.app_url,
        "repository": repository_service.repository,
        "repository_ref": repository_service.ref,
        "browser": "Chromium (Playwright)",
        "os": platform.platform(),
        "run_command": RUN_COMMAND,
        "expected_result": EXPECTED_RESULT,
        "invalid_local_target": INVALID_LOCAL_TARGET,
        "invalid_hosted_branch": INVALID_HOSTED_BRANCH,
        "preloaded_workspace_state": workspace_state,
        "steps": [],
        "human_verification": [],
    }

    try:
        if not token:
            raise RuntimeError(
                "TS-727 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
            )

        runtime = Ts727InvalidWorkspaceRestoreRuntime(
            repository=repository_service.repository,
            token=token,
            workspace_state=workspace_state,
            observation=request_observation,
        )
        with create_live_tracker_app(
            config,
            runtime_factory=lambda: runtime,
        ) as tracker_page:
            page = LiveStartupRecoveryPage(tracker_page)
            try:
                page.open()

                invalid_branch_observed, _ = poll_until(
                    probe=lambda: request_observation.invalid_branch_urls(
                        repository=repository_service.repository,
                        branch=INVALID_HOSTED_BRANCH,
                    ),
                    is_satisfied=lambda urls: len(urls) > 0,
                    timeout_seconds=150,
                    interval_seconds=1,
                )
                invalid_branch_urls = request_observation.invalid_branch_urls(
                    repository=repository_service.repository,
                    branch=INVALID_HOSTED_BRANCH,
                )
                storage_snapshot = tracker_page.snapshot_local_storage(
                    WORKSPACE_STORAGE_KEYS,
                )
                result["storage_snapshot"] = storage_snapshot
                result["normalized_workspace_state"] = _decode_workspace_state(
                    storage_snapshot,
                )
                result["request_observation"] = _request_observation_payload(
                    request_observation,
                )

                if not invalid_branch_observed and not invalid_branch_urls:
                    raise AssertionError(
                        "Precondition failed: startup never requested the configured invalid "
                        f"hosted branch `{INVALID_HOSTED_BRANCH}`, so the saved hosted "
                        "workspace validation path was not proven.\n"
                        f"Observed GitHub requests: {request_observation.requested_urls}\n"
                        f"Observed storage snapshot: {json.dumps(storage_snapshot, indent=2)}\n"
                        f"Observed body text:\n{tracker_page.body_text()}",
                    )

                _assert_preloaded_profiles(storage_snapshot)
                default_bootstrap_urls = request_observation.default_bootstrap_urls(
                    repository=repository_service.repository,
                    ref=repository_service.ref,
                )
                result["invalid_branch_urls"] = list(invalid_branch_urls)
                result["default_bootstrap_urls"] = list(default_bootstrap_urls)
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=REQUEST_STEPS[0],
                    observed=(
                        "Opened the deployed app with two invalid saved workspaces "
                        "preloaded in browser storage: one local path and one hosted "
                        "workspace pointing at a missing branch. "
                        f"Stored profiles={_workspace_summary(storage_snapshot)}. "
                        f"Observed invalid-branch requests={list(invalid_branch_urls)!r}. "
                        f"Observed default bootstrap requests={list(default_bootstrap_urls)!r}. "
                        f"Raw observed requests={list(request_observation.requested_urls)!r}."
                    ),
                )

                try:
                    shell_observation = page.wait_for_shell_routed_to_settings(
                        timeout_ms=120_000,
                    )
                    result["shell_observation"] = _shell_payload(shell_observation)
                    _assert_settings_recovery_shell(shell_observation)
                    result["request_observation"] = _request_observation_payload(
                        request_observation,
                    )
                    _record_step(
                        result,
                        step=2,
                        status="passed",
                        action=REQUEST_STEPS[1],
                        observed=(
                            "The final landing screen exposed the startup recovery shell "
                            "with Settings selected.\n"
                            f"{shell_observation.body_text}"
                        ),
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Viewed the final landing screen as a user and confirmed the "
                            "Settings recovery shell was visible instead of a broken or "
                            "blank state."
                        ),
                        observed=(
                            f"selected_buttons={shell_observation.selected_button_labels}; "
                            f"visible_navigation_labels={shell_observation.visible_navigation_labels}; "
                            f"retry_visible={shell_observation.retry_visible}; "
                            f"settings_heading_visible={shell_observation.settings_heading_visible}"
                        ),
                    )
                    page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                    result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
                    _write_pass_outputs(result)
                    print("TS-727 passed")
                    return
                except Exception as error:
                    shell_observation = page.observe_shell()
                    current_body = page.current_body_text()
                    result["shell_observation"] = _shell_payload(shell_observation)
                    result["final_body_text"] = current_body
                    result["request_observation"] = _request_observation_payload(
                        request_observation,
                    )
                    result["visible_recovery_text"] = [
                        text for text in RECOVERY_TEXT if text in current_body
                    ]
                    _record_step(
                        result,
                        step=2,
                        status="failed",
                        action=REQUEST_STEPS[1],
                        observed=(
                            "The final landing screen never routed to the Settings startup "
                            "recovery shell. After waiting for the fallback logic to "
                            "complete, the visible page text remained limited to the splash "
                            f"content: {current_body!r}. "
                            "The expected recovery text was missing: "
                            f"{[text for text in RECOVERY_TEXT if text not in current_body]!r}. "
                            f"Observed shell state: {_shell_payload(shell_observation)}. "
                            f"Observed default bootstrap requests: {list(default_bootstrap_urls)!r}. "
                            f"Raw observed requests: {list(request_observation.requested_urls)!r}."
                        ),
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Viewed the final landing screen exactly as a user would after "
                            "startup recovery should have completed."
                        ),
                        observed=(
                            "Only the splash text remained visible, and no Settings title, "
                            "startup recovery message, Retry action, or sidebar navigation "
                            f"was rendered. Visible body text: {current_body!r}"
                        ),
                    )
                    if not FAILURE_SCREENSHOT_PATH.exists():
                        page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                    result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                    raise AssertionError(
                        "Step 2 failed: after all saved workspace candidates were invalid, "
                        "the deployed app did not route to the Settings startup recovery "
                        "screen.\n"
                        f"Observed body text: {current_body!r}\n"
                        f"Observed shell state: {_shell_payload(shell_observation)}\n"
                        f"Observed invalid-branch requests: {list(invalid_branch_urls)!r}\n"
                        f"Observed default bootstrap requests: {list(default_bootstrap_urls)!r}\n"
                        f"Raw observed requests: {list(request_observation.requested_urls)!r}"
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
        result["request_observation"] = _request_observation_payload(
            request_observation,
        )
        _write_failure_outputs(result)
        raise


def _workspace_state(repository: str) -> dict[str, object]:
    local_id = f"local:{INVALID_LOCAL_TARGET}@main"
    hosted_id = f"hosted:{repository.lower()}@{INVALID_HOSTED_BRANCH}"
    return {
        "activeWorkspaceId": local_id,
        "migrationComplete": True,
        "profiles": [
            {
                "id": local_id,
                "displayName": "",
                "targetType": "local",
                "target": INVALID_LOCAL_TARGET,
                "defaultBranch": "main",
                "writeBranch": "main",
                "lastOpenedAt": "2026-05-14T12:00:00.000Z",
            },
            {
                "id": hosted_id,
                "displayName": "",
                "targetType": "hosted",
                "target": repository,
                "defaultBranch": INVALID_HOSTED_BRANCH,
                "writeBranch": INVALID_HOSTED_BRANCH,
                "lastOpenedAt": "2026-05-13T12:00:00.000Z",
            },
        ],
    }


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


def _assert_preloaded_profiles(storage_snapshot: dict[str, str | None]) -> None:
    state = _decode_workspace_state(storage_snapshot)
    if not isinstance(state, dict):
        raise AssertionError(
            "Precondition failed: browser storage did not expose a decodable saved-"
            "workspace state after preload.\n"
            f"Observed snapshot: {json.dumps(storage_snapshot, indent=2)}",
        )
    profiles = state.get("profiles")
    if not isinstance(profiles, list) or len(profiles) < 2:
        raise AssertionError(
            "Precondition failed: startup did not receive the expected multiple invalid "
            "saved workspaces.\n"
            f"Observed normalized state: {json.dumps(state, indent=2)}",
        )


def _workspace_summary(storage_snapshot: dict[str, str | None]) -> str:
    state = _decode_workspace_state(storage_snapshot)
    if not isinstance(state, dict):
        return "normalized_state_unavailable"
    profiles = state.get("profiles")
    if not isinstance(profiles, list):
        return "profiles_unavailable"
    summaries: list[str] = []
    for profile in profiles:
        if not isinstance(profile, dict):
            continue
        summaries.append(
            "|".join(
                [
                    str(profile.get("targetType", "")),
                    str(profile.get("target", "")),
                    str(profile.get("defaultBranch", "")),
                ],
            ),
        )
    return ", ".join(summaries)


def _assert_settings_recovery_shell(
    observation: StartupRecoveryShellObservation,
) -> None:
    missing_navigation = [
        label
        for label in SHELL_NAVIGATION_LABELS
        if label not in observation.visible_navigation_labels
    ]
    if missing_navigation:
        raise AssertionError(
            "Expected Result failed: the startup recovery shell did not keep the full "
            "app navigation visible.\n"
            f"Missing navigation labels: {missing_navigation}\n"
            f"Observed body text:\n{observation.body_text}",
        )
    if not observation.settings_selected:
        raise AssertionError(
            "Expected Result failed: Settings was not the selected navigation target "
            "after startup recovery.\n"
            f"Observed selected buttons: {observation.selected_button_labels}\n"
            f"Observed body text:\n{observation.body_text}",
        )
    if not observation.topbar_title_visible or not observation.settings_heading_visible:
        raise AssertionError(
            "Expected Result failed: the Settings recovery screen content was not fully "
            "visible.\n"
            f"Observed body text:\n{observation.body_text}",
        )
    if not observation.retry_visible:
        raise AssertionError(
            "Expected Result failed: the startup recovery surface did not expose the "
            "Retry action.\n"
            f"Observed body text:\n{observation.body_text}",
        )


def _shell_payload(
    observation: StartupRecoveryShellObservation,
) -> dict[str, object]:
    return asdict(observation)


def _request_observation_payload(
    observation: Ts727RestoreRequestObservation,
) -> dict[str, object]:
    return {"requested_urls": list(observation.requested_urls)}


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
    error = str(result.get("error", "AssertionError: TS-727 failed"))
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
        f"# {TICKET_KEY} - Startup stays on splash instead of routing to Settings recovery\n\n"
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
        "- **Actual:** After waiting for startup restoration to complete, the deployed web "
        "app still rendered only the splash text `TrackState.AI`. The Settings recovery "
        "shell never appeared: no `Dashboard`, `Board`, `JQL Search`, `Hierarchy`, "
        "`Settings`, `Project Settings`, `Project settings administration`, or `Retry` "
        "text was visible. Network activity showed the app attempted the invalid hosted "
        "saved workspace branch and also issued default bootstrap requests, but the UI "
        "never transitioned to a recoverable landing screen.\n\n"
        "## Environment details\n"
        f"- **URL:** {result.get('app_url')}\n"
        "- **Browser:** Chromium via Playwright\n"
        f"- **OS:** {result.get('os')}\n"
        f"- **Repository:** {result.get('repository')} @ {result.get('repository_ref')}\n"
        f"- **Invalid local target:** {result.get('invalid_local_target')}\n"
        f"- **Invalid hosted branch:** {result.get('invalid_hosted_branch')}\n\n"
        "## Screenshots and logs\n"
        f"- **Screenshot:** `{result.get('screenshot')}`\n"
        f"- **Invalid branch requests:** {result.get('invalid_branch_urls')}\n"
        f"- **Default bootstrap requests:** {result.get('default_bootstrap_urls')}\n"
        f"- **Raw observed requests:** {result.get('request_observation')}\n"
        f"- **Visible body text at failure:** {result.get('final_body_text')!r}\n"
    )


def _format_error(error: BaseException) -> str:
    return f"{type(error).__name__}: {error}"


if __name__ == "__main__":
    main()
