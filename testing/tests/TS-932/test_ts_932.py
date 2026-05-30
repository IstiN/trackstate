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

from testing.components.services.github_accessibility_stage_log_inspector import (  # noqa: E402
    GitHubAccessibilityStageLogInspector,
    GitHubWorkflowStageLogEntry,
)
from testing.core.config.github_accessibility_pull_request_gate_config import (  # noqa: E402
    GitHubAccessibilityPullRequestGateConfig,
)
from testing.core.interfaces.github_accessibility_pull_request_gate_probe import (  # noqa: E402
    GitHubAccessibilityPullRequestGateObservation,
)
from testing.tests.support.github_accessibility_placeholder_verification_probe_factory import (  # noqa: E402
    create_github_accessibility_stage_log_inspector,
    create_github_accessibility_placeholder_verification_probe,
)

TICKET_KEY = "TS-932"
TEST_CASE_TITLE = (
    "Accessibility gate initialization - flt-semantics-placeholder is verified before scanning"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-932/test_ts_932.py"
TEST_FILE_PATH = "testing/tests/TS-932/test_ts_932.py"
CONFIG_PATH = REPO_ROOT / "testing/tests/TS-932/config.yaml"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"

REQUEST_STEPS = [
    "Trigger the CI pipeline by pushing a change to a Pull Request.",
    "Monitor the 'Accessibility checks' job execution.",
    "Verify the log sequence before the axe-core scan begins.",
]
EXPECTED_RESULT = (
    "The script successfully detects the 'flt-semantics-placeholder', logs the "
    "verification, and only then proceeds to the full WCAG validation scan."
)
SUCCESS_CONCLUSIONS = {"success"}


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    config = GitHubAccessibilityPullRequestGateConfig.from_file(CONFIG_PATH)
    probe = create_github_accessibility_placeholder_verification_probe(
        REPO_ROOT,
        config_path=CONFIG_PATH,
    )
    log_inspector = create_github_accessibility_stage_log_inspector(REPO_ROOT)
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
        "accessibility_stage_log_entries": [],
        "accessibility_stage_log_excerpt": "",
        "placeholder_verification_log_entries": [],
        "runtime_accessibility_log_entries": [],
        "scan_progress_log_entries": [],
    }

    try:
        observation = probe.validate()
        result.update(observation.to_dict())

        stage_entries, stage_log_error = _read_accessibility_stage_entries(
            observation,
            log_inspector=log_inspector,
        )
        stage_log_lines = [entry.raw_line for entry in stage_entries]
        placeholder_entries = log_inspector.extract_placeholder_verification_entries(
            stage_entries
        )
        runtime_entries = log_inspector.extract_runtime_surface_entries(stage_entries)
        scan_entries = log_inspector.extract_scan_progress_entries(stage_entries)

        result["accessibility_stage_log_entries"] = stage_log_lines
        result["accessibility_stage_log_excerpt"] = log_inspector.build_excerpt(stage_entries)
        result["placeholder_verification_log_entries"] = placeholder_entries
        result["runtime_accessibility_log_entries"] = runtime_entries
        result["scan_progress_log_entries"] = scan_entries
        result["stage_log_error"] = stage_log_error

        failures: list[str] = []
        _evaluate_ci_trigger(result, observation, failures)
        _evaluate_accessibility_job_surface(
            result,
            observation,
            failures,
            stage_log_error=stage_log_error,
            stage_log_lines=stage_log_lines,
        )
        _evaluate_placeholder_sequence(
            result,
            observation,
            failures,
            stage_log_lines=stage_log_lines,
            placeholder_entries=placeholder_entries,
            runtime_entries=runtime_entries,
            scan_entries=scan_entries,
        )
        _record_live_user_verification(
            result,
            observation,
            stage_log_lines=stage_log_lines,
            placeholder_entries=placeholder_entries,
            runtime_entries=runtime_entries,
        )

        if failures:
            raise AssertionError("\n".join(failures))
    except Exception as error:
        result.setdefault("error", f"{type(error).__name__}: {error}")
        result.setdefault("traceback", traceback.format_exc())
        _write_failure_outputs(result)
        raise

    _write_pass_outputs(result)
    print("TS-932 passed")


def _read_accessibility_stage_entries(
    observation: GitHubAccessibilityPullRequestGateObservation,
    *,
    log_inspector: GitHubAccessibilityStageLogInspector,
) -> tuple[list[GitHubWorkflowStageLogEntry], str | None]:
    if observation.latest_pull_request_run_id is None:
        return [], "The workflow run ID was missing, so the hosted log could not be read."
    try:
        return (
            log_inspector.read_accessibility_stage_entries(
                observation.latest_pull_request_run_id
            ),
            None,
        )
    except Exception as error:  # noqa: BLE001
        return [], f"{type(error).__name__}: {error}"


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
            f"the observed workflow event was `{observation.latest_pull_request_run_event or '<none>'}` instead of `pull_request`."
        )
    if observation.latest_pull_request_run_status != "completed":
        step_failures.append(
            "the workflow run never completed; observed status was "
            f"`{observation.latest_pull_request_run_status or '<none>'}`."
        )
    if observation.latest_pull_request_run_conclusion not in SUCCESS_CONCLUSIONS:
        step_failures.append(
            "the live PR workflow did not finish successfully for the compliant accessibility probe."
        )
    if observation.accessibility_status_check_conclusion not in SUCCESS_CONCLUSIONS:
        step_failures.append(
            "the contributor-visible `Accessibility checks` status did not conclude success."
        )

    if step_failures:
        message = (
            "Step 1 failed: "
            + " ".join(step_failures)
            + "\n"
            + f"Pull Request URL: {observation.pull_request_url}\n"
            + f"Run URL: {observation.latest_pull_request_run_url or '<none>'}\n"
            + "Run status/conclusion: "
            + f"{observation.latest_pull_request_run_status or '<none>'}/"
            + f"{observation.latest_pull_request_run_conclusion or '<none>'}\n"
            + "Accessibility check conclusion: "
            + f"{observation.accessibility_status_check_conclusion or '<none>'}\n"
            + f"Observed status checks: {observation.observed_status_check_names or ['<none>']}"
        )
        failures.append(message)
        _record_step(result, step=1, status="failed", action=REQUEST_STEPS[0], observed=message)
        return

    observed = (
        "Triggered a real disposable PR workflow and confirmed the hosted accessibility gate completed successfully.\n"
        f"Pull Request URL: {observation.pull_request_url}\n"
        f"Run URL: {observation.latest_pull_request_run_url}\n"
        + "Run status/conclusion: "
        + f"{observation.latest_pull_request_run_status}/{observation.latest_pull_request_run_conclusion}\n"
        + "Accessibility check conclusion: "
        + f"{observation.accessibility_status_check_conclusion or '<none>'}"
    )
    _record_step(result, step=1, status="passed", action=REQUEST_STEPS[0], observed=observed)


def _evaluate_accessibility_job_surface(
    result: dict[str, object],
    observation: GitHubAccessibilityPullRequestGateObservation,
    failures: list[str],
    *,
    stage_log_error: str | None,
    stage_log_lines: list[str],
) -> None:
    step_failures: list[str] = []
    if stage_log_error is not None:
        step_failures.append(
            f"the hosted accessibility-stage log could not be read: {stage_log_error}."
        )
    if "Accessibility checks" not in observation.observed_job_names and (
        "Run axe-core accessibility checks" not in observation.observed_step_names
    ):
        step_failures.append(
            "the contributor-visible workflow surface did not expose the expected accessibility stage before log inspection."
        )
    if not stage_log_lines:
        step_failures.append(
            "no log lines were isolated for the `Accessibility checks` / `Run axe-core accessibility checks` stage."
        )

    if step_failures:
        message = (
            "Step 2 failed: "
            + " ".join(step_failures)
            + "\n"
            + f"Run URL: {observation.latest_pull_request_run_url or '<none>'}\n"
            + f"Observed jobs: {observation.observed_job_names or ['<none>']}\n"
            + f"Observed steps: {observation.observed_step_names or ['<none>']}\n"
            + "Accessibility-stage excerpt:\n"
            + (result.get("accessibility_stage_log_excerpt") or "<none>")
        )
        failures.append(message)
        _record_step(result, step=2, status="failed", action=REQUEST_STEPS[1], observed=message)
        return

    observed = (
        "Opened the contributor-visible `Accessibility checks` stage log for the hosted PR workflow run.\n"
        f"Run URL: {observation.latest_pull_request_run_url}\n"
        f"Observed jobs: {observation.observed_job_names}\n"
        f"Observed steps: {observation.observed_step_names}\n"
        "Accessibility-stage excerpt:\n"
        + (result.get("accessibility_stage_log_excerpt") or "<none>")
    )
    _record_step(result, step=2, status="passed", action=REQUEST_STEPS[1], observed=observed)


def _evaluate_placeholder_sequence(
    result: dict[str, object],
    observation: GitHubAccessibilityPullRequestGateObservation,
    failures: list[str],
    *,
    stage_log_lines: list[str],
    placeholder_entries: list[str],
    runtime_entries: list[str],
    scan_entries: list[str],
) -> None:
    step_failures = _sequence_failures(
        stage_log_lines=stage_log_lines,
        placeholder_entries=placeholder_entries,
        runtime_entries=runtime_entries,
        scan_entries=scan_entries,
    )

    if step_failures:
        message = (
            "Step 3 failed: "
            + " ".join(step_failures)
            + "\n"
            + f"Run URL: {observation.latest_pull_request_run_url or '<none>'}\n"
            + "Placeholder verification entries: "
            + f"{placeholder_entries or ['<none>']}\n"
            + "Runtime accessibility entries: "
            + f"{runtime_entries or ['<none>']}\n"
            + "Scan progress entries: "
            + f"{scan_entries or ['<none>']}\n"
            + "Accessibility-stage excerpt:\n"
            + (result.get("accessibility_stage_log_excerpt") or "<none>")
        )
        failures.append(message)
        _record_step(result, step=3, status="failed", action=REQUEST_STEPS[2], observed=message)
        return

    observed = (
        "The hosted accessibility-stage log recorded placeholder verification before the runtime accessibility surface and scan completion evidence.\n"
        + "Placeholder verification entries: "
        + f"{placeholder_entries}\n"
        + "Runtime accessibility entries: "
        + f"{runtime_entries}\n"
        + "Scan progress entries: "
        + f"{scan_entries}"
    )
    _record_step(result, step=3, status="passed", action=REQUEST_STEPS[2], observed=observed)


def _sequence_failures(
    *,
    stage_log_lines: list[str],
    placeholder_entries: list[str],
    runtime_entries: list[str],
    scan_entries: list[str],
) -> list[str]:
    failures: list[str] = []
    if not placeholder_entries:
        failures.append(
            "the hosted accessibility log never recorded that `flt-semantics-placeholder` was verified before the scan."
        )
    if not runtime_entries:
        failures.append(
            "the hosted accessibility log never recorded that the runtime accessibility surface became ready."
        )
    if not scan_entries:
        failures.append(
            "the hosted accessibility log never recorded that the full WCAG scan proceeded after placeholder verification."
        )
    if placeholder_entries and runtime_entries:
        placeholder_index = _first_index(stage_log_lines, placeholder_entries[0])
        runtime_index = _first_index(stage_log_lines, runtime_entries[0])
        if placeholder_index >= runtime_index:
            failures.append(
                "the placeholder verification entry appeared after the runtime accessibility surface was already reported ready."
            )
    if placeholder_entries and scan_entries:
        placeholder_index = _first_index(stage_log_lines, placeholder_entries[0])
        scan_index = _first_index(stage_log_lines, scan_entries[0])
        if placeholder_index >= scan_index:
            failures.append(
                "the placeholder verification entry appeared after scan-progress evidence was already logged."
            )
    return failures


def _first_index(lines: list[str], target: str) -> int:
    try:
        return lines.index(target)
    except ValueError:
        return len(lines)


def _record_live_user_verification(
    result: dict[str, object],
    observation: GitHubAccessibilityPullRequestGateObservation,
    *,
    stage_log_lines: list[str],
    placeholder_entries: list[str],
    runtime_entries: list[str],
) -> None:
    _record_human_verification(
        result,
        check=(
            "Reviewed the same PR checks surface and `Accessibility checks` stage log that a human contributor would open in GitHub to confirm whether the smoke test verified the Flutter semantics placeholder before the scan."
        ),
        observed=(
            f"PR checks URL: `{observation.pull_request_checks_url}`; run URL: "
            f"`{observation.latest_pull_request_run_url or '<none>'}`; accessibility check "
            f"conclusion: `{observation.accessibility_status_check_conclusion or '<none>'}`; "
            f"placeholder entries: `{_one_line_list(placeholder_entries) or '<none>'}`; "
            f"runtime entries: `{_one_line_list(runtime_entries) or '<none>'}`; "
            f"visible stage lines: `{_one_line_list(stage_log_lines[:5]) or '<none>'}`."
        ),
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
    error = str(result.get("error", "AssertionError: TS-932 failed"))
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
        "* Created a disposable WCAG-compliant pull request against the live repository to trigger the real PR accessibility workflow.",
        "* Read the contributor-visible `Accessibility checks` / `Run axe-core accessibility checks` stage log from GitHub Actions.",
        "* Verified whether the log recorded `flt-semantics-placeholder` verification before runtime accessibility readiness and scan-completion evidence.",
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
        "- Created a disposable WCAG-compliant pull request against the live repository to trigger the real PR accessibility workflow.",
        "- Read the contributor-visible `Accessibility checks` / `Run axe-core accessibility checks` stage log from GitHub Actions.",
        "- Verified whether the log recorded `flt-semantics-placeholder` verification before runtime accessibility readiness and scan-completion evidence.",
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
        "- Added TS-932 as a live disposable-PR accessibility-log probe against GitHub Actions.",
        "- Reused the WCAG-compliant accessibility probe path and inspected only the hosted `Accessibility checks` stage log lines.",
        f"- Test case: **{TICKET_KEY} - {TEST_CASE_TITLE}**",
        f"- Result: **{status}**",
        f"- Command: `{RUN_COMMAND}`",
        (
            f"- Environment: `{result['repository']}` @ `{result['default_branch']}` "
            f"using GitHub CLI on `{result['os']}`."
        ),
        (
            "- Outcome: the live accessibility run logged placeholder verification before the scan proceeded."
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
        f"# {TICKET_KEY} - Accessibility stage does not log flt-semantics-placeholder verification before scan evidence\n\n"
        "## Steps to reproduce\n"
        f"1. {REQUEST_STEPS[0]}  \n"
        f"   - Actual: {step_map.get(1, {}).get('observed', '<missing>')}  \n"
        f"   - Result: {'PASSED ✅' if step_map.get(1, {}).get('status') == 'passed' else 'FAILED ❌'}\n"
        f"2. {REQUEST_STEPS[1]}  \n"
        f"   - Actual: {step_map.get(2, {}).get('observed', '<missing>')}  \n"
        f"   - Result: {'PASSED ✅' if step_map.get(2, {}).get('status') == 'passed' else 'FAILED ❌'}\n"
        f"3. {REQUEST_STEPS[2]}  \n"
        f"   - Actual: {step_map.get(3, {}).get('observed', '<missing>')}  \n"
        "   - Result: FAILED ❌\n\n"
        "## Exact error message or assertion failure\n"
        "```text\n"
        f"{result.get('traceback', result.get('error', '<missing>'))}"
        "```\n\n"
        "## Actual vs Expected\n"
        f"- **Expected:** {EXPECTED_RESULT}\n"
        "- **Actual:** the hosted `Accessibility checks` log completed successfully but did not "
        "record a contributor-visible verification line for `flt-semantics-placeholder` before "
        "the runtime accessibility surface and scan-completion evidence.\n\n"
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
        "- **Placeholder verification entries:**\n"
        "```text\n"
        f"{result.get('placeholder_verification_log_entries', ['<none>'])}\n"
        "```\n"
        "- **Runtime accessibility entries:**\n"
        "```text\n"
        f"{result.get('runtime_accessibility_log_entries', ['<none>'])}\n"
        "```\n"
        "- **Accessibility-stage excerpt:**\n"
        "```text\n"
        f"{result.get('accessibility_stage_log_excerpt', '<missing stage excerpt>')}\n"
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
        prefix = f"* Step {step} - {status}: " if jira else f"- Step {step} - {status}: "
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
        if str(entry.get("status", "")).lower() == "failed":
            return f"Step {entry.get('step')} failed: {entry.get('observed')}"
    return str(result.get("error", "Unknown failure"))


def _jira_inline(value: str) -> str:
    return (
        value.replace("{", "\\{")
        .replace("}", "\\}")
        .replace("[", "\\[")
        .replace("]", "\\]")
    )


def _one_line_list(lines: list[str]) -> str:
    if not lines:
        return ""
    return " | ".join(_one_line(line) for line in lines)


def _one_line(value: object) -> str:
    return re.sub(r"\s+", " ", str(value)).strip()


if __name__ == "__main__":
    main()
