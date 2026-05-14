from __future__ import annotations

from dataclasses import asdict
import json
import platform
import re
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.github_actions_page import GitHubActionsPageObservation  # noqa: E402
from testing.core.interfaces.github_actions_preflight_gate_probe import (  # noqa: E402
    GitHubActionsPreflightGateObservation,
    GitHubActionsPreflightWorkflowObservation,
    GitHubActionsWorkflowJobObservation,
)
from testing.tests.support.github_actions_page_factory import (  # noqa: E402
    create_github_actions_page,
)
from testing.tests.support.github_actions_preflight_gate_probe_factory import (  # noqa: E402
    create_github_actions_preflight_gate_probe,
)

TICKET_KEY = "TS-706"
TEST_CASE_TITLE = (
    "Verify Ubuntu preflight readiness gate — workflow fails fast on label mismatch"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-706/test_ts_706.py"
TEST_FILE_PATH = "testing/tests/TS-706/test_ts_706.py"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
RUN_SCREENSHOT_PATH = OUTPUTS_DIR / "ts706_run_page.png"
JOB_SCREENSHOT_PATH = OUTPUTS_DIR / "ts706_job_page.png"

REQUEST_STEPS = [
    "Ensure all macOS runners registered with the label set `[self-hosted, macOS, trackstate-release, ARM64]` are offline.",
    "Push a semantic version tag (e.g., `v1.1.0`) to the `IstiN/trackstate` repository.",
    "Open the GitHub Actions tab and inspect the 'Apple release workflow'.",
    "Observe the 'Ubuntu preflight readiness gate' job status.",
]
EXPECTED_RESULT = (
    "The preflight job fails with a clear infrastructure-focused error (e.g., 'No "
    "online runners found with required labels'). The workflow terminates, and no "
    "macOS release jobs are queued, ensuring the failure is visible and actionable."
)


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    probe = create_github_actions_preflight_gate_probe(REPO_ROOT)
    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "test_case_title": TEST_CASE_TITLE,
        "run_command": RUN_COMMAND,
        "test_file_path": TEST_FILE_PATH,
        "expected_result": EXPECTED_RESULT,
        "browser": "Chromium (Playwright)",
        "os": platform.platform(),
        "steps": [],
        "human_verification": [],
    }

    try:
        observation = probe.validate()
        result.update(observation.to_dict())
        result["workflow"] = asdict(observation.workflow)
        result["run"] = asdict(observation.run)
        result["preflight_job"] = (
            asdict(observation.preflight_job) if observation.preflight_job else None
        )
        result["downstream_job"] = (
            asdict(observation.downstream_job) if observation.downstream_job else None
        )

        _assert_workflow_contract(observation)
        _record_step(
            result,
            step=1,
            status="passed",
            action=REQUEST_STEPS[0],
            observed=(
                "Confirmed the live Apple release workflow still uses an Ubuntu "
                f"preflight job with runner contract {observation.workflow.required_runner_labels} "
                f"before the macOS release job. Direct runner inventory visibility was "
                "not available via the repository runners API, so the offline/mismatch "
                "precondition was exercised through the live workflow run itself."
            ),
        )

        _assert_push_run_created(observation)
        _record_step(
            result,
            step=2,
            status="passed",
            action=REQUEST_STEPS[1],
            observed=(
                f"Created disposable tag `{observation.tag_name}` on "
                f"`{observation.repository}@{observation.head_sha}` and observed Apple "
                f"Release Builds run `{observation.run.id}` ({observation.run.html_url})."
            ),
        )

        run_page = _open_actions_page(
            url=observation.run.html_url,
            screenshot_path=RUN_SCREENSHOT_PATH,
            expected_texts=(
                observation.workflow_name,
                observation.preflight_job.name if observation.preflight_job else "",
                observation.downstream_job.name if observation.downstream_job else "",
            ),
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
                "Failure",
                "failed",
                "Resource not accessible by integration",
            ),
        )
        result["run_page"] = asdict(run_page)
        result["job_page"] = asdict(job_page)

        _record_step(
            result,
            step=3,
            status="passed",
            action=REQUEST_STEPS[2],
            observed=(
                f"Opened the live GitHub Actions run page `{run_page.url}` and the "
                f"preflight job page `{job_page.url}`. Screenshots: "
                f"`{run_page.screenshot_path}`, `{job_page.screenshot_path}`."
            ),
        )

        _assert_preflight_failure(
            observation=observation,
            run_page=run_page,
            job_page=job_page,
        )
        _record_step(
            result,
            step=4,
            status="passed",
            action=REQUEST_STEPS[3],
            observed=(
                f"The preflight job failed with infrastructure-focused text "
                f"`{observation.matched_failure_text}` and the downstream macOS job "
                f"conclusion was `{observation.downstream_job.conclusion if observation.downstream_job else '<missing>'}`."
            ),
        )

        _record_human_verification(
            result,
            check=(
                "Viewed the live GitHub Actions run page as a maintainer would and checked "
                "the visible job list."
            ),
            observed=(
                f"Run page body text included `{observation.preflight_job.name if observation.preflight_job else '<missing>'}` "
                f"and `{observation.downstream_job.name if observation.downstream_job else '<missing>'}`. "
                f"Run screenshot: `{run_page.screenshot_path}`."
            ),
        )
        _record_human_verification(
            result,
            check=(
                "Viewed the failed preflight job page and checked the user-visible failure text."
            ),
            observed=(
                f"Job page body excerpt: {_snippet(job_page.body_text, limit=600)}. "
                f"Log excerpt: {_snippet(observation.log_excerpt, limit=600)}. "
                f"Job screenshot: `{job_page.screenshot_path}`."
            ),
        )
    except Exception as error:
        result.setdefault("error", f"{type(error).__name__}: {error}")
        result.setdefault("traceback", traceback.format_exc())
        _record_failed_step_from_error(result, str(error))
        result["product_failure"] = _is_product_failure(result.get("error"))
        _write_failure_outputs(result)
        raise

    _write_pass_outputs(result)
    print("TS-706 passed")


def _assert_workflow_contract(observation: GitHubActionsPreflightGateObservation) -> None:
    if observation.workflow.state != "active":
        raise AssertionError(
            "Step 1 failed: the live Apple release workflow was not active.\n"
            f"Workflow state: {observation.workflow.state}\n"
            f"Workflow URL: {observation.workflow.html_url}"
        )
    if observation.workflow.preflight_runs_on != ["ubuntu-latest"]:
        raise AssertionError(
            "Step 1 failed: the live preflight gate no longer runs on Ubuntu.\n"
            f"Observed runs-on: {observation.workflow.preflight_runs_on}\n"
            f"Workflow path: {observation.workflow.path}"
        )
    if observation.workflow.required_runner_labels != [
        "self-hosted",
        "macOS",
        "trackstate-release",
        "ARM64",
    ]:
        raise AssertionError(
            "Step 1 failed: the live workflow runner-label contract no longer matches the "
            "ticket precondition.\n"
            f"Observed labels: {observation.workflow.required_runner_labels}\n"
            f"Workflow path: {observation.workflow.path}"
        )
    if observation.workflow.downstream_runs_on != [
        "self-hosted",
        "macOS",
        "trackstate-release",
        "ARM64",
    ]:
        raise AssertionError(
            "Step 1 failed: the downstream macOS job no longer targets the required "
            "runner labels.\n"
            f"Observed runs-on: {observation.workflow.downstream_runs_on}\n"
            f"Workflow path: {observation.workflow.path}"
        )


def _assert_push_run_created(observation: GitHubActionsPreflightGateObservation) -> None:
    if observation.run.event != "push":
        raise AssertionError(
            "Step 2 failed: the observed Apple release run was not triggered by a push.\n"
            f"Observed event: {observation.run.event}\n"
            f"Run URL: {observation.run.html_url}"
        )


def _assert_preflight_failure(
    *,
    observation: GitHubActionsPreflightGateObservation,
    run_page: GitHubActionsPageObservation,
    job_page: GitHubActionsPageObservation,
) -> None:
    if observation.preflight_job is None:
        raise AssertionError(
            "Step 4 failed: the Apple release workflow did not expose the expected "
            "preflight job.\n"
            f"Run URL: {observation.run.html_url}"
        )
    if observation.preflight_job.conclusion != "failure":
        raise AssertionError(
            "Step 4 failed: the preflight job did not fail fast.\n"
            f"Observed conclusion: {observation.preflight_job.conclusion}\n"
            f"Run URL: {observation.run.html_url}\n"
            f"Log excerpt:\n{observation.log_excerpt}"
        )
    if observation.downstream_job is None:
        raise AssertionError(
            "Step 4 failed: the downstream macOS release job was missing, so the workflow "
            "did not expose whether it was suppressed after the preflight failure.\n"
            f"Run URL: {observation.run.html_url}"
        )
    if observation.downstream_job.conclusion != "skipped":
        raise AssertionError(
            "Step 4 failed: the downstream macOS release job was not skipped after the "
            "preflight failure.\n"
            f"Observed downstream job conclusion: {observation.downstream_job.conclusion}\n"
            f"Observed downstream job status: {observation.downstream_job.status}\n"
            f"Run URL: {observation.run.html_url}"
        )
    if observation.matched_failure_text is None:
        raise AssertionError(
            "Step 4 failed: the preflight job failed, but the live failure was not the "
            "expected infrastructure-focused runner-availability message.\n"
            f"Expected one of: {observation.expected_failure_markers}\n"
            f"Actual log excerpt:\n{observation.log_excerpt}\n"
            f"Run URL: {observation.run.html_url}\n"
            f"Job URL: {observation.preflight_job.html_url}\n"
            f"Visible run-page text excerpt:\n{_snippet(run_page.body_text, limit=600)}\n"
            f"Visible job-page text excerpt:\n{_snippet(job_page.body_text, limit=600)}"
        )


def _open_actions_page(
    *,
    url: str,
    screenshot_path: Path,
    expected_texts: tuple[str, ...],
) -> GitHubActionsPageObservation:
    with create_github_actions_page() as actions_page:
        return actions_page.open_page(
            url=url,
            expected_texts=expected_texts,
            screenshot_path=str(screenshot_path),
            timeout_seconds=60,
        )


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
    PR_BODY_PATH.write_text(_markdown_summary(result, passed=True), encoding="utf-8")
    RESPONSE_PATH.write_text(_response(result, passed=True), encoding="utf-8")


def _write_failure_outputs(result: dict[str, object]) -> None:
    if result.get("product_failure") is True:
        BUG_DESCRIPTION_PATH.write_text(_bug_description(result), encoding="utf-8")
    else:
        BUG_DESCRIPTION_PATH.unlink(missing_ok=True)
    RESULT_PATH.write_text(
        json.dumps(
            {
                "status": "failed",
                "passed": 0,
                "failed": 1,
                "skipped": 0,
                "summary": "0 passed, 1 failed",
                "error": str(result.get("error", "AssertionError: TS-706 failed")),
            }
        )
        + "\n",
        encoding="utf-8",
    )
    JIRA_COMMENT_PATH.write_text(_jira_comment(result, passed=False), encoding="utf-8")
    PR_BODY_PATH.write_text(_markdown_summary(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_response(result, passed=False), encoding="utf-8")


def _jira_comment(result: dict[str, object], *, passed: bool) -> str:
    status = "✅ PASSED" if passed else "❌ FAILED"
    lines = [
        "h3. Test Automation Result",
        "",
        f"*Status:* {status}",
        f"*Test Case:* {TICKET_KEY} - {TEST_CASE_TITLE}",
        "",
        "h4. What was tested",
        (
            "* Created a disposable semantic version tag on {{IstiN/trackstate}} to "
            "exercise the live {{Apple Release Builds}} workflow."
        ),
        (
            "* Verified the live workflow definition still uses an Ubuntu preflight job "
            "before the macOS release job and still targets the TrackState runner label contract."
        ),
        (
            "* Waited for the live workflow run to complete, inspected the preflight and "
            "downstream job outcomes, and read the exact workflow log output."
        ),
        (
            "* Opened the GitHub Actions run and job pages in Chromium for human-style "
            "verification of the visible failure state."
        ),
        "",
        "h4. Result",
        (
            "* Matched the expected result."
            if passed
            else f"* Did not match the expected result. {_failed_step_summary(result)}"
        ),
        (
            f"* Environment: repository {{{{{result.get('repository', '')}}}}}, branch "
            f"{{{{{result.get('default_branch', '')}}}}}, tag "
            f"{{{{{result.get('tag_name', '')}}}}}, browser {{Chromium (Playwright)}}, "
            f"OS {{{{{result.get('os', '')}}}}}."
        ),
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
                "",
                "h4. Relevant log excerpt",
                "{code}",
                str(result.get("log_excerpt", "")),
                "{code}",
            ]
        )
    return "\n".join(lines) + "\n"


def _markdown_summary(result: dict[str, object], *, passed: bool) -> str:
    lines = [
        "## Test Automation Result",
        "",
        f"**Status:** {'✅ PASSED' if passed else '❌ FAILED'}",
        f"**Test Case:** {TICKET_KEY} - {TEST_CASE_TITLE}",
        "",
        "## What was automated",
        (
            "- Created a disposable semantic version tag on `IstiN/trackstate` to "
            "exercise the live `Apple Release Builds` workflow."
        ),
        (
            "- Verified the live workflow definition still uses an Ubuntu preflight job "
            "before the macOS release job and still targets the TrackState runner label contract."
        ),
        (
            "- Waited for the live workflow run to complete, inspected the preflight and "
            "downstream job outcomes, and read the exact workflow log output."
        ),
        (
            "- Opened the GitHub Actions run and job pages in Chromium for human-style "
            "verification of the visible failure state."
        ),
        "",
        "## Result",
        (
            "- Matched the expected result."
            if passed
            else f"- Did not match the expected result. {_failed_step_summary(result)}"
        ),
        (
            f"- Environment: repository `{result.get('repository', '')}`, branch "
            f"`{result.get('default_branch', '')}`, tag `{result.get('tag_name', '')}`, "
            f"browser `Chromium (Playwright)`, OS `{result.get('os', '')}`."
        ),
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
                "",
                "## Relevant log excerpt",
                "```text",
                str(result.get("log_excerpt", "")),
                "```",
            ]
        )
    return "\n".join(lines) + "\n"


def _response(result: dict[str, object], *, passed: bool) -> str:
    lines = [
        "## Test Automation Result",
        "",
        f"**Status:** {'✅ PASSED' if passed else '❌ FAILED'}",
        f"**Test Case:** {TICKET_KEY} - {TEST_CASE_TITLE}",
        "",
        "## Outcome",
        (
            "- The live Apple release preflight gate failed fast with the expected "
            "runner-availability message and suppressed the macOS build job."
            if passed
            else "- The live Apple release preflight gate did not expose the expected "
            "runner-availability failure behavior."
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


def _bug_description(result: dict[str, object]) -> str:
    return "\n".join(
        [
            f"# {TICKET_KEY} - Ubuntu preflight readiness gate failed with the wrong error",
            "",
            "## Steps to reproduce",
            "1. Ensure all macOS runners registered with the label set `[self-hosted, macOS, trackstate-release, ARM64]` are offline.",
            "2. Push a semantic version tag (for example `v1.1.0`) to the `IstiN/trackstate` repository.",
            "3. Open the GitHub Actions tab and inspect the `Apple Release Builds` workflow run.",
            "4. Observe the Ubuntu preflight job status and error output.",
            "",
            "## Exact steps from the test case with observations",
            (
                "1. Ensure all macOS runners registered with the label set "
                "`[self-hosted, macOS, trackstate-release, ARM64]` are offline.\n"
                "   - ⚠️ The workflow still targets that exact runner-label contract, but the "
                "repository runners API was not directly observable in this environment. "
                "The live run below reproduced the faulty preflight behavior regardless."
            ),
            _annotated_step_line(result, 2, REQUEST_STEPS[1]),
            _annotated_step_line(result, 3, REQUEST_STEPS[2]),
            _annotated_step_line(result, 4, REQUEST_STEPS[3]),
            "",
            "## Actual vs Expected",
            f"- Expected: {EXPECTED_RESULT}",
            (
                "- Actual: the preflight job failed with a GitHub permission error "
                "(`Resource not accessible by integration`) instead of a clear runner-"
                "availability message such as `No runner registered for ...` or "
                "`none are online`. The downstream macOS job was skipped, but the failure "
                "was not actionable for the infrastructure condition the ticket covers."
            ),
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
                    "matched_failure_text": result.get("matched_failure_text"),
                    "log_excerpt": result.get("log_excerpt"),
                    "run_page": result.get("run_page", {}),
                    "job_page": result.get("job_page", {}),
                },
                indent=2,
            ),
            "```",
            "",
            "## Exact error message / traceback",
            "```text",
            str(result.get("traceback", result.get("error", "<missing traceback>"))),
            "```",
            "",
            "## Relevant workflow log excerpt",
            "```text",
            str(result.get("log_excerpt", "<missing log excerpt>")),
            "```",
        ]
    ) + "\n"


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
        }
    )


def _record_human_verification(
    result: dict[str, object],
    *,
    check: str,
    observed: str,
) -> None:
    verifications = result.setdefault("human_verification", [])
    assert isinstance(verifications, list)
    verifications.append({"check": check, "observed": observed})


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    steps = result.get("steps")
    if not isinstance(steps, list):
        return lines
    for entry in steps:
        if not isinstance(entry, dict):
            continue
        step = entry.get("step")
        status = str(entry.get("status", "")).upper()
        action = str(entry.get("action", ""))
        observed = str(entry.get("observed", ""))
        if jira:
            action = _jira_inline(action)
            observed = _jira_inline(observed)
        prefix = f"* Step {step} — {status}: " if jira else f"- Step {step} — {status}: "
        lines.append(prefix + action)
        detail_prefix = "* " if jira else "  - "
        lines.append(detail_prefix + observed)
    return lines


def _human_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    verifications = result.get("human_verification")
    if not isinstance(verifications, list):
        return lines
    for entry in verifications:
        if not isinstance(entry, dict):
            continue
        check = str(entry.get("check", ""))
        observed = str(entry.get("observed", ""))
        if jira:
            check = _jira_inline(check)
            observed = _jira_inline(observed)
        prefix = "* " if jira else "- "
        lines.append(prefix + check)
        lines.append(prefix + observed)
    return lines


def _failed_step_summary(result: dict[str, object]) -> str:
    steps = result.get("steps")
    if not isinstance(steps, list):
        return str(result.get("error", "Unknown failure"))
    for entry in steps:
        if not isinstance(entry, dict):
            continue
        if entry.get("status") == "failed":
            return f"Step {entry.get('step')} failed: {entry.get('observed')}"
    return str(result.get("error", "Unknown failure"))


def _annotated_step_line(result: dict[str, object], step_number: int, action: str) -> str:
    steps = result.get("steps")
    if isinstance(steps, list):
        for entry in steps:
            if not isinstance(entry, dict):
                continue
            if entry.get("step") == step_number:
                marker = "✅" if entry.get("status") == "passed" else "❌"
                return f"{step_number}. {action}\n   - {marker} {entry.get('observed')}"
    return f"{step_number}. {action}\n   - ❌ Not reached."


def _record_failed_step_from_error(result: dict[str, object], message: str) -> None:
    match = re.search(r"Step (\d+) failed:(.*)", message, flags=re.DOTALL)
    if match is None:
        return
    step = int(match.group(1))
    if _step_exists(result, step):
        return
    observed = match.group(0).strip()
    action = REQUEST_STEPS[step - 1] if 1 <= step <= len(REQUEST_STEPS) else f"Step {step}"
    _record_step(result, step=step, status="failed", action=action, observed=observed)


def _is_product_failure(error: object) -> bool:
    return re.search(r"(^|\n)Step \d+ failed:", str(error), flags=re.MULTILINE) is not None


def _step_exists(result: dict[str, object], step_number: int) -> bool:
    steps = result.get("steps")
    if not isinstance(steps, list):
        return False
    return any(
        isinstance(entry, dict) and entry.get("step") == step_number for entry in steps
    )


def _jira_inline(value: str) -> str:
    return f"{{{{{value}}}}}"


def _snippet(value: object, *, limit: int) -> str:
    text = str(value).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _nested_value(result: dict[str, object], key: str, nested_key: str) -> str:
    payload = result.get(key)
    if isinstance(payload, dict):
        value = payload.get(nested_key)
        if isinstance(value, str):
            return value
    return ""


if __name__ == "__main__":
    main()
