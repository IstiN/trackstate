from __future__ import annotations

from pathlib import Path
import unittest

from testing.components.services.trackstate_cli_help_validator import (
    TrackStateCliHelpValidator,
)
from testing.core.config.trackstate_cli_help_config import TrackStateCliHelpConfig
from testing.tests.support.trackstate_cli_help_probe_factory import (
    create_trackstate_cli_help_probe,
)


class TrackStateCliHelpDiscoverabilityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = TrackStateCliHelpConfig.from_env()
        self.validator = TrackStateCliHelpValidator(
            repository_root=self.repository_root,
            probe=create_trackstate_cli_help_probe(self.repository_root),
        )

    def test_root_help_documents_target_selection_and_examples(self) -> None:
        result = self.validator.validate(config=self.config)

        self.assertTrue(
            result.root_help.result.succeeded,
            "Step 1 failed: the TrackState root help command did not complete "
            "successfully.\n"
            f"Requested command: {result.root_help.requested_command_text}\n"
            f"Executed command: {result.root_help.executed_command_text}\n"
            f"Fallback reason: {result.root_help.fallback_reason}\n"
            f"Exit code: {result.root_help.result.exit_code}\n"
            f"stdout:\n{result.root_help.result.stdout}\n"
            f"stderr:\n{result.root_help.result.stderr}",
        )
        self.assertTrue(
            result.session_help.result.succeeded,
            "Precondition failed: the TrackState session help command could not be "
            "read for comparison against the root help output.\n"
            f"Requested command: {result.session_help.requested_command_text}\n"
            f"Executed command: {result.session_help.executed_command_text}\n"
            f"Fallback reason: {result.session_help.fallback_reason}\n"
            f"Exit code: {result.session_help.result.exit_code}\n"
            f"stdout:\n{result.session_help.result.stdout}\n"
            f"stderr:\n{result.session_help.result.stderr}",
        )

        for example in self.config.required_root_examples:
            self.assertIn(
                example,
                result.root_help.result.stdout,
                "Step 3 failed: the root help text did not show the documented "
                "usage examples for both local and hosted targets.\n"
                f"Missing example: {example}\n"
                f"Observed root help:\n{result.root_help.result.stdout}",
            )

        for fragment in self.config.required_root_option_fragments:
            self.assertIn(
                fragment,
                result.root_help.result.stdout,
                "Step 2 failed: the root help text did not include the stable "
                "target-selection documentation requested by TS-274.\n"
                f"Missing fragment: {fragment}\n"
                f"Requested command: {result.root_help.requested_command_text}\n"
                f"Executed command: {result.root_help.executed_command_text}\n"
                f"Fallback reason: {result.root_help.fallback_reason}\n"
                f"Observed root help:\n{result.root_help.result.stdout}\n"
                "\n"
                "Session help for comparison:\n"
                f"{result.session_help.result.stdout}",
            )


if __name__ == "__main__":
    unittest.main()
