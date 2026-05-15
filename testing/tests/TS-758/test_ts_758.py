from __future__ import annotations

from dataclasses import asdict, dataclass
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
from testing.components.pages.trackstate_tracker_page import (  # noqa: E402
    TrackStateTrackerPage,
    WorkspaceSwitcherTriggerObservation,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.utils.polling import poll_until  # noqa: E402
from testing.tests.support.live_tracker_app_factory import create_live_tracker_app  # noqa: E402
from support.ts758_retry_workspace_runtime import (  # noqa: E402
    Ts758RetryWorkspaceObservation,
    Ts758RetryWorkspaceRuntime,
)

TICKET_KEY = "TS-758"
TEST_CASE_TITLE = "Startup recovery - retry validation after fixing invalid workspace"
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-758/test_ts_758.py"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts758_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts758_failure.png"

REQUEST_STEPS = [
    "Launch the application.",
    "Wait for the Startup Recovery screen to appear.",
    "Restore the workspace to a valid state.",
    "Click the 'Retry' button.",
]
EXPECTED_RESULT = (
    "The application re-validates the workspace, successfully initializes the "
    "tracker state, and navigates to the main application interface, dismissing "
    "the recovery screen."
)
WORKSPACE_STORAGE_KEYS = (
    "trackstate.workspaceProfiles.state",
    "flutter.trackstate.workspaceProfiles.state",
)
SHELL_NAVIGATION_LABELS = (
    "Dashboard",
    "Board",
    "JQL Search",
    "Hierarchy",
    "Settings",
)
BOARD_HINT = TrackStateTrackerPage.BOARD_HINT
INVALID_BRANCH = "ts758-temporarily-missing-branch"


@dataclass(frozen=True)
class PostRetryObservation:
    board_text: str
    switcher: WorkspaceSwitcherTriggerObservation
    body_text: str


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    repository_service = LiveSetupRepositoryService(config=config)
    token = repository_service.token
    workspace_state = _workspace_state(repository_service.repository)
    request_observation = Ts758RetryWorkspaceObservation(
        repository=repository_service.repository,
        invalid_ref=INVALID_BRANCH,
        repaired_ref=repository_service.ref,
    )
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
        "invalid_branch": INVALID_BRANCH,
        "repaired_ref": repository_service.ref,
        "preloaded_workspace_state": workspace_state,
        "steps": [],
        "human_verification": [],
    }

    try:
        if not token:
            raise RuntimeError(
                "TS-758 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
            )

        runtime = Ts758RetryWorkspaceRuntime(
            repository=repository_service.repository,
            token=token,
            workspace_state=workspace_state,
            invalid_ref=INVALID_BRANCH,
            repaired_ref=repository_service.ref,
            observation=request_observation,
        )
        with create_live_tracker_app(
            config,
            runtime_factory=lambda: runtime,
        ) as tracker_page:
            page = LiveStartupRecoveryPage(tracker_page)
            try:
                page.open()
                storage_snapshot = tracker_page.snapshot_local_storage(WORKSPACE_STORAGE_KEYS)
                result["storage_snapshot"] = storage_snapshot
                result["normalized_workspace_state"] = _decode_workspace_state(storage_snapshot)
                result["request_observation"] = _request_observation_payload(request_observation)
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=REQUEST_STEPS[0],
                    observed=(
                        "Opened the deployed app with one saved hosted workspace preloaded "
                        f"in browser storage. normalized_workspace_state={result.get('normalized_workspace_state')!r}"
                    ),
                )

                try:
                    shell_observation = page.wait_for_shell_routed_to_settings(timeout_ms=120_000)
                except Exception as error:
                    blocked_urls = tuple(request_observation.blocked_urls)
                    shell_observation = page.observe_shell()
                    result["initial_shell_observation"] = _shell_payload(shell_observation)
                    body_text = tracker_page.body_text()
                    if shell_observation.settings_heading_visible and not shell_observation.retry_visible:
                        observed = (
                            "The deployed app routed into Project Settings and showed the "
                            "workspace failure details, but the required Retry action never "
                            "appeared. "
                            f"selected_buttons={shell_observation.selected_button_labels}; "
                            f"visible_navigation_labels={shell_observation.visible_navigation_labels}; "
                            f"connect_github_visible={shell_observation.connect_github_visible}; "
                            f"blocked_bootstrap_requests={list(blocked_urls)!r}; "
                            f"visible body text={body_text!r}"
                        )
                        failure_message = (
                            "Step 2 failed: the app showed Project Settings after the saved "
                            "workspace restore failure, but it did not expose the required "
                            "Retry action.\n"
                            f"Observed shell state: {_shell_payload(shell_observation)}\n"
                            f"Observed blocked bootstrap requests: {list(blocked_urls)!r}\n"
                            f"Observed all requests: {request_observation.requested_urls!r}\n"
                            f"Observed body text:\n{body_text}"
                        )
                    else:
                        observed = (
                            "The deployed app never reached the visible Startup Recovery "
                            "screen after the saved workspace validation flow. "
                            f"Observed blocked bootstrap requests={list(blocked_urls)!r}; "
                            f"observed all requests={request_observation.requested_urls!r}; "
                            f"visible body text={body_text!r}"
                        )
                        failure_message = (
                            "Step 2 failed: the app stayed on a broken startup state instead of "
                            "routing to the Startup Recovery screen.\n"
                            f"Observed blocked bootstrap requests: {list(blocked_urls)!r}\n"
                            f"Observed all requests: {request_observation.requested_urls!r}\n"
                            f"Observed body text:\n{body_text}"
                        )
                    _record_step(
                        result,
                        step=2,
                        status="failed",
                        action=REQUEST_STEPS[1],
                        observed=observed,
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Viewed the post-startup screen as a user to confirm whether the "
                            "recovery surface exposed the Retry action."
                        ),
                        observed=(
                            f"retry_visible={shell_observation.retry_visible}; "
                            f"settings_heading_visible={shell_observation.settings_heading_visible}; "
                            f"connect_github_visible={shell_observation.connect_github_visible}; "
                            f"body_excerpt={_snippet(body_text)}"
                        ),
                    )
                    raise AssertionError(failure_message) from error
                result["initial_shell_observation"] = _shell_payload(shell_observation)
                _assert_settings_recovery_shell(shell_observation)
                blocked_urls = tuple(request_observation.blocked_urls)
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=REQUEST_STEPS[1],
                    observed=(
                        "The visible recovery UI routed to Project Settings with the "
                        f"Retry action available. selected_buttons={shell_observation.selected_button_labels}; "
                        f"visible_navigation_labels={shell_observation.visible_navigation_labels}; "
                        f"blocked_bootstrap_requests={list(blocked_urls)!r}"
                    ),
                )

                runtime.enable_repair()
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action=REQUEST_STEPS[2],
                    observed=(
                        "Enabled the saved workspace to become valid by replaying requests "
                        f"for `{INVALID_BRANCH}` against the live deployed ref "
                        f"`{repository_service.ref}` on the next validation attempt."
                    ),
                )

                page.tap_retry()
                board_ready, post_retry = poll_until(
                    probe=lambda: _probe_post_retry_shell(tracker_page),
                    is_satisfied=lambda observation: isinstance(observation, PostRetryObservation),
                    timeout_seconds=120,
                    interval_seconds=2,
                )
                replayed_urls = tuple(request_observation.replayed_urls)
                if not board_ready or not isinstance(post_retry, PostRetryObservation):
                    raise AssertionError(
                        "Step 4 failed: Retry re-requested the saved workspace, but the "
                        "deployed app never reached the interactive tracker shell.\n"
                        f"Observed replayed requests: {request_observation.replayed_urls!r}\n"
                        f"Observed body text:\n{tracker_page.body_text()}",
                    )
                if not replayed_urls:
                    raise AssertionError(
                        "Step 4 failed: the app reached a new state after Retry, but no "
                        "revalidation request for the saved workspace was captured.\n"
                        f"Observed requests: {request_observation.requested_urls!r}\n"
                        f"Observed body text:\n{post_retry.body_text}",
                    )

                result["post_retry_observation"] = _post_retry_payload(post_retry)
                result["request_observation"] = _request_observation_payload(request_observation)
                _record_step(
                    result,
                    step=4,
                    status="passed",
                    action=REQUEST_STEPS[3],
                    observed=(
                        "Retry triggered a new validation attempt for the saved workspace "
                        "and the app opened the live tracker shell. "
                        f"Replayed requests={list(replayed_urls)!r}; "
                        f"workspace_switcher={post_retry.switcher.aria_label!r}; "
                        f"board_excerpt={_snippet(post_retry.board_text)}"
                    ),
                )

                _record_human_verification(
                    result,
                    check=(
                        "Viewed the recovery screen as a user before retrying and confirmed "
                        "the visible Project Settings recovery UI exposed the Retry action."
                    ),
                    observed=(
                        f"selected_buttons={shell_observation.selected_button_labels}; "
                        f"retry_visible={shell_observation.retry_visible}; "
                        f"settings_heading_visible={shell_observation.settings_heading_visible}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Viewed the post-retry experience as a user and confirmed the app "
                        "left recovery and opened the live tracker interface."
                    ),
                    observed=(
                        f"workspace_switcher={post_retry.switcher.aria_label!r}; "
                        f"visible_board_text={_snippet(post_retry.board_text)}"
                    ),
                )

                tracker_page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
                _write_pass_outputs(result)
                print("TS-758 passed")
                return
            except Exception as error:
                result.setdefault("error", _format_error(error))
                result.setdefault("traceback", traceback.format_exc())
                result["request_observation"] = _request_observation_payload(request_observation)
                if not FAILURE_SCREENSHOT_PATH.exists():
                    page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                result["final_body_text"] = tracker_page.body_text()
                raise
    except Exception as error:
        result.setdefault("error", _format_error(error))
        result.setdefault("traceback", traceback.format_exc())
        result["request_observation"] = _request_observation_payload(request_observation)
        _write_failure_outputs(result)
        raise


def _workspace_state(repository: str) -> dict[str, object]:
    hosted_id = f"hosted:{repository.lower()}@{INVALID_BRANCH}"
    return {
        "activeWorkspaceId": hosted_id,
        "migrationComplete": True,
        "profiles": [
            {
                "id": hosted_id,
                "displayName": "Recovered hosted workspace",
                "targetType": "hosted",
                "target": repository,
                "defaultBranch": INVALID_BRANCH,
                "writeBranch": INVALID_BRANCH,
                "lastOpenedAt": "2026-05-15T12:00:00.000Z",
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
            "Step 2 failed: the startup recovery shell did not expose the full app "
            "navigation while waiting for Retry.\n"
            f"Missing navigation labels: {missing_navigation}\n"
            f"Observed body text:\n{observation.body_text}",
        )
    if not observation.settings_selected:
        raise AssertionError(
            "Step 2 failed: Settings was not the selected navigation target on the "
            "recovery screen.\n"
            f"Observed selected buttons: {observation.selected_button_labels}\n"
            f"Observed body text:\n{observation.body_text}",
        )
    if not observation.retry_visible:
        raise AssertionError(
            "Step 2 failed: the recovery screen did not expose the Retry action.\n"
            f"Observed body text:\n{observation.body_text}",
        )


def _probe_post_retry_shell(
    tracker_page: TrackStateTrackerPage,
) -> PostRetryObservation | str:
    try:
        board_text = tracker_page.open_board()
        switcher = tracker_page.observe_workspace_switcher_trigger(timeout_ms=15_000)
        return PostRetryObservation(
            board_text=board_text,
            switcher=switcher,
            body_text=tracker_page.body_text(),
        )
    except Exception as error:
        return str(error)


def _request_observation_payload(
    observation: Ts758RetryWorkspaceObservation,
) -> dict[str, object]:
    return {
        "requested_urls": list(observation.requested_urls),
        "blocked_urls": list(observation.blocked_urls),
        "replayed_urls": list(observation.replayed_urls),
        "blocked_request_count": observation.blocked_request_count,
        "replayed_request_count": observation.replayed_request_count,
    }


def _shell_payload(observation: StartupRecoveryShellObservation) -> dict[str, object]:
    return asdict(observation)


def _post_retry_payload(observation: PostRetryObservation) -> dict[str, object]:
    return {
        "board_text": observation.board_text,
        "body_text": observation.body_text,
        "switcher": {
            "aria_label": observation.switcher.aria_label,
            "visible_text": observation.switcher.visible_text,
            "body_text": observation.switcher.body_text,
        },
    }


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
    error = str(result.get("error", "AssertionError: TS-758 failed"))
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
    request_observation = result.get("request_observation", {})
    first_failure = _first_failure_observation(result)
    return (
        f"# {TICKET_KEY} - Retry does not restore a saved workspace after it becomes valid\n\n"
        "## Summary\n"
        f"{EXPECTED_RESULT}\n\n"
        "## Exact steps to reproduce\n"
        f"1. {REQUEST_STEPS[0]}  \n"
        f"   - Actual: {_step_actual(step_map, 1)}  \n"
        f"   - Result: {_step_result(step_map, 1)}\n"
        f"2. {REQUEST_STEPS[1]}  \n"
        f"   - Actual: {_step_actual(step_map, 2)}  \n"
        f"   - Result: {_step_result(step_map, 2)}\n"
        f"3. {REQUEST_STEPS[2]}  \n"
        f"   - Actual: {_step_actual(step_map, 3)}  \n"
        f"   - Result: {_step_result(step_map, 3)}\n"
        f"4. {REQUEST_STEPS[3]}  \n"
        f"   - Actual: {_step_actual(step_map, 4)}  \n"
        f"   - Result: {_step_result(step_map, 4)}\n\n"
        "## Exact error message or assertion failure\n"
        "```text\n"
        f"{result.get('traceback', result.get('error', '<missing>'))}"
        "```\n\n"
        "## Actual vs Expected\n"
        f"- **Expected:** {EXPECTED_RESULT}\n"
        f"- **Actual:** {first_failure}\n\n"
        "## Environment details\n"
        f"- **URL:** {result.get('app_url')}\n"
        "- **Browser:** Chromium via Playwright\n"
        f"- **OS:** {result.get('os')}\n"
        f"- **Repository:** {result.get('repository')} @ {result.get('repository_ref')}\n"
        f"- **Invalid branch before repair:** {result.get('invalid_branch')}\n"
        f"- **Repaired live ref:** {result.get('repaired_ref')}\n\n"
        "## Screenshots and logs\n"
        f"- **Screenshot:** `{result.get('screenshot')}`\n"
        f"- **Visible body text at failure:** {result.get('final_body_text')!r}\n"
        f"- **Observed requests:** {request_observation}\n"
    )


def _snippet(text: str, *, limit: int = 240) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3] + "..."


def _step_actual(step_map: dict[int, dict[str, object]], step_number: int) -> str:
    step = step_map.get(step_number)
    if step is None:
        return "Not reached because an earlier step failed."
    return str(step.get("observed", "<missing>"))


def _step_result(step_map: dict[int, dict[str, object]], step_number: int) -> str:
    step = step_map.get(step_number)
    if step is None:
        return "NOT REACHED ⏭️"
    return "PASSED ✅" if step.get("status") == "passed" else "FAILED ❌"


def _first_failure_observation(result: dict[str, object]) -> str:
    steps = result.get("steps", [])
    for step in steps:
        if isinstance(step, dict) and step.get("status") == "failed":
            return str(step.get("observed", "The live scenario failed."))
    return "The live scenario failed before the expected tracker shell appeared."


def _format_error(error: BaseException) -> str:
    return f"{type(error).__name__}: {error}"


if __name__ == "__main__":
    main()
