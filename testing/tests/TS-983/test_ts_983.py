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
    StartupRecoverySurfaceObservation,
)
from testing.components.pages.live_workspace_switcher_page import (  # noqa: E402
    LiveWorkspaceSwitcherPage,
    WorkspaceSwitcherObservation,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.interfaces.web_app_session import WebAppTimeoutError  # noqa: E402
from testing.core.utils.polling import poll_until  # noqa: E402
from testing.tests.support.live_tracker_app_factory import create_live_tracker_app  # noqa: E402
from support.ts983_startup_retry_runtime import (  # noqa: E402
    Ts983StartupRetryRuntime,
)

TICKET_KEY = "TS-983"
TEST_CASE_TITLE = (
    "Click recovery sync action re-runs startup fetch and restores workspace switcher"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-983/test_ts_983.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
BLOCKED_BOOTSTRAP_PATH = "DEMO/project.json"
LINKED_BUGS = ["TS-977"]
SHELL_NAVIGATION_LABELS = ("Dashboard", "Board", "JQL Search", "Hierarchy", "Settings")
RECOVERY_ACTION_LABELS = ("Sync issue", "Retry")
HOSTED_SETUP_WORKSPACE_NAME = "Hosted setup workspace"

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts983_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts983_failure.png"

REQUEST_STEPS = [
    'Locate the "Sync issue" button within the workspace switcher panel.',
    "Click the button to initiate a retry.",
    "Observe the transition of the workspace switcher state.",
]
EXPECTED_RESULT = (
    "The application re-attempts the fetch request. Upon receiving the successful "
    'response, the failed "Sync issue" state is cleared, and the workspace '
    "switcher panel is populated with the saved workspace rows and footer controls."
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
            "TS-983 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
        )

    workspace_state = _initial_workspace_state()
    preloaded_workspace_names = _workspace_names(workspace_state)
    runtime = Ts983StartupRetryRuntime(
        repository=config.repository,
        token=token,
        workspace_state=workspace_state,
        blocked_path=BLOCKED_BOOTSTRAP_PATH,
    )

    result: dict[str, object] = {
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
        "blocked_bootstrap_path": BLOCKED_BOOTSTRAP_PATH,
        "preloaded_workspace_state": workspace_state,
        "steps": [],
        "human_verification": [],
    }

    page: LiveWorkspaceSwitcherPage | None = None
    startup_page: LiveStartupRecoveryPage | None = None
    try:
        with create_live_tracker_app(
            config,
            runtime_factory=lambda: runtime,
        ) as tracker_page:
            page = LiveWorkspaceSwitcherPage(tracker_page)
            startup_page = LiveStartupRecoveryPage(tracker_page)
            try:
                startup_page.open()
                page.set_viewport(**DESKTOP_VIEWPORT)

                recovery_ready, recovery_surface = poll_until(
                    probe=lambda: startup_page.observe_recovery_surface(
                        accepted_action_labels=RECOVERY_ACTION_LABELS,
                    ),
                    is_satisfied=lambda observation: isinstance(
                        observation,
                        StartupRecoverySurfaceObservation,
                    )
                    and observation.visible_action_label is not None,
                    timeout_seconds=120,
                    interval_seconds=1,
                )
                result["recovery_surface_before_retry"] = _recovery_surface_payload(
                    recovery_surface,
                )
                result["blocked_requests_before_retry"] = [
                    asdict(request) for request in runtime.blocked_requests
                ]
                if not recovery_ready:
                    _record_step(
                        result,
                        step=1,
                        status="failed",
                        action=REQUEST_STEPS[0],
                        observed=(
                            "The deployed app never exposed a visible recovery action label "
                            f"matching {RECOVERY_ACTION_LABELS!r}.\n"
                            "Observed recovery surface: "
                            f"{json.dumps(_recovery_surface_payload(recovery_surface), indent=2)}"
                        ),
                    )
                    _record_not_reached_steps(result, starting_step=2)
                    raise AssertionError(
                        "Step 1 failed: the deployed app never exposed the recovery action "
                        f"needed for TS-983. Observed recovery surface:\n"
                        f"{json.dumps(_recovery_surface_payload(recovery_surface), indent=2)}",
                    )

                visible_action_label = str(recovery_surface.visible_action_label)
                if len(runtime.blocked_requests) == 0:
                    raise AssertionError(
                        "Precondition failed: the synthetic startup fetch block for "
                        f"{BLOCKED_BOOTSTRAP_PATH} was never exercised before the recovery "
                        f"action appeared.\nObserved recovery surface:\n"
                        f"{json.dumps(_recovery_surface_payload(recovery_surface), indent=2)}",
                    )

                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=REQUEST_STEPS[0],
                    observed=(
                        "The failed startup surface appeared with the expected recovery action "
                        "after the hosted bootstrap fetch was blocked.\n"
                        f"visible_action_label={visible_action_label!r}; "
                        f"visible_buttons={list(recovery_surface.visible_button_labels)!r}; "
                        f"blocked_request_count={len(runtime.blocked_requests)}; "
                        f"surface_text={recovery_surface.surface_text!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Viewed the startup failure surface as a user before retrying to "
                        "confirm the only actionable controls were the recovery action and "
                        "Connect GitHub."
                    ),
                    observed=(
                        f"visible_action_label={visible_action_label!r}; "
                        f"visible_buttons={list(recovery_surface.visible_button_labels)!r}; "
                        f"surface_text={recovery_surface.surface_text!r}"
                    ),
                )

                successful_requests_before_click = len(runtime.successful_retry_requests)
                runtime.enable_retry_success()
                clicked_action_label = startup_page.click_recovery_action(
                    accepted_action_labels=RECOVERY_ACTION_LABELS,
                )

                shell_ready, shell_observation = poll_until(
                    probe=lambda: tracker_page.observe_interactive_shell(
                        SHELL_NAVIGATION_LABELS,
                    ),
                    is_satisfied=lambda observation: bool(observation.get("shell_ready")),
                    timeout_seconds=120,
                    interval_seconds=1,
                )
                result["shell_observation_after_retry"] = shell_observation
                result["successful_retry_requests"] = [
                    asdict(request) for request in runtime.successful_retry_requests
                ]
                if not shell_ready:
                    _record_step(
                        result,
                        step=2,
                        status="failed",
                        action=REQUEST_STEPS[1],
                        observed=(
                            "The recovery action was clicked, but the deployed app never "
                            "returned to the interactive shell.\n"
                            f"Observed shell state: {json.dumps(shell_observation, indent=2)}"
                        ),
                    )
                    _record_step(
                        result,
                        step=3,
                        status="failed",
                        action=REQUEST_STEPS[2],
                        observed=(
                            "Not reached because the app never cleared the startup recovery "
                            "surface after the retry action."
                        ),
                    )
                    raise AssertionError(
                        "Step 2 failed: clicking the recovery action did not restore the "
                        "interactive shell.\n"
                        f"Observed shell state:\n{json.dumps(shell_observation, indent=2)}",
                    )
                if len(runtime.successful_retry_requests) <= successful_requests_before_click:
                    raise AssertionError(
                        "Step 2 failed: the recovery action returned the shell, but no "
                        "successful re-request of the blocked startup artifact was captured.\n"
                        f"Blocked requests: {[asdict(request) for request in runtime.blocked_requests]}\n"
                        f"Successful retry requests: "
                        f"{[asdict(request) for request in runtime.successful_retry_requests]}",
                    )

                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=REQUEST_STEPS[1],
                    observed=(
                        "Clicked the visible recovery action and captured a successful "
                        "re-request of the blocked startup artifact.\n"
                        f"visible_action_label={visible_action_label!r}; "
                        f"clicked_action_label={clicked_action_label!r}; "
                        f"successful_retry_request_count={len(runtime.successful_retry_requests)}; "
                        f"shell_ready={shell_observation.get('shell_ready')!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Clicked the visible recovery action and confirmed the blank startup "
                        "failure surface disappeared in favor of the real navigation shell."
                    ),
                    observed=(
                        f"visible_navigation_labels={shell_observation.get('visible_navigation_labels')!r}; "
                        f"shell_ready={shell_observation.get('shell_ready')!r}; "
                        f"body_excerpt={_snippet(str(shell_observation.get('body_text', '')))}"
                    ),
                )

                switcher_ready, switcher_observation = poll_until(
                    probe=lambda: _open_workspace_switcher(page),
                    is_satisfied=lambda observation: _switcher_shows_recovered_workspaces(
                        observation,
                        preloaded_workspace_names=preloaded_workspace_names,
                    ),
                    timeout_seconds=120,
                    interval_seconds=1,
                )
                result["workspace_switcher_after_retry"] = _switcher_payload(
                    switcher_observation,
                )
                if not switcher_ready:
                    raise AssertionError(
                        "Step 3 failed: after the retry succeeded, the workspace switcher "
                        "did not expose saved workspace rows plus the footer controls.\n"
                        f"Observed switcher state:\n"
                        f"{json.dumps(_switcher_payload(switcher_observation), indent=2)}",
                    )

                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action=REQUEST_STEPS[2],
                    observed=(
                        "After the successful retry, the workspace switcher exposed saved "
                        "workspace rows and the visible footer controls.\n"
                        f"row_count={switcher_observation.row_count}; "
                        "recovered_workspace_names="
                        f"{_recovered_workspace_names(switcher_observation, preloaded_workspace_names)!r}; "
                        f"switcher_text={switcher_observation.switcher_text!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Opened the workspace switcher after recovery and read the visible "
                        "saved workspace entries plus the footer controls as a user."
                    ),
                    observed=(
                        f"row_summaries={[row.visible_text for row in switcher_observation.rows]!r}; "
                        f"footer_controls={_footer_controls(switcher_observation)!r}"
                    ),
                )

                page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["success_screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
                _write_pass_outputs(result)
                return
            except Exception:
                tracker_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["failure_screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                raise
    except Exception as error:
        error_trace = traceback.format_exc()
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = error_trace
        result["blocked_requests_before_retry"] = result.get(
            "blocked_requests_before_retry",
            [asdict(request) for request in runtime.blocked_requests],
        )
        result["successful_retry_requests"] = result.get(
            "successful_retry_requests",
            [asdict(request) for request in runtime.successful_retry_requests],
        )
        _write_failure_outputs(result)
        raise


def _open_workspace_switcher(
    page: LiveWorkspaceSwitcherPage,
) -> WorkspaceSwitcherObservation:
    try:
        return page.observe_open_switcher(timeout_ms=5_000)
    except (AssertionError, WebAppTimeoutError):
        return page.open_and_observe(timeout_ms=30_000)


def _initial_workspace_state() -> dict[str, object]:
    return {
        "migrationComplete": True,
        "profiles": [],
    }


def _footer_controls(switcher: WorkspaceSwitcherObservation) -> list[str]:
    controls: list[str] = []
    for label in ("Add workspace", "Save and switch"):
        if label in switcher.switcher_text:
            controls.append(label)
    return controls


def _workspace_names(workspace_state: dict[str, object]) -> set[str]:
    raw_profiles = workspace_state.get("profiles", [])
    if not isinstance(raw_profiles, list):
        return set()
    names: set[str] = set()
    for profile in raw_profiles:
        if not isinstance(profile, dict):
            continue
        for key in ("customDisplayName", "displayName"):
            value = str(profile.get(key, "")).strip()
            if value:
                names.add(value)
                break
    return names


def _recovered_workspace_names(
    switcher: WorkspaceSwitcherObservation,
    preloaded_workspace_names: set[str],
) -> list[str]:
    recovered = {
        row.display_name
        for row in switcher.rows
        if row.display_name and row.display_name not in preloaded_workspace_names
    }
    return sorted(recovered)


def _switcher_shows_recovered_workspaces(
    observation: object,
    *,
    preloaded_workspace_names: set[str],
) -> bool:
    if not isinstance(observation, WorkspaceSwitcherObservation):
        return False
    recovered_workspace_names = _recovered_workspace_names(
        observation,
        preloaded_workspace_names,
    )
    return (
        bool(recovered_workspace_names)
        and HOSTED_SETUP_WORKSPACE_NAME in recovered_workspace_names
        and "Saved workspaces" in observation.switcher_text
        and "Add workspace" in observation.switcher_text
        and "Save and switch" in observation.switcher_text
    )


def _switcher_payload(switcher: WorkspaceSwitcherObservation) -> dict[str, object]:
    return {
        "body_text": switcher.body_text,
        "switcher_text": switcher.switcher_text,
        "row_count": switcher.row_count,
        "rows": [
            {
                "display_name": row.display_name,
                "target_type_label": row.target_type_label,
                "state_label": row.state_label,
                "detail_text": row.detail_text,
                "visible_text": row.visible_text,
                "selected": row.selected,
                "action_labels": list(row.action_labels),
                "button_labels": list(row.button_labels),
            }
            for row in switcher.rows
        ],
    }


def _recovery_surface_payload(
    observation: StartupRecoverySurfaceObservation,
) -> dict[str, object]:
    return {
        "body_text": observation.body_text,
        "surface_text": observation.surface_text,
        "visible_buttons": list(observation.visible_button_labels),
        "visible_action_label": observation.visible_action_label,
        "connect_github_visible": observation.connect_github_visible,
        "container_tag_name": observation.container_tag_name,
        "container_role": observation.container_role,
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


def _record_not_reached_steps(result: dict[str, object], *, starting_step: int) -> None:
    for step_number in range(starting_step, len(REQUEST_STEPS) + 1):
        _record_step(
            result,
            step=step_number,
            status="failed",
            action=REQUEST_STEPS[step_number - 1],
            observed="Not reached because the prior step did not complete successfully.",
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


def _snippet(value: str, *, limit: int = 300) -> str:
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


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
        ),
        encoding="utf-8",
    )
    jira_comment = _jira_comment(result, status="PASSED")
    pr_body = _markdown_summary(result, status="PASSED")
    JIRA_COMMENT_PATH.write_text(jira_comment, encoding="utf-8")
    PR_BODY_PATH.write_text(pr_body, encoding="utf-8")
    RESPONSE_PATH.write_text(pr_body, encoding="utf-8")


def _write_failure_outputs(result: dict[str, object]) -> None:
    RESULT_PATH.write_text(
        json.dumps(
            {
                "status": "failed",
                "passed": 0,
                "failed": 1,
                "skipped": 0,
                "summary": "0 passed, 1 failed",
                "error": str(result.get("error", "AssertionError: TS-983 failed")),
            },
        ),
        encoding="utf-8",
    )
    jira_comment = _jira_comment(result, status="FAILED")
    pr_body = _markdown_summary(result, status="FAILED")
    bug_description = _bug_description(result)
    JIRA_COMMENT_PATH.write_text(jira_comment, encoding="utf-8")
    PR_BODY_PATH.write_text(pr_body, encoding="utf-8")
    RESPONSE_PATH.write_text(pr_body, encoding="utf-8")
    BUG_DESCRIPTION_PATH.write_text(bug_description, encoding="utf-8")


def _jira_comment(result: dict[str, object], *, status: str) -> str:
    lines = [
        f"h2. {status} - {TICKET_KEY}",
        "",
        f"*Test case*: {TEST_CASE_TITLE}",
        f"*Expected result*: {EXPECTED_RESULT}",
        (
            f"*Environment*: URL={result.get('app_url')} | Browser={result.get('browser')} | "
            f"OS={result.get('os')} | Viewport={DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}"
        ),
        (
            f"*Blocked startup path*: {result.get('blocked_bootstrap_path')} | "
            f"*Linked bugs considered*: {', '.join(LINKED_BUGS)}"
        ),
        "",
        "h3. Automated verification",
    ]
    for step in result.get("steps", []):
        if not isinstance(step, dict):
            continue
        marker = "(/)" if step.get("status") == "passed" else "(x)"
        lines.extend(
            [
                f"{marker} *Step {step.get('step')}*: {step.get('action')}",
                f"{{noformat}}{step.get('observed', '')}{{noformat}}",
            ],
        )
    lines.extend(["", "h3. Real user-style verification"])
    for check in result.get("human_verification", []):
        if not isinstance(check, dict):
            continue
        lines.extend(
            [
                f"*Check*: {check.get('check')}",
                f"{{noformat}}{check.get('observed', '')}{{noformat}}",
            ],
        )
    if status == "FAILED":
        lines.extend(
            [
                "",
                "h3. Failure details",
                f"*Error*: {{noformat}}{result.get('error', '')}{{noformat}}",
                f"*Screenshot*: {result.get('failure_screenshot', '')}",
            ],
        )
    else:
        lines.extend(
            [
                "",
                "h3. Observed outcome",
                (
                    "The recovery action re-requested the blocked startup artifact, cleared "
                    "the failed startup surface, restored the interactive shell, and the "
                    "workspace switcher showed saved rows plus Add workspace / Save and "
                    "switch footer controls."
                ),
                f"*Screenshot*: {result.get('success_screenshot', '')}",
            ],
        )
    return "\n".join(lines) + "\n"


def _markdown_summary(result: dict[str, object], *, status: str) -> str:
    lines = [
        f"## {status} - {TICKET_KEY}",
        "",
        f"**Test case:** {TEST_CASE_TITLE}",
        f"**Expected result:** {EXPECTED_RESULT}",
        (
            f"**Environment:** URL={result.get('app_url')} · Browser={result.get('browser')} · "
            f"OS={result.get('os')} · Viewport={DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}"
        ),
        (
            f"**Blocked startup path:** `{result.get('blocked_bootstrap_path')}` · "
            f"**Linked bugs considered:** {', '.join(LINKED_BUGS)}"
        ),
        "",
        "### Automated verification",
    ]
    for step in result.get("steps", []):
        if not isinstance(step, dict):
            continue
        marker = "✅" if step.get("status") == "passed" else "❌"
        lines.extend(
            [
                f"{marker} **Step {step.get('step')}** — {step.get('action')}",
                "",
                "```text",
                str(step.get("observed", "")),
                "```",
            ],
        )
    lines.extend(["", "### Real user-style verification"])
    for check in result.get("human_verification", []):
        if not isinstance(check, dict):
            continue
        lines.extend(
            [
                f"- **Check:** {check.get('check')}",
                f"  - **Observed:** {check.get('observed')}",
            ],
        )
    if status == "FAILED":
        lines.extend(
            [
                "",
                "### Failure details",
                "",
                "```text",
                str(result.get("error", "")),
                "```",
                "",
                f"**Screenshot:** `{result.get('failure_screenshot', '')}`",
            ],
        )
    else:
        lines.extend(
            [
                "",
                "### Observed outcome",
                "",
                (
                    "The visible recovery action re-triggered the blocked startup fetch and "
                    "the deployed app returned to the live shell. Opening the workspace "
                    "switcher then showed saved workspace rows plus the `Add workspace` and "
                    "`Save and switch` footer controls."
                ),
                "",
                f"**Screenshot:** `{result.get('success_screenshot', '')}`",
            ],
        )
    return "\n".join(lines) + "\n"


def _bug_description(result: dict[str, object]) -> str:
    lines = [
        f"h2. {TICKET_KEY} automated regression failure",
        "",
        "h3. Steps to reproduce",
    ]
    for step in result.get("steps", []):
        if not isinstance(step, dict):
            continue
        status = "passed" if step.get("status") == "passed" else "failed"
        marker = "✅" if status == "passed" else "❌"
        lines.extend(
            [
                f"{marker} Step {step.get('step')}: {step.get('action')}",
                str(step.get("observed", "")),
                "",
            ],
        )
    lines.extend(
        [
            "h3. Exact error message / assertion failure",
            "{code}",
            str(result.get("traceback", result.get("error", ""))),
            "{code}",
            "",
            "h3. Actual vs Expected",
            f"*Expected*: {EXPECTED_RESULT}",
            (
                "*Actual*: "
                "The live deployment did not complete the retry-to-workspace-switcher flow "
                "described above. See the failed step annotations and captured shell / "
                "switcher observations for the exact break point."
            ),
            "",
            "h3. Environment",
            f"* URL: {result.get('app_url')}",
            f"* Browser: {result.get('browser')}",
            f"* OS: {result.get('os')}",
            f"* Viewport: {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
            f"* Repository: {result.get('repository')} @ {result.get('repository_ref')}",
            f"* Blocked startup path: {result.get('blocked_bootstrap_path')}",
            "",
            "h3. Logs / screenshots",
            f"* Screenshot: {result.get('failure_screenshot', '')}",
            "{code}",
            json.dumps(
                {
                    "blocked_requests_before_retry": result.get("blocked_requests_before_retry", []),
                    "successful_retry_requests": result.get("successful_retry_requests", []),
                    "recovery_surface_before_retry": result.get(
                        "recovery_surface_before_retry",
                        {},
                    ),
                    "shell_observation_after_retry": result.get(
                        "shell_observation_after_retry",
                        {},
                    ),
                    "workspace_switcher_after_retry": result.get(
                        "workspace_switcher_after_retry",
                        {},
                    ),
                },
                indent=2,
            ),
            "{code}",
        ],
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
