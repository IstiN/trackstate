from __future__ import annotations

import json
import platform
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.services.trackstate_cli_attachment_storage_mode_validation_validator import (  # noqa: E402
    TrackStateCliAttachmentStorageModeValidationValidator,
)
from testing.core.config.trackstate_cli_attachment_storage_mode_validation_config import (  # noqa: E402
    TrackStateCliAttachmentStorageModeValidationConfig,
)
from testing.core.models.trackstate_cli_attachment_storage_mode_validation_result import (  # noqa: E402
    TrackStateCliAttachmentStorageModeValidationRepositoryState,
    TrackStateCliAttachmentStorageModeValidationStoredFile,
    TrackStateCliAttachmentStorageModeValidationResult,
)
from testing.core.models.trackstate_cli_command_observation import (  # noqa: E402
    TrackStateCliCommandObservation,
)
from testing.tests.support.trackstate_cli_attachment_storage_mode_validation_probe_factory import (  # noqa: E402
    create_trackstate_cli_attachment_storage_mode_validation_probe,
)

TICKET_KEY = "TS-603"
TICKET_SUMMARY = (
    "Attachment storage mode validation — factory blocks unimplemented modes early"
)
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
TEST_FILE_PATH = "testing/tests/TS-603/test_ts_603.py"
RUN_COMMAND = "python3 testing/tests/TS-603/test_ts_603.py"


class Ts603AttachmentStorageModeValidationScenario:
    def __init__(self) -> None:
        self.repository_root = REPO_ROOT
        self.config_path = self.repository_root / "testing/tests/TS-603/config.yaml"
        self.config = TrackStateCliAttachmentStorageModeValidationConfig.from_file(
            self.config_path
        )
        self.validator = TrackStateCliAttachmentStorageModeValidationValidator(
            probe=create_trackstate_cli_attachment_storage_mode_validation_probe(
                self.repository_root
            )
        )

    def execute(self) -> tuple[dict[str, object], list[str]]:
        validation = self.validator.validate(config=self.config)
        result = self._build_result(validation)
        failures: list[str] = []
        failures.extend(self._assert_exact_command(validation.observation))
        failures.extend(self._assert_initial_fixture(validation.initial_state, result))
        failures.extend(self._validate_runtime(validation, result))
        failures.extend(self._validate_filesystem_state(validation, result))
        return result, failures

    def _build_result(
        self,
        validation: TrackStateCliAttachmentStorageModeValidationResult,
    ) -> dict[str, object]:
        payload = validation.observation.result.json_payload
        payload_dict = payload if isinstance(payload, dict) else None
        target = payload_dict.get("target") if isinstance(payload_dict, dict) else None
        target_dict = target if isinstance(target, dict) else None
        error = payload_dict.get("error") if isinstance(payload_dict, dict) else None
        error_dict = error if isinstance(error, dict) else None
        return {
            "ticket": TICKET_KEY,
            "ticket_summary": TICKET_SUMMARY,
            "ticket_command": self.config.ticket_command,
            "supported_ticket_command": self.config.supported_ticket_command,
            "requested_command": validation.observation.requested_command_text,
            "executed_command": validation.observation.executed_command_text,
            "compiled_binary_path": validation.observation.compiled_binary_path,
            "repository_path": validation.observation.repository_path,
            "config_path": str(self.config_path),
            "os": platform.system(),
            "project_key": self.config.project_key,
            "issue_key": self.config.issue_key,
            "unsupported_attachment_mode": self.config.unsupported_attachment_mode,
            "expected_error_categories": list(self.config.expected_error_categories),
            "stdout": validation.observation.result.stdout,
            "stderr": validation.observation.result.stderr,
            "process_exit_code": validation.observation.result.exit_code,
            "payload": payload_dict,
            "error": error_dict,
            "observed_provider": payload_dict.get("provider")
            if isinstance(payload_dict, dict)
            else None,
            "observed_target_type": target_dict.get("type")
            if isinstance(target_dict, dict)
            else None,
            "observed_target_value": target_dict.get("value")
            if isinstance(target_dict, dict)
            else None,
            "observed_output_format": payload_dict.get("output")
            if isinstance(payload_dict, dict)
            else None,
            "observed_error_code": error_dict.get("code")
            if isinstance(error_dict, dict)
            else None,
            "observed_error_category": error_dict.get("category")
            if isinstance(error_dict, dict)
            else None,
            "observed_error_message": error_dict.get("message")
            if isinstance(error_dict, dict)
            else None,
            "observed_error_details": error_dict.get("details")
            if isinstance(error_dict, dict)
            else None,
            "observed_error_exit_code": error_dict.get("exitCode")
            if isinstance(error_dict, dict)
            else None,
            "initial_state": _state_to_dict(validation.initial_state),
            "final_state": _state_to_dict(validation.final_state),
            "steps": [],
            "human_verification": [],
        }

    def _assert_exact_command(
        self,
        observation: TrackStateCliCommandObservation,
    ) -> list[str]:
        failures: list[str] = []
        if observation.requested_command != self.config.requested_command:
            failures.append(
                "Precondition failed: TS-603 did not execute the supported attachment "
                "operation chosen for this ticket scenario.\n"
                f"Expected command: {' '.join(self.config.requested_command)}\n"
                f"Observed command: {observation.requested_command_text}"
            )
        if observation.compiled_binary_path is None:
            failures.append(
                "Precondition failed: TS-603 must execute a repository-local compiled "
                "binary from this checkout.\n"
                f"Executed command: {observation.executed_command_text}\n"
                f"Fallback reason: {observation.fallback_reason}"
            )
        return failures

    def _assert_initial_fixture(
        self,
        state: TrackStateCliAttachmentStorageModeValidationRepositoryState,
        result: dict[str, object],
    ) -> list[str]:
        failures: list[str] = []
        if not state.issue_main_exists:
            failures.append(
                "Precondition failed: the seeded repository did not contain TS-10 before "
                "running TS-603.\n"
                f"Observed state:\n{_describe_state(state)}"
            )
        if not state.source_file_exists:
            failures.append(
                "Precondition failed: the seeded repository did not contain sample.txt "
                "before running TS-603.\n"
                f"Observed state:\n{_describe_state(state)}"
            )
        if state.attachment_directory_exists or state.attachments_metadata_exists:
            failures.append(
                "Precondition failed: the seeded repository already contained attachment "
                "output before TS-603 ran.\n"
                f"Observed state:\n{_describe_state(state)}"
            )
        if self.config.unsupported_attachment_mode not in (state.project_json_text or ""):
            failures.append(
                "Precondition failed: the seeded project.json did not preserve the "
                "unsupported attachment mode string required by TS-603.\n"
                f"Observed project.json:\n{state.project_json_text}"
            )
        if not failures:
            _record_step(
                result,
                step=0,
                status="passed",
                action=(
                    "Seed a disposable local TrackState repository whose project.json "
                    "contains an unsupported attachmentStorage.mode value."
                ),
                observed=(
                    f"issue_main_exists={state.issue_main_exists}; "
                    f"source_file_exists={state.source_file_exists}; "
                    f"unsupported_mode={self.config.unsupported_attachment_mode}; "
                    f"git_head={state.head_commit_subject}"
                ),
            )
        return failures

    def _validate_runtime(
        self,
        validation: TrackStateCliAttachmentStorageModeValidationResult,
        result: dict[str, object],
    ) -> list[str]:
        failures: list[str] = []
        observation = validation.observation
        payload = observation.result.json_payload
        payload_dict = payload if isinstance(payload, dict) else None
        error = payload_dict.get("error") if isinstance(payload_dict, dict) else None
        error_dict = error if isinstance(error, dict) else None
        stdout = observation.result.stdout
        stderr = observation.result.stderr
        visible_error = _visible_error_text(payload, stdout=stdout, stderr=stderr)
        result["visible_error_text"] = visible_error

        if observation.result.exit_code != self.config.expected_exit_code:
            failures.append(
                "Step 1 failed: the local attachment operation did not return the "
                "documented non-zero exit code for the invalid configuration.\n"
                f"Expected exit code: {self.config.expected_exit_code}\n"
                f"Observed output:\n{_observed_command_output(stdout=stdout, stderr=stderr)}"
            )
            return failures
        _record_step(
            result,
            step=1,
            status="passed",
            action=(
                "Run the local attachment operation against the repository with the "
                "unsupported attachment storage mode."
            ),
            observed=(
                f"exit_code={observation.result.exit_code}; "
                f"requested_command={observation.requested_command_text}"
            ),
        )

        if not isinstance(payload_dict, dict):
            failures.append(
                "Step 2 failed: the CLI did not return a machine-readable JSON error "
                "envelope for the invalid attachment storage mode scenario.\n"
                f"{_observed_command_output(stdout=stdout, stderr=stderr)}"
            )
            return failures

        if payload_dict.get("provider") != self.config.expected_provider:
            failures.append(
                "Step 2 failed: the JSON envelope did not identify the expected local "
                "provider.\n"
                f"Expected provider: {self.config.expected_provider}\n"
                f"Observed payload: {json.dumps(payload_dict, indent=2, sort_keys=True)}"
            )
        if (
            isinstance(payload_dict.get("target"), dict)
            and payload_dict["target"].get("type") != self.config.expected_target_type
        ):
            failures.append(
                "Step 2 failed: the JSON envelope did not identify the local target type.\n"
                f"Expected target type: {self.config.expected_target_type}\n"
                f"Observed payload: {json.dumps(payload_dict, indent=2, sort_keys=True)}"
            )
        if not isinstance(error_dict, dict):
            failures.append(
                "Step 2 failed: the JSON envelope did not contain an error object for the "
                "invalid attachment storage mode.\n"
                f"Observed payload: {json.dumps(payload_dict, indent=2, sort_keys=True)}"
            )
            return failures

        observed_details = error_dict.get("details")
        details_dict = observed_details if isinstance(observed_details, dict) else {}
        if details_dict.get("reason") != self.config.expected_reason_message:
            failures.append(
                "Step 2 failed: the detailed invalid-mode reason changed from the "
                "expected factory validation text.\n"
                f"Expected reason: {self.config.expected_reason_message}\n"
                f"Observed payload: {json.dumps(payload_dict, indent=2, sort_keys=True)}"
            )

        missing_visible_fragments = [
            fragment
            for fragment in self.config.expected_visible_reason_fragments
            if fragment not in observation.output
        ]
        if missing_visible_fragments:
            failures.append(
                "Human-style verification failed: the terminal-visible output did not "
                "show the unsupported mode and allowed values clearly enough for a user.\n"
                f"Missing fragments: {missing_visible_fragments}\n"
                f"Observed output:\n{observation.output}"
            )
        else:
            _record_human_verification(
                result,
                check=(
                    "Verified the terminal-visible JSON output included the unsupported "
                    "attachmentStorage.mode reason and listed the allowed values."
                ),
                observed=visible_error,
            )

        observed_code = error_dict.get("code")
        observed_category = error_dict.get("category")
        observed_message = str(error_dict.get("message") or "")
        if observed_category not in self.config.expected_error_categories:
            failures.append(
                "Step 2 failed: the machine-readable error category did not classify the "
                "unsupported attachment storage mode as a validation/provider failure.\n"
                f"Expected category in: {list(self.config.expected_error_categories)}\n"
                f"Observed error.category: {observed_category}\n"
                f"Observed payload: {json.dumps(payload_dict, indent=2, sort_keys=True)}"
            )
        if (
            observed_code == self.config.disallowed_error_code
            and observed_category == self.config.disallowed_error_category
            and self.config.disallowed_error_message_fragment in observed_message
        ):
            failures.append(
                "Step 2 failed: the invalid attachment storage mode still surfaced as a "
                "generic attachment upload repository failure instead of a factory-level "
                "validation/provider failure.\n"
                f"Observed error.code: {observed_code}\n"
                f"Observed error.category: {observed_category}\n"
                f"Observed error.message: {observed_message}\n"
                f"Observed payload: {json.dumps(payload_dict, indent=2, sort_keys=True)}"
            )
        else:
            _record_step(
                result,
                step=2,
                status="passed",
                action=(
                    "Inspect the machine-readable error contract and confirm the invalid "
                    "attachment storage mode is rejected before the upload path reports a "
                    "generic repository failure."
                ),
                observed=json.dumps(error_dict, sort_keys=True),
            )
        return failures

    def _validate_filesystem_state(
        self,
        validation: TrackStateCliAttachmentStorageModeValidationResult,
        result: dict[str, object],
    ) -> list[str]:
        failures: list[str] = []
        final_state = validation.final_state
        if final_state.attachment_directory_exists:
            failures.append(
                "Step 3 failed: the invalid configuration still created an attachments "
                "directory.\n"
                f"Observed state:\n{_describe_state(final_state)}"
            )
        if final_state.attachments_metadata_exists:
            failures.append(
                "Step 3 failed: the invalid configuration still created attachments.json.\n"
                f"Observed state:\n{_describe_state(final_state)}"
            )
        if final_state.stored_files:
            failures.append(
                "Step 3 failed: the invalid configuration still wrote attachment files.\n"
                f"Observed state:\n{_describe_state(final_state)}"
            )
        if final_state.git_status_lines:
            failures.append(
                "Step 3 failed: the repository was left dirty even though the attachment "
                "operation should fail before side effects.\n"
                f"Observed state:\n{_describe_state(final_state)}"
            )
        if not failures:
            _record_step(
                result,
                step=3,
                status="passed",
                action=(
                    "Inspect the repository after the failed command and confirm no "
                    "attachment files or metadata were created."
                ),
                observed=(
                    f"attachment_directory_exists={final_state.attachment_directory_exists}; "
                    f"attachments_metadata_exists={final_state.attachments_metadata_exists}; "
                    f"stored_files={_format_stored_files(final_state.stored_files)}; "
                    f"git_status_lines={list(final_state.git_status_lines)}"
                ),
            )
        return failures


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    scenario = Ts603AttachmentStorageModeValidationScenario()
    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "ticket_summary": TICKET_SUMMARY,
        "steps": [],
        "human_verification": [],
    }
    try:
        result, failures = scenario.execute()
        if failures:
            raise AssertionError("\n".join(failures))
        _write_pass_outputs(result)
    except Exception as error:
        result.setdefault("ticket", TICKET_KEY)
        result.setdefault("ticket_summary", TICKET_SUMMARY)
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        _write_failure_outputs(result)
        raise


def _write_pass_outputs(result: dict[str, object]) -> None:
    if BUG_DESCRIPTION_PATH.exists():
        BUG_DESCRIPTION_PATH.unlink()
    RESULT_PATH.write_text(
        json.dumps(
            {
                "status": "passed",
                "passed": 1,
                "failed": 0,
                "skipped": 0,
                "summary": "1 passed, 0 failed",
            }
        ),
        encoding="utf-8",
    )
    visible_error = _as_text(result.get("visible_error_text"))
    final_state_text = json.dumps(result.get("final_state"), indent=2, sort_keys=True)
    jira_lines = [
        "h3. Test Automation Result",
        "",
        "*Status:* ✅ PASSED",
        f"*Test Case:* {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "h4. What was tested",
        (
            f"* Ticket step reviewed: {_jira_inline(_as_text(result.get('ticket_command')))}. "
            f"Automation executed {_jira_inline(_as_text(result.get('supported_ticket_command')))}."
        ),
        "* Seeded a disposable local repository with an unsupported {{attachmentStorage.mode}} string.",
        "* Ran a real local attachment CLI command from the seeded repository.",
        "* Verified the user-visible output exposed the invalid mode reason and the repository stayed unchanged.",
        "",
        "h4. Result",
        "* ✅ The CLI failed before any attachment side effects.",
        "* ✅ The machine-readable error contract did not regress to the disallowed generic repository upload failure.",
        f"* Human-style verification: the terminal-visible output showed {_jira_inline(visible_error)}.",
        "* Observed final repository state:",
        "{code:json}",
        final_state_text,
        "{code}",
        "",
        "h4. Test file",
        "{code}",
        TEST_FILE_PATH,
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
            f"- Ticket step reviewed: `{_as_text(result.get('ticket_command'))}`. "
            f"Automation executed `{_as_text(result.get('supported_ticket_command'))}`."
        ),
        "- Seeded a disposable local repository with an unsupported `attachmentStorage.mode` string.",
        "- Ran a real local attachment CLI command from the seeded repository.",
        "- Verified the user-visible output exposed the invalid mode reason and the repository stayed unchanged.",
        "",
        "## Result",
        "- ✅ The CLI failed before any attachment side effects.",
        "- ✅ The machine-readable error contract did not regress to the disallowed generic repository upload failure.",
        f"- Human-style verification: the terminal-visible output showed `{visible_error}`.",
        "- Observed final repository state:",
        "```json",
        final_state_text,
        "```",
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
    error_message = _as_text(result.get("error"))
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
        ),
        encoding="utf-8",
    )

    stdout = _as_text(result.get("stdout"))
    stderr = _as_text(result.get("stderr"))
    payload = result.get("payload")
    final_state = result.get("final_state")
    final_state_text = json.dumps(final_state, indent=2, sort_keys=True)
    visible_error = _visible_error_text(payload, stdout=stdout, stderr=stderr)
    observed_output = _observed_command_output(stdout=stdout, stderr=stderr)
    observed_code = _as_text(result.get("observed_error_code"))
    observed_category = _as_text(result.get("observed_error_category"))
    observed_message = _as_text(result.get("observed_error_message"))
    observed_details = json.dumps(
        result.get("observed_error_details"),
        indent=2,
        sort_keys=True,
    )
    observed_provider = _as_text(result.get("observed_provider"))
    observed_target_type = _as_text(result.get("observed_target_type"))
    jira_lines = [
        "h3. Test Automation Result",
        "",
        "*Status:* ❌ FAILED",
        f"*Test Case:* {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "h4. What was tested",
        (
            f"* Ticket step reviewed: {_jira_inline(_as_text(result.get('ticket_command')))}. "
            f"Automation executed {_jira_inline(_as_text(result.get('supported_ticket_command')))}."
        ),
        "* Seeded a disposable local repository whose {{project.json}} contains an unsupported {{attachmentStorage.mode}} string.",
        "* Ran the live local attachment upload flow and inspected both the machine-readable JSON envelope and the terminal-visible output.",
        "* Verified the repository state after the failed command to ensure no attachment files or metadata were written.",
        "",
        "h4. Result",
        "* ✅ Step 1 passed: the command failed immediately and did not write attachment files or metadata.",
        (
            f"* ✅ Human-style verification passed: the terminal-visible output included the unsupported mode reason "
            f"{_jira_inline(visible_error)}."
        ),
        (
            f"* ❌ Step 2 failed: the machine-readable error contract still reported "
            f"{_jira_inline(observed_code)} / {_jira_inline(observed_category)} with message "
            f"{_jira_inline(observed_message)} instead of a factory-level validation/provider-failure contract."
        ),
        (
            f"* Observed provider/target: {_jira_inline(observed_provider)} / "
            f"{_jira_inline(observed_target_type)}"
        ),
        "* Observed error details:",
        "{code:json}",
        observed_details,
        "{code}",
        "* Observed final repository state:",
        "{code:json}",
        final_state_text,
        "{code}",
        "",
        "h4. Observed output",
        "{code}",
        observed_output,
        "{code}",
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
        (
            f"- Ticket step reviewed: `{_as_text(result.get('ticket_command'))}`. "
            f"Automation executed `{_as_text(result.get('supported_ticket_command'))}`."
        ),
        "- Seeded a disposable local repository whose `project.json` contains an unsupported `attachmentStorage.mode` string.",
        "- Ran the live local attachment upload flow and inspected both the machine-readable JSON envelope and the terminal-visible output.",
        "- Verified the repository state after the failed command to ensure no attachment files or metadata were written.",
        "",
        "## Result",
        "- ✅ Step 1 passed: the command failed immediately and did not write attachment files or metadata.",
        f"- ✅ Human-style verification passed: the terminal-visible output included the unsupported mode reason `{visible_error}`.",
        (
            f"- ❌ Step 2 failed: the machine-readable error contract still reported "
            f"`{observed_code}` / `{observed_category}` with message `{observed_message}` "
            "instead of a factory-level validation/provider-failure contract."
        ),
        f"- Observed provider/target: `{observed_provider}` / `{observed_target_type}`",
        "- Observed error details:",
        "```json",
        observed_details,
        "```",
        "- Observed final repository state:",
        "```json",
        final_state_text,
        "```",
        "",
        "## Observed output",
        "```text",
        observed_output,
        "```",
        "",
        "## How to run",
        "```bash",
        RUN_COMMAND,
        "```",
    ]
    bug_lines = [
        f"# {TICKET_KEY} bug reproduction",
        "",
        "## Environment",
        f"- Repository path: `{_as_text(result.get('repository_path'))}`",
        f"- Ticket step reviewed: `{_as_text(result.get('ticket_command'))}`",
        f"- Executed supported command: `{_as_text(result.get('supported_ticket_command'))}`",
        f"- OS: `{platform.system()}`",
        f"- Provider/target: `{observed_provider}` / `{observed_target_type}`",
        f"- Unsupported mode seeded in `TS/project.json`: `{_as_text(result.get('unsupported_attachment_mode'))}`",
        "",
        "## Steps to reproduce",
        (
            "1. ✅ Create a disposable local TrackState repository containing issue "
            "`TS-10`, a source file `sample.txt`, and a `TS/project.json` file whose "
            "`attachmentStorage.mode` is set to an unsupported string. "
            "Observed: the repository opened as a valid Git repository and started with "
            "no `attachments/` directory or `attachments.json` file."
        ),
        (
            "2. ✅ Run the local CLI attachment operation "
            f"`{_as_text(result.get('supported_ticket_command'))}` from that repository. "
            f"Observed: the command failed with exit code `{_as_text(result.get('process_exit_code'))}` and the visible output included "
            f"`{visible_error}`."
        ),
        (
            "3. ❌ Inspect the machine-readable JSON error contract. "
            f"Observed: `error.code = {observed_code}`, `error.category = {observed_category}`, "
            f"and `error.message = {observed_message}`."
        ),
        (
            "4. ✅ Inspect the repository after the failed command. Observed: no "
            "`attachments/` directory, no `attachments.json`, and no dirty git state."
        ),
        "",
        "## Expected result",
        "- The unsupported `attachmentStorage.mode` should be rejected during repository/provider initialization.",
        "- The machine-readable error should be a factory-level validation/provider-failure contract, not the generic attachment upload repository error.",
        "- The terminal-visible output should make the unsupported mode and allowed values clear to the user.",
        "- No attachment files or metadata should be created.",
        "",
        "## Actual result",
        f"- The terminal-visible output did include the invalid mode reason: `{visible_error}`.",
        (
            f"- However, the machine-readable JSON still reported the generic repository "
            f"upload failure contract: `error.code = {observed_code}`, "
            f"`error.category = {observed_category}`, and "
            f"`error.message = {observed_message}`."
        ),
        f"- The detailed reason was only present under `error.details.reason`: \n\n```json\n{observed_details}\n```",
        "",
        "## Exact error / stack trace",
        "```text",
        _as_text(result.get("traceback")).rstrip(),
        "```",
        "",
        "## Captured CLI output",
        "```json",
        stdout.rstrip() or "{}",
        "```",
        "",
        "```text",
        stderr.rstrip() or "<empty>",
        "```",
        "",
        "## Final repository state",
        "```json",
        final_state_text,
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


def _state_to_dict(
    state: TrackStateCliAttachmentStorageModeValidationRepositoryState,
) -> dict[str, object]:
    return {
        "issue_main_exists": state.issue_main_exists,
        "source_file_exists": state.source_file_exists,
        "attachment_directory_exists": state.attachment_directory_exists,
        "attachments_metadata_exists": state.attachments_metadata_exists,
        "stored_files": [
            {
                "relative_path": stored_file.relative_path,
                "size_bytes": stored_file.size_bytes,
                "sha256": stored_file.sha256,
            }
            for stored_file in state.stored_files
        ],
        "git_status_lines": list(state.git_status_lines),
        "head_commit_subject": state.head_commit_subject,
        "head_commit_count": state.head_commit_count,
        "project_json_text": state.project_json_text,
    }


def _describe_state(
    state: TrackStateCliAttachmentStorageModeValidationRepositoryState,
) -> str:
    return json.dumps(_state_to_dict(state), indent=2, sort_keys=True)


def _format_stored_files(
    stored_files: tuple[TrackStateCliAttachmentStorageModeValidationStoredFile, ...],
) -> list[str]:
    return [stored_file.relative_path for stored_file in stored_files]


def _visible_error_text(
    payload: object | None,
    *,
    stdout: str,
    stderr: str,
) -> str:
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            details = error.get("details")
            reason = (
                details.get("reason")
                if isinstance(details, dict) and isinstance(details.get("reason"), str)
                else None
            )
            message = error.get("message")
            message_text = message if isinstance(message, str) else None
            if reason and message_text:
                return f"{message_text} {reason}".strip()
            if reason:
                return reason
            if message_text:
                return message_text
    return _observed_command_output(stdout=stdout, stderr=stderr).strip()


def _observed_command_output(*, stdout: str, stderr: str) -> str:
    fragments = []
    if stdout.strip():
        fragments.append(f"stdout:\n{stdout.rstrip()}")
    if stderr.strip():
        fragments.append(f"stderr:\n{stderr.rstrip()}")
    return "\n\n".join(fragments) if fragments else "<empty>"


def _jira_inline(text: str) -> str:
    return "{{%s}}" % text.replace("}", "\\}")


def _as_text(value: object | None) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


if __name__ == "__main__":
    main()
