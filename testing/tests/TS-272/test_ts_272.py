from __future__ import annotations

from pathlib import Path
import re
import unittest

from testing.components.services.trackstate_cli_session_contract_validator import (
    TrackStateCliSessionContractValidator,
)
from testing.core.config.trackstate_cli_session_contract_config import (
    TrackStateCliSessionContractConfig,
)
from testing.tests.support.trackstate_cli_session_contract_probe_factory import (
    create_trackstate_cli_session_contract_probe,
)


class TrackStateCliSessionContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = TrackStateCliSessionContractConfig.from_env()
        self.validator = TrackStateCliSessionContractValidator(
            probe=create_trackstate_cli_session_contract_probe(self.repository_root)
        )

    def test_session_defaults_to_json_success_envelope(self) -> None:
        observation = self.validator.validate(config=self.config).observation

        self.assertNotIn(
            "--output",
            observation.requested_command_text,
            "Precondition failed: TS-272 must execute the CLI without an explicit "
            "--output flag.",
        )
        self.assertNotIn(
            "--output",
            observation.executed_command_text,
            "Precondition failed: TS-272 unexpectedly executed the CLI with an "
            "--output flag.\n"
            f"Executed command: {observation.executed_command_text}",
        )
        self.assertTrue(
            observation.result.succeeded,
            "Step 1 failed: the TrackState session command did not complete "
            "successfully against the seeded Local Git repository.\n"
            f"Requested command: {observation.requested_command_text}\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Fallback reason: {observation.fallback_reason}\n"
            f"Repository path: {observation.repository_path}\n"
            f"Exit code: {observation.result.exit_code}\n"
            f"stdout:\n{observation.result.stdout}\n"
            f"stderr:\n{observation.result.stderr}",
        )
        self.assertIsInstance(
            observation.result.json_payload,
            dict,
            "Step 2 failed: the CLI did not return a valid JSON object by default.\n"
            f"Requested command: {observation.requested_command_text}\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Repository path: {observation.repository_path}\n"
            f"stdout:\n{observation.result.stdout}\n"
            f"stderr:\n{observation.result.stderr}",
        )
        payload = observation.result.json_payload
        assert isinstance(payload, dict)

        missing_top_level_keys = [
            key for key in self.config.required_top_level_keys if key not in payload
        ]
        self.assertFalse(
            missing_top_level_keys,
            "Step 2 failed: the default JSON response did not include the required "
            "TrackState success-envelope keys.\n"
            f"Missing keys: {missing_top_level_keys}\n"
            f"Observed payload: {payload}",
        )
        self.assertTrue(
            payload["ok"],
            "Expected result failed: the default session envelope reported a non-success "
            "result.\n"
            f"Observed payload: {payload}",
        )
        self.assertEqual(
            payload["output"],
            "json",
            "Expected result failed: the CLI did not report json as the default "
            "output mode in the envelope.\n"
            f"Observed payload: {payload}",
        )
        self.assertRegex(
            str(payload["schemaVersion"]),
            re.compile(r"^\d+$"),
            "Expected result failed: schemaVersion was not a version-like value.\n"
            f"Observed payload: {payload}",
        )
        self.assertEqual(
            payload["provider"],
            "local-git",
            "Human-style verification failed: the visible provider metadata did not "
            "identify the Local Git runtime a CLI user invoked.\n"
            f"Observed payload: {payload}",
        )

        target = payload["target"]
        self.assertIsInstance(
            target,
            dict,
            "Expected result failed: target metadata was not encoded as an object.\n"
            f"Observed payload: {payload}",
        )
        assert isinstance(target, dict)
        missing_target_keys = [
            key for key in self.config.required_target_keys if key not in target
        ]
        self.assertFalse(
            missing_target_keys,
            "Expected result failed: target metadata was missing required keys.\n"
            f"Missing target keys: {missing_target_keys}\n"
            f"Observed target: {target}",
        )
        self.assertEqual(
            target["type"],
            "local",
            "Human-style verification failed: the visible target metadata did not show "
            "a local session.\n"
            f"Observed target: {target}",
        )
        self.assertEqual(
            target["value"],
            observation.repository_path,
            "Human-style verification failed: the visible target value did not match "
            "the repository path the user invoked.\n"
            f"Expected path: {observation.repository_path}\n"
            f"Observed target: {target}",
        )

        data = payload["data"]
        self.assertIsInstance(
            data,
            dict,
            "Expected result failed: the command data payload was not encoded as an "
            "object.\n"
            f"Observed payload: {payload}",
        )
        assert isinstance(data, dict)
        missing_data_keys = [
            key for key in self.config.required_data_keys if key not in data
        ]
        self.assertFalse(
            missing_data_keys,
            "Expected result failed: the command data object did not include the "
            "expected session metadata.\n"
            f"Missing data keys: {missing_data_keys}\n"
            f"Observed data: {data}",
        )
        self.assertEqual(
            data["command"],
            "session",
            "Expected result failed: the command data did not identify the session "
            "command.\n"
            f"Observed data: {data}",
        )
        self.assertEqual(
            data["provider"],
            "local-git",
            "Expected result failed: the command data provider did not match the top-"
            "level provider metadata.\n"
            f"Observed data: {data}",
        )
        self.assertEqual(
            data["authSource"],
            "none",
            "Expected result failed: the local session should report no hosted auth "
            "source.\n"
            f"Observed data: {data}",
        )

        user = data["user"]
        self.assertIsInstance(
            user,
            dict,
            "Expected result failed: user metadata was not encoded as an object.\n"
            f"Observed data: {data}",
        )
        assert isinstance(user, dict)
        self.assertTrue(
            str(user.get("login", "")).strip(),
            "Human-style verification failed: the visible session output did not "
            "include a non-empty user login.\n"
            f"Observed user: {user}",
        )
        self.assertTrue(
            str(user.get("displayName", "")).strip(),
            "Human-style verification failed: the visible session output did not "
            "include a non-empty user displayName.\n"
            f"Observed user: {user}",
        )

        permissions = data["permissions"]
        self.assertIsInstance(
            permissions,
            dict,
            "Expected result failed: permissions metadata was not encoded as an "
            "object.\n"
            f"Observed data: {data}",
        )
        assert isinstance(permissions, dict)
        missing_permission_keys = [
            key
            for key in self.config.required_permission_keys
            if key not in permissions
        ]
        self.assertFalse(
            missing_permission_keys,
            "Expected result failed: the permissions object did not include the "
            "required capability keys.\n"
            f"Missing permission keys: {missing_permission_keys}\n"
            f"Observed permissions: {permissions}",
        )
        self.assertTrue(
            permissions["canRead"],
            "Human-style verification failed: the visible permissions did not show "
            "read access for the opened local repository.\n"
            f"Observed permissions: {permissions}",
        )
        self.assertTrue(
            permissions["canWrite"],
            "Human-style verification failed: the visible permissions did not show "
            "write access for the opened local repository.\n"
            f"Observed permissions: {permissions}",
        )
        self.assertNotIn(
            '"error"',
            observation.result.stdout,
            "Expected result failed: the successful default JSON envelope exposed an "
            "error payload.\n"
            f"stdout:\n{observation.result.stdout}",
        )
        self.assertIn(
            '"output": "json"',
            observation.result.stdout,
            "Human-style verification failed: the emitted stdout did not visibly show "
            'the default `"output": "json"` field a user would inspect.\n'
            f"stdout:\n{observation.result.stdout}",
        )


if __name__ == "__main__":
    unittest.main()
