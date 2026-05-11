from __future__ import annotations

from pathlib import Path
import unittest

from testing.components.services.trackstate_cli_read_alias_validator import (
    TrackStateCliReadAliasValidator,
)
from testing.core.config.trackstate_cli_read_alias_config import (
    TrackStateCliReadAliasCase,
    TrackStateCliReadAliasConfig,
)
from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)
from testing.tests.support.trackstate_cli_read_alias_probe_factory import (
    create_trackstate_cli_read_alias_probe,
)


class CliReadAliasCompatibilityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = TrackStateCliReadAliasConfig.from_defaults()
        self.validator = TrackStateCliReadAliasValidator(
            probe=create_trackstate_cli_read_alias_probe(self.repository_root)
        )

    def test_cli_read_aliases_match_canonical_read_payloads(self) -> None:
        result = self.validator.validate(config=self.config)

        for case_result in result.case_results:
            case = case_result.case
            with self.subTest(case=case.name):
                canonical_payload = self._assert_successful_observation(
                    case=case,
                    observation=case_result.canonical_observation,
                    expected_command=case.canonical_command,
                    failure_prefix="Precondition failed",
                    expectation_label="canonical read command",
                )
                alias_payload = self._assert_successful_observation(
                    case=case,
                    observation=case_result.alias_observation,
                    expected_command=case.alias_command,
                    failure_prefix=f"Step {case.step} failed",
                    expectation_label="ticket alias command",
                )

                self.assertEqual(
                    case_result.alias_observation.repository_path,
                    case_result.canonical_observation.repository_path,
                    "Precondition failed: TS-379 did not execute the alias and "
                    "canonical commands against the same seeded repository.\n"
                    f"Alias repository path: {case_result.alias_observation.repository_path}\n"
                    f"Canonical repository path: {case_result.canonical_observation.repository_path}",
                )
                self.assertEqual(
                    alias_payload,
                    canonical_payload,
                    f"Expected result failed: `{' '.join(case.alias_command)}` did not "
                    "return the same raw Jira-shaped JSON payload as its canonical "
                    "read command counterpart.\n"
                    f"Observed alias payload: {alias_payload}\n"
                    f"Observed canonical payload: {canonical_payload}",
                )
                self.assertEqual(
                    case_result.alias_observation.result.stdout,
                    case_result.canonical_observation.result.stdout,
                    f"Human-style verification failed: `{' '.join(case.alias_command)}` "
                    "did not print the same visible raw JSON payload a user sees when "
                    f"running `{' '.join(case.canonical_command)}`.\n"
                    f"Observed alias stdout:\n{case_result.alias_observation.result.stdout}\n"
                    "\n"
                    "Observed canonical stdout:\n"
                    f"{case_result.canonical_observation.result.stdout}",
                )

                for fragment in case.required_stdout_fragments:
                    self.assertIn(
                        fragment,
                        case_result.alias_observation.result.stdout,
                        f"Human-style verification failed: the terminal output for "
                        f"`{' '.join(case.alias_command)}` did not visibly show the "
                        "expected Jira-shaped JSON content.\n"
                        f"Missing fragment: {fragment}\n"
                        f"Observed stdout:\n{case_result.alias_observation.result.stdout}",
                    )

    def _assert_successful_observation(
        self,
        *,
        case: TrackStateCliReadAliasCase,
        observation: TrackStateCliCommandObservation,
        expected_command: tuple[str, ...],
        failure_prefix: str,
        expectation_label: str,
    ) -> object:
        self.assertEqual(
            observation.requested_command,
            expected_command,
            f"{failure_prefix}: TS-379 did not execute the expected {expectation_label} "
            "for this scenario.\n"
            f"Expected command: {' '.join(expected_command)}\n"
            f"Observed command: {observation.requested_command_text}",
        )
        self.assertIsNotNone(
            observation.compiled_binary_path,
            f"{failure_prefix}: TS-379 must execute a repository-local compiled "
            "binary so the seeded repository can stay the current working "
            "directory.\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Fallback reason: {observation.fallback_reason}",
        )
        self.assertEqual(
            observation.executed_command[0],
            observation.compiled_binary_path,
            f"{failure_prefix}: TS-379 did not run the compiled repository-local "
            "CLI binary.\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Compiled binary path: {observation.compiled_binary_path}",
        )
        self.assertEqual(
            observation.result.exit_code,
            0,
            f"{failure_prefix}: executing `{observation.requested_command_text}` did "
            "not complete successfully from a valid TrackState repository.\n"
            f"Repository path: {observation.repository_path}\n"
            f"Requested command: {observation.requested_command_text}\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Fallback reason: {observation.fallback_reason}\n"
            f"Observed exit code: {observation.result.exit_code}\n"
            f"stdout:\n{observation.result.stdout}\n"
            f"stderr:\n{observation.result.stderr}",
        )
        payload = observation.result.json_payload
        if case.expected_json_kind == "object":
            self.assertIsInstance(
                payload,
                dict,
                f"{failure_prefix}: `{observation.requested_command_text}` did not "
                "return a JSON object payload.\n"
                f"stdout:\n{observation.result.stdout}\n"
                f"stderr:\n{observation.result.stderr}",
            )
            assert isinstance(payload, dict)
            return payload

        self.assertIsInstance(
            payload,
            list,
            f"{failure_prefix}: `{observation.requested_command_text}` did not return "
            "a JSON array payload.\n"
            f"stdout:\n{observation.result.stdout}\n"
            f"stderr:\n{observation.result.stderr}",
        )
        assert isinstance(payload, list)
        return payload


if __name__ == "__main__":
    unittest.main()
