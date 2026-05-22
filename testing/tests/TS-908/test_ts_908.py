from __future__ import annotations

import json
import platform
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
from testing.tests.support.github_accessibility_pull_request_gate_probe_factory import (  # noqa: E402
    create_github_accessibility_pull_request_gate_probe,
)

TICKET_KEY = "TS-908"
TEST_CASE_TITLE = (
    "Trigger CI accessibility gate — axe-core identifies contrast and semantic violations"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-908/test_ts_908.py"
TEST_FILE_PATH = "testing/tests/TS-908/test_ts_908.py"
CONFIG_PATH = REPO_ROOT / "testing/tests/TS-908/config.yaml"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"

REQUEST_STEPS = [
    "Create a Pull Request that introduces a UI element with a text-to-background contrast ratio below 4.5:1.",
    "In the same PR, include a component with a non-descriptive ARIA label.",
    "Push the changes to trigger the CI pipeline.",
    "Inspect the results of the automated accessibility check stage.",
]
EXPECTED_RESULT = (
    "The CI stage fails, reporting both the contrast ratio violation and the semantic "
    "label defect."
)
FAILURE_CONCLUSIONS = {"failure", "cancelled", "timed_out", "action_required"}


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    config = GitHubAccessibilityPullRequestGateConfig.from_file(CONFIG_PATH)
    probe = create_github_accessibility_pull_request_gate_probe(
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
        _evaluate_defective_component(result, observation, failures)
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
    print("TS-908 passed")


def _evaluate_disposable_pull_request(
    result: dict[str, object],
    observation: GitHubAccessibilityPullRequestGateObservation,
    failures: list[str],
) -> None:
    if observation.pull_request_probe_path not in observation.pull_request_file_paths:
        message = (
            "Step 1 failed: the disposable Pull Request was created, but GitHub did not "
            "report the expected probe file in the PR artifact.\n"
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
        "Created a disposable PR and verified that GitHub recorded the real probe file "
        f"`{observation.pull_request_probe_path}` on that PR.\n"
        f"Pull Request URL: {observation.pull_request_url}\n"
        f"Observed PR files: {observation.pull_request_file_paths}"
    )
    _record_step(result, step=1, status="passed", action=REQUEST_STEPS[0], observed=observed)


def _evaluate_defective_component(
    result: dict[str, object],
    observation: GitHubAccessibilityPullRequestGateObservation,
    failures: list[str],
) -> None:
    if not observation.probe_rendered_in_application:
        message = (
            "Step 2 failed: the disposable PR did not wire the defective probe into a "
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
    if not observation.probe_contains_low_contrast_indicator:
        message = (
            "Step 2 failed: the disposable PR probe did not include the intended low-contrast "
            "signal.\n"
            f"Probe file: {observation.pull_request_probe_path}"
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
    if not observation.probe_contains_semantic_label_indicator:
        message = (
            "Step 2 failed: the disposable PR probe did not include the intended weak "
            "semantics label.\n"
            f"Probe file: {observation.pull_request_probe_path}"
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
            "Step 2 failed: the live accessibility workflow run did not expose the runtime "
            "accessibility surface summary needed to prove the rendered semantic defect.\n"
            f"Pull Request URL: {observation.pull_request_url}\n"
            f"Run URL: {observation.latest_pull_request_run_url}\n"
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
    matching_runtime_labels, preserved_runtime_labels = _runtime_probe_semantic_labels(
        observation
    )
    if not matching_runtime_labels:
        message = (
            "Step 2 failed: the live runtime accessibility sample labels did not include the "
            "probe's weak semantics label, so the rendered semantic defect was not proven on "
            "the scanned surface.\n"
            f"Probe semantic label: {observation.probe_semantic_label or '<none>'}\n"
            f"Runtime sample labels: {observation.runtime_accessibility_sample_labels or ['<none>']}\n"
            f"Runtime surface summary: {observation.runtime_accessibility_surface_summary or '<none>'}"
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
    if not preserved_runtime_labels:
        message = (
            "Step 2 failed: the live runtime accessibility sample labels still included the "
            "probe's visible text, so the rendered accessible name was not the weak generic "
            "label required by the ticket.\n"
            f"Probe semantic label: {observation.probe_semantic_label or '<none>'}\n"
            f"Probe visible text: {observation.probe_visible_text or '<none>'}\n"
            f"Runtime sample labels: {observation.runtime_accessibility_sample_labels or ['<none>']}\n"
            f"Runtime surface summary: {observation.runtime_accessibility_surface_summary or '<none>'}"
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
        "The disposable PR renders the defective probe through "
        f"`{observation.probe_render_host_path}` and includes both requested defects: a "
        "reduced-contrast text treatment and a non-descriptive semantics label that stays "
        "generic on the runtime accessibility surface.\n"
        f"Probe semantic label: `{observation.probe_semantic_label}`\n"
        f"Probe visible text: `{observation.probe_visible_text}`\n"
        f"Runtime sample labels: {observation.runtime_accessibility_sample_labels}\n"
        f"Contrast technique: {observation.probe_contrast_technique}"
    )
    _record_step(result, step=2, status="passed", action=REQUEST_STEPS[1], observed=observed)


def _runtime_probe_semantic_labels(
    observation: GitHubAccessibilityPullRequestGateObservation,
) -> tuple[list[str], list[str]]:
    semantic_label = observation.probe_semantic_label.strip().lower()
    visible_text = observation.probe_visible_text.strip().lower()
    matching_labels = [
        label
        for label in observation.runtime_accessibility_sample_labels
        if semantic_label and semantic_label in label.lower()
    ]
    preserved_labels = [
        label
        for label in matching_labels
        if not visible_text or visible_text not in label.lower()
    ]
    return matching_labels, preserved_labels


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
    workflow_failed = observation.latest_pull_request_run_conclusion in FAILURE_CONCLUSIONS
    failed_check_surface = workflow_failed or bool(observation.failed_status_check_names)
    real_log_reports_both_defects = (
        _has_explicit_contrast_evidence(observation.run_log_matched_contrast_markers)
        and bool(observation.run_log_matched_semantic_markers)
    )

    _record_human_verification(
        result,
        check=(
            "Inspected the disposable PR checks surface and the live workflow run output "
            "through GitHub CLI (`gh pr view`, `gh run view --log`)."
        ),
        observed=(
            f"PR checks URL: `{observation.pull_request_checks_url}`; run URL: "
            f"`{observation.latest_pull_request_run_url}`; observed status checks: "
            f"{observation.observed_status_check_names or ['<none>']}; observed workflow "
            f"names: {observation.observed_status_check_workflow_names or ['<none>']}; "
            f"failed status checks: {observation.failed_status_check_names or ['<none>']}; "
            f"observed jobs: {observation.observed_job_names or ['<none>']}; observed "
            f"steps: {observation.observed_step_names or ['<none>']}; runtime labels: "
            f"{observation.runtime_accessibility_sample_labels or ['<none>']}; log "
            f"excerpt: `{observation.run_log_excerpt or '<none>'}`."
        ),
    )

    if failed_check_surface and real_log_reports_both_defects:
        observed = (
            "The live PR workflow failure output reported both requested defect classes, even "
            "without relying on a separately named accessibility check.\n"
            f"Failing checks: {observation.failed_status_check_names or ['<none>']}\n"
            f"Run conclusion: {observation.latest_pull_request_run_conclusion}\n"
            f"Run-log contrast markers: {observation.run_log_matched_contrast_markers}\n"
            f"Run-log semantic markers: {observation.run_log_matched_semantic_markers}\n"
            f"Runtime sample labels: {observation.runtime_accessibility_sample_labels or ['<none>']}\n"
            f"Runtime surface summary: {observation.runtime_accessibility_surface_summary or '<none>'}"
        )
        _record_step(result, step=4, status="passed", action=REQUEST_STEPS[3], observed=observed)
        return

    message = (
        "Step 4 failed: the disposable PR reached the real workflow/check surface, but "
        "GitHub did not expose a failing accessibility result that reported both the "
        "contrast and semantic defects from the ticket.\n"
        f"Pull Request URL: {observation.pull_request_url}\n"
        f"PR checks URL: {observation.pull_request_checks_url}\n"
        f"Run URL: {observation.latest_pull_request_run_url}\n"
        f"Run conclusion: {observation.latest_pull_request_run_conclusion}\n"
        f"Accessibility check: {observation.accessibility_status_check_name or '<none>'}\n"
        f"Accessibility workflow: {observation.accessibility_status_check_workflow_name or '<none>'}\n"
        f"Accessibility check conclusion: {observation.accessibility_status_check_conclusion or '<none>'}\n"
        f"Observed status checks: {observation.observed_status_check_names}\n"
        f"Failed status checks: {observation.failed_status_check_names}\n"
        f"Observed workflow names: {observation.observed_status_check_workflow_names}\n"
        f"Observed jobs: {observation.observed_job_names}\n"
        f"Observed steps: {observation.observed_step_names}\n"
        f"Matched accessibility markers: {observation.matched_accessibility_markers}\n"
        f"Matched contrast markers: {observation.matched_contrast_markers}\n"
        f"Matched semantic markers: {observation.matched_semantic_markers}\n"
        f"Run-log accessibility markers: {observation.run_log_matched_accessibility_markers}\n"
        f"Run-log contrast markers: {observation.run_log_matched_contrast_markers}\n"
        f"Run-log semantic markers: {observation.run_log_matched_semantic_markers}\n"
        f"Run log error: {observation.run_log_error or '<none>'}\n"
        f"Run log excerpt: {observation.run_log_excerpt or '<none>'}\n"
        f"Runtime sample labels: {observation.runtime_accessibility_sample_labels or ['<none>']}\n"
        f"Runtime surface summary: {observation.runtime_accessibility_surface_summary or '<none>'}"
    )
    failures.append(message)
    _record_step(result, step=4, status="failed", action=REQUEST_STEPS[3], observed=message)


def _has_explicit_contrast_evidence(markers: list[str]) -> bool:
    explicit_markers = (
        "color-contrast",
        "color contrast",
        "contrast ratio",
        "4.5:1",
        "minimum color contrast ratio thresholds",
    )
    return any(
        any(explicit_marker in marker.lower() for explicit_marker in explicit_markers)
        for marker in markers
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
    error = str(result.get("error", "AssertionError: TS-908 failed"))
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
        "* Patched the app entrypoint so the disposable PR renders a real Flutter probe surface with reduced text contrast and a weak semantics label.",
        "* Waited for the live pull-request workflow run to execute on that disposable PR.",
        "* Inspected the actual PR checks surface, workflow jobs/steps, and run logs for a failing result that reported both requested defect classes.",
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
        "- Patched the app entrypoint so the disposable PR renders a real Flutter probe surface with reduced text contrast and a weak semantics label.",
        "- Waited for the live pull-request workflow run to execute on that disposable PR.",
        "- Inspected the actual PR checks surface, workflow jobs/steps, and run logs for a failing result that reported both requested defect classes.",
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
        "- Reworked TS-908 to use a disposable PR plus the live GitHub Actions run/check surface.",
        "- The disposable PR now renders the defective probe through the app entrypoint instead of adding dead code.",
        f"- Test case: **{TICKET_KEY} - {TEST_CASE_TITLE}**",
        f"- Result: **{status}**",
        f"- Command: `{RUN_COMMAND}`",
        (
            f"- Environment: `{result['repository']}` @ `{result['default_branch']}` "
            f"using GitHub CLI on `{result['os']}`."
        ),
        (
            "- Outcome: the live PR pipeline reported the accessibility gate failure for both requested defect classes."
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
    return "\n".join(
        [
            f"# {TICKET_KEY} - Live PR CI does not expose an accessibility gate result for contrast and semantic defects",
            "",
            "## Steps to reproduce",
            "1. Create a Pull Request that introduces a UI element with a text-to-background contrast ratio below 4.5:1.",
            "2. In the same PR, include a component with a non-descriptive ARIA label.",
            "3. Push the changes to trigger the CI pipeline.",
            "4. Inspect the results of the automated accessibility check stage.",
            "",
            "## Exact test reproduction",
            (
                "1. The automation created a disposable PR, added "
                f"`{result.get('pull_request_probe_path', '')}`, and patched "
                f"`{result.get('probe_render_host_path', '')}` so the defective probe is "
                "rendered on app startup."
            ),
            (
                "2. GitHub Actions executed the contributor-visible PR workflow run "
                f"`{result.get('latest_pull_request_run_url', '')}` for that disposable PR."
            ),
            (
                "3. The PR checks surface "
                f"`{result.get('pull_request_checks_url', '')}` exposed status checks "
                f"{result.get('observed_status_check_names', [])} and workflow names "
                f"{result.get('observed_status_check_workflow_names', [])}."
            ),
            (
                "4. No failing accessibility-specific result reported both defect classes. "
                f"Observed accessibility check: `{result.get('accessibility_status_check_name', '<none>')}`; "
                f"run-log contrast markers: {result.get('run_log_matched_contrast_markers', [])}; "
                f"run-log semantic markers: {result.get('run_log_matched_semantic_markers', [])}."
            ),
            "",
            "## Expected result",
            f"- {EXPECTED_RESULT}",
            "",
            "## Actual result",
            (
                "- The live PR workflow ran, but GitHub did not expose a failing accessibility "
                "stage/check result that reported both the contrast ratio violation and the "
                "semantic label defect. The PR checks surface only showed the existing PR "
                "workflow/checks rather than a contributor-visible accessibility failure."
            ),
            "",
            "## Missing production capability",
            (
                "- The production CI pipeline does not provide a contributor-visible PR "
                "accessibility gate result for this scenario. From testing/ alone, the "
                "automation can create the defective PR and inspect real runs/checks, but it "
                "cannot make the product expose the missing accessibility stage, check-run, "
                "or defect diagnostics."
            ),
            "",
            "## Environment",
            f"- Repository: `{result.get('repository', '')}`",
            f"- Branch: `{result.get('default_branch', '')}`",
            f"- Pull Request: `{result.get('pull_request_url', '')}`",
            f"- Pull Request checks: `{result.get('pull_request_checks_url', '')}`",
            f"- Workflow run: `{result.get('latest_pull_request_run_url', '')}`",
            f"- OS: `{result.get('os', '')}`",
            "",
            "## Failing command",
            "```bash",
            RUN_COMMAND,
            "```",
            "",
            "## Failing output",
            "```text",
            str(result.get("traceback", result.get("error", "<missing traceback>"))),
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


def _jira_inline(value: str) -> str:
    return (
        value.replace("{", "\\{")
        .replace("}", "\\}")
        .replace("[", "\\[")
        .replace("]", "\\]")
    )


if __name__ == "__main__":
    main()
