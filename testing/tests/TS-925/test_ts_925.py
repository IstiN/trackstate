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
from testing.core.config.github_accessibility_pull_request_gate_config import (  # noqa: E402
    GitHubAccessibilityPullRequestGateConfig,
)
from testing.core.interfaces.github_accessibility_pull_request_gate_probe import (  # noqa: E402
    GitHubAccessibilityPullRequestGateObservation,
)
from testing.core.interfaces.github_actions_preflight_gate_probe import (  # noqa: E402
    GitHubActionsWorkflowJobObservation,
)
from testing.tests.support.github_accessibility_pull_request_gate_probe_factory import (  # noqa: E402
    create_github_accessibility_pull_request_gate_probe,
)
from testing.tests.support.github_actions_page_factory import (  # noqa: E402
    create_github_actions_page,
)

TICKET_KEY = "TS-925"
TEST_CASE_TITLE = (
    "Accessibility audit failure — CI pipeline blocks subsequent deployment stages"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-925/test_ts_925.py"
TEST_FILE_PATH = "testing/tests/TS-925/test_ts_925.py"
CONFIG_PATH = REPO_ROOT / "testing/tests/TS-925/config.yaml"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
REVIEW_REPLIES_PATH = OUTPUTS_DIR / "review_replies.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
RUN_SCREENSHOT_PATH = OUTPUTS_DIR / "ts925_run_page.png"
DISCUSSIONS_RAW_PATH = REPO_ROOT / "input" / TICKET_KEY / "pr_discussions_raw.json"

REQUEST_STEPS = [
    "Create a Pull Request that introduces a WCAG AA contrast violation (ratio below 4.5:1).",
    "Push the changes to trigger the CI pipeline.",
    "Monitor the workflow execution in the GitHub Actions UI.",
    "Check the status of the 'deploy' or 'publish' stage after the accessibility audit fails.",
]
EXPECTED_RESULT = (
    "The accessibility audit fails, and the subsequent deployment stage is skipped "
    "or blocked, preventing any code from being deployed."
)
FAILURE_CONCLUSIONS = {"failure", "cancelled", "timed_out", "action_required"}


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    raw_config = _load_yaml(CONFIG_PATH)
    runtime_inputs = raw_config.get("runtime_inputs", {})
    assert isinstance(runtime_inputs, dict)
    config = GitHubAccessibilityPullRequestGateConfig.from_file(CONFIG_PATH)
    probe = create_github_accessibility_pull_request_gate_probe(
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
    blocked_job_conclusions = {
        item.lower()
        for item in _string_list(
            runtime_inputs,
            "blocked_job_conclusions",
            default=["skipped", "cancelled", "neutral"],
        )
    }
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
        "browser": "Chromium (Playwright required)",
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
        except Exception as page_error:  # keep deployment assertions running
            run_page_error = f"{type(page_error).__name__}: {page_error}"

        result["workflow_contract"] = asdict(observation.target_workflow)
        result["workflow_jobs"] = [asdict(job) for job in jobs]
        result["accessibility_job"] = (
            None if accessibility_job is None else asdict(accessibility_job)
        )
        result["downstream_job"] = None if downstream_job is None else asdict(downstream_job)
        result["run_page"] = None if run_page is None else asdict(run_page)
        result["run_page_error"] = run_page_error
        if run_page is not None:
            result["browser"] = "Chromium (Playwright)"

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
        _evaluate_downstream_gate(
            result,
            observation=observation,
            jobs=jobs,
            accessibility_job=accessibility_job,
            downstream_job=downstream_job,
            blocked_job_conclusions=blocked_job_conclusions,
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
    print("TS-925 passed")


def _evaluate_pr_probe(
    result: dict[str, object],
    observation: GitHubAccessibilityPullRequestGateObservation,
    failures: list[str],
) -> None:
    step_failures: list[str] = []
    if observation.pull_request_probe_path not in observation.pull_request_file_paths:
        step_failures.append(
            "GitHub did not record the expected probe file in the disposable PR artifact."
        )
    if not observation.probe_rendered_in_application:
        step_failures.append(
            "the disposable PR did not wire the low-contrast probe into a rendered app surface."
        )
    if not observation.probe_contains_low_contrast_indicator:
        step_failures.append(
            "the disposable PR probe did not contain the requested low-contrast signal."
        )

    if step_failures:
        message = (
            "Step 1 failed: "
            + " ".join(step_failures)
            + "\n"
            + f"Pull Request URL: {observation.pull_request_url}\n"
            + f"Observed PR files: {observation.pull_request_file_paths}\n"
            + f"Probe technique: {observation.probe_contrast_technique}"
        )
        failures.append(message)
        _record_step(result, step=1, status="failed", action=REQUEST_STEPS[0], observed=message)
        return

    observed = (
        "Created a disposable PR and verified that GitHub recorded the rendered low-contrast "
        f"probe file `{observation.pull_request_probe_path}`.\n"
        f"Pull Request URL: {observation.pull_request_url}\n"
        f"Observed PR files: {observation.pull_request_file_paths}\n"
        f"Render host: {observation.probe_render_host_path}\n"
        f"Probe technique: {observation.probe_contrast_technique}\n"
        "Note: the shared live probe also includes a weak semantics label, but the "
        "fail-fast assertion for TS-925 is driven by the requested contrast violation."
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
            "Opened the live GitHub Actions run page and reviewed the visible workflow/job text "
            "as a maintainer would."
        ),
        observed=(
            f"Run page URL: `{run_page.url}`; matched text: `{run_page.matched_text}`; "
            f"visible body excerpt: `{_snippet(run_page.body_text, limit=900)}`; screenshot: "
            f"`{run_page.screenshot_path or '<none>'}`."
        ),
    )

    if not run_page.screenshot_path:
        message = (
            "Step 3 failed: the GitHub Actions run page opened, but browser-backed UI "
            "evidence was not captured.\n"
            f"Run URL: {run_page.url}\n"
            f"Matched text: {run_page.matched_text}\n"
            f"Visible body excerpt: {_snippet(run_page.body_text, limit=1200)}\n"
            "Screenshot: <none>"
        )
        failures.append(message)
        _record_step(result, step=3, status="failed", action=REQUEST_STEPS[2], observed=message)
        return

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


def _evaluate_downstream_gate(
    result: dict[str, object],
    *,
    observation: GitHubAccessibilityPullRequestGateObservation,
    jobs: list[GitHubActionsWorkflowJobObservation],
    accessibility_job: GitHubActionsWorkflowJobObservation | None,
    downstream_job: GitHubActionsWorkflowJobObservation | None,
    blocked_job_conclusions: set[str],
    failures: list[str],
) -> None:
    accessibility_failure_visible = _accessibility_audit_failure_visible(
        observation,
        accessibility_job=accessibility_job,
    )

    _record_human_verification(
        result,
        check=(
            "Compared the live job list and conclusions to what a user would infer from the run "
            "page and the run log."
        ),
        observed=(
            f"Observed jobs: {_job_list_summary(jobs)}; accessibility job: "
            f"{_single_job_summary(accessibility_job)}; downstream job: "
            f"{_single_job_summary(downstream_job)}; run-log contrast markers: "
            f"{observation.run_log_matched_contrast_markers}; run-log accessibility markers: "
            f"{observation.run_log_matched_accessibility_markers}; observed steps: "
            f"{observation.observed_step_names}; run-log excerpt: "
            f"`{observation.run_log_excerpt or '<none>'}`."
        ),
    )

    if not accessibility_failure_visible:
        message = (
            "Step 4 failed: the live workflow did not expose a verifiable accessibility audit "
            "failure for the disposable contrast defect.\n"
            f"Accessibility job: {_single_job_summary(accessibility_job)}\n"
            "Accessibility check conclusion: "
            f"{observation.accessibility_status_check_conclusion or '<none>'}\n"
            f"Observed steps: {observation.observed_step_names}\n"
            "Run-log accessibility markers: "
            f"{observation.run_log_matched_accessibility_markers}\n"
            f"Run conclusion: {observation.latest_pull_request_run_conclusion}\n"
            f"Failed status checks: {observation.failed_status_check_names}\n"
            f"Run-log contrast markers: {observation.run_log_matched_contrast_markers}\n"
            f"Run log excerpt: {observation.run_log_excerpt or '<none>'}\n"
            f"Run URL: {observation.latest_pull_request_run_url}"
        )
        failures.append(message)
        _record_step(result, step=4, status="failed", action=REQUEST_STEPS[3], observed=message)
        return

    if not observation.target_workflow_downstream_job_names:
        message = (
            "Step 4 failed: the target workflow does not define any downstream deploy/publish "
            "stage to block after the accessibility audit fails.\n"
            f"Workflow path: {observation.target_workflow_path}\n"
            f"Workflow jobs: {observation.target_workflow_job_names}\n"
            f"Observed run jobs: {_job_list_summary(jobs)}\n"
            f"Run URL: {observation.latest_pull_request_run_url}"
        )
        failures.append(message)
        _record_step(result, step=4, status="failed", action=REQUEST_STEPS[3], observed=message)
        return

    if not observation.target_workflow_downstream_job_depends_on_accessibility:
        message = (
            "Step 4 failed: the workflow defines a deploy/publish stage, but it is not wired "
            "to depend on the accessibility audit job.\n"
            f"Accessibility jobs in workflow: {observation.target_workflow_accessibility_job_names}\n"
            f"Downstream jobs in workflow: {observation.target_workflow_downstream_job_names}\n"
            f"Run URL: {observation.latest_pull_request_run_url}"
        )
        failures.append(message)
        _record_step(result, step=4, status="failed", action=REQUEST_STEPS[3], observed=message)
        return

    if downstream_job is None:
        message = (
            "Step 4 failed: the workflow contract defines a downstream deploy/publish stage, "
            "but the live run did not expose that stage in the job list after the accessibility "
            "audit failed.\n"
            f"Workflow downstream jobs: {observation.target_workflow_downstream_job_names}\n"
            f"Observed run jobs: {_job_list_summary(jobs)}\n"
            f"Run URL: {observation.latest_pull_request_run_url}"
        )
        failures.append(message)
        _record_step(result, step=4, status="failed", action=REQUEST_STEPS[3], observed=message)
        return

    downstream_conclusion = (downstream_job.conclusion or "").lower()
    if downstream_conclusion not in blocked_job_conclusions:
        message = (
            "Step 4 failed: the downstream deploy/publish stage was exposed, but it was not "
            "blocked after the accessibility audit failure.\n"
            f"Accessibility job: {_single_job_summary(accessibility_job)}\n"
            f"Downstream job: {_single_job_summary(downstream_job)}\n"
            f"Blocked conclusions expected: {sorted(blocked_job_conclusions)}\n"
            f"Run URL: {observation.latest_pull_request_run_url}"
        )
        failures.append(message)
        _record_step(result, step=4, status="failed", action=REQUEST_STEPS[3], observed=message)
        return

    observed = (
        "The accessibility audit failed for the disposable contrast defect, and the downstream "
        "deploy/publish stage remained blocked.\n"
        f"Accessibility job: {_single_job_summary(accessibility_job)}\n"
        f"Downstream job: {_single_job_summary(downstream_job)}\n"
        f"Workflow downstream jobs: {observation.target_workflow_downstream_job_names}"
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


def _accessibility_audit_failure_visible(
    observation: GitHubAccessibilityPullRequestGateObservation,
    *,
    accessibility_job: GitHubActionsWorkflowJobObservation | None,
) -> bool:
    accessibility_failure_surface_visible = (
        accessibility_job is not None
        and (accessibility_job.conclusion or "").lower() in FAILURE_CONCLUSIONS
    ) or (
        (observation.accessibility_status_check_conclusion or "").lower() in FAILURE_CONCLUSIONS
    )
    audit_step_visible = "Run axe-core accessibility checks" in observation.observed_step_names
    run_log_excerpt = (observation.run_log_excerpt or "").lower()
    audit_log_visible = (
        bool(observation.run_log_matched_accessibility_markers)
        and (
            "axe-core"
            in {marker.lower() for marker in observation.run_log_matched_accessibility_markers}
            or "run axe-core accessibility checks" in run_log_excerpt
            or "npm run test:a11y" in run_log_excerpt
        )
    )
    return (
        accessibility_failure_surface_visible
        and audit_step_visible
        and audit_log_visible
        and bool(observation.run_log_matched_contrast_markers)
    )


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
    REVIEW_REPLIES_PATH.write_text(
        _review_replies_payload(result, passed=True),
        encoding="utf-8",
    )


def _write_failure_outputs(result: dict[str, object]) -> None:
    error = str(result.get("error", "AssertionError: TS-925 failed"))
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
        "* Created a disposable pull request against the live repository with the rendered accessibility probe path used for the deployed PR accessibility gate.",
        "* Waited for the live pull-request GitHub Actions workflow run and read its status checks, jobs, and logs.",
        "* Opened the live run page for human-style verification and recorded visible page evidence.",
        "* Checked whether a downstream deploy or publish stage existed and whether it stayed blocked after the accessibility failure.",
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
        "- Created a disposable pull request against the live repository with the rendered accessibility probe path used for the deployed PR accessibility gate.",
        "- Waited for the live pull-request GitHub Actions workflow run and read its status checks, jobs, and logs.",
        "- Opened the live run page for human-style verification and recorded visible page evidence.",
        "- Checked whether a downstream deploy or publish stage existed and whether it stayed blocked after the accessibility failure.",
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
            f"`{result['default_branch']}`, browser `{result['browser']}`, "
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
        "- Fixed the TS-925 review findings by requiring Playwright-backed GitHub Actions UI evidence for Step 3 and by distinguishing non-verifiable audit runs from real gate-pass regressions in the failure bug output.",
        "- Reused the TS-925 live automation to create a disposable pull request, inspect the GitHub Actions jobs/logs, and record browser-captured run-page evidence.",
        "- Verified the scenario from the user-visible GitHub Actions UI in addition to the shared workflow/job assertions.",
        f"- Test case: **{TICKET_KEY} - {TEST_CASE_TITLE}**",
        f"- Result: **{status}**",
        f"- Command: `{RUN_COMMAND}`",
        (
            f"- Environment: `{result['repository']}` @ `{result['default_branch']}` "
            f"using {result['browser']} on `{result['os']}`."
        ),
        (
            "- Outcome: the accessibility failure blocked the downstream deploy/publish stage."
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


def _review_replies_payload(result: dict[str, object], *, passed: bool) -> str:
    replies = [
        {
            "inReplyToId": thread.get("rootCommentId"),
            "threadId": thread.get("threadId"),
            "reply": _review_reply_text(
                root_comment_id=thread.get("rootCommentId"),
                passed=passed,
                result=result,
            ),
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
        and thread.get("rootCommentId") is not None
        and thread.get("threadId") is not None
    ]


def _review_reply_text(
    *,
    root_comment_id: object,
    passed: bool,
    result: dict[str, object],
) -> str:
    rerun_summary = (
        f"Re-ran `{RUN_COMMAND}`: passed (`1 passed, 0 failed`)."
        if passed
        else f"Re-ran `{RUN_COMMAND}`: failed with `{result.get('error', 'unknown error')}`."
    )
    if root_comment_id == 3286778457:
        return (
            "Fixed: Step 4 now uses `observation.target_workflow` from the shared "
            "accessibility probe, so the downstream deploy/publish contract comes from the "
            "same live default-branch workflow artifact that produced the observed run "
            "instead of reparsing the reviewer checkout. "
            f"{rerun_summary}"
        )
    if root_comment_id == 3286778579:
        return (
            "Fixed: TS-925 no longer reaches for `gh api` in the test layer. The shared "
            "probe now exposes `observation.observed_run_jobs`, and the test consumes that "
            "component-owned run-job observation directly. "
            f"{rerun_summary}"
        )
    if root_comment_id == 3287294164:
        return (
            "Fixed: the shared accessibility probe now preserves the original `runApp(...)` "
            "child expression when patching multiline entrypoints, so the injected "
            "`_Ts908RenderedProbeApp` still receives a valid `child` and the disposable PR "
            "build can reach the hosted audit. "
            f"{rerun_summary}"
        )
    if root_comment_id == 3287294301:
        return (
            "Fixed: TS-925 now requires explicit accessibility-audit execution evidence "
            "before Step 4 can classify the result as a downstream-gate product gap. The "
            "test only proceeds when the hosted run shows the axe-core step/log surface in "
            "addition to the failing accessibility result and contrast evidence. "
            f"{rerun_summary}"
        )
    if root_comment_id == 3289497756:
        return (
            "Fixed: Step 3 once again requires Playwright-backed GitHub Actions UI "
            "verification. The default run-page factory now errors when the Playwright "
            "runtime is unavailable, and TS-925 also fails Step 3 if no browser screenshot "
            "evidence is captured. "
            f"{rerun_summary}"
        )
    if root_comment_id == 3289497864:
        return (
            "Fixed: the failed-result bug output now distinguishes a real "
            "\"accessibility gate passed the low-contrast defect\" regression from "
            "non-verifiable audit runs where the hosted workflow never produced trustworthy "
            "failure evidence. "
            f"{rerun_summary}"
        )
    return (
        "Fixed: TS-925 now keeps both the workflow contract and live run-job retrieval in "
        "the shared accessibility probe/component layer, preserving the intended test "
        "architecture. "
        f"{rerun_summary}"
    )


def _bug_description(result: dict[str, object]) -> str:
    failed_summary = _failed_step_summary(result)
    step_4_mode = _step_4_failure_mode(result)
    if step_4_mode == "audit-passed-defect":
        title = (
            f"# {TICKET_KEY} - Accessibility gate passes a low-contrast PR, so deployment is not blocked"
        )
        actual_result = (
            "- The disposable PR rendered the low-contrast probe and the accessibility audit "
            "ran, but `Accessibility checks` concluded success instead of failing for the "
            "contrast defect, so the downstream deploy/publish stage was not blocked."
        )
        missing_capability = (
            "- The production accessibility gate does not fail a live pull request that "
            "renders the low-contrast Flutter probe used by this test case, so the CI "
            "workflow cannot demonstrate fail-fast blocking on the requested contrast defect."
        )
    elif step_4_mode == "audit-not-verifiable":
        title = (
            f"# {TICKET_KEY} - Accessibility audit does not expose a verifiable result for the disposable contrast defect"
        )
        actual_result = (
            "- The disposable PR rendered the low-contrast probe, but the workflow run did "
            "not expose trustworthy accessibility-audit failure evidence for that defect, so "
            "the downstream deployment behavior could not be verified from the live run."
        )
        missing_capability = (
            "- The production CI workflow does not reliably surface a contributor-verifiable "
            "accessibility-audit result for the disposable low-contrast probe used by this "
            "test case."
        )
    else:
        title = (
            f"# {TICKET_KEY} - Accessibility failure does not block a downstream deployment stage"
        )
        actual_result = (
            "- The accessibility failure was observed, but the workflow did not provide a "
            "downstream deploy/publish stage that was visibly skipped or blocked after that "
            "failure."
            if _step_status(result, 4) != "passed"
            else "- The downstream deploy/publish stage was visibly blocked after the accessibility failure."
        )
        missing_capability = (
            "- The production workflow does not expose a downstream deploy/publish stage that "
            "is visibly blocked after the accessibility audit fails."
        )
    return "\n".join(
        [
            title,
            "",
            "## Steps to reproduce",
            (
                "1. ✅ Create a Pull Request that introduces a WCAG AA contrast violation "
                "(ratio below 4.5:1)."
                if _step_status(result, 1) == "passed"
                else "1. ❌ Create a Pull Request that introduces a WCAG AA contrast violation "
                "(ratio below 4.5:1)."
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
                "4. ✅ Check the status of the 'deploy' or 'publish' stage after the accessibility audit fails."
                if _step_status(result, 4) == "passed"
                else "4. ❌ Check the status of the 'deploy' or 'publish' stage after the accessibility audit fails."
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
            actual_result,
            "",
            "## Missing / broken production capability",
            missing_capability,
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
            f"- Browser: `{result.get('browser', 'Chromium (Playwright required)')}`",
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


def _step_4_failure_mode(result: dict[str, object]) -> str:
    step_4_observed = _step_observed(result, 4)
    if _step_status(result, 4) == "passed":
        return "passed"
    if "did not expose a verifiable accessibility audit failure" in step_4_observed:
        return (
            "audit-passed-defect"
            if _audit_ran_but_concluded_success(result)
            else "audit-not-verifiable"
        )
    return "downstream-gate"


def _audit_ran_but_concluded_success(result: dict[str, object]) -> bool:
    observed_steps = result.get("observed_step_names")
    audit_step_visible = isinstance(observed_steps, list) and (
        "Run axe-core accessibility checks" in observed_steps
    )
    accessibility_markers = result.get("run_log_matched_accessibility_markers")
    has_accessibility_markers = isinstance(accessibility_markers, list) and bool(
        accessibility_markers
    )
    contrast_markers = result.get("run_log_matched_contrast_markers")
    has_contrast_markers = isinstance(contrast_markers, list) and bool(contrast_markers)
    accessibility_conclusion = str(
        result.get("accessibility_status_check_conclusion", "")
    ).lower()
    return (
        audit_step_visible
        and has_accessibility_markers
        and has_contrast_markers
        and accessibility_conclusion == "success"
    )


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
        lines.append((prefix if jira else "  - ") + observed)
    return lines


def _failed_step_summary(result: dict[str, object]) -> str:
    steps = result.get("steps")
    if not isinstance(steps, list):
        return str(result.get("error", "the automation failed before step-level reporting"))
    failed_steps = [
        entry for entry in steps if isinstance(entry, dict) and entry.get("status") == "failed"
    ]
    if not failed_steps:
        return str(result.get("error", "the automation failed without a failed step summary"))
    def _summary_line(entry: dict[str, object]) -> str:
        first_line = str(entry.get("observed", "")).splitlines()[0]
        prefix = f"Step {entry.get('step')} failed: "
        if first_line.startswith(prefix):
            return first_line
        return prefix + first_line
    summaries = [
        _summary_line(entry)
        for entry in failed_steps
    ]
    return " ".join(summaries)


def _step_status(result: dict[str, object], step: int) -> str | None:
    steps = result.get("steps")
    if not isinstance(steps, list):
        return None
    for entry in steps:
        if isinstance(entry, dict) and entry.get("step") == step:
            return str(entry.get("status", "")).lower() or None
    return None


def _step_observed(result: dict[str, object], step: int) -> str:
    steps = result.get("steps")
    if not isinstance(steps, list):
        return str(result.get("error", "<no step observation recorded>"))
    for entry in steps:
        if isinstance(entry, dict) and entry.get("step") == step:
            return str(entry.get("observed", "<no observation recorded>"))
    return str(result.get("error", "<no step observation recorded>"))


def _job_list_summary(jobs: list[GitHubActionsWorkflowJobObservation]) -> str:
    if not jobs:
        return "<none>"
    return ", ".join(_single_job_summary(job) for job in jobs)


def _single_job_summary(job: GitHubActionsWorkflowJobObservation | None) -> str:
    if job is None:
        return "<missing>"
    return (
        f"{job.name} (status={job.status or '<none>'}, "
        f"conclusion={job.conclusion or '<none>'})"
    )


def _job_list_from_result(result: dict[str, object]) -> str:
    raw_jobs = result.get("workflow_jobs")
    if not isinstance(raw_jobs, list):
        return "<none>"
    summaries: list[str] = []
    for entry in raw_jobs:
        if not isinstance(entry, dict):
            continue
        summaries.append(
            f"{entry.get('name', '<missing>')} "
            f"(status={entry.get('status', '<none>')}, "
            f"conclusion={entry.get('conclusion', '<none>')})"
        )
    return ", ".join(summaries) or "<none>"


def _nested_string(result: dict[str, object], path: list[str]) -> str | None:
    current: object = result
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current if isinstance(current, str) and current else None


def _jira_inline(text: str) -> str:
    return text.replace("{", "\\{").replace("}", "\\}")


def _optional_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _snippet(text: str, *, limit: int) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3] + "..."


if __name__ == "__main__":
    main()
