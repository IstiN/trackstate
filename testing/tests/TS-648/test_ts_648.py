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
from testing.tests.support.trackstate_cli_inverse_link_canonical_storage_probe_factory import (
    create_trackstate_cli_inverse_link_canonical_storage_probe,
)


class TrackStateJiraLinkIssuesCanonicalPayloadTest(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = TrackStateCliInverseLinkCanonicalStorageConfig(
            test_id="TS-648",
            project_key="TS",
            project_name="TS-648 Jira Link Issues Canonical Payload Project",
            seed_issue_key="TS-0",
            expected_author_email="ts648@example.com",
            issue_a_summary="Issue A",
            issue_b_summary="Issue B",
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
            inverse_link_command_prefix=(
                "trackstate",
                "jira-link-issues",
                "--target",
                "local",
                "--key",
                "TS-1",
                "--target-key",
                "TS-2",
                "--type",
                "is blocked by",
            ),
            expected_canonical_link_payload={
                "type": "blocks",
                "target": "TS-1",
                "direction": "outward",
            },
        )
        self.validator = TrackStateCliInverseLinkCanonicalStorageValidator(
            probe=create_trackstate_cli_inverse_link_canonical_storage_probe(
                self.repository_root
            )
        )

    def test_jira_link_issues_returns_canonical_relationship_metadata(self) -> None:
        observation = self.validator.validate(config=self.config).observation

        self._assert_command_was_executed_exactly(
            observation=observation.issue_a_create_observation,
            expected_command=self.config.issue_a_create_command(
                observation.issue_a_create_observation.repository_path
            ),
            precondition_message=(
                "Precondition failed: TS-648 must create Issue A in the disposable "
                "Local Git repository before attempting the Jira-compatible link."
            ),
        )
        self._assert_command_was_executed_exactly(
            observation=observation.issue_b_create_observation,
            expected_command=self.config.issue_b_create_command(
                observation.issue_b_create_observation.repository_path
            ),
            precondition_message=(
                "Precondition failed: TS-648 must create Issue B in the disposable "
                "Local Git repository before attempting the Jira-compatible link."
            ),
        )
        self._assert_command_was_executed_exactly(
            observation=observation.inverse_link_observation,
            expected_command=self.config.inverse_link_command(
                observation.inverse_link_observation.repository_path
            ),
            precondition_message=(
                "Step 1 failed: TS-648 must execute the exact `trackstate "
                "jira-link-issues --key TS-1 --target-key TS-2 --type \"is blocked "
                "by\"` command from the ticket against the disposable Local Git "
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
            failure_prefix="Step 2 failed",
        )
        self.assertEqual(
            link_payload["data"]["command"],
            "jira-link-issues",
            "Step 2 failed: the Jira-compatible CLI response did not report the "
            "expected `jira-link-issues` command metadata.\n"
            f"Observed payload: {link_payload}",
        )
        self.assertEqual(
            link_payload["data"]["operation"],
            "link",
            "Step 2 failed: the Jira-compatible CLI response did not report the "
            "expected `link` operation metadata.\n"
            f"Observed payload: {link_payload}",
        )

        observed_link_payload = link_payload["data"].get("link")
        self.assertIsInstance(
            observed_link_payload,
            dict,
            "Step 2 failed: the CLI response did not include a relationship object "
            "in `data.link`.\n"
            f"Observed payload: {link_payload}\n"
            f"Observed stdout:\n{observation.inverse_link_observation.result.stdout}",
        )
        assert isinstance(observed_link_payload, dict)
        self.assertEqual(
            observed_link_payload,
            self.config.expected_canonical_link_payload,
            "Expected result failed: the visible Jira-compatible CLI response payload "
            "did not return canonical relationship metadata.\n"
            f"Expected link payload: {self.config.expected_canonical_link_payload}\n"
            f"Observed link payload: {observed_link_payload}\n"
            f"Observed stdout:\n{observation.inverse_link_observation.result.stdout}",
        )

        issue_payload = link_payload["data"].get("issue")
        self.assertIsInstance(
            issue_payload,
            dict,
            "Step 2 failed: the CLI response did not include the linked issue "
            "object in `data.issue`.\n"
            f"Observed payload: {link_payload}",
        )
        assert isinstance(issue_payload, dict)
        self.assertEqual(
            issue_payload.get("key"),
            self.config.issue_a_key,
            "Expected result failed: the visible Jira-compatible CLI response "
            "should remain anchored to Issue A after canonical normalization.\n"
            f"Observed issue payload: {issue_payload}",
        )
        self.assertEqual(
            issue_payload.get("summary"),
            self.config.issue_a_summary,
            "Human-style verification failed: the visible CLI response did not "
            "show the expected Issue A summary next to the normalized link "
            "metadata.\n"
            f"Observed issue payload: {issue_payload}\n"
            f"Observed stdout:\n{observation.inverse_link_observation.result.stdout}",
        )

        for fragment in (
            '"command": "jira-link-issues"',
            '"type": "blocks"',
            '"target": "TS-1"',
            '"direction": "outward"',
            '"summary": "Issue A"',
        ):
            self.assertIn(
                fragment,
                observation.inverse_link_observation.result.stdout,
                "Human-style verification failed: the visible CLI JSON output did "
                "not show the normalized Jira-compatible relationship details a "
                "user would read in the terminal.\n"
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
            "TS-648 must execute a repository-local compiled binary so the seeded "
            "repository remains isolated.\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Fallback reason: {observation.fallback_reason}",
        )
        self.assertEqual(
            observation.executed_command[0],
            observation.compiled_binary_path,
            f"{precondition_message}\n"
            "TS-648 did not run the compiled repository-local CLI binary.\n"
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


if __name__ == "__main__":
    unittest.main()
