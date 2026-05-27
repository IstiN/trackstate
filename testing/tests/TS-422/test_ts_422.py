from __future__ import annotations

import json
import platform
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_hosted_index_recovery_page import (  # noqa: E402
    HostedIndexRecoveryObservation,
    LiveHostedIndexRecoveryPage,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.utils.polling import poll_until  # noqa: E402
from testing.tests.support.ts422_missing_index_runtime import (  # noqa: E402
    MissingIndexBootstrapObservation,
    Ts422MissingIndexRuntime,
)

TICKET_KEY = "TS-422"
TEST_CASE_SUMMARY = (
    "Hosted recovery behavior — missing index prevents silent full scan"
)
BLOCKED_BOOTSTRAP_PATH = "DEMO/.trackstate/index/issues.json"
OBSERVATION_WINDOW_SECONDS = 8
RUN_COMMAND = "python testing/tests/TS-422/test_ts_422.py"
TEST_FILE_PATH = "testing/tests/TS-422/test_ts_422.py"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts422_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts422_failure.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_live_setup_test_config()
    request_observation = MissingIndexBootstrapObservation(
        repository=config.repository,
        ref=config.ref,
        blocked_path=BLOCKED_BOOTSTRAP_PATH,
    )
    runtime = Ts422MissingIndexRuntime(observation=request_observation)
    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "app_url": config.app_url,
        "repository": config.repository,
        "repository_ref": config.ref,
        "blocked_repository_path": BLOCKED_BOOTSTRAP_PATH,
        "observation_window_seconds": OBSERVATION_WINDOW_SECONDS,
        "steps": [],
        "human_verification": [],
    }

    try:
        with runtime as session:
            page = LiveHostedIndexRecoveryPage(session, config.app_url)
            try:
                page.open()
                failure_surface = page.wait_for_failure_surface()
                result["failure_surface"] = _failure_surface_payload(failure_surface)

                if not request_observation.tree_urls:
                    raise AssertionError(
                        "Step 1 failed: the hosted bootstrap never issued a recursive GitHub "
                        "tree request, so the missing-index scenario was not exercised.\n"
                        f"Observed bootstrap URLs: {request_observation.bootstrap_urls}\n"
                        f"Observed body text:\n{failure_surface.body_text}",
                    )
                if not request_observation.modified_tree_urls:
                    raise AssertionError(
                        "Step 1 failed: the test runtime did not remove "
                        f"`{BLOCKED_BOOTSTRAP_PATH}` from the recursive tree response.\n"
                        f"Observed tree URLs: {request_observation.tree_urls}",
                    )
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action="Attempt to bootstrap the hosted web app with `.trackstate/index/issues.json` missing from the repository tree.",
                    observed=(
                        f"tree_requests={len(request_observation.tree_urls)}; "
                        f"modified_tree_requests={len(request_observation.modified_tree_urls)}; "
                        f"blocked_index_fetches={len(request_observation.blocked_index_urls)}"
                    ),
                )

                stable, counts = poll_until(
                    probe=lambda: (
                        len(request_observation.tree_urls),
                        len(request_observation.issue_content_urls),
                    ),
                    is_satisfied=lambda snapshot: snapshot[0] >= 1,
                    timeout_seconds=15,
                    interval_seconds=1,
                )
                if not stable:
                    raise AssertionError(
                        "Step 2 failed: the hosted startup never completed the initial "
                        "recursive tree read needed to evaluate fallback behavior.\n"
                        f"Observed tree URLs: {request_observation.tree_urls}\n"
                        f"Observed body text:\n{failure_surface.body_text}",
                    )

                baseline_tree_count, baseline_issue_reads = counts
                session.wait_for_function(
                    """
                    ({ startedAt, durationMs }) =>
                      typeof startedAt === 'number'
                      && performance.now() - startedAt >= durationMs
                    """,
                    arg={
                        "startedAt": session.evaluate("() => performance.now()"),
                        "durationMs": OBSERVATION_WINDOW_SECONDS * 1000,
                    },
                    timeout_ms=(OBSERVATION_WINDOW_SECONDS + 5) * 1000,
                )

                if len(request_observation.issue_content_urls) != baseline_issue_reads:
                    raise AssertionError(
                        "Step 2 failed: the hosted runtime silently hydrated issue "
                        "`main.md` files after the missing summary index was detected.\n"
                        f"Observed issue content URLs: {request_observation.issue_content_urls}\n"
                        f"Observed tree URLs: {request_observation.tree_urls}\n"
                        f"Observed body text:\n{page.current_body_text()}",
                    )
                if len(request_observation.issue_content_urls) != 0:
                    raise AssertionError(
                        "Step 2 failed: the hosted runtime fell back to issue file hydration "
                        "instead of failing explicitly once the summary index was missing.\n"
                        f"Observed issue content URLs: {request_observation.issue_content_urls}\n"
                        f"Observed body text:\n{page.current_body_text()}",
                    )
                if len(request_observation.tree_urls) != baseline_tree_count:
                    raise AssertionError(
                        "Step 2 failed: the hosted runtime re-ran the recursive GitHub tree "
                        "walk automatically while the missing-index failure state was visible.\n"
                        f"Initial tree count: {baseline_tree_count}\n"
                        f"Observed tree URLs: {request_observation.tree_urls}\n"
                        f"Observed body text:\n{page.current_body_text()}",
                    )
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action="Monitor GitHub API calls and confirm no silent fallback tree replay or mass issue-file hydration occurs.",
                    observed=(
                        f"tree_requests={len(request_observation.tree_urls)}; "
                        f"issue_main_reads={len(request_observation.issue_content_urls)}; "
                        f"other_content_reads={len(request_observation.other_content_urls)}"
                    ),
                )

                _record_human_verification(
                    result,
                    status=(
                        "passed"
                        if failure_surface.regenerate_guidance_visible
                        else "failed"
                    ),
                    check=(
                        "Verified the user-visible failure copy explains that the hosted "
                        "bootstrap index must be regenerated."
                    ),
                    observed=(
                        f"guidance_visible={failure_surface.regenerate_guidance_visible}; "
                        f"body_text={failure_surface.body_text}"
                    ),
                )
                _record_human_verification(
                    result,
                    status="passed" if failure_surface.retry_visible else "failed",
                    check=(
                        "Verified the user-visible failure surface exposes a Retry control "
                        "instead of silently continuing with repository scanning."
                    ),
                    observed=(
                        f"retry_visible={failure_surface.retry_visible}; "
                        f"visible_buttons={list(failure_surface.visible_button_labels)}"
                    ),
                )

                step_3_error = _failure_surface_error(failure_surface)
                _record_step(
                    result,
                    step=3,
                    status="failed" if step_3_error else "passed",
                    action="Observe the visible UI state.",
                    observed=step_3_error or failure_surface.body_text,
                )

                verification_errors: list[str] = []
                if step_3_error:
                    verification_errors.append(step_3_error)
                if not failure_surface.regenerate_guidance_visible:
                    verification_errors.append(
                        "Human-style verification failed: the missing-index failure surface "
                        "did not explain that the tracker indexes must be regenerated.\n"
                        f"Observed body text:\n{failure_surface.body_text}",
                    )
                if not failure_surface.retry_visible:
                    verification_errors.append(
                        "Human-style verification failed: the missing-index failure surface "
                        "did not render a visible Retry action the user could choose.\n"
                        f"Visible buttons: {failure_surface.visible_button_labels}\n"
                        f"Observed body text:\n{failure_surface.body_text}",
                    )

                if failure_surface.retry_visible:
                    retry_tree_count = len(request_observation.tree_urls)
                    page.tap_retry()
                    retried = page.wait_for_failure_surface(timeout_ms=60_000)
                    result["retry_failure_surface"] = _failure_surface_payload(retried)

                    retry_error: str | None = None
                    if len(request_observation.tree_urls) <= retry_tree_count:
                        retry_error = (
                            "Human-style verification failed: clicking Retry did not trigger "
                            "a new hosted bootstrap attempt.\n"
                            f"Initial tree count: {retry_tree_count}\n"
                            f"Observed tree URLs: {request_observation.tree_urls}\n"
                            f"Observed body text:\n{retried.body_text}"
                        )
                    elif (
                        not retried.regenerate_guidance_visible
                        or not retried.retry_visible
                    ):
                        retry_error = (
                            "Human-style verification failed: after clicking Retry, the app "
                            "did not return to the same visible recoverable failure surface.\n"
                            f"Observed body text:\n{retried.body_text}"
                        )
                    elif request_observation.issue_content_urls:
                        retry_error = (
                            "Human-style verification failed: after clicking Retry, the app "
                            "started hydrating issue `main.md` files instead of staying in "
                            "the explicit missing-index failure state.\n"
                            "Observed issue content URLs: "
                            f"{request_observation.issue_content_urls}\n"
                            f"Observed body text:\n{retried.body_text}"
                        )

                    _record_human_verification(
                        result,
                        status="failed" if retry_error else "passed",
                        check=(
                            "Clicked Retry and confirmed the app performed one explicit retry "
                            "attempt while keeping the same visible index-regeneration failure "
                            "guidance on screen."
                        ),
                        observed=(
                            retry_error
                            or (
                                f"tree_requests_before_retry={retry_tree_count}; "
                                f"tree_requests_after_retry={len(request_observation.tree_urls)}; "
                                f"issue_main_reads={len(request_observation.issue_content_urls)}"
                            )
                        ),
                    )
                    if retry_error:
                        verification_errors.append(retry_error)
                else:
                    _record_human_verification(
                        result,
                        status="failed",
                        check=(
                            "Clicked Retry and confirmed the app performed one explicit retry "
                            "attempt while keeping the same visible index-regeneration failure "
                            "guidance on screen."
                        ),
                        observed=(
                            "Retry could not be exercised because the failure surface only "
                            f"showed {failure_surface.visible_button_labels}."
                        ),
                    )

                if verification_errors:
                    raise AssertionError("\n\n".join(verification_errors))

                page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
                result["request_observation"] = _request_observation_payload(
                    request_observation
                )
                _write_pass_outputs(result)
                return
            except Exception:
                page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                raise
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        result["request_observation"] = _request_observation_payload(request_observation)
        _write_failure_outputs(result)
        raise


def _failure_surface_error(observation: HostedIndexRecoveryObservation) -> str | None:
    issues: list[str] = []
    if not observation.tracker_data_not_found_visible:
        issues.append(
            "the failure surface did not explicitly explain that the hosted issue "
            "index needed regeneration."
        )
    if not observation.regenerate_guidance_visible:
        issues.append(
            "the failure surface did not include guidance to regenerate the tracker "
            "indexes."
        )
    if not observation.retry_visible:
        issues.append("the failure surface did not render a visible Retry action.")
    if not issues:
        return None
    return (
        "Step 3 failed: "
        + " ".join(issues)
        + "\n"
        f"Visible buttons: {observation.visible_button_labels}\n"
        f"Observed body text:\n{observation.body_text}"
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
    status: str,
    check: str,
    observed: str,
) -> None:
    checks = result.setdefault("human_verification", [])
    assert isinstance(checks, list)
    checks.append({"status": status, "check": check, "observed": observed})


def _failure_surface_payload(
    observation: HostedIndexRecoveryObservation,
) -> dict[str, object]:
    return {
        "body_text": observation.body_text,
        "retry_visible": observation.retry_visible,
        "connect_github_visible": observation.connect_github_visible,
        "regenerate_guidance_visible": observation.regenerate_guidance_visible,
        "tracker_data_not_found_visible": observation.tracker_data_not_found_visible,
        "app_title_visible": observation.app_title_visible,
        "visible_button_labels": list(observation.visible_button_labels),
    }


def _request_observation_payload(
    observation: MissingIndexBootstrapObservation,
) -> dict[str, object]:
    return {
        "blocked_target_url": observation.blocked_target_url,
        "bootstrap_urls": list(observation.bootstrap_urls),
        "tree_urls": list(observation.tree_urls),
        "modified_tree_urls": list(observation.modified_tree_urls),
        "blocked_index_urls": list(observation.blocked_index_urls),
        "issue_content_urls": list(observation.issue_content_urls),
        "other_content_urls": list(observation.other_content_urls),
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
            }
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
            }
        )
        + "\n",
        encoding="utf-8",
    )
    JIRA_COMMENT_PATH.write_text(_jira_comment(result, passed=False), encoding="utf-8")
    PR_BODY_PATH.write_text(_pr_body(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_summary(result, passed=False), encoding="utf-8")
    BUG_DESCRIPTION_PATH.write_text(_bug_description(result), encoding="utf-8")


def _jira_comment(result: dict[str, object], *, passed: bool) -> str:
    status = "✅ PASSED" if passed else "❌ FAILED"
    screenshot_path = result.get("screenshot", FAILURE_SCREENSHOT_PATH)
    lines = [
        "h3. Test Automation Result",
        "",
        f"*Status:* {status}",
        f"*Test Case:* {TICKET_KEY} — {TEST_CASE_SUMMARY}",
        "",
        "h4. What was tested",
        (
            f"* Removed {{{{{BLOCKED_BOOTSTRAP_PATH}}}}} from the intercepted recursive "
            "GitHub tree response while bootstrapping the deployed hosted app."
        ),
        (
            f"* Observed GitHub API traffic for {OBSERVATION_WINDOW_SECONDS} seconds to "
            "check for fallback tree replay or issue-file hydration."
        ),
        "* Checked the visible user-facing failure copy, guidance text, and Retry affordance.",
        "",
        "h4. Result",
        (
            "* Matched the expected result."
            if passed
            else f"* Did not match the expected result. {_failure_summary(result)}"
        ),
        (
            f"* Environment: URL {{{{{result['app_url']}}}}}, repository "
            f"{{{{{result['repository']}}}}} @ {{{{{result['repository_ref']}}}}}, "
            f"browser {{Chromium (Playwright)}}, OS {{{{{platform.system()}}}}}."
        ),
        f"* Screenshot: {{{{{screenshot_path}}}}}",
        "",
        "h4. Step results",
        *_step_lines(result, jira=True),
        "",
        "h4. Real user-style verification",
        *_human_lines(result, jira=True),
        "",
        "h4. Test file",
        "{code}",
        TEST_FILE_PATH,
        "{code}",
        "",
        "h4. Run command",
        "{code:bash}",
        RUN_COMMAND,
        "{code}",
    ]
    if not passed:
        lines.extend(
            [
                "",
                "h4. Exact error",
                "{code}",
                str(result.get("traceback", result.get("error", ""))),
                "{code}",
            ]
        )
    return "\n".join(lines) + "\n"


def _pr_body(result: dict[str, object], *, passed: bool) -> str:
    status = "✅ PASSED" if passed else "❌ FAILED"
    screenshot_path = result.get("screenshot", FAILURE_SCREENSHOT_PATH)
    lines = [
        "## Test Automation Result",
        "",
        f"**Status:** {status}",
        f"**Test Case:** {TICKET_KEY} — {TEST_CASE_SUMMARY}",
        "",
        "## What was automated",
        f"- Removed `{BLOCKED_BOOTSTRAP_PATH}` from the intercepted recursive GitHub tree response while bootstrapping the deployed hosted app.",
        f"- Observed GitHub API traffic for {OBSERVATION_WINDOW_SECONDS} seconds to detect fallback tree replay or issue `main.md` hydration.",
        "- Verified the live user-facing failure copy, regeneration guidance, and Retry affordance.",
        "",
        "## Result",
        (
            "- Matched the expected result."
            if passed
            else f"- Did not match the expected result: {_failure_summary(result)}"
        ),
        (
            f"- Environment: URL `{result['app_url']}`, repository `{result['repository']}` "
            f"@ `{result['repository_ref']}`, browser `Chromium (Playwright)`, OS `{platform.system()}`."
        ),
        f"- Screenshot: `{screenshot_path}`",
        "",
        "### Step results",
        *_step_lines(result, jira=False),
        "",
        "### Real user-style verification",
        *_human_lines(result, jira=False),
        "",
        "## Test file",
        f"`{TEST_FILE_PATH}`",
        "",
        "## How to run",
        "```bash",
        RUN_COMMAND,
        "```",
    ]
    if not passed:
        lines.extend(
            [
                "",
                "### Exact error",
                "```text",
                str(result.get("traceback", result.get("error", ""))),
                "```",
            ]
        )
    return "\n".join(lines) + "\n"


def _response_summary(result: dict[str, object], *, passed: bool) -> str:
    status = "passed" if passed else "failed"
    screenshot_path = result.get("screenshot", FAILURE_SCREENSHOT_PATH)
    lines = [
        f"# {TICKET_KEY} {status}",
        "",
        f"**Test Case:** {TEST_CASE_SUMMARY}",
        "",
        "## Summary",
        (
            f"Ran the deployed hosted app with `{BLOCKED_BOOTSTRAP_PATH}` removed from the "
            "intercepted GitHub tree response."
        ),
        "",
        "## Observed",
        f"- Screenshot: `{screenshot_path}`",
        f"- Environment: `{result['app_url']}` on Chromium/Playwright ({platform.system()})",
        (
            f"- Request summary: `{result.get('request_observation', {}).get('tree_urls', [])}`"
            if isinstance(result.get("request_observation"), dict)
            else ""
        ),
    ]
    if not passed:
        lines.extend(
            [
                "",
                "## Error",
                "```text",
                str(result.get("traceback", result.get("error", ""))),
                "```",
            ]
        )
    return "\n".join(line for line in lines if line != "") + "\n"


def _bug_description(result: dict[str, object]) -> str:
    request_observation = result.get("request_observation")
    failure_surface = result.get("failure_surface")
    lines = [
        f"h3. {TICKET_KEY} — {TEST_CASE_SUMMARY}",
        "",
        "h4. Environment",
        f"* URL: {{{{{result['app_url']}}}}}",
        f"* Repository: {{{{{result['repository']}}}}} @ {{{{{result['repository_ref']}}}}}",
        "* Browser: {{Chromium (Playwright)}}",
        f"* OS: {{{{{platform.platform()}}}}}",
        f"* Removed bootstrap artifact from tree: {{{{{BLOCKED_BOOTSTRAP_PATH}}}}}",
        f"* Observation window: {{{{{OBSERVATION_WINDOW_SECONDS} seconds}}}}",
        "",
        "h4. Steps to Reproduce",
        (
            "# Attempt to bootstrap the hosted web app. "
            f"{_status_icon(_step_status(result, 1))} {_step_observation(result, 1)}"
        ),
        (
            "# Monitor GitHub API calls to ensure no recursive tree walk or mass-file "
            f"hydration occurs as a fallback. {_status_icon(_step_status(result, 2))} "
            f"{_step_observation(result, 2)}"
        ),
        (
            "# Observe the UI state. "
            f"{_status_icon(_step_status(result, 3))} {_step_observation(result, 3)}"
        ),
        (
            "# Click the visible {{Retry}} option and observe the recovery state. "
            f"{_status_icon(_human_status(result, 3))} {_human_observation(result, 3)}"
        ),
        "",
        "h4. Expected Result",
        (
            "The app shows a recoverable failure state with a visible {{Retry}} option and "
            "guidance on index regeneration. No silent full-scan fallback is performed."
        ),
        "",
        "h4. Actual Result",
        _bug_actual_result(result),
        "",
        "h4. Logs / Error Output",
        "{code}",
        str(result.get("traceback", result.get("error", ""))),
        "{code}",
        "",
        "h4. Notes",
        f"* Screenshot: {{{{{result.get('screenshot', FAILURE_SCREENSHOT_PATH)}}}}}",
    ]
    if isinstance(failure_surface, dict):
        lines.extend(
            [
                (
                    "* Visible failure body text: "
                    f"{{{{{failure_surface.get('body_text', '')}}}}}"
                ),
                (
                    "* Visible buttons: "
                    f"{{{{{failure_surface.get('visible_button_labels', [])}}}}}"
                ),
            ]
        )
    if isinstance(request_observation, dict):
        lines.extend(
            [
                f"* Recursive tree URLs: {{{{{request_observation.get('tree_urls', [])}}}}}",
                (
                    "* Issue content URLs: "
                    f"{{{{{request_observation.get('issue_content_urls', [])}}}}}"
                ),
                (
                    "* Other content URLs: "
                    f"{{{{{request_observation.get('other_content_urls', [])}}}}}"
                ),
            ]
        )
    return "\n".join(lines) + "\n"


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for step in result.get("steps", []):
        if not isinstance(step, dict):
            continue
        prefix = "#" if jira else "1."
        lines.append(
            f"{prefix} Step {step['step']} — {step['action']} — {step['status'].upper() if jira else step['status']}: {step['observed']}"
        )
    if not lines:
        lines.append("# No step details were recorded." if jira else "1. No step details were recorded.")
    return lines


def _human_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for check in result.get("human_verification", []):
        if not isinstance(check, dict):
            continue
        prefix = "*" if jira else "-"
        status = str(check.get("status", "passed")).upper()
        lines.append(
            f"{prefix} [{status}] {check['check']} Observed: {check['observed']}"
        )
    if not lines:
        lines.append("* No human-style verification was recorded." if jira else "- No human-style verification was recorded.")
    return lines


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


def _human_check_passed(result: dict[str, object], index: int) -> bool:
    checks = result.get("human_verification", [])
    if not isinstance(checks, list) or index - 1 >= len(checks):
        return False
    check = checks[index - 1]
    return isinstance(check, dict) and check.get("status") == "passed"


def _human_status(result: dict[str, object], index: int) -> str:
    checks = result.get("human_verification", [])
    if not isinstance(checks, list) or index - 1 >= len(checks):
        return "failed"
    check = checks[index - 1]
    if not isinstance(check, dict):
        return "failed"
    return str(check.get("status", "failed"))


def _human_observation(result: dict[str, object], index: int) -> str:
    checks = result.get("human_verification", [])
    if not isinstance(checks, list) or index - 1 >= len(checks):
        return str(result.get("error", "No human verification recorded."))
    check = checks[index - 1]
    if not isinstance(check, dict):
        return str(result.get("error", "No human verification recorded."))
    return str(check.get("observed", "No human verification recorded."))


def _status_icon(status: str) -> str:
    return "✅" if status == "passed" else "❌"


def _failure_summary(result: dict[str, object]) -> str:
    step_observation = _step_observation(result, 3).strip()
    if step_observation:
        return step_observation.splitlines()[0]
    return str(result.get("error", "The test failed without a recorded step observation."))


def _bug_actual_result(result: dict[str, object]) -> str:
    failure_surface = result.get("failure_surface")
    if not isinstance(failure_surface, dict):
        return _failure_summary(result)

    body_text = str(failure_surface.get("body_text", "")).strip()
    visible_buttons = tuple(failure_surface.get("visible_button_labels", ()))
    return (
        "Observed the hosted missing-index recovery surface with body text "
        f"{{{{{body_text}}}}} and visible buttons {{{{{visible_buttons}}}}}. "
        f"{_failure_summary(result)}"
    )


if __name__ == "__main__":
    main()
