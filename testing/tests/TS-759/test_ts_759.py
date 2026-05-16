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
from support.ts759_invalid_workspace_retry_runtime import (  # noqa: E402
    Ts759InvalidWorkspaceRetryRuntime,
    Ts759RetryRequestObservation,
)

TICKET_KEY = "TS-759"
TEST_CASE_TITLE = "Startup recovery - retry with persistent invalid workspace"
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-759/test_ts_759.py"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts759_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts759_failure.png"

REQUEST_STEPS = [
    "Launch the application and wait for the Startup Recovery screen to appear.",
    "Click the 'Retry' button without correcting the workspace configuration.",
]
EXPECTED_RESULT = (
    "The application attempts to re-validate the workspace collection, fails, "
    "and remains on the Startup Recovery screen with the 'Retry' action still "
    "available."
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
INVALID_LOCAL_TARGET = "/tmp/trackstate-ts759-missing-workspace"
INVALID_HOSTED_BRANCH = "definitely-missing-branch"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    repository_service = LiveSetupRepositoryService(config=config)
    token = repository_service.token
    workspace_state = _workspace_state(repository_service.repository)
    request_observation = Ts759RetryRequestObservation()
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
                "TS-759 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
            )

        runtime = Ts759InvalidWorkspaceRetryRuntime(
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

                storage_snapshot = tracker_page.snapshot_local_storage(
                    WORKSPACE_STORAGE_KEYS,
                )
                result["storage_snapshot"] = storage_snapshot
                result["normalized_workspace_state"] = _decode_workspace_state(
                    storage_snapshot,
                )

                _assert_preloaded_profiles(storage_snapshot)
                initial_shell = page.wait_for_shell_routed_to_settings(
                    timeout_ms=120_000,
                    require_retry_action=False,
                )
                initial_request_observed, initial_invalid_branch_urls = poll_until(
                    probe=lambda: request_observation.invalid_branch_urls(
                        branch=INVALID_HOSTED_BRANCH,
                    ),
                    is_satisfied=lambda urls: len(urls) > 0,
                    timeout_seconds=10,
                    interval_seconds=1,
                )
                if not initial_request_observed:
                    raise AssertionError(
                        "Precondition failed: startup never proved validation of the configured "
                        f"invalid hosted branch `{INVALID_HOSTED_BRANCH}` before the recovery "
                        "shell assertions ran.\n"
                        f"Observed GitHub requests: {request_observation.requested_urls}\n"
                        f"Observed storage snapshot: {json.dumps(storage_snapshot, indent=2)}\n"
                        f"Observed shell state: {_shell_payload(initial_shell)}",
                    )
                _assert_settings_recovery_shell(initial_shell, require_retry=False)
                _assert_invalid_workspace_details_visible(
                    initial_shell,
                    failure_prefix=(
                        "Step 1 failed: the startup recovery screen did not keep the "
                        "invalid workspace details visible after loading invalid saved "
                        "workspaces."
                    ),
                )
                result["initial_shell_observation"] = _shell_payload(initial_shell)
                result["request_observation"] = _request_observation_payload(
                    request_observation,
                )
                result["initial_invalid_branch_request_count"] = len(
                    initial_invalid_branch_urls,
                )
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=REQUEST_STEPS[0],
                    observed=(
                        "The deployed app restored into the Settings startup recovery "
                        "shell with still-invalid saved workspaces. "
                        f"Observed invalid-branch requests={list(initial_invalid_branch_urls)!r}. "
                        f"Observed storage={_workspace_summary(storage_snapshot)}. "
                        f"Observed shell state={_shell_payload(initial_shell)}."
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Viewed the Startup Recovery screen exactly as a user would before "
                        "retrying."
                    ),
                    observed=(
                        f"Settings remained selected, Retry visible={initial_shell.retry_visible}, "
                        "the invalid local workspace and missing hosted branch remained "
                        "visible in Project Settings, and "
                        f"the shell still showed navigation labels "
                        f"{initial_shell.visible_navigation_labels}."
                    ),
                )

                if not initial_shell.retry_visible:
                    _record_step(
                        result,
                        step=2,
                        status="failed",
                        action=REQUEST_STEPS[1],
                        observed=(
                            "The app showed the startup recovery message inside Project "
                            "Settings, but no visible Retry action was rendered, so the "
                            "user could not retry validation without changing configuration. "
                            f"Observed shell state={_shell_payload(initial_shell)}."
                        ),
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Looked for the visible Retry action a user needs to re-run "
                            "validation from the recovery screen."
                        ),
                        observed=(
                            "The page showed the recovery message and Settings content, but "
                            "no Retry button or Retry text was visible anywhere on screen."
                        ),
                    )
                    result["final_body_text"] = initial_shell.body_text
                    result["post_retry_shell_observation"] = _shell_payload(initial_shell)
                    raise AssertionError(
                        "Step 2 failed: the startup recovery screen did not expose a visible "
                        "Retry action while the saved workspaces were still invalid.\n"
                        f"Observed shell state: {_shell_payload(initial_shell)}\n"
                        f"Observed body text: {initial_shell.body_text!r}\n"
                        f"Observed requests: {list(request_observation.requested_urls)!r}",
                    )

                requests_stabilized, stabilized_invalid_branch_urls = (
                    _wait_for_invalid_branch_request_count_to_stabilize(
                        request_observation,
                        branch=INVALID_HOSTED_BRANCH,
                    )
                )
                pre_retry_invalid_branch_urls = request_observation.invalid_branch_urls(
                    branch=INVALID_HOSTED_BRANCH,
                )
                result["pre_retry_invalid_branch_requests_stabilized"] = requests_stabilized
                result["pre_retry_invalid_branch_request_count"] = len(
                    pre_retry_invalid_branch_urls,
                )
                result["stabilized_invalid_branch_request_count"] = len(
                    stabilized_invalid_branch_urls,
                )

                page.click_retry(timeout_ms=30_000)
                retry_revalidated, retried_invalid_branch_urls = poll_until(
                    probe=lambda: request_observation.invalid_branch_urls(
                        branch=INVALID_HOSTED_BRANCH,
                    ),
                    is_satisfied=lambda urls: len(urls) > len(pre_retry_invalid_branch_urls),
                    timeout_seconds=150,
                    interval_seconds=1,
                )
                result["request_observation"] = _request_observation_payload(
                    request_observation,
                )
                result["post_retry_invalid_branch_request_count"] = len(
                    retried_invalid_branch_urls,
                )

                if not retry_revalidated:
                    current_body = page.current_body_text()
                    result["final_body_text"] = current_body
                    result["post_retry_shell_observation"] = _shell_payload(page.observe_shell())
                    raise AssertionError(
                        "Step 2 failed: clicking Retry did not trigger another observable "
                        "invalid-workspace validation attempt.\n"
                        f"Baseline invalid-branch requests before Retry: "
                        f"{list(pre_retry_invalid_branch_urls)!r}\n"
                        f"Pre-click request count stabilized: {requests_stabilized}\n"
                        f"Observed requests after Retry: {list(retried_invalid_branch_urls)!r}\n"
                        f"Raw observed requests: {list(request_observation.requested_urls)!r}\n"
                        f"Observed body text: {current_body!r}",
                    )

                post_retry_shell = page.wait_for_shell_routed_to_settings(timeout_ms=120_000)
                _assert_settings_recovery_shell(post_retry_shell, require_retry=True)
                _assert_invalid_workspace_details_visible(
                    post_retry_shell,
                    failure_prefix=(
                        "Expected Result failed: the post-retry screen no longer kept the "
                        "invalid workspace details visible on the startup recovery surface."
                    ),
                )
                result["post_retry_shell_observation"] = _shell_payload(post_retry_shell)
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=REQUEST_STEPS[1],
                    observed=(
                        "Retry triggered another validation request for the still-invalid "
                        "hosted workspace and the app remained on the Settings startup "
                        "recovery shell with Retry still visible. "
                        f"Pre-click invalid-branch request count={len(pre_retry_invalid_branch_urls)}; "
                        f"post-retry count={len(retried_invalid_branch_urls)}. "
                        f"Pre-click request count stabilized={requests_stabilized}. "
                        f"Observed post-retry shell state={_shell_payload(post_retry_shell)}."
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Pressed Retry without fixing the invalid workspace configuration "
                        "and observed what remained on screen."
                    ),
                    observed=(
                        "The visible page stayed on Project Settings / startup recovery, "
                        "Retry remained available, the invalid local workspace and missing "
                        "hosted branch remained visible, and the app did not navigate to a "
                        "normal workspace view."
                    ),
                )
                page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
                _write_pass_outputs(result)
                print("TS-759 passed")
                return
            except Exception as error:
                result.setdefault("error", _format_error(error))
                result.setdefault("traceback", traceback.format_exc())
                if not FAILURE_SCREENSHOT_PATH.exists():
                    page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                if "final_body_text" not in result:
                    result["final_body_text"] = page.current_body_text()
                result.setdefault(
                    "post_retry_shell_observation",
                    _shell_payload(page.observe_shell()),
                )
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
                "displayName": "Broken local workspace",
                "targetType": "local",
                "target": INVALID_LOCAL_TARGET,
                "defaultBranch": "main",
                "writeBranch": "main",
                "lastOpenedAt": "2026-05-15T08:00:00.000Z",
            },
            {
                "id": hosted_id,
                "displayName": "Broken hosted workspace",
                "targetType": "hosted",
                "target": repository,
                "defaultBranch": INVALID_HOSTED_BRANCH,
                "writeBranch": INVALID_HOSTED_BRANCH,
                "lastOpenedAt": "2026-05-14T08:00:00.000Z",
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
    if not isinstance(profiles, list) or len(profiles) < 1:
        raise AssertionError(
            "Precondition failed: startup did not receive the expected invalid saved "
            "workspace state.\n"
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


def _wait_for_invalid_branch_request_count_to_stabilize(
    observation: Ts759RetryRequestObservation,
    *,
    branch: str,
    timeout_seconds: float = 10.0,
    interval_seconds: float = 1.0,
    stable_observations_required: int = 3,
) -> tuple[bool, tuple[str, ...]]:
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be greater than zero.")
    if interval_seconds <= 0:
        raise ValueError("interval_seconds must be greater than zero.")
    if stable_observations_required <= 0:
        raise ValueError("stable_observations_required must be greater than zero.")

    last_snapshot = observation.invalid_branch_urls(branch=branch)
    if stable_observations_required == 1:
        return True, last_snapshot

    last_count = len(last_snapshot)
    stable_observations = 1

    def probe() -> tuple[tuple[str, ...], int]:
        nonlocal last_snapshot, last_count, stable_observations
        current_snapshot = observation.invalid_branch_urls(branch=branch)
        current_count = len(current_snapshot)
        if current_count == last_count:
            stable_observations += 1
        else:
            last_snapshot = current_snapshot
            last_count = current_count
            stable_observations = 1
        return current_snapshot, stable_observations

    stabilized, final_observation = poll_until(
        probe=probe,
        is_satisfied=lambda item: item[1] >= stable_observations_required,
        timeout_seconds=timeout_seconds,
        interval_seconds=interval_seconds,
    )
    return stabilized, final_observation[0]


def _assert_settings_recovery_shell(
    observation: StartupRecoveryShellObservation,
    *,
    require_retry: bool,
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
            "during startup recovery.\n"
            f"Observed selected buttons: {observation.selected_button_labels}\n"
            f"Observed body text:\n{observation.body_text}",
        )
    if not observation.topbar_title_visible or not observation.settings_heading_visible:
        raise AssertionError(
            "Expected Result failed: the Settings startup recovery screen content was "
            "not fully visible.\n"
            f"Observed body text:\n{observation.body_text}",
        )
    if require_retry and not observation.retry_visible:
        raise AssertionError(
            "Expected Result failed: the startup recovery surface did not expose the "
            "Retry action as a visible control.\n"
            f"Observed visible button labels: {observation.visible_button_labels}\n"
            f"Observed body text:\n{observation.body_text}",
        )


def _assert_invalid_workspace_details_visible(
    observation: StartupRecoveryShellObservation,
    *,
    failure_prefix: str,
) -> None:
    required_fragments = (
        Path(INVALID_LOCAL_TARGET).name,
        INVALID_HOSTED_BRANCH,
    )
    missing_fragments = [
        fragment for fragment in required_fragments if fragment not in observation.body_text
    ]
    if not missing_fragments:
        return
    raise AssertionError(
        f"{failure_prefix}\n"
        f"Missing visible fragments: {missing_fragments}\n"
        f"Observed body text:\n{observation.body_text}",
    )


def _shell_payload(
    observation: StartupRecoveryShellObservation,
) -> dict[str, object]:
    return asdict(observation)


def _request_observation_payload(
    observation: Ts759RetryRequestObservation,
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
    error = str(result.get("error", "AssertionError: TS-759 failed"))
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
    step_1_result = "PASSED ✅" if step_map.get(1, {}).get("status") == "passed" else "FAILED ❌"
    step_2_result = "PASSED ✅" if step_map.get(2, {}).get("status") == "passed" else "FAILED ❌"
    failure_summary = _failure_summary(result)
    actual_behavior = _failure_actual_behavior(result)
    missing_capability = _failure_missing_capability(result)
    return (
        f"# {TICKET_KEY} - {failure_summary}\n\n"
        "## Steps to reproduce\n"
        f"1. {REQUEST_STEPS[0]}  \n"
        f"   - Actual: {step_map.get(1, {}).get('observed', '<missing>')}\n"
        f"   - Result: {step_1_result}\n"
        f"2. {REQUEST_STEPS[1]}  \n"
        f"   - Actual: {step_map.get(2, {}).get('observed', result.get('error', '<missing>'))}\n"
        f"   - Result: {step_2_result}\n\n"
        "## Exact error message or assertion failure\n"
        "```text\n"
        f"{result.get('traceback', result.get('error', '<missing>'))}"
        "```\n\n"
        "## Actual vs Expected\n"
        f"- **Expected:** {EXPECTED_RESULT}\n"
        f"- **Actual:** {actual_behavior}\n\n"
        "## Missing or broken production capability\n"
        f"- {missing_capability}\n\n"
        "## Failing command/output\n"
        f"- **Command:** `{result.get('run_command', RUN_COMMAND)}`\n"
        "```text\n"
        f"{result.get('error', '<missing>')}\n"
        "```\n\n"
        "## Environment details\n"
        f"- **URL:** {result.get('app_url')}\n"
        "- **Browser:** Chromium via Playwright\n"
        f"- **OS:** {result.get('os')}\n"
        f"- **Repository:** {result.get('repository')} @ {result.get('repository_ref')}\n"
        f"- **Invalid local target:** {result.get('invalid_local_target')}\n"
        f"- **Invalid hosted branch:** {result.get('invalid_hosted_branch')}\n\n"
        "## Screenshots and logs\n"
        f"- **Screenshot:** `{result.get('screenshot')}`\n"
        f"- **Initial shell observation:** {result.get('initial_shell_observation')}\n"
        f"- **Post-retry shell observation:** {result.get('post_retry_shell_observation')}\n"
        f"- **Initial invalid branch requests observed during startup:** {result.get('initial_invalid_branch_request_count')}\n"
        f"- **Invalid branch requests immediately before retry:** {result.get('pre_retry_invalid_branch_request_count')}\n"
        f"- **Pre-retry request count stabilized:** {result.get('pre_retry_invalid_branch_requests_stabilized')}\n"
        f"- **Invalid branch requests after retry:** {result.get('post_retry_invalid_branch_request_count')}\n"
        f"- **Raw observed requests:** {result.get('request_observation')}\n"
        f"- **Visible body text at failure:** {result.get('final_body_text')!r}\n"
    )


def _first_failed_step(result: dict[str, object]) -> dict[str, object] | None:
    steps = result.get("steps", [])
    if not isinstance(steps, list):
        return None
    for step in steps:
        if isinstance(step, dict) and step.get("status") != "passed":
            return step
    return None


def _failure_text(result: dict[str, object]) -> str:
    failed_step = _first_failed_step(result)
    observed = failed_step.get("observed") if isinstance(failed_step, dict) else None
    return "\n".join(
        part
        for part in (
            str(observed) if observed else "",
            str(result.get("error", "")),
        )
        if part
    )


def _failure_summary(result: dict[str, object]) -> str:
    failure_text = _failure_text(result).lower()
    if "no visible retry action" in failure_text or "visible retry control" in failure_text:
        return "Startup recovery does not expose Retry while saved workspaces remain invalid"
    if "did not trigger another observable invalid-workspace validation attempt" in failure_text:
        return "Retry does not revalidate invalid saved workspaces from startup recovery"
    if "did not keep" in failure_text and "startup recovery" in failure_text:
        return "Retry leaves the startup recovery surface for invalid saved workspaces"
    if "startup recovery message" in failure_text or "startup recovery screen" in failure_text:
        return "Startup recovery screen does not fully appear for invalid saved workspaces"
    return "Startup recovery retry flow does not match the invalid-workspace requirements"


def _failure_actual_behavior(result: dict[str, object]) -> str:
    failed_step = _first_failed_step(result)
    if isinstance(failed_step, dict):
        observed = failed_step.get("observed")
        if observed:
            return str(observed)
    return str(result.get("error", "<missing>"))


def _failure_missing_capability(result: dict[str, object]) -> str:
    summary = _failure_summary(result)
    if "does not expose Retry" in summary:
        return (
            "The startup recovery UI should keep a visible, actionable Retry control "
            "available while the saved workspace collection remains invalid."
        )
    if "does not revalidate" in summary:
        return (
            "Clicking Retry should trigger a fresh validation attempt for the persisted "
            "invalid saved workspaces."
        )
    if "leaves the startup recovery surface" in summary:
        return (
            "After a failed Retry, the app should remain on the startup recovery surface "
            "with the invalid workspace context still visible."
        )
    if "does not fully appear" in summary:
        return (
            "When all saved workspaces are invalid, the app should render the startup "
            "recovery surface inside Settings so the user can recover."
        )
    return (
        "The startup recovery retry workflow should revalidate the invalid workspace "
        "collection and keep the recovery UI available to the user."
    )


def _format_error(error: BaseException) -> str:
    return f"{type(error).__name__}: {error}"


if __name__ == "__main__":
    main()
