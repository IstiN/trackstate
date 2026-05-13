from __future__ import annotations

import json
import os
import platform
import shutil
import sys
import traceback
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

SOURCE_ROOT_ENV = "TRACKSTATE_TS596_SOURCE_ROOT"


def _resolve_source_root() -> Path:
    configured_root = os.environ.get(SOURCE_ROOT_ENV)
    if not configured_root:
        return WORKSPACE_ROOT
    candidate = Path(configured_root).expanduser()
    if not candidate.is_absolute():
        candidate = (WORKSPACE_ROOT / candidate).resolve()
    else:
        candidate = candidate.resolve()
    if not candidate.is_dir():
        raise ValueError(
            f"{SOURCE_ROOT_ENV} must point to an existing TrackState checkout: {candidate}"
        )
    return candidate


SOURCE_ROOT = _resolve_source_root()

from testing.components.services.trackstate_cli_standalone_compile_validator import (  # noqa: E402
    TrackStateCliStandaloneCompileValidator,
)
from testing.core.config.trackstate_cli_standalone_compile_config import (  # noqa: E402
    TrackStateCliStandaloneCompileConfig,
)
from testing.core.models.trackstate_cli_standalone_compile_result import (  # noqa: E402
    TrackStateCliStandaloneCompileValidationResult,
)
from testing.tests.support.trackstate_cli_standalone_compile_probe_factory import (  # noqa: E402
    create_trackstate_cli_standalone_compile_probe,
)

TICKET_KEY = "TS-596"
TICKET_SUMMARY = (
    "Compile CLI for standalone Dart VM — compilation succeeds without "
    "dart:ui errors"
)
OUTPUTS_DIR = WORKSPACE_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
TEST_FILE_PATH = "testing/tests/TS-596/test_ts_596.py"
RUN_COMMAND = "python testing/tests/TS-596/test_ts_596.py"


class Ts596StandaloneCompileScenario:
    def __init__(self) -> None:
        self.workspace_root = WORKSPACE_ROOT
        self.source_root = SOURCE_ROOT
        self.config_path = self.workspace_root / "testing/tests/TS-596/config.yaml"
        self.config = TrackStateCliStandaloneCompileConfig.from_file(self.config_path)
        self.validator = TrackStateCliStandaloneCompileValidator(
            probe=create_trackstate_cli_standalone_compile_probe(self.source_root)
        )

    def execute(self) -> tuple[dict[str, object], list[str]]:
        validation = self.validator.validate(config=self.config)
        result = self._build_result(validation)
        try:
            failures: list[str] = []
            failures.extend(self._validate_preconditions(result))
            failures.extend(self._validate_compiler_outcome(validation, result))
            failures.extend(self._validate_generated_binary(validation, result))
            return result, failures
        finally:
            result["cleanup_note"] = self._cleanup_output_artifact(validation)

    def _build_result(
        self,
        validation: TrackStateCliStandaloneCompileValidationResult,
    ) -> dict[str, object]:
        observation = validation.observation
        return {
            "ticket": TICKET_KEY,
            "ticket_summary": TICKET_SUMMARY,
            "ticket_command": self.config.ticket_command,
            "requested_command": observation.requested_command_text,
            "executed_command": observation.executed_command_text,
            "fallback_reason": observation.fallback_reason,
            "repository_path": observation.repository_path,
            "source_root": str(self.source_root),
            "source_entrypoint": self.config.source_entrypoint,
            "compiled_binary_path": observation.compiled_binary_path,
            "dart_version": validation.dart_version,
            "stdout": observation.result.stdout,
            "stderr": observation.result.stderr,
            "exit_code": observation.result.exit_code,
            "output_exists": validation.output_exists,
            "output_size_bytes": validation.output_size_bytes,
            "output_is_executable": validation.output_is_executable,
            "steps": [],
            "human_verification": [],
        }

    def _cleanup_output_artifact(
        self,
        validation: TrackStateCliStandaloneCompileValidationResult,
    ) -> str:
        compiled_binary_path = Path(validation.observation.compiled_binary_path or "")
        backup_path_text = validation.preexisting_output_backup_path
        backup_path = Path(backup_path_text) if backup_path_text else None
        if backup_path is None:
            if compiled_binary_path.is_symlink() or compiled_binary_path.is_file():
                compiled_binary_path.unlink()
                return f"Removed generated artifact at {compiled_binary_path}."
            if compiled_binary_path.is_dir():
                shutil.rmtree(compiled_binary_path)
                return f"Removed generated directory artifact at {compiled_binary_path}."
            return f"No cleanup was needed for {compiled_binary_path}."

        self.validator.restore_output_path(
            output_path=compiled_binary_path,
            backup_path=backup_path,
        )
        return f"Restored pre-existing path at {compiled_binary_path} after verification."

    def _validate_preconditions(self, result: dict[str, object]) -> list[str]:
        failures: list[str] = []
        source_entrypoint = self.source_root / self.config.source_entrypoint
        if not source_entrypoint.is_file():
            failures.append(
                "Step 1 failed: the repository root does not contain the standalone CLI "
                "entrypoint required by the ticket.\n"
                f"Expected path: {source_entrypoint}"
            )
            return failures

        _record_step(
            result,
            step=1,
            status="passed",
            action="Open a terminal in the project root directory.",
            observed=f"Confirmed source entrypoint exists at {source_entrypoint}",
        )
        return failures

    def _validate_compiler_outcome(
        self,
        validation: TrackStateCliStandaloneCompileValidationResult,
        result: dict[str, object],
    ) -> list[str]:
        failures: list[str] = []
        observation = validation.observation
        visible_output = _visible_output(observation.result.stdout, observation.result.stderr)
        result["visible_output"] = visible_output

        if observation.result.exit_code != 0:
            failures.append(
                "Step 2 failed: the standalone Dart compile command exited non-zero.\n"
                f"Exit code: {observation.result.exit_code}\n"
                f"Visible output:\n{visible_output or '<empty>'}"
            )
            return failures

        lowered_output = visible_output.lower()
        forbidden_matches = [
            fragment
            for fragment in self.config.forbidden_output_fragments
            if fragment in lowered_output
        ]
        if forbidden_matches:
            failures.append(
                "Step 3 failed: the compiler output still surfaced the platform "
                "availability error that TS-596 guards against.\n"
                f"Matched fragments: {forbidden_matches}\n"
                f"Visible output:\n{visible_output}"
            )
            return failures

        _record_step(
            result,
            step=2,
            status="passed",
            action="Execute the compiler command and observe the compiler output and exit status.",
            observed=(
                f"exit_code={observation.result.exit_code}; "
                f"visible_output={visible_output or '<empty>'}"
            ),
        )
        _record_human_verification(
            result,
            check=(
                "Verified the terminal-visible compiler output completed successfully "
                "without any `dart:ui` platform error."
            ),
            observed=visible_output or "<empty>",
        )
        return failures

    def _validate_generated_binary(
        self,
        validation: TrackStateCliStandaloneCompileValidationResult,
        result: dict[str, object],
    ) -> list[str]:
        failures: list[str] = []
        compiled_binary_path = _as_text(result.get("compiled_binary_path"))

        if not validation.output_exists:
            failures.append(
                "Step 3 failed: the standalone compiler reported success, but no "
                "output binary was created.\n"
                f"Expected output path: {compiled_binary_path}"
            )
            return failures

        if not validation.output_is_executable:
            failures.append(
                "Step 3 failed: the generated standalone binary exists but is not "
                "marked executable.\n"
                f"Observed path: {compiled_binary_path}"
            )
            return failures

        _record_step(
            result,
            step=3,
            status="passed",
            action="Confirm the standalone binary is generated at the target path.",
            observed=(
                f"compiled_binary_path={compiled_binary_path}; "
                f"size_bytes={result.get('output_size_bytes')}; "
                f"is_executable={result.get('output_is_executable')}"
            ),
        )
        _record_human_verification(
            result,
            check=(
                "Verified the compiled artifact exists on disk as a standalone "
                "executable that a user can see at the reported output path."
            ),
            observed=(
                f"path={compiled_binary_path}; "
                f"size_bytes={result.get('output_size_bytes')}; "
                f"is_executable={result.get('output_is_executable')}"
            ),
        )
        return failures


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    scenario = Ts596StandaloneCompileScenario()

    try:
        result, failures = scenario.execute()
        if failures:
            raise AssertionError("\n".join(failures))
        _write_pass_outputs(result)
    except Exception as error:
        failure_result = locals().get("result", {}) if "result" in locals() else {}
        if not isinstance(failure_result, dict):
            failure_result = {}
        failure_result.setdefault("ticket_command", scenario.config.ticket_command)
        failure_result.setdefault("requested_command", " ".join(scenario.config.requested_command))
        failure_result.setdefault("config_path", str(scenario.config_path))
        failure_result.setdefault("source_root", str(scenario.source_root))
        failure_result.setdefault("source_entrypoint", scenario.config.source_entrypoint)
        failure_result.setdefault(
            "compiled_binary_path",
            failure_result.get("compiled_binary_path") or "N/A",
        )
        failure_result.setdefault(
            "dart_version",
            failure_result.get("dart_version") or "<unknown>",
        )
        failure_result.update(
            {
                "ticket": TICKET_KEY,
                "ticket_summary": TICKET_SUMMARY,
                "error": f"{type(error).__name__}: {error}",
                "traceback": traceback.format_exc(),
            }
        )
        _write_failure_outputs(failure_result)
        raise


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

    visible_output = _as_text(result.get("visible_output")) or "<empty>"
    executed_command = _as_text(result.get("executed_command"))
    compiled_binary_path = _as_text(result.get("compiled_binary_path"))
    output_size_bytes = _as_text(result.get("output_size_bytes"))
    dart_version = _as_text(result.get("dart_version"))
    cleanup_note = _as_text(result.get("cleanup_note"))
    dart_ui_text = _jira_inline("dart:ui")

    jira_lines = [
        "h3. Test Automation Result",
        "",
        "*Status:* ✅ PASSED",
        f"*Test Case:* {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "h4. What was tested",
        (
            f"* Opened the repository root and exercised the standalone compiler flow "
            f"for {_jira_inline(_as_text(result.get('source_entrypoint')))}."
        ),
        f"* Ticket command: {_jira_inline(_as_text(result.get('ticket_command')))}",
        f"* Executed command: {_jira_inline(executed_command)}",
        f"* Verified exit code 0, absence of {dart_ui_text} platform errors, and creation of {_jira_inline(compiled_binary_path)}.",
        "",
        "h4. Human-style verification",
        f"* Terminal output observed by a user: {_jira_inline(visible_output)}",
        f"* Generated executable observed on disk: {_jira_inline(compiled_binary_path)} ({_jira_inline(output_size_bytes)} bytes)",
        "",
        "h4. Result",
        "* Step 1 passed: the standalone CLI entrypoint was present in the project root.",
        "* Step 2 passed: the standalone Dart compiler completed with exit code 0.",
        "* Step 3 passed: no `dart:ui` platform-availability error appeared and the standalone executable was created.",
        "* The observed behavior matched the expected result.",
        "",
        "h4. Environment",
        f"* OS: {_jira_inline(platform.system())}",
        f"* Dart SDK: {_jira_inline(dart_version)}",
        *([f"* Cleanup note: {_jira_inline(cleanup_note)}"] if cleanup_note else []),
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

    markdown_lines = [
        "## Test Automation Result",
        "",
        "**Status:** ✅ PASSED",
        f"**Test Case:** {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "## What was automated",
        (
            f"- Opened the repository root and exercised the standalone compiler flow "
            f"for `{_as_text(result.get('source_entrypoint'))}`."
        ),
        f"- Ticket command: `{_as_text(result.get('ticket_command'))}`",
        f"- Executed command: `{executed_command}`",
        (
            f"- Verified exit code `0`, absence of `dart:ui` platform errors, and "
            f"creation of `{compiled_binary_path}`."
        ),
        "",
        "## Result",
        "- Step 1 passed: the standalone CLI entrypoint was present in the project root.",
        "- Step 2 passed: the standalone Dart compiler completed with exit code 0.",
        "- Step 3 passed: no `dart:ui` platform-availability error appeared and the standalone executable was created.",
        f"- Human-style verification: terminal output `{visible_output}` and executable `{compiled_binary_path}` ({output_size_bytes} bytes) matched the expected result.",
        "",
        "## Environment",
        f"- OS: `{platform.system()}`",
        f"- Dart SDK: `{dart_version}`",
        *([f"- Cleanup note: `{cleanup_note}`"] if cleanup_note else []),
        "",
        "## How to run",
        "```bash",
        RUN_COMMAND,
        "```",
    ]

    JIRA_COMMENT_PATH.write_text("\n".join(jira_lines) + "\n", encoding="utf-8")
    PR_BODY_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    RESPONSE_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")


def _write_failure_outputs(result: dict[str, object]) -> None:
    error_message = _as_text(result.get("error")) or "AssertionError: unknown failure"
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

    visible_output = _visible_output(
        _as_text(result.get("stdout")),
        _as_text(result.get("stderr")),
    ) or "<empty>"
    requested_command = _as_text(result.get("requested_command"))
    executed_command = _as_text(result.get("executed_command")) or requested_command
    compiled_binary_path = _as_text(result.get("compiled_binary_path"))
    output_exists = _as_text(result.get("output_exists"))
    output_size_bytes = _as_text(result.get("output_size_bytes"))
    dart_version = _as_text(result.get("dart_version"))
    traceback_text = _as_text(result.get("traceback"))
    observed_output = _observed_output(
        _as_text(result.get("stdout")),
        _as_text(result.get("stderr")),
    )

    jira_lines = [
        "h3. Test Automation Result",
        "",
        "*Status:* ❌ FAILED",
        f"*Test Case:* {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "h4. What was tested",
        f"* Ticket command: {_jira_inline(_as_text(result.get('ticket_command')))}",
        f"* Executed command: {_jira_inline(executed_command)}",
        f"* Checked the compiler exit status, visible output, and generated executable path {_jira_inline(compiled_binary_path)}.",
        "",
        "h4. Result",
        f"* ❌ Failure: {_jira_inline(error_message)}",
        f"* Observed exit code: {_jira_inline(_as_text(result.get('exit_code')))}",
        f"* Observed output exists/size: {_jira_inline(output_exists)} / {_jira_inline(output_size_bytes)}",
        f"* Observed visible output: {_jira_inline(visible_output)}",
        "* The standalone compile behavior did not match the expected result.",
        "",
        "h4. Observed compiler output",
        "{code}",
        observed_output,
        "{code}",
        "",
        "h4. Environment",
        f"* Source checkout: {_jira_inline(_as_text(result.get('source_root')))}",
        f"* OS: {_jira_inline(platform.system())}",
        f"* Dart SDK: {_jira_inline(dart_version)}",
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

    markdown_lines = [
        "## Test Automation Result",
        "",
        "**Status:** ❌ FAILED",
        f"**Test Case:** {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "## What was automated",
        f"- Ticket command: `{_as_text(result.get('ticket_command'))}`",
        f"- Executed command: `{executed_command}`",
        (
            f"- Checked the compiler exit status, visible output, and generated "
            f"executable path `{compiled_binary_path}`."
        ),
        "",
        "## Result",
        f"- ❌ Failure: `{error_message}`",
        f"- Observed exit code: `{_as_text(result.get('exit_code'))}`",
        f"- Observed output exists/size: `{output_exists}` / `{output_size_bytes}`",
        f"- Observed visible output: `{visible_output}`",
        "- The standalone compile behavior did not match the expected result.",
        "",
        "## Observed compiler output",
        "```text",
        observed_output,
        "```",
        "",
        "## Environment",
        f"- Source checkout: `{_as_text(result.get('source_root'))}`",
        f"- OS: `{platform.system()}`",
        f"- Dart SDK: `{dart_version}`",
        "",
        "## How to run",
        "```bash",
        RUN_COMMAND,
        "```",
    ]

    bug_lines = [
        "# TS-596 bug reproduction",
        "",
        "## Environment",
        f"- Source checkout: `{_as_text(result.get('source_root'))}`",
        f"- Requested ticket command: `{_as_text(result.get('ticket_command'))}`",
        f"- Executed command: `{executed_command}`",
        f"- Source entrypoint: `{_as_text(result.get('source_entrypoint'))}`",
        f"- Generated binary path: `{compiled_binary_path}`",
        f"- OS: `{platform.system()}`",
        f"- Dart SDK: `{dart_version}`",
        "",
        "## Steps to reproduce",
        (
            f"1. ✅ Open a terminal in the project root directory. Observed: the source "
            f"entrypoint `{_as_text(result.get('source_entrypoint'))}` was available in "
            f"`{_as_text(result.get('source_root'))}`."
        ),
        (
            f"2. ❌ Execute the compiler command `{_as_text(result.get('ticket_command'))}`. "
            f"Observed: command `{executed_command}` exited with code "
            f"`{_as_text(result.get('exit_code'))}` and showed `{visible_output}`."
        ),
        (
            f"3. ❌ Observe the compiler output and the target binary. Observed: "
            f"`output_exists={output_exists}`, `output_size_bytes={output_size_bytes}`, "
            "and the compiler output is captured below."
        ),
        "",
        "## Expected result",
        "- The compilation process should complete successfully with exit code `0`.",
        "- No errors about `Dart library 'dart:ui' is not available on this platform` should appear.",
        "- A standalone binary should be generated at the target path.",
        "",
        "## Actual result",
        f"- The compile flow failed with `{error_message}`.",
        f"- Visible compiler output: `{visible_output}`.",
        (
            f"- Generated binary state: `path={compiled_binary_path}`, "
            f"`exists={output_exists}`, `size_bytes={output_size_bytes}`."
        ),
        "",
        "## Exact error / stack trace",
        "```text",
        traceback_text.rstrip(),
        "```",
        "",
        "## Captured compiler output",
        "```text",
        observed_output,
        "```",
    ]

    JIRA_COMMENT_PATH.write_text("\n".join(jira_lines) + "\n", encoding="utf-8")
    PR_BODY_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    RESPONSE_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    BUG_DESCRIPTION_PATH.write_text("\n".join(bug_lines) + "\n", encoding="utf-8")


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


def _visible_output(stdout: str, stderr: str) -> str:
    fragments = [fragment.strip() for fragment in (stdout, stderr) if fragment.strip()]
    return "\n".join(fragments).strip()


def _observed_output(stdout: str, stderr: str) -> str:
    fragments = [
        f"stdout:\n{stdout.rstrip() or '<empty>'}",
        f"stderr:\n{stderr.rstrip() or '<empty>'}",
    ]
    return "\n\n".join(fragments)


def _as_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def _jira_inline(text: str) -> str:
    return "{{" + text.replace("}", "\\}") + "}}"


if __name__ == "__main__":
    main()
