from __future__ import annotations

from pathlib import Path
import unittest

from testing.components.services.trackstate_cli_symmetric_link_show_validator import (
    TrackStateCliSymmetricLinkShowValidator,
)
from testing.core.config.trackstate_cli_symmetric_link_show_config import (
    TrackStateCliSymmetricLinkShowConfig,
)
from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)
from testing.tests.support.trackstate_cli_symmetric_link_show_probe_factory import (
    create_trackstate_cli_symmetric_link_show_probe,
)


class TrackStateCliSymmetricLinkShowTest(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = TrackStateCliSymmetricLinkShowConfig.from_defaults()
        self.validator = TrackStateCliSymmetricLinkShowValidator(
            probe=create_trackstate_cli_symmetric_link_show_probe(
                self.repository_root
            )
        )

    def test_ticket_show_returns_canonical_inward_symmetric_link_metadata(self) -> None:
        observation = self.validator.validate(config=self.config).observation

        self._assert_command_was_executed_exactly(
            observation=observation.issue_a_create_observation,
            expected_command=self.config.issue_a_create_command(
                observation.issue_a_create_observation.repository_path
            ),
            precondition_message=(
                "Precondition failed: TS-657 must create Issue A in the disposable "
                "Local Git repository before viewing the target issue details."
            ),
        )
        self._assert_command_was_executed_exactly(
            observation=observation.issue_b_create_observation,
            expected_command=self.config.issue_b_create_command(
                observation.issue_b_create_observation.repository_path
            ),
            precondition_message=(
                "Precondition failed: TS-657 must create Issue B in the disposable "
                "Local Git repository before viewing the target issue details."
            ),
        )
        self._assert_command_was_executed_exactly(
            observation=observation.relates_to_link_observation,
            expected_command=self.config.inverse_link_command(
                observation.relates_to_link_observation.repository_path
            ),
            precondition_message=(
                "Precondition failed: TS-657 must create the symmetric `relates to` "
                "link between TS-1 and TS-2 before executing the ticket step."
            ),
        )
        self._assert_command_was_executed_exactly(
            observation=observation.ticket_show_observation,
            expected_command=self.config.ticket_show_command(
                observation.ticket_show_observation.repository_path
            ),
            precondition_message=(
                "Step 1 failed: TS-657 must execute the exact `trackstate ticket "
                "show --key TS-2` command from the ticket against the disposable "
                "Local Git repository."
            ),
        )
        self._assert_command_was_executed_exactly(
            observation=observation.read_ticket_observation,
            expected_command=self.config.read_ticket_command(
                observation.read_ticket_observation.repository_path
            ),
            precondition_message=(
                "Human-style verification failed: TS-657 must also capture the "
                "closest currently supported read command so the product gap is "
                "reported against a real observable CLI path."
            ),
        )

        issue_a_payload = self._assert_successful_json_object(
            observation=observation.issue_a_create_observation,
            failure_prefix="Precondition failed",
        )
        issue_a = issue_a_payload["data"]["issue"]
        self.assertEqual(
            issue_a["key"],
            self.config.issue_a_key,
            "Precondition failed: the Issue A create response returned an "
            "unexpected issue key.\n"
            f"Observed issue: {issue_a}",
        )
        self.assertEqual(
            issue_a["summary"],
            self.config.issue_a_summary,
            "Precondition failed: the Issue A create response did not preserve the "
            "requested summary.\n"
            f"Observed issue: {issue_a}",
        )

        issue_b_payload = self._assert_successful_json_object(
            observation=observation.issue_b_create_observation,
            failure_prefix="Precondition failed",
        )
        issue_b = issue_b_payload["data"]["issue"]
        self.assertEqual(
            issue_b["key"],
            self.config.issue_b_key,
            "Precondition failed: the Issue B create response returned an "
            "unexpected issue key.\n"
            f"Observed issue: {issue_b}",
        )
        self.assertEqual(
            issue_b["summary"],
            self.config.issue_b_summary,
            "Precondition failed: the Issue B create response did not preserve the "
            "requested summary.\n"
            f"Observed issue: {issue_b}",
        )

        link_payload = self._assert_successful_json_object(
            observation=observation.relates_to_link_observation,
            failure_prefix="Precondition failed",
        )
        self.assertEqual(
            link_payload["data"]["link"],
            self.config.expected_canonical_link_payload,
            "Precondition failed: the setup link response did not preserve the "
            "canonical outward symmetric metadata required by the linked bug fix.\n"
            f"Observed payload: {link_payload}",
        )

        self.assertEqual(
            observation.ticket_show_observation.result.exit_code,
            0,
            "Step 1 failed: executing the exact `trackstate ticket show --key TS-2` "
            "command from the ticket did not succeed from a valid TrackState "
            "repository.\n"
            f"Repository path: {observation.ticket_show_observation.repository_path}\n"
            f"Executed command: {observation.ticket_show_observation.executed_command_text}\n"
            f"Observed exit code: {observation.ticket_show_observation.result.exit_code}\n"
            f"stdout:\n{observation.ticket_show_observation.result.stdout}\n"
            f"stderr:\n{observation.ticket_show_observation.result.stderr}\n"
            f"Supplemental `trackstate read ticket` stdout:\n"
            f"{observation.read_ticket_observation.result.stdout}\n"
            f"Supplemental `trackstate read ticket` stderr:\n"
            f"{observation.read_ticket_observation.result.stderr}",
        )

        ticket_show_payload = observation.ticket_show_observation.result.json_payload
        self.assertIsInstance(
            ticket_show_payload,
            dict,
            "Step 2 failed: the `trackstate ticket show --key TS-2` response was "
            "not a JSON object.\n"
            f"Observed stdout:\n{observation.ticket_show_observation.result.stdout}\n"
            f"Observed stderr:\n{observation.ticket_show_observation.result.stderr}",
        )
        assert isinstance(ticket_show_payload, dict)

        links = ticket_show_payload.get("links")
        self.assertIsInstance(
            links,
            list,
            "Step 2 failed: the target issue response did not expose a `links` "
            "array in the JSON payload.\n"
            f"Observed payload: {ticket_show_payload}\n"
            f"Supplemental `trackstate read ticket` payload: "
            f"{observation.read_ticket_observation.result.json_payload}",
        )
        assert isinstance(links, list)
        self.assertIn(
            self.config.expected_inward_link_payload,
            links,
            "Expected result failed: the target issue JSON did not report the "
            f"canonical inward symmetric relationship for {self.config.issue_a_key}.\n"
            f"Expected entry: {self.config.expected_inward_link_payload}\n"
            f"Observed links: {links}\n"
            f"Observed payload: {ticket_show_payload}",
        )

        for fragment in (
            f'"key": "{self.config.issue_b_key}"',
            f'"summary": "{self.config.issue_b_summary}"',
            f'"type": "{self.config.expected_inward_link_payload["type"]}"',
            f'"target": "{self.config.expected_inward_link_payload["target"]}"',
            f'"direction": "{self.config.expected_inward_link_payload["direction"]}"',
        ):
            self.assertIn(
                fragment,
                observation.ticket_show_observation.result.stdout,
                "Human-style verification failed: the visible CLI response did not "
                "show the target issue and canonical inward link details a user "
                "would expect to read in the terminal.\n"
                f"Missing fragment: {fragment}\n"
                f"Observed stdout:\n{observation.ticket_show_observation.result.stdout}",
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
            "TS-657 must execute a repository-local compiled binary so the seeded "
            "repository remains isolated.\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Fallback reason: {observation.fallback_reason}",
        )
        self.assertEqual(
            observation.executed_command[0],
            observation.compiled_binary_path,
            f"{precondition_message}\n"
            "TS-657 did not run the compiled repository-local CLI binary.\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Compiled binary path: {observation.compiled_binary_path}",
        )

    def _assert_successful_json_object(
        self,
        *,
        observation: TrackStateCliCommandObservation,
        failure_prefix: str,
    ) -> dict[str, object]:
        self.assertEqual(
            observation.result.exit_code,
            0,
            f"{failure_prefix}: executing `{observation.requested_command_text}` did "
            "not complete successfully from a valid TrackState repository.\n"
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
