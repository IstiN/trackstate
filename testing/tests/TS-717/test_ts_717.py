from __future__ import annotations

import json
import re
import subprocess
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

TICKET_KEY = "TS-717"
TICKET_SUMMARY = (
    "Local folder inspection recognizes a usable TrackState repository as ready"
)
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
TEST_FILE_PATH = "testing/tests/TS-717/test_ts_717.dart"
RUN_COMMAND = "flutter test testing/tests/TS-717/test_ts_717.dart --reporter expanded"
REQUEST_STEPS = [
    'Launch the app and select "Open existing folder" on the Onboarding screen.',
    "Use the DirectoryPickerAdapter to select the prepared directory.",
    "Observe the LocalWorkspaceInspectionService output and UI state.",
    "Verify that interactive elements have non-empty Semantics labels (AC6).",
]


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        completed = subprocess.run(
            ["flutter", "test", TEST_FILE_PATH, "--reporter", "expanded"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        combined_output = _combine_output(completed.stdout, completed.stderr)
        observation = _extract_json_line(combined_output, "TS-717-OBSERVATION:")

        if completed.returncode != 0:
            raise AssertionError(_extract_error_message(combined_output))
        if observation is None:
            raise AssertionError(
                "Flutter test passed but did not emit the expected TS-717 observation payload."
            )

        _write_pass_outputs(
            observation=observation,
            combined_output=combined_output,
        )
    except Exception as error:
        combined_output = locals().get("combined_output", "") or ""
        _write_failure_outputs(error=error, combined_output=combined_output)
        raise


def _write_pass_outputs(*, observation: dict[str, object], combined_output: str) -> None:
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

    inspection = observation.get("inspection")
    inspection_payload = inspection if isinstance(inspection, dict) else {}
    picker_payload = observation.get("picker_invocation")
    picker_invocation = picker_payload if isinstance(picker_payload, dict) else {}
    visible_texts = _as_list(observation.get("visible_texts"))
    semantics_labels = _as_list(observation.get("interactive_semantics_labels"))
    opened_repositories = _as_list(observation.get("opened_repositories"))
    human_checks = observation.get("human_verification")
    human_verifications = human_checks if isinstance(human_checks, list) else []
    visible_texts_text = ", ".join(visible_texts) or "<none>"
    semantics_text = ", ".join(semantics_labels) or "<none>"
    opened_repositories_text = ", ".join(opened_repositories) or "<none>"
    output_excerpt = _compact_text(combined_output)

    inspection_state = _as_text(inspection_payload.get("state"))
    inspection_message = _as_text(inspection_payload.get("message"))
    selected_folder = _as_text(inspection_payload.get("folderPath"))
    workspace_name = _as_text(observation.get("workspace_name_value"))
    write_branch = _as_text(observation.get("write_branch_value"))
    submit_label = _as_text(observation.get("submit_label"))
    picker_confirm = _as_text(picker_invocation.get("confirmButtonText"))
    dashboard_visible = observation.get("dashboard_visible") is True
    before_head = _as_text(observation.get("before_head_revision"))
    after_head = _as_text(observation.get("after_head_revision"))

    jira_lines = [
        "h3. Test Automation Result",
        "",
        "*Status:* ✅ PASSED",
        f"*Test Case:* {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "h4. What was automated",
        (
            f"* Step 1: Launched the onboarding flow and activated "
            f"{{{{Open existing folder}}}} from the visible {{Add workspace}} screen."
        ),
        (
            f"* Step 2: Verified the DirectoryPickerAdapter callback ran with "
            f"{{code}}confirmButtonText={picker_confirm}{{code}} and returned the prepared local repository "
            f"{{code}}{selected_folder}{{code}}."
        ),
        (
            f"* Step 3: Verified {{code}}LocalWorkspaceInspectionService.inspectFolder(...){{code}} "
            f"reported {{code}}{inspection_state}{{code}}, rendered the visible ready state, prefilled "
            f"workspace name {{code}}{workspace_name}{{code}}, prefilled write branch {{code}}{write_branch}{{code}}, "
            f"enabled the {{code}}{submit_label}{{code}} action, opened the workspace, and left the repository unchanged on disk."
        ),
        (
            f"* Step 4: Verified interactive controls exposed non-empty semantics labels, including "
            f"{jira_inline('Open existing folder')}, {jira_inline('Change folder')}, "
            f"{jira_inline('Workspace name')}, {jira_inline('Write branch')}, and {jira_inline('Open workspace')}."
        ),
        "",
        "h4. Human-style verification",
        (
            f"* Observed the user-facing copy after folder selection: status {jira_inline('Ready to open')}, "
            f"message {jira_inline(inspection_message)}, selected folder {jira_inline(selected_folder)}, "
            f"heading {jira_inline('Workspace details')}, and enabled action {jira_inline(submit_label)}."
        ),
        (
            f"* Pressed {jira_inline(submit_label)} and observed the visible workspace shell continue to "
            f"{jira_inline('Dashboard')} while the repository stayed unchanged "
            f"(HEAD {jira_inline(before_head)} -> {jira_inline(after_head)}, opened repository call "
            f"{jira_inline(opened_repositories_text)})."
        ),
    ]

    for check in human_verifications:
        if not isinstance(check, dict):
            continue
        jira_lines.append(
            f"* {jira_inline(_as_text(check.get('check')))} — observed {jira_inline(_as_text(check.get('observed')))}"
        )

    jira_lines.extend(
        [
            "",
            "h4. Result",
            "* Step 1 passed: the onboarding screen exposed the expected open-existing entry point.",
            "* Step 2 passed: the directory picker callback was used for the prepared local repository.",
            "* Step 3 passed: the prepared repository was recognized as ready, the Workspace details surface showed the expected values, the Open action was enabled, and opening the workspace did not modify the selected folder on disk.",
            "* Step 4 passed: interactive elements kept non-empty semantics labels.",
            f"* Observed visible texts: {{code}}{visible_texts_text}{{code}}",
            f"* Observed interactive semantics labels: {{code}}{semantics_text}{{code}}",
            f"* Dashboard visible after opening: {{code}}{str(dashboard_visible).lower()}{{code}}",
            "* The observed behavior matched the expected result.",
            "",
            "h4. Run command",
            "{code:bash}",
            RUN_COMMAND,
            "{code}",
            "",
            "h4. Observed output excerpt",
            "{code}",
            output_excerpt,
            "{code}",
        ]
    )

    markdown_lines = [
        "## Test Automation Result",
        "",
        "**Status:** ✅ PASSED",
        f"**Test Case:** {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "## What was automated",
        '- Launched the onboarding flow and selected `Open existing folder` from the visible `Add workspace` screen.',
        (
            f"- Verified the DirectoryPickerAdapter callback ran with "
            f"`confirmButtonText={picker_confirm}` and returned the prepared repository `{selected_folder}`."
        ),
        (
            f"- Verified `LocalWorkspaceInspectionService.inspectFolder(...)` reported `{inspection_state}`, "
            f"rendered the ready state, prefilled workspace name `{workspace_name}`, prefilled write branch "
            f"`{write_branch}`, and enabled the `{submit_label}` action."
        ),
        (
            f"- Pressed `{submit_label}`, verified the dashboard became visible, and confirmed the selected "
            f"repository stayed unchanged on disk (`HEAD {before_head} -> {after_head}`, loader call `{opened_repositories_text}`)."
        ),
        (
            f"- Verified interactive controls exposed non-empty semantics labels: `{semantics_text}`."
        ),
        "",
        "## Human-style verification",
        (
            f"- Observed the user-facing ready state copy in place: `Ready to open`, "
            f"`{inspection_message}`, selected folder `{selected_folder}`, heading `Workspace details`, "
            f"and enabled action `{submit_label}`."
        ),
        (
            f"- Observed the post-open experience a user would see: the app continued to `Dashboard` without changing the selected folder's files."
        ),
    ]

    for check in human_verifications:
        if not isinstance(check, dict):
            continue
        markdown_lines.append(
            f"- `{_as_text(check.get('check'))}` — observed `{_as_text(check.get('observed'))}`"
        )

    markdown_lines.extend(
        [
            "",
            "## Result",
            "- Step 1 passed: the onboarding screen exposed the expected open-existing action.",
            "- Step 2 passed: the directory picker callback was used for the prepared repository.",
            "- Step 3 passed: the repository was recognized as ready, Workspace details rendered the expected values, the Open action was enabled, and opening the workspace did not modify the selected folder.",
            "- Step 4 passed: interactive elements kept non-empty semantics labels.",
            "- The observed behavior matched the expected result.",
            "",
            "## How to run",
            "```bash",
            RUN_COMMAND,
            "```",
        ]
    )

    JIRA_COMMENT_PATH.write_text("\n".join(jira_lines) + "\n", encoding="utf-8")
    PR_BODY_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    RESPONSE_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")


def _write_failure_outputs(*, error: Exception, combined_output: str) -> None:
    error_message = f"{type(error).__name__}: {error}"
    RESULT_PATH.write_text(
        json.dumps(
            {
                "status": "failed",
                "passed": 0,
                "failed": 1,
                "skipped": 0,
                "summary": "0 passed, 1 failed",
                "error": error_message,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    annotated_steps = []
    if "Step 1 failed:" in combined_output:
        annotated_steps.extend(
            [
                f"1. ❌ {REQUEST_STEPS[0]} Observed: the onboarding screen did not expose the expected open-existing entry point or did not invoke it successfully. See the assertion output below.",
                f"2. ⏭️ {REQUEST_STEPS[1]} Not reached because step 1 failed.",
                f"3. ⏭️ {REQUEST_STEPS[2]} Not reached because step 1 failed.",
                f"4. ⏭️ {REQUEST_STEPS[3]} Not reached because step 1 failed.",
            ]
        )
    elif "Step 2 failed:" in combined_output:
        annotated_steps.extend(
            [
                f"1. ✅ {REQUEST_STEPS[0]} Observed: the onboarding screen launched and the open-existing action was activated.",
                f"2. ❌ {REQUEST_STEPS[1]} Observed: the DirectoryPickerAdapter callback parameters or invocation count did not match the expected open-existing flow. See the assertion output below.",
                f"3. ⏭️ {REQUEST_STEPS[2]} Not reached because step 2 failed.",
                f"4. ⏭️ {REQUEST_STEPS[3]} Not reached because step 2 failed.",
            ]
        )
    elif "Step 3 failed:" in combined_output:
        annotated_steps.extend(
            [
                f"1. ✅ {REQUEST_STEPS[0]} Observed: the onboarding screen launched and the open-existing action was activated.",
                f"2. ✅ {REQUEST_STEPS[1]} Observed: the directory picker callback ran for the prepared local repository.",
                f"3. ❌ {REQUEST_STEPS[2]} Observed: the prepared repository was not recognized or rendered as the expected ready-to-open workspace state, or opening it changed disk state unexpectedly. See the assertion output below.",
                f"4. ⏭️ {REQUEST_STEPS[3]} Not reached because step 3 failed.",
            ]
        )
    elif "Step 4 failed:" in combined_output:
        annotated_steps.extend(
            [
                f"1. ✅ {REQUEST_STEPS[0]} Observed: the onboarding screen launched and the open-existing action was activated.",
                f"2. ✅ {REQUEST_STEPS[1]} Observed: the directory picker callback ran for the prepared local repository.",
                f"3. ✅ {REQUEST_STEPS[2]} Observed: the repository reached the ready UI state.",
                f"4. ❌ {REQUEST_STEPS[3]} Observed: one or more interactive elements did not keep a non-empty semantics label. See the assertion output below.",
            ]
        )
    else:
        annotated_steps.extend(
            [
                f"1. ❌ {REQUEST_STEPS[0]} Observed: the failure occurred before the test reached a step-specific assertion boundary.",
                f"2. ⏭️ {REQUEST_STEPS[1]} Not reached.",
                f"3. ⏭️ {REQUEST_STEPS[2]} Not reached.",
                f"4. ⏭️ {REQUEST_STEPS[3]} Not reached.",
            ]
        )

    failure_excerpt = combined_output.strip() or error_message
    jira_lines = [
        "h3. Test Automation Result",
        "",
        "*Status:* ❌ FAILED",
        f"*Test Case:* {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "h4. Failure summary",
        f"* Exact error: {{code}}{error_message}{{code}}",
        "",
        "h4. Step-by-step reproduction with observations",
        *[f"* {line}" for line in annotated_steps],
        "",
        "h4. Actual vs Expected",
        "* Expected: selecting a prepared committed local TrackState repository should classify it as ready, render the Workspace details step with the Open action enabled, keep interactive semantics labels non-empty, and leave the repository unchanged on disk.",
        f"* Actual: {{code}}{_compact_text(failure_excerpt)}{{code}}",
        "",
        "h4. Environment",
        "* URL: N/A (local flutter widget test)",
        "* Browser: N/A",
        "* OS: Linux",
        f"* Run command: {{code}}{RUN_COMMAND}{{code}}",
        "",
        "h4. Exact assertion output / stack trace",
        "{code}",
        failure_excerpt,
        "{code}",
    ]

    markdown_lines = [
        "## Test Automation Result",
        "",
        "**Status:** ❌ FAILED",
        f"**Test Case:** {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "## Failure summary",
        f"**Exact error:** `{error_message}`",
        "",
        "## Step-by-step reproduction with observations",
        *[f"1. {line[3:]}" if line.startswith('1.') else line for line in []],
    ]
    markdown_lines.extend(f"- {line}" for line in annotated_steps)
    markdown_lines.extend(
        [
            "",
            "## Actual vs Expected",
            "- Expected: selecting a prepared committed local TrackState repository should classify it as ready, render the Workspace details step with the Open action enabled, keep interactive semantics labels non-empty, and leave the repository unchanged on disk.",
            f"- Actual: `{_compact_text(failure_excerpt)}`",
            "",
            "## Environment",
            "- URL: N/A (local flutter widget test)",
            "- Browser: N/A",
            "- OS: Linux",
            f"- Run command: `{RUN_COMMAND}`",
            "",
            "## Exact assertion output / stack trace",
            "```text",
            failure_excerpt,
            "```",
        ]
    )

    bug_lines = [
        f"# {TICKET_KEY} automated test failure",
        "",
        f"## Summary",
        f"The automated reproduction for **{TICKET_SUMMARY}** failed.",
        "",
        "## Exact steps to reproduce",
        *annotated_steps,
        "",
        "## Exact error message or assertion failure",
        "```text",
        failure_excerpt,
        "```",
        "",
        "## Actual vs Expected",
        "- Expected: choosing the prepared committed local TrackState repository should classify it as ready, render the Workspace details state with an enabled Open action, keep interactive semantics labels non-empty, and avoid modifying files on disk.",
        f"- Actual: {_compact_text(failure_excerpt)}",
        "",
        "## Environment details",
        "- URL: N/A (local flutter widget test)",
        "- Browser: N/A",
        "- OS: Linux",
        f"- Run command: `{RUN_COMMAND}`",
        f"- Test file: `{TEST_FILE_PATH}`",
        "",
        "## Screenshots or logs",
        "- Screenshot: not applicable for this flutter widget test run.",
        "```text",
        failure_excerpt,
        "```",
    ]

    JIRA_COMMENT_PATH.write_text("\n".join(jira_lines) + "\n", encoding="utf-8")
    PR_BODY_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    RESPONSE_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    BUG_DESCRIPTION_PATH.write_text("\n".join(bug_lines) + "\n", encoding="utf-8")


def _extract_json_line(output: str, prefix: str) -> dict[str, object] | None:
    match = re.search(rf"{re.escape(prefix)}(\{{.*\}})", output)
    if not match:
        return None
    return json.loads(match.group(1))


def _extract_error_message(output: str) -> str:
    step_match = re.search(r"(Step \d+ failed:.*?)(?:\n\s*\n|\n══╡|\Z)", output, re.S)
    if step_match:
        return _compact_text(step_match.group(1))
    human_match = re.search(
        r"(Human-style verification failed:.*?)(?:\n\s*\n|\n══╡|\Z)", output, re.S
    )
    if human_match:
        return _compact_text(human_match.group(1))
    return "AssertionError: flutter test exited with a non-zero status"


def _combine_output(stdout: str, stderr: str) -> str:
    stdout = stdout.strip()
    stderr = stderr.strip()
    if stdout and stderr:
        return f"{stdout}\n{stderr}"
    return stdout or stderr


def _as_text(value: object | None) -> str:
    if value is None:
        return "<none>"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _as_list(value: object | None) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _compact_text(text: str) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= 1800:
        return compact
    return compact[:1800] + "…"


def jira_inline(text: str) -> str:
    escaped = text.replace("{", r"\{").replace("}", r"\}")
    return f"{{{{{escaped}}}}}"


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        raise
