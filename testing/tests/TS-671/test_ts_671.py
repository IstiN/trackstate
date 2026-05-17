from __future__ import annotations

import json
import platform
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.services.trackstate_cli_ticket_show_help_validator import (  # noqa: E402
    TrackStateCliTicketShowHelpValidator,
)
from testing.core.config.trackstate_cli_ticket_show_help_config import (  # noqa: E402
    TrackStateCliTicketShowHelpConfig,
)
from testing.core.models.trackstate_cli_ticket_show_help_result import (  # noqa: E402
    TrackStateCliTicketShowHelpValidationResult,
)
from testing.tests.support.trackstate_cli_ticket_show_help_probe_factory import (  # noqa: E402
    create_trackstate_cli_ticket_show_help_probe,
)

TICKET_KEY = "TS-671"
TICKET_SUMMARY = "CLI ticket sub-command help exposes the show action"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
RUN_COMMAND = "python testing/tests/TS-671/test_ts_671.py"
REQUEST_STEPS = (
    "Execute command: `trackstate ticket --help`.",
    "Verify the output contains the `show` action in the available actions list.",
)


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = TrackStateCliTicketShowHelpConfig.from_defaults()
    validator = TrackStateCliTicketShowHelpValidator(
        probe=create_trackstate_cli_ticket_show_help_probe(REPO_ROOT)
    )
    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "ticket_summary": TICKET_SUMMARY,
        "requested_command": " ".join(config.requested_command),
        "steps": [],
        "human_verification": [],
    }

    try:
        validation = validator.validate(config=config)
        result.update(_validation_payload(validation))
        _assert_runtime_expectations(config, validation, result)
        _write_pass_outputs(result)
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        if "validation" in locals():
            result.update(_validation_payload(validation))
        _write_failure_outputs(config, result)
        raise


def _assert_runtime_expectations(
    config: TrackStateCliTicketShowHelpConfig,
    validation: TrackStateCliTicketShowHelpValidationResult,
    result: dict[str, object],
) -> None:
    observation = validation.observation
    if observation.requested_command != config.requested_command:
        raise AssertionError(
            "Precondition failed: TS-671 did not preserve the exact CLI command from "
            "the ticket.\n"
            f"Expected command: {' '.join(config.requested_command)}\n"
            f"Observed command: {observation.requested_command_text}"
        )
    if observation.compiled_binary_path is None:
        raise AssertionError(
            "Precondition failed: TS-671 must execute a repository-local compiled CLI "
            "binary so the help surface is validated through the compiled entry point.\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Fallback reason: {observation.fallback_reason}"
        )
    if observation.executed_command[0] != observation.compiled_binary_path:
        raise AssertionError(
            "Precondition failed: TS-671 did not execute the compiled repository-local "
            "CLI binary.\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Compiled binary path: {observation.compiled_binary_path}"
        )
    if observation.result.exit_code != 0:
        raise AssertionError(
            "Step 1 failed: executing `trackstate ticket --help` did not complete "
            "successfully.\n"
            f"Repository path: {observation.repository_path}\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Observed exit code: {observation.result.exit_code}\n"
            f"stdout:\n{observation.result.stdout}\n"
            f"stderr:\n{observation.result.stderr}"
        )

    help_output = observation.output
    actions_section = _extract_actions_section(help_output)
    show_action_line = _find_action_line(actions_section, config.required_action_name)
    result["actions_section"] = actions_section
    result["show_action_line"] = show_action_line

    if config.required_actions_header not in help_output:
        raise AssertionError(
            "Step 2 failed: the help output did not render an `Actions:` section for "
            "`trackstate ticket --help`.\n"
            f"Observed output:\n{help_output}"
        )
    if show_action_line is None:
        raise AssertionError(
            "Step 2 failed: the `Actions:` list did not contain a visible `show` "
            "entry.\n"
            f"Observed actions section:\n{actions_section or help_output}"
        )
    if config.required_action_description not in show_action_line:
        raise AssertionError(
            "Expected result failed: the `show` action was listed but its visible help "
            "description did not match the deployed ticket-detail command.\n"
            f"Expected description: {config.required_action_description}\n"
            f"Observed action line: {show_action_line}"
        )
    for forbidden_fragment in config.forbidden_fragments:
        if forbidden_fragment in help_output:
            raise AssertionError(
                "Expected result failed: the help surface still exposed the legacy "
                "unknown-action failure for `show`.\n"
                f"Unexpected fragment: {forbidden_fragment}\n"
                f"Observed output:\n{help_output}"
            )
    if config.required_example not in help_output:
        raise AssertionError(
            "Human-style verification failed: the terminal help output did not visibly "
            "show the `trackstate ticket show` example a user can follow.\n"
            f"Missing example: {config.required_example}\n"
            f"Observed output:\n{help_output}"
        )

    _record_step(
        result,
        step=1,
        status="passed",
        action="Execute `trackstate ticket --help` through the compiled CLI entry point.",
        observed=(
            f"Exit code {observation.result.exit_code}; compiled binary "
            f"{observation.compiled_binary_path}."
        ),
    )
    _record_step(
        result,
        step=2,
        status="passed",
        action="Verify the available actions list contains the `show` action.",
        observed=show_action_line,
    )
    _record_human_verification(
        result,
        check=(
            "Verified the user-visible terminal help text showed the `show` command "
            "with its ticket-detail description inside the Actions list."
        ),
        observed=show_action_line,
    )
    _record_human_verification(
        result,
        check=(
            "Verified the same help output visibly included a runnable "
            "`trackstate ticket show` example for a local target."
        ),
        observed=config.required_example,
    )


def _validation_payload(
    validation: TrackStateCliTicketShowHelpValidationResult,
) -> dict[str, object]:
    observation = validation.observation
    return {
        "working_directory": observation.repository_path,
        "executed_command": observation.executed_command_text,
        "compiled_binary_path": observation.compiled_binary_path,
        "fallback_reason": observation.fallback_reason,
        "stdout": observation.result.stdout,
        "stderr": observation.result.stderr,
        "exit_code": observation.result.exit_code,
    }


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


def _extract_actions_section(help_output: str) -> str:
    lines = help_output.splitlines()
    capture = False
    section_lines: list[str] = []
    for line in lines:
        if line.strip() == "Actions:":
            capture = True
            section_lines.append(line)
            continue
        if capture and line.strip() == "Examples:":
            break
        if capture:
            section_lines.append(line)
    return "\n".join(section_lines).strip()


def _find_action_line(actions_section: str, action_name: str) -> str | None:
    for line in actions_section.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(f"{action_name} "):
            return stripped
    return None


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

    summary = (
        "TS-671 passed: the compiled `trackstate ticket --help` output lists the "
        "`show` action with the deployed ticket-detail description."
    )
    show_action_line = str(result.get("show_action_line", "")).strip()
    stdout = str(result.get("stdout", "")).rstrip()

    jira_lines = [
        f"h3. {TICKET_KEY} PASSED",
        "",
        f"*Test Case:* {TICKET_KEY} — {TICKET_SUMMARY}",
        f"*Command:* {{code}}{result.get('requested_command')}{{code}}",
        f"*Executed command:* {{code}}{result.get('executed_command')}{{code}}",
        f"*Compiled binary:* {{code}}{result.get('compiled_binary_path')}{{code}}",
        "",
        "h4. What was automated",
        "# Executed the compiled CLI help command for {{trackstate ticket}} from the repository root.",
        "# Verified the {{Actions:}} section contained a visible {{show}} entry.",
        "# Verified the visible help output also included the {{trackstate ticket show --target local --key TRACK-1}} example.",
        "",
        "h4. Human-style verification",
        f"# Observed the exact terminal action line {{code}}{show_action_line}{{code}} in the Actions list.",
        "# Observed the terminal help text show a runnable {{trackstate ticket show}} example instead of any unknown-action error.",
        "",
        "h4. Result",
        "* Step 1 passed: {{trackstate ticket --help}} completed successfully through the compiled CLI entry point.",
        "* Step 2 passed: the available actions list visibly included {{show}} with the expected description.",
        "* The observed behavior matched the expected result.",
        "",
        "h4. Run command",
        "{code:bash}",
        RUN_COMMAND,
        "{code}",
        "",
        "h4. Observed stdout",
        "{code}",
        stdout,
        "{code}",
    ]

    markdown_lines = [
        f"## {summary}",
        "",
        f"- **Test Case:** {TICKET_KEY} — {TICKET_SUMMARY}",
        f"- **Command:** `{result.get('requested_command')}`",
        f"- **Executed command:** `{result.get('executed_command')}`",
        f"- **Compiled binary:** `{result.get('compiled_binary_path')}`",
        "",
        "### What was automated",
        "- Executed the compiled CLI help command for `trackstate ticket` from the repository root.",
        "- Verified the `Actions:` section contained a visible `show` entry.",
        "- Verified the visible help text also included the example `trackstate ticket show --target local --key TRACK-1`.",
        "",
        "### Human-style verification",
        f"- Observed the exact terminal action line `{show_action_line}` in the Actions list.",
        "- Observed the terminal help text show a runnable `trackstate ticket show` example instead of any unknown-action error.",
        "",
        "### Result",
        "- Step 1 passed: `trackstate ticket --help` completed successfully through the compiled CLI entry point.",
        "- Step 2 passed: the available actions list visibly included `show` with the expected description.",
        "- The observed behavior matched the expected result.",
        "",
        "### How to run",
        "```bash",
        RUN_COMMAND,
        "```",
        "",
        "### Observed stdout",
        "```text",
        stdout,
        "```",
    ]

    JIRA_COMMENT_PATH.write_text("\n".join(jira_lines) + "\n", encoding="utf-8")
    PR_BODY_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    RESPONSE_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")


def _write_failure_outputs(
    config: TrackStateCliTicketShowHelpConfig,
    result: dict[str, object],
) -> None:
    error_text = str(result.get("error", "AssertionError: unknown failure"))
    traceback_text = str(result.get("traceback", "")).strip()
    stdout = str(result.get("stdout", "")).rstrip()
    stderr = str(result.get("stderr", "")).rstrip()
    actions_section = str(result.get("actions_section", "")).rstrip()
    show_action_line = str(result.get("show_action_line", "")).strip()
    actual_vs_expected = (
        "Expected `trackstate ticket --help` to complete successfully and visibly list "
        f"`show` inside the `Actions:` section with the description "
        f"`{config.required_action_description}`. "
        f"Actual output contained action line `{show_action_line or '<missing>'}` and "
        f"exit code `{result.get('exit_code')}`."
    )

    annotated_steps = _annotated_steps(result)
    failure_block = "\n\n".join(
        fragment
        for fragment in (
            traceback_text,
            f"stdout:\n{stdout}" if stdout else "",
            f"stderr:\n{stderr}" if stderr else "",
        )
        if fragment
    ).strip()

    jira_lines = [
        f"h3. {TICKET_KEY} FAILED",
        "",
        f"*Test Case:* {TICKET_KEY} — {TICKET_SUMMARY}",
        f"*Command:* {{code}}{result.get('requested_command')}{{code}}",
        f"*Executed command:* {{code}}{result.get('executed_command')}{{code}}",
        f"*Compiled binary:* {{code}}{result.get('compiled_binary_path')}{{code}}",
        "",
        "h4. Failed step summary",
        *[f"* {line}" for line in annotated_steps],
        "",
        "h4. Actual vs Expected",
        f"* *Expected:* {{trackstate ticket --help}} should show {{show}} in the available actions list with description {{code}}{config.required_action_description}{{code}}.",
        f"* *Actual:* {actual_vs_expected}",
        "",
        "h4. Human-style verification",
        f"* Observed action line in terminal: {{code}}{show_action_line or '<missing>'}{{code}}",
        f"* Observed actions section: {{code}}{actions_section or '<missing>'}{{code}}",
        "",
        "h4. Error output",
        "{code}",
        failure_block or error_text,
        "{code}",
        "",
        "h4. Environment",
        "* Runtime: repository-local compiled CLI help probe",
        "* Browser: N/A",
        "* URL: N/A",
        f"* OS: {platform.platform()}",
        f"* Working directory: {result.get('working_directory')}",
        f"* Run command: {RUN_COMMAND}",
    ]

    markdown_lines = [
        f"## {TICKET_KEY} failed",
        "",
        f"- **Test Case:** {TICKET_KEY} — {TICKET_SUMMARY}",
        f"- **Command:** `{result.get('requested_command')}`",
        f"- **Executed command:** `{result.get('executed_command')}`",
        f"- **Compiled binary:** `{result.get('compiled_binary_path')}`",
        "",
        "### Failed step summary",
        *[f"- {line}" for line in annotated_steps],
        "",
        "### Actual vs Expected",
        f"- **Expected:** `trackstate ticket --help` should show `show` in the available actions list with description `{config.required_action_description}`.",
        f"- **Actual:** {actual_vs_expected}",
        "",
        "### Human-style verification",
        f"- Observed action line in terminal: `{show_action_line or '<missing>'}`",
        f"- Observed actions section: `{actions_section or '<missing>'}`",
        "",
        "### Error output",
        "```text",
        failure_block or error_text,
        "```",
        "",
        "### Environment",
        "- Runtime: repository-local compiled CLI help probe",
        "- Browser: N/A",
        "- URL: N/A",
        f"- OS: {platform.platform()}",
        f"- Working directory: `{result.get('working_directory')}`",
        f"- Run command: `{RUN_COMMAND}`",
    ]

    bug_lines = [
        f"# {TICKET_KEY} - {TICKET_SUMMARY}",
        "",
        "## Steps to reproduce",
        *[f"{index + 1}. {step}" for index, step in enumerate(REQUEST_STEPS)],
        "",
        "## Step-by-step observed behavior",
        *annotated_steps,
        "",
        "## Actual vs Expected",
        f"- **Expected:** `trackstate ticket --help` completes successfully and the `Actions:` list contains `show` with description `{config.required_action_description}`.",
        f"- **Actual:** {actual_vs_expected}",
        "",
        "## Exact error message or assertion failure",
        "```text",
        failure_block or error_text,
        "```",
        "",
        "## Environment details",
        "- Runtime: repository-local compiled CLI help probe",
        "- Browser: N/A",
        "- URL: N/A",
        f"- OS: {platform.platform()}",
        f"- Working directory: `{result.get('working_directory')}`",
        f"- Requested command: `{result.get('requested_command')}`",
        f"- Executed command: `{result.get('executed_command')}`",
        f"- Compiled binary: `{result.get('compiled_binary_path')}`",
        "",
        "## Relevant logs",
        "```text",
        "\n\n".join(
            fragment
            for fragment in (
                f"Actions section:\n{actions_section}" if actions_section else "",
                f"stdout:\n{stdout}" if stdout else "",
                f"stderr:\n{stderr}" if stderr else "",
            )
            if fragment
        ).strip()
        or "<no logs captured>",
        "```",
    ]

    RESULT_PATH.write_text(
        json.dumps(
            {
                "status": "failed",
                "passed": 0,
                "failed": 1,
                "skipped": 0,
                "summary": "0 passed, 1 failed",
                "error": error_text,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    JIRA_COMMENT_PATH.write_text("\n".join(jira_lines) + "\n", encoding="utf-8")
    PR_BODY_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    RESPONSE_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    BUG_DESCRIPTION_PATH.write_text("\n".join(bug_lines) + "\n", encoding="utf-8")


def _annotated_steps(result: dict[str, object]) -> list[str]:
    error_text = str(result.get("error", ""))
    stdout = str(result.get("stdout", ""))
    actions_section = str(result.get("actions_section", ""))
    show_action_line = str(result.get("show_action_line", "")).strip()

    if "Step 1 failed:" in error_text:
        return [
            "1. ❌ Execute command: trackstate ticket --help. Observed: the compiled CLI command did not complete successfully; see the error output below.",
            "2. ⏭️ Verify the output contains the show action in the available actions list. Observed: this check could not run because the help command itself failed.",
        ]
    if "Step 2 failed:" in error_text:
        return [
            "1. ✅ Execute command: trackstate ticket --help. Observed: the command completed and produced terminal help output.",
            "2. ❌ Verify the output contains the show action in the available actions list. "
            f"Observed actions section:\n{actions_section or stdout or '<missing>'}",
        ]
    if "Expected result failed:" in error_text or "Human-style verification failed:" in error_text:
        return [
            "1. ✅ Execute command: trackstate ticket --help. Observed: the command completed through the compiled CLI entry point.",
            "2. ❌ Verify the output contains the show action in the available actions list. "
            f"Observed action line: {show_action_line or '<missing>'}",
        ]
    return [
        "1. ❌ Execute command: trackstate ticket --help. Observed: the scenario failed before the expected verification checkpoints completed.",
        "2. ⏭️ Verify the output contains the show action in the available actions list. Observed: not reached.",
    ]


if __name__ == "__main__":
    main()
