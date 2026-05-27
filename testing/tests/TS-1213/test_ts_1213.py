from __future__ import annotations

from pathlib import Path
import unittest

from testing.components.services.trackstate_cli_legacy_local_links_json_purge_validator import (
    TrackStateCliLegacyLocalLinksJsonPurgeValidator,
)
from testing.core.config.trackstate_cli_legacy_local_links_json_purge_config import (
    TrackStateCliLegacyLocalLinksJsonPurgeConfig,
)
from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)
from testing.core.models.trackstate_cli_legacy_local_links_json_purge_result import (
    TrackStateCliLegacyLocalLinksJsonPurgeObservation,
)
from testing.tests.support.trackstate_cli_legacy_local_links_json_purge_probe_factory import (
    create_trackstate_cli_legacy_local_links_json_purge_probe,
)


class TrackStateCliLegacyLocalLinksJsonPurgeTest(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = TrackStateCliLegacyLocalLinksJsonPurgeConfig.from_defaults()
        self.validator = TrackStateCliLegacyLocalLinksJsonPurgeValidator(
            probe=create_trackstate_cli_legacy_local_links_json_purge_probe(
                self.repository_root
            )
        )

    def test_link_operation_purges_legacy_issue_local_links_json(self) -> None:
        observation = self.validator.validate(config=self.config).observation

        with self.subTest("precondition-create-source-issue"):
            self._assert_command_was_executed_exactly(
                observation=observation.issue_a_create_observation,
                expected_command=self.config.issue_a_create_command(
                    observation.issue_a_create_observation.repository_path
                ),
                precondition_message=(
                    "Precondition failed: TS-1213 must create the source issue in the "
                    "disposable Local Git repository before seeding legacy metadata."
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
                "Precondition failed: the source issue create response returned an "
                "unexpected issue key.\n"
                f"Observed issue: {issue_a}",
            )
            self.assertEqual(
                issue_a["summary"],
                self.config.issue_a_summary,
                "Precondition failed: the source issue create response did not "
                "preserve the requested summary.\n"
                f"Observed issue: {issue_a}",
            )

        with self.subTest("precondition-seed-legacy-links-json"):
            expected_legacy_payload = list(self.config.legacy_links_json_payload)
            self.assertIn(
                "links.json",
                observation.issue_a_directory_entries_before_link,
                "Precondition failed: the legacy issue-local `links.json` file was not "
                "created inside the source issue directory before linking.\n"
                f"Directory: {observation.issue_a_directory_relative_path}\n"
                "Observed entries before linking: "
                f"{observation.issue_a_directory_entries_before_link}",
            )
            self.assertEqual(
                observation.legacy_links_json_payload_before_link,
                expected_legacy_payload,
                "Precondition failed: the seeded legacy issue-local `links.json` file "
                "did not contain the expected stale payload before the live link "
                "operation.\n"
                f"Expected path: {observation.legacy_links_json_relative_path}\n"
                f"Expected payload: {expected_legacy_payload}\n"
                "Observed payload before linking: "
                f"{observation.legacy_links_json_payload_before_link}\n"
                f"Observed content:\n{observation.legacy_links_json_content_before_link}",
            )

        with self.subTest("precondition-create-target-issue"):
            self._assert_command_was_executed_exactly(
                observation=observation.issue_b_create_observation,
                expected_command=self.config.issue_b_create_command(
                    observation.issue_b_create_observation.repository_path
                ),
                precondition_message=(
                    "Precondition failed: TS-1213 must create the target issue in the "
                    "disposable Local Git repository before linking it."
                ),
            )
            issue_b_payload = self._assert_successful_envelope(
                observation=observation.issue_b_create_observation,
                failure_prefix="Precondition failed",
            )
            issue_b = issue_b_payload["data"]["issue"]
            self.assertEqual(
                issue_b["key"],
                self.config.issue_b_key,
                "Precondition failed: the target issue create response returned an "
                "unexpected issue key.\n"
                f"Observed issue: {issue_b}",
            )
            self.assertEqual(
                issue_b["summary"],
                self.config.issue_b_summary,
                "Precondition failed: the target issue create response did not "
                "preserve the requested summary.\n"
                f"Observed issue: {issue_b}",
            )

        with self.subTest("step-1-execute-link-command"):
            self._assert_command_was_executed_exactly(
                observation=observation.link_observation,
                expected_command=self.config.link_command(
                    observation.link_observation.repository_path
                ),
                precondition_message=(
                    "Step 1 failed: TS-1213 must execute the exact non-hierarchical "
                    "link command from the ticket against the disposable Local Git "
                    "repository."
                ),
            )
            link_payload = self._assert_successful_envelope(
                observation=observation.link_observation,
                failure_prefix="Step 1 failed",
            )
            self.assertEqual(
                link_payload["data"]["command"],
                "ticket-link",
                "Step 1 failed: the link CLI response did not report the expected "
                "`ticket-link` command metadata.\n"
                f"Observed payload: {link_payload}",
            )
            self.assertEqual(
                link_payload["data"]["operation"],
                "link",
                "Step 1 failed: the link CLI response did not report the expected "
                "`link` operation metadata.\n"
                f"Observed payload: {link_payload}",
            )
            self.assertEqual(
                link_payload["data"]["link"],
                self.config.expected_link_payload,
                "Step 1 failed: the link CLI response did not preserve the requested "
                "non-hierarchical `blocks` relationship.\n"
                f"Expected link payload: {self.config.expected_link_payload}\n"
                f"Observed payload: {link_payload}",
            )

        with self.subTest("step-2-verify-root-links-json"):
            root_links_payload = observation.root_links_json_payload
            self.assertIsInstance(
                root_links_payload,
                list,
                "Step 2 failed: the repository-root `links.json` file was not a JSON "
                "array after the link command completed.\n"
                f"Expected path: {observation.root_links_json_relative_path}\n"
                f"Observed files: {observation.discovered_links_json_files}\n"
                f"Observed content:\n{observation.root_links_json_content}",
            )
            assert isinstance(root_links_payload, list)
            self.assertIn(
                self.config.expected_link_payload,
                root_links_payload,
                "Step 2 failed: the repository-root `links.json` file did not include "
                "the newly created live non-hierarchical link record after the "
                "legacy issue-local file was purged.\n"
                f"Expected path: {observation.root_links_json_relative_path}\n"
                f"Expected link payload: {self.config.expected_link_payload}\n"
                f"Observed payload: {root_links_payload}\n"
                f"Observed files detail:\n{self._format_links_json_snapshots(observation)}",
            )
            self.assertGreaterEqual(
                len(root_links_payload),
                1,
                "Step 2 failed: the repository-root `links.json` file was empty after "
                "the live link command completed.\n"
                f"Observed payload: {root_links_payload}",
            )
            self.assertEqual(
                observation.discovered_links_json_files,
                (observation.root_links_json_relative_path,),
                "Step 2 failed: `links.json` was not consolidated exclusively at the "
                "repository root after the link operation.\n"
                f"Expected files: {(observation.root_links_json_relative_path,)}\n"
                f"Observed files: {observation.discovered_links_json_files}\n"
                f"Observed files detail:\n{self._format_links_json_snapshots(observation)}",
            )

        with self.subTest("step-3-inspect-source-issue-directory"):
            self.assertIn(
                "main.md",
                observation.issue_a_directory_entries,
                "Step 3 failed: the source issue directory no longer exposed its "
                "visible `main.md` issue artifact after the link operation.\n"
                f"Directory: {observation.issue_a_directory_relative_path}\n"
                f"Observed entries: {observation.issue_a_directory_entries}",
            )
            self.assertNotIn(
                "links.json",
                observation.issue_a_directory_entries,
                "Step 3 failed: the stale legacy `links.json` file still existed in "
                "the source issue directory after the standard link operation.\n"
                f"Directory: {observation.issue_a_directory_relative_path}\n"
                "Observed entries before linking: "
                f"{observation.issue_a_directory_entries_before_link}\n"
                f"Observed entries after linking: {observation.issue_a_directory_entries}\n"
                "Observed files detail:\n"
                f"{self._format_links_json_snapshots(observation)}",
            )
            self.assertIsNotNone(
                observation.issue_a_main_content,
                "Human-style verification failed: the source issue markdown was not "
                "readable after the link mutation.\n"
                f"Expected path: {observation.issue_a_main_relative_path}",
            )
            assert observation.issue_a_main_content is not None
            self.assertIn(
                "# Summary",
                observation.issue_a_main_content,
                "Human-style verification failed: the source issue markdown did not "
                "show the visible summary heading a user would inspect.\n"
                f"Observed main.md:\n{observation.issue_a_main_content}",
            )
            self.assertIn(
                self.config.issue_a_summary,
                observation.issue_a_main_content,
                "Human-style verification failed: the source issue markdown did not "
                "show the requested visible summary text.\n"
                f"Observed main.md:\n{observation.issue_a_main_content}",
            )

        with self.subTest("human-style-terminal-and-target-verification"):
            self.assertIn(
                "main.md",
                observation.issue_b_directory_entries,
                "Human-style verification failed: the target issue directory did not "
                "retain its visible `main.md` issue artifact.\n"
                f"Directory: {observation.issue_b_directory_relative_path}\n"
                f"Observed entries: {observation.issue_b_directory_entries}",
            )
            self.assertIsNotNone(
                observation.issue_b_main_content,
                "Human-style verification failed: the target issue markdown was not "
                "readable after the link mutation.\n"
                f"Expected path: {observation.issue_b_main_relative_path}",
            )
            assert observation.issue_b_main_content is not None
            self.assertIn(
                "# Summary",
                observation.issue_b_main_content,
                "Human-style verification failed: the target issue markdown did not "
                "show the visible summary heading a user would inspect.\n"
                f"Observed main.md:\n{observation.issue_b_main_content}",
            )
            self.assertIn(
                self.config.issue_b_summary,
                observation.issue_b_main_content,
                "Human-style verification failed: the target issue markdown did not "
                "show the requested visible summary text.\n"
                f"Observed main.md:\n{observation.issue_b_main_content}",
            )
            for fragment in (
                '"ok": true',
                '"command": "ticket-link"',
                f'"target": "{self.config.expected_link_payload["target"]}"',
                f'"type": "{self.config.expected_link_payload["type"]}"',
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
            "TS-1213 must execute a repository-local compiled binary so the seeded "
            "repository remains isolated.\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Fallback reason: {observation.fallback_reason}",
        )
        self.assertEqual(
            observation.executed_command[0],
            observation.compiled_binary_path,
            f"{precondition_message}\n"
            "TS-1213 did not run the compiled repository-local CLI binary.\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Compiled binary path: {observation.compiled_binary_path}",
        )
        self.assertIsNotNone(
            observation.execution_working_directory,
            f"{precondition_message}\n"
            "TS-1213 must record the process working directory so the harness proves "
            "`--path` selected the disposable repository explicitly."
        )
        self.assertEqual(
            observation.execution_working_directory,
            str(self.repository_root),
            f"{precondition_message}\n"
            "TS-1213 must run the compiled CLI from the checkout root instead of the "
            "target repository.\n"
            f"Expected working directory: {self.repository_root}\n"
            f"Observed working directory: {observation.execution_working_directory}",
        )
        self.assertNotEqual(
            observation.execution_working_directory,
            observation.repository_path,
            f"{precondition_message}\n"
            "TS-1213 still coupled the CLI working directory to the seeded target "
            "repository, so `--path` was not isolated as the repository selector.\n"
            f"Repository path: {observation.repository_path}\n"
            f"Observed working directory: {observation.execution_working_directory}",
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
        observation: TrackStateCliLegacyLocalLinksJsonPurgeObservation,
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
