from __future__ import annotations

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


class TrackStateCliCommentCreationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = TrackStateCliCommentCreationConfig.from_env()
        self.validator = TrackStateCliCommentCreationValidator(
            probe=create_trackstate_cli_comment_creation_probe(self.repository_root)
        )

    def test_duplicate_comment_posts_create_two_files_and_report_revisions(
        self,
    ) -> None:
        observation = self.validator.validate(config=self.config).observation

        self.assertEqual(
            observation.requested_command,
            (
                *self.config.requested_command_prefix,
                "--path",
                observation.repository_path,
                "--key",
                self.config.issue_key,
                "--body",
                self.config.comment_body,
            ),
            "Precondition failed: TS-462 did not execute the expected live comment "
            "command against the disposable Local Git repository.\n"
            f"Requested command: {observation.requested_command_text}",
        )
        first_payload = self._assert_successful_envelope(
            result=observation.first_result,
            failure_prefix="Step 1 failed",
        )
        second_payload = self._assert_successful_envelope(
            result=observation.second_result,
            failure_prefix="Step 2 failed",
        )

        self.assertEqual(
            tuple(file.relative_path for file in observation.comment_files),
            (
                "TS/TS-1/comments/0001.md",
                "TS/TS-1/comments/0002.md",
            ),
            "Step 3 failed: repeating the exact same comment command did not create "
            "two separate markdown files in the issue comments folder.\n"
            f"Observed files: {[file.relative_path for file in observation.comment_files]}\n"
            f"Repository path: {observation.repository_path}\n"
            f"git status --short:\n{observation.git_status}",
        )
        for expected_path, file_observation in zip(
            ("TS/TS-1/comments/0001.md", "TS/TS-1/comments/0002.md"),
            observation.comment_files,
        ):
            self.assertIn(
                self.config.comment_body,
                file_observation.content,
                "Human-style verification failed: the visible markdown file did not "
                "contain the requested comment text.\n"
                f"File: {expected_path}\n"
                f"Observed content:\n{file_observation.content}",
            )
            self.assertIn(
                'author: "ts462@example.com"',
                file_observation.content,
                "Human-style verification failed: the visible markdown file did not "
                "show the expected author metadata.\n"
                f"File: {expected_path}\n"
                f"Observed content:\n{file_observation.content}",
            )

        first_comment = self._assert_comment_payload(
            payload=first_payload,
            expected_comment_id=self.config.expected_comment_ids[0],
            failure_prefix="Step 1 failed",
        )
        second_comment = self._assert_comment_payload(
            payload=second_payload,
            expected_comment_id=self.config.expected_comment_ids[1],
            failure_prefix="Step 2 failed",
        )
        for stdout, expected_comment_id in (
            (observation.first_result.stdout, self.config.expected_comment_ids[0]),
            (observation.second_result.stdout, self.config.expected_comment_ids[1]),
        ):
            self.assertIn(
                f'"id": "{expected_comment_id}"',
                stdout,
                "Human-style verification failed: the CLI stdout did not visibly show "
                "the created comment id.\n"
                f"Expected id: {expected_comment_id}\n"
                f"Observed stdout:\n{stdout}",
            )
            self.assertIn(
                f'"storagePath": "TS/TS-1/comments/{expected_comment_id}.md"',
                stdout,
                "Human-style verification failed: the CLI stdout did not visibly show "
                "the created comment storage path.\n"
                f"Expected id: {expected_comment_id}\n"
                f"Observed stdout:\n{stdout}",
            )

        self.assertNotEqual(
            first_comment["id"],
            second_comment["id"],
            "Expected result failed: posting the same comment body twice reused the "
            "same comment id instead of creating a second record.\n"
            f"First comment: {first_comment}\n"
            f"Second comment: {second_comment}",
        )

        self._assert_non_empty_revision(
            payload=first_payload,
            failure_prefix="Expected result failed after step 1",
        )
        self._assert_non_empty_revision(
            payload=second_payload,
            failure_prefix="Expected result failed after step 2",
        )

    def _assert_successful_envelope(
        self,
        *,
        result: CliCommandResult,
        failure_prefix: str,
    ) -> dict[str, object]:
        self.assertTrue(
            result.succeeded,
            f"{failure_prefix}: the comment command did not complete successfully.\n"
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
            self.config.comment_body,
            f"{failure_prefix}: the returned comment metadata did not preserve the "
            "requested comment body.\n"
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
    ) -> None:
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


if __name__ == "__main__":
    unittest.main()
