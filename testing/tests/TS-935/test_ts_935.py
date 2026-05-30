from __future__ import annotations

from dataclasses import asdict
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

from testing.components.pages.github_actions_page import GitHubActionsPageObservation  # noqa: E402
from testing.components.services.github_accessibility_compliant_pull_request_gate_probe import (  # noqa: E402
    GitHubAccessibilityCompliantPullRequestGateProbeService,
)
from testing.core.config.github_accessibility_pull_request_gate_config import (  # noqa: E402
    GitHubAccessibilityPullRequestGateConfig,
)
from testing.core.interfaces.github_accessibility_pull_request_gate_probe import (  # noqa: E402
    GitHubAccessibilityPullRequestGateObservation,
)
from testing.core.interfaces.github_actions_preflight_gate_probe import (  # noqa: E402
    GitHubActionsWorkflowJobObservation,
)
from testing.tests.support.github_accessibility_compliant_pull_request_gate_probe_factory import (  # noqa: E402
    create_github_accessibility_compliant_pull_request_gate_probe,
)
from testing.tests.support.github_actions_page_factory import (  # noqa: E402
    create_github_actions_page,
)

TICKET_KEY = "TS-935"
TEST_CASE_TITLE = "Accessibility audit passes — deployment stage is triggered"
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-935/test_ts_935.py"
TEST_FILE_PATH = "testing/tests/TS-935/test_ts_935.py"
CONFIG_PATH = REPO_ROOT / "testing/tests/TS-935/config.yaml"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
RUN_SCREENSHOT_PATH = OUTPUTS_DIR / "ts935_run_page.png"

REQUEST_STEPS = [
    "Create a Pull Request with WCAG-compliant UI components (e.g., contrast ratio >= 4.5:1).",
    "Push the changes to trigger the CI pipeline.",
    "Monitor the workflow execution in the GitHub Actions UI.",
    "Check the status of the 'deploy' or 'publish' stage.",
]
EXPECTED_RESULT = (
    "The accessibility audit passes, and the subsequent deployment stage is "
    "triggered and executed as expected."
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

    accessibility_job_markers = _string_list(
        runtime_inputs,
        "accessibility_job_markers",
        default=["Accessibility checks", "accessibility"],
    )
    downstream_job_markers = _string_list(
        runtime_inputs,
        "downstream_job_markers",
        default=["Deploy", "deployment", "publish", "pages", "distribution"],
    )
    ui_timeout_seconds = _positive_int(runtime_inputs, "ui_timeout_seconds", default=60)

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

        jobs = list(observation.observed_run_jobs)
        accessibility_job = _find_matching_job(jobs, accessibility_job_markers)
        downstream_job = _find_matching_job(jobs, downstream_job_markers)
        run_page: GitHubActionsPageObservation | None = None
        run_page_error: str | None = None
        try:
            run_page = _open_run_page(
                observation=observation,
                jobs=jobs,
                timeout_seconds=ui_timeout_seconds,
            )
        except Exception as page_error:  # keep remaining assertions running
            run_page_error = f"{type(page_error).__name__}: {page_error}"

        result["workflow_contract"] = asdict(observation.target_workflow)
        result["workflow_jobs"] = [asdict(job) for job in jobs]
        result["accessibility_job"] = (
            None if accessibility_job is None else asdict(accessibility_job)
        )
        result["downstream_job"] = None if downstream_job is None else asdict(downstream_job)
        result["run_page"] = None if run_page is None else asdict(run_page)
        result["run_page_error"] = run_page_error

        failures: list[str] = []
        _evaluate_pr_probe(result, observation, failures)
        _evaluate_ci_trigger(result, observation, failures)
        _evaluate_actions_ui(
            result,
            observation=observation,
            run_page=run_page,
            run_page_error=run_page_error,
            failures=failures,
        )
        _evaluate_downstream_execution(
            result,
            observation=observation,
            jobs=jobs,
            accessibility_job=accessibility_job,
            downstream_job=downstream_job,
            failures=failures,
        )

        if failures:
            raise AssertionError("\n".join(failures))
    except Exception as error:
        result.setdefault("error", f"{type(error).__name__}: {error}")
        result.setdefault("traceback", traceback.format_exc())
        _write_failure_outputs(result)
        raise

    _write_pass_outputs(result)
    print("TS-935 passed")


def _evaluate_pr_probe(
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
    step_failures: list[str] = []
    if missing_files:
        step_failures.append(f"GitHub did not record expected PR files: {missing_files}.")
    if not observation.probe_rendered_in_application:
        step_failures.append(
            "the disposable PR did not wire the compliant probe into a rendered app surface."
        )
    if observation.probe_contains_low_contrast_indicator:
        step_failures.append(
            "the disposable PR probe still contains the low-contrast indicator used by the failing scenario."
        )
    if (
        observation.probe_semantic_label
        != GitHubAccessibilityCompliantPullRequestGateProbeService.expected_semantic_label
    ):
        step_failures.append(
            "the disposable PR did not keep the expected descriptive semantics label."
        )

    if step_failures:
        message = (
            "Step 1 failed: "
            + " ".join(step_failures)
            + "\n"
            + f"Pull Request URL: {observation.pull_request_url}\n"
            + f"Observed PR files: {observation.pull_request_file_paths}\n"
            + f"Observed label: {observation.probe_semantic_label!r}\n"
            + f"Probe technique: {observation.probe_contrast_technique}"
        )
        failures.append(message)
        _record_step(result, step=1, status="failed", action=REQUEST_STEPS[0], observed=message)
        return

    observed = (
        "Created a disposable PR and verified that GitHub recorded the rendered compliant "
        f"probe file `{observation.pull_request_probe_path}` plus render host "
        f"`{observation.probe_render_host_path}`.\n"
        f"Pull Request URL: {observation.pull_request_url}\n"
        f"Observed PR files: {observation.pull_request_file_paths}\n"
        f"Observed label: {observation.probe_semantic_label!r}\n"
        f"Probe technique: {observation.probe_contrast_technique}"
    )
    _record_step(result, step=1, status="passed", action=REQUEST_STEPS[0], observed=observed)


def _evaluate_ci_trigger(
    result: dict[str, object],
    observation: GitHubAccessibilityPullRequestGateObservation,
    failures: list[str],
) -> None:
    step_failures: list[str] = []
    if observation.latest_pull_request_run_id is None:
        step_failures.append(
            "GitHub Actions did not expose a contributor-visible `pull_request` run for the disposable PR."
        )
    if observation.latest_pull_request_run_event != "pull_request":
        step_failures.append(
            f"the observed workflow event was `{observation.latest_pull_request_run_event}` instead of `pull_request`."
        )

    if step_failures:
        message = (
            "Step 2 failed: "
            + " ".join(step_failures)
            + "\n"
            + f"Pull Request URL: {observation.pull_request_url}\n"
            + f"Observed branch runs: {observation.observed_branch_run_names}\n"
            + f"Observed run URLs: {observation.observed_branch_run_urls}"
        )
        failures.append(message)
        _record_step(result, step=2, status="failed", action=REQUEST_STEPS[1], observed=message)
        return

    observed = (
        "Pushed the disposable PR branch and observed the live pull-request workflow run.\n"
        f"Run URL: {observation.latest_pull_request_run_url}\n"
        f"Status: {observation.latest_pull_request_run_status}\n"
        f"Conclusion: {observation.latest_pull_request_run_conclusion or '<pending>'}"
    )
    _record_step(result, step=2, status="passed", action=REQUEST_STEPS[1], observed=observed)


def _evaluate_actions_ui(
    result: dict[str, object],
    *,
    observation: GitHubAccessibilityPullRequestGateObservation,
    run_page: GitHubActionsPageObservation | None,
    run_page_error: str | None,
    failures: list[str],
) -> None:
    if run_page is None:
        message = (
            "Step 3 failed: the GitHub Actions run page could not be opened for human-style "
            "verification.\n"
            f"Run URL: {observation.latest_pull_request_run_url or '<missing>'}\n"
            f"Error: {run_page_error or '<missing>'}"
        )
        failures.append(message)
        _record_step(result, step=3, status="failed", action=REQUEST_STEPS[2], observed=message)
        return

    _record_human_verification(
        result,
        check=(
            "Opened the live GitHub Actions run page and reviewed the visible workflow and "
            "job text as a maintainer would."
        ),
        observed=(
            f"Run page URL: `{run_page.url}`; matched text: `{run_page.matched_text}`; "
            f"visible body excerpt: `{_snippet(run_page.body_text, limit=900)}`; screenshot: "
            f"`{run_page.screenshot_path or '<none>'}`."
        ),
    )

    required_tokens = [observation.target_workflow_name]
    missing = [token for token in required_tokens if token and token not in run_page.body_text]
    if missing:
        message = (
            "Step 3 failed: the GitHub Actions run page opened, but the visible body text did "
            "not show the expected workflow label for human-style verification.\n"
            f"Missing text: {missing}\n"
            f"Run URL: {run_page.url}\n"
            f"Visible body excerpt: {_snippet(run_page.body_text, limit=1200)}\n"
            f"Screenshot: {run_page.screenshot_path or '<none>'}"
        )
        failures.append(message)
        _record_step(result, step=3, status="failed", action=REQUEST_STEPS[2], observed=message)
        return

    observed = (
        "Opened the live GitHub Actions run page and verified the workflow is visible from the "
        "user-facing UI.\n"
        f"Run URL: {run_page.url}\n"
        f"Matched text: {run_page.matched_text}\n"
        f"Screenshot: {run_page.screenshot_path or '<none>'}"
    )
    _record_step(result, step=3, status="passed", action=REQUEST_STEPS[2], observed=observed)


def _evaluate_downstream_execution(
    result: dict[str, object],
    *,
    observation: GitHubAccessibilityPullRequestGateObservation,
    jobs: list[GitHubActionsWorkflowJobObservation],
    accessibility_job: GitHubActionsWorkflowJobObservation | None,
    downstream_job: GitHubActionsWorkflowJobObservation | None,
    failures: list[str],
) -> None:
    _record_human_verification(
        result,
        check=(
            "Compared the live job list, conclusions, and audit evidence to what a user would "
            "infer from the run page and workflow logs."
        ),
        observed=(
            f"Observed jobs: {_job_list_summary(jobs)}; accessibility job: "
            f"{_single_job_summary(accessibility_job)}; downstream job: "
            f"{_single_job_summary(downstream_job)}; observed steps: "
            f"{observation.observed_step_names}; accessibility markers in log: "
            f"{observation.run_log_matched_accessibility_markers}; runtime accessibility "
            f"evidence: `{observation.runtime_accessibility_surface_summary or '<none>'}`; "
            f"run-log excerpt: `{observation.run_log_excerpt or '<none>'}`."
        ),
    )

    audit_step_visible = "Run axe-core accessibility checks" in observation.observed_step_names
    log_markers = {marker.lower() for marker in observation.run_log_matched_accessibility_markers}
    run_log_excerpt_lower = (observation.run_log_excerpt or "").lower()
    audit_log_visible = bool(log_markers) and (
        "axe-core" in log_markers
        or "run axe-core accessibility checks" in run_log_excerpt_lower
        or "npm run test:a11y" in run_log_excerpt_lower
    )

    step_failures: list[str] = []
    if observation.latest_pull_request_run_conclusion not in SUCCESS_CONCLUSIONS:
        step_failures.append(
            "the live workflow run did not finish with a successful conclusion."
        )
    if observation.pull_request_status_state not in SUCCESS_CONCLUSIONS:
        step_failures.append(
            "the contributor-visible PR status did not stay green after the accessibility run."
        )
    if observation.failed_status_check_names:
        step_failures.append(
            f"GitHub still reported failed status checks: {observation.failed_status_check_names}."
        )
    if not observation.target_workflow_downstream_job_names:
        step_failures.append(
            "the target workflow does not define any downstream deploy/publish stage."
        )
    if not observation.target_workflow_downstream_job_depends_on_accessibility:
        step_failures.append(
            "the workflow defines a deploy/publish stage, but it is not wired to depend on the accessibility audit job."
        )
    if accessibility_job is None:
        step_failures.append(
            "the live run did not expose a contributor-visible accessibility job."
        )
    elif (accessibility_job.conclusion or "").lower() not in SUCCESS_CONCLUSIONS:
        step_failures.append(
            "the accessibility job did not conclude with `success`."
        )
    if observation.accessibility_status_check_conclusion not in SUCCESS_CONCLUSIONS:
        step_failures.append(
            "the contributor-visible accessibility status check did not conclude with `success`."
        )
    if not audit_step_visible:
        step_failures.append(
            "the live workflow never showed the `Run axe-core accessibility checks` step."
        )
    if not audit_log_visible:
        step_failures.append(
            "the live workflow log did not contain explicit accessibility-audit execution evidence."
        )
    if not observation.runtime_accessibility_surface_present:
        step_failures.append(
            "the accessibility run never exposed browser-visible runtime semantics evidence for the compliant probe."
        )
    if downstream_job is None:
        step_failures.append(
            "the workflow contract defines a downstream deploy/publish stage, but the live run did not expose that stage."
        )
    else:
        downstream_status = (downstream_job.status or "").lower()
        downstream_conclusion = (downstream_job.conclusion or "").lower()
        if downstream_status != "completed" or downstream_conclusion not in SUCCESS_CONCLUSIONS:
            step_failures.append(
                "the downstream deploy/publish stage was exposed, but it did not execute successfully."
            )

    if step_failures:
        message = (
            "Step 4 failed: "
            + " ".join(step_failures)
            + "\n"
            + f"Accessibility job: {_single_job_summary(accessibility_job)}\n"
            + f"Downstream job: {_single_job_summary(downstream_job)}\n"
            + f"Workflow downstream jobs: {observation.target_workflow_downstream_job_names}\n"
            + f"Observed jobs: {_job_list_summary(jobs)}\n"
            + f"Observed steps: {observation.observed_step_names}\n"
            + "Accessibility check conclusion: "
            + f"{observation.accessibility_status_check_conclusion or '<none>'}\n"
            + f"Overall PR status: {observation.pull_request_status_state or '<none>'}\n"
            + f"Run conclusion: {observation.latest_pull_request_run_conclusion or '<none>'}\n"
            + "Run-log accessibility markers: "
            + f"{observation.run_log_matched_accessibility_markers}\n"
            + f"Runtime accessibility evidence: {observation.runtime_accessibility_surface_summary or '<none>'}\n"
            + f"Run log excerpt: {observation.run_log_excerpt or '<none>'}\n"
            + f"Run URL: {observation.latest_pull_request_run_url or '<none>'}"
        )
        failures.append(message)
        _record_step(result, step=4, status="failed", action=REQUEST_STEPS[3], observed=message)
        return

    observed = (
        "The accessibility audit passed for the disposable compliant probe, and the downstream "
        "deploy/publish stage executed successfully.\n"
        f"Accessibility job: {_single_job_summary(accessibility_job)}\n"
        f"Downstream job: {_single_job_summary(downstream_job)}\n"
        f"Workflow downstream jobs: {observation.target_workflow_downstream_job_names}\n"
        f"Runtime accessibility evidence: {observation.runtime_accessibility_surface_summary}"
    )
    _record_step(result, step=4, status="passed", action=REQUEST_STEPS[3], observed=observed)


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must deserialize to a mapping.")
    return payload


def _string_list(
    payload: dict[str, object],
    key: str,
    *,
    default: list[str],
) -> list[str]:
    raw = payload.get(key, default)
    if not isinstance(raw, list):
        return default
    values = [str(item).strip() for item in raw if str(item).strip()]
    return values or default


def _positive_int(payload: dict[str, object], key: str, *, default: int) -> int:
    value = payload.get(key, default)
    return value if isinstance(value, int) and value > 0 else default


def _find_matching_job(
    jobs: list[GitHubActionsWorkflowJobObservation],
    markers: list[str],
) -> GitHubActionsWorkflowJobObservation | None:
    normalized_markers = [marker.lower() for marker in markers if marker.strip()]
    for job in jobs:
        haystack = " ".join(
            value
            for value in (job.name, job.status, job.conclusion)
            if isinstance(value, str) and value
        ).lower()
        if any(marker in haystack for marker in normalized_markers):
            return job
    return None


def _open_run_page(
    *,
    observation: GitHubAccessibilityPullRequestGateObservation,
    jobs: list[GitHubActionsWorkflowJobObservation],
    timeout_seconds: int,
) -> GitHubActionsPageObservation:
    if observation.latest_pull_request_run_url is None:
        raise AssertionError(
            "Step 3 failed: the workflow run URL is missing, so the GitHub Actions UI could "
            "not be opened for human-style verification."
        )
    expected_texts = [
        observation.target_workflow_name,
        *[job.name for job in jobs[:4] if job.name],
        *observation.target_workflow_downstream_job_names,
        "Accessibility checks",
        "Deploy preview",
    ]
    with create_github_actions_page() as actions_page:
        return actions_page.open_page(
            url=observation.latest_pull_request_run_url,
            expected_texts=tuple(dict.fromkeys(expected_texts)),
            screenshot_path=str(RUN_SCREENSHOT_PATH),
            timeout_seconds=timeout_seconds,
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
    RESPONSE_PATH.write_text(_response_summary(result, passed=True), encoding="utf-8")


def _write_failure_outputs(result: dict[str, object]) -> None:
    error = str(result.get("error", "AssertionError: TS-935 failed"))
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
        "* Created a disposable pull request against the live repository with the rendered compliant accessibility probe path used for the deployed PR accessibility gate.",
        "* Waited for the live pull-request GitHub Actions workflow run and read its status checks, jobs, and logs.",
        "* Opened the live run page for human-style verification and captured a screenshot.",
        "* Verified that the accessibility audit passed and that the downstream deploy or publish stage executed successfully.",
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
            f"{{{{{result['default_branch']}}}}}, browser {{Chromium (Playwright)}}, "
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
        "- Created a disposable pull request against the live repository with the rendered compliant accessibility probe path used for the deployed PR accessibility gate.",
        "- Waited for the live pull-request GitHub Actions workflow run and read its status checks, jobs, and logs.",
        "- Opened the live run page for human-style verification and captured a screenshot.",
        "- Verified that the accessibility audit passed and that the downstream deploy or publish stage executed successfully.",
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
            f"`{result['default_branch']}`, browser `Chromium (Playwright)`, "
            f"OS `{result['os']}`."
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
        "- Added TS-935 as a live disposable PR probe for the post-accessibility downstream deployment path.",
        "- The automation uses the real compliant accessibility probe, inspects GitHub Actions jobs/logs, and captures a run-page screenshot for human-style verification.",
        f"- Test case: **{TICKET_KEY} - {TEST_CASE_TITLE}**",
        f"- Result: **{status}**",
        f"- Command: `{RUN_COMMAND}`",
        (
            f"- Environment: `{result['repository']}` @ `{result['default_branch']}` "
            f"using Chromium (Playwright) on `{result['os']}`."
        ),
        (
            "- Outcome: the accessibility pass triggered the downstream deploy/publish stage successfully."
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
    failed_summary = _failed_step_summary(result)
    return "\n".join(
        [
            f"# {TICKET_KEY} - accessibility pass does not trigger the downstream deployment stage",
            "",
            "## Steps to reproduce",
            (
                "1. ✅ Create a Pull Request with WCAG-compliant UI components (e.g., contrast ratio >= 4.5:1)."
                if _step_status(result, 1) == "passed"
                else "1. ❌ Create a Pull Request with WCAG-compliant UI components (e.g., contrast ratio >= 4.5:1)."
            ),
            f"   - {_step_observed(result, 1)}",
            (
                "2. ✅ Push the changes to trigger the CI pipeline."
                if _step_status(result, 2) == "passed"
                else "2. ❌ Push the changes to trigger the CI pipeline."
            ),
            f"   - {_step_observed(result, 2)}",
            (
                "3. ✅ Monitor the workflow execution in the GitHub Actions UI."
                if _step_status(result, 3) == "passed"
                else "3. ❌ Monitor the workflow execution in the GitHub Actions UI."
            ),
            f"   - {_step_observed(result, 3)}",
            (
                "4. ✅ Check the status of the 'deploy' or 'publish' stage."
                if _step_status(result, 4) == "passed"
                else "4. ❌ Check the status of the 'deploy' or 'publish' stage."
            ),
            f"   - {_step_observed(result, 4)}",
            "",
            "## Exact error message / assertion failure",
            "```text",
            str(result.get("traceback", result.get("error", "<missing traceback>"))),
            "```",
            "",
            "## Expected result",
            f"- {EXPECTED_RESULT}",
            "",
            "## Actual result",
            (
                "- The accessibility audit passed, but the workflow did not expose a downstream deploy/publish stage that completed successfully."
                if _step_status(result, 4) != "passed"
                else "- The downstream deploy/publish stage completed successfully after the accessibility audit passed."
            ),
            "",
            "## Actual vs Expected",
            f"- Expected: {EXPECTED_RESULT}",
            f"- Actual: {failed_summary}",
            "",
            "## Environment details",
            f"- Repository: `{result.get('repository', '')}`",
            f"- Branch: `{result.get('default_branch', '')}`",
            f"- Pull Request: `{result.get('pull_request_url', '')}`",
            f"- Pull Request checks: `{result.get('pull_request_checks_url', '')}`",
            f"- Workflow run: `{result.get('latest_pull_request_run_url', '')}`",
            f"- Browser: `Chromium (Playwright)`",
            f"- OS: `{result.get('os', '')}`",
            "",
            "## Screenshots / logs",
            f"- Run-page screenshot: `{_nested_string(result, ['run_page', 'screenshot_path']) or '<none>'}`",
            f"- Run-log excerpt: `{result.get('run_log_excerpt', '<none>')}`",
            f"- Observed jobs: `{_job_list_from_result(result)}`",
            "",
            "## Failing command",
            "```bash",
            RUN_COMMAND,
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
    checks = result.setdefault("human_verification", [])
    assert isinstance(checks, list)
    checks.append({"check": check, "observed": observed})


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
    checks = result.get("human_verification")
    if not isinstance(checks, list):
        return lines
    for entry in checks:
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
        status = str(entry.get("status", "")).lower()
        if status == "failed":
            return f"Step {entry.get('step')} failed: {entry.get('observed')}"
    return str(result.get("error", "Unknown failure"))


def _step_status(result: dict[str, object], step_number: int) -> str:
    steps = result.get("steps")
    if not isinstance(steps, list):
        return ""
    for entry in steps:
        if isinstance(entry, dict) and entry.get("step") == step_number:
            return str(entry.get("status", ""))
    return ""


def _step_observed(result: dict[str, object], step_number: int) -> str:
    steps = result.get("steps")
    if not isinstance(steps, list):
        return "<missing>"
    for entry in steps:
        if isinstance(entry, dict) and entry.get("step") == step_number:
            return str(entry.get("observed", "<missing>"))
    return "<missing>"


def _job_list_summary(jobs: list[GitHubActionsWorkflowJobObservation]) -> str:
    if not jobs:
        return "<none>"
    return "; ".join(_single_job_summary(job) for job in jobs)


def _single_job_summary(job: GitHubActionsWorkflowJobObservation | None) -> str:
    if job is None:
        return "<none>"
    return (
        f"{job.name} [status={job.status or '<none>'}, "
        f"conclusion={job.conclusion or '<none>'}]"
    )


def _job_list_from_result(result: dict[str, object]) -> str:
    jobs = result.get("workflow_jobs")
    if not isinstance(jobs, list):
        return "<none>"
    parts: list[str] = []
    for entry in jobs:
        if not isinstance(entry, dict):
            continue
        parts.append(
            f"{entry.get('name', '<none>')} [status={entry.get('status', '<none>')}, "
            f"conclusion={entry.get('conclusion', '<none>')}]"
        )
    return "; ".join(parts) or "<none>"


def _nested_string(result: dict[str, object], path: list[str]) -> str | None:
    current: object = result
    for segment in path:
        if not isinstance(current, dict):
            return None
        current = current.get(segment)
    return str(current) if current is not None else None


def _snippet(text: str, *, limit: int) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1] + "…"


def _jira_inline(value: str) -> str:
    return (
        value.replace("{", "\\{")
        .replace("}", "\\}")
        .replace("[", "\\[")
        .replace("]", "\\]")
    )


if __name__ == "__main__":
    main()
