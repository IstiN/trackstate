from __future__ import annotations

from pathlib import Path
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


class CliAttachmentUploadMultiFileBoundaryTest(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = TrackStateCliAttachmentUploadBoundaryConfig.from_defaults()
        self.validator = TrackStateCliAttachmentUploadBoundaryValidator(
            probe=create_trackstate_cli_attachment_upload_boundary_probe(
                self.repository_root
            )
        )

    def test_attachment_upload_rejects_multiple_file_flags(self) -> None:
        result = self.validator.validate(config=self.config)
        self._assert_exact_command(result.observation)
        self._assert_initial_fixture(result.initial_state)

        failures: list[str] = []
        failures.extend(self._collect_runtime_failures(result.observation))
        failures.extend(
            self._collect_repository_side_effect_failures(
                initial_state=result.initial_state,
                final_state=result.final_state,
            )
        )
        self.assertFalse(failures, "\n\n".join(failures))

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

        if observation.result.exit_code != self.config.expected_exit_code:
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
            return failures

        if not isinstance(payload, dict):
            failures.append(
                "Step 1 failed: the duplicate-file CLI invocation did not return a "
                "machine-readable JSON envelope.\n"
                f"Observed stdout:\n{observation.result.stdout}\n"
                f"Observed stderr:\n{observation.result.stderr}"
            )
            return failures

        if payload.get("ok") is not False:
            failures.append(
                "Expected result failed: the duplicate-file invocation did not return "
                "`ok: false`.\n"
                f"Observed payload: {payload}"
            )

        error = payload.get("error")
        if not isinstance(error, dict):
            failures.append(
                "Step 1 failed: the failure envelope did not include an `error` object.\n"
                f"Observed payload: {payload}"
            )
            return failures

        if error.get("category") != self.config.expected_error_category:
            failures.append(
                "Expected result failed: the duplicate-file invocation did not classify "
                "the outcome as a validation error.\n"
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


if __name__ == "__main__":
    unittest.main()
