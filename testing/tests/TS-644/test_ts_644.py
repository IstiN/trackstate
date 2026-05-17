from __future__ import annotations

from pathlib import Path
import unittest

from testing.components.services.trackstate_cli_link_formatter_warning_validator import (
    TrackStateCliLinkFormatterWarningValidator,
)
from testing.core.config.trackstate_cli_link_formatter_warning_config import (
    TrackStateCliLinkFormatterWarningConfig,
)
from testing.tests.support.trackstate_cli_link_formatter_warning_probe_factory import (
    create_trackstate_cli_link_formatter_warning_probe,
)


class TrackStateCliLinkFormatterWarningTest(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = TrackStateCliLinkFormatterWarningConfig.from_defaults()
        self.validator = TrackStateCliLinkFormatterWarningValidator(
            probe=create_trackstate_cli_link_formatter_warning_probe(self.repository_root)
        )

    def test_noncanonical_link_metadata_emits_validation_warning(self) -> None:
        result = self.validator.validate(config=self.config)
        observation = result.observation

        self.assertTrue(
            observation.succeeded,
            "Precondition failed: the TS-644 Dart probe could not analyze or run.\n"
            f"Analyze output:\n{observation.analyze_output}\n"
            f"Run output:\n{observation.run_output or ''}\n"
            f"Run stderr:\n{observation.run_stderr or ''}",
        )
        payload = observation.observation_payload
        self.assertIsInstance(
            payload,
            dict,
            "Precondition failed: the TS-644 probe did not emit a structured "
            "observation payload.\n"
            f"Analyze output:\n{observation.analyze_output}\n"
            f"Run output:\n{observation.run_output or ''}\n"
            f"Run stderr:\n{observation.run_stderr or ''}",
        )
        assert isinstance(payload, dict)

        self.assertEqual(
            payload.get("invokedMembers"),
            ["_linkPayload", "_textSuccess"],
            "Precondition failed: TS-644 did not invoke the expected production "
            "formatter helpers.\n"
            f"Observed payload: {payload}",
        )
        self.assertEqual(
            payload.get("linkInput"),
            self.config.probe_link_payload,
            "Precondition failed: TS-644 did not pass the expected non-canonical "
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

        stdout_preview = str(payload.get("stdoutPreview", ""))
        success_text = str(payload.get("visibleSuccessText", ""))
        for fragment in self.config.required_visible_fragments:
            self.assertTrue(
                fragment in stdout_preview or fragment in success_text,
                "Human-style verification failed: the user-visible formatter output "
                "did not surface the non-canonical relationship in either the JSON "
                "preview or the terminal-style summary.\n"
                f"Missing fragment: {fragment}\n"
                f"Observed JSON preview:\n{stdout_preview}\n"
                f"Observed success text:\n{success_text}",
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
            "Expected result failed: the CLI response formatter did not emit the "
            "schema validation warning required for non-canonical link metadata.\n"
            f"Missing stderr fragments: {missing_warning_fragments}\n"
            f"Observed stderr:\n{captured_stderr or '<empty>'}\n"
            f"Observed formatted payload: {observed_link_payload}\n"
            f"Observed JSON preview:\n{stdout_preview}\n"
            f"Observed success text:\n{success_text}",
        )


if __name__ == "__main__":
    unittest.main()
