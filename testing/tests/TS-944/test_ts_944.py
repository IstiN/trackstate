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
from testing.tests.support.github_accessibility_early_engine_crash_probe_factory import (  # noqa: E402
    create_github_accessibility_early_engine_crash_probe,
)

TICKET_KEY = "TS-944"
TEST_CASE_TITLE = (
    "Early Flutter engine crash - logs capture partial startup milestones"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-944/test_ts_944.py"
TEST_FILE_PATH = "testing/tests/TS-944/test_ts_944.py"
CONFIG_PATH = REPO_ROOT / "testing/tests/TS-944/config.yaml"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"

REQUEST_STEPS = [
    "Trigger a CI run for accessibility checks in the crash-simulated environment.",
    "Open the run logs for the 'Accessibility checks' stage.",
    "Search for the initial 'Flutter engine initialization' transition tokens.",
]
EXPECTED_RESULT = (
    "The logs show the initial startup tokens, helping to distinguish this "
    "low-level engine crash from a high-level semantics discovery timeout."
)
EXPECTED_FAILURE_CONCLUSION = "failure"
REQUIRED_INITIAL_ENGINE_STATES = ["bootstrap requested", "page loaded"]
CRASH_MARKER = "TS-944 simulated Flutter engine crash after bootstrap"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    config = GitHubAccessibilityPullRequestGateConfig.from_file(CONFIG_PATH)
    probe = create_github_accessibility_early_engine_crash_probe(
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
        _evaluate_crash_simulation_run(result, observation, failures)
        _evaluate_accessibility_log_surface(result, observation, failures)
        _evaluate_startup_tokens(result, observation, failures)
        _record_live_user_verification(result, observation)

        if failures:
            raise AssertionError("\n".join(failures))
    except Exception as error:
        result.setdefault("error", f"{type(error).__name__}: {error}")
        result.setdefault("traceback", traceback.format_exc())
        _write_failure_outputs(result)
        raise

    _write_pass_outputs(result)
    print("TS-944 passed")


def _evaluate_crash_simulation_run(
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
    unexpected_files = [
        path
        for path in observation.pull_request_file_paths
        if not path.startswith("testing/accessibility/")
    ]
    if missing_files:
        step_failures.append(
            f"GitHub did not record the expected crash-simulation files: {missing_files}."
        )
    if unexpected_files:
        step_failures.append(
            "the disposable PR changed files outside `testing/accessibility/`, so the "
            f"crash simulation was not isolated to the accessibility harness: {unexpected_files}."
        )
    if observation.latest_pull_request_run_id is None:
        step_failures.append(
            "GitHub Actions did not expose a contributor-visible pull-request workflow run "
            "for the crash-simulated branch."
        )
    if observation.latest_pull_request_run_event != "pull_request":
        step_failures.append(
            f"the observed workflow event was `{observation.latest_pull_request_run_event or '<none>'}` "
            "instead of `pull_request`."
        )
    if observation.latest_pull_request_run_status != "completed":
        step_failures.append(
            "the workflow run never completed; observed status was "
            f"`{observation.latest_pull_request_run_status or '<none>'}`."
        )
    if observation.latest_pull_request_run_conclusion != EXPECTED_FAILURE_CONCLUSION:
        step_failures.append(
            "the workflow run did not fail after the simulated early engine crash; observed "
            f"conclusion was `{observation.latest_pull_request_run_conclusion or '<none>'}`."
        )
    if observation.accessibility_status_check_conclusion != EXPECTED_FAILURE_CONCLUSION:
        step_failures.append(
            "the contributor-visible accessibility status check did not end in failure; "
            f"observed conclusion was `{observation.accessibility_status_check_conclusion or '<none>'}`."
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
            + "Accessibility check conclusion: "
            + f"{observation.accessibility_status_check_conclusion or '<none>'}\n"
            + f"Simulation technique: {observation.probe_contrast_technique}"
        )
        failures.append(message)
        _record_step(result, step=1, status="failed", action=REQUEST_STEPS[0], observed=message)
        return

    observed = (
        "Created a disposable PR that simulates an early Flutter web engine crash only "
        "through the accessibility harness files and observed the real pull-request "
        "workflow fail as expected.\n"
        f"Pull Request URL: {observation.pull_request_url}\n"
        f"Observed PR files: {observation.pull_request_file_paths}\n"
        f"Run URL: {observation.latest_pull_request_run_url}\n"
        f"Run status/conclusion: {observation.latest_pull_request_run_status}/{observation.latest_pull_request_run_conclusion}\n"
        "Accessibility check conclusion: "
        f"{observation.accessibility_status_check_conclusion or '<none>'}\n"
        f"Simulation technique: {observation.probe_contrast_technique}"
    )
    _record_step(result, step=1, status="passed", action=REQUEST_STEPS[0], observed=observed)


def _evaluate_accessibility_log_surface(
    result: dict[str, object],
    observation: GitHubAccessibilityPullRequestGateObservation,
    failures: list[str],
) -> None:
    step_failures: list[str] = []
    if observation.run_log_error is not None:
        step_failures.append(
            "GitHub CLI could not read the hosted workflow log: "
            f"{observation.run_log_error}."
        )
    if "Accessibility checks" not in observation.observed_job_names and (
        "Run axe-core accessibility checks" not in observation.observed_step_names
    ):
        step_failures.append(
            "the contributor-visible workflow surface did not expose the expected "
            "`Accessibility checks` stage before log inspection."
        )
    if "Run axe-core accessibility checks" not in observation.observed_step_names:
        step_failures.append(
            "the live workflow never reached the `Run axe-core accessibility checks` step."
        )

    if step_failures:
        message = (
            "Step 2 failed: "
            + " ".join(step_failures)
            + "\n"
            + f"Run URL: {observation.latest_pull_request_run_url or '<none>'}\n"
            + f"Observed jobs: {observation.observed_job_names or ['<none>']}\n"
            + f"Observed steps: {observation.observed_step_names or ['<none>']}\n"
            + f"Run log excerpt:\n{observation.run_log_excerpt or '<none>'}"
        )
        failures.append(message)
        _record_step(result, step=2, status="failed", action=REQUEST_STEPS[1], observed=message)
        return

    observed = (
        "Opened the hosted accessibility-stage log for the live crash-simulated PR run.\n"
        f"Run URL: {observation.latest_pull_request_run_url}\n"
        f"Observed jobs: {observation.observed_job_names}\n"
        f"Observed steps: {observation.observed_step_names}\n"
        f"Run log excerpt:\n{observation.run_log_excerpt or '<none>'}"
    )
    _record_step(result, step=2, status="passed", action=REQUEST_STEPS[1], observed=observed)


def _evaluate_startup_tokens(
    result: dict[str, object],
    observation: GitHubAccessibilityPullRequestGateObservation,
    failures: list[str],
) -> None:
    engine_entries = observation.flutter_engine_initialization_log_entries
    semantics_entries = observation.semantics_tree_discovery_log_entries
    distinct_engine_states = _normalized_flutter_engine_states(engine_entries)
    lower_states = {state.lower() for state in distinct_engine_states}
    missing_states = [
        state for state in REQUIRED_INITIAL_ENGINE_STATES if state not in lower_states
    ]
    surface_ready_visible = observation.runtime_accessibility_surface_present or any(
        "accessibility runtime surface ready" in entry.lower()
        for entry in semantics_entries
    )
    crash_marker_visible = _one_line(CRASH_MARKER).lower() in _one_line(
        observation.run_log_excerpt
    ).lower()

    step_failures: list[str] = []
    if not engine_entries:
        step_failures.append(
            "No hosted log entries containing `Flutter engine initialization` were captured."
        )
    if missing_states:
        step_failures.append(
            "The hosted log did not preserve the full set of expected initial startup "
            f"tokens; missing states: {missing_states}."
        )
    if surface_ready_visible:
        step_failures.append(
            "The crash-simulated run still reached `Accessibility runtime surface ready`, "
            "so it did not stop before the surface-ready state."
        )
    if not crash_marker_visible:
        step_failures.append(
            "The hosted log did not show the crash-simulation marker, so the observed "
            "failure could not be tied back to the intended early-engine-crash path."
        )

    if step_failures:
        message = (
            "Step 3 failed: "
            + " ".join(step_failures)
            + "\n"
            + f"Run URL: {observation.latest_pull_request_run_url or '<none>'}\n"
            + f"Flutter engine log entries: {engine_entries or ['<none>']}\n"
            + f"Distinct Flutter engine states: {distinct_engine_states or ['<none>']}\n"
            + f"Semantics discovery log entries: {semantics_entries or ['<none>']}\n"
            + f"Runtime accessibility surface summary: {observation.runtime_accessibility_surface_summary or '<none>'}\n"
            + f"Run log excerpt:\n{observation.run_log_excerpt or '<none>'}"
        )
        failures.append(message)
        _record_step(result, step=3, status="failed", action=REQUEST_STEPS[2], observed=message)
        return

    observed = (
        "Found the requested early startup milestones in the hosted accessibility log "
        "before the crash prevented the runtime from reaching surface ready.\n"
        f"Flutter engine initialization entries: {engine_entries}\n"
        f"Distinct Flutter engine states: {distinct_engine_states}\n"
        f"Semantics discovery entries: {semantics_entries or ['<none>']}\n"
        f"Crash marker: {CRASH_MARKER}\n"
        f"Runtime accessibility surface summary: {observation.runtime_accessibility_surface_summary or '<none>'}"
    )
    _record_step(result, step=3, status="passed", action=REQUEST_STEPS[2], observed=observed)


def _record_live_user_verification(
    result: dict[str, object],
    observation: GitHubAccessibilityPullRequestGateObservation,
) -> None:
    _record_human_verification(
        result,
        check=(
            "Reviewed the same contributor-visible PR checks surface and hosted GitHub "
            "Actions log a human reviewer would use to understand the early engine crash."
        ),
        observed=(
            f"PR checks URL: `{observation.pull_request_checks_url}`; run URL: "
            f"`{observation.latest_pull_request_run_url or '<none>'}`; accessibility "
            f"check conclusion: `{observation.accessibility_status_check_conclusion or '<none>'}`; "
            f"visible engine startup tokens: `{observation.flutter_engine_initialization_summary or '<none>'}`; "
            f"visible semantics summary: `{observation.semantics_tree_discovery_summary or '<none>'}`; "
            f"surface-ready summary: `{observation.runtime_accessibility_surface_summary or '<none>'}`."
        ),
    )


def _normalized_flutter_engine_states(entries: list[str]) -> list[str]:
    seen: set[str] = set()
    states: list[str] = []
    for entry in entries:
        state = _normalized_flutter_engine_state(entry)
        if not state or state in seen:
            continue
        seen.add(state)
        states.append(state)
    return states


def _normalized_flutter_engine_state(entry: str) -> str:
    marker = "flutter engine initialization:"
    normalized_entry = " ".join(entry.split()).strip()
    lowered_entry = normalized_entry.lower()
    marker_index = lowered_entry.find(marker)
    if marker_index >= 0:
        normalized_entry = normalized_entry[marker_index + len(marker) :]
    return normalized_entry.strip(" -:.;").lower()


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
    error = str(result.get("error", "AssertionError: TS-944 failed"))
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
        "h4. What was tested",
        "* Created a disposable pull request against the live repository.",
        "* Simulated an early Flutter web engine crash only through {{testing/accessibility/}} changes in that disposable PR.",
        "* Waited for the live {{Accessibility checks}} job, opened the hosted log, and checked for the initial Flutter engine startup tokens before surface-ready state.",
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
        "",
        "h4. Test file",
        "{code}",
        TEST_FILE_PATH,
        "{code}",
        "",
        "h4. Run command",
        "{code:bash}",
        RUN_COMMAND,
        "{code}",
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
        "- Simulated an early Flutter web engine crash only through `testing/accessibility/` changes in that disposable PR.",
        "- Waited for the live `Accessibility checks` job, opened the hosted log, and checked for the initial Flutter engine startup tokens before surface-ready state.",
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
        "## Test file",
        f"`{TEST_FILE_PATH}`",
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
        "- Added TS-944 as a disposable PR probe against the live GitHub Actions accessibility gate.",
        "- The probe simulates an early Flutter web engine crash strictly through `testing/accessibility/` changes in the disposable PR.",
        f"- Test case: **{TICKET_KEY} - {TEST_CASE_TITLE}**",
        f"- Result: **{status}**",
        f"- Command: `{RUN_COMMAND}`",
        (
            f"- Environment: `{result['repository']}` @ `{result['default_branch']}` "
            f"using GitHub CLI on `{result['os']}`."
        ),
        (
            "- Outcome: the live accessibility log preserved the early Flutter engine "
            "startup tokens before the crash prevented surface-ready state."
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
    lines = [
        f"# {TICKET_KEY} - {TEST_CASE_TITLE}",
        "",
        "h4. Environment",
        f"- URL: `{result.get('latest_pull_request_run_url', '<none>')}`",
        "- Browser/client: `GitHub CLI / GitHub Actions hosted log surface`",
        f"- OS: `{result.get('os', '<unknown>')}`",
        f"- Repository: `{result.get('repository', '<unknown>')}`",
        f"- Branch: `{result.get('default_branch', '<unknown>')}`",
        f"- Pull Request URL: `{result.get('pull_request_url', '<none>')}`",
        f"- PR checks URL: `{result.get('pull_request_checks_url', '<none>')}`",
        "",
        "h4. Steps to Reproduce",
        *_bug_step_lines(result),
        "",
        "h4. Expected Result",
        EXPECTED_RESULT,
        "",
        "h4. Actual Result",
        _failed_step_summary(result),
        "",
        "h4. Logs / Error Output",
        "```text",
        str(result.get("traceback", result.get("error", ""))),
        "```",
        "",
        "h4. Notes",
        "- Hosted Flutter engine entries:",
        "```text",
        str(result.get("flutter_engine_initialization_log_entries", ["<none>"])),
        "```",
        "- Hosted semantics entries:",
        "```text",
        str(result.get("semantics_tree_discovery_log_entries", ["<none>"])),
        "```",
        "- Hosted log excerpt:",
        "```text",
        str(result.get("run_log_excerpt", "<none>")),
        "```",
    ]
    return "\n".join(lines) + "\n"


def _bug_step_lines(result: dict[str, object]) -> list[str]:
    recorded_steps = {int(step["step"]): step for step in result.get("steps", [])}
    lines: list[str] = []
    for index, action in enumerate(REQUEST_STEPS, start=1):
        step = recorded_steps.get(index)
        status = "✅" if step is not None and step.get("status") == "passed" else "❌"
        observed = "<no observation recorded>" if step is None else str(step.get("observed", ""))
        lines.append(f"{index}. {status} {action}")
        lines.append(f"   - Observed: {observed}")
    return lines


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
        action = _jira_text(step["action"]) if jira else step["action"]
        observed = _jira_text(step["observed"]) if jira else step["observed"]
        lines.append(
            f"{prefix} {marker} Step {step['step']}: {action}  "
            f"Observed: {observed}"
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
        f"{prefix} {(_jira_text(entry['check']) if jira else entry['check'])} "
        f"Observed: {(_jira_text(entry['observed']) if jira else entry['observed'])}"
        for entry in entries
    ]


def _record_step(
    result: dict[str, object],
    *,
    step: int,
    status: str,
    action: str,
    observed: str,
) -> None:
    result.setdefault("steps", []).append(
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
    result.setdefault("human_verification", []).append(
        {
            "check": check,
            "observed": observed,
        }
    )


def _one_line(text: object) -> str:
    return " ".join(str(text).split())


def _jira_text(text: object) -> str:
    return re.sub(r"`([^`]+)`", r"{{\1}}", str(text))


if __name__ == "__main__":
    main()
