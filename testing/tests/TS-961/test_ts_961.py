from __future__ import annotations

import json
import platform
import sys
import traceback
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.services.github_accessibility_compliant_pull_request_gate_probe import (  # noqa: E402
    GitHubAccessibilityCompliantPullRequestGateProbeService,
)
from testing.core.config.github_accessibility_pull_request_gate_config import (  # noqa: E402
    GitHubAccessibilityPullRequestGateConfig,
)
from testing.core.interfaces.github_accessibility_pull_request_gate_probe import (  # noqa: E402
    GitHubAccessibilityPullRequestGateObservation,
)
from testing.core.interfaces.github_workflow_run_log_reader import (  # noqa: E402
    GitHubWorkflowRunLogReader,
)
from testing.core.interfaces.github_workflow_step_sequence_inspector import (  # noqa: E402
    GitHubWorkflowRunStepObservation,
    GitHubWorkflowStepSequenceObservation,
)
from testing.tests.support.github_accessibility_compliant_pull_request_gate_probe_factory import (  # noqa: E402
    create_github_accessibility_compliant_pull_request_gate_probe,
)
from testing.tests.support.github_workflow_run_log_reader_factory import (  # noqa: E402
    create_github_workflow_run_log_reader,
)
from testing.tests.support.github_workflow_step_sequence_inspector_factory import (  # noqa: E402
    create_github_workflow_step_sequence_inspector,
)

TICKET_KEY = "TS-961"
TEST_CASE_TITLE = "Accessibility audit succeeds — log-validation step executes and passes"
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-961/test_ts_961.py"
TEST_FILE_PATH = "testing/tests/TS-961/test_ts_961.py"
CONFIG_PATH = REPO_ROOT / "testing/tests/TS-961/config.yaml"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"

REQUEST_STEPS = [
    "Trigger a CI run for a pull request that includes valid accessibility changes.",
    "Allow the 'Run axe-core accessibility checks' step to complete successfully.",
    "Observe the execution of the 'log-validation' step in the GitHub Actions workflow logs.",
]
EXPECTED_RESULT = (
    "The 'log-validation' step executes after the successful scan and returns a "
    "success status, indicating that mandatory logs were found and validated."
)
SUCCESS_CONCLUSIONS = {"success"}


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    raw_config = _load_yaml(CONFIG_PATH)
    runtime_inputs = raw_config.get("runtime_inputs", {})
    assert isinstance(runtime_inputs, dict)

    config = GitHubAccessibilityPullRequestGateConfig.from_file(CONFIG_PATH)
    probe = create_github_accessibility_compliant_pull_request_gate_probe(
        REPO_ROOT,
        config_path=CONFIG_PATH,
    )
    sequence_inspector = create_github_workflow_step_sequence_inspector(REPO_ROOT)
    log_reader = create_github_workflow_run_log_reader(REPO_ROOT)

    accessibility_job_name = _required_string(runtime_inputs, "accessibility_job_name")
    axe_step_name = _required_string(runtime_inputs, "axe_step_name")
    log_validation_step_name = _required_string(
        runtime_inputs,
        "log_validation_step_name",
    )
    success_log_markers = _string_list(
        runtime_inputs,
        "log_validation_success_markers",
        default=[
            "log-validation passed: mandatory engine state tokens were found in the output.",
        ],
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

        sequence = sequence_inspector.inspect(
            repository=config.repository,
            workflow_path=config.target_workflow_path,
            workflow_ref=config.base_branch,
            run_id=observation.latest_pull_request_run_id,
            accessibility_job_name=accessibility_job_name,
            axe_step_name=axe_step_name,
            log_validation_step_name=log_validation_step_name,
        )
        result["workflow_sequence"] = sequence.to_dict()

        full_run_log_text, full_run_log_error = _read_full_run_log(
            observation,
            log_reader=log_reader,
        )
        result["full_run_log_error"] = full_run_log_error
        result["full_run_log_excerpt"] = _extract_relevant_log_excerpt(
            full_run_log_text,
            markers=[*success_log_markers, log_validation_step_name],
        )

        failures: list[str] = []
        _evaluate_valid_accessibility_trigger(result, observation, failures)
        _evaluate_successful_axe_step(
            result,
            observation=observation,
            sequence=sequence,
            axe_step_name=axe_step_name,
            failures=failures,
        )
        _evaluate_log_validation_success(
            result,
            observation=observation,
            sequence=sequence,
            axe_step_name=axe_step_name,
            log_validation_step_name=log_validation_step_name,
            full_run_log_text=full_run_log_text,
            full_run_log_error=full_run_log_error,
            success_log_markers=success_log_markers,
            failures=failures,
        )
        _record_human_verification(
            result,
            observation=observation,
            sequence=sequence,
            axe_step_name=axe_step_name,
            log_validation_step_name=log_validation_step_name,
            success_log_markers=success_log_markers,
        )

        if failures:
            raise AssertionError("\n\n".join(failures))
    except Exception as error:
        result.setdefault("error", f"{type(error).__name__}: {error}")
        result.setdefault("traceback", traceback.format_exc())
        _write_failure_outputs(result)
        raise

    _write_pass_outputs(result)
    print("TS-961 passed")


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


def _evaluate_valid_accessibility_trigger(
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
    if missing_files:
        step_failures.append(
            f"GitHub did not record the expected disposable probe files: {missing_files}."
        )
    if not observation.probe_rendered_in_application:
        step_failures.append(
            "the disposable PR did not wire the compliant accessibility probe into a rendered application surface."
        )
    if observation.probe_contains_low_contrast_indicator:
        step_failures.append(
            "the disposable PR still contains the low-contrast indicator from the failing accessibility scenario."
        )
    if (
        observation.probe_semantic_label
        != GitHubAccessibilityCompliantPullRequestGateProbeService.expected_semantic_label
    ):
        step_failures.append(
            "the disposable PR did not preserve the expected descriptive semantics label."
        )
    if observation.latest_pull_request_run_id is None:
        step_failures.append(
            "GitHub Actions did not expose a contributor-visible pull-request workflow run."
        )
    if observation.latest_pull_request_run_event != "pull_request":
        step_failures.append(
            f"the observed workflow event was `{observation.latest_pull_request_run_event or '<none>'}` instead of `pull_request`."
        )

    if step_failures:
        message = (
            "Step 1 failed: "
            + " ".join(step_failures)
            + "\n"
            + f"Pull Request URL: {observation.pull_request_url}\n"
            + f"Observed PR files: {observation.pull_request_file_paths}\n"
            + f"Observed label: {observation.probe_semantic_label!r}\n"
            + f"Run URL: {observation.latest_pull_request_run_url or '<none>'}\n"
            + "Runtime accessibility evidence: "
            + f"{observation.runtime_accessibility_surface_summary or '<none>'}"
        )
        failures.append(message)
        _record_step(result, step=1, status="failed", action=REQUEST_STEPS[0], observed=message)
        return

    observed = (
        "Created a disposable PR with a rendered, WCAG-compliant accessibility probe and "
        "triggered the live pull-request workflow.\n"
        f"Pull Request URL: {observation.pull_request_url}\n"
        f"Observed PR files: {observation.pull_request_file_paths}\n"
        f"Observed label: {observation.probe_semantic_label!r}\n"
        f"Run URL: {observation.latest_pull_request_run_url}\n"
        f"Runtime accessibility evidence: {observation.runtime_accessibility_surface_summary or '<none>'}"
    )
    _record_step(result, step=1, status="passed", action=REQUEST_STEPS[0], observed=observed)


def _evaluate_successful_axe_step(
    result: dict[str, object],
    *,
    observation: GitHubAccessibilityPullRequestGateObservation,
    sequence: GitHubWorkflowStepSequenceObservation,
    axe_step_name: str,
    failures: list[str],
) -> None:
    step_failures: list[str] = []
    axe_step_run = sequence.axe_step_run

    if observation.latest_pull_request_run_status != "completed":
        step_failures.append(
            f"the workflow run never completed; observed status was `{observation.latest_pull_request_run_status or '<none>'}`."
        )
    if sequence.axe_step_contract is None:
        step_failures.append(
            f"the live workflow file did not expose the `{axe_step_name}` step in the accessibility job."
        )
    if axe_step_run is None:
        step_failures.append(
            f"the live workflow run did not expose the `{axe_step_name}` step in the accessibility job."
        )
    else:
        if (axe_step_run.status or "").lower() != "completed":
            step_failures.append(
                f"`{axe_step_name}` did not complete. Observed step summary: {_step_summary(axe_step_run)}."
            )
        if (axe_step_run.conclusion or "").lower() != "success":
            step_failures.append(
                f"`{axe_step_name}` did not succeed. Observed step summary: {_step_summary(axe_step_run)}."
            )
    if observation.accessibility_status_check_name and (
        observation.accessibility_status_check_conclusion or ""
    ).lower() != "success":
        step_failures.append(
            "the contributor-visible accessibility status check did not report success; "
            f"observed conclusion was `{observation.accessibility_status_check_conclusion or '<none>'}`."
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
            + f"Observed jobs: {sequence.observed_job_names or ['<none>']}\n"
            + f"Observed steps: {sequence.observed_step_names or ['<none>']}\n"
            + f"`{axe_step_name}` summary: {_step_summary(axe_step_run)}\n"
            + "Accessibility check conclusion: "
            + f"{observation.accessibility_status_check_conclusion or '<none>'}"
        )
        failures.append(message)
        _record_step(result, step=2, status="failed", action=REQUEST_STEPS[1], observed=message)
        return

    observed = (
        f"Allowed the live PR workflow to finish and confirmed `{axe_step_name}` completed "
        "with a success conclusion.\n"
        f"Run URL: {observation.latest_pull_request_run_url}\n"
        f"Run status/conclusion: {observation.latest_pull_request_run_status}/{observation.latest_pull_request_run_conclusion or '<none>'}\n"
        f"`{axe_step_name}` summary: {_step_summary(axe_step_run)}\n"
        f"Accessibility check conclusion: {observation.accessibility_status_check_conclusion or '<derived from step result>'}"
    )
    _record_step(result, step=2, status="passed", action=REQUEST_STEPS[1], observed=observed)


def _evaluate_log_validation_success(
    result: dict[str, object],
    *,
    observation: GitHubAccessibilityPullRequestGateObservation,
    sequence: GitHubWorkflowStepSequenceObservation,
    axe_step_name: str,
    log_validation_step_name: str,
    full_run_log_text: str,
    full_run_log_error: str | None,
    success_log_markers: list[str],
    failures: list[str],
) -> None:
    step_failures: list[str] = []
    axe_step_run = sequence.axe_step_run
    log_validation_contract = sequence.log_validation_step_contract
    log_validation_step_run = sequence.log_validation_step_run
    missing_log_markers = [
        marker for marker in success_log_markers if marker not in full_run_log_text
    ]

    if log_validation_contract is None:
        step_failures.append(
            f"the live workflow file did not expose the `{log_validation_step_name}` step in the accessibility job."
        )
    elif not log_validation_contract.uses_always:
        step_failures.append(
            "the live workflow file does not keep the `always()` contract on "
            f"`{log_validation_step_name}`. Observed `if:` value: "
            f"`{log_validation_contract.if_condition or '<none>'}`."
        )
    if log_validation_step_run is None:
        step_failures.append(
            f"the live workflow run did not expose the `{log_validation_step_name}` step."
        )
    else:
        if (log_validation_step_run.status or "").lower() != "completed":
            step_failures.append(
                f"`{log_validation_step_name}` did not complete. Observed step summary: {_step_summary(log_validation_step_run)}."
            )
        if (log_validation_step_run.conclusion or "").lower() != "success":
            step_failures.append(
                f"`{log_validation_step_name}` did not succeed. Observed step summary: {_step_summary(log_validation_step_run)}."
            )
    if (
        axe_step_run is not None
        and log_validation_step_run is not None
        and axe_step_run.number is not None
        and log_validation_step_run.number is not None
        and log_validation_step_run.number != axe_step_run.number + 1
    ):
        step_failures.append(
            f"`{log_validation_step_name}` was not immediately after `{axe_step_name}`. "
            f"Observed numbers: {axe_step_run.number} -> {log_validation_step_run.number}."
        )
    if full_run_log_error is not None:
        step_failures.append(f"the hosted workflow log could not be read: {full_run_log_error}.")
    if missing_log_markers:
        step_failures.append(
            "the hosted workflow log did not include the expected successful validator output. "
            f"Missing markers: {missing_log_markers}."
        )

    if step_failures:
        message = (
            "Step 3 failed: "
            + " ".join(step_failures)
            + "\n"
            + f"Workflow URL: {sequence.workflow_url}\n"
            + f"Workflow excerpt: {sequence.workflow_excerpt or '<none>'}\n"
            + f"Run URL: {observation.latest_pull_request_run_url or '<none>'}\n"
            + f"`{axe_step_name}` summary: {_step_summary(axe_step_run)}\n"
            + f"`{log_validation_step_name}` summary: {_step_summary(log_validation_step_run)}\n"
            + f"Full run log excerpt:\n{result.get('full_run_log_excerpt', '<none>')}"
        )
        failures.append(message)
        _record_step(result, step=3, status="failed", action=REQUEST_STEPS[2], observed=message)
        return

    observed = (
        f"Observed the live workflow contract and run log for `{log_validation_step_name}`, "
        f"which executed immediately after `{axe_step_name}` and completed successfully.\n"
        f"Workflow URL: {sequence.workflow_url}\n"
        f"Workflow excerpt: {sequence.workflow_excerpt}\n"
        f"`{axe_step_name}` summary: {_step_summary(axe_step_run)}\n"
        f"`{log_validation_step_name}` summary: {_step_summary(log_validation_step_run)}\n"
        f"Full run log excerpt:\n{result.get('full_run_log_excerpt', '<none>')}"
    )
    _record_step(result, step=3, status="passed", action=REQUEST_STEPS[2], observed=observed)


def _record_human_verification(
    result: dict[str, object],
    *,
    observation: GitHubAccessibilityPullRequestGateObservation,
    sequence: GitHubWorkflowStepSequenceObservation,
    axe_step_name: str,
    log_validation_step_name: str,
    success_log_markers: list[str],
) -> None:
    _record_human_line(
        result,
        check=(
            "Checked the contributor-visible PR checks surface and workflow metadata a reviewer "
            "would use to confirm the live run was for the disposable PR."
        ),
        observed=(
            f"PR checks URL: `{observation.pull_request_checks_url}`; run URL: "
            f"`{observation.latest_pull_request_run_url or '<none>'}`; observed status checks: "
            f"{observation.observed_status_check_names or ['<none>']}; observed jobs: "
            f"{sequence.observed_job_names or ['<none>']}; observed steps: "
            f"{sequence.observed_step_names or ['<none>']}; mergeable state: "
            f"`{observation.pull_request_mergeable_state or '<none>'}`."
        ),
    )
    _record_human_line(
        result,
        check=(
            "Compared the live workflow file on `main` with the run sequence to ensure "
            "`log-validation` still sits directly after the axe-core scan under an `always()` guard."
        ),
        observed=(
            f"Workflow URL: `{sequence.workflow_url}`; workflow excerpt: "
            f"`{sequence.workflow_excerpt or '<none>'}`; `{axe_step_name}` summary: "
            f"`{_step_summary(sequence.axe_step_run)}`; `{log_validation_step_name}` summary: "
            f"`{_step_summary(sequence.log_validation_step_run)}`; `if:` condition: "
            f"`{None if sequence.log_validation_step_contract is None else sequence.log_validation_step_contract.if_condition}`."
        ),
    )
    _record_human_line(
        result,
        check=(
            "Read the live workflow log as a user would and verified the validator success text "
            "that indicates mandatory logs were found."
        ),
        observed=(
            f"Expected success markers: {success_log_markers}; runtime accessibility evidence: "
            f"`{observation.runtime_accessibility_surface_summary or '<none>'}`; log excerpt: "
            f"`{result.get('full_run_log_excerpt', '<none>')}`."
        ),
    )


def _extract_relevant_log_excerpt(text: str, *, markers: list[str], radius: int = 12) -> str:
    lines = text.splitlines()
    if not lines:
        return ""

    normalized_markers = [marker.lower() for marker in markers if marker.strip()]
    for marker in normalized_markers:
        for index, line in enumerate(lines):
            if marker in line.lower():
                start = max(index - radius, 0)
                end = min(index + radius + 1, len(lines))
                return "\n".join(lines[start:end])
    return "\n".join(lines[: min(len(lines), radius * 2)])


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
    error = str(result.get("error", "AssertionError: TS-961 failed"))
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
        "* Created a disposable pull request against the live repository with valid accessibility changes only.",
        "* Verified the live workflow contract for {{Run axe-core accessibility checks}} and {{log-validation}} on {{main}}.",
        "* Read the contributor-visible run jobs, step sequence, and full workflow log for the disposable PR run.",
        "* Confirmed the validator success message that proves mandatory logs were found.",
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
        "- Created a disposable pull request against the live repository with valid accessibility changes only.",
        "- Verified the live workflow contract for `Run axe-core accessibility checks` and `log-validation` on `main`.",
        "- Read the contributor-visible run jobs, step sequence, and full workflow log for the disposable PR run.",
        "- Confirmed the validator success message that proves mandatory logs were found.",
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
    rerun_summary = (
        f"Re-ran `{RUN_COMMAND}`: passed (`1 passed, 0 failed`)."
        if passed
        else f"Re-ran `{RUN_COMMAND}`: failed with `{result.get('error')}`."
    )
    lines = [
        "## Test Automation Result",
        "",
        f"- **Test Case:** {TICKET_KEY} - {TEST_CASE_TITLE}",
        f"- **Status:** {status}",
        f"- **Test Run:** `{RUN_COMMAND}`",
        f"- **Summary:** {rerun_summary}",
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
    return "\n".join(lines).strip() + "\n"


def _bug_description(result: dict[str, object]) -> str:
    step_map = {
        int(step["step"]): step
        for step in result.get("steps", [])
        if isinstance(step, dict) and isinstance(step.get("step"), int)
    }
    sequence = result.get("workflow_sequence") or {}
    return (
        f"# {TICKET_KEY} - log-validation does not execute successfully after a successful accessibility scan\n\n"
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
        "- **Actual:** The disposable PR reached the live GitHub Actions workflow surface, but "
        "`log-validation` either did not run immediately after the successful axe-core step, did "
        "not finish with a success conclusion, or the workflow log did not contain the validator "
        "success message showing that mandatory engine-state logs were found.\n\n"
        "## Environment details\n"
        f"- **URL:** {result.get('pull_request_url', '<missing pull request URL>')}\n"
        "- **Client:** GitHub CLI for live workflow/API inspection\n"
        f"- **OS:** {result.get('os')}\n"
        f"- **Repository:** {result.get('repository')}\n"
        f"- **Branch:** {result.get('default_branch')}\n"
        f"- **PR checks URL:** {result.get('pull_request_checks_url', '<missing checks URL>')}\n"
        f"- **Workflow run URL:** {result.get('latest_pull_request_run_url', '<missing run URL>')}\n"
        f"- **Workflow file URL:** {sequence.get('workflow_url', '<missing workflow URL>')}\n"
        f"- **Run command:** `{result.get('run_command')}`\n"
        f"- **Config:** `{CONFIG_PATH}`\n\n"
        "## Screenshots or logs\n"
        f"- **Workflow excerpt:** `{sequence.get('workflow_excerpt', '<none>')}`\n"
        f"- **Full run log excerpt:** `{result.get('full_run_log_excerpt', '<none>')}`\n"
        f"- **Axe step summary:** `{_step_summary_from_mapping(sequence.get('axe_step_run'))}`\n"
        f"- **log-validation step summary:** `{_step_summary_from_mapping(sequence.get('log_validation_step_run'))}`\n"
        f"- **Runtime accessibility evidence:** `{result.get('runtime_accessibility_surface_summary', '<none>')}`\n"
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


def _record_human_line(result: dict[str, object], *, check: str, observed: str) -> None:
    human_verification = result.setdefault("human_verification", [])
    assert isinstance(human_verification, list)
    human_verification.append({"check": check, "observed": observed})


def _human_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for item in result.get("human_verification", []):
        if not isinstance(item, dict):
            continue
        check = str(item.get("check", "")).strip()
        observed = str(item.get("observed", "")).strip()
        prefix = "*" if jira else "-"
        lines.append(f"{prefix} {check}")
        lines.append(f"{prefix} Observed: {observed}")
    return lines or (["* <none recorded>"] if jira else ["- <none recorded>"])


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for item in result.get("steps", []):
        if not isinstance(item, dict):
            continue
        prefix = "*" if jira else "-"
        lines.append(
            f"{prefix} Step {item.get('step')}: {str(item.get('status', '')).upper()} — "
            f"{item.get('action', '')}"
        )
        lines.append(f"{prefix} Observed: {item.get('observed', '')}")
    return lines or (["* <none recorded>"] if jira else ["- <none recorded>"])


def _failed_step_summary(result: dict[str, object]) -> str:
    failed_steps = [
        f"Step {item.get('step')}"
        for item in result.get("steps", [])
        if isinstance(item, dict) and item.get("status") != "passed"
    ]
    return ", ".join(failed_steps) if failed_steps else "No individual failing step was recorded."


def _step_summary(step: GitHubWorkflowRunStepObservation | None) -> str:
    if step is None:
        return "<none>"
    return (
        f"job={step.job_name!r}, step={step.step_name!r}, number={step.number}, "
        f"status={step.status!r}, conclusion={step.conclusion!r}, "
        f"started_at={step.started_at!r}, completed_at={step.completed_at!r}"
    )


def _step_summary_from_mapping(payload: object) -> str:
    if not isinstance(payload, dict):
        return "<none>"
    return (
        f"job={payload.get('job_name')!r}, step={payload.get('step_name')!r}, "
        f"number={payload.get('number')!r}, status={payload.get('status')!r}, "
        f"conclusion={payload.get('conclusion')!r}, started_at={payload.get('started_at')!r}, "
        f"completed_at={payload.get('completed_at')!r}"
    )


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must deserialize to a mapping.")
    return payload


def _required_string(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"runtime_inputs.{key} must be a non-empty string.")
    return value.strip()


def _string_list(
    payload: dict[str, object],
    key: str,
    *,
    default: list[str],
) -> list[str]:
    value = payload.get(key, default)
    if not isinstance(value, list):
        return list(default)
    strings = [str(entry).strip() for entry in value if str(entry).strip()]
    return strings or list(default)


if __name__ == "__main__":
    main()
