from __future__ import annotations

from pathlib import Path
import unittest

from testing.components.services.trackstate_cli_read_fields_local_validator import (
    TrackStateCliReadFieldsLocalValidator,
)
from testing.core.config.trackstate_cli_read_fields_local_config import (
    TrackStateCliReadFieldsLocalConfig,
)
from testing.tests.support.trackstate_cli_read_fields_local_probe_factory import (
    create_trackstate_cli_read_fields_local_probe,
)


class TrackStateCliReadFieldsLocalTest(unittest.TestCase):
    """Verify that the `read fields` command returns a flat array of field objects
    with the Jira-standard schema (TS-380).
    """

    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = TrackStateCliReadFieldsLocalConfig.from_defaults()
        self.validator = TrackStateCliReadFieldsLocalValidator(
            probe=create_trackstate_cli_read_fields_local_probe(self.repository_root)
        )

    def test_read_fields_returns_jira_schema_array(self) -> None:
        validation_result = self.validator.validate(config=self.config)
        observation = validation_result.observation

        self.assertEqual(
            observation.requested_command,
            self.config.requested_command,
            "TS-380 did not execute the exact ticket command.\n"
            f"Expected command: {observation.requested_command_text}\n"
            f"Observed command: {observation.executed_command_text}",
        )
        self.assertIsNotNone(
            observation.compiled_binary_path,
            "TS-380 must execute a repository-local compiled binary "
            "so the seeded Local Git repository stays the current working directory.\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Fallback reason: {observation.fallback_reason}",
        )
        self.assertEqual(
            observation.executed_command[0],
            observation.compiled_binary_path,
            "TS-380 did not run the compiled repository-local CLI binary.\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Compiled binary path: {observation.compiled_binary_path}",
        )
        self.assertEqual(
            observation.result.exit_code,
            0,
            "CLI 'read fields' failed unexpectedly.\n"
            f"Requested command: {observation.requested_command_text}\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"stdout:\n{observation.result.stdout}\n"
            f"stderr:\n{observation.result.stderr}",
        )

        fields = validation_result.fields
        self.assertTrue(
            fields,
            "CLI 'read fields' returned an empty or non-array payload.\n"
            f"stdout:\n{observation.result.stdout}\n"
            f"stderr:\n{observation.result.stderr}",
        )

        for idx, entry in enumerate(fields):
            with self.subTest(index=idx, field=entry.get("id", "?")):
                self.assertIsInstance(
                    entry,
                    dict,
                    f"Array entry {idx} is not an object: {entry!r}",
                )
                missing_keys = set(self.config.required_field_keys) - set(entry.keys())
                self.assertFalse(
                    missing_keys,
                    f"Field entry {idx} missing required keys: {missing_keys}.\n"
                    f"Observed entry: {entry}",
                )
                schema = entry.get("schema")
                self.assertIsInstance(
                    schema,
                    dict,
                    f"Field entry {idx} 'schema' is not an object.\n"
                    f"Observed entry: {entry}",
                )
                if isinstance(schema, dict):
                    missing_schema_keys = (
                        set(self.config.required_schema_keys) - set(schema.keys())
                    )
                    self.assertFalse(
                        missing_schema_keys,
                        f"Field entry {idx} schema missing required keys: "
                        f"{missing_schema_keys}.\n"
                        f"Observed schema: {schema}",
                    )
                    has_discriminator = "system" in schema or "custom" in schema
                    self.assertTrue(
                        has_discriminator,
                        f"Field entry {idx} schema missing either 'system' or "
                        f"'custom' key.\nObserved schema: {schema}",
                    )

        stdout_text = observation.result.stdout.strip()
        self.assertNotIn(
            '"ok"',
            stdout_text,
            "Raw 'read fields' output should not contain a TrackState envelope 'ok' key.",
        )
        self.assertNotIn(
            '"schemaVersion"',
            stdout_text,
            "Raw 'read fields' output should not contain a TrackState envelope "
            "'schemaVersion' key.",
        )
        self.assertNotIn(
            '"data"',
            stdout_text,
            "Raw 'read fields' output should not contain a TrackState envelope 'data' key.",
        )


if __name__ == "__main__":
    unittest.main()
