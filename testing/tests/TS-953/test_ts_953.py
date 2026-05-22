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
from testing.tests.support.github_accessibility_network_timeout_probe_factory import (  # noqa: E402
    create_github_accessibility_network_timeout_probe,
)

TICKET_KEY = "TS-953"
TEST_CASE_TITLE = (
    "Network timeout during load - standard automation error logged without Flutter specifics"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-953/test_ts_953.py"
TEST_FILE_PATH = "testing/tests/TS-953/test_ts_953.py"
CONFIG_PATH = REPO_ROOT / "testing/tests/TS-953/config.yaml"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"

REQUEST_STEPS = [
    "Trigger the accessibility gate CI job.",
    "Simulate a network-level timeout during the initial page load phase.",
    "Inspect the resulting failure message in the GitHub Actions log.",
]
EXPECTED_RESULT = (
    "The log surfaces a standard network or Playwright automation timeout error "
    "and does not incorrectly report a 'Flutter semantics initialization failure' "
    "message."
)
EXPECTED_FAILURE_CONCLUSION = "failure"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    config = GitHubAccessibilityPullRequestGateConfig.from_file(CONFIG_PATH)
    probe = create_github_accessibility_network_timeout_probe(
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
        _evaluate_workflow_trigger(result, observation, failures)
        _evaluate_network_timeout_simulation(result, observation, failures)
        _evaluate_error_log(result, observation, failures)
        _record_live_user_verification(result, observation)

        if failures:
            raise AssertionError("\n".join(failures))
    except Exception as error:
        result.setdefault("error", f"{type(error).__name__}: {error}")
        result.setdefault("traceback", traceback.format_exc())
        _write_failure_outputs(result)
        raise

    _write_pass_outputs(result)
    print("TS-953 passed")


def _evaluate_workflow_trigger(
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
        step_failures.append(f"GitHub did not record the expected simulation files: {missing_files}.")
    if unexpected_files:
        step_failures.append(
            "the disposable PR changed files outside `testing/accessibility/`, so the "
            f"network timeout simulation was not isolated to the accessibility harness: {unexpected_files}."
        )
    if observation.latest_pull_request_run_id is None:
        step_failures.append(
            "GitHub Actions did not expose a contributor-visible pull-request workflow run "
            "for the network-timeout branch."
        )
    if observation.latest_pull_request_run_event != "pull_request":
        step_failures.append(
            f"the observed workflow event was `{observation.latest_pull_request_run_event or '<none>'}` "
            "instead of `pull_request`."
        )

    if step_failures:
        message = (
            "Step 1 failed: "
            + " ".join(step_failures)
            + "\n"
            + f"Pull Request URL: {observation.pull_request_url}\n"
            + f"Observed PR files: {observation.pull_request_file_paths}\n"
            + f"Run URL: {observation.latest_pull_request_run_url or '<none>'}\n"
            + f"Simulation technique: {observation.probe_contrast_technique}"
        )
        failures.append(message)
        _record_step(result, step=1, status="failed", action=REQUEST_STEPS[0], observed=message)
        return

    observed = (
        "Created a disposable PR that triggers the live pull-request accessibility job "
        "using only `testing/accessibility/` changes for the network-timeout probe.\n"
        f"Pull Request URL: {observation.pull_request_url}\n"
        f"Observed PR files: {observation.pull_request_file_paths}\n"
        f"Run URL: {observation.latest_pull_request_run_url}\n"
        f"Simulation technique: {observation.probe_contrast_technique}"
    )
    _record_step(result, step=1, status="passed", action=REQUEST_STEPS[0], observed=observed)


def _evaluate_network_timeout_simulation(
    result: dict[str, object],
    observation: GitHubAccessibilityPullRequestGateObservation,
    failures: list[str],
) -> None:
    step_failures: list[str] = []
    if observation.latest_pull_request_run_status != "completed":
        step_failures.append(
            "the workflow run never completed; observed status was "
            f"`{observation.latest_pull_request_run_status or '<none>'}`."
        )
    if observation.latest_pull_request_run_conclusion != EXPECTED_FAILURE_CONCLUSION:
        step_failures.append(
            "the workflow run did not fail after the simulated page-load timeout; observed "
            f"conclusion was `{observation.latest_pull_request_run_conclusion or '<none>'}`."
        )
    if "Run axe-core accessibility checks" not in observation.observed_step_names:
        step_failures.append(
            "the live workflow never reached the `Run axe-core accessibility checks` step."
        )
    if observation.accessibility_status_check_conclusion != EXPECTED_FAILURE_CONCLUSION:
        step_failures.append(
            "the contributor-visible accessibility status check did not end in failure; "
            f"observed conclusion was `{observation.accessibility_status_check_conclusion or '<none>'}`."
        )

    if step_failures:
        message = (
            "Step 2 failed: "
            + " ".join(step_failures)
            + "\n"
            + f"Run URL: {observation.latest_pull_request_run_url or '<none>'}\n"
            + f"Run status/conclusion: {observation.latest_pull_request_run_status or '<none>'}/"
            + f"{observation.latest_pull_request_run_conclusion or '<none>'}\n"
            + f"Accessibility check: {observation.accessibility_status_check_name or '<none>'}\n"
            + f"Accessibility check conclusion: {observation.accessibility_status_check_conclusion or '<none>'}\n"
            + f"Observed jobs: {observation.observed_job_names or ['<none>']}\n"
            + f"Observed steps: {observation.observed_step_names or ['<none>']}"
        )
        failures.append(message)
        _record_step(result, step=2, status="failed", action=REQUEST_STEPS[1], observed=message)
        return

    observed = (
        "Waited for the live pull-request workflow to complete after stalling the initial "
        "page navigation request.\n"
        f"Run URL: {observation.latest_pull_request_run_url}\n"
        f"Run status/conclusion: {observation.latest_pull_request_run_status}/{observation.latest_pull_request_run_conclusion}\n"
        f"Accessibility check: {observation.accessibility_status_check_name or '<derived from run surface>'}\n"
        f"Accessibility check conclusion: {observation.accessibility_status_check_conclusion or '<none>'}\n"
        f"Observed jobs: {observation.observed_job_names}\n"
        f"Observed steps: {observation.observed_step_names}"
    )
    _record_step(result, step=2, status="passed", action=REQUEST_STEPS[1], observed=observed)


def _evaluate_error_log(
    result: dict[str, object],
    observation: GitHubAccessibilityPullRequestGateObservation,
    failures: list[str],
) -> None:
    step_failures: list[str] = []
    log_excerpt = observation.run_log_excerpt or ""
    if observation.run_log_error is not None:
        step_failures.append(
            "GitHub CLI could not read the live workflow log: "
            f"{observation.run_log_error}."
        )

    generic_timeout_present = _has_generic_network_or_playwright_timeout(observation)
    semantics_failure_present = _has_descriptive_semantics_failure_message(observation)

    if not generic_timeout_present:
        step_failures.append(
            "the live workflow log did not surface a standard network or Playwright timeout "
            "during the initial page-load phase."
        )
    if semantics_failure_present:
        step_failures.append(
            "the live workflow log incorrectly reported a Flutter semantics initialization "
            "failure for a page-load timeout scenario."
        )

    if step_failures:
        message = (
            "Step 3 failed: "
            + " ".join(step_failures)
            + "\n"
            + f"Run URL: {observation.latest_pull_request_run_url or '<none>'}\n"
            + f"Runtime accessibility evidence: {observation.runtime_accessibility_surface_summary or '<none>'}\n"
            + f"Run-log timeout markers: {observation.run_log_matched_contrast_markers or ['<none>']}\n"
            + f"Run-log semantics markers: {observation.run_log_matched_semantic_markers or ['<none>']}\n"
            + f"Run log excerpt:\n{log_excerpt or '<none>'}"
        )
        failures.append(message)
        _record_step(result, step=3, status="failed", action=REQUEST_STEPS[2], observed=message)
        return

    observed = (
        "Inspected the live GitHub Actions log and found a generic page-load timeout "
        "signal without any Flutter semantics initialization failure wording.\n"
        f"Run URL: {observation.latest_pull_request_run_url}\n"
        f"Runtime accessibility evidence: {observation.runtime_accessibility_surface_summary or '<none>'}\n"
        f"Run-log timeout markers: {observation.run_log_matched_contrast_markers or ['<none>']}\n"
        f"Run-log semantics markers: {observation.run_log_matched_semantic_markers or ['<none>']}\n"
        f"Run log excerpt:\n{log_excerpt}"
    )
    _record_step(result, step=3, status="passed", action=REQUEST_STEPS[2], observed=observed)


def _record_live_user_verification(
    result: dict[str, object],
    observation: GitHubAccessibilityPullRequestGateObservation,
) -> None:
    _record_human_verification(
        result,
        check=(
            "Reviewed the same contributor-visible PR checks surface and GitHub Actions log "
            "that a human reviewer would open to understand why the accessibility gate failed."
        ),
        observed=(
            f"PR checks URL: `{observation.pull_request_checks_url}`; run URL: "
            f"`{observation.latest_pull_request_run_url or '<none>'}`; accessibility check: "
            f"`{observation.accessibility_status_check_name or '<none>'}` with conclusion "
            f"`{observation.accessibility_status_check_conclusion or '<none>'}`; runtime "
            f"accessibility evidence: `{observation.runtime_accessibility_surface_summary or '<none>'}`; "
            f"run-log excerpt: `{_one_line(observation.run_log_excerpt) or '<none>'}`."
        ),
    )


def _has_descriptive_semantics_failure_message(
    observation: GitHubAccessibilityPullRequestGateObservation,
) -> bool:
    if (
        observation.run_log_mentions_semantic_issue
        or observation.run_log_matched_semantic_markers
    ):
        return True

    text = observation.run_log_excerpt or ""
    normalized = " ".join(text.lower().split())
    patterns = [
        r"flutter engine[^\n]*failed to render semantics nodes",
        r"failed to (?:load|render|expose)[^\n]*semantics (?:tree|nodes)",
        r"semantics (?:tree|nodes)[^\n]*(?:failed|failure|did not|could not)[^\n]*(?:load|render|expose)",
        r"flutter[^\n]*semantics (?:tree|nodes)[^\n]*(?:failed|failure|did not|could not)",
        r"page\.waitforfunction",
    ]
    return any(re.search(pattern, normalized) for pattern in patterns)


def _has_generic_network_or_playwright_timeout(
    observation: GitHubAccessibilityPullRequestGateObservation,
) -> bool:
    if observation.run_log_mentions_contrast_issue or observation.run_log_matched_contrast_markers:
        return True

    normalized = " ".join((observation.run_log_excerpt or "").lower().split())
    patterns = [
        r"page\.goto[^\n]*timeout",
        r"page\.waitforloadstate[^\n]*timeout",
        r"navigation timeout",
        r"networkidle",
        r"net::err_[a-z_]+",
        r"timeout of \d+ms exceeded",
        r"timed out while waiting for",
        r"test timeout of \d+ms exceeded",
    ]
    return any(re.search(pattern, normalized) for pattern in patterns)


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
    error = str(result.get("error", "AssertionError: TS-953 failed"))
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
        "* Simulated a network-level page-load timeout only through `testing/accessibility/` in that disposable PR.",
        "* Waited for the live pull-request accessibility workflow to complete.",
        "* Inspected the contributor-visible GitHub Actions log for a generic timeout signal and absence of Flutter-semantics failure wording.",
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
        "- Simulated a network-level page-load timeout only through `testing/accessibility/` in that disposable PR.",
        "- Waited for the live pull-request accessibility workflow to complete.",
        "- Inspected the contributor-visible GitHub Actions log for a generic timeout signal and absence of Flutter-semantics failure wording.",
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
        "- Added TS-953 as a disposable PR probe against the live GitHub Actions accessibility gate.",
        "- The probe simulates a page-load network timeout strictly through `testing/accessibility/` changes in the disposable PR.",
        f"- Test case: **{TICKET_KEY} - {TEST_CASE_TITLE}**",
        f"- Result: **{status}**",
        f"- Command: `{RUN_COMMAND}`",
        (
            f"- Environment: `{result['repository']}` @ `{result['default_branch']}` "
            f"using GitHub CLI on `{result['os']}`."
        ),
        (
            "- Outcome: the live accessibility failure path preserved a generic network or Playwright timeout without reporting a Flutter semantics initialization failure."
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
        "## Steps to reproduce",
        *_bug_step_lines(result),
        "",
        "## Expected",
        EXPECTED_RESULT,
        "",
        "## Actual",
        _failed_step_summary(result),
        "",
        "## Exact error",
        "```text",
        str(result.get("traceback", result.get("error", ""))),
        "```",
        "",
        "## Environment",
        f"- Repository: `{result.get('repository', '<unknown>')}`",
        f"- Branch: `{result.get('default_branch', '<unknown>')}`",
        f"- Browser/client: `{result.get('browser', '<unknown>')}`",
        f"- OS: `{result.get('os', '<unknown>')}`",
        f"- Pull Request URL: `{result.get('pull_request_url', '<none>')}`",
        f"- PR checks URL: `{result.get('pull_request_checks_url', '<none>')}`",
        f"- Workflow run URL: `{result.get('latest_pull_request_run_url', '<none>')}`",
        "",
        "## Relevant logs",
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
        status = "❌" if step is None or step.get("status") != "passed" else "✅"
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


def _one_line(value: object) -> str:
    return " ".join(str(value).split()).strip()


if __name__ == "__main__":
    main()
