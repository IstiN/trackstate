from __future__ import annotations

from pathlib import Path
import unittest

from testing.components.services.trackstate_cli_invalid_pagination_validator import (
    TrackStateCliInvalidPaginationValidator,
)
from testing.core.config.trackstate_cli_invalid_pagination_config import (
    TrackStateCliInvalidPaginationConfig,
)
from testing.tests.support.trackstate_cli_invalid_pagination_probe_factory import (
    create_trackstate_cli_invalid_pagination_probe,
)


class CliSearchInvalidPaginationValidationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = TrackStateCliInvalidPaginationConfig.from_defaults()
        self.validator = TrackStateCliInvalidPaginationValidator(
            probe=create_trackstate_cli_invalid_pagination_probe(self.repository_root)
        )

    def test_search_rejects_invalid_pagination_values_with_json_validation_errors(
        self,
    ) -> None:
        result = self.validator.validate(config=self.config)
        control = result.supported_control

        self.assertEqual(
            control.requested_command,
            self.config.supported_control_command,
            "Precondition failed: TS-338 did not execute the supported control search "
            "command needed to validate the seeded repository fixture.\n"
            f"Expected command: {' '.join(self.config.supported_control_command)}\n"
            f"Observed command: {control.requested_command_text}",
        )
        self.assertEqual(
            control.result.exit_code,
            0,
            "Precondition failed: the supported local-search control command did not "
            "succeed against the seeded TrackState repository.\n"
            f"Repository path: {control.repository_path}\n"
            f"Requested command: {control.requested_command_text}\n"
            f"Executed command: {control.executed_command_text}\n"
            f"Fallback reason: {control.fallback_reason}\n"
            f"stdout:\n{control.result.stdout}\n"
            f"stderr:\n{control.result.stderr}",
        )
        self.assertIsInstance(
            control.result.json_payload,
            dict,
            "Precondition failed: the supported local-search control command did not "
            "return a JSON envelope, so the seeded repository fixture could not be "
            "validated.\n"
            f"stdout:\n{control.result.stdout}\n"
            f"stderr:\n{control.result.stderr}",
        )
        control_payload = control.result.json_payload
        assert isinstance(control_payload, dict)
        control_data = control_payload.get("data")
        self.assertIsInstance(
            control_data,
            dict,
            "Precondition failed: the supported control search did not return a "
            "search data payload.\n"
            f"Observed payload: {control_payload}",
        )
        assert isinstance(control_data, dict)
        control_page = control_data.get("page")
        self.assertIsInstance(
            control_page,
            dict,
            "Precondition failed: the supported control search did not return page "
            "metadata for the seeded fixture.\n"
            f"Observed payload: {control_payload}",
        )
        assert isinstance(control_page, dict)
        control_issues = control_data.get("issues")
        self.assertIsInstance(
            control_issues,
            list,
            "Precondition failed: the supported control search did not return an "
            "issues array for the seeded fixture.\n"
            f"Observed payload: {control_payload}",
        )
        assert isinstance(control_issues, list)
        self.assertEqual(
            [issue.get("key") for issue in control_issues if isinstance(issue, dict)],
            list(self.config.expected_issue_keys),
            "Precondition failed: the seeded repository fixture did not return the "
            "expected two TRACK issues during the supported control search.\n"
            f"Observed payload: {control_payload}",
        )
        self.assertEqual(
            control_page.get("startAt"),
            self.config.expected_control_start_at,
            "Precondition failed: the supported control search did not honor the "
            "requested start offset.\n"
            f"Observed payload: {control_payload}",
        )
        self.assertEqual(
            control_page.get("maxResults"),
            self.config.expected_control_max_results,
            "Precondition failed: the supported control search did not honor the "
            "requested maxResults value.\n"
            f"Observed payload: {control_payload}",
        )
        self.assertEqual(
            control_page.get("total"),
            self.config.expected_control_total,
            "Precondition failed: the supported control search did not report the "
            "expected total issue count.\n"
            f"Observed payload: {control_payload}",
        )

        for case_result in result.case_results:
            case = case_result.case
            observation = case_result.observation
            with self.subTest(case=case.name):
                self.assertEqual(
                    observation.requested_command,
                    case.requested_command,
                    "Precondition failed: TS-338 did not execute the exact ticket "
                    "command for this invalid pagination scenario.\n"
                    f"Expected command: {' '.join(case.requested_command)}\n"
                    f"Observed command: {observation.requested_command_text}",
                )
                self.assertIsNotNone(
                    observation.compiled_binary_path,
                    "Precondition failed: TS-338 must execute a repository-local "
                    "compiled binary so the current working directory can remain the "
                    "seeded TrackState repository.\n"
                    f"Executed command: {observation.executed_command_text}\n"
                    f"Fallback reason: {observation.fallback_reason}",
                )
                self.assertEqual(
                    observation.executed_command[0],
                    observation.compiled_binary_path,
                    "Precondition failed: TS-338 did not run the compiled repository-"
                    "local CLI binary.\n"
                    f"Executed command: {observation.executed_command_text}\n"
                    f"Compiled binary path: {observation.compiled_binary_path}",
                )
                self.assertEqual(
                    observation.repository_path,
                    control.repository_path,
                    "Precondition failed: TS-338 did not run the invalid command "
                    "against the same seeded repository that passed the supported "
                    "control search.\n"
                    f"Control repository path: {control.repository_path}\n"
                    f"Observed repository path: {observation.repository_path}",
                )
                self.assertEqual(
                    observation.result.exit_code,
                    self.config.expected_exit_code,
                    "Step failed: the invalid pagination command did not return the "
                    "documented validation exit code.\n"
                    f"Repository path: {observation.repository_path}\n"
                    f"Requested command: {observation.requested_command_text}\n"
                    f"Executed command: {observation.executed_command_text}\n"
                    f"Observed exit code: {observation.result.exit_code}\n"
                    f"stdout:\n{observation.result.stdout}\n"
                    f"stderr:\n{observation.result.stderr}",
                )
                self.assertIsInstance(
                    observation.result.json_payload,
                    dict,
                    "Step failed: the invalid pagination command did not return a "
                    "machine-readable JSON validation envelope.\n"
                    f"stdout:\n{observation.result.stdout}\n"
                    f"stderr:\n{observation.result.stderr}",
                )
                payload = observation.result.json_payload
                assert isinstance(payload, dict)
                target = payload.get("target")
                target_dict = target if isinstance(target, dict) else {}
                error = payload.get("error")
                error_dict = error if isinstance(error, dict) else {}
                details = error_dict.get("details")
                details_dict = details if isinstance(details, dict) else {}

                self.assertIs(
                    payload.get("ok"),
                    False,
                    "Step failed: the invalid pagination scenario did not report "
                    "`ok: false`.\n"
                    f"Observed payload: {payload}",
                )
                self.assertEqual(
                    payload.get("provider"),
                    self.config.expected_provider,
                    "Step failed: the JSON envelope did not identify the Local Git "
                    "provider.\n"
                    f"Observed payload: {payload}",
                )
                self.assertEqual(
                    target_dict.get("type"),
                    self.config.expected_target_type,
                    "Step failed: the JSON envelope did not identify the local target "
                    "type.\n"
                    f"Observed payload: {payload}",
                )
                self.assertEqual(
                    target_dict.get("value"),
                    observation.repository_path,
                    "Step failed: the JSON envelope did not report the seeded "
                    "repository path the CLI searched.\n"
                    f"Observed payload: {payload}",
                )
                self.assertEqual(
                    error_dict.get("code"),
                    self.config.expected_error_code,
                    "Expected result failed: the JSON validation error code changed.\n"
                    f"Observed payload: {payload}",
                )
                self.assertEqual(
                    error_dict.get("category"),
                    self.config.expected_error_category,
                    "Expected result failed: the JSON validation error category "
                    "changed.\n"
                    f"Observed payload: {payload}",
                )
                self.assertEqual(
                    error_dict.get("exitCode"),
                    self.config.expected_exit_code,
                    "Expected result failed: the JSON validation error did not repeat "
                    "the CLI exit code.\n"
                    f"Observed payload: {payload}",
                )
                self.assertEqual(
                    error_dict.get("message"),
                    case.expected_message,
                    "Expected result failed: the visible validation message did not "
                    "match the live CLI contract for this invalid pagination value.\n"
                    f"Observed payload: {payload}",
                )
                self.assertEqual(
                    details_dict.get("option"),
                    case.expected_option,
                    "Expected result failed: the validation error did not identify the "
                    "normalized option name.\n"
                    f"Observed payload: {payload}",
                )
                self.assertEqual(
                    details_dict.get("value"),
                    case.expected_value,
                    "Expected result failed: the validation error did not echo the "
                    "invalid value the user entered.\n"
                    f"Observed payload: {payload}",
                )
                self.assertNotIn(
                    "data",
                    payload,
                    "Expected result failed: the invalid pagination response should "
                    "not include successful search data.\n"
                    f"Observed payload: {payload}",
                )

                for fragment in self.config.required_stdout_fragments:
                    self.assertIn(
                        fragment,
                        observation.result.stdout,
                        "Human-style verification failed: the terminal output did not "
                        "visibly show the validation error envelope a user would rely "
                        "on.\n"
                        f"Missing fragment: {fragment}\n"
                        f"Observed stdout:\n{observation.result.stdout}",
                    )
                for fragment in (
                    case.expected_message.replace('"', '\\"'),
                    f'"option": "{case.expected_option}"',
                    f'"value": "{case.expected_value}"',
                ):
                    self.assertIn(
                        fragment,
                        observation.result.stdout,
                        "Human-style verification failed: the terminal output did not "
                        "clearly show the invalid pagination value and the message the "
                        "user would read.\n"
                        f"Missing fragment: {fragment}\n"
                        f"Observed stdout:\n{observation.result.stdout}",
                    )


if __name__ == "__main__":
    unittest.main()
