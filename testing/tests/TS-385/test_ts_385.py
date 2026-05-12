from __future__ import annotations

import json
import os
from pathlib import Path
import unittest

from testing.components.services.trackstate_cli_fallback_boundaries_validator import (
    TrackStateCliFallbackBoundariesValidator,
)
from testing.core.config.trackstate_cli_fallback_boundaries_config import (
    TrackStateCliFallbackBoundariesConfig,
    TrackStateCliFallbackBoundaryScenarioConfig,
)
from testing.core.models.trackstate_cli_fallback_boundaries_result import (
    TrackStateCliFallbackBoundaryObservation,
)
from testing.tests.support.trackstate_cli_fallback_boundaries_probe_factory import (
    create_trackstate_cli_fallback_boundaries_probe,
)


class TrackStateCliFallbackBoundariesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config_path = self.repository_root / "testing/tests/TS-385/config.yaml"
        self.config = TrackStateCliFallbackBoundariesConfig.from_file(self.config_path)
        self.validator = TrackStateCliFallbackBoundariesValidator(
            probe=create_trackstate_cli_fallback_boundaries_probe(self.repository_root)
        )

    def test_cli_rejects_binary_and_admin_fallback_requests_before_repo_access(
        self,
    ) -> None:
        result = self.validator.validate(config=self.config)
        self._write_result_if_requested(result.to_dict())

        self.assertEqual(
            len(result.observations),
            len(self.config.scenarios),
            "Precondition failed: TS-385 did not execute the expected number of "
            "fallback boundary scenarios.\n"
            f"Expected scenarios: {[scenario.name for scenario in self.config.scenarios]}\n"
            f"Observed scenarios: {[observation.name for observation in result.observations]}",
        )

        failures: list[str] = []
        for scenario, observation in zip(self.config.scenarios, result.observations):
            failures.extend(self._validate_observation(scenario, observation))

        self.assertFalse(failures, "\n\n".join(failures))

    def _validate_observation(
        self,
        scenario: TrackStateCliFallbackBoundaryScenarioConfig,
        observation: TrackStateCliFallbackBoundaryObservation,
    ) -> list[str]:
        failures: list[str] = []
        payload = observation.result.json_payload
        payload_dict = payload if isinstance(payload, dict) else None
        error_dict = (
            payload_dict.get("error")
            if isinstance(payload_dict, dict) and isinstance(payload_dict.get("error"), dict)
            else None
        )
        target_dict = (
            payload_dict.get("target")
            if isinstance(payload_dict, dict) and isinstance(payload_dict.get("target"), dict)
            else None
        )

        if observation.ticket_command != scenario.ticket_command:
            failures.append(
                f"Precondition failed for {scenario.name}: the probe did not preserve "
                "the ticket command text.\n"
                f"Expected ticket command: {scenario.ticket_command}\n"
                f"Observed ticket command: {observation.ticket_command}"
            )

        if payload_dict is None:
            failures.append(
                f"Step failed for {scenario.name}: the CLI did not return a machine-"
                "readable JSON envelope.\n"
                f"Ticket command: {scenario.ticket_command}\n"
                f"Executed command: {observation.executed_command_text}\n"
                f"Execution cwd: {observation.execution_cwd}\n"
                f"Exit code: {observation.result.exit_code}\n"
                f"stdout:\n{observation.result.stdout}\n"
                f"stderr:\n{observation.result.stderr}"
            )
            return failures

        if observation.result.exit_code != self.config.expected_exit_code:
            failures.append(
                f"Step failed for {scenario.name}: the fallback command did not return "
                "the documented unsupported exit code before repository access.\n"
                f"Ticket command: {scenario.ticket_command}\n"
                f"Executed command: {observation.executed_command_text}\n"
                f"Execution cwd: {observation.execution_cwd}\n"
                f"Expected exit code: {self.config.expected_exit_code}\n"
                f"Observed exit code: {observation.result.exit_code}\n"
                f"Observed payload: {payload_dict}\n"
                f"stdout:\n{observation.result.stdout}\n"
                f"stderr:\n{observation.result.stderr}"
            )

        if payload_dict.get("ok") is not False:
            failures.append(
                f"Expected-result verification failed for {scenario.name}: the JSON "
                "envelope did not report ok=false.\n"
                f"Observed payload: {payload_dict}"
            )

        if error_dict is None:
            failures.append(
                f"Step failed for {scenario.name}: the JSON envelope omitted the error "
                "object for the unsupported request.\n"
                f"Observed payload: {payload_dict}"
            )
            return failures

        if error_dict.get("code") != self.config.expected_error_code:
            failures.append(
                f"Step failed for {scenario.name}: the CLI did not classify the unsafe "
                f"fallback request as {self.config.expected_error_code}.\n"
                f"Expected error code: {self.config.expected_error_code}\n"
                f"Observed error code: {error_dict.get('code')}\n"
                f"Observed payload: {payload_dict}"
            )

        if error_dict.get("category") != self.config.expected_error_category:
            failures.append(
                f"Step failed for {scenario.name}: the CLI did not report the "
                f"{self.config.expected_error_category} error category.\n"
                f"Expected category: {self.config.expected_error_category}\n"
                f"Observed category: {error_dict.get('category')}\n"
                f"Observed payload: {payload_dict}"
            )

        if error_dict.get("exitCode") != self.config.expected_exit_code:
            failures.append(
                f"Step failed for {scenario.name}: the JSON error object did not "
                "repeat the documented unsupported exit code.\n"
                f"Expected error exitCode: {self.config.expected_exit_code}\n"
                f"Observed error exitCode: {error_dict.get('exitCode')}\n"
                f"Observed payload: {payload_dict}"
            )

        if target_dict is None:
            failures.append(
                f"Human-style verification failed for {scenario.name}: the terminal "
                "output did not expose target metadata.\n"
                f"Observed payload: {payload_dict}"
            )
        else:
            if target_dict.get("type") != "local":
                failures.append(
                    f"Human-style verification failed for {scenario.name}: the visible "
                    "target type was not local.\n"
                    f"Observed target: {target_dict}"
                )
            if target_dict.get("value") != observation.execution_cwd:
                failures.append(
                    f"Human-style verification failed for {scenario.name}: the visible "
                    "target value did not match the empty working directory used to "
                    "prove repository access was unnecessary.\n"
                    f"Expected target value: {observation.execution_cwd}\n"
                    f"Observed target: {target_dict}"
                )

        message = str(error_dict.get("message", ""))
        lowered_message = message.lower()
        missing_fragments = [
            fragment
            for fragment in scenario.expected_message_fragments
            if fragment not in lowered_message
        ]
        if missing_fragments:
            failures.append(
                f"Human-style verification failed for {scenario.name}: the terminal "
                "error message did not visibly explain the unsupported request.\n"
                f"Missing message fragments: {missing_fragments}\n"
                f"Observed message: {message}\n"
                f"Observed payload: {payload_dict}"
            )

        for fragment in (
            '"ok": false',
            f'"code": "{self.config.expected_error_code}"',
            f'"category": "{self.config.expected_error_category}"',
        ):
            if fragment not in observation.result.stdout:
                failures.append(
                    f"Human-style verification failed for {scenario.name}: stdout did "
                    "not visibly show the unsupported JSON contract.\n"
                    f"Missing stdout fragment: {fragment}\n"
                    f"Observed stdout:\n{observation.result.stdout}"
                )

        return failures

    def _write_result_if_requested(self, payload: dict[str, object]) -> None:
        result_path = os.environ.get("TS385_RESULT_PATH")
        if not result_path:
            return

        destination = Path(result_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    unittest.main()
