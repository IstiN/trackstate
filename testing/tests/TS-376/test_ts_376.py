from __future__ import annotations

from pathlib import Path
import unittest

from testing.components.services.trackstate_cli_issue_link_types_validator import (
    TrackStateCliIssueLinkTypesValidator,
)
from testing.core.config.trackstate_cli_issue_link_types_config import (
    TrackStateCliIssueLinkTypesConfig,
)
from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)
from testing.tests.support.trackstate_cli_issue_link_types_probe_factory import (
    create_trackstate_cli_issue_link_types_probe,
)


class CliReadIssueLinkTypesTest(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = TrackStateCliIssueLinkTypesConfig.from_defaults()
        self.validator = TrackStateCliIssueLinkTypesValidator(
            probe=create_trackstate_cli_issue_link_types_probe(self.repository_root)
        )

    def test_read_issue_link_types_returns_canonical_jira_labels(self) -> None:
        result = self.validator.validate(config=self.config)
        ticket_observation = result.ticket_observation
        canonical_observation = result.canonical_observation

        self._assert_command_was_executed_exactly(
            observation=ticket_observation,
            expected_command=self.config.ticket_command,
            precondition_message=(
                "Precondition failed: TS-376 must execute the exact ticket command "
                "from the seeded Local Git repository."
            ),
        )
        self._assert_command_was_executed_exactly(
            observation=canonical_observation,
            expected_command=self.config.canonical_command,
            precondition_message=(
                "Precondition failed: TS-376 must also execute the canonical "
                "link-types control command from the same seeded repository."
            ),
        )

        self.assertEqual(
            ticket_observation.result.exit_code,
            0,
            "Step 1 failed: executing `trackstate read issue-link-types` did not "
            "succeed from a valid TrackState repository.\n"
            f"Repository path: {ticket_observation.repository_path}\n"
            f"Requested command: {ticket_observation.requested_command_text}\n"
            f"Executed command: {ticket_observation.executed_command_text}\n"
            f"Fallback reason: {ticket_observation.fallback_reason}\n"
            f"Observed exit code: {ticket_observation.result.exit_code}\n"
            f"stdout:\n{ticket_observation.result.stdout}\n"
            f"stderr:\n{ticket_observation.result.stderr}\n"
            "\n"
            "Control observation from the same repository:\n"
            f"Requested command: {canonical_observation.requested_command_text}\n"
            f"Executed command: {canonical_observation.executed_command_text}\n"
            f"Observed exit code: {canonical_observation.result.exit_code}\n"
            f"stdout:\n{canonical_observation.result.stdout}\n"
            f"stderr:\n{canonical_observation.result.stderr}",
        )

        ticket_payload = self._assert_successful_payload(
            observation=ticket_observation,
            failure_prefix="Step 2 failed",
        )
        canonical_payload = self._assert_successful_payload(
            observation=canonical_observation,
            failure_prefix="Precondition failed",
        )
        expected_payload = [
            fixture.to_payload() for fixture in self.config.expected_link_types
        ]
        self.assertEqual(
            ticket_payload,
            expected_payload,
            "Step 2 failed: `trackstate read issue-link-types` did not return the "
            "expected four canonical issue link types with Jira inward and outward "
            "labels.\n"
            f"Expected payload: {expected_payload}\n"
            f"Observed payload: {ticket_payload}",
        )
        self.assertEqual(
            ticket_payload,
            canonical_payload,
            "Expected result failed: the exact ticket command did not match the "
            "canonical `trackstate read link-types` response.\n"
            f"Ticket payload: {ticket_payload}\n"
            f"Canonical payload: {canonical_payload}",
        )

        for fragment in (
            '"id": "blocks"',
            '"inward": "is blocked by"',
            '"id": "duplicates"',
            '"inward": "is duplicated by"',
            '"id": "clones"',
            '"inward": "is cloned by"',
        ):
            self.assertIn(
                fragment,
                ticket_observation.result.stdout,
                "Human-style verification failed: the visible CLI JSON output did not "
                "show the expected Jira label text for issue link types.\n"
                f"Missing fragment: {fragment}\n"
                f"Observed stdout:\n{ticket_observation.result.stdout}",
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
            "TS-376 must execute a repository-local compiled binary so the seeded "
            "repository remains the current working directory.\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Fallback reason: {observation.fallback_reason}",
        )
        self.assertEqual(
            observation.executed_command[0],
            observation.compiled_binary_path,
            f"{precondition_message}\n"
            "TS-376 did not run the compiled repository-local CLI binary.\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Compiled binary path: {observation.compiled_binary_path}",
        )

    def _assert_successful_payload(
        self,
        *,
        observation: TrackStateCliCommandObservation,
        failure_prefix: str,
    ) -> list[dict[str, object]]:
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
            list,
            f"{failure_prefix}: `{observation.requested_command_text}` did not return "
            "a JSON array payload.\n"
            f"stdout:\n{observation.result.stdout}\n"
            f"stderr:\n{observation.result.stderr}",
        )
        assert isinstance(payload, list)
        for entry in payload:
            self.assertIsInstance(
                entry,
                dict,
                f"{failure_prefix}: the issue link type list included a non-object "
                "entry.\n"
                f"Observed payload: {payload}",
            )
        return payload


if __name__ == "__main__":
    unittest.main()
