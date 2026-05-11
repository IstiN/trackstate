from __future__ import annotations

import unittest
from pathlib import Path

from testing.components.services.trackstate_cli_read_fields_validator import (
    TrackStateCliReadFieldsValidator,
)
from testing.core.config.trackstate_cli_read_fields_config import (
    TrackStateCliReadFieldsConfig,
)
from testing.tests.support.trackstate_cli_read_fields_probe_factory import (
    create_trackstate_cli_read_fields_probe,
)


class CliReadFieldsJiraSchemaConsistencyTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = TrackStateCliReadFieldsConfig.from_defaults()
        self.validator = TrackStateCliReadFieldsValidator(
            probe=create_trackstate_cli_read_fields_probe(self.repository_root)
        )

    def test_read_fields_returns_flat_jira_style_field_objects(self) -> None:
        observation = self.validator.validate(config=self.config).observation

        self.assertEqual(
            observation.requested_command,
            self.config.requested_command,
            "Precondition failed: TS-380 did not execute the exact ticket command.\n"
            f"Expected command: {' '.join(self.config.requested_command)}\n"
            f"Observed command: {observation.requested_command_text}",
        )
        self.assertIsNotNone(
            observation.compiled_binary_path,
            "Precondition failed: TS-380 must execute a repository-local compiled "
            "binary so the current working directory can remain the seeded "
            "repository.\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Fallback reason: {observation.fallback_reason}",
        )
        self.assertEqual(
            observation.executed_command[0],
            observation.compiled_binary_path,
            "Precondition failed: TS-380 did not run the compiled repository-local "
            "CLI binary.\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Compiled binary path: {observation.compiled_binary_path}",
        )
        self.assertEqual(
            observation.result.exit_code,
            0,
            "Step 1 failed: executing `trackstate read fields` did not succeed "
            "against the seeded Local Git repository.\n"
            f"Repository path: {observation.repository_path}\n"
            f"Requested command: {observation.requested_command_text}\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Fallback reason: {observation.fallback_reason}\n"
            f"Observed exit code: {observation.result.exit_code}\n"
            f"stdout:\n{observation.result.stdout}\n"
            f"stderr:\n{observation.result.stderr}",
        )
        self.assertTrue(
            observation.result.stdout.lstrip().startswith("["),
            "Human-style verification failed: the visible CLI output did not start "
            "with a JSON array.\n"
            f"Observed stdout:\n{observation.result.stdout}",
        )
        self.assertNotIn(
            '"data":',
            observation.result.stdout,
            "Expected result failed: `trackstate read fields` returned a wrapped "
            "response instead of the flat JSON array required by the ticket.\n"
            f"Observed stdout:\n{observation.result.stdout}",
        )
        self.assertIsInstance(
            observation.result.json_payload,
            list,
            "Step 2 failed: the CLI did not return a JSON array of field objects.\n"
            f"stdout:\n{observation.result.stdout}\n"
            f"stderr:\n{observation.result.stderr}",
        )
        payload = observation.result.json_payload
        assert isinstance(payload, list)
        self.assertGreaterEqual(
            len(payload),
            2,
            "Precondition failed: the seeded repository did not return the expected "
            "system and custom fields.\n"
            f"Observed payload: {payload}",
        )

        self.assertTrue(
            all(isinstance(item, dict) for item in payload),
            "Step 2 failed: the JSON array did not contain only field objects.\n"
            f"Observed payload: {payload}",
        )
        fields = [item for item in payload if isinstance(item, dict)]

        summary = next(
            (
                field
                for field in fields
                if field.get("id") == self.config.summary_field_id
            ),
            None,
        )
        self.assertIsNotNone(
            summary,
            "Step 2 failed: the `summary` field was missing from the JSON array.\n"
            f"Observed payload: {payload}",
        )
        assert isinstance(summary, dict)

        custom_field = next(
            (
                field
                for field in fields
                if field.get("id") == self.config.custom_field_id
            ),
            None,
        )
        self.assertIsNotNone(
            custom_field,
            "Precondition failed: the seeded repository did not return the custom "
            "field needed to verify Jira-compatible custom schema metadata.\n"
            f"Observed payload: {payload}",
        )
        assert isinstance(custom_field, dict)

        for field in (summary, custom_field):
            missing_keys = [
                key for key in self.config.required_field_keys if key not in field
            ]
            self.assertFalse(
                missing_keys,
                "Expected result failed: a returned field object was missing the "
                "required Jira-style keys.\n"
                f"Missing keys: {missing_keys}\n"
                f"Observed field: {field}",
            )
            self.assertIsInstance(
                field["custom"],
                bool,
                "Expected result failed: the `custom` property was not a boolean.\n"
                f"Observed field: {field}",
            )
            for forbidden_key in self.config.disallowed_trackstate_keys:
                self.assertNotIn(
                    forbidden_key,
                    field,
                    "Expected result failed: the field object still exposed raw "
                    "TrackState configuration keys instead of Jira-compatible schema "
                    "metadata.\n"
                    f"Forbidden key: {forbidden_key}\n"
                    f"Observed field: {field}",
                )

        summary_schema = summary.get("schema")
        self.assertIsInstance(
            summary_schema,
            dict,
            "Expected result failed: the `summary` field did not expose a schema "
            "object.\n"
            f"Observed field: {summary}",
        )
        assert isinstance(summary_schema, dict)
        self.assertEqual(
            summary.get("name"),
            self.config.summary_field_name,
            "Expected result failed: the `summary` field name changed.\n"
            f"Observed field: {summary}",
        )
        self.assertEqual(
            summary.get("key"),
            self.config.summary_field_id,
            "Expected result failed: the `summary` field key no longer matches its "
            "Jira identifier.\n"
            f"Observed field: {summary}",
        )
        self.assertFalse(
            summary.get("custom"),
            "Expected result failed: the system `summary` field was incorrectly "
            "flagged as custom.\n"
            f"Observed field: {summary}",
        )
        self.assertEqual(
            summary_schema.get("type"),
            self.config.summary_schema_type,
            "Expected result failed: the `summary` field schema did not expose the "
            "expected Jira type.\n"
            f"Observed field: {summary}",
        )
        self.assertEqual(
            summary_schema.get("system"),
            self.config.summary_field_id,
            "Expected result failed: the `summary` field schema did not expose the "
            "expected Jira system identifier.\n"
            f"Observed field: {summary}",
        )
        self.assertNotIn(
            "custom",
            summary_schema,
            "Expected result failed: the `summary` field schema incorrectly exposed "
            "custom metadata.\n"
            f"Observed field: {summary}",
        )

        custom_schema = custom_field.get("schema")
        self.assertIsInstance(
            custom_schema,
            dict,
            "Expected result failed: the custom field did not expose a schema object.\n"
            f"Observed field: {custom_field}",
        )
        assert isinstance(custom_schema, dict)
        self.assertEqual(
            custom_field.get("name"),
            self.config.custom_field_name,
            "Expected result failed: the custom field name changed.\n"
            f"Observed field: {custom_field}",
        )
        self.assertTrue(
            custom_field.get("custom"),
            "Expected result failed: the custom field was not marked as custom.\n"
            f"Observed field: {custom_field}",
        )
        self.assertEqual(
            custom_schema.get("type"),
            self.config.custom_schema_type,
            "Expected result failed: the custom field schema did not expose the "
            "expected Jira type.\n"
            f"Observed field: {custom_field}",
        )
        self.assertEqual(
            custom_schema.get("custom"),
            self.config.custom_field_id,
            "Expected result failed: the custom field schema did not expose the "
            "expected Jira custom identifier.\n"
            f"Observed field: {custom_field}",
        )
        self.assertNotIn(
            "system",
            custom_schema,
            "Expected result failed: the custom field schema incorrectly exposed a "
            "system identifier.\n"
            f"Observed field: {custom_field}",
        )

        self.assertIn(
            f'"name": "{self.config.summary_field_name}"',
            observation.result.stdout,
            "Human-style verification failed: the visible CLI output did not show the "
            "`summary` field entry by name.\n"
            f"Observed stdout:\n{observation.result.stdout}",
        )
        self.assertIn(
            '"schema"',
            observation.result.stdout,
            "Human-style verification failed: the visible CLI output did not show a "
            "schema object for the `summary` field entry.\n"
            f"Observed stdout:\n{observation.result.stdout}",
        )
        self.assertIn(
            f'"type": "{self.config.summary_schema_type}"',
            observation.result.stdout,
            "Human-style verification failed: the visible CLI output did not show the "
            "expected Jira-style schema type for the `summary` field.\n"
            f"Observed stdout:\n{observation.result.stdout}",
        )
        self.assertIn(
            f'"system": "{self.config.summary_field_id}"',
            observation.result.stdout,
            "Human-style verification failed: the visible CLI output did not show the "
            "Jira-style schema for the `summary` field.\n"
            f"Observed stdout:\n{observation.result.stdout}",
        )
        self.assertNotIn(
            '"required":',
            observation.result.stdout,
            "Expected result failed: the visible CLI output still leaked the raw "
            "TrackState `required` field marker.\n"
            f"Observed stdout:\n{observation.result.stdout}",
        )


if __name__ == "__main__":
    unittest.main()
