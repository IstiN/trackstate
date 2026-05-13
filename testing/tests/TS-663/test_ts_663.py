from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import unittest

from testing.components.services.trackstate_cli_self_link_guard_validator import (
    TrackStateCliSelfLinkGuardValidator,
)
from testing.core.config.trackstate_cli_self_link_guard_config import (
    TrackStateCliSelfLinkGuardConfig,
)
from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)
from testing.core.models.trackstate_cli_self_link_guard_result import (
    TrackStateCliSelfLinkGuardObservation,
)
from testing.tests.support.trackstate_cli_self_link_guard_probe_factory import (
    create_trackstate_cli_self_link_guard_probe,
)


class TrackStateCliMixedCaseSelfLinkGuardTest(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = self._build_config()
        self.validator = TrackStateCliSelfLinkGuardValidator(
            probe=create_trackstate_cli_self_link_guard_probe(self.repository_root)
        )

    def test_mixed_case_self_link_returns_validation_error_without_persisting_metadata(
        self,
    ) -> None:
        observation = self.validator.validate(config=self.config).observation

        self._assert_command_was_executed_exactly(
            observation=observation.issue_a_create_observation,
            expected_command=self.config.issue_a_create_command(
                observation.issue_a_create_observation.repository_path
            ),
            precondition_message=(
                "Precondition failed: TS-663 must create Issue A in the disposable "
                "Local Git repository before attempting the mixed-case "
                "self-referencing link."
            ),
        )
        self._assert_command_was_executed_exactly(
            observation=observation.self_link_observation,
            expected_command=self.config.self_link_command(
                observation.self_link_observation.repository_path
            ),
            precondition_message=(
                "Step 1 failed: TS-663 must execute the exact mixed-case self-link "
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

        self_link_payload = self._assert_failed_envelope(
            observation=observation.self_link_observation,
            failure_prefix="Step 2 failed",
        )
        self.assertEqual(
            self_link_payload.get("provider"),
            "local-git",
            "Step 2 failed: the mixed-case self-link CLI response did not identify "
            "the Local Git provider in the visible error envelope.\n"
            f"Observed payload: {self_link_payload}",
        )

        error_payload = self_link_payload.get("error")
        self.assertIsInstance(
            error_payload,
            dict,
            "Step 2 failed: the CLI response did not include an `error` object for "
            "the mixed-case self-referencing link attempt.\n"
            f"Observed payload: {self_link_payload}",
        )
        assert isinstance(error_payload, dict)
        self.assertEqual(
            error_payload.get("code"),
            self.config.expected_error_code,
            "Expected result failed: the CLI did not classify the mixed-case "
            "self-link attempt as a validation mutation error.\n"
            f"Observed error payload: {error_payload}",
        )
        self.assertEqual(
            error_payload.get("category"),
            self.config.expected_error_category,
            "Expected result failed: the CLI did not report the mixed-case "
            "self-link attempt under the validation error category.\n"
            f"Observed error payload: {error_payload}",
        )
        self.assertEqual(
            error_payload.get("exitCode"),
            self.config.expected_error_exit_code,
            "Expected result failed: the CLI did not surface the expected "
            "validation exit code for a mixed-case self-referencing link.\n"
            f"Observed error payload: {error_payload}",
        )

        error_message = error_payload.get("message")
        self.assertIsInstance(
            error_message,
            str,
            "Expected result failed: the CLI error payload did not include a "
            "descriptive message for the mixed-case self-referencing link "
            "attempt.\n"
            f"Observed error payload: {error_payload}",
        )
        assert isinstance(error_message, str)
        normalized_message = error_message.lower()
        for fragment in self.config.expected_error_message_fragments:
            self.assertIn(
                fragment.lower(),
                normalized_message,
                "Expected result failed: the CLI error message did not make it clear "
                "that the issue cannot be linked to itself regardless of key "
                "casing.\n"
                f"Required fragment: {fragment}\n"
                f"Observed message: {error_message}",
            )

        error_details = error_payload.get("details")
        self.assertIsInstance(
            error_details,
            dict,
            "Step 2 failed: the CLI error response did not expose details for the "
            "mixed-case self-referencing link attempt.\n"
            f"Observed error payload: {error_payload}",
        )
        assert isinstance(error_details, dict)
        self.assertEqual(
            error_details.get("operation"),
            "link",
            "Expected result failed: the CLI error details did not preserve the "
            "ticket-link operation name.\n"
            f"Observed error details: {error_details}",
        )
        self.assertEqual(
            error_details.get("issueKey"),
            self.config.issue_a_key,
            "Expected result failed: the CLI error details did not preserve the "
            "source issue key from the attempted mixed-case self-link command.\n"
            f"Observed error details: {error_details}",
        )

        self.assertEqual(
            observation.discovered_links_json_files,
            (),
            "Expected result failed: the mixed-case self-link mutation still "
            "produced a `links.json` file even though the CLI should reject the "
            "relationship.\n"
            f"Observed files: {observation.discovered_links_json_files}\n"
            f"Observed files detail:\n{self._format_links_json_snapshots(observation)}",
        )
        self.assertIsNone(
            observation.links_json_content,
            "Expected result failed: the source issue still has persisted link "
            "metadata after the mixed-case self-link attempt should have been "
            "rejected.\n"
            f"Unexpected path: {observation.links_json_relative_path}\n"
            f"Observed content:\n{observation.links_json_content}\n"
            f"Observed files detail:\n{self._format_links_json_snapshots(observation)}",
        )
        self.assertIsNone(
            observation.links_json_payload,
            "Expected result failed: the source issue still has parsed link "
            "metadata after the mixed-case self-link attempt should have been "
            "rejected.\n"
            f"Unexpected path: {observation.links_json_relative_path}\n"
            f"Observed payload: {observation.links_json_payload}\n"
            f"Observed files detail:\n{self._format_links_json_snapshots(observation)}",
        )

        for fragment in (
            '"ok": false',
            f'"code": "{self.config.expected_error_code}"',
            f'"exitCode": {self.config.expected_error_exit_code}',
            f'"issueKey": "{self.config.issue_a_key}"',
        ):
            self.assertIn(
                fragment,
                observation.self_link_observation.result.stdout,
                "Human-style verification failed: the visible CLI JSON output did not "
                "show the rejection details a user would read in the terminal after "
                "attempting the mixed-case self-referencing relationship.\n"
                f"Missing fragment: {fragment}\n"
                f"Observed stdout:\n{observation.self_link_observation.result.stdout}",
            )

    def _build_config(self) -> TrackStateCliSelfLinkGuardConfig:
        base_config = TrackStateCliSelfLinkGuardConfig.from_defaults()
        return replace(
            base_config,
            test_id="TS-663",
            project_name="TS-663 Mixed Case Self Link Guard Project",
            expected_author_email="ts663@example.com",
            self_link_command_prefix=(
                "trackstate",
                "ticket",
                "link",
                "--target",
                "local",
                "--key",
                "TS-1",
                "--target-key",
                "ts-1",
                "--type",
                "relates to",
            ),
            expected_error_message_fragments=("ts-1", "itself"),
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
            "TS-663 must execute a repository-local compiled binary so the seeded "
            "repository remains isolated.\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Fallback reason: {observation.fallback_reason}",
        )
        self.assertEqual(
            observation.executed_command[0],
            observation.compiled_binary_path,
            f"{precondition_message}\n"
            "TS-663 did not run the compiled repository-local CLI binary.\n"
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

    def _assert_failed_envelope(
        self,
        *,
        observation: TrackStateCliCommandObservation,
        failure_prefix: str,
    ) -> dict[str, object]:
        self.assertEqual(
            observation.result.exit_code,
            self.config.expected_error_exit_code,
            f"{failure_prefix}: executing `{observation.requested_command_text}` did "
            "not return the expected validation exit code for a mixed-case "
            "self-referencing link.\n"
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
            "a JSON object failure envelope.\n"
            f"stdout:\n{observation.result.stdout}\n"
            f"stderr:\n{observation.result.stderr}",
        )
        assert isinstance(payload, dict)
        self.assertFalse(
            payload.get("ok"),
            f"{failure_prefix}: `{observation.requested_command_text}` unexpectedly "
            "reported success for a mixed-case self-referencing link.\n"
            f"Observed payload: {payload}",
        )
        return payload

    @staticmethod
    def _format_links_json_snapshots(
        observation: TrackStateCliSelfLinkGuardObservation,
    ) -> str:
        if not observation.discovered_links_json_snapshots:
            return "<none>"
        return "\n".join(
            f"- {snapshot.relative_path}\n{snapshot.content or '<empty>'}"
            for snapshot in observation.discovered_links_json_snapshots
        )


if __name__ == "__main__":
    unittest.main()
