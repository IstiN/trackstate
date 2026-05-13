from __future__ import annotations

from pathlib import Path
import unittest

from testing.components.services.trackstate_cli_invalid_link_type_validator import (
    TrackStateCliInvalidLinkTypeValidator,
)
from testing.core.config.trackstate_cli_invalid_link_type_config import (
    TrackStateCliInvalidLinkTypeConfig,
)
from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)
from testing.tests.support.trackstate_cli_invalid_link_type_probe_factory import (
    create_trackstate_cli_invalid_link_type_probe,
)


class TrackStateCliUnsupportedRelationshipTypeTest(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = self._build_config()
        self.validator = TrackStateCliInvalidLinkTypeValidator(
            probe=create_trackstate_cli_invalid_link_type_probe(self.repository_root)
        )

    def test_unsupported_relationship_type_returns_error_and_creates_no_link(self) -> None:
        observation = self.validator.validate(config=self.config).observation

        self._assert_command_was_executed_exactly(
            observation=observation.issue_a_create_observation,
            expected_command=self.config.issue_a_create_command(
                observation.issue_a_create_observation.repository_path
            ),
            precondition_message=(
                "Precondition failed: TS-658 must create Issue A in the disposable "
                "Local Git repository before attempting the invalid link mutation."
            ),
        )
        self._assert_command_was_executed_exactly(
            observation=observation.issue_b_create_observation,
            expected_command=self.config.issue_b_create_command(
                observation.issue_b_create_observation.repository_path
            ),
            precondition_message=(
                "Precondition failed: TS-658 must create Issue B in the disposable "
                "Local Git repository before attempting the invalid link mutation."
            ),
        )
        self._assert_command_was_executed_exactly(
            observation=observation.invalid_link_observation,
            expected_command=self.config.invalid_link_command(
                observation.invalid_link_observation.repository_path
            ),
            precondition_message=(
                "Step 1 failed: TS-658 must execute the exact invalid link command "
                "from the ticket against the disposable Local Git repository."
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

        invalid_link_payload = self._assert_failed_envelope(
            observation=observation.invalid_link_observation,
            failure_prefix="Step 2 failed",
        )
        self.assertEqual(
            invalid_link_payload.get("provider"),
            "local-git",
            "Step 2 failed: the invalid-link CLI response did not identify the Local "
            "Git provider in the visible error envelope.\n"
            f"Observed payload: {invalid_link_payload}",
        )

        error_payload = invalid_link_payload.get("error")
        self.assertIsInstance(
            error_payload,
            dict,
            "Step 2 failed: the CLI response did not include an `error` object for "
            "the unsupported link type.\n"
            f"Observed payload: {invalid_link_payload}",
        )
        assert isinstance(error_payload, dict)
        self.assertEqual(
            error_payload.get("code"),
            self.config.expected_error_code,
            "Expected result failed: the CLI did not classify the unsupported link "
            "type as a validation mutation error.\n"
            f"Observed error payload: {error_payload}",
        )
        self.assertEqual(
            error_payload.get("category"),
            self.config.expected_error_category,
            "Expected result failed: the CLI did not report the unsupported link "
            "type under the validation error category.\n"
            f"Observed error payload: {error_payload}",
        )
        self.assertEqual(
            error_payload.get("exitCode"),
            self.config.expected_error_exit_code,
            "Expected result failed: the CLI did not surface the expected validation "
            "exit code for the unsupported link type.\n"
            f"Observed error payload: {error_payload}",
        )
        self.assertEqual(
            error_payload.get("message"),
            self.config.expected_error_message,
            "Expected result failed: the CLI did not return the descriptive invalid "
            "link type message required by the ticket.\n"
            f"Expected message: {self.config.expected_error_message}\n"
            f"Observed error payload: {error_payload}",
        )

        error_details = error_payload.get("details")
        self.assertIsInstance(
            error_details,
            dict,
            "Step 2 failed: the CLI error response did not expose details for the "
            "unsupported link mutation.\n"
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
            "source issue key from the attempted link command.\n"
            f"Observed error details: {error_details}",
        )

        self.assertEqual(
            observation.discovered_links_json_files,
            (),
            "Expected result failed: the unsupported link mutation still produced a "
            "`links.json` file even though the CLI reported a validation error.\n"
            f"Observed links.json files: {observation.discovered_links_json_files}",
        )

        for fragment in (
            '"ok": false',
            f'"message": "{self.config.expected_error_message}"',
            f'"issueKey": "{self.config.issue_a_key}"',
            self.config.unsupported_link_type_label,
        ):
            self.assertIn(
                fragment,
                observation.invalid_link_observation.result.stdout,
                "Human-style verification failed: the visible CLI JSON output did not "
                "show the unsupported-link failure details a user would read in the "
                "terminal.\n"
                f"Missing fragment: {fragment}\n"
                f"Observed stdout:\n{observation.invalid_link_observation.result.stdout}",
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
            "TS-658 must execute a repository-local compiled binary so the seeded "
            "repository remains isolated.\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Fallback reason: {observation.fallback_reason}",
        )
        self.assertEqual(
            observation.executed_command[0],
            observation.compiled_binary_path,
            f"{precondition_message}\n"
            "TS-658 did not run the compiled repository-local CLI binary.\n"
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
            "not return the expected validation exit code for an unsupported link "
            "type.\n"
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
            "reported success for an unsupported link type.\n"
            f"Observed payload: {payload}",
        )
        return payload

    @staticmethod
    def _build_config() -> TrackStateCliInvalidLinkTypeConfig:
        unsupported_link_type_label = "unsupported-relationship-type"
        return TrackStateCliInvalidLinkTypeConfig(
            test_id="TS-658",
            project_key="TS",
            project_name="TS-658 Invalid Link Type Project",
            seed_issue_key="TS-0",
            expected_author_email="ts658@example.com",
            issue_a_summary="Issue A",
            issue_b_summary="Issue B",
            unsupported_link_type_label=unsupported_link_type_label,
            issue_a_create_command_prefix=(
                "trackstate",
                "ticket",
                "create",
                "--target",
                "local",
                "--summary",
                "Issue A",
                "--issue-type",
                "Story",
            ),
            issue_b_create_command_prefix=(
                "trackstate",
                "ticket",
                "create",
                "--target",
                "local",
                "--summary",
                "Issue B",
                "--issue-type",
                "Story",
            ),
            invalid_link_command_prefix=(
                "trackstate",
                "ticket",
                "link",
                "--target",
                "local",
                "--key",
                "TS-1",
                "--target-key",
                "TS-2",
                "--type",
                unsupported_link_type_label,
            ),
            expected_error_code="INVALID_MUTATION",
            expected_error_category="validation",
            expected_error_exit_code=2,
        )


if __name__ == "__main__":
    unittest.main()
