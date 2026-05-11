from __future__ import annotations

from pathlib import Path
import unittest

from testing.components.services.trackstate_cli_jira_search_validator import (
    TrackStateCliJiraSearchValidator,
)
from testing.core.config.trackstate_cli_jira_search_config import (
    TrackStateCliJiraSearchConfig,
)
from testing.tests.support.trackstate_cli_jira_search_probe_factory import (
    create_trackstate_cli_jira_search_probe,
)


class JiraCompatibleCliSearchResponseShapeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = TrackStateCliJiraSearchConfig.from_defaults()
        self.validator = TrackStateCliJiraSearchValidator(
            probe=create_trackstate_cli_jira_search_probe(self.repository_root)
        )

    def test_search_command_returns_jira_compatible_pagination_fields(self) -> None:
        result = self.validator.validate(config=self.config)
        control = result.supported_control

        self.assertEqual(
            control.requested_command,
            self.config.supported_control_command,
            "Precondition failed: TS-319 did not execute the supported local-search "
            "control command needed to validate the seeded repository fixture.\n"
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
            self.config.expected_start_at,
            "Precondition failed: the supported control search did not honor the "
            "requested start offset.\n"
            f"Observed payload: {control_payload}",
        )
        self.assertEqual(
            control_page.get("maxResults"),
            self.config.expected_max_results,
            "Precondition failed: the supported control search did not honor the "
            "requested maxResults value.\n"
            f"Observed payload: {control_payload}",
        )
        self.assertEqual(
            control_page.get("total"),
            self.config.expected_total,
            "Precondition failed: the supported control search did not report the "
            "expected total issue count.\n"
            f"Observed payload: {control_payload}",
        )

        observation = result.ticket_command
        self.assertEqual(
            observation.requested_command,
            self.config.requested_command,
            "Precondition failed: TS-319 did not execute the exact ticket command.\n"
            f"Expected command: {' '.join(self.config.requested_command)}\n"
            f"Observed command: {observation.requested_command_text}",
        )
        self.assertIsNotNone(
            observation.compiled_binary_path,
            "Precondition failed: TS-319 must execute a repository-local compiled "
            "binary so the current working directory can remain the seeded TrackState "
            "repository.\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Fallback reason: {observation.fallback_reason}",
        )
        self.assertEqual(
            observation.executed_command[0],
            observation.compiled_binary_path,
            "Precondition failed: TS-319 did not run the compiled repository-local "
            "CLI binary.\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Compiled binary path: {observation.compiled_binary_path}",
        )
        self.assertEqual(
            observation.result.exit_code,
            0,
            "Step 1 failed: executing `trackstate search --jql \"project = TRACK\" "
            "--startAt 0 --maxResults 2` did not succeed from a valid TrackState "
            "repository.\n"
            f"Repository path: {observation.repository_path}\n"
            f"Requested command: {observation.requested_command_text}\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Fallback reason: {observation.fallback_reason}\n"
            f"Observed exit code: {observation.result.exit_code}\n"
            f"stdout:\n{observation.result.stdout}\n"
            f"stderr:\n{observation.result.stderr}\n"
            "\n"
            "Supported control output from the same seeded repository:\n"
            f"{control.result.stdout}",
        )
        self.assertIsInstance(
            observation.result.json_payload,
            dict,
            "Step 2 failed: the ticket command did not return a machine-readable "
            "JSON envelope.\n"
            f"stdout:\n{observation.result.stdout}\n"
            f"stderr:\n{observation.result.stderr}",
        )
        payload = observation.result.json_payload
        assert isinstance(payload, dict)
        self.assertIs(
            payload.get("ok"),
            True,
            "Step 2 failed: the ticket command returned a failure envelope instead of "
            "search results.\n"
            f"Observed payload: {payload}\n"
            "\n"
            "Supported control payload:\n"
            f"{control_payload}",
        )
        self.assertEqual(
            payload.get("provider"),
            self.config.expected_provider,
            "Expected result failed: the successful search envelope did not identify "
            "the Local Git runtime.\n"
            f"Observed payload: {payload}",
        )

        target = payload.get("target")
        self.assertIsInstance(
            target,
            dict,
            "Expected result failed: the successful search envelope did not include "
            "target metadata as an object.\n"
            f"Observed payload: {payload}",
        )
        assert isinstance(target, dict)
        self.assertEqual(
            target.get("type"),
            self.config.expected_target_type,
            "Expected result failed: the successful search envelope did not identify "
            "the target type as local.\n"
            f"Observed payload: {payload}",
        )
        self.assertEqual(
            target.get("value"),
            observation.repository_path,
            "Expected result failed: the successful search envelope did not keep the "
            "seeded repository as the resolved target.\n"
            f"Observed payload: {payload}",
        )

        data = payload.get("data")
        self.assertIsInstance(
            data,
            dict,
            "Step 2 failed: the JSON envelope did not include a `data` object for "
            "the search response.\n"
            f"Observed payload: {payload}",
        )
        assert isinstance(data, dict)

        missing_data_keys = [
            key for key in self.config.required_data_keys if key not in data
        ]
        self.assertFalse(
            missing_data_keys,
            "Expected result failed: the search response under `data` was missing the "
            "Jira-compatible pagination keys required by the ticket.\n"
            f"Missing keys: {missing_data_keys}\n"
            f"Observed data: {data}\n"
            "\n"
            "Supported control payload for comparison:\n"
            f"{control_payload}",
        )

        issues = data.get("issues")
        self.assertIsInstance(
            issues,
            list,
            "Expected result failed: `data.issues` was not encoded as an array.\n"
            f"Observed data: {data}",
        )
        assert isinstance(issues, list)
        self.assertEqual(
            [issue.get("key") for issue in issues if isinstance(issue, dict)],
            list(self.config.expected_issue_keys),
            "Expected result failed: the search response did not include the expected "
            "two issues from the seeded TRACK project.\n"
            f"Observed data: {data}",
        )
        self.assertEqual(
            data.get("startAt"),
            self.config.expected_start_at,
            "Expected result failed: `data.startAt` did not report the requested "
            "offset.\n"
            f"Observed data: {data}",
        )
        self.assertEqual(
            data.get("maxResults"),
            self.config.expected_max_results,
            "Expected result failed: `data.maxResults` did not report the requested "
            "page size.\n"
            f"Observed data: {data}",
        )
        self.assertEqual(
            data.get("total"),
            self.config.expected_total,
            "Expected result failed: `data.total` did not report the total number of "
            "matching issues.\n"
            f"Observed data: {data}",
        )
        self.assertIsInstance(
            data.get("isLastPage"),
            bool,
            "Expected result failed: `data.isLastPage` was missing or not encoded as "
            "a boolean.\n"
            f"Observed data: {data}",
        )
        self.assertIs(
            data.get("isLastPage"),
            True,
            "Expected result failed: `data.isLastPage` did not report that the first "
            "page already contains the last search results.\n"
            f"Observed data: {data}",
        )

        for fragment in (
            '"issues": [',
            '"startAt": 0',
            '"maxResults": 2',
            '"total": 2',
            '"isLastPage": true',
            '"key": "TRACK-1"',
            '"summary": "Issue 1"',
        ):
            self.assertIn(
                fragment,
                observation.result.stdout,
                "Human-style verification failed: the visible JSON output did not show "
                "the expected Jira-compatible search fields and issue content.\n"
                f"Missing fragment: {fragment}\n"
                f"Observed stdout:\n{observation.result.stdout}",
            )


if __name__ == "__main__":
    unittest.main()
