from __future__ import annotations

import json
import platform
import re
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.core.config.github_accessibility_pull_request_gate_config import (  # noqa: E402
    GitHubAccessibilityPullRequestGateConfig,
)
from testing.core.interfaces.github_accessibility_pull_request_gate_probe import (  # noqa: E402
    GitHubAccessibilityPullRequestGateObservation,
)
from testing.core.interfaces.github_workflow_run_log_reader import (  # noqa: E402
    GitHubWorkflowRunLogReader,
)
from testing.tests.support.github_accessibility_wrapper_failure_probe_factory import (  # noqa: E402
    create_github_accessibility_wrapper_failure_probe,
    create_github_accessibility_wrapper_failure_run_log_reader,
)

TICKET_KEY = "TS-969"
TEST_CASE_TITLE = (
    "CI contract validation failure - standardized wrapper ensures failure propagation"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-969/test_ts_969.py"
TEST_FILE_PATH = "testing/tests/TS-969/test_ts_969.py"
CONFIG_PATH = REPO_ROOT / "testing/tests/TS-969/config.yaml"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
REVIEW_REPLIES_PATH = OUTPUTS_DIR / "review_replies.json"
DISCUSSIONS_RAW_PATH = REPO_ROOT / "input" / TICKET_KEY / "pr_discussions_raw.json"

REQUEST_STEPS = [
    "Invoke the standardized CI test wrapper to execute a contract validation script that is designed to fail.",
    "Inspect the execution logs to ensure the error was captured.",
    "Verify the final exit code of the wrapper process.",
]
EXPECTED_RESULT = (
    "The wrapper identifies the validation failure and returns exit code 1, "
    "preventing the CI step from allowing a contract violation to pass unnoticed."
)
EXPECTED_FAILURE_CONCLUSION = "failure"
WRAPPER_STEP_PATTERN = re.compile(
    r"Run axe-core accessibility checks",
    re.IGNORECASE,
)
FAILURE_MESSAGE_PATTERNS = (
    re.compile(r"TS-969 simulated contract validation failure", re.IGNORECASE),
    re.compile(
        r"standardized wrapper must propagate exit code 1",
        re.IGNORECASE,
    ),
)
EXIT_CODE_PATTERN = re.compile(
    r"process completed with exit code (?P<code>\d+)",
    re.IGNORECASE,
)


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    config = GitHubAccessibilityPullRequestGateConfig.from_file(CONFIG_PATH)
    probe = create_github_accessibility_wrapper_failure_probe(
        REPO_ROOT,
        config_path=CONFIG_PATH,
    )
    log_reader = create_github_accessibility_wrapper_failure_run_log_reader(REPO_ROOT)
    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "test_case_title": TEST_CASE_TITLE,
        "run_command": RUN_COMMAND,
        "test_file_path": TEST_FILE_PATH,
        "expected_result": EXPECTED_RESULT,
        "repository": config.repository,
        "default_branch": config.base_branch,
        "target_workflow_name": config.target_workflow_name,
        "target_workflow_path": config.target_workflow_path,
        "browser": "GitHub CLI",
        "os": platform.platform(),
        "steps": [],
        "human_verification": [],
    }

    try:
        observation = probe.validate()
        result.update(observation.to_dict())

        full_run_log_text, full_run_log_error = _read_full_run_log(
            observation,
            log_reader=log_reader,
        )
        wrapper_step_output = _extract_step_output(full_run_log_text, WRAPPER_STEP_PATTERN)
        result["full_run_log_error"] = full_run_log_error
        result["wrapper_step_output"] = wrapper_step_output
        result["wrapper_failure_message"] = _extract_failure_message(wrapper_step_output)
        result["wrapper_exit_code"] = _extract_exit_code(wrapper_step_output)
        result["full_run_log_excerpt"] = _extract_relevant_full_log_excerpt(
            full_run_log_text,
            observation=observation,
        )

        failures: list[str] = []
        _evaluate_wrapper_invocation(result, observation, failures)
        _evaluate_error_captured(
            result,
            observation,
            failures,
            full_run_log_text=full_run_log_text,
            full_run_log_error=full_run_log_error,
        )
        _evaluate_wrapper_exit_code(
            result,
            observation,
            failures,
            full_run_log_text=full_run_log_text,
            wrapper_step_output=wrapper_step_output,
        )
        _record_live_user_verification(
            result,
            observation,
            full_run_log_text=full_run_log_text,
            full_run_log_error=full_run_log_error,
        )

        if failures:
            raise AssertionError("\n\n".join(failures))
    except Exception as error:
        result.setdefault("error", f"{type(error).__name__}: {error}")
        result.setdefault("traceback", traceback.format_exc())
        _write_failure_outputs(result)
        raise

    _write_pass_outputs(result)
    print("TS-969 passed")


def _read_full_run_log(
    observation: GitHubAccessibilityPullRequestGateObservation,
    *,
    log_reader: GitHubWorkflowRunLogReader,
) -> tuple[str, str | None]:
    if observation.latest_pull_request_run_id is None:
        return "", "The workflow run ID was missing, so the hosted run log could not be read."
    try:
        return log_reader.read_run_log(observation.latest_pull_request_run_id), None
    except Exception as error:  # noqa: BLE001
        return "", f"{type(error).__name__}: {error}"


def _evaluate_wrapper_invocation(
    result: dict[str, object],
    observation: GitHubAccessibilityPullRequestGateObservation,
    failures: list[str],
) -> None:
    step_failures: list[str] = []
    expected_files = [
        observation.pull_request_probe_path,
        observation.probe_render_host_path,
    ]
    missing_files = [
        path for path in expected_files if path and path not in observation.pull_request_file_paths
    ]
    unexpected_files = [
        path
        for path in observation.pull_request_file_paths
        if path not in expected_files
    ]
    if missing_files:
        step_failures.append(
            f"GitHub did not record the expected wrapper probe files: {missing_files}."
        )
    if unexpected_files:
        step_failures.append(
            "the disposable PR changed files outside the wrapper scenario under test: "
            f"{unexpected_files}."
        )
    if observation.latest_pull_request_run_id is None:
        step_failures.append(
            "GitHub Actions did not expose a contributor-visible pull-request workflow run."
        )

    if step_failures:
        message = (
            "Step 1 failed: "
            + " ".join(step_failures)
            + "\n"
            + f"Pull Request URL: {observation.pull_request_url}\n"
            + f"Observed PR files: {observation.pull_request_file_paths}\n"
            + f"Simulation technique: {observation.probe_contrast_technique}"
        )
        failures.append(message)
        _record_step(result, step=1, status="failed", action=REQUEST_STEPS[0], observed=message)
        return

    observed = (
        "Created a disposable PR that redirects `npm run test:a11y` to a failing "
        "contract-validation node test and triggered the live pull-request workflow.\n"
        f"Pull Request URL: {observation.pull_request_url}\n"
        f"Observed PR files: {observation.pull_request_file_paths}\n"
        f"Workflow run URL: {observation.latest_pull_request_run_url}\n"
        f"Simulation technique: {observation.probe_contrast_technique}"
    )
    _record_step(result, step=1, status="passed", action=REQUEST_STEPS[0], observed=observed)


def _evaluate_error_captured(
    result: dict[str, object],
    observation: GitHubAccessibilityPullRequestGateObservation,
    failures: list[str],
    *,
    full_run_log_text: str,
    full_run_log_error: str | None,
) -> None:
    step_failures: list[str] = []
    wrapper_step_output = _extract_step_output(full_run_log_text, WRAPPER_STEP_PATTERN)
    failure_message = _extract_failure_message(wrapper_step_output)
    wrapper_step_visible = _has_wrapper_step(
        observation.observed_step_names,
        full_run_log_text,
    )

    if full_run_log_error is not None:
        step_failures.append(
            f"the hosted run log could not be read: {full_run_log_error}."
        )
    if not wrapper_step_visible:
        step_failures.append(
            "the CI output did not expose the `Run axe-core accessibility checks` wrapper step."
        )
    if not wrapper_step_output.strip():
        step_failures.append(
            "the hosted run log did not include output from the wrapper step."
        )
    if failure_message is None:
        step_failures.append(
            "the wrapper step log did not capture the failing contract-validation error message."
        )

    if step_failures:
        message = (
            "Step 2 failed: "
            + " ".join(step_failures)
            + "\n"
            + f"Run URL: {observation.latest_pull_request_run_url or '<none>'}\n"
            + f"Observed steps: {observation.observed_step_names or ['<none>']}\n"
            + "Wrapper step excerpt:\n"
            + (
                _extract_relevant_full_log_excerpt(
                    full_run_log_text,
                    observation=observation,
                )
                or "<none>"
            )
        )
        failures.append(message)
        _record_step(result, step=2, status="failed", action=REQUEST_STEPS[1], observed=message)
        return

    observed = (
        "Inspected the wrapper-step log and found the failing contract-validation "
        "message captured in the contributor-visible GitHub Actions output.\n"
        f"Run URL: {observation.latest_pull_request_run_url}\n"
        f"Observed steps: {observation.observed_step_names}\n"
        f"Failure message: {failure_message}"
    )
    _record_step(result, step=2, status="passed", action=REQUEST_STEPS[1], observed=observed)


def _evaluate_wrapper_exit_code(
    result: dict[str, object],
    observation: GitHubAccessibilityPullRequestGateObservation,
    failures: list[str],
    *,
    full_run_log_text: str,
    wrapper_step_output: str,
) -> None:
    step_failures: list[str] = []
    exit_code = _extract_exit_code(wrapper_step_output)
    if observation.latest_pull_request_run_event != "pull_request":
        step_failures.append(
            f"the observed workflow event was `{observation.latest_pull_request_run_event or '<none>'}` instead of `pull_request`."
        )
    if observation.latest_pull_request_run_status != "completed":
        step_failures.append(
            f"the workflow run never completed; observed status was `{observation.latest_pull_request_run_status or '<none>'}`."
        )
    if observation.latest_pull_request_run_conclusion != EXPECTED_FAILURE_CONCLUSION:
        step_failures.append(
            "the overall CI workflow did not finish in a failed state; observed conclusion "
            f"was `{observation.latest_pull_request_run_conclusion or '<none>'}`."
        )
    if observation.pull_request_status_state != EXPECTED_FAILURE_CONCLUSION:
        step_failures.append(
            "the contributor-visible pull request checks did not report failure; observed "
            f"status state was `{observation.pull_request_status_state or '<none>'}`."
        )
    if not wrapper_step_output.strip():
        step_failures.append(
            "the hosted run log did not include output from the `Run axe-core accessibility checks` wrapper step."
        )
    if exit_code != "1":
        step_failures.append(
            "the wrapper step did not report `Process completed with exit code 1` in its own output; "
            f"observed exit code was `{exit_code or '<none>'}`."
        )

    if step_failures:
        message = (
            "Step 3 failed: "
            + " ".join(step_failures)
            + "\n"
            + f"Run URL: {observation.latest_pull_request_run_url or '<none>'}\n"
            + "Run status/conclusion: "
            + f"{observation.latest_pull_request_run_status or '<none>'}/"
            + f"{observation.latest_pull_request_run_conclusion or '<none>'}\n"
            + f"Observed pull-request status state: {observation.pull_request_status_state or '<none>'}\n"
            + f"Observed failed status checks: {observation.failed_status_check_names or ['<none>']}\n"
            + "Observed failed workflows: "
            + f"{observation.failed_status_check_workflow_names or ['<none>']}\n"
            + f"Observed exit code: {exit_code or '<none>'}\n"
            + "Relevant log excerpt:\n"
            + (
                _extract_relevant_full_log_excerpt(
                    full_run_log_text,
                    observation=observation,
                )
                or "<none>"
            )
        )
        failures.append(message)
        _record_step(result, step=3, status="failed", action=REQUEST_STEPS[2], observed=message)
        return

    observed = (
        "Confirmed the wrapper propagated the failing contract-validation result as "
        "exit code 1 and the CI surface finished in a failed state.\n"
        f"Run URL: {observation.latest_pull_request_run_url}\n"
        f"Run status/conclusion: {observation.latest_pull_request_run_status}/{observation.latest_pull_request_run_conclusion}\n"
        f"Pull-request status state: {observation.pull_request_status_state}\n"
        f"Failed status checks: {observation.failed_status_check_names or ['<none>']}\n"
        f"Failed workflows: {observation.failed_status_check_workflow_names or ['<none>']}\n"
        f"Observed exit code: {exit_code}"
    )
    _record_step(result, step=3, status="passed", action=REQUEST_STEPS[2], observed=observed)


def _record_live_user_verification(
    result: dict[str, object],
    observation: GitHubAccessibilityPullRequestGateObservation,
    *,
    full_run_log_text: str,
    full_run_log_error: str | None,
) -> None:
    wrapper_step_output = _extract_step_output(full_run_log_text, WRAPPER_STEP_PATTERN)
    _record_human_verification(
        result,
        check=(
            "Reviewed the same contributor-visible PR checks surface and workflow summary a "
            "maintainer would use before merging."
        ),
        observed=(
            f"PR checks URL: `{observation.pull_request_checks_url}`; run URL: "
            f"`{observation.latest_pull_request_run_url or '<none>'}`; workflow conclusion: "
            f"`{observation.latest_pull_request_run_conclusion or '<none>'}`; pull-request "
            f"status state: `{observation.pull_request_status_state or '<none>'}`; failed "
            f"checks: `{observation.failed_status_check_names or ['<none>']}`; failed "
            f"workflows: `{observation.failed_status_check_workflow_names or ['<none>']}`."
        ),
    )
    _record_human_verification(
        result,
        check=(
            "Read the hosted GitHub Actions log the way a reviewer would to confirm the "
            "wrapper step showed the failure message and exit code."
        ),
        observed=(
            f"Log read error: `{full_run_log_error or '<none>'}`; wrapper step visible: "
            f"`{_has_wrapper_step(observation.observed_step_names, full_run_log_text)}`; failure "
            f"message: `{_extract_failure_message(wrapper_step_output) or '<none>'}`; wrapper "
            f"exit code: `{_extract_exit_code(wrapper_step_output) or '<none>'}`; "
            f"log excerpt: `{_one_line(_extract_relevant_full_log_excerpt(full_run_log_text, observation=observation)) or '<none>'}`."
        ),
    )


def _has_wrapper_step(step_names: list[str], full_run_log_text: str) -> bool:
    if any(WRAPPER_STEP_PATTERN.search(name or "") for name in step_names):
        return True
    return any(
        WRAPPER_STEP_PATTERN.search(step_name)
        for step_name in _surface_step_names_from_log(full_run_log_text)
    )


def _surface_step_names_from_log(full_run_log_text: str) -> list[str]:
    step_names: list[str] = []
    for raw_line in full_run_log_text.splitlines():
        parts = raw_line.lstrip("\ufeff").split("\t", 2)
        if len(parts) != 3:
            continue
        step_name = parts[1].strip()
        if step_name:
            step_names.append(step_name)
    return step_names


def _extract_step_output(full_run_log_text: str, step_pattern: re.Pattern[str]) -> str:
    lines: list[str] = []
    for raw_line in full_run_log_text.splitlines():
        parts = raw_line.lstrip("\ufeff").split("\t", 2)
        if len(parts) != 3:
            continue
        step_name = parts[1].strip()
        if not step_pattern.search(step_name):
            continue
        payload = parts[2].strip()
        if payload:
            lines.append(payload)
    return "\n".join(lines)


def _extract_failure_message(text: str) -> str | None:
    for pattern in FAILURE_MESSAGE_PATTERNS:
        match = pattern.search(text)
        if match is not None:
            return _one_line(match.group(0))
    return None


def _extract_exit_code(text: str) -> str | None:
    match = EXIT_CODE_PATTERN.search(text)
    if match is None:
        return None
    return match.group("code")


def _extract_relevant_full_log_excerpt(
    full_run_log_text: str,
    *,
    observation: GitHubAccessibilityPullRequestGateObservation,
) -> str:
    wrapper_step_output = _extract_step_output(full_run_log_text, WRAPPER_STEP_PATTERN)
    if wrapper_step_output.strip():
        return _snippet(wrapper_step_output, limit=1800)
    if not full_run_log_text.strip():
        return observation.run_log_excerpt or ""

    lowered = full_run_log_text.lower()
    markers = [
        "run axe-core accessibility checks",
        "ts-969 simulated contract validation failure",
        "standardized wrapper must propagate exit code 1",
        "process completed with exit code 1",
        "npm run test:a11y",
    ]
    for marker in markers:
        index = lowered.find(marker)
        if index >= 0:
            start = max(index - 250, 0)
            end = min(index + 1250, len(full_run_log_text))
            return _snippet(full_run_log_text[start:end], limit=1800)
    return _snippet(full_run_log_text, limit=1800)


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
    RESPONSE_PATH.write_text(_response_summary(result, passed=True), encoding="utf-8")
    REVIEW_REPLIES_PATH.write_text(
        _review_replies_payload(result, passed=True),
        encoding="utf-8",
    )


def _write_failure_outputs(result: dict[str, object]) -> None:
    error = str(result.get("error", "AssertionError: TS-969 failed"))
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
    PR_BODY_PATH.write_text(_markdown_summary(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_summary(result, passed=False), encoding="utf-8")
    REVIEW_REPLIES_PATH.write_text(
        _review_replies_payload(result, passed=False),
        encoding="utf-8",
    )
    BUG_DESCRIPTION_PATH.write_text(_bug_description(result), encoding="utf-8")


def _jira_comment(result: dict[str, object], *, passed: bool) -> str:
    status = "✅ PASSED" if passed else "❌ FAILED"
    lines = [
        "h3. Test Automation Result",
        "",
        f"*Status:* {status}",
        f"*Test Case:* {TICKET_KEY} - {TEST_CASE_TITLE}",
        "",
        "h4. What was automated",
        "* Created a disposable pull request against the live repository that patches {{package.json}} so {{npm run test:a11y}} runs a ticket-specific failing contract-validation node test.",
        "* Waited for the real {{Flutter Required Checks}} pull-request workflow to complete on GitHub Actions.",
        "* Inspected the contributor-visible {{Run axe-core accessibility checks}} wrapper log for the captured failure message and {{Process completed with exit code 1}}.",
        "",
        "h4. Human-style verification",
        *_human_lines(result, jira=True),
        "",
        "h4. Result",
        (
            "* Matched the expected result."
            if passed
            else f"* Did not match the expected result. {_failed_step_summary(result)}"
        ),
        (
            f"* Environment: repository {{{{{result['repository']}}}}} @ "
            f"{{{{{result['default_branch']}}}}}, client {{GitHub CLI}}, "
            f"OS {{{{{result['os']}}}}}."
        ),
        "",
        "h4. Step results",
        *_step_lines(result, jira=True),
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


def _markdown_summary(result: dict[str, object], *, passed: bool) -> str:
    status = "✅ PASSED" if passed else "❌ FAILED"
    lines = [
        "## Test Automation Result",
        "",
        f"**Status:** {status}",
        f"**Test Case:** {TICKET_KEY} - {TEST_CASE_TITLE}",
        "",
        "## What was automated",
        "- Created a disposable pull request against the live repository that patches `package.json` so `npm run test:a11y` runs a ticket-specific failing contract-validation node test.",
        "- Waited for the real `Flutter Required Checks` pull-request workflow to complete on GitHub Actions.",
        "- Inspected the contributor-visible `Run axe-core accessibility checks` wrapper log for the captured failure message and `Process completed with exit code 1`.",
        "",
        "## Human-style verification",
        *_human_lines(result, jira=False),
        "",
        "## Result",
        (
            "- Matched the expected result."
            if passed
            else f"- Did not match the expected result. {_failed_step_summary(result)}"
        ),
        (
            f"- Environment: repository `{result['repository']}` @ "
            f"`{result['default_branch']}`, client `GitHub CLI`, OS `{result['os']}`."
        ),
        "",
        "## Step results",
        *_step_lines(result, jira=False),
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


def _response_summary(result: dict[str, object], *, passed: bool) -> str:
    status = "PASSED" if passed else "FAILED"
    lines = [
        "## Test Automation Summary",
        "",
        "- Added TS-969 as a disposable PR probe against the live GitHub Actions CI wrapper.",
        "- The probe redirects `npm run test:a11y` to a failing contract-validation node test and checks whether the wrapper logs the error and exits with code 1.",
        f"- Test case: **{TICKET_KEY} - {TEST_CASE_TITLE}**",
        f"- Result: **{status}**",
        f"- Command: `{RUN_COMMAND}`",
        (
            f"- Environment: `{result['repository']}` @ `{result['default_branch']}` "
            f"using GitHub CLI on `{result['os']}`."
        ),
        (
            "- Outcome: the live wrapper captured the failing contract-validation test and propagated exit code 1."
            if passed
            else f"- Outcome: {_failed_step_summary(result)}"
        ),
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
    step_map = {
        int(step["step"]): step
        for step in result.get("steps", [])
        if isinstance(step, dict) and isinstance(step.get("step"), int)
    }
    return (
        f"# {TICKET_KEY} - CI wrapper does not propagate failing contract-validation exit code\n\n"
        "## Steps to reproduce\n"
        f"1. {REQUEST_STEPS[0]}  \n"
        f"   - Actual: {step_map.get(1, {}).get('observed', '<missing>')}  \n"
        f"   - Result: {'PASSED ✅' if step_map.get(1, {}).get('status') == 'passed' else 'FAILED ❌'}\n"
        f"2. {REQUEST_STEPS[1]}  \n"
        f"   - Actual: {step_map.get(2, {}).get('observed', '<missing>')}  \n"
        f"   - Result: {'PASSED ✅' if step_map.get(2, {}).get('status') == 'passed' else 'FAILED ❌'}\n"
        f"3. {REQUEST_STEPS[2]}  \n"
        f"   - Actual: {step_map.get(3, {}).get('observed', '<missing>')}  \n"
        f"   - Result: {'PASSED ✅' if step_map.get(3, {}).get('status') == 'passed' else 'FAILED ❌'}\n\n"
        "## Exact error message or assertion failure\n"
        "```text\n"
        f"{result.get('traceback', result.get('error', '<missing>'))}"
        "```\n\n"
        "## Actual vs Expected\n"
        f"- **Expected:** {EXPECTED_RESULT}\n"
        "- **Actual:** The live `Run axe-core accessibility checks` wrapper did not expose the "
        "ticket-specific contract-validation failure message and/or did not finish with "
        "`Process completed with exit code 1`, so the failing validation could still pass "
        "through the CI step without the expected non-zero exit.\n\n"
        "## Environment details\n"
        f"- **URL:** {result.get('pull_request_url', '<missing pull request URL>')}\n"
        "- **Browser:** GitHub CLI / GitHub Actions hosted log surface\n"
        f"- **OS:** {result.get('os')}\n"
        f"- **Repository:** {result.get('repository')}\n"
        f"- **Branch:** {result.get('default_branch')}\n"
        f"- **PR checks URL:** {result.get('pull_request_checks_url', '<missing checks URL>')}\n"
        f"- **Workflow run URL:** {result.get('latest_pull_request_run_url', '<missing run URL>')}\n"
        f"- **Run command:** `{result.get('run_command')}`\n"
        f"- **Config:** `{CONFIG_PATH}`\n\n"
        "## Screenshots or logs\n"
        "- **Wrapper step output:**\n"
        "```text\n"
        f"{result.get('wrapper_step_output', '<missing wrapper step output>')}\n"
        "```\n"
        "- **Full workflow/log excerpt:**\n"
        "```text\n"
        f"{result.get('full_run_log_excerpt', '<missing log excerpt>')}\n"
        "```\n"
    )


def _review_replies_payload(result: dict[str, object], *, passed: bool) -> str:
    replies = [
        {
            "inReplyToId": thread.get("rootCommentId"),
            "threadId": thread.get("threadId"),
            "reply": _review_reply_text(result=result, passed=passed),
        }
        for thread in _discussion_threads()
    ]
    return json.dumps({"replies": replies}, indent=2) + "\n"


def _discussion_threads() -> list[dict[str, object]]:
    if not DISCUSSIONS_RAW_PATH.is_file():
        return []
    raw = json.loads(DISCUSSIONS_RAW_PATH.read_text(encoding="utf-8"))
    threads = raw.get("threads")
    if not isinstance(threads, list):
        return []
    return [
        thread
        for thread in threads
        if isinstance(thread, dict)
        and thread.get("resolved") is False
        and thread.get("rootCommentId") is not None
        and thread.get("threadId") is not None
    ]


def _review_reply_text(result: dict[str, object], *, passed: bool) -> str:
    rerun_summary = (
        f"Re-ran `{RUN_COMMAND}`: passed (`1 passed, 0 failed`)."
        if passed
        else f"Re-ran `{RUN_COMMAND}`: failed with `{result.get('error', 'unknown error')}`."
    )
    return (
        "Fixed: step 3 now derives `Process completed with exit code 1` only from the "
        "`Run axe-core accessibility checks` wrapper-step output, and TS-969 now includes "
        "a regression that rejects exit-code lines emitted by other workflow steps. "
        f"{rerun_summary}"
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
        }
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


def _failed_step_summary(result: dict[str, object]) -> str:
    failures = [
        f"Step {step['step']}: {step['observed']}"
        for step in result.get("steps", [])
        if step.get("status") != "passed"
    ]
    if failures:
        return " | ".join(failures)
    return str(result.get("error", "No failure details recorded."))


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for step in result.get("steps", []):
        marker = "✅" if step["status"] == "passed" else "❌"
        prefix = "*" if jira else "-"
        lines.append(
            f"{prefix} {marker} Step {step['step']}: {step['action']}  "
            f"Observed: {step['observed']}"
        )
    return lines or (["* No steps recorded."] if jira else ["- No steps recorded."])


def _human_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    entries = result.get("human_verification", [])
    if not entries:
        return ["* No human-style verification recorded."] if jira else [
            "- No human-style verification recorded."
        ]
    prefix = "*" if jira else "-"
    return [
        f"{prefix} {entry['check']} Observed: {entry['observed']}"
        for entry in entries
    ]


def _snippet(text: str, *, limit: int) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"


def _one_line(text: object) -> str:
    return " ".join(str(text).split())


if __name__ == "__main__":
    main()
