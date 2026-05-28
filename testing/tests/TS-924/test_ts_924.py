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

from testing.components.services.github_accessibility_compliant_pull_request_gate_probe import (  # noqa: E402
    GitHubAccessibilityCompliantPullRequestGateProbeService,
)
from testing.core.config.github_accessibility_pull_request_gate_config import (  # noqa: E402
    GitHubAccessibilityPullRequestGateConfig,
)
from testing.core.interfaces.github_accessibility_pull_request_gate_probe import (  # noqa: E402
    GitHubAccessibilityPullRequestGateObservation,
)
from testing.tests.support.github_accessibility_compliant_pull_request_gate_probe_factory import (  # noqa: E402
    create_github_accessibility_compliant_pull_request_gate_probe,
)

TICKET_KEY = "TS-924"
TEST_CASE_TITLE = "Push PR with WCAG AA compliant UI — accessibility gate passes"
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-924/test_ts_924.py"
TEST_FILE_PATH = "testing/tests/TS-924/test_ts_924.py"
CONFIG_PATH = REPO_ROOT / "testing/tests/TS-924/config.yaml"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"

REQUEST_STEPS = [
    "Create a Pull Request that introduces a UI element with a text-to-background contrast ratio of exactly 4.5:1 or higher.",
    "Ensure the component includes a descriptive ARIA/semantics label.",
    "Push the changes to trigger the CI pipeline.",
    "Inspect the 'accessibility-audit' stage and the overall PR status check.",
]
EXPECTED_RESULT = (
    "The accessibility gate stage passes successfully, and the Pull Request is not "
    "blocked by the accessibility status check."
)
SUCCESS_CONCLUSIONS = {"success"}


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    config = GitHubAccessibilityPullRequestGateConfig.from_file(CONFIG_PATH)
    probe = create_github_accessibility_compliant_pull_request_gate_probe(
        REPO_ROOT,
        config_path=CONFIG_PATH,
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

        failures: list[str] = []
        _evaluate_disposable_pull_request(result, observation, failures)
        _evaluate_compliant_component(result, observation, failures)
        _evaluate_ci_trigger(result, observation, failures)
        _evaluate_accessibility_gate_result(result, observation, failures)

        if failures:
            raise AssertionError("\n".join(failures))
    except Exception as error:
        result.setdefault("error", f"{type(error).__name__}: {error}")
        result.setdefault("traceback", traceback.format_exc())
        _write_failure_outputs(result)
        raise

    _write_pass_outputs(result)
    print("TS-924 passed")


def _evaluate_disposable_pull_request(
    result: dict[str, object],
    observation: GitHubAccessibilityPullRequestGateObservation,
    failures: list[str],
) -> None:
    if observation.pull_request_probe_path not in observation.pull_request_file_paths:
        message = (
            "Step 1 failed: the disposable Pull Request was created, but GitHub did not "
            "report the expected compliant probe file in the PR artifact.\n"
            f"Pull Request URL: {observation.pull_request_url}\n"
            f"Expected file: {observation.pull_request_probe_path}\n"
            f"Observed PR files: {observation.pull_request_file_paths}"
        )
        failures.append(message)
        _record_step(
            result,
            step=1,
            status="failed",
            action=REQUEST_STEPS[0],
            observed=message,
        )
        return

    observed = (
        "Created a disposable PR and verified that GitHub recorded the real compliant "
        f"probe file `{observation.pull_request_probe_path}` on that PR.\n"
        f"Pull Request URL: {observation.pull_request_url}\n"
        f"Observed PR files: {observation.pull_request_file_paths}"
    )
    _record_step(result, step=1, status="passed", action=REQUEST_STEPS[0], observed=observed)


def _evaluate_compliant_component(
    result: dict[str, object],
    observation: GitHubAccessibilityPullRequestGateObservation,
    failures: list[str],
) -> None:
    if not observation.probe_rendered_in_application:
        message = (
            "Step 2 failed: the disposable PR did not wire the compliant probe into a "
            "rendered application surface.\n"
            f"Probe file: {observation.pull_request_probe_path}\n"
            f"Expected render host: {observation.probe_render_host_path}\n"
            f"Observed PR files: {observation.pull_request_file_paths}"
        )
        failures.append(message)
        _record_step(
            result,
            step=2,
            status="failed",
            action=REQUEST_STEPS[1],
            observed=message,
        )
        return
    if observation.probe_contains_low_contrast_indicator:
        message = (
            "Step 2 failed: the disposable PR probe still contains the low-contrast "
            "indicator used by the failing accessibility regression.\n"
            f"Probe file: {observation.pull_request_probe_path}\n"
            f"Observed contrast technique: {observation.probe_contrast_technique}"
        )
        failures.append(message)
        _record_step(
            result,
            step=2,
            status="failed",
            action=REQUEST_STEPS[1],
            observed=message,
        )
        return
    if observation.probe_semantic_label != GitHubAccessibilityCompliantPullRequestGateProbeService.expected_semantic_label:
        message = (
            "Step 2 failed: the disposable PR probe did not use the expected descriptive "
            "semantics label.\n"
            f"Expected label: "
            f"{GitHubAccessibilityCompliantPullRequestGateProbeService.expected_semantic_label!r}\n"
            f"Observed label: {observation.probe_semantic_label!r}"
        )
        failures.append(message)
        _record_step(
            result,
            step=2,
            status="failed",
            action=REQUEST_STEPS[1],
            observed=message,
        )
        return
    if not observation.runtime_accessibility_surface_present:
        message = (
            "Step 2 failed: the accessibility run never exposed browser-visible runtime "
            "semantics evidence for the compliant probe, so the descriptive label could "
            "not be verified on the actual rendered surface.\n"
            f"Run URL: {observation.latest_pull_request_run_url or '<none>'}\n"
            f"Runtime accessibility evidence: "
            f"{observation.runtime_accessibility_surface_summary or '<none>'}\n"
            f"Run log excerpt: {observation.run_log_excerpt or '<none>'}"
        )
        failures.append(message)
        _record_step(
            result,
            step=2,
            status="failed",
            action=REQUEST_STEPS[1],
            observed=message,
        )
        return
    if not _runtime_accessibility_surface_includes_label(
        observation.runtime_accessibility_surface_summary,
        observation.probe_semantic_label,
    ):
        message = (
            "Step 2 failed: the runtime accessibility evidence did not include the "
            "expected descriptive semantics label for the compliant probe.\n"
            f"Expected label: {observation.probe_semantic_label!r}\n"
            f"Runtime accessibility evidence: "
            f"{observation.runtime_accessibility_surface_summary or '<none>'}\n"
            f"Run URL: {observation.latest_pull_request_run_url or '<none>'}\n"
            f"Run log excerpt: {observation.run_log_excerpt or '<none>'}"
        )
        failures.append(message)
        _record_step(
            result,
            step=2,
            status="failed",
            action=REQUEST_STEPS[1],
            observed=message,
        )
        return

    observed = (
        "The disposable PR renders the compliant probe through "
        f"`{observation.probe_render_host_path}` and keeps the requested user-facing "
        "accessibility characteristics: no low-contrast indicator, the descriptive "
        f"semantics label `{observation.probe_semantic_label}`, and browser-visible "
        "runtime accessibility output.\n"
        f"Contrast technique: {observation.probe_contrast_technique}\n"
        f"Runtime accessibility evidence: {observation.runtime_accessibility_surface_summary}"
    )
    _record_step(result, step=2, status="passed", action=REQUEST_STEPS[1], observed=observed)


def _evaluate_ci_trigger(
    result: dict[str, object],
    observation: GitHubAccessibilityPullRequestGateObservation,
    failures: list[str],
) -> None:
    if observation.latest_pull_request_run_id is None:
        message = (
            "Step 3 failed: GitHub Actions did not expose a contributor-visible "
            "`pull_request` workflow run for the disposable PR branch.\n"
            f"Pull Request URL: {observation.pull_request_url}\n"
            f"Branch: {observation.pull_request_head_branch}\n"
            f"Observed branch runs: {observation.observed_branch_run_names}\n"
            f"Observed run URLs: {observation.observed_branch_run_urls}"
        )
        failures.append(message)
        _record_step(
            result,
            step=3,
            status="failed",
            action=REQUEST_STEPS[2],
            observed=message,
        )
        return
    if observation.latest_pull_request_run_event != "pull_request":
        message = (
            "Step 3 failed: the observed workflow run was not triggered by the disposable "
            "Pull Request.\n"
            f"Run URL: {observation.latest_pull_request_run_url}\n"
            f"Observed event: {observation.latest_pull_request_run_event}"
        )
        failures.append(message)
        _record_step(
            result,
            step=3,
            status="failed",
            action=REQUEST_STEPS[2],
            observed=message,
        )
        return

    observed = (
        "GitHub Actions executed the real PR workflow for the disposable branch.\n"
        f"Run URL: {observation.latest_pull_request_run_url}\n"
        f"Status: {observation.latest_pull_request_run_status}\n"
        f"Conclusion: {observation.latest_pull_request_run_conclusion or '<pending>'}"
    )
    _record_step(result, step=3, status="passed", action=REQUEST_STEPS[2], observed=observed)


def _evaluate_accessibility_gate_result(
    result: dict[str, object],
    observation: GitHubAccessibilityPullRequestGateObservation,
    failures: list[str],
) -> None:
    workflow_succeeded = observation.latest_pull_request_run_conclusion in SUCCESS_CONCLUSIONS
    overall_status_succeeded = observation.pull_request_status_state in SUCCESS_CONCLUSIONS
    no_failed_status_checks = not observation.failed_status_check_names
    accessibility_runtime_step_present = (
        "Run axe-core accessibility checks" in observation.observed_step_names
    )
    accessibility_check_passed = (
        observation.accessibility_status_check_conclusion in SUCCESS_CONCLUSIONS
        if observation.accessibility_status_check_name
        else False
    )
    accessibility_surface_present = bool(
        observation.accessibility_status_check_name
        or {"Accessibility checks", "Run axe-core accessibility checks"}
        & set(observation.observed_status_check_names + observation.observed_job_names + observation.observed_step_names)
    )
    accessibility_result_passed = (
        accessibility_check_passed
        if observation.accessibility_status_check_name
        else accessibility_runtime_step_present and workflow_succeeded
    )

    _record_human_verification(
        result,
        check=(
            "Inspected the disposable PR checks surface and the live workflow run output "
            "through GitHub CLI (`gh pr view`, `gh run view --log`) the same way a "
            "reviewer would confirm whether the PR is blocked."
        ),
        observed=(
            f"PR checks URL: `{observation.pull_request_checks_url}`; run URL: "
            f"`{observation.latest_pull_request_run_url}`; observed status checks: "
            f"{observation.observed_status_check_names or ['<none>']}; observed workflow "
            f"names: {observation.observed_status_check_workflow_names or ['<none>']}; "
            f"observed jobs: {observation.observed_job_names or ['<none>']}; observed "
            f"steps: {observation.observed_step_names or ['<none>']}; mergeable state: "
            f"`{observation.pull_request_mergeable_state or '<none>'}`; overall PR status: "
            f"`{observation.pull_request_status_state or '<none>'}`; accessibility check: "
            f"`{observation.accessibility_status_check_name or '<none>'}` with conclusion "
            f"`{observation.accessibility_status_check_conclusion or '<none>'}`; runtime "
            f"accessibility evidence: `{observation.runtime_accessibility_surface_summary or '<none>'}`."
        ),
    )

    if (
        workflow_succeeded
        and overall_status_succeeded
        and no_failed_status_checks
        and accessibility_surface_present
        and accessibility_result_passed
    ):
        observed = (
            "The live PR workflow stayed green and the contributor-visible PR surface was "
            "not blocked by accessibility.\n"
            f"Overall PR status: {observation.pull_request_status_state}\n"
            f"Accessibility check: {observation.accessibility_status_check_name or '<derived from job/step surface>'}\n"
            f"Accessibility check conclusion: {observation.accessibility_status_check_conclusion or '<derived from successful workflow>'}\n"
            f"Runtime accessibility evidence: {observation.runtime_accessibility_surface_summary or '<none>'}\n"
            f"Observed jobs: {observation.observed_job_names or ['<none>']}\n"
            f"Observed steps: {observation.observed_step_names or ['<none>']}"
        )
        _record_step(result, step=4, status="passed", action=REQUEST_STEPS[3], observed=observed)
        return

    message = (
        "Step 4 failed: the disposable PR reached the real workflow/check surface, but "
        "GitHub did not expose a passing accessibility result plus an unblocked overall "
        "PR status for the compliant scenario.\n"
        f"Pull Request URL: {observation.pull_request_url}\n"
        f"PR checks URL: {observation.pull_request_checks_url}\n"
        f"Run URL: {observation.latest_pull_request_run_url}\n"
        f"Run conclusion: {observation.latest_pull_request_run_conclusion}\n"
        f"Overall PR status: {observation.pull_request_status_state}\n"
        f"Accessibility check: {observation.accessibility_status_check_name or '<none>'}\n"
        f"Accessibility workflow: {observation.accessibility_status_check_workflow_name or '<none>'}\n"
        f"Accessibility check conclusion: {observation.accessibility_status_check_conclusion or '<none>'}\n"
        f"Observed status checks: {observation.observed_status_check_names}\n"
        f"Failed status checks: {observation.failed_status_check_names}\n"
        f"Observed workflow names: {observation.observed_status_check_workflow_names}\n"
        f"Observed jobs: {observation.observed_job_names}\n"
        f"Observed steps: {observation.observed_step_names}\n"
        f"Runtime accessibility evidence: {observation.runtime_accessibility_surface_summary or '<none>'}\n"
        f"Matched accessibility markers: {observation.matched_accessibility_markers}\n"
        f"Run-log accessibility markers: {observation.run_log_matched_accessibility_markers}\n"
        f"Run log error: {observation.run_log_error or '<none>'}\n"
        f"Run log excerpt: {observation.run_log_excerpt or '<none>'}"
    )
    failures.append(message)
    _record_step(result, step=4, status="failed", action=REQUEST_STEPS[3], observed=message)


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
    error = str(result.get("error", "AssertionError: TS-924 failed"))
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
        "* Created a disposable pull request against the live repository.",
        "* Patched the app entrypoint so the disposable PR renders a real Flutter probe surface with compliant contrast and a descriptive semantics label.",
        "* Waited for the live pull-request workflow run to execute on that disposable PR.",
        "* Inspected the actual PR checks surface, workflow jobs/steps, and run logs for a passing accessibility result and an unblocked PR status.",
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
        "- Created a disposable pull request against the live repository.",
        "- Patched the app entrypoint so the disposable PR renders a real Flutter probe surface with compliant contrast and a descriptive semantics label.",
        "- Waited for the live pull-request workflow run to execute on that disposable PR.",
        "- Inspected the actual PR checks surface, workflow jobs/steps, and run logs for a passing accessibility result and an unblocked PR status.",
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
        "- Added TS-924 as a disposable PR probe against the live GitHub Actions checks surface.",
        "- The disposable PR renders a compliant accessibility probe through the app entrypoint instead of relying on static workflow inspection.",
        f"- Test case: **{TICKET_KEY} - {TEST_CASE_TITLE}**",
        f"- Result: **{status}**",
        f"- Command: `{RUN_COMMAND}`",
        (
            f"- Environment: `{result['repository']}` @ `{result['default_branch']}` "
            f"using GitHub CLI on `{result['os']}`."
        ),
        (
            "- Outcome: the live PR pipeline surfaced a passing accessibility result and did not block the compliant disposable PR."
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
        f"# {TICKET_KEY} - compliant PR is still blocked or missing a passing accessibility result\n\n"
        "## Steps to reproduce\n"
        f"1. {REQUEST_STEPS[0]}  \n"
        f"   - Actual: {step_map.get(1, {}).get('observed', '<missing>')}  \n"
        f"   - Result: {'PASSED ✅' if step_map.get(1, {}).get('status') == 'passed' else 'FAILED ❌'}\n"
        f"2. {REQUEST_STEPS[1]}  \n"
        f"   - Actual: {step_map.get(2, {}).get('observed', '<missing>')}  \n"
        f"   - Result: {'PASSED ✅' if step_map.get(2, {}).get('status') == 'passed' else 'FAILED ❌'}\n"
        f"3. {REQUEST_STEPS[2]}  \n"
        f"   - Actual: {step_map.get(3, {}).get('observed', '<missing>')}  \n"
        f"   - Result: {'PASSED ✅' if step_map.get(3, {}).get('status') == 'passed' else 'FAILED ❌'}\n"
        f"4. {REQUEST_STEPS[3]}  \n"
        f"   - Actual: {step_map.get(4, {}).get('observed', '<missing>')}  \n"
        "   - Result: FAILED ❌\n\n"
        "## Exact error message or assertion failure\n"
        "```text\n"
        f"{result.get('traceback', result.get('error', '<missing>'))}"
        "```\n\n"
        "## Actual vs Expected\n"
        f"- **Expected:** {EXPECTED_RESULT}\n"
        "- **Actual:** The live PR workflow either failed, left the overall PR status blocked, "
        "or did not expose a contributor-visible passing accessibility result for the "
        "compliant rendered probe.\n\n"
        "## Environment details\n"
        f"- **URL:** {result.get('pull_request_url', '<missing pull request URL>')}\n"
        "- **Browser:** GitHub CLI / GitHub PR checks surface\n"
        f"- **OS:** {result.get('os')}\n"
        f"- **Repository:** {result.get('repository')}\n"
        f"- **Branch:** {result.get('default_branch')}\n"
        f"- **PR checks URL:** {result.get('pull_request_checks_url', '<missing checks URL>')}\n"
        f"- **Workflow run URL:** {result.get('latest_pull_request_run_url', '<missing run URL>')}\n"
        f"- **Run command:** `{result.get('run_command')}`\n"
        f"- **Config:** `{CONFIG_PATH}`\n\n"
        "## Screenshots or logs\n"
        "- **Workflow/log excerpt:**\n"
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


def _runtime_accessibility_surface_includes_label(summary: str, expected_label: str) -> bool:
    normalized_summary = summary.strip()
    normalized_label = expected_label.strip()
    if not normalized_summary or not normalized_label:
        return False

    sample_labels_match = re.search(
        r"sample-labels\s*=\s*(\[[^\]]*\])",
        normalized_summary,
        flags=re.IGNORECASE,
    )
    if sample_labels_match is not None:
        try:
            sample_labels = json.loads(sample_labels_match.group(1))
        except json.JSONDecodeError:
            sample_labels = None
        if isinstance(sample_labels, list):
            return any(str(label) == normalized_label for label in sample_labels)

    return normalized_label in normalized_summary


def _jira_inline(value: str) -> str:
    return (
        value.replace("{", "\\{")
        .replace("}", "\\}")
        .replace("[", "\\[")
        .replace("]", "\\]")
    )


if __name__ == "__main__":
    main()
