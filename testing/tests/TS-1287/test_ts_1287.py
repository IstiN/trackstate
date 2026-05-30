from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import unittest

from testing.components.services.trackstate_cli_comment_creation_validator import (
    TrackStateCliCommentCreationValidator,
)
from testing.core.config.trackstate_cli_comment_creation_config import (
    TrackStateCliCommentCreationConfig,
)
from testing.core.models.cli_command_result import CliCommandResult
from testing.tests.support.trackstate_cli_comment_creation_probe_factory import (
    create_trackstate_cli_comment_creation_probe,
)


class TrackStateCliCommentRevisionEnvelopeTest(unittest.TestCase):
    def setUp(self) -> None:
        repository_root = Path(__file__).resolve().parents[3]
        base_config = TrackStateCliCommentCreationConfig.from_env()
        self.config = replace(
            base_config,
            comment_bodies=(
                "Regression test comment 1",
                "Regression test comment 2",
            ),
        )
        self.validator = TrackStateCliCommentCreationValidator(
            probe=create_trackstate_cli_comment_creation_probe(repository_root)
        )

    def test_ticket_comment_success_envelope_reports_head_revision(self) -> None:
        observation = self.validator.validate(config=self.config).observation

        expected_requested_commands = tuple(
            (
                *self.config.requested_command_prefix,
                "--path",
                observation.repository_path,
                "--key",
                self.config.issue_key,
                "--body",
                comment_body,
            )
            for comment_body in self.config.comment_bodies
        )
        self.assertEqual(
            observation.requested_commands,
            expected_requested_commands,
            "Precondition failed: TS-1287 did not execute the expected live ticket "
            "comment commands against the disposable Local Git repository.\n"
            f"Observed commands: {[' '.join(command) for command in observation.requested_commands]}",
        )

        first_payload = self._assert_successful_envelope(
            result=observation.first_result,
            failure_prefix="Step 2 failed",
        )
        second_payload = self._assert_successful_envelope(
            result=observation.second_result,
            failure_prefix="Step 4 failed",
        )

        expected_file_paths = (
            "TS/TS-1/comments/0001.md",
            "TS/TS-1/comments/0002.md",
        )
        self.assertEqual(
            tuple(file.relative_path for file in observation.comment_files),
            expected_file_paths,
            "Step 4 failed: the live commands did not create the expected comment "
            "markdown files.\n"
            f"Observed files: {[file.relative_path for file in observation.comment_files]}\n"
            f"Repository path: {observation.repository_path}\n"
            f"git status --short:\n{observation.git_status}",
        )

        for expected_path, file_observation, expected_body in zip(
            expected_file_paths,
            observation.comment_files,
            self.config.comment_bodies,
        ):
            self.assertIn(
                expected_body,
                file_observation.content,
                "Human-style verification failed: the saved markdown comment did not "
                "show the same body a user submitted through the CLI.\n"
                f"File: {expected_path}\n"
                f"Expected body: {expected_body}\n"
                f"Observed content:\n{file_observation.content}",
            )
            self.assertIn(
                'author: "ts462@example.com"',
                file_observation.content,
                "Human-style verification failed: the saved markdown comment did not "
                "show the expected visible author metadata.\n"
                f"File: {expected_path}\n"
                f"Observed content:\n{file_observation.content}",
            )

        first_comment = self._assert_comment_payload(
            payload=first_payload,
            expected_comment_id=self.config.expected_comment_ids[0],
            expected_body=self.config.comment_bodies[0],
            failure_prefix="Step 2 failed",
        )
        second_comment = self._assert_comment_payload(
            payload=second_payload,
            expected_comment_id=self.config.expected_comment_ids[1],
            expected_body=self.config.comment_bodies[1],
            failure_prefix="Step 4 failed",
        )

        self.assertNotEqual(
            first_comment["id"],
            second_comment["id"],
            "Expected result failed: the second comment write reused the first "
            "comment id instead of creating a new record.\n"
            f"First comment: {first_comment}\n"
            f"Second comment: {second_comment}",
        )

        self.assertNotEqual(
            observation.initial_head_revision,
            observation.first_head_revision,
            "Step 2 failed: the first comment write did not advance repository "
            "HEAD even though the CLI reported success.\n"
            f"Initial HEAD: {observation.initial_head_revision}\n"
            f"HEAD after step 2: {observation.first_head_revision}\n"
            f"Repository path: {observation.repository_path}",
        )
        self.assertNotEqual(
            observation.first_head_revision,
            observation.second_head_revision,
            "Step 4 failed: the second comment write did not advance repository "
            "HEAD even though the CLI reported success.\n"
            f"HEAD after step 2: {observation.first_head_revision}\n"
            f"HEAD after step 4: {observation.second_head_revision}\n"
            f"Repository path: {observation.repository_path}",
        )

        for step_number, payload, result, expected_revision, expected_body in (
            (
                2,
                first_payload,
                observation.first_result,
                observation.first_head_revision,
                self.config.comment_bodies[0],
            ),
            (
                4,
                second_payload,
                observation.second_result,
                observation.second_head_revision,
                self.config.comment_bodies[1],
            ),
        ):
            with self.subTest(step=step_number):
                revision = self._assert_non_empty_revision(
                    payload=payload,
                    failure_prefix=f"Expected result failed at step {step_number}",
                )
                self.assertEqual(
                    revision,
                    expected_revision,
                    f"Expected result failed at step {step_number}: the success "
                    "envelope revision did not match the repository HEAD SHA "
                    "created by the live write.\n"
                    f"Expected revision: {expected_revision}\n"
                    f"Observed revision: {revision}\n"
                    f"Observed payload: {payload}",
                )
                self.assertIn(
                    f'"revision": "{revision}"',
                    result.stdout,
                    f"Human-style verification failed at step {step_number}: the "
                    "visible CLI JSON output did not show the same revision users "
                    "would rely on.\n"
                    f"Expected revision: {revision}\n"
                    f"Observed stdout:\n{result.stdout}",
                )
                self.assertIn(
                    f'"body": "{expected_body}"',
                    result.stdout,
                    f"Human-style verification failed at step {step_number}: the "
                    "visible CLI JSON output did not show the submitted comment "
                    "body.\n"
                    f"Expected body: {expected_body}\n"
                    f"Observed stdout:\n{result.stdout}",
                )

    def _assert_successful_envelope(
        self,
        *,
        result: CliCommandResult,
        failure_prefix: str,
    ) -> dict[str, object]:
        self.assertTrue(
            result.succeeded,
            f"{failure_prefix}: the ticket comment command did not complete "
            "successfully.\n"
            f"Executed command: {result.command_text}\n"
            f"Exit code: {result.exit_code}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}",
        )
        payload = result.json_payload
        self.assertIsInstance(
            payload,
            dict,
            f"{failure_prefix}: the CLI did not return a JSON success envelope.\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}",
        )
        assert isinstance(payload, dict)
        missing_top_level_keys = [
            key for key in self.config.required_top_level_keys if key not in payload
        ]
        self.assertFalse(
            missing_top_level_keys,
            f"{failure_prefix}: the success envelope was missing required top-level "
            "keys.\n"
            f"Missing keys: {missing_top_level_keys}\n"
            f"Observed payload: {payload}",
        )
        self.assertTrue(
            payload["ok"],
            f"{failure_prefix}: the envelope reported a non-success result.\n"
            f"Observed payload: {payload}",
        )
        data = payload["data"]
        self.assertIsInstance(
            data,
            dict,
            f"{failure_prefix}: the envelope data payload was not an object.\n"
            f"Observed payload: {payload}",
        )
        assert isinstance(data, dict)
        missing_data_keys = [
            key for key in self.config.required_data_keys if key not in data
        ]
        self.assertFalse(
            missing_data_keys,
            f"{failure_prefix}: the envelope data object was missing required keys.\n"
            f"Missing keys: {missing_data_keys}\n"
            f"Observed payload: {payload}",
        )
        self.assertEqual(
            data["command"],
            "ticket-comment",
            f"{failure_prefix}: the envelope did not identify the comment command.\n"
            f"Observed payload: {payload}",
        )
        self.assertEqual(
            data["operation"],
            "comment",
            f"{failure_prefix}: the envelope did not identify the comment mutation "
            "operation.\n"
            f"Observed payload: {payload}",
        )
        return payload

    def _assert_comment_payload(
        self,
        *,
        payload: dict[str, object],
        expected_comment_id: str,
        expected_body: str,
        failure_prefix: str,
    ) -> dict[str, object]:
        data = payload["data"]
        assert isinstance(data, dict)
        comment = data["comment"]
        self.assertIsInstance(
            comment,
            dict,
            f"{failure_prefix}: the created comment metadata was not encoded as an "
            "object.\n"
            f"Observed payload: {payload}",
        )
        assert isinstance(comment, dict)
        self.assertEqual(
            comment["id"],
            expected_comment_id,
            f"{failure_prefix}: the command did not return the expected created "
            "comment id.\n"
            f"Observed comment: {comment}",
        )
        self.assertEqual(
            comment["body"],
            expected_body,
            f"{failure_prefix}: the returned comment metadata did not preserve the "
            "submitted comment body.\n"
            f"Observed comment: {comment}",
        )
        self.assertEqual(
            comment["storagePath"],
            f"TS/TS-1/comments/{expected_comment_id}.md",
            f"{failure_prefix}: the returned comment metadata did not point to the "
            "new comment file.\n"
            f"Observed comment: {comment}",
        )
        return comment

    def _assert_non_empty_revision(
        self,
        *,
        payload: dict[str, object],
        failure_prefix: str,
    ) -> str:
        data = payload["data"]
        assert isinstance(data, dict)
        revision = data["revision"]
        self.assertIsInstance(
            revision,
            str,
            f"{failure_prefix}: the success envelope did not include a repository "
            "revision string for the created comment.\n"
            f"Observed revision: {revision!r}\n"
            f"Observed payload: {payload}",
        )
        assert isinstance(revision, str)
        self.assertTrue(
            revision.strip(),
            f"{failure_prefix}: the success envelope reported an empty repository "
            "revision for the created comment.\n"
            f"Observed payload: {payload}",
        )
        return revision


if __name__ == "__main__":
    unittest.main()
