from __future__ import annotations

from pathlib import Path
import unittest

from testing.components.services.trackstate_cli_links_json_hierarchy_exclusion_validator import (
    TrackStateCliLinksJsonHierarchyExclusionValidator,
)
from testing.core.config.trackstate_cli_links_json_hierarchy_exclusion_config import (
    TrackStateCliLinksJsonHierarchyExclusionConfig,
)
from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)
from testing.tests.support.trackstate_cli_links_json_hierarchy_exclusion_probe_factory import (
    create_trackstate_cli_links_json_hierarchy_exclusion_probe,
)


class TrackStateCliLinksJsonHierarchyExclusionTest(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = TrackStateCliLinksJsonHierarchyExclusionConfig.from_defaults()
        self.validator = TrackStateCliLinksJsonHierarchyExclusionValidator(
            probe=create_trackstate_cli_links_json_hierarchy_exclusion_probe(
                self.repository_root
            )
        )

    def test_hierarchy_relationships_are_excluded_from_links_json(self) -> None:
        observation = self.validator.validate(config=self.config).observation

        command_expectations = (
            (
                observation.parent_create_observation,
                self.config.parent_create_command,
                "Step 1 failed: TS-602 must execute the parent-story create command "
                "against the disposable Local Git repository.",
            ),
            (
                observation.child_create_observation,
                self.config.child_create_command,
                "Step 2 failed: TS-602 must execute the sub-task create command with "
                "the requested parent relationship.",
            ),
            (
                observation.unrelated_source_create_observation,
                self.config.unrelated_source_create_command,
                "Step 3 failed: TS-602 must create the unrelated source issue before "
                "linking it.",
            ),
            (
                observation.unrelated_target_create_observation,
                self.config.unrelated_target_create_command,
                "Step 3 failed: TS-602 must create the unrelated target issue before "
                "linking it.",
            ),
            (
                observation.link_observation,
                self.config.link_command,
                "Step 4 failed: TS-602 must execute the non-hierarchical link command "
                "from the seeded Local Git repository.",
            ),
        )
        for command_observation, expected_command_factory, failure_message in (
            command_expectations
        ):
            self._assert_command_was_executed_exactly(
                observation=command_observation,
                expected_command=expected_command_factory(
                    command_observation.repository_path
                ),
                precondition_message=failure_message,
            )

        parent_payload = self._assert_successful_envelope(
            observation=observation.parent_create_observation,
            failure_prefix="Step 1 failed",
        )
        parent_issue = parent_payload["data"]["issue"]
        self.assertEqual(
            parent_issue["key"],
            self.config.parent_issue_key,
            "Step 1 failed: the parent story create response returned an unexpected "
            "issue key.\n"
            f"Observed issue: {parent_issue}",
        )
        self.assertEqual(
            parent_issue["summary"],
            self.config.parent_summary,
            "Step 1 failed: the parent story create response did not preserve the "
            "requested summary.\n"
            f"Observed issue: {parent_issue}",
        )
        self.assertIsNone(
            parent_issue["parent"],
            "Expected result failed: the parent story unexpectedly carried a parent "
            "relationship.\n"
            f"Observed issue: {parent_issue}",
        )

        child_payload = self._assert_successful_envelope(
            observation=observation.child_create_observation,
            failure_prefix="Step 2 failed",
        )
        child_issue = child_payload["data"]["issue"]
        self.assertEqual(
            child_issue["key"],
            self.config.child_issue_key,
            "Step 2 failed: the sub-task create response returned an unexpected issue "
            "key.\n"
            f"Observed issue: {child_issue}",
        )
        self.assertEqual(
            child_issue["issueType"],
            "subtask",
            "Step 2 failed: the created child issue did not resolve to the canonical "
            "sub-task type.\n"
            f"Observed issue: {child_issue}",
        )
        self.assertEqual(
            child_issue["parent"],
            self.config.parent_issue_key,
            "Step 2 failed: the sub-task create response did not preserve the selected "
            "parent issue key.\n"
            f"Observed issue: {child_issue}",
        )
        self.assertEqual(
            child_issue["storagePath"],
            self.config.child_main_relative_path,
            "Step 2 failed: the created sub-task was not stored under the parent issue "
            "directory.\n"
            f"Observed issue: {child_issue}",
        )

        source_payload = self._assert_successful_envelope(
            observation=observation.unrelated_source_create_observation,
            failure_prefix="Step 3 failed",
        )
        source_issue = source_payload["data"]["issue"]
        self.assertEqual(
            source_issue["key"],
            self.config.unrelated_source_issue_key,
            "Step 3 failed: the unrelated source issue was not created with the "
            "expected key sequence.\n"
            f"Observed issue: {source_issue}",
        )
        self.assertIsNone(
            source_issue["parent"],
            "Step 3 failed: the unrelated source issue unexpectedly inherited a parent "
            "relationship.\n"
            f"Observed issue: {source_issue}",
        )

        target_payload = self._assert_successful_envelope(
            observation=observation.unrelated_target_create_observation,
            failure_prefix="Step 3 failed",
        )
        target_issue = target_payload["data"]["issue"]
        self.assertEqual(
            target_issue["key"],
            self.config.unrelated_target_issue_key,
            "Step 3 failed: the unrelated target issue was not created with the "
            "expected key sequence.\n"
            f"Observed issue: {target_issue}",
        )
        self.assertIsNone(
            target_issue["parent"],
            "Step 3 failed: the unrelated target issue unexpectedly inherited a parent "
            "relationship.\n"
            f"Observed issue: {target_issue}",
        )

        link_payload = self._assert_successful_envelope(
            observation=observation.link_observation,
            failure_prefix="Step 4 failed",
        )
        link_data = link_payload["data"]
        self.assertEqual(
            link_data["command"],
            "ticket-link",
            "Step 4 failed: the linking command did not report the canonical "
            "`ticket-link` operation.\n"
            f"Observed payload: {link_payload}",
        )
        self.assertEqual(
            link_data["link"],
            self.config.expected_link_payload,
            "Step 4 failed: the link response did not show the expected outward "
            "`blocks` relationship between the unrelated issues.\n"
            f"Observed payload: {link_payload}",
        )
        self.assertEqual(
            link_data["issue"]["key"],
            self.config.unrelated_source_issue_key,
            "Step 4 failed: the link response did not identify the unrelated source "
            "issue as the mutated issue.\n"
            f"Observed payload: {link_payload}",
        )

        links_payload = observation.links_json_payload
        self.assertIsInstance(
            links_payload,
            list,
            "Step 5 failed: the persisted links file was not a JSON array.\n"
            f"Path: {observation.links_json_relative_path}\n"
            f"Observed content:\n{observation.links_json_content}",
        )
        assert isinstance(links_payload, list)
        self.assertEqual(
            links_payload,
            [self.config.expected_link_payload],
            "Step 5 failed: `links.json` did not contain exactly the expected "
            "non-hierarchical link record.\n"
            f"Path: {observation.links_json_relative_path}\n"
            f"Observed payload: {links_payload}",
        )
        self.assertEqual(
            observation.links_json_files,
            (self.config.links_json_relative_path,),
            "Expected result failed: hierarchy creation produced extra `links.json` "
            "files instead of keeping only the unrelated issue link file.\n"
            f"Observed links.json files: {observation.links_json_files}",
        )
        self.assertNotIn(
            self.config.parent_issue_key,
            observation.links_json_content or "",
            "Expected result failed: the persisted non-hierarchical link file leaked "
            "the parent issue key from the hierarchy relationship.\n"
            f"Observed content:\n{observation.links_json_content}",
        )
        self.assertNotIn(
            self.config.child_issue_key,
            observation.links_json_content or "",
            "Expected result failed: the persisted non-hierarchical link file leaked "
            "the child issue key from the hierarchy relationship.\n"
            f"Observed content:\n{observation.links_json_content}",
        )

        self.assertIsNotNone(
            observation.child_main_content,
            "Step 5 failed: the created child issue markdown was not readable.\n"
            f"Expected path: {observation.child_main_relative_path}",
        )
        assert observation.child_main_content is not None
        self.assertIn(
            f"parent: {self.config.parent_issue_key}",
            observation.child_main_content,
            "Expected result failed: the child issue markdown did not visibly store "
            "the hierarchy relationship through the canonical parent field.\n"
            f"Observed main.md:\n{observation.child_main_content}",
        )
        self.assertIn(
            "# Summary",
            observation.child_main_content,
            "Human-style verification failed: the child issue markdown did not render "
            "the visible summary heading a user would read.\n"
            f"Observed main.md:\n{observation.child_main_content}",
        )
        self.assertIn(
            self.config.child_summary,
            observation.child_main_content,
            "Human-style verification failed: the child issue markdown did not render "
            "the requested summary text.\n"
            f"Observed main.md:\n{observation.child_main_content}",
        )

        issue_index_payload = observation.issue_index_payload
        self.assertIsInstance(
            issue_index_payload,
            list,
            "Expected result failed: the local issue index was not updated as a JSON "
            "array after the hierarchy and link mutations.\n"
            f"Path: {observation.issue_index_relative_path}\n"
            f"Observed content:\n{observation.issue_index_content}",
        )
        assert isinstance(issue_index_payload, list)
        index_by_key = {
            entry["key"]: entry
            for entry in issue_index_payload
            if isinstance(entry, dict) and "key" in entry
        }
        self.assertIn(
            self.config.parent_issue_key,
            index_by_key,
            "Expected result failed: the parent story was missing from the local issue "
            "index after creation.\n"
            f"Observed index payload: {issue_index_payload}",
        )
        self.assertIn(
            self.config.child_issue_key,
            index_by_key,
            "Expected result failed: the sub-task was missing from the local issue "
            "index after creation.\n"
            f"Observed index payload: {issue_index_payload}",
        )
        self.assertEqual(
            index_by_key[self.config.child_issue_key].get("parent"),
            self.config.parent_issue_key,
            "Expected result failed: the local issue index did not preserve the "
            "parent-child relationship.\n"
            f"Observed child index entry: {index_by_key[self.config.child_issue_key]}",
        )
        self.assertIn(
            self.config.child_issue_key,
            index_by_key[self.config.parent_issue_key].get("children", []),
            "Expected result failed: the local issue index did not list the sub-task "
            "under the parent story's children.\n"
            f"Observed parent index entry: {index_by_key[self.config.parent_issue_key]}",
        )

        for fragment in (
            '"command": "ticket-link"',
            f'"target": "{self.config.unrelated_target_issue_key}"',
            '"type": "blocks"',
        ):
            self.assertIn(
                fragment,
                observation.link_observation.result.stdout,
                "Human-style verification failed: the visible CLI response for the "
                "link command did not show the expected non-hierarchical link details.\n"
                f"Missing fragment: {fragment}\n"
                f"Observed stdout:\n{observation.link_observation.result.stdout}",
            )

    def _assert_command_was_executed_exactly(
        self,
        *,
        observation: TrackStateCliCommandObservation,
        expected_command: tuple[str, ...],
        precondition_message: str,
    ) -> None:
        self.assertEqual(
            observation.requested_command,
            expected_command,
            f"{precondition_message}\n"
            f"Expected command: {' '.join(expected_command)}\n"
            f"Observed command: {observation.requested_command_text}",
        )
        self.assertIsNotNone(
            observation.compiled_binary_path,
            f"{precondition_message}\n"
            "TS-602 must execute a repository-local compiled binary so the seeded "
            "repository remains isolated.\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Fallback reason: {observation.fallback_reason}",
        )
        self.assertEqual(
            observation.executed_command[0],
            observation.compiled_binary_path,
            f"{precondition_message}\n"
            "TS-602 did not run the compiled repository-local CLI binary.\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Compiled binary path: {observation.compiled_binary_path}",
        )

    def _assert_successful_envelope(
        self,
        *,
        observation: TrackStateCliCommandObservation,
        failure_prefix: str,
    ) -> dict[str, object]:
        self.assertEqual(
            observation.result.exit_code,
            0,
            f"{failure_prefix}: executing `{observation.requested_command_text}` did "
            "not complete successfully.\n"
            f"Repository path: {observation.repository_path}\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Observed exit code: {observation.result.exit_code}\n"
            f"stdout:\n{observation.result.stdout}\n"
            f"stderr:\n{observation.result.stderr}",
        )
        payload = observation.result.json_payload
        self.assertIsInstance(
            payload,
            dict,
            f"{failure_prefix}: `{observation.requested_command_text}` did not return "
            "a JSON object envelope.\n"
            f"stdout:\n{observation.result.stdout}\n"
            f"stderr:\n{observation.result.stderr}",
        )
        assert isinstance(payload, dict)
        self.assertTrue(
            payload.get("ok"),
            f"{failure_prefix}: `{observation.requested_command_text}` returned a "
            "non-success envelope.\n"
            f"Observed payload: {payload}",
        )
        data = payload.get("data")
        self.assertIsInstance(
            data,
            dict,
            f"{failure_prefix}: `{observation.requested_command_text}` did not include "
            "a data object.\n"
            f"Observed payload: {payload}",
        )
        return payload


if __name__ == "__main__":
    unittest.main()
