from __future__ import annotations

from pathlib import Path
import unittest

from testing.components.services.trackstate_cli_canonical_link_formatter_validator import (
    TrackStateCliCanonicalLinkFormatterValidator,
)
from testing.core.config.trackstate_cli_canonical_link_formatter_config import (
    TrackStateCliCanonicalLinkFormatterConfig,
)
from testing.tests.support.trackstate_cli_canonical_link_formatter_probe_factory import (
    create_trackstate_cli_canonical_link_formatter_probe,
)


class TrackStateCliCanonicalLinkFormatterTest(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = TrackStateCliCanonicalLinkFormatterConfig.from_defaults()
        self.validator = TrackStateCliCanonicalLinkFormatterValidator(
            probe=create_trackstate_cli_canonical_link_formatter_probe(
                self.repository_root
            )
        )

    def test_canonical_link_metadata_emits_no_validation_warning(self) -> None:
        result = self.validator.validate(config=self.config)
        observation = result.observation

        self.assertTrue(
            observation.succeeded,
            "Precondition failed: the TS-653 Dart probe could not analyze or run.\n"
            f"Analyze output:\n{observation.analyze_output}\n"
            f"Run output:\n{observation.run_output or ''}\n"
            f"Run stderr:\n{observation.run_stderr or ''}",
        )
        payload = observation.observation_payload
        self.assertIsInstance(
            payload,
            dict,
            "Precondition failed: the TS-653 probe did not emit a structured "
            "observation payload.\n"
            f"Analyze output:\n{observation.analyze_output}\n"
            f"Run output:\n{observation.run_output or ''}\n"
            f"Run stderr:\n{observation.run_stderr or ''}",
        )
        assert isinstance(payload, dict)

        self.assertEqual(
            payload.get("invokedMembers"),
            ["_linkPayload", "_textSuccess"],
            "Precondition failed: TS-653 did not invoke the expected production "
            "formatter helpers.\n"
            f"Observed payload: {payload}",
        )
        self.assertEqual(
            payload.get("linkInput"),
            self.config.probe_link_payload,
            "Precondition failed: TS-653 did not pass the expected canonical "
            "relationship object into the production formatter.\n"
            f"Observed payload: {payload}",
        )

        observed_link_payload = payload.get("observedLinkPayload")
        self.assertEqual(
            observed_link_payload,
            self.config.probe_link_payload,
            "Step 1 failed: the production formatter probe did not return the same "
            "canonical relationship metadata it was asked to format.\n"
            f"Expected payload: {self.config.probe_link_payload}\n"
            f"Observed payload: {observed_link_payload}",
        )

        stdout_preview = str(payload.get("stdoutPreview", ""))
        success_text = str(payload.get("visibleSuccessText", ""))
        for fragment in self.config.required_visible_fragments:
            self.assertTrue(
                fragment in stdout_preview or fragment in success_text,
                "Human-style verification failed: the user-visible formatter output "
                "did not surface the canonical relationship in either the JSON "
                "preview or the terminal-style summary.\n"
                f"Missing fragment: {fragment}\n"
                f"Observed JSON preview:\n{stdout_preview}\n"
                f"Observed success text:\n{success_text}",
            )

        captured_stderr = observation.run_stderr or ""
        self.assertEqual(
            captured_stderr.strip(),
            "",
            "Expected result failed: the CLI response formatter emitted an "
            "unexpected validation warning for canonical link metadata.\n"
            f"Observed stderr:\n{captured_stderr or '<empty>'}\n"
            f"Observed formatted payload: {observed_link_payload}\n"
            f"Observed JSON preview:\n{stdout_preview}\n"
            f"Observed success text:\n{success_text}",
        )


if __name__ == "__main__":
    unittest.main()
