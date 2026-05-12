from __future__ import annotations

from pathlib import Path
import unittest

from testing.components.services.trackstate_cli_localized_components_validator import (
    TrackStateCliLocalizedComponentsValidator,
)
from testing.core.config.trackstate_cli_localized_components_config import (
    TrackStateCliLocalizedComponentsConfig,
)
from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)
from testing.tests.support.trackstate_cli_localized_components_probe_factory import (
    create_trackstate_cli_localized_components_probe,
)


class CliLocalizedComponentMetadataTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = TrackStateCliLocalizedComponentsConfig.from_defaults()
        self.validator = TrackStateCliLocalizedComponentsValidator(
            probe=create_trackstate_cli_localized_components_probe(self.repository_root)
        )

    def test_read_components_reports_localized_display_names_and_fallback_flags(
        self,
    ) -> None:
        result = self.validator.validate(config=self.config)

        default_payload = self._assert_successful_payload(
            observation=result.default_observation,
            expected_command=self.config.default_command,
            failure_prefix="Step 1 failed",
        )
        default_by_id = self._payload_by_id(default_payload)
        self.assertEqual(
            default_by_id,
            {
                "tracker-cli": {
                    "id": "tracker-cli",
                    "name": "Tracker CLI",
                    "description": "",
                    "assigneeType": "PROJECT_DEFAULT",
                    "isAssigneeTypeValid": True,
                },
                "tracker-core": {
                    "id": "tracker-core",
                    "name": "Tracker Core",
                    "description": "",
                    "assigneeType": "PROJECT_DEFAULT",
                    "isAssigneeTypeValid": True,
                },
            },
            "Step 1 failed: `trackstate read components` without a locale did not keep "
            "the canonical component metadata payload.\n"
            f"Observed payload: {default_payload}",
        )
        self.assertNotIn(
            '"displayName"',
            result.default_observation.result.stdout,
            "Human-style verification failed: the default terminal output visibly added "
            "localized metadata even though no locale was requested.\n"
            f"Observed stdout:\n{result.default_observation.result.stdout}",
        )
        self.assertNotIn(
            '"usedFallback"',
            result.default_observation.result.stdout,
            "Human-style verification failed: the default terminal output visibly added "
            "fallback flags even though no locale was requested.\n"
            f"Observed stdout:\n{result.default_observation.result.stdout}",
        )

        french_payload = self._assert_successful_payload(
            observation=result.french_observation,
            expected_command=self.config.french_command,
            failure_prefix="Step 2 failed",
        )
        french_by_id = self._payload_by_id(french_payload)
        self.assertEqual(
            french_by_id,
            {
                "tracker-cli": {
                    "id": "tracker-cli",
                    "name": "Tracker CLI",
                    "displayName": "Interface CLI",
                    "usedFallback": False,
                    "description": "",
                    "assigneeType": "PROJECT_DEFAULT",
                    "isAssigneeTypeValid": True,
                },
                "tracker-core": {
                    "id": "tracker-core",
                    "name": "Tracker Core",
                    "displayName": "Noyau TrackState",
                    "usedFallback": False,
                    "description": "",
                    "assigneeType": "PROJECT_DEFAULT",
                    "isAssigneeTypeValid": True,
                },
            },
            "Step 2 failed: `trackstate read components --locale fr` did not expose the "
            "expected French display names alongside the canonical fields.\n"
            f"Observed payload: {french_payload}",
        )
        for fragment in (
            '"displayName": "Interface CLI"',
            '"displayName": "Noyau TrackState"',
            '"usedFallback": false',
        ):
            self.assertIn(
                fragment,
                result.french_observation.result.stdout,
                "Human-style verification failed: the French terminal output did not "
                "visibly show the localized component labels and explicit non-fallback "
                "state.\n"
                f"Missing fragment: {fragment}\n"
                f"Observed stdout:\n{result.french_observation.result.stdout}",
            )

        german_payload = self._assert_successful_payload(
            observation=result.german_observation,
            expected_command=self.config.german_command,
            failure_prefix="Step 3 failed",
        )
        german_by_id = self._payload_by_id(german_payload)
        self.assertEqual(
            german_by_id,
            {
                "tracker-cli": {
                    "id": "tracker-cli",
                    "name": "Tracker CLI",
                    "displayName": "CLI-Oberflaeche",
                    "usedFallback": False,
                    "description": "",
                    "assigneeType": "PROJECT_DEFAULT",
                    "isAssigneeTypeValid": True,
                },
                "tracker-core": {
                    "id": "tracker-core",
                    "name": "Tracker Core",
                    "displayName": "Tracker Core",
                    "usedFallback": True,
                    "description": "",
                    "assigneeType": "PROJECT_DEFAULT",
                    "isAssigneeTypeValid": True,
                },
            },
            "Step 3 failed: `trackstate read components --locale de` did not preserve "
            "the canonical metadata while marking the missing translation with "
            "`usedFallback: true`.\n"
            f"Observed payload: {german_payload}",
        )
        for fragment in (
            '"displayName": "CLI-Oberflaeche"',
            '"displayName": "Tracker Core"',
            '"usedFallback": true',
        ):
            self.assertIn(
                fragment,
                result.german_observation.result.stdout,
                "Human-style verification failed: the German terminal output did not "
                "visibly show the fallback value and machine-readable fallback flag for "
                "the untranslated component.\n"
                f"Missing fragment: {fragment}\n"
                f"Observed stdout:\n{result.german_observation.result.stdout}",
            )

    def _assert_successful_payload(
        self,
        *,
        observation: TrackStateCliCommandObservation,
        expected_command: tuple[str, ...],
        failure_prefix: str,
    ) -> list[dict[str, object]]:
        self.assertEqual(
            observation.requested_command,
            expected_command,
            f"{failure_prefix}: TS-468 did not execute the expected CLI command.\n"
            f"Expected command: {' '.join(expected_command)}\n"
            f"Observed command: {observation.requested_command_text}",
        )
        self.assertIsNotNone(
            observation.compiled_binary_path,
            f"{failure_prefix}: TS-468 must execute a repository-local compiled binary "
            "so the seeded repository can stay the current working directory.\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Fallback reason: {observation.fallback_reason}",
        )
        self.assertEqual(
            observation.executed_command[0],
            observation.compiled_binary_path,
            f"{failure_prefix}: TS-468 did not run the compiled repository-local CLI "
            "binary.\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Compiled binary path: {observation.compiled_binary_path}",
        )
        self.assertEqual(
            observation.result.exit_code,
            0,
            f"{failure_prefix}: executing `{observation.requested_command_text}` did not "
            "complete successfully from a valid TrackState repository.\n"
            f"Repository path: {observation.repository_path}\n"
            f"Requested command: {observation.requested_command_text}\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Fallback reason: {observation.fallback_reason}\n"
            f"Observed exit code: {observation.result.exit_code}\n"
            f"stdout:\n{observation.result.stdout}\n"
            f"stderr:\n{observation.result.stderr}",
        )
        payload = observation.result.json_payload
        self.assertIsInstance(
            payload,
            list,
            f"{failure_prefix}: `{observation.requested_command_text}` did not return a "
            "JSON array payload.\n"
            f"stdout:\n{observation.result.stdout}\n"
            f"stderr:\n{observation.result.stderr}",
        )
        assert isinstance(payload, list)
        payload_by_id = self._payload_by_id(payload)
        self.assertEqual(
            set(payload_by_id),
            {"tracker-cli", "tracker-core"},
            f"{failure_prefix}: the CLI did not return the expected two seeded project "
            "components.\n"
            f"Observed payload: {payload}",
        )
        return payload

    def _payload_by_id(
        self,
        payload: list[object],
    ) -> dict[str, dict[str, object]]:
        mapped: dict[str, dict[str, object]] = {}
        for entry in payload:
            self.assertIsInstance(
                entry,
                dict,
                "Expected result failed: the component list included a non-object item.\n"
                f"Observed payload: {payload}",
            )
            assert isinstance(entry, dict)
            component_id = entry.get("id")
            self.assertIsInstance(
                component_id,
                str,
                "Expected result failed: a component entry did not expose a string id.\n"
                f"Observed entry: {entry}",
            )
            assert isinstance(component_id, str)
            mapped[component_id] = entry
        return mapped


if __name__ == "__main__":
    unittest.main()
