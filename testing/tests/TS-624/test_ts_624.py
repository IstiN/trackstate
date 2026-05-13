from __future__ import annotations

from pathlib import Path
import unittest

from testing.components.services.trackstate_cli_inverse_link_canonical_storage_validator import (
    TrackStateCliInverseLinkCanonicalStorageValidator,
)
from testing.core.config.trackstate_cli_inverse_link_canonical_storage_config import (
    TrackStateCliInverseLinkCanonicalStorageConfig,
)
from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)
from testing.core.models.trackstate_cli_inverse_link_canonical_storage_result import (
    TrackStateCliInverseLinkCanonicalStorageObservation,
)
from testing.tests.support.trackstate_cli_inverse_link_canonical_storage_probe_factory import (
    create_trackstate_cli_inverse_link_canonical_storage_probe,
)


class TrackStateCliInverseLinkCanonicalStorageTest(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = TrackStateCliInverseLinkCanonicalStorageConfig.from_defaults()
        self.validator = TrackStateCliInverseLinkCanonicalStorageValidator(
            probe=create_trackstate_cli_inverse_link_canonical_storage_probe(
                self.repository_root
            )
        )

    def test_inverse_link_label_is_persisted_in_canonical_direction(self) -> None:
        observation = self.validator.validate(config=self.config).observation

        self._assert_command_was_executed_exactly(
            observation=observation.issue_a_create_observation,
            expected_command=self.config.issue_a_create_command(
                observation.issue_a_create_observation.repository_path
            ),
            precondition_message=(
                "Precondition failed: TS-624 must create Issue A in the disposable "
                "Local Git repository before attempting the inverse link."
            ),
        )
        self._assert_command_was_executed_exactly(
            observation=observation.issue_b_create_observation,
            expected_command=self.config.issue_b_create_command(
                observation.issue_b_create_observation.repository_path
            ),
            precondition_message=(
                "Precondition failed: TS-624 must create Issue B in the disposable "
                "Local Git repository before attempting the inverse link."
            ),
        )
        self._assert_command_was_executed_exactly(
            observation=observation.inverse_link_observation,
            expected_command=self.config.inverse_link_command(
                observation.inverse_link_observation.repository_path
            ),
            precondition_message=(
                "Step 1 failed: TS-624 must execute the exact inverse-label link "
                "command from the ticket against the disposable Local Git "
                "repository."
            ),
        )

        issue_a_payload = self._assert_successful_envelope(
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

        issue_b_payload = self._assert_successful_envelope(
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

        link_payload = self._assert_successful_envelope(
            observation=observation.inverse_link_observation,
            failure_prefix="Step 1 failed",
        )
        self.assertEqual(
            link_payload["data"]["command"],
            "ticket-link",
            "Step 1 failed: the inverse-link CLI response did not report the "
            "canonical `ticket-link` operation.\n"
            f"Observed payload: {link_payload}",
        )

        target_links_payload = observation.target_links_json_payload
        self.assertIsInstance(
            target_links_payload,
            list,
            "Step 2 failed: inspecting the target issue `links.json` did not yield "
            "a JSON array at the canonical storage location.\n"
            f"Expected canonical path: {observation.target_links_json_relative_path}\n"
            f"Observed source path: {observation.source_links_json_relative_path}\n"
            f"Discovered links.json files: {observation.discovered_links_json_files}\n"
            f"Observed files:\n{self._format_links_json_snapshots(observation)}",
        )
        assert isinstance(target_links_payload, list)
        self.assertEqual(
            target_links_payload,
            [self.config.expected_canonical_link_payload],
            "Step 2 failed: the persisted `links.json` content was not normalized to "
            "the canonical stored `blocks` relation from Issue B back to Issue A.\n"
            f"Expected canonical path: {observation.target_links_json_relative_path}\n"
            f"Expected payload: {[self.config.expected_canonical_link_payload]}\n"
            f"Observed payload: {target_links_payload}\n"
            f"Discovered links.json files: {observation.discovered_links_json_files}\n"
            f"Observed files:\n{self._format_links_json_snapshots(observation)}",
        )
        self.assertEqual(
            observation.discovered_links_json_files,
            (observation.target_links_json_relative_path,),
            "Expected result failed: the repository did not store exactly one "
            "`links.json` file at the canonical target issue location after inverse "
            "normalization.\n"
            f"Expected path: {observation.target_links_json_relative_path}\n"
            f"Observed files: {observation.discovered_links_json_files}\n"
            f"Observed files detail:\n{self._format_links_json_snapshots(observation)}",
        )
        self.assertIsNone(
            observation.source_links_json_content,
            "Expected result failed: the source issue still has a `links.json` file, "
            "so the inverse wording was not rewritten into canonical stored form on "
            "Issue B.\n"
            f"Unexpected source path: {observation.source_links_json_relative_path}\n"
            f"Observed content:\n{observation.source_links_json_content}\n"
            f"Observed files detail:\n{self._format_links_json_snapshots(observation)}",
        )

        for fragment in (
            '"command": "ticket-link"',
            f'"key": "{self.config.issue_a_key}"',
            f'"target": "{self.config.issue_b_key}"',
        ):
            self.assertIn(
                fragment,
                observation.inverse_link_observation.result.stdout,
                "Human-style verification failed: the visible CLI response did not "
                "show the expected ticket-link confirmation details a user would "
                "see immediately after running the inverse-label command.\n"
                f"Missing fragment: {fragment}\n"
                f"Observed stdout:\n{observation.inverse_link_observation.result.stdout}",
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
            "TS-624 must execute a repository-local compiled binary so the seeded "
            "repository remains isolated.\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Fallback reason: {observation.fallback_reason}",
        )
        self.assertEqual(
            observation.executed_command[0],
            observation.compiled_binary_path,
            f"{precondition_message}\n"
            "TS-624 did not run the compiled repository-local CLI binary.\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Compiled binary path: {observation.compiled_binary_path}",
        )

    def _assert_successful_envelope(
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

    @staticmethod
    def _format_links_json_snapshots(
        observation: TrackStateCliInverseLinkCanonicalStorageObservation,
    ) -> str:
        if not observation.discovered_links_json_snapshots:
            return "<none>"
        fragments: list[str] = []
        for snapshot in observation.discovered_links_json_snapshots:
            fragments.append(f"{snapshot.relative_path}:\n{snapshot.content}")
        return "\n\n".join(fragments)


if __name__ == "__main__":
    unittest.main()
