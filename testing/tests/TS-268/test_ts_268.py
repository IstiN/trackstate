from __future__ import annotations

from pathlib import Path
import unittest

from testing.components.services.hosted_target_selection_cli_validator import (
    HostedTargetSelectionCliValidator,
)
from testing.core.config.hosted_target_selection_cli_config import (
    HostedTargetSelectionCliConfig,
)
from testing.tests.support.hosted_target_selection_cli_probe_factory import (
    create_hosted_target_selection_cli_probe,
)


class HostedTargetSelectionProviderNeutralFlagsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = HostedTargetSelectionCliConfig.from_defaults()
        self.validator = HostedTargetSelectionCliValidator(
            probe=create_hosted_target_selection_cli_probe(self.repository_root)
        )

    def test_root_cli_resolves_hosted_target_with_provider_neutral_flags(
        self,
    ) -> None:
        result = self.validator.validate(config=self.config)
        observation = result.observation

        self.assertTrue(
            observation.succeeded,
            "Precondition failed: the TS-268 Dart probe could not analyze or run.\n"
            f"Analyze output:\n{observation.analyze_output}\n"
            f"Run output:\n{observation.run_output or ''}",
        )
        payload = observation.observation_payload
        self.assertIsInstance(
            payload,
            dict,
            "Precondition failed: the TS-268 probe did not emit a structured "
            "observation payload.\n"
            f"Analyze output:\n{observation.analyze_output}\n"
            f"Run output:\n{observation.run_output or ''}",
        )
        assert isinstance(payload, dict)

        self.assertEqual(
            tuple(payload.get("arguments", [])),
            self.config.requested_arguments,
            "Precondition failed: TS-268 did not execute the exact ticket command "
            "arguments.\n"
            f"Expected arguments: {self.config.requested_arguments}\n"
            f"Observed payload: {payload}",
        )
        self.assertEqual(
            payload.get("requestedCommand"),
            self.config.requested_command_text,
            "Precondition failed: TS-268 did not report the exact ticket command.\n"
            f"Expected command: {self.config.requested_command_text}\n"
            f"Observed payload: {payload}",
        )

        envelope = payload.get("parsedEnvelope")
        self.assertIsInstance(
            envelope,
            dict,
            "Step 2 failed: the CLI did not emit a machine-readable JSON envelope "
            "for the provider-neutral hosted target command.\n"
            f"Observed exit code: {payload.get('exitCode')}\n"
            f"Observed stdout:\n{payload.get('stdout', '')}",
        )
        assert isinstance(envelope, dict)

        self.assertEqual(
            payload.get("exitCode"),
            0,
            "Step 1 failed: running the exact provider-neutral hosted target command "
            "did not initialize successfully.\n"
            f"Requested command: {payload.get('requestedCommand')}\n"
            f"Observed exit code: {payload.get('exitCode')}\n"
            f"Observed stdout:\n{payload.get('stdout', '')}",
        )
        self.assertIs(
            envelope.get("ok"),
            True,
            "Step 2 failed: the JSON envelope did not report a successful result.\n"
            f"Observed envelope: {envelope}",
        )
        self.assertEqual(
            envelope.get("provider"),
            self.config.expected_provider,
            "Expected result failed: the JSON envelope did not expose the expected "
            "hosted provider.\n"
            f"Observed envelope: {envelope}",
        )

        target = envelope.get("target")
        self.assertIsInstance(
            target,
            dict,
            "Step 2 failed: the JSON envelope did not expose target metadata as an "
            "object.\n"
            f"Observed envelope: {envelope}",
        )
        assert isinstance(target, dict)
        self.assertEqual(
            target.get("type"),
            self.config.expected_target_type,
            "Expected result failed: the target metadata did not identify the "
            "hosted target type.\n"
            f"Observed target: {target}",
        )
        self.assertEqual(
            target.get("value"),
            self.config.expected_target_value,
            "Expected result failed: the target metadata did not preserve the "
            "owner/name hosted repository value.\n"
            f"Observed target: {target}",
        )

        data = envelope.get("data")
        self.assertIsInstance(
            data,
            dict,
            "Step 2 failed: the JSON envelope did not include a session data object.\n"
            f"Observed envelope: {envelope}",
        )
        assert isinstance(data, dict)
        self.assertEqual(
            data.get("branch"),
            self.config.expected_branch,
            "Expected result failed: the session payload did not keep the explicit "
            "branch flag.\n"
            f"Observed data: {data}",
        )

        hosted_call = payload.get("createHostedCall")
        self.assertIsInstance(
            hosted_call,
            dict,
            "Step 1 failed: the CLI never forwarded the hosted target metadata into "
            "the provider factory.\n"
            f"Observed payload: {payload}",
        )
        assert isinstance(hosted_call, dict)
        self.assertEqual(
            hosted_call.get("provider"),
            self.config.expected_provider,
            "Step 1 failed: the provider factory did not receive the expected hosted "
            "provider value.\n"
            f"Observed provider factory call: {hosted_call}",
        )
        self.assertEqual(
            hosted_call.get("repository"),
            self.config.expected_target_value,
            "Step 1 failed: the provider factory did not receive the expected hosted "
            "repository value.\n"
            f"Observed provider factory call: {hosted_call}",
        )
        self.assertEqual(
            hosted_call.get("branch"),
            self.config.expected_branch,
            "Step 1 failed: the provider factory did not receive the explicit branch "
            "from the provider-neutral command.\n"
            f"Observed provider factory call: {hosted_call}",
        )

        connection = payload.get("providerConnection")
        self.assertIsInstance(
            connection,
            dict,
            "Step 1 failed: the mocked basic read operation never authenticated "
            "against the resolved hosted target.\n"
            f"Observed payload: {payload}",
        )
        assert isinstance(connection, dict)
        self.assertEqual(
            connection.get("repository"),
            self.config.expected_target_value,
            "Step 1 failed: the mocked hosted read did not receive the expected "
            "repository value.\n"
            f"Observed connection: {connection}",
        )
        self.assertEqual(
            connection.get("branch"),
            self.config.expected_branch,
            "Step 1 failed: the mocked hosted read did not receive the explicit "
            "branch value.\n"
            f"Observed connection: {connection}",
        )

        stdout = str(payload.get("stdout", ""))
        for fragment in self.config.required_visible_fragments:
            self.assertIn(
                fragment,
                stdout,
                "Human-style verification failed: the visible CLI JSON output did "
                "not show the expected hosted target metadata.\n"
                f"Missing fragment: {fragment}\n"
                f"Observed stdout:\n{stdout}",
            )


if __name__ == "__main__":
    unittest.main()
