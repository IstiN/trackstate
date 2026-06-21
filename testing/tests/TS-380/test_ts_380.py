from __future__ import annotations

import unittest
from pathlib import Path

from testing.components.services.trackstate_cli_read_fields_validator import (
    TrackStateCliReadFieldsValidator,
)
from testing.core.config.trackstate_cli_read_fields_config import (
    TrackStateCliReadFieldsConfig,
)
from testing.core.models.trackstate_cli_read_fields_result import (
    TrackStateCliReadFieldsObservation,
)
from testing.tests.support.trackstate_cli_read_fields_probe_factory import (
    create_trackstate_cli_read_fields_probe,
)


REPO_ROOT = Path(__file__).resolve().parents[3]


class TrackStateCliReadFieldsTest(unittest.TestCase):
    """Verify that the `read fields` command returns a flat array of field objects
    with the Jira-standard schema (TS-380).
    """

    def setUp(self) -> None:
        self.config = TrackStateCliReadFieldsConfig.from_defaults()
        self.validator = TrackStateCliReadFieldsValidator(
            probe=create_trackstate_cli_read_fields_probe(REPO_ROOT)
        )

    def test_read_fields_returns_jira_schema_array(self) -> None:
        result = self.validator.validate(config=self.config)
        observation = result.observation

        self._assert_successful_execution(observation)
        payload = observation.result.json_payload
        self.assertIsInstance(
            payload,
            list,
            f"Expected a JSON array, got {type(payload).__name__}.\n"
            f"Observed payload:\n{observation.result.stdout}",
        )
        assert isinstance(payload, list)
        self.assertTrue(
            payload,
            "CLI 'read fields' returned an empty array.",
        )

        # Verify each entry has the Jira-standard schema keys promised by config.yaml
        required_keys = set(self.config.required_field_keys)
        for idx, entry in enumerate(payload):
            with self.subTest(index=idx, field=entry.get("id", "?")):
                self.assertIsInstance(
                    entry,
                    dict,
                    f"Array entry {idx} is not an object: {entry!r}",
                )
                missing = required_keys - set(entry.keys())
                self.assertFalse(
                    missing,
                    f"Field entry {idx} missing required keys: {missing}.\n"
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
                    self.assertIn(
                        "type",
                        schema,
                        f"Field entry {idx} schema missing 'type'.\n"
                        f"Observed schema: {schema}",
                    )
                    has_schema_discriminator = "system" in schema or "custom" in schema
                    self.assertTrue(
                        has_schema_discriminator,
                        f"Field entry {idx} schema missing either 'system' or 'custom' key.\n"
                        f"Observed schema: {schema}",
                    )

        # Verify no TrackState-specific envelope markers are present
        stdout_text = observation.result.stdout.strip()
        self.assertNotIn(
            '"ok"',
            stdout_text,
            "Raw 'read fields' output should not contain a TrackState envelope 'ok' key.",
        )
        self.assertNotIn(
            '"schemaVersion"',
            stdout_text,
            "Raw 'read fields' output should not contain a TrackState envelope 'schemaVersion' key.",
        )
        self.assertNotIn(
            '"data"',
            stdout_text,
            "Raw 'read fields' output should not contain a TrackState envelope 'data' key.",
        )

    def _assert_successful_execution(
        self,
        observation: TrackStateCliReadFieldsObservation,
    ) -> None:
        self.assertEqual(
            observation.requested_command,
            self.config.requested_command,
            "Step 1 failed: TS-380 did not execute the exact ticket command.\n"
            f"Expected command: {observation.requested_command_text}\n"
            f"Observed command: {observation.executed_command_text}",
        )
        self.assertEqual(
            observation.result.exit_code,
            0,
            f"CLI 'read fields' failed unexpectedly.\n"
            f"Requested command: {observation.requested_command_text}\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Fallback reason: {observation.fallback_reason}\n"
            f"stdout:\n{observation.result.stdout}\n"
            f"stderr:\n{observation.result.stderr}",
        )


if __name__ == "__main__":
    unittest.main()
