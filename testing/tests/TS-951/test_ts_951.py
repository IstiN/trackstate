from __future__ import annotations

from dataclasses import asdict
import json
import platform
import re
import sys
import traceback
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.github_actions_page import GitHubActionsPageObservation  # noqa: E402
from testing.core.config.github_accessibility_pull_request_gate_config import (  # noqa: E402
    GitHubAccessibilityPullRequestGateConfig,
)
from testing.core.interfaces.github_accessibility_pull_request_gate_probe import (  # noqa: E402
    GitHubAccessibilityPullRequestGateObservation,
)
from testing.core.interfaces.github_workflow_step_sequence_inspector import (  # noqa: E402
    GitHubWorkflowRunStepObservation,
    GitHubWorkflowStepSequenceObservation,
)
from testing.tests.support.github_accessibility_early_engine_crash_probe_factory import (  # noqa: E402
    create_github_accessibility_early_engine_crash_probe,
)
from testing.tests.support.github_actions_page_factory import (  # noqa: E402
    create_github_actions_page,
)
from testing.tests.support.github_workflow_step_sequence_inspector_factory import (  # noqa: E402
    create_github_workflow_step_sequence_inspector,
)

TICKET_KEY = "TS-951"
TEST_CASE_TITLE = "Accessibility audit fails — log-validation step executes regardless"
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-951/test_ts_951.py"
TEST_FILE_PATH = "testing/tests/TS-951/test_ts_951.py"
CONFIG_PATH = REPO_ROOT / "testing/tests/TS-951/config.yaml"
OUTPUTS_DIR = REPO_ROOT / "outputs"
DISCUSSIONS_RAW_PATH = REPO_ROOT / "input" / TICKET_KEY / "pr_discussions_raw.json"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
REVIEW_REPLIES_PATH = OUTPUTS_DIR / "review_replies.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
RUN_SCREENSHOT_PATH = OUTPUTS_DIR / "ts951_run_page.png"
WORKFLOW_SCREENSHOT_PATH = OUTPUTS_DIR / "ts951_workflow_page.png"

REQUEST_STEPS = [
    "Trigger a CI run where the 'Run axe-core accessibility checks' step is forced to fail (e.g., by providing an invalid environment variable or corrupted input).",
    "Observe the workflow execution sequence in the GitHub Actions UI.",
]
EXPECTED_RESULT = (
    "The 'log-validation' step is executed despite the 'Run axe-core accessibility "
    "checks' step having a failure status, ensuring logs are still validated."
)
FAILURE_CONCLUSIONS = {"failure", "cancelled", "timed_out", "action_required"}
ALWAYS_PATTERN = re.compile(r"\balways\s*\(", re.IGNORECASE)


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    raw_config = _load_yaml(CONFIG_PATH)
    runtime_inputs = raw_config.get("runtime_inputs", {})
    assert isinstance(runtime_inputs, dict)
    config = GitHubAccessibilityPullRequestGateConfig.from_file(CONFIG_PATH)
    probe = create_github_accessibility_early_engine_crash_probe(
        REPO_ROOT,
        config_path=CONFIG_PATH,
    )
    sequence_inspector = create_github_workflow_step_sequence_inspector(REPO_ROOT)

    ui_timeout_seconds = _positive_int(runtime_inputs, "ui_timeout_seconds", default=60)
    accessibility_job_name = _required_string(runtime_inputs, "accessibility_job_name")
    axe_step_name = _required_string(runtime_inputs, "axe_step_name")
    log_validation_step_name = _required_string(
        runtime_inputs,
        "log_validation_step_name",
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
        "browser": "Chromium (Playwright)",
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

        run_page, run_page_error = _open_run_page(
            observation=observation,
            sequence=sequence,
            timeout_seconds=ui_timeout_seconds,
        )
        workflow_page, workflow_page_error = _open_workflow_page(
            sequence=sequence,
            axe_step_name=axe_step_name,
            log_validation_step_name=log_validation_step_name,
            timeout_seconds=ui_timeout_seconds,
        )
        result["run_page"] = None if run_page is None else asdict(run_page)
        result["run_page_error"] = run_page_error
        result["workflow_page"] = None if workflow_page is None else asdict(workflow_page)
        result["workflow_page_error"] = workflow_page_error

        failures: list[str] = []
        _evaluate_forced_failure_trigger(result, observation, failures)
        _evaluate_execution_sequence(
            result,
            observation=observation,
            sequence=sequence,
            run_page=run_page,
            run_page_error=run_page_error,
            workflow_page=workflow_page,
            workflow_page_error=workflow_page_error,
            axe_step_name=axe_step_name,
            log_validation_step_name=log_validation_step_name,
            failures=failures,
        )
        _record_human_verification(
            result,
            observation=observation,
            sequence=sequence,
            run_page=run_page,
            run_page_error=run_page_error,
            workflow_page=workflow_page,
            workflow_page_error=workflow_page_error,
            axe_step_name=axe_step_name,
            log_validation_step_name=log_validation_step_name,
        )

        if failures:
            raise AssertionError("\n\n".join(failures))
    except Exception as error:
        result.setdefault("error", f"{type(error).__name__}: {error}")
        result.setdefault("traceback", traceback.format_exc())
        _write_failure_outputs(result)
        raise

    _write_pass_outputs(result)
    print("TS-951 passed")


def _evaluate_forced_failure_trigger(
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
    if observation.latest_pull_request_run_conclusion not in FAILURE_CONCLUSIONS:
        step_failures.append(
            "the forced accessibility-failure scenario did not produce a failing workflow run; "
            f"observed conclusion was `{observation.latest_pull_request_run_conclusion or '<none>'}`."
        )
    if not observation.run_log_matched_contrast_markers:
        step_failures.append(
            "the hosted log did not expose contrast/accessibility failure markers, so the "
            "axe-core failure reproduction was not visible."
        )

    if step_failures:
        message = (
            "Step 1 failed: "
            + " ".join(step_failures)
            + "\n"
            + f"Pull Request URL: {observation.pull_request_url}\n"
            + f"Observed PR files: {observation.pull_request_file_paths}\n"
            + f"Run URL: {observation.latest_pull_request_run_url or '<none>'}\n"
            + f"Run status/conclusion: {observation.latest_pull_request_run_status or '<none>'}/"
            + f"{observation.latest_pull_request_run_conclusion or '<none>'}\n"
            + f"Run-log contrast markers: {observation.run_log_matched_contrast_markers or ['<none>']}\n"
            + f"Run log excerpt:\n{observation.run_log_excerpt or '<none>'}"
        )
        failures.append(message)
        _record_step(result, step=1, status="failed", action=REQUEST_STEPS[0], observed=message)
        return

    observed = (
        "Created a disposable PR that forces a real accessibility scan failure and waited "
        "for the live PR workflow to finish.\n"
        f"Pull Request URL: {observation.pull_request_url}\n"
        f"Observed PR files: {observation.pull_request_file_paths}\n"
        f"Run URL: {observation.latest_pull_request_run_url}\n"
        f"Run status/conclusion: {observation.latest_pull_request_run_status}/{observation.latest_pull_request_run_conclusion}\n"
        f"Run-log contrast markers: {observation.run_log_matched_contrast_markers}\n"
        f"Run log excerpt:\n{observation.run_log_excerpt or '<none>'}"
    )
    _record_step(result, step=1, status="passed", action=REQUEST_STEPS[0], observed=observed)


def _evaluate_execution_sequence(
    result: dict[str, object],
    *,
    observation: GitHubAccessibilityPullRequestGateObservation,
    sequence: GitHubWorkflowStepSequenceObservation,
    run_page: GitHubActionsPageObservation | None,
    run_page_error: str | None,
    workflow_page: GitHubActionsPageObservation | None,
    workflow_page_error: str | None,
    axe_step_name: str,
    log_validation_step_name: str,
    failures: list[str],
) -> None:
    step_failures: list[str] = []
    log_validation_contract = sequence.log_validation_step_contract
    axe_step_run = sequence.axe_step_run
    log_validation_step_run = sequence.log_validation_step_run

    if sequence.axe_step_contract is None:
        step_failures.append(
            f"the live workflow file did not expose the `{axe_step_name}` step in the accessibility job."
        )
    if log_validation_contract is None:
        step_failures.append(
            f"the live workflow file did not expose the `{log_validation_step_name}` step in the accessibility job."
        )
    elif not log_validation_contract.uses_always:
        step_failures.append(
            "the live workflow file does not configure `log-validation` with an `always()` "
            "conditional. "
            f"Observed `if:` value: `{log_validation_contract.if_condition or '<none>'}`."
        )

    if axe_step_run is None:
        step_failures.append(
            f"the live workflow run did not expose the `{axe_step_name}` step in the accessibility job."
        )
    elif (axe_step_run.conclusion or "").lower() != "failure":
        step_failures.append(
            "the live run did not show `Run axe-core accessibility checks` with a failure "
            f"status. Observed step summary: {_step_summary(axe_step_run)}."
        )

    if log_validation_step_run is None:
        step_failures.append(
            f"the live workflow run did not expose the `{log_validation_step_name}` step after the forced accessibility failure."
        )
    elif (log_validation_step_run.status or "").lower() != "completed":
        step_failures.append(
            "the live run exposed `log-validation`, but it did not complete. "
            f"Observed step summary: {_step_summary(log_validation_step_run)}."
        )

    if (
        axe_step_run is not None
        and log_validation_step_run is not None
        and axe_step_run.number is not None
        and log_validation_step_run.number is not None
        and log_validation_step_run.number != axe_step_run.number + 1
    ):
        step_failures.append(
            "the live run exposed both steps, but `log-validation` was not immediately after "
            f"`Run axe-core accessibility checks`. Observed numbers: "
            f"{axe_step_run.number} -> {log_validation_step_run.number}."
        )

    if run_page is None:
        step_failures.append(
            "the GitHub Actions run page could not be opened for contributor-visible verification. "
            f"Error: {run_page_error or '<none>'}."
        )
    if workflow_page is None:
        step_failures.append(
            "the live workflow file page could not be opened for contributor-visible verification. "
            f"Error: {workflow_page_error or '<none>'}."
        )

    if step_failures:
        message = (
            "Step 2 failed: "
            + " ".join(step_failures)
            + "\n"
            + f"Workflow URL: {sequence.workflow_url}\n"
            + f"Workflow excerpt: {sequence.workflow_excerpt or '<none>'}\n"
            + f"Run URL: {observation.latest_pull_request_run_url or '<none>'}\n"
            + f"Observed jobs: {sequence.observed_job_names or ['<none>']}\n"
            + f"Observed steps: {sequence.observed_step_names or ['<none>']}\n"
            + f"`{axe_step_name}` summary: {_step_summary(axe_step_run)}\n"
            + f"`{log_validation_step_name}` summary: {_step_summary(log_validation_step_run)}\n"
            + f"Run page screenshot: {None if run_page is None else run_page.screenshot_path}\n"
            + f"Workflow page screenshot: {None if workflow_page is None else workflow_page.screenshot_path}"
        )
        failures.append(message)
        _record_step(result, step=2, status="failed", action=REQUEST_STEPS[1], observed=message)
        return

    observed = (
        "Observed the live workflow sequence and confirmed the workflow file and run page "
        "show `log-validation` executing after a failing axe-core step.\n"
        f"Workflow URL: {sequence.workflow_url}\n"
        f"Workflow excerpt: {sequence.workflow_excerpt}\n"
        f"Run URL: {observation.latest_pull_request_run_url}\n"
        f"`{axe_step_name}` summary: {_step_summary(axe_step_run)}\n"
        f"`{log_validation_step_name}` summary: {_step_summary(log_validation_step_run)}\n"
        f"Run page screenshot: {None if run_page is None else run_page.screenshot_path}\n"
        f"Workflow page screenshot: {None if workflow_page is None else workflow_page.screenshot_path}"
    )
    _record_step(result, step=2, status="passed", action=REQUEST_STEPS[1], observed=observed)


def _record_human_verification(
    result: dict[str, object],
    *,
    observation: GitHubAccessibilityPullRequestGateObservation,
    sequence: GitHubWorkflowStepSequenceObservation,
    run_page: GitHubActionsPageObservation | None,
    run_page_error: str | None,
    workflow_page: GitHubActionsPageObservation | None,
    workflow_page_error: str | None,
    axe_step_name: str,
    log_validation_step_name: str,
) -> None:
    _record_human_line(
        result,
        check=(
            "Opened the live GitHub Actions run page a reviewer would use and checked the "
            "visible workflow/job labels."
        ),
        observed=(
            f"Run URL: `{observation.latest_pull_request_run_url or '<none>'}`; page error: "
            f"`{run_page_error or '<none>'}`; matched text: "
            f"`{None if run_page is None else run_page.matched_text}`; screenshot: "
            f"`{None if run_page is None else run_page.screenshot_path}`; visible body excerpt: "
            f"`{_snippet('' if run_page is None else run_page.body_text, limit=900)}`."
        ),
    )
    _record_human_line(
        result,
        check=(
            "Opened the live workflow file page and checked the visible `log-validation` "
            "condition text a maintainer would review."
        ),
        observed=(
            f"Workflow URL: `{sequence.workflow_url}`; page error: "
            f"`{workflow_page_error or '<none>'}`; screenshot: "
            f"`{None if workflow_page is None else workflow_page.screenshot_path}`; "
            f"`{log_validation_step_name}` if-condition: "
            f"`{None if sequence.log_validation_step_contract is None else sequence.log_validation_step_contract.if_condition}`; "
            f"`always()` present: "
            f"`{None if sequence.log_validation_step_contract is None else sequence.log_validation_step_contract.uses_always}`; "
            f"visible body excerpt: "
            f"`{_snippet('' if workflow_page is None else workflow_page.body_text, limit=900)}`."
        ),
    )
    _record_human_line(
        result,
        check=(
            "Compared the contributor-visible step sequence to the ticket expectation from a "
            "user perspective."
        ),
        observed=(
            f"`{axe_step_name}` summary: `{_step_summary(sequence.axe_step_run)}`; "
            f"`{log_validation_step_name}` summary: "
            f"`{_step_summary(sequence.log_validation_step_run)}`; run conclusion: "
            f"`{observation.latest_pull_request_run_conclusion or '<none>'}`; "
            f"workflow excerpt: `{sequence.workflow_excerpt or '<none>'}`."
        ),
    )


def _open_run_page(
    *,
    observation: GitHubAccessibilityPullRequestGateObservation,
    sequence: GitHubWorkflowStepSequenceObservation,
    timeout_seconds: int,
) -> tuple[GitHubActionsPageObservation | None, str | None]:
    if observation.latest_pull_request_run_url is None:
        return None, "Workflow run URL is missing."
    expected_texts = [
        observation.target_workflow_name,
        *(sequence.observed_job_names[:4]),
        "Accessibility checks",
        "log-validation",
    ]
    try:
        with create_github_actions_page() as actions_page:
            return (
                actions_page.open_page(
                    url=observation.latest_pull_request_run_url,
                    expected_texts=tuple(dict.fromkeys(text for text in expected_texts if text)),
                    screenshot_path=str(RUN_SCREENSHOT_PATH),
                    timeout_seconds=timeout_seconds,
                ),
                None,
            )
    except Exception as error:  # noqa: BLE001
        return None, f"{type(error).__name__}: {error}"


def _open_workflow_page(
    *,
    sequence: GitHubWorkflowStepSequenceObservation,
    axe_step_name: str,
    log_validation_step_name: str,
    timeout_seconds: int,
) -> tuple[GitHubActionsPageObservation | None, str | None]:
    expected_texts = [
        axe_step_name,
        log_validation_step_name,
        "Accessibility checks",
        "if:",
    ]
    try:
        with create_github_actions_page() as actions_page:
            return (
                actions_page.open_page(
                    url=sequence.workflow_url,
                    expected_texts=tuple(dict.fromkeys(expected_texts)),
                    screenshot_path=str(WORKFLOW_SCREENSHOT_PATH),
                    timeout_seconds=timeout_seconds,
                ),
                None,
            )
    except Exception as error:  # noqa: BLE001
        return None, f"{type(error).__name__}: {error}"


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must deserialize to a mapping.")
    return payload


def _positive_int(payload: dict[str, object], key: str, *, default: int) -> int:
    value = payload.get(key, default)
    return value if isinstance(value, int) and value > 0 else default


def _required_string(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"runtime_inputs.{key} must be a non-empty string.")
    return value.strip()


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
    _write_review_replies(result, passed=True)


def _write_failure_outputs(result: dict[str, object]) -> None:
    error = str(result.get("error", "AssertionError: TS-951 failed"))
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
    _write_review_replies(result, passed=False)
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
        "* Created a disposable pull request against the live repository to force a real accessibility scan failure in the PR workflow.",
        "* Read the live workflow file from GitHub and inspected the accessibility job step contract for {{log-validation}}.",
        "* Read the live workflow run step sequence for {{Run axe-core accessibility checks}} and {{log-validation}}.",
        "* Opened the contributor-visible run page and workflow file page for human-style verification text evidence.",
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
            f"{{{{{result['default_branch']}}}}}, browser {{{{{result['browser']}}}}}, "
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
        "- Created a disposable pull request against the live repository to force a real accessibility scan failure in the PR workflow.",
        "- Read the live workflow file from GitHub and inspected the accessibility job step contract for `log-validation`.",
        "- Read the live workflow run step sequence for `Run axe-core accessibility checks` and `log-validation`.",
        "- Opened the contributor-visible run page and workflow file page for human-style verification text evidence.",
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
            f"`{result['default_branch']}`, browser `{result['browser']}`, OS `{result['os']}`."
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
    status = "✅ PASSED" if passed else "❌ FAILED"
    rerun_summary = (
        f"Re-ran `{RUN_COMMAND}`: passed (`1 passed, 0 failed`)."
        if passed
        else f"Re-ran `{RUN_COMMAND}`: failed with `{result.get('error')}`."
    )
    lines = [
        "h3. PR Rework Result",
        "",
        "*Fixed:* Removed the direct `UrllibWebAppRuntime` injection so the GitHub Actions page checks now stay on the standard Playwright-backed factory path, and added `testing/tests/TS-951/README.md`.",
        f"*Test Run:* `{RUN_COMMAND}`",
        f"*Result:* {status}",
        f"*Summary:* {rerun_summary}",
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
    return "\n".join(lines).strip() + "\n"


def _bug_description(result: dict[str, object]) -> str:
    step_map = {
        int(step["step"]): step
        for step in result.get("steps", [])
        if isinstance(step, dict) and isinstance(step.get("step"), int)
    }
    run_page = result.get("run_page") or {}
    workflow_page = result.get("workflow_page") or {}
    sequence = result.get("workflow_sequence") or {}
    return (
        f"# {TICKET_KEY} - log-validation does not run under an always() contract after axe failure\n\n"
        "## Steps to reproduce\n"
        f"1. {REQUEST_STEPS[0]}  \n"
        f"   - Actual: {step_map.get(1, {}).get('observed', '<missing>')}  \n"
        f"   - Result: {'PASSED ✅' if step_map.get(1, {}).get('status') == 'passed' else 'FAILED ❌'}\n"
        f"2. {REQUEST_STEPS[1]}  \n"
        f"   - Actual: {step_map.get(2, {}).get('observed', '<missing>')}  \n"
        f"   - Result: {'PASSED ✅' if step_map.get(2, {}).get('status') == 'passed' else 'FAILED ❌'}\n\n"
        "## Exact error message or assertion failure\n"
        "```text\n"
        f"{result.get('traceback', result.get('error', '<missing>'))}"
        "```\n\n"
        "## Actual vs Expected\n"
        f"- **Expected:** {EXPECTED_RESULT}\n"
        "- **Actual:** The live workflow file still defines `log-validation` with "
        "``if: steps.changes.outputs.accessibility == 'true'`` instead of an "
        "`always()` guard, and the live disposable PR run shows `Run axe-core accessibility "
        "checks` as non-failing/success while `log-validation` fails later. The contributor-visible "
        "sequence therefore does not prove that `log-validation` runs after a failed axe step.\n\n"
        "## Environment details\n"
        f"- **URL:** {result.get('pull_request_url', '<missing pull request URL>')}\n"
        "- **Browser:** Chromium via Playwright for page verification; GitHub CLI for API/run data\n"
        f"- **OS:** {result.get('os')}\n"
        f"- **Repository:** {result.get('repository')}\n"
        f"- **Branch:** {result.get('default_branch')}\n"
        f"- **PR checks URL:** {result.get('pull_request_checks_url', '<missing checks URL>')}\n"
        f"- **Workflow run URL:** {result.get('latest_pull_request_run_url', '<missing run URL>')}\n"
        f"- **Workflow file URL:** {sequence.get('workflow_url', '<missing workflow URL>')}\n"
        f"- **Run command:** `{result.get('run_command')}`\n"
        f"- **Config:** `{CONFIG_PATH}`\n\n"
        "## Screenshots or logs\n"
        f"- **Run page screenshot:** `{run_page.get('screenshot_path', '<none>')}`\n"
        f"- **Workflow page screenshot:** `{workflow_page.get('screenshot_path', '<none>')}`\n"
        f"- **Workflow excerpt:** `{sequence.get('workflow_excerpt', '<none>')}`\n"
        f"- **Run log excerpt:** `{result.get('run_log_excerpt', '<none>')}`\n"
        f"- **Axe step summary:** `{_step_summary_from_mapping(sequence.get('axe_step_run'))}`\n"
        f"- **log-validation step summary:** `{_step_summary_from_mapping(sequence.get('log_validation_step_run'))}`\n"
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


def _write_review_replies(result: dict[str, object], *, passed: bool) -> None:
    replies = [
        {
            "inReplyToId": thread.get("rootCommentId"),
            "threadId": thread.get("threadId"),
            "reply": _review_reply_text(result, passed=passed),
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
        "Fixed: removed the direct `UrllibWebAppRuntime` override so the GitHub Actions "
        "run/workflow checks now use the standard `create_github_actions_page()` "
        "Playwright-backed factory path, and added `testing/tests/TS-951/README.md` "
        f"for the ticket folder. {rerun_summary}"
    )


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for item in result.get("steps", []):
        if not isinstance(item, dict):
            continue
        prefix = "*" if jira else "-"
        lines.append(
            f"{prefix} Step {item.get('step')}: {item.get('status', '').upper()} — "
            f"{item.get('action', '')}"
        )
        lines.append(f"{prefix} Observed: {item.get('observed', '')}")
    return lines or (["* <none recorded>"] if jira else ["- <none recorded>"])


def _failed_step_summary(result: dict[str, object]) -> str:
    failed_steps = [
        item
        for item in result.get("steps", [])
        if isinstance(item, dict) and item.get("status") == "failed"
    ]
    if not failed_steps:
        return str(result.get("error", "The test failed before step details were recorded."))
    first = failed_steps[0]
    return (
        f"Step {first.get('step')} failed. "
        f"{_snippet(str(first.get('observed', '')), limit=500)}"
    )


def _step_summary(step: GitHubWorkflowRunStepObservation | None) -> str:
    if step is None:
        return "<missing>"
    return (
        f"job={step.job_name}, step={step.step_name}, number={step.number}, "
        f"status={step.status}, conclusion={step.conclusion}"
    )


def _step_summary_from_mapping(payload: object) -> str:
    if not isinstance(payload, dict):
        return "<missing>"
    return (
        f"job={payload.get('job_name')}, step={payload.get('step_name')}, "
        f"number={payload.get('number')}, status={payload.get('status')}, "
        f"conclusion={payload.get('conclusion')}"
    )


def _snippet(text: str, *, limit: int) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3] + "..."


if __name__ == "__main__":
    main()
