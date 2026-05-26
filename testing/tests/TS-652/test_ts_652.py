from __future__ import annotations

import json
from pathlib import Path
import unittest

from testing.components.services.trackstate_cli_nonblocking_link_formatter_warning_validator import (
    TrackStateCliNonblockingLinkFormatterWarningValidator,
)
from testing.core.config.trackstate_cli_nonblocking_link_formatter_warning_config import (
    TrackStateCliNonblockingLinkFormatterWarningConfig,
)
from testing.tests.support.trackstate_cli_nonblocking_link_formatter_warning_probe_factory import (
    create_trackstate_cli_nonblocking_link_formatter_warning_probe,
)


class TrackStateCliNonblockingLinkFormatterWarningTest(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = TrackStateCliNonblockingLinkFormatterWarningConfig.from_defaults()
        self.validator = TrackStateCliNonblockingLinkFormatterWarningValidator(
            probe=create_trackstate_cli_nonblocking_link_formatter_warning_probe(
                self.repository_root
            )
        )

    def test_noncanonical_link_warning_does_not_interrupt_primary_output(self) -> None:
        result = self.validator.validate(config=self.config)
        observation = result.observation

        self.assertTrue(
            observation.succeeded,
            "Precondition failed: the TS-652 Dart probe could not analyze or run.\n"
            f"Analyze output:\n{observation.analyze_output}\n"
            f"Run output:\n{observation.run_output or ''}\n"
            f"Run stderr:\n{observation.run_stderr or ''}",
        )
        payload = observation.observation_payload
        self.assertIsInstance(
            payload,
            dict,
            "Precondition failed: the TS-652 probe did not emit a structured "
            "observation payload.\n"
            f"Analyze output:\n{observation.analyze_output}\n"
            f"Run output:\n{observation.run_output or ''}\n"
            f"Run stderr:\n{observation.run_stderr or ''}",
        )
        assert isinstance(payload, dict)

        self.assertEqual(
            payload.get("invokedMembers"),
            ["_linkPayload", "_success"],
            "Precondition failed: TS-652 did not invoke the expected production "
            "formatter helpers.\n"
            f"Observed payload: {payload}",
        )
        self.assertEqual(
            payload.get("linkInput"),
            self.config.probe_link_payload,
            "Precondition failed: TS-652 did not pass the expected non-canonical "
            "relationship object into the production formatter.\n"
            f"Observed payload: {payload}",
        )

        observed_link_payload = payload.get("observedLinkPayload")
        self.assertEqual(
            observed_link_payload,
            self.config.probe_link_payload,
            "Step 1 failed: the production formatter probe did not return the same "
            "non-canonical relationship metadata it was asked to format.\n"
            f"Expected payload: {self.config.probe_link_payload}\n"
            f"Observed payload: {observed_link_payload}",
        )

        json_stdout = str(payload.get("stdoutPreview", ""))
        self.assertTrue(
            json_stdout.strip(),
            "Step 2 failed: the production formatter did not produce JSON success "
            "output on stdout.\n"
            f"Observed payload: {payload}",
        )
        json_output = json.loads(json_stdout)
        self.assertTrue(
            json_output.get("ok"),
            "Step 2 failed: the primary JSON stdout stream did not return a "
            "successful formatter envelope.\n"
            f"Observed JSON stdout:\n{json_stdout}",
        )
        self.assertEqual(
            json_output.get("output"),
            "json",
            "Step 2 failed: the primary JSON stdout stream did not identify itself "
            "as JSON output.\n"
            f"Observed JSON stdout:\n{json_stdout}",
        )
        json_data = json_output.get("data")
        self.assertIsInstance(
            json_data,
            dict,
            "Step 2 failed: the JSON stdout stream did not include a data object.\n"
            f"Observed JSON stdout:\n{json_stdout}",
        )
        assert isinstance(json_data, dict)
        self.assertEqual(
            json_data.get("command"),
            "ticket-link",
            "Step 2 failed: the JSON stdout stream did not preserve the expected "
            "formatter command metadata.\n"
            f"Observed JSON stdout:\n{json_stdout}",
        )
        self.assertEqual(
            json_data.get("link"),
            self.config.probe_link_payload,
            "Expected result failed: the JSON stdout stream was corrupted by the "
            "warning path instead of preserving the non-canonical relationship "
            "payload.\n"
            f"Expected link payload: {self.config.probe_link_payload}\n"
            f"Observed JSON stdout:\n{json_stdout}",
        )

        text_stdout = str(payload.get("visibleSuccessText", ""))
        for fragment in self.config.required_text_fragments:
            self.assertIn(
                fragment,
                text_stdout,
                "Human-style verification failed: the terminal-style success output "
                "did not visibly preserve the expected confirmation details while "
                "the warning was written to stderr.\n"
                f"Missing fragment: {fragment}\n"
                f"Observed text stdout:\n{text_stdout}",
            )

        captured_stderr = observation.run_stderr or ""
        normalized_stderr = captured_stderr.lower()
        missing_warning_fragments = [
            fragment
            for fragment in self.config.expected_warning_fragments
            if fragment not in normalized_stderr
        ]
        self.assertFalse(
            missing_warning_fragments,
            "Expected result failed: the formatter did not emit the schema "
            "validation warning to stderr while rendering the primary success "
            "output.\n"
            f"Missing stderr fragments: {missing_warning_fragments}\n"
            f"Observed stderr:\n{captured_stderr or '<empty>'}\n"
            f"Observed JSON stdout:\n{json_stdout}\n"
            f"Observed text stdout:\n{text_stdout}",
        )


if __name__ == "__main__":
    unittest.main()
