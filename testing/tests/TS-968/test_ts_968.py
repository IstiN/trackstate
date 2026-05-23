from __future__ import annotations

import json
import platform
import re
import subprocess
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.services.accessibility_log_validation_exit_code_probe import (  # noqa: E402
    AccessibilityLogValidationExitCodeProbeService,
)
from testing.core.config.accessibility_log_validation_exit_code_config import (  # noqa: E402
    AccessibilityLogValidationExitCodeConfig,
)
from testing.core.models.accessibility_log_validation_exit_code_result import (  # noqa: E402
    AccessibilityLogValidationExitCodeObservation,
)
from testing.core.models.cli_command_result import CliCommandResult  # noqa: E402

TICKET_KEY = "TS-968"
TEST_CASE_TITLE = "Accessibility validation failure - runner returns non-zero exit code"
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-968/test_ts_968.py"
TEST_FILE_PATH = "testing/tests/TS-968/test_ts_968.py"
CONFIG_PATH = REPO_ROOT / "testing/tests/TS-968/config.yaml"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
REVIEW_REPLIES_PATH = OUTPUTS_DIR / "review_replies.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
DISCUSSIONS_RAW_PATH = REPO_ROOT / "input" / TICKET_KEY / "pr_discussions_raw.json"

REQUEST_STEPS = [
    "Modify the accessibility validation script or its local environment to trigger an 'AssertionError' (e.g., simulate a missing mandatory step).",
    "Execute the script directly using the command: `node testing/accessibility/log_validation.node.test.js`.",
    "Check the exit status code of the process immediately after execution (e.g., using `echo $?` in a Bash terminal).",
]
EXPECTED_RESULT = (
    "The script returns exit code 1, ensuring that the CI workflow step is accurately "
    "marked as a failure instead of reporting success."
)
REWORK_FIXES = [
    "Relaxed the control precondition so it checks for a clean passing baseline via exit code `0`, `# fail 0`, and no `not ok` lines instead of hardcoding the current pass count.",
    "Restricted `bug_description.md` generation to the real product-defect path where the baseline passed, the disposable workflow mutation succeeded, the expected assertion failure surfaced, and only the exit-code propagation stayed broken.",
    "Relaxed the Step 2 TAP-summary assertion so it now accepts any failing summary plus a visible `not ok` record instead of pinning the mutated run to exactly `# fail 1`.",
]
ASSERTION_PATTERN = re.compile(r"AssertionError", re.IGNORECASE)
FAILING_SUMMARY_PATTERN = re.compile(r"# fail\s+[1-9]\d*", re.IGNORECASE)
ZERO_FAIL_COUNT_PATTERN = re.compile(r"# fail\s+0", re.IGNORECASE)
NOT_OK_PATTERN = re.compile(r"^\s*not ok\b", re.IGNORECASE | re.MULTILINE)


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    config = AccessibilityLogValidationExitCodeConfig.from_file(CONFIG_PATH)
    probe = AccessibilityLogValidationExitCodeProbeService(REPO_ROOT)
    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "test_case_title": TEST_CASE_TITLE,
        "run_command": RUN_COMMAND,
        "test_file_path": TEST_FILE_PATH,
        "expected_result": EXPECTED_RESULT,
        "command": " ".join(config.requested_command),
        "workflow_path": config.workflow_relative_path,
        "node_test_path": config.node_test_relative_path,
        "validator_path": config.validator_relative_path,
        "browser": "Terminal / Node.js",
        "os": platform.platform(),
        "node_version": _node_version(),
        "steps": [],
        "human_verification": [],
    }

    try:
        observation = probe.validate(config)
        result.update(_observation_to_dict(observation))

        failures: list[str] = []
        _evaluate_control_run(
            result,
            observation=observation,
            expected_exit_code=config.expected_pass_exit_code,
            failures=failures,
        )
        _evaluate_mutation(
            result,
            observation=observation,
            expected_message=config.expected_missing_step_message,
            failures=failures,
        )
        _evaluate_direct_command_output(
            result,
            observation=observation,
            expected_message=config.expected_missing_step_message,
            expected_subtest=config.expected_failing_subtest,
            failures=failures,
        )
        _evaluate_exit_code(
            result,
            observation=observation,
            expected_exit_code=config.expected_fail_exit_code,
            failures=failures,
        )
        _record_human_verification(
            result,
            observation=observation,
            expected_message=config.expected_missing_step_message,
        )

        if failures:
            raise AssertionError("\n\n".join(failures))
    except Exception as error:
        result.setdefault("error", f"{type(error).__name__}: {error}")
        result.setdefault("traceback", traceback.format_exc())
        _write_failure_outputs(result)
        raise

    _write_pass_outputs(result)
    print("TS-968 passed")


def _evaluate_control_run(
    result: dict[str, object],
    *,
    observation: AccessibilityLogValidationExitCodeObservation,
    expected_exit_code: int,
    failures: list[str],
) -> None:
    control_output = _combine_output(observation.control_run)
    step_failures: list[str] = []
    if observation.control_run.exit_code != expected_exit_code:
        step_failures.append(
            "the unmodified repository did not preserve a passing control run before the "
            f"failure simulation; observed exit code was `{observation.control_run.exit_code}`."
        )
    if not ZERO_FAIL_COUNT_PATTERN.search(control_output):
        step_failures.append(
            "the control run did not report a zero-failure TAP summary."
        )
    if NOT_OK_PATTERN.search(control_output):
        step_failures.append(
            "the control run still emitted a failing `not ok` TAP record."
        )

    if step_failures:
        message = (
            "Precondition failed: "
            + " ".join(step_failures)
            + "\n"
            + f"Command: {observation.requested_command_text}\n"
            + "Observed control output:\n"
            + _compact_text(control_output)
        )
        failures.append(message)
        _record_step(
            result,
            step=0,
            status="failed",
            action=(
                "Run the production Node contract test against the unmodified repository "
                "to confirm the baseline still passes."
            ),
            observed=message,
        )
        return

    observed = (
        "Ran the production Node contract test against the unmodified repository and "
        "confirmed the current workflow still passes before simulating the failure.\n"
        f"Command: {observation.requested_command_text}\n"
        f"Observed exit code: {observation.control_run.exit_code}\n"
        f"Observed summary: {_extract_summary_line(control_output, '# fail')}"
    )
    _record_step(
        result,
        step=0,
        status="passed",
        action=(
            "Run the production Node contract test against the unmodified repository "
            "to confirm the baseline still passes."
        ),
        observed=observed,
    )


def _evaluate_mutation(
    result: dict[str, object],
    *,
    observation: AccessibilityLogValidationExitCodeObservation,
    expected_message: str,
    failures: list[str],
) -> None:
    step_failures: list[str] = []
    if not observation.original_workflow_contains_log_validation_step:
        step_failures.append(
            "the baseline workflow did not contain the mandatory `log-validation` step."
        )
    if observation.mutated_workflow_contains_log_validation_step:
        step_failures.append(
            "the disposable workflow copy still contained the `log-validation` step after mutation."
        )

    if step_failures:
        message = (
            "Step 1 failed: "
            + " ".join(step_failures)
            + "\n"
            + f"Workflow path: {observation.workflow_relative_path}\n"
            + f"Expected assertion message: {expected_message}"
        )
        failures.append(message)
        _record_step(result, step=1, status="failed", action=REQUEST_STEPS[0], observed=message)
        return

    observed = (
        "Created a disposable local environment by copying the production Node test and "
        "workflow file, then removed the mandatory `log-validation` step only from the "
        "copied workflow to trigger the AssertionError path.\n"
        f"Workflow path: {observation.workflow_relative_path}\n"
        "Mutation result: baseline copy contained `log-validation`; disposable copy did not."
    )
    _record_step(result, step=1, status="passed", action=REQUEST_STEPS[0], observed=observed)


def _evaluate_direct_command_output(
    result: dict[str, object],
    *,
    observation: AccessibilityLogValidationExitCodeObservation,
    expected_message: str,
    expected_subtest: str,
    failures: list[str],
) -> None:
    mutated_output = _combine_output(observation.mutated_run)
    step_failures: list[str] = []
    if expected_subtest not in mutated_output:
        step_failures.append(
            "the terminal output did not show the expected failing accessibility subtest name."
        )
    if expected_message not in mutated_output:
        step_failures.append(
            "the terminal output did not include the expected missing-step assertion message."
        )
    if not ASSERTION_PATTERN.search(mutated_output):
        step_failures.append(
            "the terminal output did not identify the failure as an `AssertionError`."
        )
    if not FAILING_SUMMARY_PATTERN.search(mutated_output):
        step_failures.append(
            "the terminal summary did not report a failing TAP summary."
        )
    if not NOT_OK_PATTERN.search(mutated_output):
        step_failures.append(
            "the terminal output did not include a failing `not ok` TAP record."
        )

    if step_failures:
        message = (
            "Step 2 failed: "
            + " ".join(step_failures)
            + "\n"
            + f"Command: {observation.requested_command_text}\n"
            + "Observed output:\n"
            + _compact_text(mutated_output)
        )
        failures.append(message)
        _record_step(result, step=2, status="failed", action=REQUEST_STEPS[1], observed=message)
        return

    observed = (
        "Executed the same Node command a contributor would run and observed the TAP failure "
        "surface in the terminal.\n"
        f"Command: {observation.requested_command_text}\n"
        f"Observed failing subtest: {expected_subtest}\n"
        f"Observed assertion message: {expected_message}\n"
        f"Observed failure summary: {_extract_summary_line(mutated_output, '# fail')}"
    )
    _record_step(result, step=2, status="passed", action=REQUEST_STEPS[1], observed=observed)


def _evaluate_exit_code(
    result: dict[str, object],
    *,
    observation: AccessibilityLogValidationExitCodeObservation,
    expected_exit_code: int,
    failures: list[str],
) -> None:
    if observation.mutated_run.exit_code != expected_exit_code:
        message = (
            "Step 3 failed: the process did not propagate the failing assertion as the "
            f"expected non-zero exit code.\nExpected exit code: {expected_exit_code}\n"
            f"Observed exit code: {observation.mutated_run.exit_code}\n"
            + "Observed output:\n"
            + _compact_text(_combine_output(observation.mutated_run))
        )
        failures.append(message)
        _record_step(result, step=3, status="failed", action=REQUEST_STEPS[2], observed=message)
        return

    observed = (
        "Checked the direct process status exactly as a shell user would inspect `$?` and "
        f"confirmed the failing run exited with `{observation.mutated_run.exit_code}`."
    )
    _record_step(result, step=3, status="passed", action=REQUEST_STEPS[2], observed=observed)


def _record_human_verification(
    result: dict[str, object],
    *,
    observation: AccessibilityLogValidationExitCodeObservation,
    expected_message: str,
) -> None:
    mutated_output = _combine_output(observation.mutated_run)
    plain_expected_message = expected_message.replace("`", "").rstrip(".")
    result["human_verification"] = [
        {
            "check": "Visible terminal failure text",
            "observed": (
                "The terminal showed not ok 1 - accessibility workflow exposes a "
                "contributor-visible log-validation step followed by the exact assertion "
                f"message {plain_expected_message}."
            ),
        },
        {
            "check": "Visible terminal summary",
            "observed": (
                f"The terminal summary showed {_extract_summary_line(mutated_output, '# pass')} "
                f"and {_extract_summary_line(mutated_output, '# fail')}."
            ),
        },
        {
            "check": "Observed shell exit status",
            "observed": f"The command returned exit code {observation.mutated_run.exit_code}.",
        },
    ]


def _write_pass_outputs(result: dict[str, object]) -> None:
    BUG_DESCRIPTION_PATH.unlink(missing_ok=True)
    _write_review_replies(result, passed=True)
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

    control_output = _as_text(result.get("control_output"))
    mutated_output = _as_text(result.get("mutated_output"))
    human_verification = _human_checks(result)

    jira_lines = [
        "h3. Test Automation Result",
        "",
        "*Status:* ✅ PASSED",
        f"*Test Case:* {TICKET_KEY} — {TEST_CASE_TITLE}",
        "",
        "h4. What was automated",
        (
            "* Precondition: Ran the production Node contract test on the unmodified repository "
            f"and confirmed it returned exit code {{code}}{result.get('control_exit_code')}{{code}}."
        ),
        (
            "* Step 1: Created a disposable local copy of "
            f"{{code}}{result.get('workflow_path')}{{code}} and removed only the mandatory "
            "{code}log-validation{code} step to trigger the assertion path."
        ),
        (
            "* Step 2: Executed {code}node testing/accessibility/log_validation.node.test.js{code} "
            "against that disposable copy and captured the terminal output."
        ),
        (
            "* Step 3: Verified the process status returned "
            f"{{code}}{result.get('mutated_exit_code')}{{code}}, which matches the expected "
            "{code}echo $?{code} result for a failed assertion."
        ),
        "",
        "h4. Human-style verification",
    ]

    for check in human_verification:
        jira_lines.append(
            f"* {jira_inline(_as_text(check.get('check')))} — observed {jira_inline(_as_text(check.get('observed')))}"
        )

    jira_lines.extend(
        [
            "",
            "h4. Result",
            "* Step 1 passed: the local environment mutation removed the mandatory workflow step without altering the production repository.",
            "* Step 2 passed: the terminal visibly showed the failing accessibility subtest, the missing-step assertion, and a failing TAP summary.",
            "* Step 3 passed: the process propagated the assertion failure with exit code 1.",
            "* The observed behavior matched the expected result.",
            "",
            "h4. Run command",
            "{code:bash}",
            RUN_COMMAND,
            "{code}",
            "",
            "h4. Observed control output excerpt",
            "{code}",
            _compact_text(control_output),
            "{code}",
            "",
            "h4. Observed failing output excerpt",
            "{code}",
            _compact_text(mutated_output),
            "{code}",
        ]
    )

    markdown_lines = [
        "## Rework Summary",
        "",
        *[f"- {fix}" for fix in REWORK_FIXES],
        "",
        "## Test Automation Result",
        "",
        "**Status:** ✅ PASSED",
        f"**Test Case:** {TICKET_KEY} — {TEST_CASE_TITLE}",
        "",
        "## What was automated",
        (
            "- Ran the production Node contract test on the unmodified repository and "
            f"confirmed it returned exit code `{result.get('control_exit_code')}`."
        ),
        (
            "- Created a disposable local copy of "
            f"`{result.get('workflow_path')}` and removed only the mandatory "
            "`log-validation` step to trigger the assertion path."
        ),
        (
            "- Executed `node testing/accessibility/log_validation.node.test.js` against the "
            "disposable copy and captured the terminal output."
        ),
        (
            "- Verified the failing process returned exit code "
            f"`{result.get('mutated_exit_code')}`, matching the shell-visible `$?` value."
        ),
        "",
        "## Human-style verification",
    ]

    for check in human_verification:
        markdown_lines.append(
            f"- `{_as_text(check.get('check'))}` — observed `{_as_text(check.get('observed'))}`"
        )

    markdown_lines.extend(
        [
            "",
            "## Result",
            "- Step 1 passed: the disposable local environment removed the mandatory workflow step.",
            "- Step 2 passed: the terminal visibly showed the failing subtest, assertion message, and TAP failure summary.",
            "- Step 3 passed: the process returned exit code `1`.",
            "- The observed behavior matched the expected result.",
            "",
            "## How to run",
            "```bash",
            RUN_COMMAND,
            "```",
        ]
    )

    JIRA_COMMENT_PATH.write_text("\n".join(jira_lines) + "\n", encoding="utf-8")
    PR_BODY_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    RESPONSE_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")


def _write_failure_outputs(result: dict[str, object]) -> None:
    error_message = _as_text(result.get("error")) or "AssertionError: TS-968 failed"
    _write_review_replies(result, passed=False)
    RESULT_PATH.write_text(
        json.dumps(
            {
                "status": "failed",
                "passed": 0,
                "failed": 1,
                "skipped": 0,
                "summary": "0 passed, 1 failed",
                "error": error_message,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    steps = result.get("steps")
    recorded_steps = steps if isinstance(steps, list) else []
    precondition_state = _step_status(recorded_steps, 0)
    step1_state = _step_status(recorded_steps, 1)
    step2_state = _step_status(recorded_steps, 2)
    step3_state = _step_status(recorded_steps, 3)
    mutated_output = _as_text(result.get("mutated_output"))
    trace_text = _as_text(result.get("traceback"))
    node_version = _as_text(result.get("node_version"))
    command = _as_text(result.get("command"))
    bug_is_product_gap = _should_write_bug_description(recorded_steps)
    environment_text = (
        f"Repository: IstiN/trackstate\n"
        f"Working directory: {REPO_ROOT}\n"
        f"Workflow path: {_as_text(result.get('workflow_path'))}\n"
        f"Node test path: {_as_text(result.get('node_test_path'))}\n"
        f"Command: {command}\n"
        f"Node.js: {node_version}\n"
        f"OS: {_as_text(result.get('os'))}"
    )

    jira_lines = [
        "h3. Test Automation Result",
        "",
        "*Status:* ❌ FAILED",
        f"*Test Case:* {TICKET_KEY} — {TEST_CASE_TITLE}",
        "",
        "h4. Exact steps to reproduce",
        (
            f"* {'✅' if precondition_state == 'passed' else '❌'} Precondition: "
            "Run the production Node contract test on the unmodified repository."
            + (
                f" Observed exit code {{code}}{result.get('control_exit_code')}{{code}}."
                if precondition_state == "passed"
                else " Observed: the baseline did not pass before the failure simulation."
            )
        ),
        (
            f"* {'✅' if step1_state == 'passed' else '❌'} Step 1: {REQUEST_STEPS[0]} "
            + _step_observed(recorded_steps, 1)
        ),
        (
            f"* {'✅' if step2_state == 'passed' else '❌'} Step 2: {REQUEST_STEPS[1]} "
            + _step_observed(recorded_steps, 2)
        ),
        (
            f"* {'✅' if step3_state == 'passed' else '❌'} Step 3: {REQUEST_STEPS[2]} "
            + _step_observed(recorded_steps, 3)
        ),
        "",
        "h4. Actual vs Expected",
        f"* *Expected:* {EXPECTED_RESULT}",
        (
            "* *Actual:* The disposable run returned exit code "
            f"{{code}}{result.get('mutated_exit_code', '<none>')}{{code}} and produced terminal output "
            f"{{code}}{_compact_text(mutated_output)}{{code}}."
        ),
        "",
        "h4. Environment",
        "{code}",
        environment_text,
        "{code}",
        "",
        "h4. Exact error message / assertion failure",
        "{code}",
        error_message,
        "",
        trace_text,
        "{code}",
        "",
        "h4. Terminal output",
        "{code}",
        _compact_text(mutated_output),
        "{code}",
    ]

    markdown_lines = [
        "## Rework Summary",
        "",
        *[f"- {fix}" for fix in REWORK_FIXES],
        "",
        "## Test Automation Result",
        "",
        "**Status:** ❌ FAILED",
        f"**Test Case:** {TICKET_KEY} — {TEST_CASE_TITLE}",
        "",
        "## Exact steps to reproduce",
        (
            f"1. {'✅' if precondition_state == 'passed' else '❌'} Precondition: run the production Node contract test on the unmodified repository."
            + (
                f" Observed exit code `{result.get('control_exit_code')}`."
                if precondition_state == "passed"
                else " Observed: the baseline did not pass before the failure simulation."
            )
        ),
        f"2. {'✅' if step1_state == 'passed' else '❌'} {REQUEST_STEPS[0]} {_step_observed(recorded_steps, 1)}",
        f"3. {'✅' if step2_state == 'passed' else '❌'} {REQUEST_STEPS[1]} {_step_observed(recorded_steps, 2)}",
        f"4. {'✅' if step3_state == 'passed' else '❌'} {REQUEST_STEPS[2]} {_step_observed(recorded_steps, 3)}",
        "",
        "## Actual vs Expected",
        f"- **Expected:** {EXPECTED_RESULT}",
        (
            "- **Actual:** The disposable run returned exit code "
            f"`{result.get('mutated_exit_code', '<none>')}` and produced terminal output "
            f"`{_compact_text(mutated_output)}`."
        ),
        "",
        "## Environment",
        "```text",
        environment_text,
        "```",
        "",
        "## Exact error message / assertion failure",
        "```text",
        error_message,
        "",
        trace_text,
        "```",
        "",
        "## Terminal output",
        "```text",
        _compact_text(mutated_output),
        "```",
    ]

    JIRA_COMMENT_PATH.write_text("\n".join(jira_lines) + "\n", encoding="utf-8")
    PR_BODY_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    RESPONSE_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    if bug_is_product_gap:
        BUG_DESCRIPTION_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    else:
        BUG_DESCRIPTION_PATH.unlink(missing_ok=True)


def _observation_to_dict(
    observation: AccessibilityLogValidationExitCodeObservation,
) -> dict[str, object]:
    return {
        "control_exit_code": observation.control_run.exit_code,
        "control_output": _combine_output(observation.control_run),
        "mutated_exit_code": observation.mutated_run.exit_code,
        "mutated_output": _combine_output(observation.mutated_run),
        "mutation_removed_log_validation_step": (
            observation.mutation_removed_log_validation_step
        ),
        "original_workflow_contains_log_validation_step": (
            observation.original_workflow_contains_log_validation_step
        ),
        "mutated_workflow_contains_log_validation_step": (
            observation.mutated_workflow_contains_log_validation_step
        ),
    }


def _node_version() -> str:
    completed = subprocess.run(
        ["node", "--version"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    output = (completed.stdout or completed.stderr).strip()
    return output or f"exit code {completed.returncode}"


def _record_step(
    result: dict[str, object],
    *,
    step: int,
    status: str,
    action: str,
    observed: str,
) -> None:
    steps = result.setdefault("steps", [])
    if not isinstance(steps, list):
        raise TypeError("TS-968 result.steps must be a list.")
    steps.append(
        {
            "step": step,
            "status": status,
            "action": action,
            "observed": observed,
        }
    )


def _human_checks(result: dict[str, object]) -> list[dict[str, object]]:
    checks = result.get("human_verification")
    if not isinstance(checks, list):
        return []
    return [check for check in checks if isinstance(check, dict)]


def _step_status(steps: list[object], step_number: int) -> str:
    for step in steps:
        if isinstance(step, dict) and step.get("step") == step_number:
            status = step.get("status")
            if isinstance(status, str):
                return status
    return "not_run"


def _step_observed(steps: list[object], step_number: int) -> str:
    for step in steps:
        if isinstance(step, dict) and step.get("step") == step_number:
            observed = step.get("observed")
            if isinstance(observed, str):
                return f"Observed: {observed}"
    return "Observed: no step-specific observation was recorded."


def _should_write_bug_description(steps: list[object]) -> bool:
    return (
        _step_status(steps, 0) == "passed"
        and _step_status(steps, 1) == "passed"
        and _step_status(steps, 2) == "passed"
        and _step_status(steps, 3) == "failed"
    )


def _combine_output(result: CliCommandResult) -> str:
    parts = [result.stdout.strip(), result.stderr.strip()]
    return "\n".join(part for part in parts if part).strip()


def _extract_summary_line(output: str, marker: str) -> str:
    for line in output.splitlines():
        if marker.lower() in line.lower():
            return line.strip()
    return "<none>"


def _compact_text(text: str, *, limit: int = 2500) -> str:
    compact = text.strip()
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


def _as_text(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def jira_inline(value: str) -> str:
    return f"{{{{{value}}}}}"


def _write_review_replies(result: dict[str, object], *, passed: bool) -> None:
    replies = [
        {
            "inReplyToId": thread.get("rootCommentId"),
            "threadId": thread.get("threadId"),
            "reply": _review_reply_text(thread=thread, result=result, passed=passed),
        }
        for thread in _discussion_threads()
    ]
    REVIEW_REPLIES_PATH.write_text(
        json.dumps({"replies": replies}, indent=2) + "\n",
        encoding="utf-8",
    )


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
        and thread.get("rootCommentId") is not None
        and thread.get("threadId") is not None
    ]


def _review_reply_text(
    *,
    thread: dict[str, object],
    result: dict[str, object],
    passed: bool,
) -> str:
    root_comment_id = thread.get("rootCommentId")
    if root_comment_id == 3291696660:
        return (
            "Fixed: the control precondition no longer hardcodes `# pass 3`. It now "
            "requires a clean baseline run with exit code `0`, a `# fail 0` TAP "
            "summary, and no `not ok` lines, so legitimate future subtest additions "
            "won't break TS-968."
        )

    if root_comment_id == 3291696699:
        if passed:
            return (
                "Fixed: `bug_description.md` is no longer emitted for every exception. "
                "The test now writes it only when the run reaches the real product-defect "
                "boundary: baseline pass, successful disposable mutation, visible expected "
                "assertion failure, and a wrong propagated exit code."
            )
        return (
            "Fixed: `bug_description.md` is now gated behind the real product-defect "
            "path only. This run still failed, but automation/setup failures no longer "
            "produce downstream product-bug payloads."
        )

    if root_comment_id == 3291709994:
        return (
            "Fixed: Step 2 no longer pins the mutated run to `# fail 1`. It now requires "
            "the expected failing subtest and assertion message, a failing TAP summary, "
            "and at least one visible `not ok` record, so future mutation-sensitive "
            "subtests will not create false negatives."
        )

    status = "passed" if passed else "failed"
    return (
        f"Addressed in TS-968 rework; the updated automation has been rerun and the new "
        f"status is `{status}`."
    )


if __name__ == "__main__":
    main()
