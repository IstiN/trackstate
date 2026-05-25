from __future__ import annotations

from pathlib import Path
import unittest

from testing.components.services.trackstate_cli_root_links_json_exclusivity_validator import (
    TrackStateCliRootLinksJsonExclusivityValidator,
)
from testing.core.config.trackstate_cli_root_links_json_exclusivity_config import (
    TrackStateCliRootLinksJsonExclusivityConfig,
)
from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)
from testing.core.models.trackstate_cli_root_links_json_exclusivity_result import (
    TrackStateCliRootLinksJsonExclusivityObservation,
)
from testing.tests.support.trackstate_cli_root_links_json_exclusivity_probe_factory import (
    create_trackstate_cli_root_links_json_exclusivity_probe,
)


class TrackStateCliRootLinksJsonExclusivityTest(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = TrackStateCliRootLinksJsonExclusivityConfig.from_defaults()
        self.validator = TrackStateCliRootLinksJsonExclusivityValidator(
            probe=create_trackstate_cli_root_links_json_exclusivity_probe(
                self.repository_root
            )
        )

    def test_links_json_exists_only_at_repository_root(self) -> None:
        observation = self.validator.validate(config=self.config).observation

        with self.subTest("step-1-create-issue-a"):
            self._assert_command_was_executed_exactly(
                observation=observation.issue_a_create_observation,
                expected_command=self.config.issue_a_create_command(
                    observation.issue_a_create_observation.repository_path
                ),
                precondition_message=(
                    "Step 1 failed: TS-1136 must create Issue A in the disposable "
                    "Local Git repository before linking it."
                ),
            )
            issue_a_payload = self._assert_successful_envelope(
                observation=observation.issue_a_create_observation,
                failure_prefix="Step 1 failed",
            )
            issue_a = issue_a_payload["data"]["issue"]
            self.assertEqual(
                issue_a["key"],
                self.config.issue_a_key,
                "Step 1 failed: the Issue A create response returned an unexpected "
                "issue key.\n"
                f"Observed issue: {issue_a}",
            )
            self.assertEqual(
                issue_a["summary"],
                self.config.issue_a_summary,
                "Step 1 failed: the Issue A create response did not preserve the "
                "requested summary.\n"
                f"Observed issue: {issue_a}",
            )

        with self.subTest("step-2-create-issue-b"):
            self._assert_command_was_executed_exactly(
                observation=observation.issue_b_create_observation,
                expected_command=self.config.issue_b_create_command(
                    observation.issue_b_create_observation.repository_path
                ),
                precondition_message=(
                    "Step 2 failed: TS-1136 must create Issue B in the disposable "
                    "Local Git repository before linking it."
                ),
            )
            issue_b_payload = self._assert_successful_envelope(
                observation=observation.issue_b_create_observation,
                failure_prefix="Step 2 failed",
            )
            issue_b = issue_b_payload["data"]["issue"]
            self.assertEqual(
                issue_b["key"],
                self.config.issue_b_key,
                "Step 2 failed: the Issue B create response returned an unexpected "
                "issue key.\n"
                f"Observed issue: {issue_b}",
            )
            self.assertEqual(
                issue_b["summary"],
                self.config.issue_b_summary,
                "Step 2 failed: the Issue B create response did not preserve the "
                "requested summary.\n"
                f"Observed issue: {issue_b}",
            )

        with self.subTest("step-3-link-issues"):
            self._assert_command_was_executed_exactly(
                observation=observation.link_observation,
                expected_command=self.config.link_command(
                    observation.link_observation.repository_path
                ),
                precondition_message=(
                    "Step 3 failed: TS-1136 must execute the exact non-hierarchical "
                    "link command from the ticket against the disposable Local Git "
                    "repository."
                ),
            )
            link_payload = self._assert_successful_envelope(
                observation=observation.link_observation,
                failure_prefix="Step 3 failed",
            )
            self.assertEqual(
                link_payload["data"]["command"],
                "ticket-link",
                "Step 3 failed: the link CLI response did not report the expected "
                "`ticket-link` command metadata.\n"
                f"Observed payload: {link_payload}",
            )
            self.assertEqual(
                link_payload["data"]["operation"],
                "link",
                "Step 3 failed: the link CLI response did not report the expected "
                "`link` operation metadata.\n"
                f"Observed payload: {link_payload}",
            )
            self.assertEqual(
                link_payload["data"]["link"],
                self.config.expected_link_payload,
                "Step 3 failed: the link CLI response did not preserve the requested "
                "non-hierarchical `blocks` relationship.\n"
                f"Expected link payload: {self.config.expected_link_payload}\n"
                f"Observed payload: {link_payload}",
            )

        with self.subTest("step-4-root-links-json-only"):
            root_links_payload = observation.root_links_json_payload
            self.assertIsInstance(
                root_links_payload,
                list,
                "Step 4 failed: the repository-root `links.json` file was not a JSON "
                "array.\n"
                f"Expected path: {observation.root_links_json_relative_path}\n"
                f"Observed files: {observation.discovered_links_json_files}\n"
                f"Observed content:\n{observation.root_links_json_content}",
            )
            assert isinstance(root_links_payload, list)
            self.assertEqual(
                root_links_payload,
                [self.config.expected_link_payload],
                "Step 4 failed: the repository-root `links.json` file did not contain "
                "exactly the expected non-hierarchical link record.\n"
                f"Expected path: {observation.root_links_json_relative_path}\n"
                f"Expected payload: {[self.config.expected_link_payload]}\n"
                f"Observed payload: {root_links_payload}\n"
                f"Observed files detail:\n{self._format_links_json_snapshots(observation)}",
            )
            self.assertEqual(
                observation.discovered_links_json_files,
                (observation.root_links_json_relative_path,),
                "Expected result failed: the link metadata was not stored exclusively "
                "at the repository root.\n"
                f"Expected files: {(observation.root_links_json_relative_path,)}\n"
                f"Observed files: {observation.discovered_links_json_files}\n"
                f"Observed files detail:\n{self._format_links_json_snapshots(observation)}",
            )

        with self.subTest("step-5-inspect-issue-directories"):
            self.assertIn(
                "main.md",
                observation.issue_a_directory_entries,
                "Step 5 failed: Issue A's directory did not contain its visible "
                "`main.md` issue artifact.\n"
                f"Directory: {observation.issue_a_directory_relative_path}\n"
                f"Observed entries: {observation.issue_a_directory_entries}",
            )
            self.assertIn(
                "main.md",
                observation.issue_b_directory_entries,
                "Step 5 failed: Issue B's directory did not contain its visible "
                "`main.md` issue artifact.\n"
                f"Directory: {observation.issue_b_directory_relative_path}\n"
                f"Observed entries: {observation.issue_b_directory_entries}",
            )
            self.assertNotIn(
                "links.json",
                observation.issue_a_directory_entries,
                "Expected result failed: Issue A persisted a redundant `links.json` "
                "artifact in its own directory.\n"
                f"Directory: {observation.issue_a_directory_relative_path}\n"
                f"Observed entries: {observation.issue_a_directory_entries}\n"
                f"Observed files detail:\n{self._format_links_json_snapshots(observation)}",
            )
            self.assertNotIn(
                "links.json",
                observation.issue_b_directory_entries,
                "Expected result failed: Issue B persisted a redundant `links.json` "
                "artifact in its own directory.\n"
                f"Directory: {observation.issue_b_directory_relative_path}\n"
                f"Observed entries: {observation.issue_b_directory_entries}\n"
                f"Observed files detail:\n{self._format_links_json_snapshots(observation)}",
            )
            self.assertIsNotNone(
                observation.issue_a_main_content,
                "Human-style verification failed: Issue A's `main.md` file was not "
                "readable after the link mutation.\n"
                f"Expected path: {observation.issue_a_main_relative_path}",
            )
            self.assertIsNotNone(
                observation.issue_b_main_content,
                "Human-style verification failed: Issue B's `main.md` file was not "
                "readable after the link mutation.\n"
                f"Expected path: {observation.issue_b_main_relative_path}",
            )
            assert observation.issue_a_main_content is not None
            assert observation.issue_b_main_content is not None
            self.assertIn(
                "# Summary",
                observation.issue_a_main_content,
                "Human-style verification failed: Issue A's markdown did not expose "
                "the visible summary heading a user would inspect.\n"
                f"Observed main.md:\n{observation.issue_a_main_content}",
            )
            self.assertIn(
                self.config.issue_a_summary,
                observation.issue_a_main_content,
                "Human-style verification failed: Issue A's markdown did not show the "
                "requested visible summary text.\n"
                f"Observed main.md:\n{observation.issue_a_main_content}",
            )
            self.assertIn(
                "# Summary",
                observation.issue_b_main_content,
                "Human-style verification failed: Issue B's markdown did not expose "
                "the visible summary heading a user would inspect.\n"
                f"Observed main.md:\n{observation.issue_b_main_content}",
            )
            self.assertIn(
                self.config.issue_b_summary,
                observation.issue_b_main_content,
                "Human-style verification failed: Issue B's markdown did not show the "
                "requested visible summary text.\n"
                f"Observed main.md:\n{observation.issue_b_main_content}",
            )

            for fragment in (
                '"ok": true',
                '"command": "ticket-link"',
                f'"type": "{self.config.expected_link_payload["type"]}"',
                f'"target": "{self.config.expected_link_payload["target"]}"',
                f'"direction": "{self.config.expected_link_payload["direction"]}"',
            ):
                self.assertIn(
                    fragment,
                    observation.link_observation.result.stdout,
                    "Human-style verification failed: the visible CLI success output "
                    "did not show the relationship confirmation a user would read in "
                    "the terminal after linking the two issues.\n"
                    f"Missing fragment: {fragment}\n"
                    f"Observed stdout:\n{observation.link_observation.result.stdout}",
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
            "TS-1136 must execute a repository-local compiled binary so the seeded "
            "repository remains isolated.\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Fallback reason: {observation.fallback_reason}",
        )
        self.assertEqual(
            observation.executed_command[0],
            observation.compiled_binary_path,
            f"{precondition_message}\n"
            "TS-1136 did not run the compiled repository-local CLI binary.\n"
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
            f"{failure_prefix}: `{observation.requested_command_text}` returned a JSON "
            "envelope without an `ok: true` success marker.\n"
            f"Observed payload: {payload}",
        )
        self.assertIn(
            "data",
            payload,
            f"{failure_prefix}: `{observation.requested_command_text}` did not include "
            "a `data` object in its success envelope.\n"
            f"Observed payload: {payload}",
        )
        return payload

    @staticmethod
    def _format_links_json_snapshots(
        observation: TrackStateCliRootLinksJsonExclusivityObservation,
    ) -> str:
        if not observation.discovered_links_json_snapshots:
            return "<none>"
        return "\n\n".join(
            "\n".join(
                (
                    f"Path: {snapshot.relative_path}",
                    f"Payload: {snapshot.payload}",
                    f"Content:\n{snapshot.content}",
                )
            )
            for snapshot in observation.discovered_links_json_snapshots
        )


if __name__ == "__main__":
    unittest.main()
