from __future__ import annotations

from pathlib import Path
import unittest

from testing.components.services.trackstate_cli_hierarchy_alias_validator import (
    TrackStateCliHierarchyAliasValidator,
)
from testing.core.config.trackstate_cli_hierarchy_alias_config import (
    TrackStateCliHierarchyAliasConfig,
)
from testing.core.models.cli_command_result import CliCommandResult
from testing.tests.support.trackstate_cli_hierarchy_alias_probe_factory import (
    create_trackstate_cli_hierarchy_alias_probe,
)


class TrackStateCliHierarchyAliasTest(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = TrackStateCliHierarchyAliasConfig.from_env()
        self.validator = TrackStateCliHierarchyAliasValidator(
            probe=create_trackstate_cli_hierarchy_alias_probe(self.repository_root)
        )

    def test_single_parent_input_maps_to_epic_or_parent_by_target_issue_type(self) -> None:
        observation = self.validator.validate(config=self.config).observation

        self.assertEqual(
            observation.create_observation.requested_command,
            self.config.requested_create_command,
            "Precondition failed: TS-459 did not execute the expected create command "
            "from the ticket scenario.\n"
            f"Observed command: {observation.create_observation.requested_command_text}",
        )
        self.assertEqual(
            observation.update_observation.requested_command,
            self.config.requested_update_command,
            "Precondition failed: TS-459 did not execute the expected update-parent "
            "command for the seeded hierarchy scenario.\n"
            f"Observed command: {observation.update_observation.requested_command_text}",
        )
        self.assertIsNotNone(
            observation.create_observation.compiled_binary_path,
            "Precondition failed: TS-459 must run a repository-local compiled binary so "
            "the seeded repository remains the current working directory.\n"
            f"Executed command: {observation.create_observation.executed_command_text}",
        )

        create_payload = self._assert_successful_envelope(
            result=observation.create_observation.result,
            failure_prefix="Step 1 failed",
        )
        create_data = create_payload["data"]
        assert isinstance(create_data, dict)
        created_issue = create_data["issue"]
        self.assertIsInstance(
            created_issue,
            dict,
            "Step 1 failed: the create response did not include the created issue "
            "object.\n"
            f"Observed payload: {create_payload}",
        )
        assert isinstance(created_issue, dict)

        self.assertEqual(
            create_data["command"],
            "jira-create-ticket-with-parent",
            "Step 1 failed: the create command did not report the Jira-compatible "
            "parent alias operation.\n"
            f"Observed payload: {create_payload}",
        )
        self.assertEqual(
            created_issue.get("epic"),
            self.config.epic_key,
            "Expected result failed: creating a story with `--parent EPIC-1` did not "
            "map the relationship to the canonical epic field.\n"
            f"Observed issue: {created_issue}",
        )
        self.assertIsNone(
            created_issue.get("parent"),
            "Expected result failed: creating a story under an Epic incorrectly stored "
            "the relationship as `parent`.\n"
            f"Observed issue: {created_issue}",
        )
        self.assertIsInstance(
            observation.created_issue_relative_path,
            str,
            "Step 1 failed: the create response did not expose a storagePath for the "
            "newly created issue.\n"
            f"Observed issue: {created_issue}",
        )
        assert isinstance(observation.created_issue_relative_path, str)
        self.assertEqual(
            created_issue.get("storagePath"),
            observation.created_issue_relative_path,
            "Expected result failed: the observed created issue path did not match the "
            "returned storagePath.\n"
            f"Observed issue: {created_issue}\n"
            f"Observed path: {observation.created_issue_relative_path}",
        )
        self.assertTrue(
            observation.created_issue_relative_path.startswith(
                f"{self.config.project_key}/{self.config.epic_key}/"
            ),
            "Step 1 failed: the created issue was not stored under the canonical epic "
            "directory.\n"
            f"Observed storagePath: {observation.created_issue_relative_path}",
        )
        self.assertTrue(
            observation.created_issue_relative_path.endswith("/main.md"),
            "Step 1 failed: the created issue storagePath did not point to main.md.\n"
            f"Observed storagePath: {observation.created_issue_relative_path}",
        )
        self.assertIsNotNone(
            observation.created_issue_content,
            "Step 1 failed: the created issue markdown file was not written at the "
            "reported storagePath.\n"
            f"Observed storagePath: {observation.created_issue_relative_path}",
        )
        assert observation.created_issue_content is not None
        self.assertIn(
            f"epic: {self.config.epic_key}",
            observation.created_issue_content,
            "Step 1 failed: the created issue markdown did not visibly store the "
            "canonical epic relationship.\n"
            f"Observed main.md:\n{observation.created_issue_content}",
        )
        self.assertIn(
            "parent: null",
            observation.created_issue_content,
            "Expected result failed: the created issue markdown did not preserve the "
            "unset canonical parent field as null after resolving the Epic alias.\n"
            f"Observed main.md:\n{observation.created_issue_content}",
        )
        self.assertIn(
            "# Summary",
            observation.created_issue_content,
            "Human-style verification failed: the created issue markdown did not show "
            "the visible summary section a user would read.\n"
            f"Observed main.md:\n{observation.created_issue_content}",
        )
        self.assertIn(
            self.config.created_summary,
            observation.created_issue_content,
            "Human-style verification failed: the created issue markdown did not show "
            "the requested summary text.\n"
            f"Observed main.md:\n{observation.created_issue_content}",
        )
        for fragment in (
            '"command": "jira-create-ticket-with-parent"',
            f'"epic": "{self.config.epic_key}"',
            '"parent": null',
        ):
            self.assertIn(
                fragment,
                observation.create_observation.result.stdout,
                "Human-style verification failed: the visible CLI response for the "
                "create command did not show the expected canonical hierarchy fields.\n"
                f"Missing fragment: {fragment}\n"
                f"Observed stdout:\n{observation.create_observation.result.stdout}",
            )

        update_payload = self._assert_successful_envelope(
            result=observation.update_observation.result,
            failure_prefix="Step 2 failed",
        )
        update_data = update_payload["data"]
        assert isinstance(update_data, dict)
        updated_issue = update_data["issue"]
        self.assertIsInstance(
            updated_issue,
            dict,
            "Step 2 failed: the update response did not include the moved issue "
            "object.\n"
            f"Observed payload: {update_payload}",
        )
        assert isinstance(updated_issue, dict)

        self.assertEqual(
            update_data["command"],
            "jira-update-ticket-parent",
            "Step 2 failed: the update command did not report the Jira-compatible "
            "parent reassignment alias.\n"
            f"Observed payload: {update_payload}",
        )
        self.assertEqual(
            updated_issue.get("parent"),
            self.config.target_story_key,
            "Expected result failed: reassigning `SUB-1` with `--parent STORY-1` did "
            "not map the relationship to the canonical parent field.\n"
            f"Observed issue: {updated_issue}",
        )
        self.assertEqual(
            updated_issue.get("epic"),
            self.config.epic_key,
            "Expected result failed: reassigning the sub-task did not preserve the epic "
            "inherited from the target story.\n"
            f"Observed issue: {updated_issue}",
        )
        self.assertEqual(
            updated_issue.get("storagePath"),
            observation.updated_subtask_relative_path,
            "Step 2 failed: the returned issue payload did not point at the canonical "
            "moved sub-task path.\n"
            f"Observed issue: {updated_issue}\n"
            f"Expected path: {observation.updated_subtask_relative_path}",
        )
        self.assertFalse(
            observation.original_subtask_exists_after_update,
            "Step 2 failed: the old sub-task path still existed after the parent "
            "reassignment completed.\n"
            f"Old path: {observation.original_subtask_relative_path}",
        )
        self.assertTrue(
            observation.updated_subtask_exists_after_update,
            "Step 2 failed: the sub-task was not moved into the target story "
            "directory.\n"
            f"Expected path: {observation.updated_subtask_relative_path}",
        )
        self.assertIsNotNone(
            observation.updated_subtask_content,
            "Step 2 failed: the moved sub-task markdown file was missing.\n"
            f"Expected path: {observation.updated_subtask_relative_path}",
        )
        assert observation.updated_subtask_content is not None
        self.assertIn(
            f"parent: {self.config.target_story_key}",
            observation.updated_subtask_content,
            "Step 2 failed: the moved sub-task markdown did not visibly show the new "
            "canonical parent.\n"
            f"Observed main.md:\n{observation.updated_subtask_content}",
        )
        self.assertIn(
            f"epic: {self.config.epic_key}",
            observation.updated_subtask_content,
            "Expected result failed: the moved sub-task markdown did not preserve the "
            "epic inherited from the target story.\n"
            f"Observed main.md:\n{observation.updated_subtask_content}",
        )
        self.assertIn(
            "# Summary",
            observation.updated_subtask_content,
            "Human-style verification failed: the moved sub-task markdown no longer "
            "contained the visible summary section a user would read.\n"
            f"Observed main.md:\n{observation.updated_subtask_content}",
        )
        for fragment in (
            '"command": "jira-update-ticket-parent"',
            f'"parent": "{self.config.target_story_key}"',
            f'"epic": "{self.config.epic_key}"',
            f'"storagePath": "{observation.updated_subtask_relative_path}"',
        ):
            self.assertIn(
                fragment,
                observation.update_observation.result.stdout,
                "Human-style verification failed: the visible CLI response for the "
                "parent update did not show the expected moved sub-task details.\n"
                f"Missing fragment: {fragment}\n"
                f"Observed stdout:\n{observation.update_observation.result.stdout}",
            )

        self.assertFalse(
            observation.final_git_status.strip(),
            "Expected result failed: the repository worktree was not clean after the "
            "two hierarchy mutations completed.\n"
            f"git status --short:\n{observation.final_git_status}",
        )

    def _assert_successful_envelope(
        self,
        *,
        result: CliCommandResult,
        failure_prefix: str,
    ) -> dict[str, object]:
        self.assertTrue(
            result.succeeded,
            f"{failure_prefix}: the CLI command did not complete successfully.\n"
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
            f"{failure_prefix}: the envelope reported a failed result.\n"
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
