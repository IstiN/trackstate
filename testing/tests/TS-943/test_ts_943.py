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
from testing.tests.support.github_accessibility_engine_log_validation_failure_probe_factory import (  # noqa: E402
    create_github_accessibility_engine_log_validation_failure_probe,
    create_github_accessibility_engine_log_validation_run_log_reader,
)

TICKET_KEY = "TS-943"
TEST_CASE_TITLE = (
    "Integration suite log-validation - build fails when engine state tokens are missing"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-943/test_ts_943.py"
TEST_FILE_PATH = "testing/tests/TS-943/test_ts_943.py"
CONFIG_PATH = REPO_ROOT / "testing/tests/TS-943/config.yaml"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"

REQUEST_STEPS = [
    "Trigger the integration test suite for the accessibility module.",
    "Allow the process to complete the execution phase.",
    "Inspect the 'log-validation' step in the CI pipeline output.",
]
EXPECTED_RESULT = (
    "The 'log-validation' step fails, and the build status is set to 'Failed' "
    "because mandatory engine state tokens were not found in the output."
)
EXPECTED_FAILURE_CONCLUSION = "failure"
LOG_VALIDATION_STEP_PATTERN = re.compile(r"\blog[- ]validation\b", re.IGNORECASE)
MISSING_TOKEN_PATTERNS = (
    re.compile(r"mandatory[^\n]*engine state tokens[^\n]*(?:not found|missing)", re.IGNORECASE),
    re.compile(r"engine state tokens[^\n]*(?:not found|missing)", re.IGNORECASE),
    re.compile(r"missing[^\n]*engine state tokens", re.IGNORECASE),
    re.compile(r"flutter engine[^\n]*tokens[^\n]*(?:not found|missing)", re.IGNORECASE),
)


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    config = GitHubAccessibilityPullRequestGateConfig.from_file(CONFIG_PATH)
    probe = create_github_accessibility_engine_log_validation_failure_probe(
        REPO_ROOT,
        config_path=CONFIG_PATH,
    )
    log_reader = create_github_accessibility_engine_log_validation_run_log_reader(
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
        _evaluate_trigger(result, observation, failures)
        _evaluate_execution_phase(result, observation, failures)
        _evaluate_log_validation_output(
            result,
            observation,
            failures,
            full_run_log_text=full_run_log_text,
            full_run_log_error=full_run_log_error,
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
    print("TS-943 passed")


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


def _evaluate_trigger(
    result: dict[str, object],
    observation: GitHubAccessibilityPullRequestGateObservation,
    failures: list[str],
) -> None:
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
        if not path.startswith("testing/accessibility/")
    ]
    step_failures: list[str] = []
    if missing_files:
        step_failures.append(f"GitHub did not record the expected probe files: {missing_files}.")
    if unexpected_files:
        step_failures.append(
            "the disposable PR changed files outside `testing/accessibility/`, which means "
            f"the suppression scenario was not isolated: {unexpected_files}."
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
        "Created a disposable PR that suppresses the engine-state logging wrapper only "
        "through accessibility harness files and triggered the live PR workflow.\n"
        f"Pull Request URL: {observation.pull_request_url}\n"
        f"Observed PR files: {observation.pull_request_file_paths}\n"
        f"Workflow run URL: {observation.latest_pull_request_run_url}\n"
        f"Simulation technique: {observation.probe_contrast_technique}"
    )
    _record_step(result, step=1, status="passed", action=REQUEST_STEPS[0], observed=observed)


def _evaluate_execution_phase(
    result: dict[str, object],
    observation: GitHubAccessibilityPullRequestGateObservation,
    failures: list[str],
) -> None:
    step_failures: list[str] = []
    if observation.latest_pull_request_run_id is None:
        step_failures.append(
            "GitHub Actions did not expose a contributor-visible pull-request workflow run."
        )
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
            "the overall build did not finish in the expected failed state; observed run "
            f"conclusion was `{observation.latest_pull_request_run_conclusion or '<none>'}`."
        )
    if observation.accessibility_status_check_conclusion != EXPECTED_FAILURE_CONCLUSION:
        step_failures.append(
            "the contributor-visible accessibility status did not fail; observed conclusion "
            f"was `{observation.accessibility_status_check_conclusion or '<none>'}`."
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
            + "Accessibility check conclusion: "
            + f"{observation.accessibility_status_check_conclusion or '<none>'}\n"
            + f"Observed jobs: {observation.observed_job_names or ['<none>']}\n"
            + f"Observed steps: {observation.observed_step_names or ['<none>']}"
        )
        failures.append(message)
        _record_step(result, step=2, status="failed", action=REQUEST_STEPS[1], observed=message)
        return

    observed = (
        "Allowed the disposable PR workflow to finish and confirmed the build reached a "
        "failed conclusion, as a reviewer would expect for a missing-token contract.\n"
        f"Run URL: {observation.latest_pull_request_run_url}\n"
        f"Run status/conclusion: {observation.latest_pull_request_run_status}/{observation.latest_pull_request_run_conclusion}\n"
        f"Accessibility check conclusion: {observation.accessibility_status_check_conclusion or '<none>'}\n"
        f"Observed jobs: {observation.observed_job_names}\n"
        f"Observed steps: {observation.observed_step_names}"
    )
    _record_step(result, step=2, status="passed", action=REQUEST_STEPS[1], observed=observed)


def _evaluate_log_validation_output(
    result: dict[str, object],
    observation: GitHubAccessibilityPullRequestGateObservation,
    failures: list[str],
    *,
    full_run_log_text: str,
    full_run_log_error: str | None,
) -> None:
    step_failures: list[str] = []
    log_validation_step_output = _extract_log_validation_step_output(full_run_log_text)
    log_validation_visible = _has_log_validation_step(
        observation.observed_step_names,
        full_run_log_text,
    )
    missing_token_message = _extract_missing_token_message(log_validation_step_output)
    if full_run_log_error is not None:
        step_failures.append(
            f"the hosted run log could not be read: {full_run_log_error}."
        )
    if not log_validation_visible:
        step_failures.append(
            "the CI output did not expose a `log-validation` step in the contributor-visible workflow surface."
        )
    if missing_token_message is None:
        step_failures.append(
            "the CI output did not report that mandatory engine state tokens were missing."
        )
    if observation.flutter_engine_initialization_log_entries:
        step_failures.append(
            "the suppression scenario still emitted Flutter engine initialization lines, so "
            f"tokens were not actually absent: {observation.flutter_engine_initialization_log_entries}."
        )
    if observation.semantics_tree_discovery_log_entries:
        step_failures.append(
            "the suppression scenario still emitted semantics discovery lines, so the "
            f"expected missing-token condition was not reproduced: {observation.semantics_tree_discovery_log_entries}."
        )

    if step_failures:
        message = (
            "Step 3 failed: "
            + " ".join(step_failures)
            + "\n"
            + f"Run URL: {observation.latest_pull_request_run_url or '<none>'}\n"
            + f"Observed steps: {observation.observed_step_names or ['<none>']}\n"
            + f"Flutter engine log entries: {observation.flutter_engine_initialization_log_entries or ['<none>']}\n"
            + f"Semantics discovery log entries: {observation.semantics_tree_discovery_log_entries or ['<none>']}\n"
            + "log-validation step excerpt:\n"
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
        "Inspected the CI output and found the failing `log-validation` surface plus the "
        "expected missing-token error.\n"
        f"Run URL: {observation.latest_pull_request_run_url}\n"
        f"Observed steps: {observation.observed_step_names}\n"
        f"Missing-token message: {missing_token_message}"
    )
    _record_step(result, step=3, status="passed", action=REQUEST_STEPS[2], observed=observed)


def _record_live_user_verification(
    result: dict[str, object],
    observation: GitHubAccessibilityPullRequestGateObservation,
    *,
    full_run_log_text: str,
    full_run_log_error: str | None,
) -> None:
    log_validation_step_output = _extract_log_validation_step_output(full_run_log_text)
    _record_human_verification(
        result,
        check=(
            "Reviewed the same contributor-visible PR checks surface and workflow summary a "
            "human maintainer would use."
        ),
        observed=(
            f"PR checks URL: `{observation.pull_request_checks_url}`; run URL: "
            f"`{observation.latest_pull_request_run_url or '<none>'}`; jobs: "
            f"`{observation.observed_job_names or ['<none>']}`; steps: "
            f"`{observation.observed_step_names or ['<none>']}`; run conclusion: "
            f"`{observation.latest_pull_request_run_conclusion or '<none>'}`; accessibility "
            f"check conclusion: `{observation.accessibility_status_check_conclusion or '<none>'}`."
        ),
    )
    _record_human_verification(
        result,
        check=(
            "Read the hosted run log the way a reviewer would to look for the "
            "`log-validation` failure and the missing-token message."
        ),
        observed=(
            f"Log read error: `{full_run_log_error or '<none>'}`; missing-token message: "
            f"`{_extract_missing_token_message(log_validation_step_output) or '<none>'}`; Flutter "
            f"engine lines: `{observation.flutter_engine_initialization_summary or '<none>'}`; "
            f"semantics lines: `{observation.semantics_tree_discovery_summary or '<none>'}`; "
            f"log excerpt: `{_one_line(_extract_relevant_full_log_excerpt(full_run_log_text, observation=observation)) or '<none>'}`."
        ),
    )


def _has_log_validation_step(step_names: list[str], full_run_log_text: str) -> bool:
    if any(LOG_VALIDATION_STEP_PATTERN.search(name or "") for name in step_names):
        return True
    return any(
        LOG_VALIDATION_STEP_PATTERN.search(step_name)
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


def _extract_log_validation_step_output(full_run_log_text: str) -> str:
    lines: list[str] = []
    for raw_line in full_run_log_text.splitlines():
        parts = raw_line.lstrip("\ufeff").split("\t", 2)
        if len(parts) != 3:
            continue
        step_name = parts[1].strip()
        if not LOG_VALIDATION_STEP_PATTERN.search(step_name):
            continue
        payload = parts[2].strip()
        if payload:
            lines.append(payload)
    return "\n".join(lines)


def _extract_missing_token_message(text: str) -> str | None:
    for pattern in MISSING_TOKEN_PATTERNS:
        match = pattern.search(text)
        if match is not None:
            return _one_line(match.group(0))
    return None


def _extract_relevant_full_log_excerpt(
    full_run_log_text: str,
    *,
    observation: GitHubAccessibilityPullRequestGateObservation,
) -> str:
    log_validation_step_output = _extract_log_validation_step_output(full_run_log_text)
    if log_validation_step_output.strip():
        return _snippet(log_validation_step_output, limit=1600)
    if not full_run_log_text.strip():
        return observation.run_log_excerpt or ""

    lowered = full_run_log_text.lower()
    markers = [
        "log-validation",
        "log validation",
        "engine state tokens",
        "run axe-core accessibility checks",
        "accessibility checks",
        "flutter engine initialization",
        "semantics tree discovery",
        "accessibility runtime surface ready",
        "process completed with exit code 1",
    ]
    for marker in markers:
        index = lowered.find(marker)
        if index >= 0:
            start = max(index - 250, 0)
            end = min(index + 1250, len(full_run_log_text))
            return _snippet(full_run_log_text[start:end], limit=1600)
    return _snippet(full_run_log_text, limit=1600)


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
    error = str(result.get("error", "AssertionError: TS-943 failed"))
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
        "* Created a disposable pull request against the live repository that silences the accessibility engine-state logger only through {{testing/accessibility/}} changes.",
        "* Waited for the real {{Flutter Required Checks}} pull-request workflow to complete on GitHub Actions.",
        "* Inspected the contributor-visible workflow summary and full run log for a failing {{log-validation}} step plus a missing-engine-token error.",
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
        "- Created a disposable pull request against the live repository that silences the accessibility engine-state logger only through `testing/accessibility/` changes.",
        "- Waited for the real `Flutter Required Checks` pull-request workflow to complete on GitHub Actions.",
        "- Inspected the contributor-visible workflow summary and full run log for a failing `log-validation` step plus a missing-engine-token error.",
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
        "- Added TS-943 as a disposable PR probe against the live GitHub Actions accessibility workflow.",
        "- The probe suppresses the engine-state logger only through `testing/accessibility/` changes and checks whether CI fails for missing engine-state tokens.",
        f"- Test case: **{TICKET_KEY} - {TEST_CASE_TITLE}**",
        f"- Result: **{status}**",
        f"- Command: `{RUN_COMMAND}`",
        (
            f"- Environment: `{result['repository']}` @ `{result['default_branch']}` "
            f"using GitHub CLI on `{result['os']}`."
        ),
        (
            "- Outcome: the live CI surface rejected the missing engine-state tokens with a failing log-validation step."
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
        f"# {TICKET_KEY} - CI does not fail when engine-state log tokens are missing\n\n"
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
        "- **Actual:** The live disposable PR run completed without surfacing a failing "
        "`log-validation` step or an explicit missing-engine-token error even though the "
        "engine-state logging wrapper was silenced and the accessibility-stage log no "
        "longer contained the required engine/semantics tokens.\n\n"
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
        "- **Flutter engine log entries:**\n"
        "```text\n"
        f"{result.get('flutter_engine_initialization_log_entries', ['<none>'])}\n"
        "```\n"
        "- **Semantics discovery log entries:**\n"
        "```text\n"
        f"{result.get('semantics_tree_discovery_log_entries', ['<none>'])}\n"
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
