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
BLOCKED_BOOTSTRAP_PATH = "DEMO/.trackstate/index/issues.json"
OBSERVATION_WINDOW_SECONDS = 8
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
                    check=(
                        "Verified the user-visible failure surface exposes a Retry control "
                        "instead of silently continuing with repository scanning."
                    ),
                    observed=(
                        f"retry_visible={failure_surface.retry_visible}; "
                        f"visible_buttons={list(failure_surface.visible_button_labels)}"
                    ),
                )

                _assert_failure_surface(failure_surface)
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action="Observe the visible UI state.",
                    observed=failure_surface.body_text,
                )

                if not failure_surface.retry_visible:
                    raise AssertionError(
                        "Human-style verification failed: the missing-index failure surface "
                        "did not render a visible Retry action the user could choose.\n"
                        f"Visible buttons: {failure_surface.visible_button_labels}\n"
                        f"Observed body text:\n{failure_surface.body_text}",
                    )

                retry_tree_count = len(request_observation.tree_urls)
                page.tap_retry()
                retried = page.wait_for_failure_surface(timeout_ms=60_000)
                result["retry_failure_surface"] = _failure_surface_payload(retried)
                if len(request_observation.tree_urls) <= retry_tree_count:
                    raise AssertionError(
                        "Human-style verification failed: clicking Retry did not trigger a "
                        "new hosted bootstrap attempt.\n"
                        f"Initial tree count: {retry_tree_count}\n"
                        f"Observed tree URLs: {request_observation.tree_urls}\n"
                        f"Observed body text:\n{retried.body_text}",
                    )
                if not retried.regenerate_guidance_visible or not retried.retry_visible:
                    raise AssertionError(
                        "Human-style verification failed: after clicking Retry, the app did "
                        "not return to the same visible recoverable failure surface.\n"
                        f"Observed body text:\n{retried.body_text}",
                    )
                if request_observation.issue_content_urls:
                    raise AssertionError(
                        "Human-style verification failed: after clicking Retry, the app "
                        "started hydrating issue `main.md` files instead of staying in the "
                        "explicit missing-index failure state.\n"
                        f"Observed issue content URLs: {request_observation.issue_content_urls}\n"
                        f"Observed body text:\n{retried.body_text}",
                    )
                _record_human_verification(
                    result,
                    check=(
                        "Clicked Retry and confirmed the app performed one explicit retry "
                        "attempt while keeping the same visible index-regeneration failure "
                        "guidance on screen."
                    ),
                    observed=(
                        f"tree_requests_before_retry={retry_tree_count}; "
                        f"tree_requests_after_retry={len(request_observation.tree_urls)}; "
                        f"issue_main_reads={len(request_observation.issue_content_urls)}"
                    ),
                )

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


def _assert_failure_surface(observation: HostedIndexRecoveryObservation) -> None:
    if not observation.tracker_data_not_found_visible:
        raise AssertionError(
            "Step 3 failed: the failure surface did not explain that TrackState data could "
            "not be loaded.\n"
            f"Observed body text:\n{observation.body_text}",
        )
    if not observation.regenerate_guidance_visible:
        raise AssertionError(
            "Step 3 failed: the failure surface did not include guidance to regenerate the "
            "tracker indexes.\n"
            f"Observed body text:\n{observation.body_text}",
        )
    if not observation.retry_visible:
        raise AssertionError(
            "Step 3 failed: the failure surface did not render a visible Retry action.\n"
            f"Visible buttons: {observation.visible_button_labels}\n"
            f"Observed body text:\n{observation.body_text}",
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
    status = "PASSED" if passed else "FAILED"
    screenshot_path = result.get("screenshot", FAILURE_SCREENSHOT_PATH)
    lines = [
        f"h3. {TICKET_KEY} {status}",
        "",
        "*Automation coverage*",
        (
            f"* Removed {{{{{BLOCKED_BOOTSTRAP_PATH}}}}} from the intercepted recursive "
            "GitHub tree response while bootstrapping the deployed hosted app."
        ),
        (
            f"* Observed GitHub API traffic for {OBSERVATION_WINDOW_SECONDS} seconds to "
            "check for fallback tree replay or issue-file hydration."
        ),
        "* Checked the visible user-facing failure copy and Retry affordance.",
        "",
        "*Observed result*",
        (
            "* Matched the expected result."
            if passed
            else "* Did not match the expected result."
        ),
        (
            f"* Environment: URL {{{{{result['app_url']}}}}}, repository "
            f"{{{{{result['repository']}}}}} @ {{{{{result['repository_ref']}}}}}, "
            f"browser {{Chromium (Playwright)}}, OS {{{{{platform.system()}}}}}."
        ),
        f"* Screenshot: {{{{{screenshot_path}}}}}",
        "",
        "*Step results*",
        *_step_lines(result, jira=True),
        "",
        "*Human-style verification*",
        *_human_lines(result, jira=True),
    ]
    if not passed:
        lines.extend(
            [
                "",
                "*Exact error*",
                "{code}",
                str(result.get("traceback", result.get("error", ""))),
                "{code}",
            ]
        )
    return "\n".join(lines) + "\n"


def _pr_body(result: dict[str, object], *, passed: bool) -> str:
    status = "Passed" if passed else "Failed"
    screenshot_path = result.get("screenshot", FAILURE_SCREENSHOT_PATH)
    lines = [
        f"## {TICKET_KEY} {status}",
        "",
        "### Automation",
        f"- Removed `{BLOCKED_BOOTSTRAP_PATH}` from the intercepted recursive GitHub tree response while bootstrapping the deployed hosted app.",
        f"- Observed GitHub API traffic for {OBSERVATION_WINDOW_SECONDS} seconds to detect fallback tree replay or issue `main.md` hydration.",
        "- Verified the user-visible failure copy and Retry affordance on the live app.",
        "",
        "### Observed result",
        (
            "- Matched the expected result."
            if passed
            else "- Did not match the expected result."
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
        "### Human-style verification",
        *_human_lines(result, jira=False),
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
        f"# {TICKET_KEY} - Missing hosted index recovery regression",
        "",
        "## Steps to reproduce",
        "1. Open the deployed hosted TrackState app.",
        f"   - {'✅' if _step_status(result, 1) == 'passed' else '❌'} {_step_observation(result, 1)}",
        "2. Remove `DEMO/.trackstate/index/issues.json` from the hosted repository tree seen by the browser and continue startup.",
        f"   - {'✅' if _step_status(result, 2) == 'passed' else '❌'} {_step_observation(result, 2)}",
        "3. Watch GitHub API requests and observe the visible UI state.",
        f"   - {'✅' if _step_status(result, 3) == 'passed' else '❌'} {_step_observation(result, 3)}",
        "4. Click the visible `Retry` action if one is shown.",
        (
            f"   - {'✅' if _human_check_passed(result, 3) else '❌'} "
            f"{_human_observation(result, 3)}"
        ),
        "",
        "## Actual vs Expected",
        (
            "- Expected: the hosted runtime fails explicitly with a visible recoverable "
            "state, shows `Retry`, shows guidance to regenerate the tracker indexes, and "
            "does not silently read issue `main.md` files or replay recursive tree scans "
            "while the failure is visible."
        ),
        (
            "- Actual: "
            + str(
                result.get("error")
                or "the visible runtime behavior did not match the recoverable missing-index flow."
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
        f"- Removed bootstrap artifact from tree: `{BLOCKED_BOOTSTRAP_PATH}`",
        f"- Observation window: `{OBSERVATION_WINDOW_SECONDS}` seconds",
        "",
        "## Evidence",
        f"- Screenshot: `{result.get('screenshot', FAILURE_SCREENSHOT_PATH)}`",
    ]
    if isinstance(failure_surface, dict):
        lines.append(f"- Visible failure body text: `{failure_surface.get('body_text', '')}`")
    if isinstance(request_observation, dict):
        lines.extend(
            [
                f"- Recursive tree URLs: `{request_observation.get('tree_urls', [])}`",
                f"- Issue content URLs: `{request_observation.get('issue_content_urls', [])}`",
                f"- Other content URLs: `{request_observation.get('other_content_urls', [])}`",
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
        lines.append(f"{prefix} {check['check']} Observed: {check['observed']}")
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
    return True


def _human_observation(result: dict[str, object], index: int) -> str:
    checks = result.get("human_verification", [])
    if not isinstance(checks, list) or index - 1 >= len(checks):
        return str(result.get("error", "No human verification recorded."))
    check = checks[index - 1]
    if not isinstance(check, dict):
        return str(result.get("error", "No human verification recorded."))
    return str(check.get("observed", "No human verification recorded."))


if __name__ == "__main__":
    main()
