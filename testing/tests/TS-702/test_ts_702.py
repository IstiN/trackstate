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

TICKET_KEY = "TS-702"
TICKET_SUMMARY = (
    "Returning user entry point keeps Add workspace visible in the active shell"
)
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
TEST_FILE_PATH = "testing/tests/TS-702/test_ts_702.dart"
RUN_COMMAND = "flutter test testing/tests/TS-702/test_ts_702.dart --reporter expanded"
REQUEST_STEPS = [
    "Launch the application.",
    "Inspect the top app bar or the area adjacent to the workspace switcher.",
    "Click the 'Add workspace' action.",
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
        observation = _extract_json_line(combined_output, "TS-702-OBSERVATION:")

        if completed.returncode != 0:
            raise AssertionError(_extract_error_message(combined_output))
        if observation is None:
            raise AssertionError(
                "Flutter test passed but did not emit the expected TS-702 observation payload."
            )

        _write_pass_outputs(observation=observation, combined_output=combined_output)
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

    initial_visible_texts = _as_list(observation.get("initial_visible_texts"))
    initial_semantics = _as_list(observation.get("initial_interactive_semantics_labels"))
    post_click_visible_texts = _as_list(observation.get("post_click_visible_texts"))
    post_click_semantics = _as_list(
        observation.get("post_click_interactive_semantics_labels")
    )
    onboarding_choices = _as_list(observation.get("post_click_onboarding_choices"))
    opened_repositories = _as_list(observation.get("opened_repositories"))
    human_checks = observation.get("human_verification")
    human_verifications = human_checks if isinstance(human_checks, list) else []
    shell_layout = observation.get("shell_layout")
    shell_layout_text = json.dumps(shell_layout, sort_keys=True)
    output_excerpt = _compact_text(combined_output)

    jira_lines = [
        "h3. Test Automation Result",
        "",
        "*Status:* ✅ PASSED",
        f"*Test Case:* {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "h4. What was automated",
        (
            f"* Step 1: Launched the returning-user app shell and verified the saved active workspace "
            f"opened directly into the dashboard via {{code}}{_as_text(_single_or_none(opened_repositories))}{{code}}."
        ),
        (
            f"* Step 2: Verified a persistent {jira_inline('Add workspace')} action was visible in the "
            f"top shell controls beside the workspace switcher, using the rendered shell layout "
            f"{{code}}{shell_layout_text}{{code}}."
        ),
        (
            f"* Step 3: Clicked {jira_inline('Add workspace')} and verified the onboarding screen rendered "
            f"with the visible entry actions {{code}}{', '.join(onboarding_choices) or '<none>'}{{code}}."
        ),
        "",
        "h4. Human-style verification",
        (
            f"* Viewed the shell as a returning user would: visible texts {{code}}{', '.join(initial_visible_texts) or '<none>'}{{code}} "
            f"and interactive semantics {{code}}{', '.join(initial_semantics) or '<none>'}{{code}}."
        ),
        (
            f"* After clicking {jira_inline('Add workspace')}, observed the onboarding heading and visible actions "
            f"{{code}}{', '.join(post_click_visible_texts) or '<none>'}{{code}} in the rendered UI."
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
            "* Step 1 passed: the stored workspace opened and the returning-user shell rendered.",
            "* Step 2 passed: the persistent Add workspace control stayed visible beside the workspace switcher in the top shell controls.",
            "* Step 3 passed: clicking Add workspace opened onboarding without navigating to Settings.",
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
        (
            f"- Launched the returning-user shell and verified the stored active workspace opened directly "
            f"into the dashboard (`{_as_text(_single_or_none(opened_repositories))}`)."
        ),
        (
            f"- Verified the persistent `Add workspace` action stayed visible beside the workspace switcher "
            f"in the top shell controls (`{shell_layout_text}`)."
        ),
        (
            "- Clicked `Add workspace` and verified the onboarding screen rendered with "
            f"`Add workspace` and the visible onboarding entry actions `{', '.join(onboarding_choices) or '<none>'}`."
        ),
        "",
        "## Human-style verification",
        (
            f"- Observed the returning-user shell the way a user would see it after launch: "
            f"`{', '.join(initial_visible_texts) or '<none>'}`."
        ),
        (
            f"- Observed the onboarding content after clicking `Add workspace`: "
            f"`{', '.join(post_click_visible_texts) or '<none>'}`."
        ),
        (
            f"- Checked the interactive shell/onboarding controls exposed to users: "
            f"`{', '.join(initial_semantics + post_click_semantics) or '<none>'}`."
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
            "- Step 1 passed: the active workspace opened in the returning-user shell.",
            "- Step 2 passed: the Add workspace action stayed visible near the workspace switcher in the primary shell controls.",
            "- Step 3 passed: clicking Add workspace opened onboarding.",
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

    if "Step 1 failed:" in combined_output:
        annotated_steps = [
            f"1. ❌ {REQUEST_STEPS[0]} Observed: the returning-user shell did not open with both the active workspace and the Add workspace entry point visible.",
            f"2. ⏭️ {REQUEST_STEPS[1]} Not reached because step 1 failed.",
            f"3. ⏭️ {REQUEST_STEPS[2]} Not reached because step 1 failed.",
        ]
    elif "Step 2 failed:" in combined_output:
        annotated_steps = [
            f"1. ✅ {REQUEST_STEPS[0]} Observed: the active workspace shell launched.",
            f"2. ❌ {REQUEST_STEPS[1]} Observed: Add workspace was not rendered beside the workspace switcher in the primary shell controls.",
            f"3. ⏭️ {REQUEST_STEPS[2]} Not reached because step 2 failed.",
        ]
    elif "Step 3 failed:" in combined_output:
        annotated_steps = [
            f"1. ✅ {REQUEST_STEPS[0]} Observed: the active workspace shell launched.",
            f"2. ✅ {REQUEST_STEPS[1]} Observed: Add workspace appeared near the workspace switcher.",
            f"3. ❌ {REQUEST_STEPS[2]} Observed: clicking Add workspace did not route to the onboarding screen.",
        ]
    else:
        annotated_steps = [
            f"1. ❌ {REQUEST_STEPS[0]} Observed: the failure occurred before a step-specific assertion boundary.",
            f"2. ⏭️ {REQUEST_STEPS[1]} Not reached.",
            f"3. ⏭️ {REQUEST_STEPS[2]} Not reached.",
        ]

    failure_excerpt = combined_output.strip() or error_message
    expected_text = (
        "a returning user with an active saved workspace should see a persistent Add workspace action "
        "near the workspace switcher in the app shell, and clicking it should open onboarding without "
        "going through Settings"
    )

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
        f"* Expected: {expected_text}.",
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
    ]
    markdown_lines.extend(f"- {line}" for line in annotated_steps)
    markdown_lines.extend(
        [
            "",
            "## Actual vs Expected",
            f"- Expected: {expected_text}.",
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
        "## Summary",
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
        (
            "- Expected: a returning user with an active saved workspace should see a persistent "
            "Add workspace action near the workspace switcher in the app shell, and clicking it "
            "should open onboarding without visiting Settings."
        ),
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
    precondition_match = re.search(
        r"(Precondition failed:.*?)(?:\n\s*\n|\n══╡|\Z)", output, re.S
    )
    if precondition_match:
        return _compact_text(precondition_match.group(1))
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


def _single_or_none(values: list[str]) -> str | None:
    if len(values) != 1:
        return None
    return values[0]


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
