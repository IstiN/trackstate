from __future__ import annotations

from dataclasses import asdict
import json
import platform
import re
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.core.interfaces.github_workflow_trigger_isolation_probe import (  # noqa: E402
    GitHubWorkflowTriggerIsolationProbe,
    GitHubWorkflowTriggerIsolationObservation,
    WorkflowDefinitionObservation,
    WorkflowRunObservation,
)
from testing.tests.support.github_workflow_trigger_isolation_probe_factory import (  # noqa: E402
    create_github_workflow_trigger_isolation_probe,
)

TICKET_KEY = "TS-709"
TEST_CASE_TITLE = (
    "Apple release trigger isolation — workflow ignores main pushes and triggers on tags"
)
RUN_COMMAND = "PYTHONPATH=. python3 testing/tests/TS-709/test_ts_709.py"
TEST_FILE_PATH = "testing/tests/TS-709/test_ts_709.py"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"

REQUEST_STEPS = [
    "Push a standard commit (no tag) to the `main` branch of `IstiN/trackstate`.",
    "Observe the Actions tab to see which workflows trigger.",
    "Push a semantic version tag `v1.2.3` to the `main` branch.",
    "Observe the Actions tab again.",
]
EXPECTED_RESULT = (
    "The push to `main` triggers only the general CI path. The semantic version tag "
    "`v1.2.3` triggers the dedicated Apple release workflow, so Apple release "
    "failures do not redefine or block standard Ubuntu validation for non-release commits."
)


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    probe: GitHubWorkflowTriggerIsolationProbe = (
        create_github_workflow_trigger_isolation_probe(
            REPO_ROOT,
            screenshot_directory=OUTPUTS_DIR,
        )
    )
    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "test_case_title": TEST_CASE_TITLE,
        "run_command": RUN_COMMAND,
        "test_file_path": TEST_FILE_PATH,
        "expected_result": EXPECTED_RESULT,
        "browser": "Chromium (Playwright)",
        "os": platform.platform(),
        "steps": [],
        "human_verification": [],
    }

    try:
        observation = probe.validate()
        result.update(observation.to_dict())
        result["apple_release"] = _workflow_as_dict(observation.apple_release)
        result["main_ci"] = _workflow_as_dict(observation.main_ci)

        _record_step(
            result,
            step=1,
            status="passed",
            action=REQUEST_STEPS[0],
            observed=(
                f"Loaded the live workflow registrations for `{observation.repository}` on "
                f"branch `{observation.default_branch}`. Current default-branch head SHA is "
                f"`{observation.current_default_branch_sha}`. Apple workflow state="
                f"`{observation.apple_release.state}`; main CI workflow state="
                f"`{observation.main_ci.state}`."
            ),
        )

        _assert_workflow_active(observation.apple_release, "Apple release workflow")
        _assert_workflow_active(observation.main_ci, "General CI workflow")

        _assert_apple_release_scope(observation.apple_release, observation.default_branch)
        _record_step(
            result,
            step=2,
            status="passed",
            action=REQUEST_STEPS[1],
            observed=(
                f"`{observation.apple_release.workflow_name}` is defined at "
                f"`{observation.apple_release.workflow_path}` with push tags "
                f"{observation.apple_release.push_tags} and push branches "
                f"{observation.apple_release.push_branches or ['<none>']}. "
                f"The file also shows the semantic example `v1.2.3`."
            ),
        )

        _assert_main_ci_scope(observation.main_ci, observation.default_branch)
        _record_step(
            result,
            step=3,
            status="passed",
            action=REQUEST_STEPS[2],
            observed=(
                f"`{observation.main_ci.workflow_name}` remains wired to push branches "
                f"{observation.main_ci.push_branches}. The Apple workflow keeps the tag-only "
                f"pattern {observation.apple_release.push_tags} needed for `v1.2.3`."
            ),
        )

        _assert_live_run_isolation(observation)
        _record_step(
            result,
            step=4,
            status="passed",
            action=REQUEST_STEPS[3],
            observed=(
                f"Current head SHA `{observation.current_default_branch_sha}` appears on "
                f"{len(observation.main_ci_push_main_current_sha)} recent "
                f"`{observation.main_ci.workflow_name}` push run(s) and on "
                f"{len(observation.apple_push_main_current_sha)} recent "
                f"`{observation.apple_release.workflow_name}` push run(s). "
                f"Post-update cutoff `{observation.cutoff_timestamp}` produced "
                f"{len(observation.main_ci_push_main_after_cutoff)} main-branch CI run(s) and "
                f"{len(observation.apple_push_main_after_cutoff)} Apple main-branch run(s)."
            ),
        )

        _assert_human_verification(observation.apple_release, observation.default_branch)
        _assert_human_verification(observation.main_ci, observation.default_branch)
        _record_human_verification(
            result,
            check=(
                "Opened the live GitHub browser page for the Apple workflow file and "
                "checked the visible trigger text."
            ),
            observed=(
                f"GitHub page `{observation.apple_release.ui_url}` visibly included "
                f"`{observation.apple_release.workflow_name}`, `tags`, "
                f"`{', '.join(observation.apple_release.push_tags)}`, and `v1.2.3`. "
                f"Screenshot: `{observation.apple_release.ui_screenshot_path}`."
            ),
        )
        _record_human_verification(
            result,
            check=(
                "Opened the live GitHub browser page for the general CI workflow file and "
                "checked the visible main-branch trigger text."
            ),
            observed=(
                f"GitHub page `{observation.main_ci.ui_url}` visibly included "
                f"`{observation.main_ci.workflow_name}`, `branches`, and "
                f"`{observation.default_branch}`. Screenshot: "
                f"`{observation.main_ci.ui_screenshot_path}`."
            ),
        )
        _record_human_verification(
            result,
            check=(
                "Reviewed the live Actions outcome a maintainer would care about for the "
                "current default-branch head."
            ),
            observed=(
                f"The current `main` commit `{observation.current_default_branch_sha}` "
                f"appears on `{observation.main_ci.workflow_name}` run URL(s): "
                f"{_run_url_list(observation.main_ci_push_main_current_sha)}. "
                f"No `{observation.apple_release.workflow_name}` push run targeted that same "
                f"SHA. This matches the expected isolation."
            ),
        )
    except Exception as error:
        result.setdefault("error", f"{type(error).__name__}: {error}")
        result.setdefault("traceback", traceback.format_exc())
        _record_failed_step_from_error(result, str(error))
        result["product_failure"] = True
        _write_failure_outputs(result)
        raise

    _write_pass_outputs(result)
    print("TS-709 passed")


def _assert_workflow_active(
    workflow: WorkflowDefinitionObservation,
    label: str,
) -> None:
    if workflow.state != "active":
        raise AssertionError(
            f"Step 1 failed: {label} was not active.\n"
            f"Workflow: {workflow.workflow_name}\n"
            f"State: {workflow.state}\n"
            f"Path: {workflow.workflow_path}\n"
            f"URL: {workflow.html_url}"
        )


def _assert_apple_release_scope(
    workflow: WorkflowDefinitionObservation,
    default_branch: str,
) -> None:
    if "v*" not in workflow.push_tags:
        raise AssertionError(
            "Step 2 failed: the live Apple release workflow did not expose the expected "
            "semantic tag trigger.\n"
            f"Observed push tags: {workflow.push_tags}\n"
            f"Workflow URL: {workflow.html_url}\n"
            f"Raw workflow:\n{workflow.raw_file_text}"
        )
    if default_branch in workflow.push_branches:
        raise AssertionError(
            "Step 2 failed: the live Apple release workflow still listens to pushes on "
            f"`{default_branch}`.\n"
            f"Observed push branches: {workflow.push_branches}\n"
            f"Workflow URL: {workflow.html_url}\n"
            f"Raw workflow:\n{workflow.raw_file_text}"
        )
    if not workflow.workflow_dispatch_enabled:
        raise AssertionError(
            "Step 2 failed: the live Apple release workflow no longer exposes the "
            "workflow_dispatch fallback expected by maintainers.\n"
            f"Workflow URL: {workflow.html_url}"
        )
    if not workflow.semantic_tag_hint_present:
        raise AssertionError(
            "Step 2 failed: the live Apple release workflow file no longer shows the "
            "`v1.2.3` semantic tag example for users.\n"
            f"Workflow URL: {workflow.html_url}\n"
            f"Raw workflow:\n{workflow.raw_file_text}"
        )


def _assert_main_ci_scope(
    workflow: WorkflowDefinitionObservation,
    default_branch: str,
) -> None:
    if default_branch not in workflow.push_branches:
        raise AssertionError(
            "Step 3 failed: the general CI workflow no longer listens to pushes on the "
            f"default branch `{default_branch}`.\n"
            f"Observed push branches: {workflow.push_branches}\n"
            f"Workflow URL: {workflow.html_url}\n"
            f"Raw workflow:\n{workflow.raw_file_text}"
        )
    if workflow.push_tags:
        raise AssertionError(
            "Step 3 failed: the general CI workflow unexpectedly declared tag push "
            "filters, which would blur the isolation between release and non-release "
            "validation.\n"
            f"Observed push tags: {workflow.push_tags}\n"
            f"Workflow URL: {workflow.html_url}"
        )


def _assert_live_run_isolation(
    observation: GitHubWorkflowTriggerIsolationObservation,
) -> None:
    if len(observation.main_ci_push_main_current_sha) == 0:
        raise AssertionError(
            "Step 4 failed: the current default-branch head did not appear on any recent "
            "general CI push run.\n"
            f"Current head SHA: {observation.current_default_branch_sha}\n"
            f"General CI recent runs:\n{_run_summary_block(observation.main_ci.recent_runs)}"
        )
    if len(observation.apple_push_main_current_sha) != 0:
        raise AssertionError(
            "Step 4 failed: the current default-branch head still triggered the Apple "
            "release workflow on a normal main-branch push.\n"
            f"Current head SHA: {observation.current_default_branch_sha}\n"
            f"Apple matching runs:\n{_run_summary_block(observation.apple_push_main_current_sha)}"
        )
    if len(observation.apple_push_main_after_cutoff) != 0:
        raise AssertionError(
            "Step 4 failed: Apple Release Builds still recorded main-branch push runs "
            "after the workflow was updated to tag-only scope.\n"
            f"Cutoff timestamp: {observation.cutoff_timestamp}\n"
            f"Apple post-cutoff runs:\n{_run_summary_block(observation.apple_push_main_after_cutoff)}"
        )
    if len(observation.main_ci_push_main_after_cutoff) == 0:
        raise AssertionError(
            "Step 4 failed: no post-update main-branch CI runs were visible, so the "
            "live Actions history did not provide positive evidence that normal main "
            "pushes still flow through general CI.\n"
            f"Cutoff timestamp: {observation.cutoff_timestamp}\n"
            f"General CI recent runs:\n{_run_summary_block(observation.main_ci.recent_runs)}"
        )


def _assert_human_verification(
    workflow: WorkflowDefinitionObservation,
    default_branch: str,
) -> None:
    if workflow.ui_error is not None:
        raise AssertionError(
            "Human-style verification failed: the GitHub browser page could not be "
            f"opened for `{workflow.workflow_path}`.\n"
            f"Error: {workflow.ui_error}"
        )
    body_text = workflow.ui_body_text
    required_tokens = [workflow.workflow_name, "push"]
    if workflow.push_tags:
        required_tokens.extend(["tags", *workflow.push_tags])
    if workflow.push_branches:
        required_tokens.extend(["branches", default_branch])
    if workflow.semantic_tag_hint_present:
        required_tokens.append("v1.2.3")
    missing = [token for token in required_tokens if token not in body_text]
    if missing:
        raise AssertionError(
            "Human-style verification failed: the visible GitHub file page did not "
            "show the expected trigger text.\n"
            f"Workflow: {workflow.workflow_name}\n"
            f"Missing text: {missing}\n"
            f"URL: {workflow.ui_url}\n"
            f"Visible body text excerpt:\n{_snippet(body_text, limit=1200)}"
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
    RESPONSE_PATH.write_text(_response(result, passed=True), encoding="utf-8")


def _write_failure_outputs(result: dict[str, object]) -> None:
    BUG_DESCRIPTION_PATH.write_text(_bug_description(result), encoding="utf-8")
    RESULT_PATH.write_text(
        json.dumps(
            {
                "status": "failed",
                "passed": 0,
                "failed": 1,
                "skipped": 0,
                "summary": "0 passed, 1 failed",
                "error": str(result.get("error", "AssertionError: TS-709 failed")),
            }
        )
        + "\n",
        encoding="utf-8",
    )
    JIRA_COMMENT_PATH.write_text(_jira_comment(result, passed=False), encoding="utf-8")
    PR_BODY_PATH.write_text(_markdown_summary(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_response(result, passed=False), encoding="utf-8")


def _jira_comment(result: dict[str, object], *, passed: bool) -> str:
    status = "✅ PASSED" if passed else "❌ FAILED"
    lines = [
        "h3. Test Automation Result",
        "",
        f"*Status:* {status}",
        f"*Test Case:* {TICKET_KEY} - {TEST_CASE_TITLE}",
        "",
        "h4. What was tested",
        (
            "* Queried the live GitHub Actions workflow definitions for "
            "{{IstiN/trackstate}} and compared {{Apple Release Builds}} against the "
            "{{Flutter CI}} main-branch pipeline."
        ),
        (
            "* Verified the live Apple workflow file is tag-scoped with "
            "{{tags: [v*]}} and still shows the semantic example {{v1.2.3}}."
        ),
        (
            "* Verified the live general CI workflow still listens to pushes on "
            "{{main}}."
        ),
        (
            "* Checked recent live Actions runs for the current {{main}} head SHA to "
            "confirm standard pushes continue through general CI and do not trigger "
            "the Apple release workflow."
        ),
        "",
        "h4. Result",
        (
            "* Matched the expected result."
            if passed
            else f"* Did not match the expected result. {_failed_step_summary(result)}"
        ),
        (
            f"* Environment: repository {{{{{result.get('repository', '')}}}}}, branch "
            f"{{{{{result.get('default_branch', '')}}}}}, browser {{Chromium (Playwright)}}, "
            f"OS {{{{{result.get('os', '')}}}}}."
        ),
        "",
        "h4. Step results",
        *_step_lines(result, jira=True),
        "",
        "h4. Human-style verification",
        *_human_lines(result, jira=True),
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
    lines = [
        "## Test Automation Result",
        "",
        f"**Status:** {'✅ PASSED' if passed else '❌ FAILED'}",
        f"**Test Case:** {TICKET_KEY} - {TEST_CASE_TITLE}",
        "",
        "## What was automated",
        (
            "- Queried the live GitHub Actions workflow definitions for "
            "`IstiN/trackstate` and compared `Apple Release Builds` against the "
            "`Flutter CI` main-branch pipeline."
        ),
        (
            "- Verified the live Apple workflow file is tag-scoped with "
            "`tags: [v*]` and still shows the semantic example `v1.2.3`."
        ),
        "- Verified the live general CI workflow still listens to pushes on `main`.",
        (
            "- Checked recent live Actions runs for the current `main` head SHA to "
            "confirm standard pushes continue through general CI and do not trigger "
            "the Apple release workflow."
        ),
        "",
        "## Result",
        (
            "- Matched the expected result."
            if passed
            else f"- Did not match the expected result. {_failed_step_summary(result)}"
        ),
        (
            f"- Environment: repository `{result.get('repository', '')}`, branch "
            f"`{result.get('default_branch', '')}`, browser `Chromium (Playwright)`, "
            f"OS `{result.get('os', '')}`."
        ),
        "",
        "## Step results",
        *_step_lines(result, jira=False),
        "",
        "## Human-style verification",
        *_human_lines(result, jira=False),
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


def _response(result: dict[str, object], *, passed: bool) -> str:
    lines = [
        "## Test Automation Result",
        "",
        f"**Status:** {'✅ PASSED' if passed else '❌ FAILED'}",
        f"**Test Case:** {TICKET_KEY} - {TEST_CASE_TITLE}",
        "",
        "## Outcome",
        (
            "- The live workflow configuration and run history matched the expected "
            "trigger isolation."
            if passed
            else f"- The live workflow configuration or run history did not match the "
            f"expected trigger isolation. {_failed_step_summary(result)}"
        ),
        "",
        "## Step results",
        *_step_lines(result, jira=False),
        "",
        "## Human-style verification",
        *_human_lines(result, jira=False),
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
            f"# {TICKET_KEY} - Apple release workflow is not isolated from main pushes",
            "",
            "## Steps to reproduce",
            "1. Push a standard commit (no tag) to the `main` branch of `IstiN/trackstate`.",
            "2. Observe the Actions tab to see which workflows trigger.",
            "3. Push a semantic version tag `v1.2.3` to the `main` branch.",
            "4. Observe the Actions tab again.",
            "",
            "## Exact steps from the test case with observations",
            _annotated_step_line(result, 1, REQUEST_STEPS[0]),
            _annotated_step_line(result, 2, REQUEST_STEPS[1]),
            _annotated_step_line(result, 3, REQUEST_STEPS[2]),
            _annotated_step_line(result, 4, REQUEST_STEPS[3]),
            "",
            "## Actual vs Expected",
            f"- Expected: {EXPECTED_RESULT}",
            f"- Actual: {result.get('error', '<missing error>')}",
            "",
            "## Environment",
            f"- Repository: `{result.get('repository', '')}`",
            f"- Branch: `{result.get('default_branch', '')}`",
            f"- Current branch head SHA: `{result.get('current_default_branch_sha', '')}`",
            f"- Browser: `{result.get('browser', '')}`",
            f"- OS: `{result.get('os', '')}`",
            f"- Apple workflow page screenshot: `{_workflow_screenshot(result, 'apple_release')}`",
            f"- General CI workflow page screenshot: `{_workflow_screenshot(result, 'main_ci')}`",
            "",
            "## Live workflow observations",
            "```json",
            json.dumps(
                {
                    "apple_release": result.get("apple_release", {}),
                    "main_ci": result.get("main_ci", {}),
                    "apple_push_main_after_cutoff": result.get(
                        "apple_push_main_after_cutoff", []
                    ),
                    "main_ci_push_main_after_cutoff": result.get(
                        "main_ci_push_main_after_cutoff", []
                    ),
                    "apple_push_main_current_sha": result.get(
                        "apple_push_main_current_sha", []
                    ),
                    "main_ci_push_main_current_sha": result.get(
                        "main_ci_push_main_current_sha", []
                    ),
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


def _workflow_as_dict(workflow: WorkflowDefinitionObservation) -> dict[str, object]:
    return asdict(workflow)


def _workflow_screenshot(result: dict[str, object], key: str) -> str:
    workflow = result.get(key)
    if isinstance(workflow, dict):
        screenshot_path = workflow.get("ui_screenshot_path")
        if isinstance(screenshot_path, str):
            return screenshot_path
    return ""


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
    verifications = result.setdefault("human_verification", [])
    assert isinstance(verifications, list)
    verifications.append({"check": check, "observed": observed})


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
    verifications = result.get("human_verification")
    if not isinstance(verifications, list):
        return lines
    for entry in verifications:
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
        if entry.get("status") == "failed":
            return f"Step {entry.get('step')} failed: {entry.get('observed')}"
    return str(result.get("error", "Unknown failure"))


def _annotated_step_line(result: dict[str, object], step_number: int, action: str) -> str:
    steps = result.get("steps")
    if isinstance(steps, list):
        for entry in steps:
            if not isinstance(entry, dict):
                continue
            if entry.get("step") == step_number:
                marker = "✅" if entry.get("status") == "passed" else "❌"
                return f"{step_number}. {action}\n   - {marker} {entry.get('observed')}"
    return f"{step_number}. {action}\n   - ❌ Not reached."


def _record_failed_step_from_error(result: dict[str, object], message: str) -> None:
    match = re.search(r"Step (\d+) failed:(.*)", message, flags=re.DOTALL)
    if match is None:
        return
    step = int(match.group(1))
    if _step_exists(result, step):
        return
    observed = match.group(0).strip()
    action = REQUEST_STEPS[step - 1] if 1 <= step <= len(REQUEST_STEPS) else f"Step {step}"
    _record_step(result, step=step, status="failed", action=action, observed=observed)


def _step_exists(result: dict[str, object], step_number: int) -> bool:
    steps = result.get("steps")
    if not isinstance(steps, list):
        return False
    return any(
        isinstance(entry, dict) and entry.get("step") == step_number for entry in steps
    )


def _run_url_list(runs: list[WorkflowRunObservation]) -> str:
    if not runs:
        return "<none>"
    return ", ".join(run.html_url for run in runs if run.html_url)


def _run_summary_block(runs: list[WorkflowRunObservation]) -> str:
    if not runs:
        return "<none>"
    return "\n".join(
        (
            f"- {run.created_at or '<no time>'} | event={run.event} | "
            f"branch={run.head_branch or '<none>'} | sha={run.head_sha or '<none>'} | "
            f"conclusion={run.conclusion or '<none>'} | {run.html_url}"
        )
        for run in runs
    )


def _snippet(text: str, *, limit: int = 800) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3] + "..."


def _jira_inline(text: str) -> str:
    return re.sub(r"`([^`]+)`", r"{{\1}}", text)


if __name__ == "__main__":
    main()
