from __future__ import annotations

import json
import platform
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

TICKET_KEY = "TS-934"
TEST_CASE_TITLE = (
    "CI accessibility audit execution - Flutter engine initialization states are logged"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-934/test_ts_934.py"
TEST_FILE_PATH = "testing/tests/TS-934/test_ts_934.py"
CONFIG_PATH = REPO_ROOT / "testing/tests/TS-934/config.yaml"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"

REQUEST_STEPS = [
    "Trigger a standard CI run for accessibility checks.",
    "Open the run logs for the 'Accessibility checks' stage.",
    "Search for entries related to 'Flutter engine initialization'.",
]
EXPECTED_RESULT = (
    "The logs contain automated entries documenting the transition states of the "
    "Flutter engine during startup and the status of the semantics tree discovery."
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
        _evaluate_standard_ci_run(result, observation, failures)
        _evaluate_accessibility_logs_open(result, observation, failures)
        _evaluate_flutter_engine_logging(result, observation, failures)

        if failures:
            raise AssertionError("\n".join(failures))
    except Exception as error:
        result.setdefault("error", f"{type(error).__name__}: {error}")
        result.setdefault("traceback", traceback.format_exc())
        _write_failure_outputs(result)
        raise

    _write_pass_outputs(result)
    print("TS-934 passed")


def _evaluate_standard_ci_run(
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
            f"Observed workflow event was `{observation.latest_pull_request_run_event or '<none>'}` instead of `pull_request`."
        )
    if observation.accessibility_status_check_conclusion not in SUCCESS_CONCLUSIONS:
        step_failures.append(
            "The hosted accessibility check did not complete successfully for the disposable compliant probe."
        )

    if step_failures:
        message = (
            "Step 1 failed: "
            + " ".join(step_failures)
            + "\n"
            + f"Pull Request URL: {observation.pull_request_url}\n"
            + f"Run URL: {observation.latest_pull_request_run_url}\n"
            + f"Run status/conclusion: {observation.latest_pull_request_run_status}/{observation.latest_pull_request_run_conclusion}\n"
            + "Accessibility check conclusion: "
            + f"{observation.accessibility_status_check_conclusion or '<none>'}\n"
            + f"Observed status checks: {observation.observed_status_check_names or ['<none>']}"
        )
        failures.append(message)
        _record_step(result, step=1, status="failed", action=REQUEST_STEPS[0], observed=message)
        return

    observed = (
        "Triggered a real disposable PR workflow and confirmed the standard accessibility run "
        "completed on GitHub Actions.\n"
        f"Pull Request URL: {observation.pull_request_url}\n"
        f"Run URL: {observation.latest_pull_request_run_url}\n"
        f"Run status/conclusion: {observation.latest_pull_request_run_status}/{observation.latest_pull_request_run_conclusion}\n"
        "Accessibility check conclusion: "
        f"{observation.accessibility_status_check_conclusion or '<none>'}"
    )
    _record_step(result, step=1, status="passed", action=REQUEST_STEPS[0], observed=observed)


def _evaluate_accessibility_logs_open(
    result: dict[str, object],
    observation: GitHubAccessibilityPullRequestGateObservation,
    failures: list[str],
) -> None:
    _record_human_verification(
        result,
        check=(
            "Reviewed the live workflow output the way a human reviewer would, using "
            "`gh pr view` for the checks surface and `gh run view --log` for the hosted log."
        ),
        observed=(
            f"PR checks URL: `{observation.pull_request_checks_url}`; run URL: "
            f"`{observation.latest_pull_request_run_url}`; observed jobs: "
            f"{observation.observed_job_names or ['<none>']}; observed steps: "
            f"{observation.observed_step_names or ['<none>']}; accessibility check conclusion: "
            f"`{observation.accessibility_status_check_conclusion or '<none>'}`; engine log summary: "
            f"`{observation.flutter_engine_initialization_summary or '<none>'}`; semantics summary: "
            f"`{observation.semantics_tree_discovery_summary or '<none>'}`."
        ),
    )

    if observation.run_log_error:
        message = (
            "Step 2 failed: the automation could not open the hosted workflow log for the "
            "real accessibility run.\n"
            f"Run URL: {observation.latest_pull_request_run_url}\n"
            f"Log error: {observation.run_log_error}"
        )
        failures.append(message)
        _record_step(result, step=2, status="failed", action=REQUEST_STEPS[1], observed=message)
        return

    if "Accessibility checks" not in observation.observed_job_names and (
        "Run axe-core accessibility checks" not in observation.observed_step_names
    ):
        message = (
            "Step 2 failed: the contributor-visible workflow surface did not expose the "
            "expected accessibility-check stage before log inspection.\n"
            f"Run URL: {observation.latest_pull_request_run_url}\n"
            f"Observed jobs: {observation.observed_job_names or ['<none>']}\n"
            f"Observed steps: {observation.observed_step_names or ['<none>']}"
        )
        failures.append(message)
        _record_step(result, step=2, status="failed", action=REQUEST_STEPS[1], observed=message)
        return

    observed = (
        "Opened the hosted accessibility-stage log for the live disposable PR run.\n"
        f"Run URL: {observation.latest_pull_request_run_url}\n"
        f"Observed jobs: {observation.observed_job_names or ['<none>']}\n"
        f"Observed steps: {observation.observed_step_names or ['<none>']}\n"
        f"Run log excerpt: {observation.run_log_excerpt or '<none>'}"
    )
    _record_step(result, step=2, status="passed", action=REQUEST_STEPS[1], observed=observed)


def _evaluate_flutter_engine_logging(
    result: dict[str, object],
    observation: GitHubAccessibilityPullRequestGateObservation,
    failures: list[str],
) -> None:
    engine_entries = observation.flutter_engine_initialization_log_entries
    semantics_entries = observation.semantics_tree_discovery_log_entries
    distinct_engine_states = _normalized_flutter_engine_states(engine_entries)
    engine_transitions_logged = len(distinct_engine_states) >= 2 or any(
        "->" in state or "transition" in state for state in distinct_engine_states
    )

    step_failures: list[str] = []
    if not engine_entries:
        step_failures.append(
            "No run-log entries containing `Flutter engine initialization` were captured."
        )
    elif not engine_transitions_logged:
        step_failures.append(
            "Only one distinct Flutter engine initialization state was logged, so the transition sequence was not documented."
        )
    if not semantics_entries:
        step_failures.append(
            "No log entry documented semantics-tree discovery status."
        )

    if step_failures:
        message = (
            "Step 3 failed: "
            + " ".join(step_failures)
            + "\n"
            + f"Run URL: {observation.latest_pull_request_run_url}\n"
            + f"Flutter engine log entries: {engine_entries or ['<none>']}\n"
            + f"Distinct Flutter engine states: {distinct_engine_states or ['<none>']}\n"
            + f"Semantics discovery log entries: {semantics_entries or ['<none>']}\n"
            + f"Run log excerpt: {observation.run_log_excerpt or '<none>'}"
        )
        failures.append(message)
        _record_step(result, step=3, status="failed", action=REQUEST_STEPS[2], observed=message)
        return

    observed = (
        "Found the requested startup diagnostics in the hosted accessibility log.\n"
        f"Flutter engine initialization entries: {engine_entries}\n"
        f"Distinct Flutter engine states: {distinct_engine_states}\n"
        f"Semantics discovery entries: {semantics_entries}"
    )
    _record_step(result, step=3, status="passed", action=REQUEST_STEPS[2], observed=observed)


def _normalized_flutter_engine_states(entries: list[str]) -> list[str]:
    seen: set[str] = set()
    distinct_states: list[str] = []
    for entry in entries:
        state = _normalized_flutter_engine_state(entry)
        if not state or state in seen:
            continue
        seen.add(state)
        distinct_states.append(state)
    return distinct_states


def _normalized_flutter_engine_state(entry: str) -> str:
    marker = "flutter engine initialization:"
    normalized_entry = " ".join(entry.split()).strip()
    lowered_entry = normalized_entry.lower()
    marker_index = lowered_entry.find(marker)
    if marker_index >= 0:
        normalized_entry = normalized_entry[marker_index + len(marker) :]
    normalized_state = normalized_entry.strip(" -:.;")
    return normalized_state.lower()


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
    error = str(result.get("error", "AssertionError: TS-934 failed"))
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
        "* Created a disposable compliant pull request against the live repository to trigger the real PR accessibility workflow.",
        "* Reused the shared accessibility gate probe and extended it to capture Flutter engine initialization lines plus semantics-tree discovery status from the hosted run log.",
        "* Verified the contributor-visible workflow surface and the hosted accessibility log instead of inferring behavior from source only.",
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
        "- Created a disposable compliant pull request against the live repository to trigger the real PR accessibility workflow.",
        "- Reused the shared accessibility gate probe and extended it to capture Flutter engine initialization lines plus semantics-tree discovery status from the hosted run log.",
        "- Verified the contributor-visible workflow surface and the hosted accessibility log instead of inferring behavior from source only.",
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
        "- Added TS-934 as a live disposable-PR accessibility-log probe against GitHub Actions.",
        "- Extended the shared accessibility probe to capture Flutter engine initialization lines and semantics-tree discovery evidence from hosted run logs.",
        f"- Test case: **{TICKET_KEY} - {TEST_CASE_TITLE}**",
        f"- Result: **{status}**",
        f"- Command: `{RUN_COMMAND}`",
        (
            f"- Environment: `{result['repository']}` @ `{result['default_branch']}` "
            f"using GitHub CLI on `{result['os']}`."
        ),
        (
            "- Outcome: the live accessibility run logged Flutter engine initialization transitions and semantics-tree discovery status."
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
        f"# {TICKET_KEY} - Accessibility run logs do not document Flutter engine initialization transitions and semantics discovery status\n\n"
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
        "- **Actual:** The live hosted accessibility log did not expose enough Flutter-engine "
        "startup transition entries and/or did not expose a semantics-tree discovery status line.\n\n"
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


if __name__ == "__main__":
    main()
