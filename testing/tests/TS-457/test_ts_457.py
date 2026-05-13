from __future__ import annotations

from pathlib import Path
import re
import unittest

from testing.components.services.trackstate_cli_create_native_hierarchy_validator import (
    TrackStateCliCreateNativeHierarchyValidator,
)
from testing.core.config.trackstate_cli_create_native_hierarchy_config import (
    TrackStateCliCreateNativeHierarchyConfig,
)
from testing.core.models.cli_command_result import CliCommandResult
from testing.tests.support.trackstate_cli_create_native_hierarchy_probe_factory import (
    create_trackstate_cli_create_native_hierarchy_probe,
)


class TrackStateCliCreateNativeHierarchyTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = TrackStateCliCreateNativeHierarchyConfig.from_env()
        self.validator = TrackStateCliCreateNativeHierarchyValidator(
            probe=create_trackstate_cli_create_native_hierarchy_probe(
                self.repository_root
            )
        )

    def test_create_accepts_native_hierarchy_flags_and_returns_canonical_envelope(
        self,
    ) -> None:
        observation = self.validator.validate(config=self.config).observation

        self.assertEqual(
            observation.requested_command,
            (*self.config.requested_command_prefix, "--path", observation.repository_path),
            "Precondition failed: TS-457 did not execute the expected live create "
            "command against the disposable Local Git repository.\n"
            f"Requested command: {observation.requested_command_text}",
        )

        payload = self._assert_successful_envelope(
            result=observation.result,
            failure_prefix="Step 1 failed",
        )

        target = payload["target"]
        self.assertIsInstance(
            target,
            dict,
            "Step 2 failed: the canonical envelope did not expose target metadata "
            "as an object.\n"
            f"Observed payload: {payload}",
        )
        assert isinstance(target, dict)
        missing_target_keys = [
            key for key in self.config.required_target_keys if key not in target
        ]
        self.assertFalse(
            missing_target_keys,
            "Step 2 failed: the target metadata was missing required keys.\n"
            f"Missing target keys: {missing_target_keys}\n"
            f"Observed target: {target}",
        )
        self.assertEqual(
            target["type"],
            "local",
            "Expected result failed: the create envelope did not report a local "
            "target.\n"
            f"Observed target: {target}",
        )
        self.assertEqual(
            target["value"],
            observation.repository_path,
            "Human-style verification failed: the visible target metadata did not "
            "show the repository path the user targeted.\n"
            f"Expected path: {observation.repository_path}\n"
            f"Observed target: {target}",
        )

        data = payload["data"]
        assert isinstance(data, dict)
        issue = data["issue"]
        self.assertIsInstance(
            issue,
            dict,
            "Step 2 failed: the canonical envelope did not include the created issue "
            "object.\n"
            f"Observed payload: {payload}",
        )
        assert isinstance(issue, dict)
        missing_issue_keys = [
            key for key in self.config.required_issue_keys if key not in issue
        ]
        self.assertFalse(
            missing_issue_keys,
            "Step 2 failed: the created issue payload was missing required keys.\n"
            f"Missing issue keys: {missing_issue_keys}\n"
            f"Observed issue: {issue}",
        )
        self.assertEqual(
            data["command"],
            self.config.expected_command_name,
            "Expected result failed: the success envelope did not identify the "
            "canonical create command.\n"
            f"Observed data: {data}",
        )
        self.assertEqual(
            data["operation"],
            "create",
            "Expected result failed: the create command did not report the create "
            "operation.\n"
            f"Observed data: {data}",
        )
        self.assertEqual(
            data["authSource"],
            "none",
            "Expected result failed: the local create flow should not require hosted "
            "authentication.\n"
            f"Observed data: {data}",
        )
        self.assertTrue(
            str(data["revision"]).strip(),
            "Expected result failed: the success envelope did not report a non-empty "
            "repository revision.\n"
            f"Observed data: {data}",
        )

        self.assertEqual(
            issue["key"],
            self.config.expected_issue_key,
            "Step 2 failed: the created issue payload reported an unexpected key.\n"
            f"Observed issue: {issue}",
        )
        self.assertEqual(
            issue["project"],
            self.config.project_key,
            "Expected result failed: the created issue payload reported the wrong "
            "project key.\n"
            f"Observed issue: {issue}",
        )
        self.assertEqual(
            issue["summary"],
            self.config.summary,
            "Step 2 failed: the created issue payload did not preserve the requested "
            "summary.\n"
            f"Observed issue: {issue}",
        )
        self.assertEqual(
            issue["description"],
            self.config.expected_description,
            "Expected result failed: the created issue payload did not return the "
            "default description the CLI writes for a new local issue.\n"
            f"Observed issue: {issue}",
        )
        self.assertEqual(
            issue["issueType"],
            self.config.expected_issue_type,
            "Step 2 failed: the created issue payload did not resolve Story to the "
            "canonical issue type id.\n"
            f"Observed issue: {issue}",
        )
        self.assertEqual(
            issue["status"],
            self.config.expected_status,
            "Expected result failed: the created issue payload did not use the "
            "default status.\n"
            f"Observed issue: {issue}",
        )
        self.assertEqual(
            issue["priority"],
            self.config.expected_priority,
            "Expected result failed: the created issue payload did not use the "
            "default priority.\n"
            f"Observed issue: {issue}",
        )
        self.assertEqual(
            issue["assignee"],
            self.config.expected_author_email,
            "Expected result failed: the created issue payload did not inherit the "
            "local Git identity as assignee.\n"
            f"Observed issue: {issue}",
        )
        self.assertEqual(
            issue["reporter"],
            self.config.expected_author_email,
            "Expected result failed: the created issue payload did not inherit the "
            "local Git identity as reporter.\n"
            f"Observed issue: {issue}",
        )
        self.assertEqual(
            issue["epic"],
            self.config.epic_key,
            "Step 2 failed: the created issue payload did not preserve the requested "
            "epic hierarchy.\n"
            f"Observed issue: {issue}",
        )
        self.assertEqual(
            issue["storagePath"],
            self.config.expected_storage_path,
            "Step 3 failed: the created issue payload did not point to the canonical "
            "epic-nested markdown file.\n"
            f"Observed issue: {issue}",
        )
        self.assertFalse(
            issue["archived"],
            "Expected result failed: the newly created issue was unexpectedly marked "
            "archived.\n"
            f"Observed issue: {issue}",
        )

        self.assertTrue(
            observation.created_issue_main_exists,
            "Step 3 failed: the repository did not physically create the new issue "
            "under the selected epic directory.\n"
            f"Expected file: {observation.created_issue_main_relative_path}\n"
            f"Observed entries under {self.config.project_key}/{self.config.epic_key}: "
            f"{observation.epic_directory_entries}",
        )
        created_issue_main = observation.created_issue_main_content
        self.assertIsNotNone(
            created_issue_main,
            "Step 3 failed: the created issue markdown file was not readable.\n"
            f"Expected file: {observation.created_issue_main_relative_path}",
        )
        assert created_issue_main is not None
        self.assertIn(
            'summary: "New Story"',
            created_issue_main,
            "Step 3 failed: the new issue markdown did not visibly show the requested "
            "summary.\n"
            f"Observed content:\n{created_issue_main}",
        )
        self.assertIn(
            "epic: EPIC-101",
            created_issue_main,
            "Step 3 failed: the new issue markdown did not visibly show the selected "
            "epic.\n"
            f"Observed content:\n{created_issue_main}",
        )
        self.assertIn(
            "# Summary",
            created_issue_main,
            "Human-style verification failed: the created issue markdown did not show "
            "the rendered summary section a user would read.\n"
            f"Observed content:\n{created_issue_main}",
        )
        self.assertIn(
            "New Story",
            created_issue_main,
            "Human-style verification failed: the created issue markdown did not show "
            "the visible summary text.\n"
            f"Observed content:\n{created_issue_main}",
        )

        issue_index_payload = observation.issue_index_payload
        self.assertIsInstance(
            issue_index_payload,
            list,
            "Expected result failed: the issue index was not updated as a JSON list.\n"
            f"Observed {observation.issue_index_relative_path}:\n"
            f"{observation.issue_index_content}",
        )
        assert isinstance(issue_index_payload, list)
        created_issue_entries = [
            entry
            for entry in issue_index_payload
            if isinstance(entry, dict) and entry.get("key") == self.config.expected_issue_key
        ]
        self.assertEqual(
            len(created_issue_entries),
            1,
            "Expected result failed: the issue index did not contain exactly one "
            "entry for the created issue.\n"
            f"Observed {observation.issue_index_relative_path}:\n"
            f"{observation.issue_index_content}",
        )
        created_issue_entry = created_issue_entries[0]
        self.assertEqual(
            created_issue_entry.get("epic"),
            self.config.epic_key,
            "Expected result failed: the issue index did not record the epic link "
            "for the created issue.\n"
            f"Observed entry: {created_issue_entry}",
        )
        self.assertEqual(
            created_issue_entry.get("path"),
            self.config.expected_storage_path,
            "Expected result failed: the issue index did not record the canonical "
            "epic-nested path for the created issue.\n"
            f"Observed entry: {created_issue_entry}",
        )

        for fragment in (
            '"ok": true',
            f'"command": "{self.config.expected_command_name}"',
            f'"summary": "{self.config.summary}"',
            f'"epic": "{self.config.epic_key}"',
            f'"storagePath": "{self.config.expected_storage_path}"',
        ):
            self.assertIn(
                fragment,
                observation.result.stdout,
                "Human-style verification failed: the visible CLI JSON response did "
                "not show the created issue details a user would inspect.\n"
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
            f"{failure_prefix}: the create command did not complete successfully.\n"
            f"Executed command: {result.command_text}\n"
            f"Exit code: {result.exit_code}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}",
        )
        payload = result.json_payload
        self.assertIsInstance(
            payload,
            dict,
            f"{failure_prefix}: the CLI did not return a canonical JSON success "
            f"envelope.\nstdout:\n{result.stdout}\n"
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
        self.assertEqual(
            payload["provider"],
            "local-git",
            f"{failure_prefix}: the envelope did not identify the Local Git provider.\n"
            f"Observed payload: {payload}",
        )
        self.assertEqual(
            payload["output"],
            "json",
            f"{failure_prefix}: the envelope did not report json output.\n"
            f"Observed payload: {payload}",
        )
        self.assertRegex(
            str(payload["schemaVersion"]),
            re.compile(r"^\d+$"),
            f"{failure_prefix}: schemaVersion was not a version-like value.\n"
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
