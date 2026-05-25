from __future__ import annotations

import json
import platform
from pathlib import Path
import traceback
import unittest

from testing.components.services.trackstate_cli_attachment_upload_boundary_validator import (
    TrackStateCliAttachmentUploadBoundaryValidator,
)
from testing.core.config.trackstate_cli_attachment_upload_boundary_config import (
    TrackStateCliAttachmentUploadBoundaryConfig,
)
from testing.core.models.trackstate_cli_attachment_upload_boundary_result import (
    TrackStateCliAttachmentUploadBoundaryRepositoryState,
)
from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)
from testing.tests.support.trackstate_cli_attachment_upload_boundary_probe_factory import (
    create_trackstate_cli_attachment_upload_boundary_probe,
)

TICKET_KEY = "TS-387"
REPO_ROOT = Path(__file__).resolve().parents[3]
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"


class CliAttachmentUploadMultiFileBoundaryTest(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.repository_root = REPO_ROOT
        self.config = TrackStateCliAttachmentUploadBoundaryConfig.from_defaults()
        self.validator = TrackStateCliAttachmentUploadBoundaryValidator(
            probe=create_trackstate_cli_attachment_upload_boundary_probe(
                self.repository_root
            )
        )

    def test_attachment_upload_rejects_multiple_file_flags(self) -> None:
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        result = self._result_template()

        try:
            validation = self.validator.validate(config=self.config)
            result["requested_command"] = validation.observation.requested_command_text
            result["executed_command"] = validation.observation.executed_command_text
            result["repository_path"] = validation.observation.repository_path
            result["compiled_binary_path"] = validation.observation.compiled_binary_path
            result["fallback_reason"] = validation.observation.fallback_reason
            result["stdout"] = validation.observation.result.stdout
            result["stderr"] = validation.observation.result.stderr
            result["output"] = validation.observation.output
            result["json_payload"] = validation.observation.result.json_payload
            result["initial_state"] = self._state_payload(validation.initial_state)
            result["final_state"] = self._state_payload(validation.final_state)

            self._assert_exact_command(validation.observation)
            self._assert_initial_fixture(validation.initial_state)

            runtime_failures = self._collect_runtime_failures(validation.observation)
            repository_failures = self._collect_repository_side_effect_failures(
                initial_state=validation.initial_state,
                final_state=validation.final_state,
            )
            failures = [*runtime_failures, *repository_failures]

            _record_step(
                result,
                step=1,
                status="passed" if not failures else "failed",
                action=(
                    "Execute `trackstate attachment upload --issue TS-22 --file "
                    "file1.png --file file2.png --target local` from the seeded local "
                    "TrackState repository."
                ),
                observed=self._step_observation_text(
                    validation.observation,
                    validation.final_state,
                ),
            )
            _record_human_verification(
                result,
                check=(
                    "Observed the user-visible CLI JSON output to confirm it clearly "
                    "reported a single-file validation failure instead of a success "
                    "upload envelope."
                ),
                observed=(
                    f"exit_code={validation.observation.result.exit_code}; "
                    f"visible_output={validation.observation.output or '<empty>'}"
                ),
            )
            _record_human_verification(
                result,
                check=(
                    "Inspected the local repository the same way a user would after the "
                    "command: attachment files on disk and git history."
                ),
                observed=self._repository_observation_text(validation.final_state),
            )

            if failures:
                result["product_failure"] = True
                raise AssertionError("\n\n".join(failures))

            _write_pass_outputs(result)
        except Exception as error:
            result["error"] = f"{type(error).__name__}: {error}"
            result["traceback"] = traceback.format_exc()
            _write_failure_outputs(
                result,
                include_bug_description=bool(result.get("product_failure")),
            )
            raise

    def _assert_exact_command(self, observation: TrackStateCliCommandObservation) -> None:
        self.assertEqual(
            observation.requested_command,
            self.config.requested_command,
            "Precondition failed: TS-387 did not execute the exact ticket command.\n"
            f"Expected command: {' '.join(self.config.requested_command)}\n"
            f"Observed command: {observation.requested_command_text}",
        )
        self.assertIsNotNone(
            observation.compiled_binary_path,
            "Precondition failed: TS-387 must execute a repository-local compiled "
            "binary so the seeded repository stays the current working directory.\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Fallback reason: {observation.fallback_reason}",
        )
        self.assertEqual(
            observation.executed_command[0],
            observation.compiled_binary_path,
            "Precondition failed: TS-387 did not run the compiled repository-local "
            "CLI binary.\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Compiled binary path: {observation.compiled_binary_path}",
        )

    def _assert_initial_fixture(
        self,
        state: TrackStateCliAttachmentUploadBoundaryRepositoryState,
    ) -> None:
        self.assertTrue(
            state.issue_main_exists,
            "Precondition failed: the seeded repository did not contain TS-22 before "
            "executing the duplicate-file upload scenario.\n"
            f"Observed repository state:\n{self._describe_state(state)}",
        )
        self.assertFalse(
            state.attachment_directory_exists or state.uploaded_attachment_paths,
            "Precondition failed: the seeded repository already contained uploaded "
            "attachments before TS-387 ran.\n"
            f"Observed repository state:\n{self._describe_state(state)}",
        )
        self.assertEqual(
            state.head_commit_count,
            1,
            "Precondition failed: TS-387 expected a single seed commit before the "
            "upload command executed.\n"
            f"Observed repository state:\n{self._describe_state(state)}",
        )

    def _collect_runtime_failures(
        self,
        observation: TrackStateCliCommandObservation,
    ) -> list[str]:
        failures: list[str] = []
        payload = observation.result.json_payload

        if self.config.expected_exit_code is None:
            if observation.result.exit_code == 0:
                failures.append(
                    "Step 1 failed: executing the exact duplicate-file command "
                    "succeeded instead of failing with a validation error.\n"
                    f"Observed exit code: {observation.result.exit_code}\n"
                    f"Repository path: {observation.repository_path}\n"
                    f"Requested command: {observation.requested_command_text}\n"
                    f"Executed command: {observation.executed_command_text}\n"
                    f"Fallback reason: {observation.fallback_reason}\n"
                    f"stdout:\n{observation.result.stdout}\n"
                    f"stderr:\n{observation.result.stderr}"
                )
        elif observation.result.exit_code != self.config.expected_exit_code:
            failures.append(
                "Step 1 failed: executing the exact duplicate-file command did not fail "
                "with the expected validation exit code.\n"
                f"Expected exit code: {self.config.expected_exit_code}\n"
                f"Observed exit code: {observation.result.exit_code}\n"
                f"Repository path: {observation.repository_path}\n"
                f"Requested command: {observation.requested_command_text}\n"
                f"Executed command: {observation.executed_command_text}\n"
                f"Fallback reason: {observation.fallback_reason}\n"
                f"stdout:\n{observation.result.stdout}\n"
                f"stderr:\n{observation.result.stderr}"
            )

        if not isinstance(payload, dict):
            failures.append(
                "Step 1 failed: the duplicate-file CLI invocation did not return a "
                "machine-readable JSON envelope.\n"
                f"Observed stdout:\n{observation.result.stdout}\n"
                f"Observed stderr:\n{observation.result.stderr}"
            )
        else:
            if payload.get("ok") is not False:
                failures.append(
                    "Expected result failed: the duplicate-file invocation did not return "
                    "`ok: false`.\n"
                    f"Observed payload: {payload}"
                )

            error = payload.get("error")
            if not isinstance(error, dict):
                failures.append(
                    "Step 1 failed: the failure envelope did not include an `error` "
                    f"object.\nObserved payload: {payload}"
                )
            elif error.get("category") != self.config.expected_error_category:
                failures.append(
                    "Expected result failed: the duplicate-file invocation did not "
                    "classify the outcome as a validation error.\n"
                    f"Expected category: {self.config.expected_error_category}\n"
                    f"Observed error: {error}"
                )

        output = observation.output
        if not self._contains_single_file_validation_message(output):
            failures.append(
                "Human-style verification failed: the visible CLI output did not tell "
                "the user that only one file may be uploaded per invocation.\n"
                f"Observed output:\n{output}"
            )

        for fragment in self.config.required_failure_stdout_fragments:
            if fragment not in observation.result.stdout:
                failures.append(
                    "Human-style verification failed: the visible CLI output did not "
                    "show the expected failure envelope markers.\n"
                    f"Missing fragment: {fragment}\n"
                    f"Observed stdout:\n{observation.result.stdout}"
                )

        if '"command": "attachment-upload"' in observation.result.stdout:
            failures.append(
                "Expected result failed: the visible CLI output still reported an "
                "attachment-upload success payload instead of rejecting the duplicate "
                "`--file` options.\n"
                f"Observed stdout:\n{observation.result.stdout}"
            )
        return failures

    def _collect_repository_side_effect_failures(
        self,
        *,
        initial_state: TrackStateCliAttachmentUploadBoundaryRepositoryState,
        final_state: TrackStateCliAttachmentUploadBoundaryRepositoryState,
    ) -> list[str]:
        failures: list[str] = []
        if final_state.attachment_directory_exists:
            failures.append(
                "Expected result failed: the repository gained an attachment directory "
                "even though the duplicate-file command should have been rejected.\n"
                f"Observed repository state:\n{self._describe_state(final_state)}"
            )
        if final_state.uploaded_attachment_paths:
            failures.append(
                "Expected result failed: the duplicate-file command uploaded at least "
                "one attachment instead of leaving the issue unchanged.\n"
                f"Uploaded attachment paths: {final_state.uploaded_attachment_paths}\n"
                f"Observed repository state:\n{self._describe_state(final_state)}"
            )
        if final_state.head_commit_count != initial_state.head_commit_count:
            failures.append(
                "Expected result failed: the duplicate-file command created a new git "
                "commit even though no upload should occur.\n"
                f"Initial commit count: {initial_state.head_commit_count}\n"
                f"Final commit count: {final_state.head_commit_count}\n"
                f"Observed repository state:\n{self._describe_state(final_state)}"
            )
        if final_state.head_commit_subject != initial_state.head_commit_subject:
            failures.append(
                "Expected result failed: the duplicate-file command changed HEAD from "
                "the seed commit, which indicates the CLI persisted upload side "
                "effects.\n"
                f"Initial HEAD: {initial_state.head_commit_subject}\n"
                f"Final HEAD: {final_state.head_commit_subject}\n"
                f"Observed repository state:\n{self._describe_state(final_state)}"
            )
        return failures

    def _contains_single_file_validation_message(self, output: str) -> bool:
        normalized = output.lower()
        if "file" not in normalized:
            return False
        return any(
            marker in normalized
            for marker in self.config.accepted_error_message_markers
        )

    def _describe_state(
        self,
        state: TrackStateCliAttachmentUploadBoundaryRepositoryState,
    ) -> str:
        return "\n".join(
            (
                f"issue_main_exists={state.issue_main_exists}",
                f"attachment_directory_exists={state.attachment_directory_exists}",
                f"uploaded_attachment_paths={state.uploaded_attachment_paths}",
                f"head_commit_subject={state.head_commit_subject}",
                f"head_commit_count={state.head_commit_count}",
                f"git_status_lines={state.git_status_lines}",
                "issue_main_content=",
                state.issue_main_content or "<missing>",
            )
        )

    def _result_template(self) -> dict[str, object]:
        return {
            "ticket": TICKET_KEY,
            "requested_command": " ".join(self.config.requested_command),
            "steps": [],
            "human_verification": [],
            "expected_result": (
                "The command fails with a validation error indicating that exactly one "
                "file must be provided per invocation, and no files are uploaded."
            ),
        }

    def _step_observation_text(
        self,
        observation: TrackStateCliCommandObservation,
        final_state: TrackStateCliAttachmentUploadBoundaryRepositoryState,
    ) -> str:
        payload_text = (
            json.dumps(observation.result.json_payload, indent=2, sort_keys=True)
            if isinstance(observation.result.json_payload, dict)
            else "<non-json>"
        )
        return "\n".join(
            (
                f"exit_code={observation.result.exit_code}",
                f"repository_path={observation.repository_path}",
                f"executed_command={observation.executed_command_text}",
                f"payload={payload_text}",
                f"uploaded_attachment_paths={final_state.uploaded_attachment_paths}",
                f"head_commit_subject={final_state.head_commit_subject}",
                f"head_commit_count={final_state.head_commit_count}",
            )
        )

    def _repository_observation_text(
        self,
        state: TrackStateCliAttachmentUploadBoundaryRepositoryState,
    ) -> str:
        return (
            f"attachment_directory_exists={state.attachment_directory_exists}; "
            f"uploaded_attachment_paths={state.uploaded_attachment_paths}; "
            f"head_commit_subject={state.head_commit_subject}; "
            f"head_commit_count={state.head_commit_count}; "
            f"git_status_lines={state.git_status_lines}"
        )

    def _state_payload(
        self,
        state: TrackStateCliAttachmentUploadBoundaryRepositoryState,
    ) -> dict[str, object]:
        return {
            "issue_main_exists": state.issue_main_exists,
            "attachment_directory_exists": state.attachment_directory_exists,
            "uploaded_attachment_paths": list(state.uploaded_attachment_paths),
            "issue_main_content": state.issue_main_content,
            "git_status_lines": list(state.git_status_lines),
            "head_commit_subject": state.head_commit_subject,
            "head_commit_count": state.head_commit_count,
        }


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
    PR_BODY_PATH.write_text(_pr_body(result, passed=True), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_summary(result, passed=True), encoding="utf-8")


def _write_failure_outputs(
    result: dict[str, object],
    *,
    include_bug_description: bool,
) -> None:
    error = str(result.get("error", "AssertionError: unknown failure"))
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
    PR_BODY_PATH.write_text(_pr_body(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_summary(result, passed=False), encoding="utf-8")
    if include_bug_description:
        BUG_DESCRIPTION_PATH.write_text(_bug_description(result), encoding="utf-8")
    else:
        BUG_DESCRIPTION_PATH.unlink(missing_ok=True)


def _jira_comment(result: dict[str, object], *, passed: bool) -> str:
    lines = [
        f"h3. {TICKET_KEY} {'PASSED' if passed else 'FAILED'}",
        "",
        "*Automation coverage*",
        (
            "* Compiled the current TrackState CLI, seeded a disposable local repository "
            "with {{TS-22}} plus {{file1.png}} and {{file2.png}}, and executed the exact "
            "ticket command."
        ),
        (
            "* Verified the command should fail with a visible validation error for "
            "duplicate {{--file}} input."
        ),
        (
            "* Verified no attachment directory, uploaded file, or extra git commit "
            "should be created."
        ),
        "",
        "*Observed result*",
        (
            "* Matched the expected result."
            if passed
            else "* Did not match the expected result."
        ),
        (
            f"* Environment: target local TrackState repository, repository path "
            f"{{{{{result.get('repository_path', '<unknown>')}}}}}, compiled binary "
            f"{{{{{result.get('compiled_binary_path', '<unknown>')}}}}}, OS "
            f"{{{{{platform.system()}}}}}."
        ),
        "* Screenshot: not applicable for CLI; logs included below.",
        "",
        "*Step results*",
        *_step_lines(result, jira=True),
        "",
        "*Human-style verification*",
        *_human_lines(result, jira=True),
    ]
    if not passed:
        lines.extend(
            [
                "",
                "*Exact error*",
                "{code}",
                str(result.get("traceback", result.get("error", ""))),
                "{code}",
            ]
        )
    return "\n".join(lines) + "\n"


def _pr_body(result: dict[str, object], *, passed: bool) -> str:
    lines = [
        f"## {TICKET_KEY} {'Passed' if passed else 'Failed'}",
        "",
        "### Automation",
        (
            "- Compiled the current TrackState CLI, seeded a disposable local repository "
            "with `TS-22`, `file1.png`, and `file2.png`, and executed the exact ticket "
            "command."
        ),
        "- Verified the command should fail with a visible validation error for duplicate `--file` input.",
        "- Verified no attachment directory, uploaded file, or extra git commit should be created.",
        "",
        "### Observed result",
        "- Matched the expected result." if passed else "- Did not match the expected result.",
        (
            f"- Environment: target `local TrackState repository`, repository path "
            f"`{result.get('repository_path', '<unknown>')}`, compiled binary "
            f"`{result.get('compiled_binary_path', '<unknown>')}`, OS `{platform.system()}`."
        ),
        "- Screenshot: not applicable for CLI; logs included below.",
        "",
        "### Step results",
        *_step_lines(result, jira=False),
        "",
        "### Human-style verification",
        *_human_lines(result, jira=False),
    ]
    if not passed:
        lines.extend(
            [
                "",
                "### Exact error",
                "```text",
                str(result.get("traceback", result.get("error", ""))),
                "```",
            ]
        )
    return "\n".join(lines) + "\n"


def _response_summary(result: dict[str, object], *, passed: bool) -> str:
    status = "passed" if passed else "failed"
    lines = [
        f"# {TICKET_KEY} {status}",
        "",
        (
            "The duplicate `--file` attachment upload boundary matched the expected "
            "behavior."
            if passed
            else "The duplicate `--file` attachment upload boundary did not match the "
            "expected behavior."
        ),
        "",
        "## Automation",
        f"- Command: `{result.get('requested_command', '')}`",
        (
            f"- Repository path: `{result.get('repository_path', '<unknown>')}`; "
            f"compiled binary: `{result.get('compiled_binary_path', '<unknown>')}`."
        ),
        "- Verified a validation failure is surfaced and the repository stays unchanged.",
        "",
        "## Human-style verification",
        *_human_lines(result, jira=False),
    ]
    if not passed:
        lines.extend(
            [
                "",
                "## Error",
                "```text",
                str(result.get("error", "AssertionError: unknown failure")),
                "```",
            ]
        )
    return "\n".join(lines) + "\n"


def _bug_description(result: dict[str, object]) -> str:
    step_lines = _bug_step_lines(result)
    return "\n".join(
        [
            f"# {TICKET_KEY} regression: CLI attachment upload accepts duplicate `--file` input",
            "",
            "## Steps to reproduce",
            *step_lines,
            "",
            "## Actual result",
            (
                "The command exits successfully, returns an attachment-upload success "
                "payload, uploads `TS/TS-22/attachments/file2.png`, and creates the git "
                "commit `Upload attachment to TS-22`."
            ),
            "",
            "## Expected result",
            str(result.get("expected_result", "")),
            "",
            "## Exact error message or assertion failure",
            "```text",
            str(result.get("traceback", result.get("error", ""))),
            "```",
            "",
            "## Environment",
            f"- Target: local TrackState repository",
            f"- Repository path: `{result.get('repository_path', '<unknown>')}`",
            f"- Compiled binary: `{result.get('compiled_binary_path', '<unknown>')}`",
            f"- OS: `{platform.system()}`",
            "",
            "## Logs",
            "```text",
            f"stdout:\n{result.get('stdout', '')}\n",
            f"stderr:\n{result.get('stderr', '')}\n",
            f"final_state={json.dumps(result.get('final_state', {}), indent=2, sort_keys=True)}",
            "```",
        ]
    ) + "\n"


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for step in result.get("steps", []):
        if not isinstance(step, dict):
            continue
        marker = "PASS" if step.get("status") == "passed" else "FAIL"
        prefix = "*" if jira else "-"
        lines.append(f"{prefix} Step {step.get('step')} - {marker}: {step.get('action')}")
        lines.append(f"{prefix} Observed: {step.get('observed')}")
    return lines or [("* No step observations recorded." if jira else "- No step observations recorded.")]


def _human_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for check in result.get("human_verification", []):
        if not isinstance(check, dict):
            continue
        prefix = "*" if jira else "-"
        lines.append(f"{prefix} {check.get('check')}")
        lines.append(f"{prefix} Observed: {check.get('observed')}")
    return lines or [("* No human-style checks recorded." if jira else "- No human-style checks recorded.")]


def _bug_step_lines(result: dict[str, object]) -> list[str]:
    stdout = result.get("stdout", "")
    return [
        (
            "1. Execute `trackstate attachment upload --issue TS-22 --file file1.png "
            "--file file2.png --target local` from the seeded local repository. "
            "Failed: the command exited `0` and printed a success payload instead of a "
            "validation error."
        ),
        "```text",
        str(stdout),
        "```",
    ]


if __name__ == "__main__":
    unittest.main()
