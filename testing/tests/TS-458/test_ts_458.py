from __future__ import annotations

from pathlib import Path
import unittest

from testing.components.services.trackstate_cli_field_resolution_validator import (
    TrackStateCliFieldResolutionValidator,
)
from testing.core.config.trackstate_cli_field_resolution_config import (
    TrackStateCliFieldResolutionConfig,
)
from testing.core.models.cli_command_result import CliCommandResult
from testing.tests.support.trackstate_cli_field_resolution_probe_factory import (
    create_trackstate_cli_field_resolution_probe,
)


class TrackStateCliFieldResolutionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = TrackStateCliFieldResolutionConfig.from_env()
        self.validator = TrackStateCliFieldResolutionValidator(
            probe=create_trackstate_cli_field_resolution_probe(self.repository_root)
        )

    def test_update_field_prioritizes_exact_ids_and_rejects_ambiguous_names(
        self,
    ) -> None:
        observation = self.validator.validate(config=self.config).observation

        self.assertEqual(
            observation.exact_id.requested_command,
            (
                *self.config.requested_command_prefix,
                "--path",
                observation.repository_path,
                "--key",
                self.config.issue_key,
                "--field",
                self.config.exact_field_identifier,
                "--value",
                str(self.config.exact_field_value),
            ),
            "Precondition failed: TS-458 did not execute the expected exact-id "
            "command against the disposable Local Git repository.\n"
            f"Requested command: {observation.exact_id.requested_command_text}",
        )
        self.assertEqual(
            observation.display_name.requested_command,
            (
                *self.config.requested_command_prefix,
                "--path",
                observation.repository_path,
                "--key",
                self.config.issue_key,
                "--field",
                self.config.display_name_identifier,
                "--value",
                str(self.config.display_name_value),
            ),
            "Precondition failed: TS-458 did not execute the expected display-name "
            "command against the disposable Local Git repository.\n"
            f"Requested command: {observation.display_name.requested_command_text}",
        )
        self.assertEqual(
            observation.ambiguous_name.requested_command,
            (
                *self.config.requested_command_prefix,
                "--path",
                observation.repository_path,
                "--key",
                self.config.issue_key,
                "--field",
                self.config.ambiguous_field_identifier,
                "--value",
                str(self.config.ambiguous_field_value),
            ),
            "Precondition failed: TS-458 did not execute the expected ambiguity "
            "command against the disposable Local Git repository.\n"
            f"Requested command: {observation.ambiguous_name.requested_command_text}",
        )

        exact_payload = self._assert_successful_envelope(
            result=observation.exact_id.result,
            failure_prefix="Step 1 failed",
        )
        exact_data = exact_payload["data"]
        assert isinstance(exact_data, dict)
        self.assertEqual(
            exact_data["command"],
            self.config.expected_command_name,
            "Step 1 failed: the exact-id command did not identify itself as "
            "`ticket-update-field`.\n"
            f"Observed payload: {exact_payload}",
        )
        self.assertEqual(
            exact_data["operation"],
            "update-fields",
            "Step 1 failed: the exact-id command did not report the shared "
            "update-fields mutation.\n"
            f"Observed payload: {exact_payload}",
        )
        exact_field = exact_data["field"]
        self.assertIsInstance(
            exact_field,
            dict,
            "Step 1 failed: the success envelope did not include resolved field "
            "metadata.\n"
            f"Observed payload: {exact_payload}",
        )
        assert isinstance(exact_field, dict)
        self.assertEqual(
            exact_field["requested"],
            self.config.exact_field_identifier,
            "Step 1 failed: the visible CLI output did not preserve the requested "
            "exact field identifier.\n"
            f"Observed field payload: {exact_field}",
        )
        self.assertEqual(
            exact_field["resolved"],
            self.config.exact_field_identifier,
            "Expected result failed: the exact customfield id did not resolve to "
            "itself.\n"
            f"Observed field payload: {exact_field}",
        )
        exact_issue = self._assert_issue_payload(
            payload=exact_payload,
            failure_prefix="Step 1 failed",
        )
        self.assertEqual(
            exact_issue["customFields"],
            {
                "customfield_10016": 8,
                "storyPoints": 2,
                "velocityPoints": 13,
                "effortPoints": 21,
            },
            "Step 1 failed: the exact-id command did not update only the targeted "
            "custom field.\n"
            f"Observed issue: {exact_issue}",
        )

        display_payload = self._assert_successful_envelope(
            result=observation.display_name.result,
            failure_prefix="Step 2 failed",
        )
        display_data = display_payload["data"]
        assert isinstance(display_data, dict)
        self.assertEqual(
            display_data["command"],
            self.config.expected_command_name,
            "Step 2 failed: the display-name command did not identify itself as "
            "`ticket-update-field`.\n"
            f"Observed payload: {display_payload}",
        )
        self.assertEqual(
            display_data["operation"],
            "update-fields",
            "Step 2 failed: the display-name command did not report the shared "
            "update-fields mutation.\n"
            f"Observed payload: {display_payload}",
        )
        display_field = display_data["field"]
        self.assertIsInstance(
            display_field,
            dict,
            "Step 2 failed: the success envelope did not include resolved field "
            "metadata.\n"
            f"Observed payload: {display_payload}",
        )
        assert isinstance(display_field, dict)
        self.assertEqual(
            display_field["requested"],
            self.config.display_name_identifier,
            "Step 2 failed: the visible CLI output did not preserve the requested "
            "display name.\n"
            f"Observed field payload: {display_field}",
        )
        self.assertEqual(
            display_field["resolved"],
            "storyPoints",
            "Expected result failed: the display name did not resolve to the "
            "configured canonical field id.\n"
            f"Observed field payload: {display_field}",
        )
        display_issue = self._assert_issue_payload(
            payload=display_payload,
            failure_prefix="Step 2 failed",
        )
        self.assertEqual(
            display_issue["customFields"],
            {
                "customfield_10016": 8,
                "storyPoints": 5,
                "velocityPoints": 13,
                "effortPoints": 21,
            },
            "Step 2 failed: the display-name command did not update only the "
            "intended Story Points field while preserving the exact-id update.\n"
            f"Observed issue: {display_issue}",
        )

        error_payload = self._assert_error_envelope(
            result=observation.ambiguous_name.result,
            failure_prefix="Step 4 failed",
        )
        error = error_payload["error"]
        assert isinstance(error, dict)
        self.assertEqual(
            error["code"],
            "AMBIGUOUS_FIELD",
            "Step 4 failed: the ambiguity command did not return the machine-readable "
            "AMBIGUOUS_FIELD code.\n"
            f"Observed payload: {error_payload}",
        )
        self.assertEqual(
            error["category"],
            "validation",
            "Step 4 failed: the ambiguity command did not classify the failure as a "
            "validation error.\n"
            f"Observed payload: {error_payload}",
        )
        self.assertEqual(
            error["exitCode"],
            2,
            "Step 4 failed: the ambiguity command did not return the expected "
            "validation exit code.\n"
            f"Observed payload: {error_payload}",
        )
        self.assertEqual(
            error["message"],
            'Field "Points" matches multiple configured fields. Use a canonical id instead.',
            "Step 4 failed: the ambiguity message was not explicit enough for a "
            "user to understand the resolution guidance.\n"
            f"Observed payload: {error_payload}",
        )
        details = error["details"]
        self.assertIsInstance(
            details,
            dict,
            "Step 4 failed: the ambiguity error did not include machine-readable "
            "details.\n"
            f"Observed payload: {error_payload}",
        )
        assert isinstance(details, dict)
        self.assertEqual(
            details["field"],
            self.config.ambiguous_field_identifier,
            "Step 4 failed: the ambiguity error did not echo the requested field "
            "token.\n"
            f"Observed details: {details}",
        )
        self.assertEqual(
            details["matches"],
            list(self.config.ambiguous_field_ids),
            "Expected result failed: the ambiguity error did not list the exact "
            "conflicting canonical field ids.\n"
            f"Observed details: {details}",
        )

        self.assertEqual(
            observation.after_exact_commit_count,
            observation.initial_commit_count + 1,
            "Step 1 failed: the exact-id command did not persist as exactly one new "
            "Git commit.\n"
            f"Initial commit count: {observation.initial_commit_count}\n"
            f"After exact-id: {observation.after_exact_commit_count}",
        )
        self.assertEqual(
            observation.after_display_commit_count,
            observation.initial_commit_count + 2,
            "Step 2 failed: the display-name command did not persist as exactly one "
            "additional Git commit.\n"
            f"Initial commit count: {observation.initial_commit_count}\n"
            f"After display-name: {observation.after_display_commit_count}",
        )
        self.assertEqual(
            observation.final_commit_count,
            observation.before_ambiguous_commit_count,
            "Step 4 failed: the ambiguous field command should not have created a new "
            "Git commit after the conflict setup commit.\n"
            f"Before ambiguity: {observation.before_ambiguous_commit_count}\n"
            f"Final commit count: {observation.final_commit_count}",
        )
        self.assertNotEqual(
            observation.initial_head_revision,
            observation.after_exact_head_revision,
            "Step 1 failed: repository HEAD did not change after the exact-id update.",
        )
        self.assertNotEqual(
            observation.after_exact_head_revision,
            observation.after_display_head_revision,
            "Step 2 failed: repository HEAD did not change after the display-name "
            "update.",
        )
        self.assertEqual(
            observation.final_head_revision,
            observation.before_ambiguous_head_revision,
            "Step 4 failed: the ambiguous field command unexpectedly changed the "
            "repository HEAD.\n"
            f"Before ambiguity: {observation.before_ambiguous_head_revision}\n"
            f"Final HEAD: {observation.final_head_revision}",
        )
        self.assertEqual(
            observation.after_display_latest_commit_subject,
            self.config.expected_commit_subject,
            "Expected result failed: the display-name update did not persist as the "
            "expected field update commit.\n"
            f"Observed commit subject: {observation.after_display_latest_commit_subject}",
        )
        self.assertFalse(
            observation.git_status.strip(),
            "Expected result failed: the repository worktree was not clean after the "
            "field-resolution scenario completed.\n"
            f"git status --short:\n{observation.git_status}",
        )

        main_file = observation.main_file_content
        for fragment in (
            'customFields: {"customfield_10016":8',
            '"storyPoints":5',
            '"velocityPoints":13',
            '"effortPoints":21',
            "# Summary",
            self.config.initial_summary,
        ):
            self.assertIn(
                fragment,
                main_file,
                "Human-style verification failed: the visible issue markdown did not "
                "show the expected final state after the two successful updates.\n"
                f"Missing fragment: {fragment}\n"
                f"Observed {observation.main_file_relative_path} contents:\n{main_file}",
            )
        self.assertNotIn(
            '"velocityPoints":3',
            main_file,
            "Step 4 failed: the ambiguous field command unexpectedly mutated one of "
            "the conflicting fields in main.md.\n"
            f"Observed {observation.main_file_relative_path} contents:\n{main_file}",
        )
        self.assertNotIn(
            '"effortPoints":3',
            main_file,
            "Step 4 failed: the ambiguous field command unexpectedly mutated one of "
            "the conflicting fields in main.md.\n"
            f"Observed {observation.main_file_relative_path} contents:\n{main_file}",
        )

        for fragment in (
            '"requested": "customfield_10016"',
            '"resolved": "customfield_10016"',
            '"customfield_10016": 8',
        ):
            self.assertIn(
                fragment,
                observation.exact_id.result.stdout,
                "Human-style verification failed: the exact-id CLI output did not "
                "visibly show the successful field update.\n"
                f"Missing fragment: {fragment}\n"
                f"Observed stdout:\n{observation.exact_id.result.stdout}",
            )
        for fragment in (
            '"requested": "Story Points"',
            '"resolved": "storyPoints"',
            '"storyPoints": 5',
        ):
            self.assertIn(
                fragment,
                observation.display_name.result.stdout,
                "Human-style verification failed: the display-name CLI output did not "
                "visibly show the resolved Story Points update.\n"
                f"Missing fragment: {fragment}\n"
                f"Observed stdout:\n{observation.display_name.result.stdout}",
            )
        for fragment in (
            '"code": "AMBIGUOUS_FIELD"',
            '"field": "Points"',
            '"velocityPoints"',
            '"effortPoints"',
        ):
            self.assertIn(
                fragment,
                observation.ambiguous_name.result.stdout,
                "Human-style verification failed: the ambiguous-name CLI output did "
                "not visibly show the machine-readable failure details.\n"
                f"Missing fragment: {fragment}\n"
                f"Observed stdout:\n{observation.ambiguous_name.result.stdout}",
            )

    def _assert_successful_envelope(
        self,
        *,
        result: CliCommandResult,
        failure_prefix: str,
    ) -> dict[str, object]:
        self.assertTrue(
            result.succeeded,
            f"{failure_prefix}: the field update command did not complete "
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
        self.assertIn(
            "data",
            payload,
            f"{failure_prefix}: the success envelope did not include a data payload.\n"
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
            key for key in self.config.required_success_data_keys if key not in data
        ]
        self.assertFalse(
            missing_data_keys,
            f"{failure_prefix}: the success envelope was missing required data keys.\n"
            f"Missing keys: {missing_data_keys}\n"
            f"Observed payload: {payload}",
        )
        return payload

    def _assert_error_envelope(
        self,
        *,
        result: CliCommandResult,
        failure_prefix: str,
    ) -> dict[str, object]:
        self.assertFalse(
            result.succeeded,
            f"{failure_prefix}: the ambiguous field command unexpectedly succeeded.\n"
            f"Executed command: {result.command_text}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}",
        )
        payload = result.json_payload
        self.assertIsInstance(
            payload,
            dict,
            f"{failure_prefix}: the CLI did not return a JSON error envelope.\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}",
        )
        assert isinstance(payload, dict)
        missing_top_level_keys = [
            key for key in self.config.required_top_level_keys if key not in payload
        ]
        self.assertFalse(
            missing_top_level_keys,
            f"{failure_prefix}: the error envelope was missing required top-level "
            "keys.\n"
            f"Missing keys: {missing_top_level_keys}\n"
            f"Observed payload: {payload}",
        )
        self.assertFalse(
            payload["ok"],
            f"{failure_prefix}: the envelope reported a success result for an "
            "ambiguous field.\n"
            f"Observed payload: {payload}",
        )
        self.assertIn(
            "error",
            payload,
            f"{failure_prefix}: the error envelope did not include an error object.\n"
            f"Observed payload: {payload}",
        )
        error = payload["error"]
        self.assertIsInstance(
            error,
            dict,
            f"{failure_prefix}: the error payload was not an object.\n"
            f"Observed payload: {payload}",
        )
        assert isinstance(error, dict)
        missing_error_keys = [
            key for key in self.config.required_error_keys if key not in error
        ]
        self.assertFalse(
            missing_error_keys,
            f"{failure_prefix}: the error envelope was missing required error keys.\n"
            f"Missing keys: {missing_error_keys}\n"
            f"Observed payload: {payload}",
        )
        return payload

    def _assert_issue_payload(
        self,
        *,
        payload: dict[str, object],
        failure_prefix: str,
    ) -> dict[str, object]:
        data = payload["data"]
        assert isinstance(data, dict)
        issue = data["issue"]
        self.assertIsInstance(
            issue,
            dict,
            f"{failure_prefix}: the updated issue payload was not encoded as an "
            "object.\n"
            f"Observed payload: {payload}",
        )
        assert isinstance(issue, dict)
        self.assertEqual(
            issue["storagePath"],
            "TS/TS-1/main.md",
            f"{failure_prefix}: the returned issue payload did not point to the "
            "canonical markdown file.\n"
            f"Observed issue: {issue}",
        )
        return issue


if __name__ == "__main__":
    unittest.main()
