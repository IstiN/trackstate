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
from testing.core.interfaces.github_accessibility_cancellation_probe import (  # noqa: E402
    GitHubAccessibilityCancellationProbeObservation,
)
from testing.core.interfaces.github_workflow_step_sequence_inspector import (  # noqa: E402
    GitHubWorkflowRunStepObservation,
    GitHubWorkflowStepSequenceObservation,
)
from testing.tests.support.github_accessibility_cancellation_probe_factory import (  # noqa: E402
    create_github_accessibility_cancellation_probe,
)
from testing.tests.support.github_actions_page_factory import (  # noqa: E402
    create_github_actions_page,
)
from testing.tests.support.github_workflow_step_sequence_inspector_factory import (  # noqa: E402
    create_github_workflow_step_sequence_inspector,
)

TICKET_KEY = "TS-962"
TEST_CASE_TITLE = "CI job manually cancelled - log-validation step execution is not skipped"
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-962/test_ts_962.py"
TEST_FILE_PATH = "testing/tests/TS-962/test_ts_962.py"
CONFIG_PATH = REPO_ROOT / "testing/tests/TS-962/config.yaml"
OUTPUTS_DIR = REPO_ROOT / "outputs"
DISCUSSIONS_RAW_PATH = REPO_ROOT / "input" / TICKET_KEY / "pr_discussions_raw.json"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
REVIEW_REPLIES_PATH = OUTPUTS_DIR / "review_replies.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
RUN_SCREENSHOT_PATH = OUTPUTS_DIR / "ts962_run_page.png"
WORKFLOW_SCREENSHOT_PATH = OUTPUTS_DIR / "ts962_workflow_page.png"

REQUEST_STEPS = [
    "Start a CI run that triggers the `unit-tests.yml` workflow.",
    "Manually cancel the job while `Run axe-core accessibility checks` is still in progress.",
    "Navigate to the job details and check the status of the `log-validation` step.",
]
EXPECTED_RESULT = (
    "The `log-validation` step is not skipped; it attempts to execute despite the "
    "`Cancelled` status of the preceding step, ensuring log cleanup or final validation "
    "is attempted."
)
ALWAYS_PATTERN = re.compile(r"\balways\s*\(", re.IGNORECASE)


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    raw_config = _load_yaml(CONFIG_PATH)
    runtime_inputs = raw_config.get("runtime_inputs", {})
    assert isinstance(runtime_inputs, dict)
    config = GitHubAccessibilityPullRequestGateConfig.from_file(CONFIG_PATH)

    accessibility_job_name = _required_string(runtime_inputs, "accessibility_job_name")
    axe_step_name = _required_string(runtime_inputs, "axe_step_name")
    log_validation_step_name = _required_string(
        runtime_inputs,
        "log_validation_step_name",
    )
    ui_timeout_seconds = _positive_int(runtime_inputs, "ui_timeout_seconds", default=60)

    probe = create_github_accessibility_cancellation_probe(
        REPO_ROOT,
        config_path=CONFIG_PATH,
    )
    sequence_inspector = create_github_workflow_step_sequence_inspector(REPO_ROOT)

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
        workflow_observation = observation.workflow_observation
        result.update(workflow_observation.to_dict())
        result["cancellation_probe"] = observation.to_dict()

        sequence = sequence_inspector.inspect(
            repository=workflow_observation.repository,
            workflow_path=workflow_observation.target_workflow_path,
            workflow_ref=workflow_observation.default_branch,
            run_id=workflow_observation.latest_pull_request_run_id,
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
        _evaluate_run_trigger_and_cancellation(
            result,
            observation=observation,
            failures=failures,
        )
        _evaluate_log_validation_after_cancellation(
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
    print("TS-962 passed")


def _evaluate_run_trigger_and_cancellation(
    result: dict[str, object],
    *,
    observation: GitHubAccessibilityCancellationProbeObservation,
    failures: list[str],
) -> None:
    workflow = observation.workflow_observation
    step_failures: list[str] = []
    expected_files = [
        workflow.pull_request_probe_path,
        workflow.probe_render_host_path,
    ]
    missing_files = [
        path for path in expected_files if path and path not in workflow.pull_request_file_paths
    ]
    if missing_files:
        step_failures.append(
            f"GitHub did not record the expected disposable probe files: {missing_files}."
        )
    if workflow.latest_pull_request_run_id is None:
        step_failures.append(
            "GitHub Actions did not expose a contributor-visible pull-request workflow run."
        )
    if workflow.latest_pull_request_run_event != "pull_request":
        step_failures.append(
            f"the observed workflow event was `{workflow.latest_pull_request_run_event or '<none>'}` instead of `pull_request`."
        )
    if observation.pre_cancel_axe_step is None:
        step_failures.append(
            "the live run never exposed `Run axe-core accessibility checks` before the cancellation request."
        )
    elif (observation.pre_cancel_axe_step.status or "").lower() != "in_progress":
        step_failures.append(
            "the cancellation request was not captured while `Run axe-core accessibility checks` "
            f"was still in progress. Observed step summary: {_step_summary(observation.pre_cancel_axe_step)}."
        )
    if not observation.cancellation_requested:
        step_failures.append(
            "the automation could not request run cancellation through GitHub CLI. "
            f"Error: {observation.cancellation_request_error or '<none>'}."
        )
    if (workflow.latest_pull_request_run_conclusion or "").lower() != "cancelled":
        step_failures.append(
            "the live workflow run did not finish in a cancelled state after the manual-style "
            f"cancellation request. Observed conclusion: `{workflow.latest_pull_request_run_conclusion or '<none>'}`."
        )

    if step_failures:
        message = (
            "Step 1 failed: "
            + " ".join(step_failures)
            + "\n"
            + f"Pull Request URL: {workflow.pull_request_url}\n"
            + f"Observed PR files: {workflow.pull_request_file_paths}\n"
            + f"Run URL: {workflow.latest_pull_request_run_url or '<none>'}\n"
            + f"Cancellation requested at: {observation.cancellation_requested_at or '<none>'}\n"
            + f"Pre-cancel axe step: {_step_summary(observation.pre_cancel_axe_step)}\n"
            + f"Run status trace: {observation.run_status_trace or ['<none>']}\n"
            + f"Step poll trace: {observation.step_poll_trace or ['<none>']}"
        )
        failures.append(message)
        _record_step(result, step=1, status="failed", action=REQUEST_STEPS[0], observed=message)
        _record_step(result, step=2, status="failed", action=REQUEST_STEPS[1], observed=message)
        return

    observed = (
        "Created a disposable PR that keeps the accessibility step alive long enough to cancel "
        "the live pull-request run while `Run axe-core accessibility checks` was still in progress.\n"
        f"Pull Request URL: {workflow.pull_request_url}\n"
        f"Observed PR files: {workflow.pull_request_file_paths}\n"
        f"Run URL: {workflow.latest_pull_request_run_url}\n"
        f"Cancellation requested at: {observation.cancellation_requested_at}\n"
        f"Pre-cancel axe step: {_step_summary(observation.pre_cancel_axe_step)}\n"
        f"Run status trace: {observation.run_status_trace}"
    )
    _record_step(result, step=1, status="passed", action=REQUEST_STEPS[0], observed=observed)
    _record_step(result, step=2, status="passed", action=REQUEST_STEPS[1], observed=observed)


def _evaluate_log_validation_after_cancellation(
    result: dict[str, object],
    *,
    observation: GitHubAccessibilityCancellationProbeObservation,
    sequence: GitHubWorkflowStepSequenceObservation,
    run_page: GitHubActionsPageObservation | None,
    run_page_error: str | None,
    workflow_page: GitHubActionsPageObservation | None,
    workflow_page_error: str | None,
    axe_step_name: str,
    log_validation_step_name: str,
    failures: list[str],
) -> None:
    workflow = observation.workflow_observation
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
    elif not log_validation_contract.uses_always or not ALWAYS_PATTERN.search(
        log_validation_contract.if_condition or ""
    ):
        step_failures.append(
            "the live workflow file does not configure `log-validation` with an `always()` "
            f"conditional. Observed `if:` value: `{log_validation_contract.if_condition or '<none>'}`."
        )

    if axe_step_run is None:
        step_failures.append(
            f"the cancelled live run did not expose the `{axe_step_name}` step in the accessibility job."
        )
    elif (axe_step_run.conclusion or "").lower() != "cancelled":
        step_failures.append(
            "the cancelled live run did not show `Run axe-core accessibility checks` with a "
            f"`cancelled` conclusion. Observed step summary: {_step_summary(axe_step_run)}."
        )

    if log_validation_step_run is None:
        step_failures.append(
            f"the cancelled live workflow run did not expose the `{log_validation_step_name}` step after the cancelled axe step."
        )
    else:
        if (
            axe_step_run is not None
            and axe_step_run.number is not None
            and log_validation_step_run.number is not None
            and log_validation_step_run.number != axe_step_run.number + 1
        ):
            step_failures.append(
                "the cancelled live run exposed both steps, but `log-validation` was not "
                f"immediately after `{axe_step_name}`. Observed numbers: "
                f"{axe_step_run.number} -> {log_validation_step_run.number}."
            )
        if log_validation_step_run.started_at is None:
            step_failures.append(
                "`log-validation` appeared in the run metadata, but GitHub did not record a "
                f"start time. Observed step summary: {_step_summary(log_validation_step_run)}."
            )
        if (log_validation_step_run.conclusion or "").lower() == "skipped":
            step_failures.append(
                "`log-validation` was explicitly marked as skipped after cancellation. "
                f"Observed step summary: {_step_summary(log_validation_step_run)}."
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
    if workflow.pull_request_status_state not in {"failure", "cancelled"}:
        step_failures.append(
            "the contributor-visible pull request checks did not report a cancelled/failing "
            f"status after the cancellation scenario. Observed state: `{workflow.pull_request_status_state or '<none>'}`."
        )

    if step_failures:
        message = (
            "Step 3 failed: "
            + " ".join(step_failures)
            + "\n"
            + f"Workflow URL: {sequence.workflow_url}\n"
            + f"Workflow excerpt: {sequence.workflow_excerpt or '<none>'}\n"
            + f"Run URL: {workflow.latest_pull_request_run_url or '<none>'}\n"
            + f"`{axe_step_name}` summary: {_step_summary(axe_step_run)}\n"
            + f"`{log_validation_step_name}` summary: {_step_summary(log_validation_step_run)}\n"
            + f"Pre-cancel axe step: {_step_summary(observation.pre_cancel_axe_step)}\n"
            + f"Post-cancel log-validation step: {_step_summary(observation.post_cancel_log_validation_step)}\n"
            + f"Run page screenshot: {None if run_page is None else run_page.screenshot_path}\n"
            + f"Workflow page screenshot: {None if workflow_page is None else workflow_page.screenshot_path}\n"
            + f"Run log excerpt: {workflow.run_log_excerpt or '<none>'}"
        )
        failures.append(message)
        _record_step(result, step=3, status="failed", action=REQUEST_STEPS[2], observed=message)
        return

    observed = (
        "Observed the cancelled live workflow sequence and confirmed the workflow file and run "
        "metadata still exposed `log-validation` as attempted after the cancelled axe step.\n"
        f"Workflow URL: {sequence.workflow_url}\n"
        f"Workflow excerpt: {sequence.workflow_excerpt}\n"
        f"Run URL: {workflow.latest_pull_request_run_url}\n"
        f"`{axe_step_name}` summary: {_step_summary(axe_step_run)}\n"
        f"`{log_validation_step_name}` summary: {_step_summary(log_validation_step_run)}\n"
        f"Run page screenshot: {None if run_page is None else run_page.screenshot_path}\n"
        f"Workflow page screenshot: {None if workflow_page is None else workflow_page.screenshot_path}"
    )
    _record_step(result, step=3, status="passed", action=REQUEST_STEPS[2], observed=observed)


def _record_human_verification(
    result: dict[str, object],
    *,
    observation: GitHubAccessibilityCancellationProbeObservation,
    sequence: GitHubWorkflowStepSequenceObservation,
    run_page: GitHubActionsPageObservation | None,
    run_page_error: str | None,
    workflow_page: GitHubActionsPageObservation | None,
    workflow_page_error: str | None,
    axe_step_name: str,
    log_validation_step_name: str,
) -> None:
    workflow = observation.workflow_observation
    _record_human_line(
        result,
        check=(
            "Opened the live GitHub Actions run page a reviewer would use and checked the "
            "visible cancelled workflow labels."
        ),
        observed=(
            f"Run URL: `{workflow.latest_pull_request_run_url or '<none>'}`; page error: "
            f"`{run_page_error or '<none>'}`; matched text: "
            f"`{None if run_page is None else run_page.matched_text}`; screenshot: "
            f"`{None if run_page is None else run_page.screenshot_path}`; visible body excerpt: "
            f"`{_snippet('' if run_page is None else run_page.body_text, limit=900)}`."
        ),
    )
    _record_human_line(
        result,
        check=(
            "Opened the live workflow file page and checked that `log-validation` still uses "
            "an `always()` condition."
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
            "Compared the cancelled step sequence to the ticket expectation from a user "
            "perspective."
        ),
        observed=(
            f"Pre-cancel `{axe_step_name}` summary: `{_step_summary(observation.pre_cancel_axe_step)}`; "
            f"final `{axe_step_name}` summary: `{_step_summary(sequence.axe_step_run)}`; "
            f"final `{log_validation_step_name}` summary: `{_step_summary(sequence.log_validation_step_run)}`; "
            f"run conclusion: `{workflow.latest_pull_request_run_conclusion or '<none>'}`; "
            f"status state: `{workflow.pull_request_status_state or '<none>'}`."
        ),
    )


def _open_run_page(
    *,
    observation: GitHubAccessibilityCancellationProbeObservation,
    sequence: GitHubWorkflowStepSequenceObservation,
    timeout_seconds: int,
) -> tuple[GitHubActionsPageObservation | None, str | None]:
    workflow = observation.workflow_observation
    if workflow.latest_pull_request_run_url is None:
        return None, "Workflow run URL is missing."
    expected_texts = [
        workflow.target_workflow_name,
        "Accessibility checks",
        "log-validation",
        "Cancelled",
        *(sequence.observed_job_names[:4]),
    ]
    try:
        with create_github_actions_page() as actions_page:
            return (
                actions_page.open_page(
                    url=workflow.latest_pull_request_run_url,
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
        "always()",
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
    error = str(result.get("error", "AssertionError: TS-962 failed"))
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
        "* Created a disposable pull request against the live repository that holds the accessibility Playwright spec open long enough to cancel the run while {{Run axe-core accessibility checks}} is still in progress.",
        "* Read the live workflow file from GitHub and inspected the accessibility job step contract for {{log-validation}}.",
        "* Read the cancelled live workflow run step sequence for {{Run axe-core accessibility checks}} and {{log-validation}}.",
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
    rerun_summary = (
        f"Re-ran `{RUN_COMMAND}`: passed (`1 passed, 0 failed`)."
        if passed
        else f"Re-ran `{RUN_COMMAND}`: failed with `{result.get('error')}`."
    )
    lines = [
        "## PR Rework Result",
        "",
        "- Switched the GitHub Actions UI verification back to the standard `create_github_actions_page()` Playwright-backed path and removed the raw HTML fallback.",
        "- Added a `testing/core/interfaces` cancellation probe contract so the factory returns an interface instead of the concrete service type.",
        "- Added `testing/tests/TS-962/README.md` for the ticket folder.",
        f"- Test rerun: {rerun_summary}",
        "",
        "## Test Automation Result",
        "",
        f"**Status:** {status}",
        f"**Test Case:** {TICKET_KEY} - {TEST_CASE_TITLE}",
        "",
        "## What was automated",
        "- Created a disposable pull request against the live repository that holds the accessibility Playwright spec open long enough to cancel the run while `Run axe-core accessibility checks` is still in progress.",
        "- Read the live workflow file from GitHub and inspected the accessibility job step contract for `log-validation`.",
        "- Read the cancelled live workflow run step sequence for `Run axe-core accessibility checks` and `log-validation`.",
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
        "*Fixed:* Restored the standard Playwright-backed `create_github_actions_page()` path, returned the TS-962 cancellation probe through a core interface contract, and added `testing/tests/TS-962/README.md`.",
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
    return "\n".join(lines) + "\n"


def _bug_description(result: dict[str, object]) -> str:
    step_map = {
        int(step["step"]): step
        for step in result.get("steps", [])
        if isinstance(step, dict) and isinstance(step.get("step"), int)
    }
    return (
        f"# {TICKET_KEY} - cancelled accessibility run skips or never starts log-validation\n\n"
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
        "- **Actual:** After cancelling the live `Flutter Required Checks` pull-request run "
        "while `Run axe-core accessibility checks` was in progress, the cancelled run did not "
        "expose `log-validation` as an attempted step with visible execution metadata and/or "
        "the workflow contract surface did not show the expected `always()` protection.\n\n"
        "## Environment details\n"
        f"- **URL:** {result.get('pull_request_url', '<missing pull request URL>')}\n"
        "- **Browser:** Chromium via Playwright against GitHub Actions\n"
        f"- **OS:** {result.get('os')}\n"
        f"- **Repository:** {result.get('repository')}\n"
        f"- **Branch:** {result.get('default_branch')}\n"
        f"- **PR checks URL:** {result.get('pull_request_checks_url', '<missing checks URL>')}\n"
        f"- **Workflow run URL:** {result.get('latest_pull_request_run_url', '<missing run URL>')}\n"
        f"- **Run command:** `{result.get('run_command')}`\n"
        f"- **Config:** `{CONFIG_PATH}`\n\n"
        "## Screenshots or logs\n"
        "- **Run page screenshot:**\n"
        "```text\n"
        f"{result.get('run_page', {}).get('screenshot_path') if isinstance(result.get('run_page'), dict) else '<none>'}\n"
        "```\n"
        "- **Workflow page screenshot:**\n"
        "```text\n"
        f"{result.get('workflow_page', {}).get('screenshot_path') if isinstance(result.get('workflow_page'), dict) else '<none>'}\n"
        "```\n"
        "- **Observed cancellation trace:**\n"
        "```text\n"
        f"{result.get('cancellation_probe', {}).get('step_poll_trace') if isinstance(result.get('cancellation_probe'), dict) else '<none>'}\n"
        "```\n"
        "- **Run/log excerpt:**\n"
        "```text\n"
        f"{result.get('run_log_excerpt', '<missing log excerpt>')}\n"
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
    if any(
        isinstance(existing, dict) and existing.get("step") == step for existing in steps
    ):
        return
    steps.append(
        {
            "step": step,
            "status": status,
            "action": action,
            "observed": observed,
        }
    )


def _record_human_line(
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
        "Fixed: TS-962 now uses the standard `create_github_actions_page()` "
        "Playwright-backed path with no urllib fallback, the cancellation probe "
        "factory returns a core interface contract instead of the concrete "
        "service, and `testing/tests/TS-962/README.md` has been added. "
        f"{rerun_summary}"
    )


def _step_summary(step: GitHubWorkflowRunStepObservation | None) -> str:
    if step is None:
        return "<missing>"
    return (
        f"job={step.job_name}, step={step.step_name}, number={step.number}, "
        f"status={step.status or '<none>'}, conclusion={step.conclusion or '<none>'}, "
        f"started_at={step.started_at or '<none>'}, completed_at={step.completed_at or '<none>'}"
    )


def _snippet(text: str, *, limit: int) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"


if __name__ == "__main__":
    main()
