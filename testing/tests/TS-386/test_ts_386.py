from __future__ import annotations

from pathlib import Path
import unittest

from testing.components.services.trackstate_cli_attachment_discovery_validator import (
    TrackStateCliAttachmentDiscoveryValidator,
)
from testing.core.config.trackstate_cli_attachment_discovery_config import (
    TrackStateCliAttachmentDiscoveryConfig,
)
from testing.core.models.trackstate_cli_help_result import TrackStateCliHelpObservation
from testing.tests.support.trackstate_cli_attachment_discovery_probe_factory import (
    create_trackstate_cli_attachment_discovery_probe,
)


class TrackStateCliAttachmentDiscoveryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = TrackStateCliAttachmentDiscoveryConfig.from_env()
        self.validator = TrackStateCliAttachmentDiscoveryValidator(
            probe=create_trackstate_cli_attachment_discovery_probe(self.repository_root)
        )

    def test_attachment_help_and_jira_alias_are_discoverable(self) -> None:
        result = self.validator.validate(config=self.config)

        root_help = self._assert_help_command_succeeded(
            observation=result.root_help,
            expected_command=self.config.requested_root_help_command,
            failure_prefix="Step 1 failed",
        )
        upload_help = self._assert_help_command_succeeded(
            observation=result.attachment_upload_help,
            expected_command=self.config.requested_attachment_upload_help_command,
            failure_prefix="Step 2 failed",
        )
        alias_help = self._assert_help_command_succeeded(
            observation=result.jira_attachment_upload_help,
            expected_command=self.config.requested_jira_attachment_upload_help_command,
            failure_prefix="Step 3 failed",
        )

        for fragment in self.config.required_root_fragments:
            self.assertIn(
                fragment,
                root_help,
                "Step 1 failed: the TrackState root help text did not keep the "
                "attachment command discoverable from the top-level CLI entry point.\n"
                f"Missing fragment: {fragment}\n"
                f"Observed root help:\n{root_help}",
            )

        for fragment in self.config.required_attachment_upload_fragments:
            self.assertIn(
                fragment,
                upload_help,
                "Step 2 failed: `trackstate attachment upload --help` did not show "
                "the documented attachment upload help text and required flags.\n"
                f"Missing fragment: {fragment}\n"
                f"Observed upload help:\n{upload_help}",
            )

        for fragment in self.config.required_jira_attachment_upload_fragments:
            self.assertIn(
                fragment,
                alias_help,
                "Step 3 failed: `trackstate jira_attach_file_to_ticket --help` did "
                "not expose the documented compatibility alias help and required "
                "flag mapping.\n"
                f"Missing fragment: {fragment}\n"
                f"Observed alias help:\n{alias_help}",
            )

        self.assertEqual(
            alias_help,
            upload_help,
            "Expected result failed: the Jira attachment alias did not resolve to the "
            "same visible command help as `trackstate attachment upload --help`.\n"
            f"Observed upload help:\n{upload_help}\n\n"
            f"Observed alias help:\n{alias_help}",
        )
        self.assertIn(
            "--issueKey",
            alias_help,
            "Human-style verification failed: the alias help did not visibly document "
            "`--issueKey` as the Jira-compatible flag name for the issue input.\n"
            f"Observed alias help:\n{alias_help}",
        )
        self.assertIn(
            "--issue",
            alias_help,
            "Human-style verification failed: the alias help did not visibly preserve "
            "the canonical `--issue` option mapping alongside the Jira alias.\n"
            f"Observed alias help:\n{alias_help}",
        )
        self.assertIn(
            "Upload or download one attachment.",
            root_help,
            "Human-style verification failed: the root help no longer described the "
            "attachment command as the entry point for both upload and download.\n"
            f"Observed root help:\n{root_help}",
        )

    def _assert_help_command_succeeded(
        self,
        *,
        observation: TrackStateCliHelpObservation,
        expected_command: tuple[str, ...],
        failure_prefix: str,
    ) -> str:
        self.assertEqual(
            observation.requested_command,
            expected_command,
            f"{failure_prefix}: TS-386 did not execute the expected CLI help command.\n"
            f"Expected command: {' '.join(expected_command)}\n"
            f"Observed command: {observation.requested_command_text}",
        )
        self.assertTrue(
            observation.result.succeeded,
            f"{failure_prefix}: executing `{observation.requested_command_text}` did "
            "not complete successfully.\n"
            f"Requested command: {observation.requested_command_text}\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Fallback reason: {observation.fallback_reason}\n"
            f"Exit code: {observation.result.exit_code}\n"
            f"stdout:\n{observation.result.stdout}\n"
            f"stderr:\n{observation.result.stderr}",
        )
        return observation.output


if __name__ == "__main__":
    unittest.main()
