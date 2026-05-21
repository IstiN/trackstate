from __future__ import annotations

from dataclasses import asdict
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
from testing.tests.support.github_actions_page_factory import (  # noqa: E402
    create_github_actions_page,
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
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts908_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts908_failure.png"

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


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

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
        "expected_accessibility_markers": list(config.expected_accessibility_markers),
        "browser": "Chromium (Playwright)",
        "os": platform.platform(),
        "steps": [],
        "human_verification": [],
    }

    try:
        observation = probe.validate()
        result.update(observation.to_dict())

        failures: list[str] = []
        _evaluate_workflow_presence(result, observation, failures)
        _evaluate_accessibility_gate_contract(result, observation, failures)
        _evaluate_required_checks(result, observation, failures)
        _evaluate_human_verification(result, observation, config, failures)

        if failures:
            raise AssertionError("\n".join(failures))
    except Exception as error:
        result.setdefault("error", f"{type(error).__name__}: {error}")
        result.setdefault("traceback", traceback.format_exc())
        _write_failure_outputs(result)
        raise

    _write_pass_outputs(result)
    print("TS-908 passed")


def _evaluate_workflow_presence(
    result: dict[str, object],
    observation: GitHubAccessibilityPullRequestGateObservation,
    failures: list[str],
) -> None:
    if not observation.target_workflow_present_on_default_branch:
        message = (
            "Step 1 failed: the live repository does not expose the pull-request workflow "
            f"`{observation.target_workflow_path}` on the default branch.\n"
            f"Observed workflow paths: {observation.default_branch_workflow_paths}"
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
    if not observation.target_workflow_declares_pull_request_trigger:
        message = (
            "Step 1 failed: the target workflow exists, but it does not declare a "
            "contributor-visible `pull_request` trigger.\n"
            f"Workflow path: {observation.target_workflow_path}\n"
            f"Observed PR workflows: {observation.pull_request_workflow_paths}"
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

    _record_step(
        result,
        step=1,
        status="passed",
        action=REQUEST_STEPS[0],
        observed=(
            "Read the live default-branch workflow contract instead of mutating the "
            "repository. The contributor-visible PR workflow "
            f"`{observation.target_workflow_path}` is present and declares `pull_request`."
        ),
    )


def _evaluate_accessibility_gate_contract(
    result: dict[str, object],
    observation: GitHubAccessibilityPullRequestGateObservation,
    failures: list[str],
) -> None:
    if observation.workflows_with_accessibility_markers:
        _record_step(
            result,
            step=2,
            status="passed",
            action=REQUEST_STEPS[1],
            observed=(
                "The live PR workflow set declares accessibility-oriented markers in "
                f"{observation.workflow_accessibility_markers_found}."
            ),
        )
        return

    message = (
        "Step 2 failed: none of the live default-branch PR workflows declared any "
        "accessibility gate markers, so a PR carrying a low-contrast widget plus a "
        "non-descriptive ARIA label would not reach an `axe-core`/accessibility stage.\n"
        f"Expected markers: {observation.expected_accessibility_markers}\n"
        f"Observed PR workflows: {observation.pull_request_workflow_paths}\n"
        f"Observed target workflow jobs: {observation.target_workflow_job_names}\n"
        f"Observed target workflow steps: {observation.target_workflow_step_names}"
    )
    failures.append(message)
    _record_step(
        result,
        step=2,
        status="failed",
        action=REQUEST_STEPS[1],
        observed=message,
    )


def _evaluate_required_checks(
    result: dict[str, object],
    observation: GitHubAccessibilityPullRequestGateObservation,
    failures: list[str],
) -> None:
    if observation.repository_declares_accessibility_required_check:
        _record_step(
            result,
            step=3,
            status="passed",
            action=REQUEST_STEPS[2],
            observed=(
                "The repository rules declare an accessibility-related required check or "
                f"workflow: contexts={observation.required_check_contexts}, "
                f"workflows={observation.required_check_workflow_paths}."
            ),
        )
        return

    message = (
        "Step 3 failed: the live branch rules / required checks do not declare any "
        "accessibility-oriented status check or workflow, so the CI pipeline would not "
        "block a pull request on contrast or ARIA defects.\n"
        f"Required rule descriptions: {observation.required_rule_descriptions}\n"
        f"Required contexts: {observation.required_check_contexts}\n"
        f"Required workflows: {observation.required_check_workflow_paths}\n"
        f"Required workflow names: {observation.required_check_workflow_names}"
    )
    failures.append(message)
    _record_step(
        result,
        step=3,
        status="failed",
        action=REQUEST_STEPS[2],
        observed=message,
    )


def _evaluate_human_verification(
    result: dict[str, object],
    observation: GitHubAccessibilityPullRequestGateObservation,
    config: GitHubAccessibilityPullRequestGateConfig,
    failures: list[str],
) -> None:
    expected_texts = tuple(
        value
        for value in (
            observation.target_workflow_name,
            *observation.target_workflow_step_names[:2],
            *observation.target_workflow_job_names[:1],
        )
        if value
    )
    workflow_file_url = _workflow_file_url(
        repository=observation.repository,
        branch=observation.default_branch,
        workflow_path=observation.target_workflow_path,
    )

    try:
        with create_github_actions_page() as page:
            page_observation = page.open_page(
                url=workflow_file_url,
                expected_texts=expected_texts or (observation.target_workflow_name,),
                screenshot_path=str(
                    SUCCESS_SCREENSHOT_PATH if not failures else FAILURE_SCREENSHOT_PATH
                ),
                timeout_seconds=config.ui_timeout_seconds,
            )
    except Exception as error:
        message = (
            "Step 4 failed: the live GitHub workflow file page could not be opened for "
            f"human-style verification.\nURL: {workflow_file_url}\nError: {error}"
        )
        failures.append(message)
        _record_step(
            result,
            step=4,
            status="failed",
            action=REQUEST_STEPS[3],
            observed=message,
        )
        _record_human_verification(
            result,
            check=(
                "Tried to open the live GitHub workflow file page as a maintainer would "
                "when checking what PR stages are actually visible."
            ),
            observed=message,
        )
        return

    result["workflow_file_url"] = workflow_file_url
    result["workflow_file_page"] = asdict(page_observation)

    body_text = page_observation.body_text
    visible_markers = [
        marker
        for marker in observation.expected_accessibility_markers
        if marker.lower() in body_text.lower()
    ]
    visible_step_list = observation.target_workflow_step_names or ["<none>"]
    _record_human_verification(
        result,
        check=(
            "Opened the live GitHub workflow file page and read the visible step list the "
            "same way a maintainer would inspect a PR workflow."
        ),
        observed=(
            f"Workflow file URL: `{workflow_file_url}`; visible step names from the live "
            f"YAML: {visible_step_list}; visible accessibility markers on the page: "
            f"{visible_markers or ['<none>']}; screenshot: "
            f"`{page_observation.screenshot_path}`."
        ),
    )

    if visible_markers:
        _record_step(
            result,
            step=4,
            status="passed",
            action=REQUEST_STEPS[3],
            observed=(
                "The live workflow file page visibly referenced accessibility-oriented "
                f"markers: {visible_markers}."
            ),
        )
        return

    message = (
        "Step 4 failed: the live GitHub workflow file page visibly listed only the "
        "existing Flutter validation steps and did not show any accessibility / "
        "`axe-core` stage that could report contrast and semantic defects.\n"
        f"Workflow file URL: {workflow_file_url}\n"
        f"Matched page text: {page_observation.matched_text!r}\n"
        f"Visible workflow steps: {visible_step_list}\n"
        f"Visible page body excerpt:\n{_snippet(body_text, limit=1200)}"
    )
    failures.append(message)
    _record_step(
        result,
        step=4,
        status="failed",
        action=REQUEST_STEPS[3],
        observed=message,
    )


def _workflow_file_url(*, repository: str, branch: str, workflow_path: str) -> str:
    return f"https://github.com/{repository}/blob/{branch}/{workflow_path}"


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
        "* Read the live default-branch GitHub Actions workflow definitions through the GitHub API.",
        "* Checked whether any contributor-visible PR workflow declared accessibility-gate markers such as {{axe-core}}, {{accessibility}}, {{contrast}}, or {{aria}}.",
        "* Checked whether the repository branch rules / required checks would enforce such an accessibility workflow on PRs.",
        "* Opened the live workflow file page in GitHub and recorded the visible step list as human-style evidence.",
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
    lines.extend(_artifact_lines(result, jira=True))
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
        "- Read the live default-branch GitHub Actions workflow definitions through the GitHub API.",
        "- Checked whether any contributor-visible PR workflow declared accessibility-gate markers such as `axe-core`, `accessibility`, `contrast`, or `aria`.",
        "- Checked whether the repository branch rules / required checks would enforce such an accessibility workflow on PRs.",
        "- Opened the live workflow file page in GitHub and recorded the visible step list as human-style evidence.",
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
    lines.extend(_artifact_lines(result, jira=False))
    return "\n".join(lines) + "\n"


def _response_summary(result: dict[str, object], *, passed: bool) -> str:
    status = "PASSED" if passed else "FAILED"
    lines = [
        "## Test Automation Summary",
        "",
        "- Added TS-908 read-only CI accessibility gate coverage against the live GitHub repository contract.",
        f"- Test case: **{TICKET_KEY} - {TEST_CASE_TITLE}**",
        f"- Result: **{status}**",
        f"- Command: `{RUN_COMMAND}`",
        (
            f"- Environment: `{result['repository']}` @ `{result['default_branch']}` on "
            f"Chromium/Playwright (`{result['os']}`)."
        ),
        (
            "- Outcome: the live PR pipeline exposes and requires an accessibility gate that can catch contrast and ARIA defects."
            if passed
            else f"- Outcome: {_failed_step_summary(result)}"
        ),
    ]
    lines.extend(_artifact_lines(result, jira=False))
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
            f"# {TICKET_KEY} - PR CI does not expose an accessibility gate for contrast and ARIA defects",
            "",
            "## Steps to reproduce",
            "1. Create a Pull Request that introduces a UI element with a text-to-background contrast ratio below 4.5:1.",
            "2. In the same PR, include a component with a non-descriptive ARIA label.",
            "3. Push the changes to trigger the CI pipeline.",
            "4. Inspect the results of the automated accessibility check stage.",
            "",
            "## Exact steps from the test case with observations",
            (
                "1. Create a Pull Request that introduces a UI element with a text-to-background "
                "contrast ratio below 4.5:1.\n"
                "   - ⚠️ Not executed as a repo mutation because this ticket run had to stay "
                "read-only. Instead, the live PR workflow contract on the default branch was "
                "inspected directly to verify whether such a PR would encounter an "
                "accessibility gate."
            ),
            (
                "2. In the same PR, include a component with a non-descriptive ARIA label.\n"
                "   - ⚠️ Not executed as a repo mutation for the same read-only reason. The "
                "live workflow/rules contract below shows there is no CI stage that would "
                "inspect this ARIA defect."
            ),
            (
                "3. Push the changes to trigger the CI pipeline.\n"
                "   - ❌ The live branch rules / required checks do not declare any "
                "accessibility-oriented status check or workflow. Observed required rule "
                f"descriptions: {result.get('required_rule_descriptions', [])}; contexts: "
                f"{result.get('required_check_contexts', [])}; workflows: "
                f"{result.get('required_check_workflow_paths', [])}."
            ),
            (
                "4. Inspect the results of the automated accessibility check stage.\n"
                "   - ❌ The live pull-request workflow `.github/workflows/unit-tests.yml` "
                "visibly exposes only the existing Flutter validation steps and no "
                "accessibility / `axe-core` stage. Observed jobs: "
                f"{result.get('target_workflow_job_names', [])}; observed steps: "
                f"{result.get('target_workflow_step_names', [])}; workflow file URL: "
                f"`{result.get('workflow_file_url', '')}`."
            ),
            "",
            "## Actual vs Expected",
            f"- Expected: {EXPECTED_RESULT}",
            (
                "- Actual: the live PR CI contract does not expose any accessibility gate at "
                "all. No default-branch PR workflow contains `axe-core` / accessibility scan "
                "markers, and the branch rules do not require an accessibility-related status "
                "check. A PR containing both a sub-4.5:1 contrast defect and a weak ARIA label "
                "would therefore not produce the expected failing accessibility stage."
            ),
            "",
            "## Environment",
            f"- Repository: `{result.get('repository', '')}`",
            f"- Branch: `{result.get('default_branch', '')}`",
            f"- Workflow path: `{result.get('target_workflow_path', '')}`",
            f"- Workflow file URL: `{result.get('workflow_file_url', '')}`",
            f"- Browser: `{result.get('browser', '')}`",
            f"- OS: `{result.get('os', '')}`",
            f"- Screenshot: `{_artifact_path(result)}`",
            "",
            "## Live observations",
            "```json",
            json.dumps(
                {
                    "pull_request_workflow_paths": result.get("pull_request_workflow_paths", []),
                    "workflows_with_accessibility_markers": result.get(
                        "workflows_with_accessibility_markers",
                        [],
                    ),
                    "workflow_accessibility_markers_found": result.get(
                        "workflow_accessibility_markers_found",
                        {},
                    ),
                    "required_rule_descriptions": result.get(
                        "required_rule_descriptions",
                        [],
                    ),
                    "required_check_contexts": result.get("required_check_contexts", []),
                    "required_check_workflow_paths": result.get(
                        "required_check_workflow_paths",
                        [],
                    ),
                    "required_check_workflow_names": result.get(
                        "required_check_workflow_names",
                        [],
                    ),
                    "target_workflow_job_names": result.get(
                        "target_workflow_job_names",
                        [],
                    ),
                    "target_workflow_step_names": result.get(
                        "target_workflow_step_names",
                        [],
                    ),
                    "workflow_file_page": result.get("workflow_file_page", {}),
                },
                indent=2,
            ),
            "```",
            "",
            "## Exact error message / traceback",
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


def _artifact_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    screenshot = _artifact_path(result)
    if not screenshot:
        return []
    if jira:
        return ["", f"* Evidence screenshot: {{{{{screenshot}}}}}"]
    return ["", f"- Evidence screenshot: `{screenshot}`"]


def _artifact_path(result: dict[str, object]) -> str:
    page = result.get("workflow_file_page")
    if isinstance(page, dict):
        screenshot = page.get("screenshot_path")
        if isinstance(screenshot, str):
            return screenshot
    return ""


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


def _snippet(text: str, *, limit: int) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3] + "..."


if __name__ == "__main__":
    main()
