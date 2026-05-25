from __future__ import annotations

from pathlib import Path
import unittest

from testing.components.services.trackstate_cli_read_ticket_mixed_link_directions_validator import (
    TrackStateCliReadTicketMixedLinkDirectionsValidator,
)
from testing.core.config.trackstate_cli_read_ticket_mixed_link_directions_config import (
    TrackStateCliReadTicketMixedLinkDirectionsConfig,
)
from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)
from testing.tests.support.trackstate_cli_read_ticket_mixed_link_directions_probe_factory import (
    create_trackstate_cli_read_ticket_mixed_link_directions_probe,
)


class TrackStateCliReadTicketMixedLinkDirectionsTest(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = TrackStateCliReadTicketMixedLinkDirectionsConfig.from_defaults()
        self.validator = TrackStateCliReadTicketMixedLinkDirectionsValidator(
            probe=create_trackstate_cli_read_ticket_mixed_link_directions_probe(
                self.repository_root
            )
        )

    def test_read_ticket_aggregates_inward_and_outward_links(self) -> None:
        observation = self.validator.validate(config=self.config).observation

        self._assert_command_was_executed_exactly(
            observation=observation.issue_a_create_observation,
            expected_command=self.config.issue_a_create_command(
                observation.issue_a_create_observation.repository_path
            ),
            precondition_message=(
                "Precondition failed: TS-675 must create Issue A in the disposable "
                "Local Git repository before reading the linked target issue."
            ),
        )
        self._assert_command_was_executed_exactly(
            observation=observation.issue_b_create_observation,
            expected_command=self.config.issue_b_create_command(
                observation.issue_b_create_observation.repository_path
            ),
            precondition_message=(
                "Precondition failed: TS-675 must create Issue B in the disposable "
                "Local Git repository before reading the linked target issue."
            ),
        )
        self._assert_command_was_executed_exactly(
            observation=observation.issue_c_create_observation,
            expected_command=self.config.issue_c_create_command(
                observation.issue_c_create_observation.repository_path
            ),
            precondition_message=(
                "Precondition failed: TS-675 must create Issue C in the disposable "
                "Local Git repository before creating the outbound `blocks` link."
            ),
        )
        self._assert_command_was_executed_exactly(
            observation=observation.inward_relates_link_observation,
            expected_command=self.config.inverse_link_command(
                observation.inward_relates_link_observation.repository_path
            ),
            precondition_message=(
                "Precondition failed: TS-675 must create the inward symmetric "
                "`relates to` link from TS-1 to TS-2 before executing the ticket step."
            ),
        )
        self._assert_command_was_executed_exactly(
            observation=observation.outward_blocks_link_observation,
            expected_command=self.config.outward_link_command(
                observation.outward_blocks_link_observation.repository_path
            ),
            precondition_message=(
                "Precondition failed: TS-675 must create the outward `blocks` link "
                "from TS-2 to TS-3 before executing the ticket step."
            ),
        )
        self._assert_command_was_executed_exactly(
            observation=observation.read_ticket_observation,
            expected_command=self.config.read_ticket_command(
                observation.read_ticket_observation.repository_path
            ),
            precondition_message=(
                "Step 1 failed: TS-675 must execute the exact `trackstate read "
                "ticket --key TS-2` command from the ticket against the seeded "
                "repository."
            ),
        )

        issue_a = self._assert_created_issue(
            observation=observation.issue_a_create_observation,
            expected_key=self.config.issue_a_key,
            expected_summary=self.config.issue_a_summary,
            failure_prefix="Precondition failed",
        )
        self.assertEqual(
            issue_a["key"],
            self.config.issue_a_key,
            "Precondition failed: the Issue A create response returned an "
            "unexpected issue key.\n"
            f"Observed issue: {issue_a}",
        )
        issue_b = self._assert_created_issue(
            observation=observation.issue_b_create_observation,
            expected_key=self.config.issue_b_key,
            expected_summary=self.config.issue_b_summary,
            failure_prefix="Precondition failed",
        )
        self.assertEqual(
            issue_b["key"],
            self.config.issue_b_key,
            "Precondition failed: the Issue B create response returned an "
            "unexpected issue key.\n"
            f"Observed issue: {issue_b}",
        )
        issue_c = self._assert_created_issue(
            observation=observation.issue_c_create_observation,
            expected_key=self.config.issue_c_key,
            expected_summary=self.config.issue_c_summary,
            failure_prefix="Precondition failed",
        )
        self.assertEqual(
            issue_c["key"],
            self.config.issue_c_key,
            "Precondition failed: the Issue C create response returned an "
            "unexpected issue key.\n"
            f"Observed issue: {issue_c}",
        )

        inward_link_payload = self._assert_successful_json_object(
            observation=observation.inward_relates_link_observation,
            failure_prefix="Precondition failed",
        )
        self.assertEqual(
            inward_link_payload["data"]["link"],
            self.config.expected_canonical_link_payload,
            "Precondition failed: the setup `relates to` link response did not "
            "preserve the canonical outward symmetric metadata required by the "
            "linked bug fix.\n"
            f"Observed payload: {inward_link_payload}",
        )

        outward_link_payload = self._assert_successful_json_object(
            observation=observation.outward_blocks_link_observation,
            failure_prefix="Precondition failed",
        )
        self.assertEqual(
            outward_link_payload["data"]["link"],
            self.config.expected_outward_link_payload,
            "Precondition failed: the setup `blocks` link response did not "
            "preserve the canonical outward metadata for TS-3.\n"
            f"Observed payload: {outward_link_payload}",
        )

        self.assertEqual(
            observation.read_ticket_observation.result.exit_code,
            0,
            "Step 1 failed: executing the exact `trackstate read ticket --key TS-2` "
            "command did not succeed from a valid TrackState repository.\n"
            f"Repository path: {observation.read_ticket_observation.repository_path}\n"
            f"Executed command: {observation.read_ticket_observation.executed_command_text}\n"
            f"Observed exit code: {observation.read_ticket_observation.result.exit_code}\n"
            f"stdout:\n{observation.read_ticket_observation.result.stdout}\n"
            f"stderr:\n{observation.read_ticket_observation.result.stderr}",
        )

        payload = observation.read_ticket_observation.result.json_payload
        self.assertIsInstance(
            payload,
            dict,
            "Step 2 failed: the `trackstate read ticket --key TS-2` response was "
            "not a JSON object.\n"
            f"Observed stdout:\n{observation.read_ticket_observation.result.stdout}\n"
            f"Observed stderr:\n{observation.read_ticket_observation.result.stderr}",
        )
        assert isinstance(payload, dict)

        self.assertEqual(
            payload.get("key"),
            self.config.issue_b_key,
            "Step 2 failed: the read ticket response did not describe TS-2.\n"
            f"Observed payload: {payload}",
        )

        links = payload.get("links")
        self.assertIsInstance(
            links,
            list,
            "Step 2 failed: the read ticket response did not expose the expected "
            "`links` array in the JSON payload.\n"
            f"Observed payload: {payload}\n"
            f"Observed stdout:\n{observation.read_ticket_observation.result.stdout}",
        )
        assert isinstance(links, list)

        normalized_links = self._normalize_links(links)
        expected_links = self._normalize_links(list(self.config.expected_links_payload))

        self.assertEqual(
            len(links),
            2,
            "Expected result failed: the `links` array did not contain exactly two "
            "aggregated relationships for TS-2.\n"
            f"Observed links: {links}\n"
            f"Observed payload: {payload}",
        )
        self.assertEqual(
            normalized_links,
            expected_links,
            "Expected result failed: the read ticket JSON did not preserve both the "
            "inward and outward canonical link entries for TS-2.\n"
            f"Expected links: {self.config.expected_links_payload}\n"
            f"Observed links: {links}\n"
            f"Observed payload: {payload}",
        )

        for fragment in (
            f'"key": "{self.config.issue_b_key}"',
            '"links": [',
            f'"type": "{self.config.expected_inward_link_payload["type"]}"',
            f'"target": "{self.config.expected_inward_link_payload["target"]}"',
            f'"direction": "{self.config.expected_inward_link_payload["direction"]}"',
            f'"type": "{self.config.expected_outward_link_payload["type"]}"',
            f'"target": "{self.config.expected_outward_link_payload["target"]}"',
            f'"direction": "{self.config.expected_outward_link_payload["direction"]}"',
        ):
            self.assertIn(
                fragment,
                observation.read_ticket_observation.result.stdout,
                "Human-style verification failed: the visible CLI response did not "
                "show both canonical link entries a user would expect to read in the "
                "terminal.\n"
                f"Missing fragment: {fragment}\n"
                f"Observed stdout:\n{observation.read_ticket_observation.result.stdout}",
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
            "TS-675 must execute a repository-local compiled binary so the seeded "
            "repository remains isolated.\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Fallback reason: {observation.fallback_reason}",
        )
        self.assertEqual(
            observation.executed_command[0],
            observation.compiled_binary_path,
            f"{precondition_message}\n"
            "TS-675 did not run the compiled repository-local CLI binary.\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Compiled binary path: {observation.compiled_binary_path}",
        )

    def _assert_created_issue(
        self,
        *,
        observation: TrackStateCliCommandObservation,
        expected_key: str,
        expected_summary: str,
        failure_prefix: str,
    ) -> dict[str, object]:
        payload = self._assert_successful_json_object(
            observation=observation,
            failure_prefix=failure_prefix,
        )
        issue = payload["data"]["issue"]
        self.assertEqual(
            issue["key"],
            expected_key,
            f"{failure_prefix}: the create response returned an unexpected issue key.\n"
            f"Observed issue: {issue}",
        )
        self.assertEqual(
            issue["summary"],
            expected_summary,
            f"{failure_prefix}: the create response did not preserve the requested "
            "summary.\n"
            f"Observed issue: {issue}",
        )
        return issue

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
            f"{failure_prefix}: `{observation.requested_command_text}` did not return "
            "a data object.\n"
            f"Observed payload: {payload}",
        )
        return payload

    @staticmethod
    def _normalize_links(links: list[object]) -> list[tuple[tuple[str, str], ...]]:
        normalized_links: list[tuple[tuple[str, str], ...]] = []
        for link in links:
            if not isinstance(link, dict):
                raise AssertionError(
                    "Expected every link entry to be a JSON object.\n"
                    f"Observed link entry: {link!r}"
                )
            normalized_link = tuple(
                sorted((str(key), str(value)) for key, value in link.items())
            )
            normalized_links.append(normalized_link)
        return sorted(normalized_links)
