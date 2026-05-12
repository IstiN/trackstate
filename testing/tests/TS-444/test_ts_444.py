from __future__ import annotations

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
from testing.tests.support.startup_recovery_rate_limit_runtime import (  # noqa: E402
    StartupRecoveryRateLimitObservation,
    StartupRecoveryRateLimitRuntime,
)

TICKET_KEY = "TS-444"
BLOCKED_BOOTSTRAP_PATH = "DEMO/.trackstate/index/tombstones.json"
RATE_LIMIT_MESSAGE = "API rate limit exceeded for TS-444 synthetic deferred bootstrap probe"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts444_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts444_failure.png"
SHELL_NAVIGATION_LABELS = (
    "Dashboard",
    "Board",
    "JQL Search",
    "Hierarchy",
    "Settings",
)


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_live_setup_test_config()
    rate_limit_observation = StartupRecoveryRateLimitObservation(
        blocked_repository_path=BLOCKED_BOOTSTRAP_PATH,
    )
    runtime = StartupRecoveryRateLimitRuntime(
        observation=rate_limit_observation,
        failure_message=RATE_LIMIT_MESSAGE,
    )

    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "app_url": config.app_url,
        "repository": config.repository,
        "repository_ref": config.ref,
        "blocked_repository_path": BLOCKED_BOOTSTRAP_PATH,
        "steps": [],
        "human_verification": [],
    }

    try:
        with create_live_tracker_app(
            config,
            runtime_factory=lambda: runtime,
        ) as tracker_page:
            page = LiveStartupRecoveryPage(tracker_page)
            try:
                runtime_state = tracker_page.open()
                result["runtime_state"] = runtime_state.kind
                result["runtime_body_text"] = runtime_state.body_text
                if runtime_state.kind != "ready":
                    raise AssertionError(
                        "Precondition failed: the deployed app never reached the hosted "
                        "tracker shell before the TS-444 deferred-bootstrap scenario ran.\n"
                        f"Observed body text:\n{runtime_state.body_text}",
                    )

                blocked_detected, blocked_urls = poll_until(
                    probe=lambda: tuple(rate_limit_observation.blocked_urls),
                    is_satisfied=lambda blocked: len(blocked) > 0,
                    timeout_seconds=120,
                    interval_seconds=2,
                )
                result["blocked_urls"] = list(blocked_urls)
                if not blocked_detected:
                    raise AssertionError(
                        "Step 1 failed: the live app never requested the deferred bootstrap "
                        f"artifact `{BLOCKED_BOOTSTRAP_PATH}`, so the recoverable rate-limit "
                        "path was not exercised.\n"
                        f"Observed blocked URLs: {list(blocked_urls)}\n"
                        f"Observed body text:\n{page.current_body_text()}",
                    )
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=(
                        "Trigger a 403 GitHub rate limit during deferred bootstrap after the "
                        "mandatory hosted shell data has already loaded."
                    ),
                    observed="\n".join(blocked_urls),
                )

                shell_observation = page.wait_for_shell_routed_to_settings(timeout_ms=120_000)
                result["shell_observation"] = _shell_payload(shell_observation)
                _assert_shell_visible(shell_observation)
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action="Observe the rendered UI after the recoverable rate limit.",
                    observed=shell_observation.body_text,
                )

                if not shell_observation.settings_selected:
                    raise AssertionError(
                        "Step 3 failed: the visible selected navigation target was not "
                        "Settings after the recoverable deferred-bootstrap rate limit.\n"
                        f"Observed selected buttons: {shell_observation.selected_button_labels}\n"
                        f"Observed body text:\n{shell_observation.body_text}",
                    )
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action="Verify the active section corresponds to TrackerViewModel Settings.",
                    observed=(
                        f"selected_buttons={shell_observation.selected_button_labels}; "
                        f"settings_heading_visible={shell_observation.settings_heading_visible}"
                    ),
                )

                _record_human_verification(
                    result,
                    check=(
                        "Verified the visible shell still showed the sidebar navigation and "
                        "top-bar Settings title instead of a dead-end startup banner."
                    ),
                    observed=(
                        f"navigation={shell_observation.visible_navigation_labels}; "
                        f"topbar_title_visible={shell_observation.topbar_title_visible}; "
                        f"retry_visible={shell_observation.retry_visible}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        'Verified the user lands on the visible "Project settings '
                        'administration" content with the "Settings" navigation item selected.'
                    ),
                    observed=(
                        f"selected_buttons={shell_observation.selected_button_labels}; "
                        f"settings_heading_visible={shell_observation.settings_heading_visible}; "
                        f"connect_github_visible={shell_observation.connect_github_visible}"
                    ),
                )

                page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                _write_pass_outputs(result)
                return
            except Exception:
                tracker_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                raise
    except Exception as error:
        error_trace = traceback.format_exc()
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = error_trace
        _write_failure_outputs(result)
        raise


def _assert_shell_visible(shell_observation: StartupRecoveryShellObservation) -> None:
    missing_navigation = [
        label
        for label in SHELL_NAVIGATION_LABELS
        if label not in shell_observation.visible_navigation_labels
    ]
    if missing_navigation:
        raise AssertionError(
            "Step 2 failed: the recoverable rate-limit state did not keep the full app "
            "shell navigation visible.\n"
            f"Missing navigation labels: {missing_navigation}\n"
            f"Observed visible navigation labels: {shell_observation.visible_navigation_labels}\n"
            f"Observed body text:\n{shell_observation.body_text}",
        )
    if not shell_observation.topbar_title_visible:
        raise AssertionError(
            "Step 2 failed: the top bar did not keep the visible Project Settings title "
            "after the recoverable deferred-bootstrap rate limit.\n"
            f"Observed body text:\n{shell_observation.body_text}",
        )
    if not shell_observation.settings_heading_visible:
        raise AssertionError(
            "Step 2 failed: the Settings page content did not remain visible after the "
            "recoverable deferred-bootstrap rate limit.\n"
            f"Observed body text:\n{shell_observation.body_text}",
        )
    if not shell_observation.retry_visible:
        raise AssertionError(
            "Step 2 failed: the recovery affordance was not visible after the deferred "
            "bootstrap rate limit.\n"
            f"Observed body text:\n{shell_observation.body_text}",
        )


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


def _shell_payload(observation: StartupRecoveryShellObservation) -> dict[str, object]:
    return {
        "body_text": observation.body_text,
        "selected_button_labels": list(observation.selected_button_labels),
        "visible_navigation_labels": list(observation.visible_navigation_labels),
        "retry_visible": observation.retry_visible,
        "connect_github_visible": observation.connect_github_visible,
        "topbar_title_visible": observation.topbar_title_visible,
        "settings_heading_visible": observation.settings_heading_visible,
    }


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
    PR_BODY_PATH.write_text(_pr_body(result, passed=True), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_summary(result, passed=True), encoding="utf-8")


def _write_failure_outputs(result: dict[str, object]) -> None:
    error = str(result.get("error", "AssertionError: unknown failure"))
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
    PR_BODY_PATH.write_text(_pr_body(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_summary(result, passed=False), encoding="utf-8")
    BUG_DESCRIPTION_PATH.write_text(_bug_description(result), encoding="utf-8")


def _jira_comment(result: dict[str, object], *, passed: bool) -> str:
    status = "PASSED" if passed else "FAILED"
    steps = _steps_lines(result, jira=True)
    human_checks = _human_lines(result, jira=True)
    screenshot_path = SUCCESS_SCREENSHOT_PATH if passed else FAILURE_SCREENSHOT_PATH
    outcome = (
        "Matched the expected result: the app shell stayed visible and the visible "
        "selected destination was Settings after the recoverable deferred-bootstrap rate limit."
        if passed
        else "Did not match the expected result."
    )
    lines = [
        f"h3. {TICKET_KEY} {status}",
        "",
        "*Automation coverage*",
        (
            f"* Blocked {{{{{BLOCKED_BOOTSTRAP_PATH}}}}} with a synthetic GitHub 403 "
            "rate-limit response during deferred bootstrap."
        ),
        "* Confirmed the app stayed in the hosted shell with Settings content visible.",
        "* Confirmed the visible selected navigation target was Settings.",
        "",
        "*Observed result*",
        f"* {outcome}",
        (
            f"* Environment: URL {{{{{result['app_url']}}}}}, repository "
            f"{{{{{result['repository']}}}}} @ {{{{{result['repository_ref']}}}}}, "
            f"browser {{Chromium (Playwright)}}, OS {{{{{platform.system()}}}}}."
        ),
        f"* Screenshot: {{{{{screenshot_path}}}}}",
        "",
        "*Step results*",
        *steps,
        "",
        "*Human-style verification*",
        *human_checks,
    ]
    if not passed:
        lines.extend(
            [
                "",
                "*Exact error*",
                "{code}",
                str(result.get("traceback", result.get("error", ""))),
                "{code}",
            ],
        )
    return "\n".join(lines) + "\n"


def _pr_body(result: dict[str, object], *, passed: bool) -> str:
    status = "Passed" if passed else "Failed"
    steps = _steps_lines(result, jira=False)
    human_checks = _human_lines(result, jira=False)
    screenshot_path = SUCCESS_SCREENSHOT_PATH if passed else FAILURE_SCREENSHOT_PATH
    outcome = (
        "Matched the expected result: the app shell stayed visible and the selected section was Settings after the recoverable deferred-bootstrap rate limit."
        if passed
        else "Did not match the expected result."
    )
    lines = [
        f"## {TICKET_KEY} {status}",
        "",
        "### Automation",
        f"- Blocked `{BLOCKED_BOOTSTRAP_PATH}` with a synthetic GitHub 403 rate-limit response during deferred bootstrap.",
        "- Verified the hosted app shell stayed visible with sidebar navigation and Settings content rendered.",
        "- Verified the visible selected navigation target was `Settings`.",
        "",
        "### Observed result",
        f"- {outcome}",
        (
            f"- Environment: URL `{result['app_url']}`, repository `{result['repository']}` "
            f"@ `{result['repository_ref']}`, browser `Chromium (Playwright)`, OS `{platform.system()}`."
        ),
        f"- Screenshot: `{screenshot_path}`",
        "",
        "### Step results",
        *steps,
        "",
        "### Human-style verification",
        *human_checks,
    ]
    if not passed:
        lines.extend(
            [
                "",
                "### Exact error",
                "```text",
                str(result.get("traceback", result.get("error", ""))),
                "```",
            ],
        )
    return "\n".join(lines) + "\n"


def _response_summary(result: dict[str, object], *, passed: bool) -> str:
    status = "passed" if passed else "failed"
    screenshot_path = SUCCESS_SCREENSHOT_PATH if passed else FAILURE_SCREENSHOT_PATH
    lines = [
        f"# {TICKET_KEY} {status}",
        "",
        (
            f"Blocked `{BLOCKED_BOOTSTRAP_PATH}` with a synthetic GitHub rate-limit 403 "
            "during deferred bootstrap and exercised the live hosted recovery path."
        ),
        "",
        "## Observed",
        f"- Selected buttons: {result.get('shell_observation', {}).get('selected_button_labels', []) if isinstance(result.get('shell_observation'), dict) else []}",
        f"- Screenshot: `{screenshot_path}`",
        f"- Environment: `{result['app_url']}` on Chromium/Playwright ({platform.system()})",
    ]
    if not passed:
        lines.extend(
            [
                "",
                "## Error",
                "```text",
                str(result.get("traceback", result.get("error", ""))),
                "```",
            ],
        )
    return "\n".join(lines) + "\n"


def _bug_description(result: dict[str, object]) -> str:
    lines = [
        f"# {TICKET_KEY} - Recovery entry point regression",
        "",
        "## Steps to reproduce",
        "1. Trigger a 403 rate limit during the `deferred-bootstrap` phase where mandatory artifacts were already cached or loaded.",
        (
            f"   - {'✅' if _step_status(result, 1) == 'passed' else '❌'} "
            f"{_step_observation(result, 1)}"
        ),
        "2. Observe the rendered UI.",
        (
            f"   - {'✅' if _step_status(result, 2) == 'passed' else '❌'} "
            f"{_step_observation(result, 2)}"
        ),
        "3. Verify the current active section in `TrackerViewModel`.",
        (
            f"   - {'✅' if _step_status(result, 3) == 'passed' else '❌'} "
            f"{_step_observation(result, 3)}"
        ),
        "",
        "## Actual vs Expected",
        "- Expected: the hosted app shell keeps the TopBar and Sidebar visible and automatically lands in Settings after the recoverable deferred-bootstrap rate limit.",
        (
            "- Actual: "
            + str(
                result.get("error")
                or "the visible shell or Settings selection did not match the expected recovery behavior."
            )
        ),
        "",
        "## Exact error message",
        "```text",
        str(result.get("traceback", result.get("error", ""))),
        "```",
        "",
        "## Environment",
        f"- URL: `{result['app_url']}`",
        f"- Repository: `{result['repository']}` @ `{result['repository_ref']}`",
        "- Browser: `Chromium (Playwright)`",
        f"- OS: `{platform.platform()}`",
        f"- Blocked bootstrap artifact: `{BLOCKED_BOOTSTRAP_PATH}`",
        "",
        "## Evidence",
        f"- Screenshot: `{FAILURE_SCREENSHOT_PATH}`",
        f"- Blocked URLs: `{result.get('blocked_urls', [])}`",
        "",
        "## Observed body text",
        "```text",
        str(
            result.get("shell_observation", {}).get("body_text")
            if isinstance(result.get("shell_observation"), dict)
            else result.get("runtime_body_text", "")
        ),
        "```",
    ]
    return "\n".join(lines) + "\n"


def _steps_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    marker = "*" if jira else "-"
    rendered: list[str] = []
    for step in result.get("steps", []):
        if not isinstance(step, dict):
            continue
        status = str(step.get("status", "")).upper()
        action = str(step.get("action", ""))
        observed = str(step.get("observed", ""))
        rendered.append(f"{marker} Step {step.get('step')}: {status} - {action}")
        rendered.append(f"{marker} Observed: {observed}")
    return rendered or [f"{marker} No step data was recorded."]


def _human_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    marker = "*" if jira else "-"
    rendered: list[str] = []
    for check in result.get("human_verification", []):
        if not isinstance(check, dict):
            continue
        rendered.append(f"{marker} {check.get('check')}")
        rendered.append(f"{marker} Observed: {check.get('observed')}")
    return rendered or [f"{marker} No human-style verification data was recorded."]


def _step_status(result: dict[str, object], step_number: int) -> str:
    for step in result.get("steps", []):
        if isinstance(step, dict) and step.get("step") == step_number:
            return str(step.get("status", "failed"))
    return "failed"


def _step_observation(result: dict[str, object], step_number: int) -> str:
    for step in result.get("steps", []):
        if isinstance(step, dict) and step.get("step") == step_number:
            return str(step.get("observed", "No observation recorded."))
    return str(result.get("error", "No observation recorded."))


if __name__ == "__main__":
    main()
