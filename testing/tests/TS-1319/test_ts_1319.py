from __future__ import annotations

from dataclasses import asdict
import json
from datetime import datetime, timezone
import platform
import sys
import traceback
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.github_actions_page import (  # noqa: E402
    GitHubActionsPageObservation,
)
from testing.components.services.github_actions_preflight_gate_probe import (  # noqa: E402
    GitHubActionsPreflightGatePreconditionError,
)
from testing.core.config.github_actions_preflight_gate_config import (  # noqa: E402
    GitHubActionsPreflightGateConfig,
)
from testing.core.interfaces.github_actions_preflight_gate_probe import (  # noqa: E402
    GitHubActionsPreflightGateObservation,
)
from testing.tests.support.github_actions_page_factory import (  # noqa: E402
    create_github_actions_page,
)
from testing.tests.support.github_actions_preflight_gate_probe_factory import (  # noqa: E402
    create_github_actions_preflight_gate_probe,
)

TICKET_KEY = "TS-1319"
TEST_CASE_TITLE = "Infrastructure readiness gate hangs — job fails after 5-minute timeout"
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-1319/test_ts_1319.py"
CONFIG_PATH = REPO_ROOT / "testing/tests/TS-1319/config.yaml"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
RUN_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1319_run.png"
JOB_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1319_job.png"

REQUEST_STEPS = [
    "Push a semantic version tag to `IstiN/trackstate` to trigger the live `Apple Release Builds` workflow.",
    "Monitor the `Ubuntu preflight readiness gate` job until the workflow run completes.",
    "Open the GitHub Actions run and job pages and confirm the gate fails after about five minutes instead of hanging.",
]

EXPECTED_RESULT = (
    "The live preflight gate run completes with a failure/timeout result after "
    "roughly five minutes, the downstream macOS build job does not proceed, and "
    "the workflow does not remain stuck indefinitely."
)

MIN_EXPECTED_DURATION_SECONDS = 295
MAX_EXPECTED_DURATION_SECONDS = 360


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    RUN_SCREENSHOT_PATH.unlink(missing_ok=True)
    JOB_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = GitHubActionsPreflightGateConfig.from_file(CONFIG_PATH)
    probe = create_github_actions_preflight_gate_probe(
        REPO_ROOT,
        config_path=CONFIG_PATH,
    )
    result: dict[str, Any] = {
        "ticket": TICKET_KEY,
        "test_case_title": TEST_CASE_TITLE,
        "run_command": RUN_COMMAND,
        "expected_result": EXPECTED_RESULT,
        "repository": config.repository,
        "default_branch": config.default_branch,
        "workflow_name": config.workflow_name,
        "workflow_path": config.workflow_path,
        "preflight_job_name": config.preflight_job_name,
        "downstream_job_name": config.downstream_job_name,
        "browser": "Chromium (Playwright)",
        "os": platform.platform(),
        "steps": [],
        "human_verification": [],
    }

    try:
        observation = probe.validate()
        result.update(_observation_payload(observation))
        run_page = _open_actions_page(
            url=observation.run.html_url,
            screenshot_path=RUN_SCREENSHOT_PATH,
            expected_texts=(
                observation.workflow_name,
                observation.preflight_job.name if observation.preflight_job else "",
                observation.downstream_job.name if observation.downstream_job else "",
                "timed out",
                "failure",
                "failed",
            ),
            timeout_seconds=config.ui_timeout_seconds,
        )
        job_page = _open_actions_page(
            url=(
                observation.preflight_job.html_url
                if observation.preflight_job is not None
                else observation.run.html_url
            ),
            screenshot_path=JOB_SCREENSHOT_PATH,
            expected_texts=(
                observation.preflight_job.name if observation.preflight_job else "",
                "timed out",
                "Timed out",
                "failure",
                "failed",
                "timeout",
            ),
            timeout_seconds=config.ui_timeout_seconds,
        )
        result["run_page"] = asdict(run_page)
        result["job_page"] = asdict(job_page)

        _record_step(
            result,
            1,
            "passed",
            REQUEST_STEPS[0],
            (
                f"Created a disposable semantic version tag `{observation.tag_name}` and "
                f"observed workflow run `{observation.run.id}` at {observation.run.html_url}."
            ),
        )

        _assert_timeout_contract(observation)
        _record_step(
            result,
            2,
            "passed",
            REQUEST_STEPS[1],
            (
                f"The preflight job `{observation.preflight_job.name if observation.preflight_job else '<missing>'}` "
                f"completed with conclusion `{_job_conclusion(observation.preflight_job)}` after "
                f"{result['preflight_job_duration_seconds']} seconds."
            ),
        )
        _record_step(
            result,
            3,
            "passed",
            REQUEST_STEPS[2],
            (
                f"Opened the live GitHub Actions run page `{run_page.url}` and the job page "
                f"`{job_page.url}`. Screenshots: `{run_page.screenshot_path}`, "
                f"`{job_page.screenshot_path}`."
            ),
        )
        _record_human_verification(
            result,
            "Viewed the workflow run page like a maintainer would.",
            (
                f"Run page body text included `{observation.workflow_name}` and the job names "
                f"`{observation.preflight_job.name if observation.preflight_job else '<missing>'}` "
                f"/ `{observation.downstream_job.name if observation.downstream_job else '<missing>'}`."
            ),
        )
        _record_human_verification(
            result,
            "Viewed the failed preflight job page and checked the visible status text.",
            (
                f"Job page body excerpt: {_snippet(job_page.body_text, 700)}. "
                f"Observed job conclusion: `{_job_conclusion(observation.preflight_job)}`."
            ),
        )
    except GitHubActionsPreflightGatePreconditionError as error:
        _merge_probe_error_context(result, error)
        result.setdefault("error", f"{type(error).__name__}: {error}")
        result.setdefault("traceback", traceback.format_exc())
        result["precondition_failure"] = True
        result["product_failure"] = False
        if not result.get("steps"):
            _record_step(
                result,
                1,
                "blocked",
                REQUEST_STEPS[0],
                str(error),
            )
        _write_blocked_outputs(result)
        print("TS-1319 blocked")
        return
    except Exception as error:
        _merge_probe_error_context(result, error)
        if (
            isinstance(error, AssertionError)
            and result.get("run_page")
            and result.get("job_page")
        ):
            _record_step(
                result,
                2,
                "failed",
                REQUEST_STEPS[1],
                (
                    f"The preflight job finished in {result.get('preflight_job_duration_seconds')} "
                    f"seconds with conclusion `{_nested_value(result, 'preflight_job', 'conclusion')}` "
                    f"instead of holding for roughly five minutes."
                ),
            )
            _record_human_verification(
                result,
                "Viewed the live GitHub Actions run and job pages after the workflow finished.",
                (
                    f"Run page URL: `{_nested_value(result, 'run', 'html_url')}`. "
                    f"Job page URL: `{_nested_value(result, 'preflight_job', 'html_url')}`. "
                    f"Observed duration: {result.get('preflight_job_duration_seconds')} seconds."
                ),
            )
        result.setdefault("error", f"{type(error).__name__}: {error}")
        result.setdefault("traceback", traceback.format_exc())
        result.setdefault("product_failure", isinstance(error, AssertionError))
        _write_failure_outputs(result)
        raise

    _write_pass_outputs(result)
    print("TS-1319 passed")


def _assert_timeout_contract(observation: GitHubActionsPreflightGateObservation) -> None:
    failures: list[str] = []
    if observation.run.event != "push":
        failures.append(
            "Step 1 failed: the workflow run was not triggered by a tag push.\n"
            f"Observed event: {observation.run.event}\n"
            f"Run URL: {observation.run.html_url}"
        )
    if observation.preflight_job is None:
        failures.append(
            "Step 2 failed: the preflight gate job was missing from the completed run.\n"
            f"Run URL: {observation.run.html_url}"
        )
        raise AssertionError("\n\n".join(failures))

    if observation.preflight_job.completed_at is None or observation.preflight_job.started_at is None:
        failures.append(
            "Step 2 failed: the preflight job did not expose started_at/completed_at timestamps.\n"
            f"Job URL: {observation.preflight_job.html_url}"
        )
    if observation.preflight_job.conclusion not in {"failure", "timed_out"}:
        failures.append(
            "Step 2 failed: the preflight job did not finish with a failure or timeout result.\n"
            f"Observed conclusion: {observation.preflight_job.conclusion}\n"
            f"Job URL: {observation.preflight_job.html_url}"
        )
    if observation.downstream_job is None:
        failures.append(
            "Step 2 failed: the downstream build job was missing from the workflow run.\n"
            f"Run URL: {observation.run.html_url}"
        )
    elif observation.downstream_job.conclusion != "skipped":
        failures.append(
            "Step 2 failed: the downstream build job was not skipped after the preflight gate failed.\n"
            f"Observed conclusion: {observation.downstream_job.conclusion}\n"
            f"Job URL: {observation.downstream_job.html_url}"
        )

    duration_seconds = _duration_seconds(
        observation.preflight_job.started_at if observation.preflight_job else None,
        observation.preflight_job.completed_at if observation.preflight_job else None,
    )
    if duration_seconds is None:
        failures.append(
            "Step 2 failed: could not calculate the preflight job duration from GitHub Actions timestamps."
        )
    else:
        if duration_seconds < MIN_EXPECTED_DURATION_SECONDS:
            failures.append(
                "Step 2 failed: the preflight gate finished too quickly, which means the "
                "5-minute timeout contract was not observed.\n"
                f"Observed duration: {duration_seconds} seconds\n"
                f"Expected minimum: {MIN_EXPECTED_DURATION_SECONDS} seconds\n"
                f"Job URL: {observation.preflight_job.html_url if observation.preflight_job else '<missing>'}"
            )
        if duration_seconds > MAX_EXPECTED_DURATION_SECONDS:
            failures.append(
                "Step 2 failed: the preflight gate took longer than the expected five-minute timeout window.\n"
                f"Observed duration: {duration_seconds} seconds\n"
                f"Expected maximum: {MAX_EXPECTED_DURATION_SECONDS} seconds\n"
                f"Job URL: {observation.preflight_job.html_url if observation.preflight_job else '<missing>'}"
            )

    if failures:
        raise AssertionError("\n\n".join(failures))


def _observation_payload(
    observation: GitHubActionsPreflightGateObservation,
) -> dict[str, Any]:
    payload = {
        "tag_name": observation.tag_name,
        "head_sha": observation.head_sha,
        "workflow": asdict(observation.workflow),
        "run": asdict(observation.run),
        "preflight_job": asdict(observation.preflight_job) if observation.preflight_job else None,
        "downstream_job": asdict(observation.downstream_job) if observation.downstream_job else None,
        "matched_failure_text": observation.matched_failure_text,
        "log_excerpt": observation.log_excerpt,
        "log_text": observation.log_text,
    }
    duration_seconds = _duration_seconds(
        observation.preflight_job.started_at if observation.preflight_job else None,
        observation.preflight_job.completed_at if observation.preflight_job else None,
    )
    payload["preflight_job_duration_seconds"] = duration_seconds
    return payload


def _open_actions_page(
    *,
    url: str,
    screenshot_path: Path,
    expected_texts: tuple[str, ...],
    timeout_seconds: int,
) -> GitHubActionsPageObservation:
    with create_github_actions_page() as actions_page:
        return actions_page.open_page(
            url=url,
            expected_texts=expected_texts,
            screenshot_path=str(screenshot_path),
            timeout_seconds=timeout_seconds,
        )


def _write_pass_outputs(result: dict[str, Any]) -> None:
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
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    JIRA_COMMENT_PATH.write_text(_jira_comment(result, passed=True), encoding="utf-8")
    PR_BODY_PATH.write_text(_markdown_summary(result, passed=True), encoding="utf-8")
    RESPONSE_PATH.write_text(_response(result, passed=True), encoding="utf-8")


def _write_failure_outputs(result: dict[str, Any]) -> None:
    if result.get("product_failure") is True:
        BUG_DESCRIPTION_PATH.write_text(_bug_description(result), encoding="utf-8")
    else:
        BUG_DESCRIPTION_PATH.unlink(missing_ok=True)
    RESULT_PATH.write_text(
        json.dumps(_test_automation_result_payload(result), indent=2) + "\n",
        encoding="utf-8",
    )
    JIRA_COMMENT_PATH.write_text(_jira_comment(result, passed=False), encoding="utf-8")
    PR_BODY_PATH.write_text(_markdown_summary(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_response(result, passed=False), encoding="utf-8")


def _write_blocked_outputs(result: dict[str, Any]) -> None:
    BUG_DESCRIPTION_PATH.unlink(missing_ok=True)
    RESULT_PATH.write_text(
        json.dumps(_test_automation_result_payload(result), indent=2) + "\n",
        encoding="utf-8",
    )
    JIRA_COMMENT_PATH.write_text(_jira_comment(result, passed=False), encoding="utf-8")
    PR_BODY_PATH.write_text(_markdown_summary(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_response(result, passed=False), encoding="utf-8")


def _test_automation_result_payload(result: dict[str, Any]) -> dict[str, Any]:
    error = str(result.get("error", "AssertionError: test failed"))
    if not error.startswith(("AssertionError:", "RuntimeError:", "ValueError:", "TypeError:")):
        error = f"AssertionError: {error}"
    if result.get("precondition_failure") is True:
        return {
            "status": "blocked",
            "passed": 0,
            "failed": 0,
            "skipped": 1,
            "summary": "0 passed, 0 failed, 1 blocked",
            "error": error,
        }
    return {
        "status": "failed",
        "passed": 0,
        "failed": 1,
        "skipped": 0,
        "summary": "0 passed, 1 failed",
        "error": error,
    }


def _jira_comment(result: dict[str, Any], *, passed: bool) -> str:
    status = _status_text(result, passed=passed)
    lines = [
        "h3. Test Automation Result",
        "",
        f"*Status:* {status}",
        f"*Test Case:* {TICKET_KEY} - {TEST_CASE_TITLE}",
        "",
        "h4. What was automated",
        (
            "* Pushed a disposable semantic version tag to {{IstiN/trackstate}} and "
            "waited for the live {{Apple Release Builds}} workflow."
        ),
        (
            "* Verified the Ubuntu preflight readiness gate completed around the five-minute "
            "mark instead of hanging indefinitely."
        ),
        (
            "* Opened the GitHub Actions run page and job page in Chromium for "
            "human-style verification."
        ),
        "",
        "h4. Result",
        (
            "* Matched the expected result."
            if passed
            else (
                f"* Blocked before full verification. {_failed_step_summary(result)}"
                if result.get("precondition_failure") is True
                else f"* Did not match the expected result. {_failed_step_summary(result)}"
            )
        ),
        f"* Environment: repository {{{{{result.get('repository', '')}}}}}, branch {{{{{result.get('default_branch', '')}}}}}, browser {{Chromium (Playwright)}}, OS {{{{{result.get('os', '')}}}}}.",
        "",
        "h4. Step results",
        *_step_lines(result, jira=True),
        "",
        "h4. Human-style verification",
        *_human_lines(result, jira=True),
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


def _markdown_summary(result: dict[str, Any], *, passed: bool) -> str:
    status = _status_text(result, passed=passed)
    lines = [
        "## Test Automation Result",
        "",
        f"**Status:** {status}",
        f"**Test Case:** {TICKET_KEY} - {TEST_CASE_TITLE}",
        "",
        "## What was automated",
        "- Pushed a disposable semantic version tag to `IstiN/trackstate` and waited for the live `Apple Release Builds` workflow.",
        "- Verified the Ubuntu preflight readiness gate completed around the five-minute mark instead of hanging indefinitely.",
        "- Opened the GitHub Actions run page and job page in Chromium for human-style verification.",
        "",
        "## Result",
        (
            "- Matched the expected result."
            if passed
            else (
                f"- Blocked before full verification. {_failed_step_summary(result)}"
                if result.get("precondition_failure") is True
                else f"- Did not match the expected result. {_failed_step_summary(result)}"
            )
        ),
        f"- Environment: repository `{result.get('repository', '')}`, branch `{result.get('default_branch', '')}`, browser `Chromium (Playwright)`, OS `{result.get('os', '')}`.",
        "",
        "## Step results",
        *_step_lines(result, jira=False),
        "",
        "## Human-style verification",
        *_human_lines(result, jira=False),
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
                "## Exact error",
                "```text",
                str(result.get("traceback", result.get("error", ""))),
                "```",
            ]
        )
    return "\n".join(lines) + "\n"


def _response(result: dict[str, Any], *, passed: bool) -> str:
    status = _status_text(result, passed=passed)
    lines = [
        "## Test Automation Result",
        "",
        f"**Status:** {status}",
        f"**Test Case:** {TICKET_KEY} - {TEST_CASE_TITLE}",
        "",
        "## Outcome",
        (
            "- The live Apple Release Builds workflow failed after about five minutes and did not hang."
            if passed
            else (
                "- Blocked: the required no-runner timeout precondition could not be reproduced."
                if result.get("precondition_failure") is True
                else "- The live workflow did not meet the five-minute timeout expectation."
            )
        ),
        "",
        "## Step results",
        *_step_lines(result, jira=False),
        "",
        "## Human-style verification",
        *_human_lines(result, jira=False),
    ]
    if not passed:
        lines.extend(
            [
                "",
                "## Exact error",
                "```text",
                str(result.get("traceback", result.get("error", ""))),
                "```",
            ]
        )
    return "\n".join(lines) + "\n"


def _bug_description(result: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"# {TICKET_KEY} - Infrastructure readiness gate did not fail after five minutes",
            "",
            "## Steps to reproduce",
            "1. Push a semantic version tag to `IstiN/trackstate` to trigger the live `Apple Release Builds` workflow.",
            "2. Monitor the `Ubuntu preflight readiness gate` job until the workflow run completes.",
            "3. Open the GitHub Actions run and job pages and confirm whether the gate stopped after roughly five minutes.",
            "",
            "## Exact steps from the test case with observations",
            _annotated_step_line(result, 1, REQUEST_STEPS[0]),
            _annotated_step_line(result, 2, REQUEST_STEPS[1]),
            _annotated_step_line(result, 3, REQUEST_STEPS[2]),
            "",
            "## Actual vs Expected",
            f"- Expected: {EXPECTED_RESULT}",
            f"- Actual: {_actual_result(result)}",
            "",
            "## Environment",
            f"- Repository: `{result.get('repository', '')}`",
            f"- Branch: `{result.get('default_branch', '')}`",
            f"- Disposable tag used: `{result.get('tag_name', '')}`",
            f"- Head SHA: `{result.get('head_sha', '')}`",
            f"- Workflow run URL: `{_nested_value(result, 'run', 'html_url')}`",
            f"- Preflight job URL: `{_nested_value(result, 'preflight_job', 'html_url')}`",
            f"- Browser: `{result.get('browser', '')}`",
            f"- OS: `{result.get('os', '')}`",
            f"- Run page screenshot: `{_nested_value(result, 'run_page', 'screenshot_path')}`",
            f"- Job page screenshot: `{_nested_value(result, 'job_page', 'screenshot_path')}`",
            "",
            "## Live observations",
            "```json",
            json.dumps(
                {
                    "workflow": result.get("workflow", {}),
                    "run": result.get("run", {}),
                    "preflight_job": result.get("preflight_job", {}),
                    "downstream_job": result.get("downstream_job", {}),
                    "run_page": result.get("run_page", {}),
                    "job_page": result.get("job_page", {}),
                    "duration_seconds": result.get("preflight_job_duration_seconds"),
                },
                indent=2,
            ),
            "```",
            "",
            "## Error",
            "```text",
            str(result.get("traceback", result.get("error", ""))),
            "```",
        ]
    ) + "\n"


def _actual_result(result: dict[str, Any]) -> str:
    duration = result.get("preflight_job_duration_seconds")
    conclusion = _nested_value(result, "preflight_job", "conclusion") or "<missing>"
    downstream = _nested_value(result, "downstream_job", "conclusion") or "<missing>"
    return (
        f"the preflight job concluded as `{conclusion}` after `{duration}` seconds and "
        f"the downstream job concluded as `{downstream}` instead of the gate hanging and "
        "failing after about five minutes."
    )


def _failed_step_summary(result: dict[str, Any]) -> str:
    if result.get("precondition_failure") is True:
        for step in reversed(result.get("steps", [])):
            if step.get("status") == "blocked":
                return str(step.get("observed", ""))
    for step in reversed(result.get("steps", [])):
        if step.get("status") == "failed":
            return str(step.get("observed", ""))
    return "The live workflow did not match the expected five-minute timeout behavior."


def _status_text(result: dict[str, Any], *, passed: bool) -> str:
    if passed:
        return "PASSED"
    if result.get("precondition_failure") is True:
        return "BLOCKED"
    return "FAILED"


def _step_lines(result: dict[str, Any], *, jira: bool) -> list[str]:
    prefix = "* " if jira else "- "
    lines: list[str] = []
    for step in result.get("steps", []):
        status = str(step.get("status", "")).upper()
        action = str(step.get("action", ""))
        observed = str(step.get("observed", ""))
        lines.append(f"{prefix}{status}: {action}")
        lines.append(f"{prefix}  {observed}")
    return lines


def _human_lines(result: dict[str, Any], *, jira: bool) -> list[str]:
    prefix = "* " if jira else "- "
    lines: list[str] = []
    for item in result.get("human_verification", []):
        lines.append(f"{prefix}{item.get('check', '')}")
        lines.append(f"{prefix}  {item.get('observed', '')}")
    return lines


def _record_step(
    result: dict[str, Any],
    step: int,
    status: str,
    action: str,
    observed: str,
) -> None:
    result.setdefault("steps", []).append(
        {
            "step": step,
            "status": status,
            "action": action,
            "observed": observed,
        }
    )


def _record_human_verification(
    result: dict[str, Any],
    check: str,
    observed: str,
) -> None:
    result.setdefault("human_verification", []).append(
        {
            "check": check,
            "observed": observed,
        }
    )


def _merge_probe_error_context(result: dict[str, Any], error: Exception) -> None:
    partial_result = getattr(error, "partial_result", None)
    if isinstance(partial_result, dict):
        result.update(partial_result)


def _duration_seconds(started_at: str | None, completed_at: str | None) -> int | None:
    if not started_at or not completed_at:
        return None
    try:
        started = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        completed = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
    except ValueError:
        return None
    return int((completed - started).total_seconds())


def _job_conclusion(job: Any) -> str:
    if job is None:
        return "<missing>"
    conclusion = getattr(job, "conclusion", None)
    return str(conclusion) if conclusion else "<missing>"


def _nested_value(result: dict[str, Any], first_key: str, second_key: str) -> str:
    payload = result.get(first_key)
    if not isinstance(payload, dict):
        return ""
    value = payload.get(second_key)
    return value if isinstance(value, str) else ""


def _snippet(text: str, limit: int = 600) -> str:
    text = text or ""
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def _annotated_step_line(result: dict[str, Any], step: int, requested_step: str) -> str:
    for entry in result.get("steps", []):
        if entry.get("step") == step:
            status = "✅" if entry.get("status") == "passed" else "❌"
            return (
                f"{step}. {requested_step}\n"
                f"   - {status} {entry.get('observed', '')}"
            )
    return f"{step}. {requested_step}\n   - ⚠️ No recorded observation."


if __name__ == "__main__":
    main()
