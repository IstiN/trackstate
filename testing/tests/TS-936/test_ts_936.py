from __future__ import annotations

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

from testing.core.config.github_accessibility_pull_request_gate_config import (  # noqa: E402
    GitHubAccessibilityPullRequestGateConfig,
)
from testing.core.interfaces.github_accessibility_branch_protection_merge_block_probe import (  # noqa: E402
    GitHubAccessibilityBranchProtectionMergeBlockObservation,
)
from testing.tests.support.github_accessibility_branch_protection_merge_block_probe_factory import (  # noqa: E402
    create_github_accessibility_branch_protection_merge_block_probe,
)

TICKET_KEY = "TS-936"
TEST_CASE_TITLE = "Branch protection blocks merge when accessibility audit fails"
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-936/test_ts_936.py"
TEST_FILE_PATH = "testing/tests/TS-936/test_ts_936.py"
CONFIG_PATH = REPO_ROOT / "testing/tests/TS-936/config.yaml"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"

REQUEST_STEPS = [
    "Create a Pull Request that introduces a WCAG AA contrast violation.",
    "Push the changes to trigger the CI pipeline.",
    'Wait for the "Accessibility checks" job to fail.',
    "Attempt to merge the Pull Request into the 'main' branch.",
]
EXPECTED_RESULT = (
    'The merge is blocked by GitHub branch protection rules because the required "Accessibility checks" '
    "status has failed."
)
FAILURE_CONCLUSIONS = {"failure", "cancelled", "timed_out", "action_required"}


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    raw_config = _load_yaml(CONFIG_PATH)
    runtime_inputs = raw_config.get("runtime_inputs", {})
    assert isinstance(runtime_inputs, dict)
    config = GitHubAccessibilityPullRequestGateConfig.from_file(CONFIG_PATH)
    expected_required_check = _optional_string(runtime_inputs.get("expected_required_check")) or (
        "Accessibility checks"
    )
    merge_block_markers = _string_list(
        runtime_inputs,
        "merge_block_markers",
        default=["blocked", "required", "status check", "merge"],
    )
    probe = create_github_accessibility_branch_protection_merge_block_probe(
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
        "expected_required_check": expected_required_check,
        "merge_block_markers": merge_block_markers,
        "steps": [],
        "human_verification": [],
    }

    try:
        observation = probe.validate()
        gate = observation.gate
        result.update(gate.to_dict())
        result["required_rule_descriptions"] = observation.required_rule_descriptions
        result["required_check_contexts"] = observation.required_check_contexts
        result["repository_declares_accessibility_required_check"] = (
            observation.repository_declares_accessibility_required_check
        )
        result["pull_request_mergeable"] = observation.pull_request_mergeable
        result["pull_request_merge_state_status"] = observation.pull_request_merge_state_status

        failures: list[str] = []
        _evaluate_pull_request_probe(result, gate=gate, failures=failures)
        _evaluate_ci_trigger(result, gate=gate, failures=failures)
        _evaluate_accessibility_failure(result, observation=observation, failures=failures)
        _evaluate_merge_block(
            result,
            observation=observation,
            expected_required_check=expected_required_check,
            merge_block_markers=merge_block_markers,
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
    print("TS-936 passed")


def _evaluate_pull_request_probe(
    result: dict[str, object],
    *,
    gate,
    failures: list[str],
) -> None:
    step_failures: list[str] = []
    if gate.pull_request_probe_path not in gate.pull_request_file_paths:
        step_failures.append(
            f"GitHub did not record the expected disposable probe file `{gate.pull_request_probe_path}`."
        )
    if not gate.probe_rendered_in_application:
        step_failures.append(
            "the disposable PR did not wire the low-contrast probe into a rendered application surface."
        )
    if not gate.runtime_accessibility_surface_present:
        step_failures.append(
            "the accessibility scan did not expose a runtime semantics surface for the rendered probe."
        )
    if not gate.probe_contains_low_contrast_indicator:
        step_failures.append(
            "the disposable PR probe did not contain the requested WCAG AA contrast violation signal."
        )

    if step_failures:
        message = (
            "Step 1 failed: "
            + " ".join(step_failures)
            + "\n"
            + f"Pull Request URL: {gate.pull_request_url}\n"
            + f"Observed PR files: {gate.pull_request_file_paths}\n"
            + "Live host summary: "
            + f"{gate.default_branch_probe_host_summary or '<none>'}\n"
            + "Runtime accessibility surface: "
            + f"{gate.runtime_accessibility_surface_summary or '<none>'}\n"
            + f"Probe technique: {gate.probe_contrast_technique}"
        )
        failures.append(message)
        _record_step(result, step=1, status="failed", action=REQUEST_STEPS[0], observed=message)
        return

    if gate.probe_render_host_path in gate.pull_request_file_paths:
        observed = (
            "Created a disposable PR and verified that GitHub recorded the rendered low-contrast "
            f"probe file `{gate.pull_request_probe_path}` plus render host `{gate.probe_render_host_path}`.\n"
            f"Pull Request URL: {gate.pull_request_url}\n"
            f"Observed PR files: {gate.pull_request_file_paths}\n"
            f"Runtime accessibility surface: {gate.runtime_accessibility_surface_summary}\n"
            f"Probe technique: {gate.probe_contrast_technique}"
        )
    else:
        observed = (
            "Created a disposable PR and verified that GitHub recorded the low-contrast "
            f"probe file `{gate.pull_request_probe_path}` while the live `{gate.probe_render_host_path}` "
            "already exposed the rendered accessibility probe on the default branch.\n"
            f"Pull Request URL: {gate.pull_request_url}\n"
            f"Observed PR files: {gate.pull_request_file_paths}\n"
            f"Live host summary: {gate.default_branch_probe_host_summary}\n"
            f"Runtime accessibility surface: {gate.runtime_accessibility_surface_summary}\n"
            f"Probe technique: {gate.probe_contrast_technique}"
        )
    _record_step(result, step=1, status="passed", action=REQUEST_STEPS[0], observed=observed)


def _evaluate_ci_trigger(
    result: dict[str, object],
    *,
    gate,
    failures: list[str],
) -> None:
    step_failures: list[str] = []
    if gate.latest_pull_request_run_id is None:
        step_failures.append(
            "GitHub Actions did not expose a contributor-visible `pull_request` run for the disposable PR."
        )
    if gate.latest_pull_request_run_event != "pull_request":
        step_failures.append(
            f"the observed workflow event was `{gate.latest_pull_request_run_event}` instead of `pull_request`."
        )

    if step_failures:
        message = (
            "Step 2 failed: "
            + " ".join(step_failures)
            + "\n"
            + f"Pull Request URL: {gate.pull_request_url}\n"
            + f"Observed branch runs: {gate.observed_branch_run_names}\n"
            + f"Observed run URLs: {gate.observed_branch_run_urls}"
        )
        failures.append(message)
        _record_step(result, step=2, status="failed", action=REQUEST_STEPS[1], observed=message)
        return

    observed = (
        "Pushed the disposable PR branch and observed the live pull-request workflow run.\n"
        f"Run URL: {gate.latest_pull_request_run_url}\n"
        f"Status: {gate.latest_pull_request_run_status}\n"
        f"Conclusion: {gate.latest_pull_request_run_conclusion or '<pending>'}"
    )
    _record_step(result, step=2, status="passed", action=REQUEST_STEPS[1], observed=observed)


def _evaluate_accessibility_failure(
    result: dict[str, object],
    *,
    observation: GitHubAccessibilityBranchProtectionMergeBlockObservation,
    failures: list[str],
) -> None:
    gate = observation.gate
    step_failures: list[str] = []

    if gate.accessibility_status_check_name is None:
        step_failures.append(
            "the PR checks surface did not expose a contributor-visible accessibility status check."
        )
    if (gate.accessibility_status_check_conclusion or "").lower() not in FAILURE_CONCLUSIONS:
        step_failures.append(
            f'the accessibility status check did not fail; observed conclusion was `{gate.accessibility_status_check_conclusion or "<none>"}`.'
        )
    if "Run axe-core accessibility checks" not in gate.observed_step_names:
        step_failures.append(
            "the live workflow run did not expose the `Run axe-core accessibility checks` step."
        )
    if not gate.run_log_matched_contrast_markers:
        step_failures.append(
            "the live workflow log did not expose contrast-violation evidence after the accessibility job failed."
        )

    _record_human_verification(
        result,
        check=(
            "Inspected the disposable PR checks surface and live workflow output through GitHub CLI "
            "(`gh pr view`, `gh run view --log`)."
        ),
        observed=(
            f"PR checks URL: `{gate.pull_request_checks_url}`; required checks: "
            f"{observation.required_check_contexts or ['<none>']}; status checks: "
            f"{gate.observed_status_check_names or ['<none>']}; failed status checks: "
            f"{gate.failed_status_check_names or ['<none>']}; run URL: "
            f"`{gate.latest_pull_request_run_url or '<none>'}`; run conclusion: "
            f"`{gate.latest_pull_request_run_conclusion or '<none>'}`; run-log contrast markers: "
            f"{gate.run_log_matched_contrast_markers or ['<none>']}."
        ),
    )

    if step_failures:
        message = (
            "Step 3 failed: "
            + " ".join(step_failures)
            + "\n"
            + f"Pull Request URL: {gate.pull_request_url}\n"
            + f"Checks URL: {gate.pull_request_checks_url}\n"
            + f"Required checks: {observation.required_check_contexts}\n"
            + f"Required rule descriptions: {observation.required_rule_descriptions}\n"
            + f"Accessibility check: {gate.accessibility_status_check_name or '<none>'}\n"
            + "Accessibility check conclusion: "
            + f"{gate.accessibility_status_check_conclusion or '<none>'}\n"
            + f"Run URL: {gate.latest_pull_request_run_url or '<none>'}\n"
            + f"Run conclusion: {gate.latest_pull_request_run_conclusion or '<none>'}\n"
            + f"Observed steps: {gate.observed_step_names}\n"
            + f"Run log excerpt: {gate.run_log_excerpt or '<none>'}"
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
        'Waited for the contributor-visible "Accessibility checks" status to fail and verified '
        "that the accessibility failure was the live gate outcome.\n"
        f"Required checks: {observation.required_check_contexts}\n"
        f"Accessibility check: {gate.accessibility_status_check_name}\n"
        f"Accessibility check conclusion: {gate.accessibility_status_check_conclusion}\n"
        f"Run URL: {gate.latest_pull_request_run_url}\n"
        f"Run-log contrast markers: {gate.run_log_matched_contrast_markers}"
    )
    _record_step(result, step=3, status="passed", action=REQUEST_STEPS[2], observed=observed)


def _evaluate_merge_block(
    result: dict[str, object],
    *,
    observation: GitHubAccessibilityBranchProtectionMergeBlockObservation,
    expected_required_check: str,
    merge_block_markers: list[str],
    failures: list[str],
) -> None:
    gate = observation.gate
    step_failures: list[str] = []
    required_contexts_lower = [entry.lower() for entry in observation.required_check_contexts]
    merge_surface_text = " ".join(
        [
            observation.pull_request_mergeable or "",
            observation.pull_request_merge_state_status or "",
            gate.pull_request_mergeable_state or "",
            gate.pull_request_status_state or "",
            gate.accessibility_status_check_name or "",
            gate.accessibility_status_check_conclusion or "",
            " ".join(gate.failed_status_check_names),
        ]
    ).lower()

    if expected_required_check.lower() not in required_contexts_lower:
        step_failures.append(
            f'the main-branch protection rules did not list "{expected_required_check}" as a required check.'
        )
    if gate.pull_request_mergeable_state != "blocked":
        step_failures.append(
            f'GitHub did not report the REST mergeable state as `blocked`; observed `{gate.pull_request_mergeable_state or "<none>"}`.'
        )
    if observation.pull_request_merge_state_status != "BLOCKED":
        step_failures.append(
            "GitHub did not report the contributor-visible `mergeStateStatus` as `BLOCKED`; "
            f'observed `{observation.pull_request_merge_state_status or "<none>"}`.'
        )
    if gate.pull_request_status_state != "failure":
        step_failures.append(
            f'GitHub did not report failing status checks on the PR head commit; observed `{gate.pull_request_status_state or "<none>"}`.'
        )
    if expected_required_check not in gate.failed_status_check_names:
        step_failures.append(
            f'the failed status-check list did not include "{expected_required_check}".'
        )
    if not any(marker.lower() in merge_surface_text for marker in merge_block_markers):
        step_failures.append(
            "the merge-blocked PR surface did not expose the expected blocked-state markers."
        )

    _record_human_verification(
        result,
        check=(
            "Reviewed the contributor-visible PR merge surface a maintainer reaches before pressing "
            "Merge and checked whether GitHub marked the PR as blocked."
        ),
        observed=(
            f"Pull Request URL: `{gate.pull_request_url}`; checks URL: `{gate.pull_request_checks_url}`; "
            f"required checks: {observation.required_check_contexts}; failed status checks: "
            f"{gate.failed_status_check_names}; mergeable: `{observation.pull_request_mergeable or '<none>'}`; "
            f"mergeStateStatus: `{observation.pull_request_merge_state_status or '<none>'}`; "
            f"REST mergeable_state: `{gate.pull_request_mergeable_state or '<none>'}`."
        ),
    )

    if step_failures:
        message = (
            "Step 4 failed: "
            + " ".join(step_failures)
            + "\n"
            + f"Pull Request URL: {gate.pull_request_url}\n"
            + f"Checks URL: {gate.pull_request_checks_url}\n"
            + f"Required checks: {observation.required_check_contexts}\n"
            + f"Failed status checks: {gate.failed_status_check_names}\n"
            + f"GraphQL mergeable: {observation.pull_request_mergeable or '<none>'}\n"
            + "GraphQL mergeStateStatus: "
            + f"{observation.pull_request_merge_state_status or '<none>'}\n"
            + f"REST mergeable_state: {gate.pull_request_mergeable_state or '<none>'}\n"
            + f"Commit status state: {gate.pull_request_status_state or '<none>'}"
        )
        failures.append(message)
        _record_step(
            result,
            step=4,
            status="failed",
            action=REQUEST_STEPS[3],
            observed=message,
        )
        return

    observed = (
        "GitHub's merge surface showed the disposable PR as blocked from merge after the "
        f'"{expected_required_check}" failure.\n'
        f"Required checks: {observation.required_check_contexts}\n"
        f"Failed status checks: {gate.failed_status_check_names}\n"
        f"GraphQL mergeable: {observation.pull_request_mergeable or '<none>'}\n"
        f"GraphQL mergeStateStatus: {observation.pull_request_merge_state_status}\n"
        f"REST mergeable_state: {gate.pull_request_mergeable_state}\n"
        f"Commit status state: {gate.pull_request_status_state}"
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
    error = str(result.get("error", "AssertionError: TS-936 failed"))
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
    failed_summary = _jira_inline(_failed_step_summary(result))
    lines = [
        "h3. Test Automation Result",
        "",
        f"*Status:* {status}",
        f"*Test Case:* {TICKET_KEY} - {TEST_CASE_TITLE}",
        "",
        "h4. What was automated",
        "* Created a disposable pull request against the live repository using the real accessibility-failure probe pattern.",
        "* Waited for the live pull-request workflow run and contributor-visible accessibility status check to fail.",
        "* Read the branch-protection required-check configuration for the live main branch.",
        "* Verified the contributor-visible PR merge surface stayed blocked after the failed accessibility gate.",
        "",
        "h4. Human-style verification",
        *_human_lines(result, jira=True),
        "",
        "h4. Result",
        (
            "* Matched the expected result."
            if passed
            else f"* Did not match the expected result. {failed_summary}"
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
        "- Created a disposable pull request against the live repository using the real accessibility-failure probe pattern.",
        "- Waited for the live pull-request workflow run and contributor-visible accessibility status check to fail.",
        "- Read the live `main` branch-protection required-check configuration.",
        "- Verified the contributor-visible PR merge surface stayed blocked after the failed accessibility gate.",
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
        "- Added TS-936 as a live disposable-PR regression for accessibility-driven branch protection on `main`.",
        "- The automation verifies the failed accessibility check, required-check configuration, and merge-blocked PR surface through GitHub CLI.",
        f"- Test case: **{TICKET_KEY} - {TEST_CASE_TITLE}**",
        f"- Result: **{status}**",
        f"- Command: `{RUN_COMMAND}`",
        (
            f"- Environment: `{result['repository']}` @ `{result['default_branch']}` "
            f"using GitHub CLI on `{result['os']}`."
        ),
        (
            '- Outcome: the required "Accessibility checks" failure blocked the PR from merge.'
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
    actual_result = (
        f'The live required checks were `{result.get("required_check_contexts", [])}`, '
        f'the `Accessibility checks` status concluded '
        f'`{result.get("accessibility_status_check_conclusion", "<none>")}`, '
        f'the failed status-check list was `{result.get("failed_status_check_names", [])}`, '
        f'and GitHub still reported `mergeStateStatus='
        f'{result.get("pull_request_merge_state_status", "<none>")}` with '
        f'`mergeable_state={result.get("pull_request_mergeable_state", "<none>")}`.'
    )
    return "\n".join(
        [
            f"# {TICKET_KEY} - Branch protection did not keep the PR merge-blocked after accessibility failure",
            "",
            "## Steps to reproduce",
            (
                "1. ✅ Create a Pull Request that introduces a WCAG AA contrast violation."
                if _step_status(result, 1) == "passed"
                else "1. ❌ Create a Pull Request that introduces a WCAG AA contrast violation."
            ),
            f"   - {_step_observed(result, 1)}",
            (
                "2. ✅ Push the changes to trigger the CI pipeline."
                if _step_status(result, 2) == "passed"
                else "2. ❌ Push the changes to trigger the CI pipeline."
            ),
            f"   - {_step_observed(result, 2)}",
            (
                '3. ✅ Wait for the "Accessibility checks" job to fail.'
                if _step_status(result, 3) == "passed"
                else '3. ❌ Wait for the "Accessibility checks" job to fail.'
            ),
            f"   - {_step_observed(result, 3)}",
            (
                "4. ✅ Attempt to merge the Pull Request into the 'main' branch."
                if _step_status(result, 4) == "passed"
                else "4. ❌ Attempt to merge the Pull Request into the 'main' branch."
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
            f"- {actual_result}",
            "",
            "## Actual vs Expected",
            f"- Expected: {EXPECTED_RESULT}",
            f"- Actual: {_failed_step_summary(result)}",
            "",
            "## Environment details",
            f"- Repository: `{result.get('repository', '')}`",
            f"- Branch: `{result.get('default_branch', '')}`",
            f"- Pull Request: `{result.get('pull_request_url', '')}`",
            f"- Pull Request checks: `{result.get('pull_request_checks_url', '')}`",
            f"- Workflow run: `{result.get('latest_pull_request_run_url', '')}`",
            f"- Client: `GitHub CLI`",
            f"- OS: `{result.get('os', '')}`",
            "",
            "## Screenshots / logs",
            f"- Required checks: `{result.get('required_check_contexts', [])}`",
            f"- Failed status checks: `{result.get('failed_status_check_names', [])}`",
            f"- GraphQL mergeStateStatus: `{result.get('pull_request_merge_state_status', '<none>')}`",
            f"- REST mergeable_state: `{result.get('pull_request_mergeable_state', '<none>')}`",
            f"- Run-log excerpt: `{result.get('run_log_excerpt', '<none>')}`",
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
    def _first_line(entry: dict[str, object]) -> str:
        first_line = str(entry.get("observed", "")).splitlines()[0]
        prefix = f"Step {entry.get('step')} failed: "
        if first_line.startswith(prefix):
            return first_line[len(prefix) :]
        return first_line
    summaries = [
        f"Step {entry.get('step')} failed: {_first_line(entry)}"
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


def _jira_inline(text: str) -> str:
    code_segments: list[str] = []

    def _capture(match: re.Match[str]) -> str:
        code_segments.append(match.group(1))
        return f"__TS936_JIRA_CODE_{len(code_segments) - 1}__"

    text = re.sub(r"`([^`]+)`", _capture, text)
    text = text.replace("{", "\\{").replace("}", "\\}")
    for index, segment in enumerate(code_segments):
        escaped_segment = segment.replace("{", "\\{").replace("}", "\\}")
        text = text.replace(f"__TS936_JIRA_CODE_{index}__", f"{{{{{escaped_segment}}}}}")
    return text


def _optional_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


if __name__ == "__main__":
    main()
