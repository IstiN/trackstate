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
from testing.tests.support.github_accessibility_log_validation_step_presence_probe_factory import (  # noqa: E402
    create_github_accessibility_log_validation_step_presence_probe,
    create_github_accessibility_log_validation_step_presence_run_log_reader,
)

TICKET_KEY = "TS-950"
TEST_CASE_TITLE = "CI workflow configuration - log-validation step presence is mandatory"
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-950/test_ts_950.py"
TEST_FILE_PATH = "testing/tests/TS-950/test_ts_950.py"
CONFIG_PATH = REPO_ROOT / "testing/tests/TS-950/config.yaml"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"

REQUEST_STEPS = [
    "Create a Pull Request with a workflow modification that removes the `log-validation` step from the accessibility job.",
    "Observe the CI pipeline status for the automated schema validation check.",
    "Confirm the failing schema validation prevents the pull request from being mergeable.",
]
EXPECTED_RESULT = (
    "The CI schema check fails, reports that the `log-validation` step is missing "
    "from the workflow configuration, and prevents the merge."
)
EXPECTED_FAILURE_CONCLUSION = "failure"
LOG_VALIDATION_STEP_PATTERN = re.compile(r"\blog[- ]validation\b", re.IGNORECASE)
MISSING_STEP_MESSAGE_PATTERNS = (
    re.compile(
        r"expected the accessibility workflow to expose a contributor-visible "
        r"`?log-validation`? step",
        re.IGNORECASE,
    ),
    re.compile(
        r"expected `?log-validation`? to run after the axe-core accessibility scan",
        re.IGNORECASE,
    ),
    re.compile(
        r"expected the `?log-validation`? step to invoke the accessibility log validator",
        re.IGNORECASE,
    ),
    re.compile(
        r"log-validation[^\n]*missing",
        re.IGNORECASE,
    ),
    re.compile(
        r"missing[^\n]*log-validation",
        re.IGNORECASE,
    ),
)


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    config = GitHubAccessibilityPullRequestGateConfig.from_file(CONFIG_PATH)
    probe = create_github_accessibility_log_validation_step_presence_probe(
        REPO_ROOT,
        config_path=CONFIG_PATH,
    )
    log_reader = create_github_accessibility_log_validation_step_presence_run_log_reader(
        REPO_ROOT
    )
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
        result["full_run_log_error"] = full_run_log_error
        result["full_run_log_excerpt"] = _extract_relevant_full_log_excerpt(
            full_run_log_text,
            observation=observation,
        )

        failures: list[str] = []
        _evaluate_pull_request_creation(result, observation, failures)
        _evaluate_schema_validation_failure(
            result,
            observation,
            failures,
            full_run_log_text=full_run_log_text,
            full_run_log_error=full_run_log_error,
        )
        _evaluate_merge_block(result, observation, failures)
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
    print("TS-950 passed")


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


def _evaluate_pull_request_creation(
    result: dict[str, object],
    observation: GitHubAccessibilityPullRequestGateObservation,
    failures: list[str],
) -> None:
    step_failures: list[str] = []
    expected_files = [observation.pull_request_probe_path]
    missing_files = [
        path for path in expected_files if path and path not in observation.pull_request_file_paths
    ]
    unexpected_files = [
        path
        for path in observation.pull_request_file_paths
        if path != observation.target_workflow_path
    ]
    if missing_files:
        step_failures.append(f"GitHub did not record the mutated workflow file: {missing_files}.")
    if unexpected_files:
        step_failures.append(
            "the disposable PR changed files outside the workflow contract under test: "
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
        "Created a disposable PR that removes only the workflow `log-validation` step and "
        "triggered the live pull-request CI run.\n"
        f"Pull Request URL: {observation.pull_request_url}\n"
        f"Observed PR files: {observation.pull_request_file_paths}\n"
        f"Workflow run URL: {observation.latest_pull_request_run_url}\n"
        f"Simulation technique: {observation.probe_contrast_technique}"
    )
    _record_step(result, step=1, status="passed", action=REQUEST_STEPS[0], observed=observed)


def _evaluate_schema_validation_failure(
    result: dict[str, object],
    observation: GitHubAccessibilityPullRequestGateObservation,
    failures: list[str],
    *,
    full_run_log_text: str,
    full_run_log_error: str | None,
) -> None:
    step_failures: list[str] = []
    missing_step_message = _extract_missing_step_message(full_run_log_text)
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
    if not observation.failed_status_check_names and not observation.failed_status_check_workflow_names:
        step_failures.append(
            "the contributor-visible PR checks surface did not show any failed status checks."
        )
    if full_run_log_error is not None:
        step_failures.append(f"the hosted run log could not be read: {full_run_log_error}.")
    if missing_step_message is None:
        step_failures.append(
            "the CI output did not report that the `log-validation` step was missing from the workflow contract."
        )

    if step_failures:
        message = (
            "Step 2 failed: "
            + " ".join(step_failures)
            + "\n"
            + f"Run URL: {observation.latest_pull_request_run_url or '<none>'}\n"
            + "Run status/conclusion: "
            + f"{observation.latest_pull_request_run_status or '<none>'}/"
            + f"{observation.latest_pull_request_run_conclusion or '<none>'}\n"
            + f"Observed failed status checks: {observation.failed_status_check_names or ['<none>']}\n"
            + "Observed failed workflows: "
            + f"{observation.failed_status_check_workflow_names or ['<none>']}\n"
            + "Full run log excerpt:\n"
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
        "Observed the live CI schema/contract validation fail after removing the workflow "
        "`log-validation` step.\n"
        f"Run URL: {observation.latest_pull_request_run_url}\n"
        f"Run status/conclusion: {observation.latest_pull_request_run_status}/{observation.latest_pull_request_run_conclusion}\n"
        f"Failed status checks: {observation.failed_status_check_names or ['<none>']}\n"
        f"Failed workflows: {observation.failed_status_check_workflow_names or ['<none>']}\n"
        f"Missing-step message: {missing_step_message}"
    )
    _record_step(result, step=2, status="passed", action=REQUEST_STEPS[1], observed=observed)


def _evaluate_merge_block(
    result: dict[str, object],
    observation: GitHubAccessibilityPullRequestGateObservation,
    failures: list[str],
) -> None:
    step_failures: list[str] = []
    if observation.pull_request_mergeable_state != "blocked":
        step_failures.append(
            "GitHub did not report the disposable pull request as merge-blocked after the "
            f"failing contract check; observed mergeable state was `{observation.pull_request_mergeable_state or '<none>'}`."
        )
    if not (
        observation.failed_status_check_names or observation.failed_status_check_workflow_names
    ):
        step_failures.append(
            "there were no failed contributor-visible status checks to justify a merge block."
        )

    if step_failures:
        message = (
            "Step 3 failed: "
            + " ".join(step_failures)
            + "\n"
            + f"Pull Request URL: {observation.pull_request_url}\n"
            + f"Checks URL: {observation.pull_request_checks_url}\n"
            + f"Mergeable state: {observation.pull_request_mergeable_state or '<none>'}\n"
            + f"Failed status checks: {observation.failed_status_check_names or ['<none>']}\n"
            + "Failed workflows: "
            + f"{observation.failed_status_check_workflow_names or ['<none>']}"
        )
        failures.append(message)
        _record_step(result, step=3, status="failed", action=REQUEST_STEPS[2], observed=message)
        return

    observed = (
        "Confirmed the disposable PR stayed merge-blocked after the failing schema validation "
        "surface appeared.\n"
        f"Pull Request URL: {observation.pull_request_url}\n"
        f"Checks URL: {observation.pull_request_checks_url}\n"
        f"Mergeable state: {observation.pull_request_mergeable_state}\n"
        f"Failed status checks: {observation.failed_status_check_names or ['<none>']}\n"
        f"Failed workflows: {observation.failed_status_check_workflow_names or ['<none>']}"
    )
    _record_step(result, step=3, status="passed", action=REQUEST_STEPS[2], observed=observed)


def _record_live_user_verification(
    result: dict[str, object],
    observation: GitHubAccessibilityPullRequestGateObservation,
    *,
    full_run_log_text: str,
    full_run_log_error: str | None,
) -> None:
    _record_human_verification(
        result,
        check=(
            "Reviewed the same contributor-visible PR checks and workflow summary a maintainer "
            "would use before merging."
        ),
        observed=(
            f"PR checks URL: `{observation.pull_request_checks_url}`; run URL: "
            f"`{observation.latest_pull_request_run_url or '<none>'}`; failed checks: "
            f"`{observation.failed_status_check_names or ['<none>']}`; failed workflows: "
            f"`{observation.failed_status_check_workflow_names or ['<none>']}`; mergeable "
            f"state: `{observation.pull_request_mergeable_state or '<none>'}`."
        ),
    )
    _record_human_verification(
        result,
        check=(
            "Read the hosted GitHub Actions log the way a reviewer would to confirm the "
            "workflow-contract failure reason."
        ),
        observed=(
            f"Log read error: `{full_run_log_error or '<none>'}`; missing-step message: "
            f"`{_extract_missing_step_message(full_run_log_text) or '<none>'}`; visible steps: "
            f"`{observation.observed_step_names or ['<none>']}`; log excerpt: "
            f"`{_one_line(_extract_relevant_full_log_excerpt(full_run_log_text, observation=observation)) or '<none>'}`."
        ),
    )


def _extract_missing_step_message(text: str) -> str | None:
    for pattern in MISSING_STEP_MESSAGE_PATTERNS:
        match = pattern.search(text)
        if match is not None:
            return _one_line(match.group(0))
    return None


def _extract_relevant_full_log_excerpt(
    full_run_log_text: str,
    *,
    observation: GitHubAccessibilityPullRequestGateObservation,
) -> str:
    if not full_run_log_text.strip():
        return observation.run_log_excerpt or ""

    lowered = full_run_log_text.lower()
    markers = [
        "log-validation",
        "contributor-visible",
        "workflow configuration",
        "unit-tests.yml",
        "run unit and golden tests",
        "process completed with exit code 1",
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


def _write_failure_outputs(result: dict[str, object]) -> None:
    error = str(result.get("error", "AssertionError: TS-950 failed"))
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
        "* Created a disposable pull request against the live repository that removes only the mandatory {{log-validation}} step from {{.github/workflows/unit-tests.yml}}.",
        "* Waited for the real {{Flutter Required Checks}} pull-request workflow to finish on GitHub Actions.",
        "* Inspected the contributor-visible workflow summary and hosted run log for an explicit missing-{{log-validation}} contract failure and merge-blocked PR state.",
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
        "- Created a disposable pull request against the live repository that removes only the mandatory `log-validation` step from `.github/workflows/unit-tests.yml`.",
        "- Waited for the real `Flutter Required Checks` pull-request workflow to finish on GitHub Actions.",
        "- Inspected the contributor-visible workflow summary and hosted run log for an explicit missing-`log-validation` contract failure and merge-blocked PR state.",
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
        "- Added TS-950 as a disposable PR probe against the live GitHub Actions workflow contract.",
        "- The probe removes the workflow `log-validation` step and checks whether CI reports the missing-step contract failure and blocks merge.",
        f"- Test case: **{TICKET_KEY} - {TEST_CASE_TITLE}**",
        f"- Result: **{status}**",
        f"- Command: `{RUN_COMMAND}`",
        (
            f"- Environment: `{result['repository']}` @ `{result['default_branch']}` "
            f"using GitHub CLI on `{result['os']}`."
        ),
        (
            "- Outcome: the live CI surface rejected the workflow change and blocked merge when the `log-validation` step was removed."
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
        f"# {TICKET_KEY} - CI does not reject workflow changes that remove the mandatory log-validation step\n\n"
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
        "- **Actual:** The live disposable PR did not expose a contributor-visible failing "
        "schema/contract message that the `log-validation` step was missing and/or did not "
        "leave the pull request merge-blocked after removing that step from "
        "`.github/workflows/unit-tests.yml`.\n\n"
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
        "- **Observed failed status checks:**\n"
        "```text\n"
        f"{result.get('failed_status_check_names', ['<none>'])}\n"
        "```\n"
        "- **Observed failed workflows:**\n"
        "```text\n"
        f"{result.get('failed_status_check_workflow_names', ['<none>'])}\n"
        "```\n"
        "- **Full workflow/log excerpt:**\n"
        "```text\n"
        f"{result.get('full_run_log_excerpt', '<missing log excerpt>')}\n"
        "```\n"
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
