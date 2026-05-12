from __future__ import annotations

from pathlib import Path
import unittest

from testing.components.services.trackstate_cli_multi_field_update_validator import (
    TrackStateCliMultiFieldUpdateValidator,
)
from testing.core.config.trackstate_cli_multi_field_update_config import (
    TrackStateCliMultiFieldUpdateConfig,
)
from testing.core.models.cli_command_result import CliCommandResult
from testing.tests.support.trackstate_cli_multi_field_update_probe_factory import (
    create_trackstate_cli_multi_field_update_probe,
)


class TrackStateCliMultiFieldUpdateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = TrackStateCliMultiFieldUpdateConfig.from_env()
        self.validator = TrackStateCliMultiFieldUpdateValidator(
            probe=create_trackstate_cli_multi_field_update_probe(self.repository_root)
        )

    def test_multi_field_update_uses_one_success_envelope_and_one_commit(self) -> None:
        observation = self.validator.validate(config=self.config).observation

        self.assertEqual(
            observation.requested_command,
            (
                *self.config.requested_command_prefix,
                "--path",
                observation.repository_path,
                "--issueKey",
                self.config.issue_key,
                "--json",
                (
                    '{"fields":{"summary":"New Title","priority":{"name":"High"},'
                    '"labels":["bug","ai"],"assignee":{"name":"user1"}}}'
                ),
            ),
            "Precondition failed: TS-460 did not execute the expected multi-field "
            "update command against the disposable Local Git repository.\n"
            f"Requested command: {observation.requested_command_text}",
        )

        payload = self._assert_successful_envelope(
            result=observation.result,
            failure_prefix="Step 1 failed",
        )
        data = payload["data"]
        assert isinstance(data, dict)
        issue = data["issue"]
        self.assertIsInstance(
            issue,
            dict,
            "Step 2 failed: the success envelope did not include an updated issue "
            "object.\n"
            f"Observed payload: {payload}",
        )
        assert isinstance(issue, dict)

        self.assertEqual(
            data["command"],
            "jira-update-ticket",
            "Step 1 failed: the success envelope did not identify the canonical "
            "multi-field update command.\n"
            f"Observed payload: {payload}",
        )
        self.assertEqual(
            data["operation"],
            "update-fields",
            "Expected result failed: the update did not report the shared field "
            "mutation operation.\n"
            f"Observed payload: {payload}",
        )
        self.assertEqual(
            data["revision"],
            observation.final_head_revision,
            "Expected result failed: the reported revision did not match the final "
            "repository HEAD after the multi-field update.\n"
            f"Envelope revision: {data['revision']}\n"
            f"Final HEAD: {observation.final_head_revision}",
        )
        self.assertEqual(
            issue["summary"],
            self.config.updated_summary,
            "Step 2 failed: the returned issue payload did not preserve the updated "
            "summary.\n"
            f"Observed issue: {issue}",
        )
        self.assertEqual(
            issue["priority"],
            self.config.updated_priority_id,
            "Step 2 failed: the returned issue payload did not resolve the updated "
            "priority to the canonical id.\n"
            f"Observed issue: {issue}",
        )
        self.assertEqual(
            issue["assignee"],
            self.config.updated_assignee,
            "Step 2 failed: the returned issue payload did not preserve the updated "
            "assignee.\n"
            f"Observed issue: {issue}",
        )
        self.assertEqual(
            issue["labels"],
            list(self.config.updated_labels),
            "Step 2 failed: the returned issue payload did not preserve the updated "
            "labels.\n"
            f"Observed issue: {issue}",
        )
        self.assertEqual(
            issue["storagePath"],
            observation.main_file_relative_path,
            "Expected result failed: the updated issue payload did not point to the "
            "canonical markdown file path.\n"
            f"Observed issue: {issue}",
        )

        self.assertEqual(
            observation.final_commit_count,
            observation.initial_commit_count + 1,
            "Step 3 failed: the multi-field update did not persist as exactly one new "
            "Git commit.\n"
            f"Initial commit count: {observation.initial_commit_count}\n"
            f"Final commit count: {observation.final_commit_count}\n"
            f"Latest commit subject: {observation.latest_commit_subject}",
        )
        self.assertNotEqual(
            observation.initial_head_revision,
            observation.final_head_revision,
            "Step 3 failed: the repository HEAD did not change after the multi-field "
            "update command completed.\n"
            f"Initial HEAD: {observation.initial_head_revision}\n"
            f"Final HEAD: {observation.final_head_revision}",
        )
        self.assertEqual(
            observation.latest_commit_subject,
            self.config.expected_commit_subject,
            "Expected result failed: the latest Git commit was not dedicated to the "
            "single issue field update.\n"
            f"Observed commit subject: {observation.latest_commit_subject}",
        )
        self.assertFalse(
            observation.git_status.strip(),
            "Expected result failed: the repository worktree was not clean after the "
            "update commit completed.\n"
            f"git status --short:\n{observation.git_status}",
        )

        main_file = observation.main_file_content
        self.assertIn(
            'summary: "New Title"',
            main_file,
            "Step 2 failed: main.md did not visibly show the updated summary.\n"
            f"Observed {observation.main_file_relative_path} contents:\n{main_file}",
        )
        self.assertIn(
            "priority: high",
            main_file,
            "Step 2 failed: main.md did not visibly show the updated canonical "
            "priority id.\n"
            f"Observed {observation.main_file_relative_path} contents:\n{main_file}",
        )
        self.assertIn(
            "assignee: user1",
            main_file,
            "Step 2 failed: main.md did not visibly show the updated assignee.\n"
            f"Observed {observation.main_file_relative_path} contents:\n{main_file}",
        )
        self.assertIn(
            'labels: ["bug","ai"]',
            main_file,
            "Step 2 failed: main.md did not visibly show the updated labels.\n"
            f"Observed {observation.main_file_relative_path} contents:\n{main_file}",
        )
        self.assertIn(
            "# Summary",
            main_file,
            "Human-style verification failed: the issue markdown did not show the "
            "rendered summary section after the update.\n"
            f"Observed {observation.main_file_relative_path} contents:\n{main_file}",
        )
        self.assertIn(
            self.config.updated_summary,
            main_file,
            "Human-style verification failed: the updated issue markdown did not show "
            "the new summary text in the rendered content.\n"
            f"Observed {observation.main_file_relative_path} contents:\n{main_file}",
        )
        self.assertNotIn(
            self.config.initial_summary,
            main_file,
            "Expected result failed: main.md still showed the original summary after "
            "the update completed.\n"
            f"Observed {observation.main_file_relative_path} contents:\n{main_file}",
        )
        self.assertNotIn(
            f"assignee: {self.config.initial_assignee}",
            main_file,
            "Expected result failed: main.md still showed the original assignee after "
            "the update completed.\n"
            f"Observed {observation.main_file_relative_path} contents:\n{main_file}",
        )

        for fragment in (
            '"command": "jira-update-ticket"',
            '"summary": "New Title"',
            '"priority": "high"',
            '"assignee": "user1"',
            '"labels": [',
            '"bug"',
            '"ai"',
            f'"revision": "{observation.final_head_revision}"',
        ):
            self.assertIn(
                fragment,
                observation.result.stdout,
                "Human-style verification failed: the visible CLI JSON response did "
                "not show the expected updated issue details.\n"
                f"Missing fragment: {fragment}\n"
                f"Observed stdout:\n{observation.result.stdout}",
            )

    def _assert_successful_envelope(
        self,
        *,
        result: CliCommandResult,
        failure_prefix: str,
    ) -> dict[str, object]:
        self.assertTrue(
            result.succeeded,
            f"{failure_prefix}: the multi-field update command did not complete "
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
            f"{failure_prefix}: the CLI did not return a single JSON success "
            "envelope.\n"
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
        return payload


if __name__ == "__main__":
    unittest.main()
