from __future__ import annotations

import json
import os
from pathlib import Path
import unittest

from testing.components.services.trackstate_cli_raw_jira_comment_response_validator import (
    TrackStateCliRawJiraCommentResponseValidator,
)
from testing.core.config.trackstate_cli_raw_jira_comment_response_config import (
    TrackStateCliRawJiraCommentResponseConfig,
)
from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)
from testing.core.models.trackstate_cli_raw_jira_comment_response_result import (
    TrackStateCliRawJiraCommentResponseValidationResult,
)
from testing.tests.support.trackstate_cli_raw_jira_comment_response_probe_factory import (
    create_trackstate_cli_raw_jira_comment_response_probe,
)


class CliCompatibilityRawJiraCommentResponseTest(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = TrackStateCliRawJiraCommentResponseConfig.from_defaults()
        self.validator = TrackStateCliRawJiraCommentResponseValidator(
            probe=create_trackstate_cli_raw_jira_comment_response_probe(
                self.repository_root
            )
        )

    def test_allowlisted_comment_request_returns_raw_jira_payload(self) -> None:
        result = self.validator.validate(config=self.config)
        self._write_result_if_requested(result)
        observation = result.observation

        self.assertEqual(
            observation.requested_command,
            self.config.ticket_command,
            "Precondition failed: TS-384 did not preserve the exact ticket command "
            "text.\n"
            f"Expected command: {' '.join(self.config.ticket_command)}\n"
            f"Observed command: {observation.requested_command_text}",
        )
        self.assertIsNotNone(
            observation.compiled_binary_path,
            "Precondition failed: TS-384 must execute a repository-local compiled "
            "binary so the seeded repository stays the current working directory.\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Fallback reason: {observation.fallback_reason}",
        )
        self.assertEqual(
            observation.executed_command[0],
            observation.compiled_binary_path,
            "Precondition failed: TS-384 did not run the compiled repository-local "
            "CLI binary.\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Compiled binary path: {observation.compiled_binary_path}",
        )
        self.assertEqual(
            observation.executed_command[1:],
            self.config.compatibility_command[1:],
            "Precondition failed: TS-384 did not execute the current `--request-path` "
            "equivalent of the ticket command.\n"
            f"Expected executed arguments: {self.config.compatibility_command[1:]}\n"
            f"Observed executed arguments: {observation.executed_command[1:]}",
        )
        self.assertEqual(
            observation.result.exit_code,
            0,
            "Step 1 failed: the allowlisted Jira comment request did not complete "
            "successfully.\n"
            f"Repository path: {observation.repository_path}\n"
            f"Requested command: {observation.requested_command_text}\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Fallback reason: {observation.fallback_reason}\n"
            f"stdout:\n{observation.result.stdout}\n"
            f"stderr:\n{observation.result.stderr}",
        )

        payload = observation.result.json_payload
        self.assertIsInstance(
            payload,
            dict,
            "Step 2 failed: the successful allowlisted comment request did not return "
            "a JSON object payload.\n"
            f"stdout:\n{observation.result.stdout}\n"
            f"stderr:\n{observation.result.stderr}",
        )
        assert isinstance(payload, dict)

        missing_root_keys = [
            key for key in self.config.required_root_keys if key not in payload
        ]
        self.assertFalse(
            missing_root_keys,
            "Step 2 failed: the raw Jira-compatible payload was missing required "
            "comment-list keys.\n"
            f"Missing keys: {missing_root_keys}\n"
            f"Observed payload: {payload}",
        )

        unexpected_wrapper_keys = [
            key for key in self.config.forbidden_root_keys if key in payload
        ]
        self.assertFalse(
            unexpected_wrapper_keys,
            "Expected result failed: the allowlisted response still exposed "
            "TrackState wrapper keys at the root.\n"
            f"Unexpected keys: {unexpected_wrapper_keys}\n"
            f"Observed payload: {payload}",
        )

        self.assertEqual(
            payload["startAt"],
            0,
            "Expected result failed: the raw Jira-compatible comment payload did "
            "not start at index 0 by default.\n"
            f"Observed payload: {payload}",
        )
        self.assertEqual(
            payload["maxResults"],
            self.config.expected_comment_count,
            "Expected result failed: the raw comment payload did not expose the full "
            "comment count as maxResults.\n"
            f"Observed payload: {payload}",
        )
        self.assertEqual(
            payload["total"],
            self.config.expected_comment_count,
            "Expected result failed: the raw comment payload did not report the "
            "seeded comment total.\n"
            f"Observed payload: {payload}",
        )

        comments = payload["comments"]
        self.assertIsInstance(
            comments,
            list,
            "Step 2 failed: the raw Jira-compatible payload did not expose a "
            "`comments` array.\n"
            f"Observed payload: {payload}",
        )
        assert isinstance(comments, list)
        self.assertEqual(
            len(comments),
            self.config.expected_comment_count,
            "Expected result failed: the raw Jira-compatible payload did not return "
            "the seeded comment rows.\n"
            f"Observed comments: {comments}",
        )

        observed_bodies: list[str | None] = []
        for index, expected_comment in enumerate(self.config.fixture_comments):
            comment = comments[index]
            self.assertIsInstance(
                comment,
                dict,
                "Step 2 failed: a raw Jira-compatible comment row was not encoded as "
                "an object.\n"
                f"Comment index: {index}\n"
                f"Observed comment: {comment}",
            )
            assert isinstance(comment, dict)
            author = comment.get("author")
            self.assertIsInstance(
                author,
                dict,
                "Expected result failed: the raw Jira-compatible comment row did not "
                "include an `author` object.\n"
                f"Comment index: {index}\n"
                f"Observed comment: {comment}",
            )
            assert isinstance(author, dict)
            observed_bodies.append(comment.get("body"))
            self.assertEqual(
                comment.get("id"),
                expected_comment.id,
                "Expected result failed: the raw Jira-compatible comment row did not "
                "preserve the seeded comment id.\n"
                f"Comment index: {index}\n"
                f"Observed comment: {comment}",
            )
            self.assertEqual(
                comment.get("body"),
                expected_comment.body,
                "Expected result failed: the raw Jira-compatible comment row did not "
                "preserve the seeded comment body text.\n"
                f"Comment index: {index}\n"
                f"Observed comment: {comment}",
            )
            self.assertEqual(
                author.get("displayName"),
                expected_comment.author,
                "Expected result failed: the raw Jira-compatible comment row did not "
                "preserve the visible author name.\n"
                f"Comment index: {index}\n"
                f"Observed comment: {comment}",
            )
            self.assertEqual(
                comment.get("created"),
                expected_comment.created,
                "Expected result failed: the raw Jira-compatible comment row did not "
                "preserve the created timestamp.\n"
                f"Comment index: {index}\n"
                f"Observed comment: {comment}",
            )
            self.assertEqual(
                comment.get("updated"),
                expected_comment.updated,
                "Expected result failed: the raw Jira-compatible comment row did not "
                "preserve the updated timestamp.\n"
                f"Comment index: {index}\n"
                f"Observed comment: {comment}",
            )
            self.assertEqual(
                comment.get("self"),
                f"/rest/api/2/issue/{self.config.issue_key}/comment/{expected_comment.id}",
                "Expected result failed: the raw Jira-compatible comment row did not "
                "expose the Jira-shaped comment self link.\n"
                f"Comment index: {index}\n"
                f"Observed comment: {comment}",
            )

        self.assertEqual(
            tuple(observed_bodies),
            tuple(comment.body for comment in self.config.fixture_comments),
            "Human-style verification failed: the terminal-visible comment rows did "
            "not stay in the seeded order.\n"
            f"Observed bodies: {observed_bodies}",
        )
        for fragment in self.config.required_stdout_fragments:
            self.assertIn(
                fragment,
                observation.result.stdout,
                "Human-style verification failed: the visible CLI output did not "
                "show the expected raw Jira comment payload.\n"
                f"Missing fragment: {fragment}\n"
                f"Observed stdout:\n{observation.result.stdout}",
            )
        for forbidden_fragment in ('"ok":', '"schemaVersion":', '"data":'):
            self.assertNotIn(
                forbidden_fragment,
                observation.result.stdout,
                "Human-style verification failed: the visible CLI output still "
                "showed TrackState envelope markers.\n"
                f"Forbidden fragment: {forbidden_fragment}\n"
                f"Observed stdout:\n{observation.result.stdout}",
            )

    def _write_result_if_requested(
        self,
        result: TrackStateCliRawJiraCommentResponseValidationResult,
    ) -> None:
        result_path = os.environ.get("TS384_RESULT_PATH")
        if not result_path:
            return

        observation = result.observation
        payload = {
            "ticket_command": list(observation.requested_command),
            "executed_command": list(observation.executed_command),
            "repository_path": observation.repository_path,
            "compiled_binary_path": observation.compiled_binary_path,
            "fallback_reason": observation.fallback_reason,
            "exit_code": observation.result.exit_code,
            "stdout": observation.result.stdout,
            "stderr": observation.result.stderr,
            "json_payload": observation.result.json_payload,
        }
        destination = Path(result_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    unittest.main()
