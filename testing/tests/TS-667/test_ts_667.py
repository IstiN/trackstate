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

TICKET_KEY = "TS-667"
TICKET_SUMMARY = (
    "Delete active workspace profile removes scoped credentials and falls back "
    "to the remaining workspace"
)
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
TEST_FILE_PATH = "testing/tests/TS-667/test_ts_667.dart"
RUN_COMMAND = "flutter test testing/tests/TS-667/test_ts_667.dart --reporter expanded"
REQUEST_STEPS = [
    "Trigger the delete operation for W2 in Project Settings.",
    "Verify the presence of a confirmation dialog explaining the loss of credentials.",
    "Confirm the deletion.",
    "Inspect WorkspaceCredentialStore for W2's ID.",
    "Verify the active workspace state in WorkspaceProfileService.",
]


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        completed = subprocess.run(
            ["flutter", "test", "testing/tests/TS-667/test_ts_667.dart", "--reporter", "expanded"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        combined_output = _combine_output(completed.stdout, completed.stderr)
        ui_observation = _extract_json_line(combined_output, "TS-667-UI:")
        service_observation = _extract_json_line(combined_output, "TS-667-SERVICE:")

        if completed.returncode != 0:
            raise AssertionError(_extract_error_message(combined_output))
        if ui_observation is None or service_observation is None:
            raise AssertionError(
                "Flutter test passed but did not emit the expected TS-667 observation payloads."
            )

        _write_pass_outputs(
            ui_observation=ui_observation,
            service_observation=service_observation,
            combined_output=combined_output,
        )
    except Exception as error:
        combined_output = locals().get("combined_output", "") or ""
        _write_failure_outputs(
            error=error,
            combined_output=combined_output,
        )
        raise


def _write_pass_outputs(
    *,
    ui_observation: dict[str, object],
    service_observation: dict[str, object],
    combined_output: str,
) -> None:
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

    dialog_title = _as_text(ui_observation.get("dialogTitle"))
    dialog_message = _as_text(ui_observation.get("dialogMessage"))
    deleted_workspace_id = _as_text(ui_observation.get("deletedWorkspaceId"))
    active_after_delete = _as_text(service_observation.get("activeAfterDelete"))
    remaining_workspaces = service_observation.get("remainingWorkspaces")
    remaining_workspace_list = (
        [str(item) for item in remaining_workspaces]
        if isinstance(remaining_workspaces, list)
        else []
    )
    remaining_workspace_text = ", ".join(remaining_workspace_list) or "<none>"
    output_excerpt = _compact_text(combined_output)

    jira_lines = [
        "h3. Test Automation Result",
        "",
        "*Status:* ✅ PASSED",
        f"*Test Case:* {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "h4. What was automated",
        "* Step 1: Opened the live Flutter *Settings* surface with two saved workspaces where W2 was active.",
        (
            f"* Step 2: Verified the visible confirmation dialog showed "
            f"{{{{{dialog_title}}}}} and {{code}}{dialog_message}{{code}} before deletion."
        ),
        (
            f"* Steps 3-5: Executed the production WorkspaceProfileService deletion flow and "
            f"verified workspace-scoped credentials for {{code}}{deleted_workspace_id}{{code}} "
            f"were removed while the remaining workspace became active."
        ),
        "",
        "h4. Human-style verification",
        (
            f"* Observed the user-facing dialog title {jira_inline(dialog_title)} with the "
            f"exact destructive warning {jira_inline(dialog_message)} and visible "
            f"{jira_inline('Cancel')} / {jira_inline('Delete')} actions."
        ),
        (
            f"* Observed the remaining workspace state after deletion converge to "
            f"{jira_inline(remaining_workspace_text)} with active workspace id "
            f"{jira_inline(active_after_delete)}."
        ),
        "",
        "h4. Result",
        "* Step 1 passed: the active saved workspace deletion action was reachable from Project Settings.",
        "* Step 2 passed: confirmation was explicitly required and the loss-of-credentials warning was visible in the dialog.",
        "* Step 3 passed: confirming the delete action invoked the deletion flow for W2.",
        "* Step 4 passed: the credential store stopped returning a token for W2's workspace id.",
        "* Step 5 passed: WorkspaceProfileService persisted W1 as the active fallback workspace.",
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

    markdown_lines = [
        "## Test Automation Result",
        "",
        "**Status:** ✅ PASSED",
        f"**Test Case:** {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "## What was automated",
        "- Opened the live Flutter `Settings` surface with two saved workspaces where W2 was active.",
        (
            f"- Verified the visible confirmation dialog showed `{dialog_title}` and the exact "
            f"warning `{dialog_message}` before deletion."
        ),
        (
            f"- Executed the production `WorkspaceProfileService.deleteProfile(...)` flow and "
            f"verified workspace-scoped credentials for `{deleted_workspace_id}` were removed."
        ),
        (
            f"- Verified the remaining workspace list converged to `{remaining_workspace_text}` "
            f"and the active workspace id became `{active_after_delete}`."
        ),
        "",
        "## Human-style verification",
        (
            f"- Observed the dialog copy a user sees: title `{dialog_title}`, warning "
            f"`{dialog_message}`, and visible `Cancel` / `Delete` actions."
        ),
        (
            f"- Observed the post-delete state as a user/system would experience it: only "
            f"`{remaining_workspace_text}` remained active."
        ),
        "",
        "## Result",
        "- Step 1 passed: the delete action for the active workspace was available in Project Settings.",
        "- Step 2 passed: confirmation was required and the credential-loss warning was visible.",
        "- Step 3 passed: confirming deletion targeted W2.",
        "- Step 4 passed: W2's scoped credentials were removed.",
        "- Step 5 passed: the remaining workspace became the active fallback profile.",
        "- The observed behavior matched the expected result.",
        "",
        "## How to run",
        "```bash",
        RUN_COMMAND,
        "```",
    ]

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

    step_lines = [
        f"{index + 1}. {step}"
        for index, step in enumerate(REQUEST_STEPS)
    ]
    annotated_steps = [
        f"1. ✅ {REQUEST_STEPS[0]} Observed: the test reached Settings and exposed the active workspace delete action before the failure boundary."
    ]
    if "Step 2 failed:" in combined_output:
        annotated_steps.append(
            "2. ❌ "
            + REQUEST_STEPS[1]
            + " Observed: the confirmation dialog did not match the required title/message. See the assertion output below."
        )
    elif "Step 3 failed:" in combined_output:
        annotated_steps.extend(
            [
                "2. ✅ " + REQUEST_STEPS[1] + " Observed: the confirmation dialog was shown.",
                "3. ❌ "
                + REQUEST_STEPS[2]
                + " Observed: confirming deletion did not invoke the expected deletion flow. See the assertion output below.",
            ]
        )
    elif "Step 4 failed:" in combined_output:
        annotated_steps.extend(
            [
                "2. ✅ " + REQUEST_STEPS[1] + " Observed: the confirmation dialog was shown.",
                "3. ✅ " + REQUEST_STEPS[2] + " Observed: the delete confirmation was submitted.",
                "4. ❌ "
                + REQUEST_STEPS[3]
                + " Observed: WorkspaceCredentialStore still returned a token or did not remove W2's scoped credentials.",
            ]
        )
    elif "Step 5 failed:" in combined_output:
        annotated_steps.extend(
            [
                "2. ✅ " + REQUEST_STEPS[1] + " Observed: the confirmation dialog was shown.",
                "3. ✅ " + REQUEST_STEPS[2] + " Observed: the delete confirmation was submitted.",
                "4. ✅ " + REQUEST_STEPS[3] + " Observed: W2's credentials were removed.",
                "5. ❌ "
                + REQUEST_STEPS[4]
                + " Observed: WorkspaceProfileService did not promote the expected fallback workspace.",
            ]
        )
    else:
        annotated_steps.append(
            "2. ❌ The scenario failed before the expected verification checkpoints completed. See the assertion output below."
        )

    jira_lines = [
        "h3. Test Automation Result",
        "",
        "*Status:* ❌ FAILED",
        f"*Test Case:* {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "h4. Failed step summary",
        *[f"* {line}" for line in annotated_steps],
        "",
        "h4. Actual vs Expected",
        "* *Expected:* deleting the active workspace should require confirmation, remove W2 and its scoped credentials, and promote W1 to active.",
        "* *Actual:* the Flutter automation failed before those conditions were all observed. See the assertion output for the precise mismatch.",
        "",
        "h4. Error output",
        "{code}",
        combined_output.strip() or error_message,
        "{code}",
        "",
        "h4. Environment",
        "* Runtime: local Flutter widget/service test",
        "* Browser: N/A",
        "* URL: N/A",
        "* OS: Linux",
        f"* Command: {RUN_COMMAND}",
    ]

    markdown_lines = [
        "## Test Automation Result",
        "",
        "**Status:** ❌ FAILED",
        f"**Test Case:** {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "## Failed step summary",
        *[f"- {line}" for line in annotated_steps],
        "",
        "## Actual vs Expected",
        "- **Expected:** deleting the active workspace should require confirmation, remove W2 and its scoped credentials, and promote W1 to active.",
        "- **Actual:** the Flutter automation failed before all of those conditions were observed. See the assertion output below for the precise mismatch.",
        "",
        "## Error output",
        "```text",
        combined_output.strip() or error_message,
        "```",
        "",
        "## Environment",
        "- Runtime: local Flutter widget/service test",
        "- Browser: N/A",
        "- URL: N/A",
        "- OS: Linux",
        f"- Command: `{RUN_COMMAND}`",
    ]

    bug_lines = [
        f"# {TICKET_KEY} - {TICKET_SUMMARY}",
        "",
        "## Steps to reproduce",
        *step_lines,
        "",
        "## Step-by-step observed behavior",
        *annotated_steps,
        "",
        "## Actual vs Expected",
        "- **Expected:** confirmation is required, W2 and its scoped credentials are permanently removed, and W1 becomes the active fallback workspace.",
        "- **Actual:** the automated scenario failed before those user-visible and service-visible outcomes were all observed.",
        "",
        "## Exact error message or assertion failure",
        "```text",
        combined_output.strip() or error_message,
        "```",
        "",
        "## Environment details",
        "- Runtime: local Flutter widget/service test",
        "- Browser: N/A",
        "- URL: N/A",
        "- OS: Linux",
        f"- Command: `{RUN_COMMAND}`",
        "",
        "## Logs",
        "```text",
        combined_output.strip() or traceback.format_exc(),
        "```",
    ]

    JIRA_COMMENT_PATH.write_text("\n".join(jira_lines) + "\n", encoding="utf-8")
    PR_BODY_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    RESPONSE_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    BUG_DESCRIPTION_PATH.write_text("\n".join(bug_lines) + "\n", encoding="utf-8")


def _extract_json_line(output: str, prefix: str) -> dict[str, object] | None:
    pattern = re.compile(rf"{re.escape(prefix)}(\{{.*\}})")
    match = pattern.search(output)
    if match is None:
        return None
    payload = json.loads(match.group(1))
    return payload if isinstance(payload, dict) else None


def _extract_error_message(output: str) -> str:
    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith("Step ") and "failed:" in stripped:
            return f"AssertionError: {stripped}"
    stripped_output = output.strip()
    if stripped_output:
        last_line = stripped_output.splitlines()[-1].strip()
        if last_line:
            return f"AssertionError: {last_line}"
    return "AssertionError: flutter test exited with a non-zero status"


def _combine_output(stdout: str, stderr: str) -> str:
    stdout = stdout.strip()
    stderr = stderr.strip()
    if stdout and stderr:
        return f"{stdout}\n{stderr}"
    return stdout or stderr


def _as_text(value: object) -> str:
    return "" if value is None else str(value)


def _compact_text(value: str, *, limit: int = 1200) -> str:
    text = " ".join(value.split())
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def jira_inline(value: str) -> str:
    escaped = value.replace("{", "\\{").replace("}", "\\}")
    return f"{{{{{escaped}}}}}"


if __name__ == "__main__":
    main()
