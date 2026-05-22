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
    GitHubWorkflowStageLogEntry,
)
from testing.core.config.github_accessibility_pull_request_gate_config import (  # noqa: E402
    GitHubAccessibilityPullRequestGateConfig,
)
from testing.core.interfaces.github_accessibility_pull_request_gate_probe import (  # noqa: E402
    GitHubAccessibilityPullRequestGateObservation,
)
from testing.tests.support.github_accessibility_missing_placeholder_probe_factory import (  # noqa: E402
    create_github_accessibility_missing_placeholder_probe,
    create_github_accessibility_missing_placeholder_stage_log_inspector,
)

TICKET_KEY = "TS-952"
TEST_CASE_TITLE = (
    "Execute gate with missing semantics placeholder - descriptive pre-flight error logged"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-952/test_ts_952.py"
TEST_FILE_PATH = "testing/tests/TS-952/test_ts_952.py"
CONFIG_PATH = REPO_ROOT / "testing/tests/TS-952/config.yaml"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"

REQUEST_STEPS = [
    "Trigger the accessibility gate CI job.",
    "Monitor the 'Accessibility checks' job execution at the pre-flight validation stage.",
    "Inspect the resulting error log output.",
]
EXPECTED_RESULT = (
    "The job fails during the pre-flight check with a specific error message "
    "identifying the missing 'flt-semantics-placeholder' instead of proceeding "
    "to the standard timeout-prone polling logic."
)
EXPECTED_FAILURE_CONCLUSION = "failure"
MISSING_PLACEHOLDER_PATTERNS = (
    re.compile(
        r"(?:pre-flight|preflight)[^\n]*flt-semantics-placeholder[^\n]*"
        r"(?:missing|absent|not found|not present|did not render|never appeared)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:missing|absent|not found|not present|did not render|never appeared)"
        r"[^\n]*flt-semantics-placeholder",
        re.IGNORECASE,
    ),
    re.compile(
        r"flt-semantics-placeholder[^\n]*(?:missing|absent|not found|not present|"
        r"did not render|never appeared)",
        re.IGNORECASE,
    ),
)
GENERIC_TIMEOUT_PATTERNS = (
    re.compile(r"page\.waitforselector[^\n]*timeout", re.IGNORECASE),
    re.compile(r"page\.waitforfunction[^\n]*timeout", re.IGNORECASE),
    re.compile(r"test timeout of \d+ms exceeded", re.IGNORECASE),
    re.compile(r"timeout \d+ms exceeded", re.IGNORECASE),
)
UNEXPECTED_POLLING_MARKERS = (
    "verified flt-semantics-placeholder",
    "accessibility runtime surface ready:",
    "page.waitforfunction",
    "semantics placeholder attached",
)


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    config = GitHubAccessibilityPullRequestGateConfig.from_file(CONFIG_PATH)
    probe = create_github_accessibility_missing_placeholder_probe(
        REPO_ROOT,
        config_path=CONFIG_PATH,
    )
    log_inspector = create_github_accessibility_missing_placeholder_stage_log_inspector(
        REPO_ROOT
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
        "accessibility_stage_log_entries": [],
        "accessibility_stage_log_excerpt": "",
    }

    try:
        observation = probe.validate()
        result.update(observation.to_dict())

        stage_entries, stage_log_error = _read_accessibility_stage_entries(
            observation,
            log_inspector=log_inspector,
        )
        stage_log_lines = [entry.raw_line for entry in stage_entries]
        result["stage_log_error"] = stage_log_error
        result["accessibility_stage_log_entries"] = stage_log_lines
        result["accessibility_stage_log_excerpt"] = _stage_excerpt(stage_log_lines, observation)

        failures: list[str] = []
        _evaluate_failure_simulation_setup(result, observation, failures)
        _evaluate_preflight_stage_surface(
            result,
            observation,
            failures,
            stage_log_error=stage_log_error,
            stage_log_lines=stage_log_lines,
        )
        _evaluate_error_log(
            result,
            observation,
            failures,
            stage_log_lines=stage_log_lines,
        )
        _record_live_user_verification(
            result,
            observation,
            stage_log_error=stage_log_error,
            stage_log_lines=stage_log_lines,
        )

        if failures:
            raise AssertionError("\n\n".join(failures))
    except Exception as error:
        result.setdefault("error", f"{type(error).__name__}: {error}")
        result.setdefault("traceback", traceback.format_exc())
        _write_failure_outputs(result)
        raise

    _write_pass_outputs(result)
    print("TS-952 passed")


def _read_accessibility_stage_entries(
    observation: GitHubAccessibilityPullRequestGateObservation,
    *,
    log_inspector,
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


def _evaluate_failure_simulation_setup(
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
            f"GitHub did not record the expected simulation files: {missing_files}."
        )
    if unexpected_files:
        step_failures.append(
            "the disposable PR changed files outside `testing/accessibility/`, which means "
            f"the missing-placeholder simulation was not isolated: {unexpected_files}."
        )
    if observation.latest_pull_request_run_id is None:
        step_failures.append(
            "GitHub Actions did not expose a contributor-visible pull-request workflow run."
        )

    if step_failures:
        message = (
            "Step 1 failed: "
            + " ".join(step_failures)
            + "\n"
            + f"Pull Request URL: {observation.pull_request_url}\n"
            + f"Observed PR files: {observation.pull_request_file_paths}\n"
            + f"Simulation technique: {observation.probe_contrast_technique}"
        )
        failures.append(message)
        _record_step(result, step=1, status="failed", action=REQUEST_STEPS[0], observed=message)
        return

    observed = (
        "Created a disposable PR that hides `flt-semantics-placeholder` only through "
        "accessibility harness files and triggered the live pull-request workflow.\n"
        f"Pull Request URL: {observation.pull_request_url}\n"
        f"Observed PR files: {observation.pull_request_file_paths}\n"
        f"Workflow run URL: {observation.latest_pull_request_run_url}\n"
        f"Simulation technique: {observation.probe_contrast_technique}"
    )
    _record_step(result, step=1, status="passed", action=REQUEST_STEPS[0], observed=observed)


def _evaluate_preflight_stage_surface(
    result: dict[str, object],
    observation: GitHubAccessibilityPullRequestGateObservation,
    failures: list[str],
    *,
    stage_log_error: str | None,
    stage_log_lines: list[str],
) -> None:
    step_failures: list[str] = []
    if observation.latest_pull_request_run_event != "pull_request":
        step_failures.append(
            f"the observed workflow event was `{observation.latest_pull_request_run_event or '<none>'}` instead of `pull_request`."
        )
    if observation.latest_pull_request_run_status != "completed":
        step_failures.append(
            f"the workflow run never completed; observed status was `{observation.latest_pull_request_run_status or '<none>'}`."
        )
    if observation.latest_pull_request_run_conclusion != EXPECTED_FAILURE_CONCLUSION:
        step_failures.append(
            "the workflow run did not fail after the simulated missing placeholder; "
            f"observed conclusion was `{observation.latest_pull_request_run_conclusion or '<none>'}`."
        )
    if observation.accessibility_status_check_conclusion != EXPECTED_FAILURE_CONCLUSION:
        step_failures.append(
            "the contributor-visible accessibility status check did not end in failure; "
            f"observed conclusion was `{observation.accessibility_status_check_conclusion or '<none>'}`."
        )
    if stage_log_error is not None:
        step_failures.append(
            f"the hosted accessibility-stage log could not be read: {stage_log_error}."
        )
    if "Accessibility checks" not in observation.observed_job_names and (
        "Run axe-core accessibility checks" not in observation.observed_step_names
    ):
        step_failures.append(
            "the contributor-visible workflow surface did not expose the expected `Accessibility checks` stage."
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
            + "Run status/conclusion: "
            + f"{observation.latest_pull_request_run_status or '<none>'}/"
            + f"{observation.latest_pull_request_run_conclusion or '<none>'}\n"
            + f"Accessibility check conclusion: {observation.accessibility_status_check_conclusion or '<none>'}\n"
            + f"Observed jobs: {observation.observed_job_names or ['<none>']}\n"
            + f"Observed steps: {observation.observed_step_names or ['<none>']}\n"
            + "Accessibility-stage excerpt:\n"
            + (_stage_excerpt(stage_log_lines, observation) or "<none>")
        )
        failures.append(message)
        _record_step(result, step=2, status="failed", action=REQUEST_STEPS[1], observed=message)
        return

    observed = (
        "Opened the contributor-visible `Accessibility checks` stage log for the hosted PR "
        "workflow run and confirmed the run failed during the accessibility stage.\n"
        f"Run URL: {observation.latest_pull_request_run_url}\n"
        f"Run status/conclusion: {observation.latest_pull_request_run_status}/{observation.latest_pull_request_run_conclusion}\n"
        f"Accessibility check conclusion: {observation.accessibility_status_check_conclusion}\n"
        f"Observed jobs: {observation.observed_job_names}\n"
        f"Observed steps: {observation.observed_step_names}\n"
        f"Accessibility-stage excerpt:\n{_stage_excerpt(stage_log_lines, observation)}"
    )
    _record_step(result, step=2, status="passed", action=REQUEST_STEPS[1], observed=observed)


def _evaluate_error_log(
    result: dict[str, object],
    observation: GitHubAccessibilityPullRequestGateObservation,
    failures: list[str],
    *,
    stage_log_lines: list[str],
) -> None:
    focused_excerpt = observation.run_log_excerpt or _stage_excerpt(stage_log_lines, observation)
    descriptive_message = _extract_missing_placeholder_message(focused_excerpt)
    full_log_timeout_message = _full_log_generic_timeout_message(observation, focused_excerpt)
    unexpected_polling_lines = _full_log_unexpected_polling_lines(
        observation,
        focused_excerpt=focused_excerpt,
        stage_log_lines=stage_log_lines,
    )

    step_failures: list[str] = []
    if observation.run_log_error is not None:
        step_failures.append(
            f"GitHub CLI could not read the hosted workflow log: {observation.run_log_error}."
        )
    if descriptive_message is None:
        step_failures.append(
            "the hosted accessibility error did not explicitly identify the missing "
            "`flt-semantics-placeholder` pre-flight condition."
        )
    if full_log_timeout_message is not None:
        step_failures.append(
            "the hosted accessibility failure still surfaced a generic Playwright timeout "
            f"instead of a targeted missing-placeholder message: {full_log_timeout_message}."
        )
    if unexpected_polling_lines:
        step_failures.append(
            "the hosted accessibility flow unexpectedly continued into later polling/runtime "
            f"evidence after the missing-placeholder failure: {unexpected_polling_lines}."
        )

    if step_failures:
        message = (
            "Step 3 failed: "
            + " ".join(step_failures)
            + "\n"
            + f"Run URL: {observation.latest_pull_request_run_url or '<none>'}\n"
            + f"Missing-placeholder message: {descriptive_message or '<none>'}\n"
            + f"Generic timeout evidence: {full_log_timeout_message or '<none>'}\n"
            + "Run-log timeout markers: "
            + f"{observation.run_log_matched_contrast_markers or ['<none>']}\n"
            + "Unexpected polling/runtime evidence: "
            + f"{unexpected_polling_lines or ['<none>']}\n"
            + "Hosted run-log excerpt:\n"
            + (focused_excerpt or "<none>")
        )
        failures.append(message)
        _record_step(result, step=3, status="failed", action=REQUEST_STEPS[2], observed=message)
        return

    observed = (
        "Inspected the contributor-visible GitHub Actions log and found a descriptive "
        "missing-`flt-semantics-placeholder` pre-flight failure without the generic timeout "
        "or later polling/runtime evidence.\n"
        f"Run URL: {observation.latest_pull_request_run_url}\n"
        f"Missing-placeholder message: {descriptive_message}\n"
        f"Hosted run-log excerpt:\n{focused_excerpt}"
    )
    _record_step(result, step=3, status="passed", action=REQUEST_STEPS[2], observed=observed)


def _record_live_user_verification(
    result: dict[str, object],
    observation: GitHubAccessibilityPullRequestGateObservation,
    *,
    stage_log_error: str | None,
    stage_log_lines: list[str],
) -> None:
    excerpt = _stage_excerpt(stage_log_lines, observation)
    _record_human_verification(
        result,
        check=(
            "Reviewed the same contributor-visible PR checks surface and accessibility-stage "
            "log a human maintainer would open from GitHub Actions."
        ),
        observed=(
            f"PR checks URL: `{observation.pull_request_checks_url}`; run URL: "
            f"`{observation.latest_pull_request_run_url or '<none>'}`; accessibility check: "
            f"`{observation.accessibility_status_check_name or '<none>'}` with conclusion "
            f"`{observation.accessibility_status_check_conclusion or '<none>'}`; jobs: "
            f"`{observation.observed_job_names or ['<none>']}`; steps: "
            f"`{observation.observed_step_names or ['<none>']}`."
        ),
    )
    _record_human_verification(
        result,
        check=(
            "Read the hosted error text as a reviewer would to confirm the failure calls out "
            "the missing placeholder instead of a generic timeout."
        ),
        observed=(
            f"Stage log read error: `{stage_log_error or '<none>'}`; missing-placeholder "
            f"message: `{_extract_missing_placeholder_message(excerpt) or '<none>'}`; generic "
            f"timeout: `{_extract_generic_timeout_message(excerpt) or '<none>'}`; stage/log "
            f"excerpt: `{_one_line(excerpt) or '<none>'}`."
        ),
    )


def _extract_missing_placeholder_message(text: str) -> str | None:
    for raw_line in text.splitlines():
        line = _one_line(raw_line)
        if "flt-semantics-placeholder" not in line.lower():
            continue
        for pattern in MISSING_PLACEHOLDER_PATTERNS:
            match = pattern.search(line)
            if match is not None:
                return _one_line(match.group(0))
    return None


def _extract_generic_timeout_message(text: str) -> str | None:
    for raw_line in text.splitlines():
        line = _one_line(raw_line)
        for pattern in GENERIC_TIMEOUT_PATTERNS:
            match = pattern.search(line)
            if match is not None:
                return _one_line(match.group(0))
    return None


def _unexpected_polling_lines(log_lines: list[str]) -> list[str]:
    matches: list[str] = []
    for line in log_lines:
        lowered = line.lower()
        if any(marker in lowered for marker in UNEXPECTED_POLLING_MARKERS):
            matches.append(line)
    return _dedupe_preserving_order(matches)


def _full_log_generic_timeout_message(
    observation: GitHubAccessibilityPullRequestGateObservation,
    focused_excerpt: str,
) -> str | None:
    excerpt_timeout = _extract_generic_timeout_message(focused_excerpt)
    if excerpt_timeout is not None:
        return excerpt_timeout
    if observation.run_log_matched_contrast_markers:
        return " / ".join(observation.run_log_matched_contrast_markers)
    if observation.run_log_mentions_contrast_issue:
        return "run_log_mentions_contrast_issue"
    return None


def _full_log_unexpected_polling_lines(
    observation: GitHubAccessibilityPullRequestGateObservation,
    *,
    focused_excerpt: str,
    stage_log_lines: list[str],
) -> list[str]:
    evidence_lines = [
        *focused_excerpt.splitlines(),
        *stage_log_lines,
        *observation.semantics_tree_discovery_log_entries,
        *observation.flutter_engine_initialization_log_entries,
    ]
    if observation.runtime_accessibility_surface_summary:
        evidence_lines.append(observation.runtime_accessibility_surface_summary)
    return _unexpected_polling_lines(evidence_lines)


def _stage_excerpt(
    stage_log_lines: list[str],
    observation: GitHubAccessibilityPullRequestGateObservation,
) -> str:
    if stage_log_lines:
        return "\n".join(stage_log_lines[:12])
    return observation.run_log_excerpt or ""


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
    error = str(result.get("error", "AssertionError: TS-952 failed"))
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
        "* Simulated a missing {{flt-semantics-placeholder}} strictly through {{testing/accessibility/}} changes in that disposable PR.",
        "* Waited for the live pull-request accessibility workflow to complete and isolated the contributor-visible {{Accessibility checks}} stage log.",
        "* Checked that the hosted error names the missing placeholder and does not continue into the generic timeout/polling path.",
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
        "- Simulated a missing `flt-semantics-placeholder` strictly through `testing/accessibility/` changes in that disposable PR.",
        "- Waited for the live pull-request accessibility workflow to complete and isolated the contributor-visible `Accessibility checks` stage log.",
        "- Checked that the hosted error names the missing placeholder and does not continue into the generic timeout/polling path.",
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
        "- Added TS-952 as a disposable PR probe against the live GitHub Actions accessibility gate.",
        "- The probe hides `flt-semantics-placeholder` through `testing/accessibility/` changes and checks whether the workflow reports the missing-placeholder pre-flight failure instead of a generic timeout.",
        f"- Test case: **{TICKET_KEY} - {TEST_CASE_TITLE}**",
        f"- Result: **{status}**",
        f"- Command: `{RUN_COMMAND}`",
        (
            f"- Environment: `{result['repository']}` @ `{result['default_branch']}` "
            f"using GitHub CLI on `{result['os']}`."
        ),
        (
            "- Outcome: the live accessibility gate reported the missing placeholder directly and stopped before the timeout-prone polling path."
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
        f"# {TICKET_KEY} - Accessibility gate does not log a descriptive missing-placeholder pre-flight error\n\n"
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
        "- **Actual:** The live disposable PR run did not expose a contributor-visible "
        "pre-flight error that explicitly names the missing "
        "`flt-semantics-placeholder` and/or it still fell through to generic timeout "
        "or later polling/runtime evidence.\n\n"
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
        "- **Accessibility-stage log excerpt:**\n"
        "```text\n"
        f"{result.get('accessibility_stage_log_excerpt', '<missing stage log excerpt>')}\n"
        "```\n"
        "- **Hosted run-log excerpt:**\n"
        "```text\n"
        f"{result.get('run_log_excerpt', '<missing run log excerpt>')}\n"
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


def _dedupe_preserving_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        normalized = _one_line(value)
        if normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(value)
    return deduped


def _one_line(text: object) -> str:
    return " ".join(str(text).split())


if __name__ == "__main__":
    main()
