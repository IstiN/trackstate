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
        self.maxDiff = None
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = TrackStateCliJiraSearchConfig.from_defaults()
        self.validator = TrackStateCliJiraSearchValidator(
            probe=create_trackstate_cli_jira_search_probe(self.repository_root)
        )

    def test_search_command_returns_jira_compatible_pagination_fields(self) -> None:
        result = self.validator.validate(config=self.config)
        control = result.supported_control
        failures: list[str] = []

        def check(condition: bool, message: str) -> None:
            if not condition:
                failures.append(message)

        check(
            control.requested_command == self.config.supported_control_command,
            "Precondition failed: TS-319 did not execute the supported local-search "
            "control command needed to validate the seeded repository fixture.\n"
            f"Expected command: {' '.join(self.config.supported_control_command)}\n"
            f"Observed command: {control.requested_command_text}",
        )
        check(
            control.result.exit_code == 0,
            "Precondition failed: the supported local-search control command did not "
            "succeed against the seeded TrackState repository.\n"
            f"Repository path: {control.repository_path}\n"
            f"Requested command: {control.requested_command_text}\n"
            f"Executed command: {control.executed_command_text}\n"
            f"Fallback reason: {control.fallback_reason}\n"
            f"stdout:\n{control.result.stdout}\n"
            f"stderr:\n{control.result.stderr}",
        )
        check(
            isinstance(control.result.json_payload, dict),
            "Precondition failed: the supported local-search control command did not "
            "return a JSON envelope, so the seeded repository fixture could not be "
            "validated.\n"
            f"stdout:\n{control.result.stdout}\n"
            f"stderr:\n{control.result.stderr}",
        )
        control_payload = (
            control.result.json_payload if isinstance(control.result.json_payload, dict) else {}
        )
        check(
            control_payload.get("ok") is True,
            "Precondition failed: the supported control search returned a failure "
            "envelope instead of search results.\n"
            f"Observed payload: {control_payload}",
        )
        control_data = control_payload.get("data") if isinstance(control_payload, dict) else None
        check(
            isinstance(control_data, dict),
            "Precondition failed: the supported control search did not return a "
            "search data payload.\n"
            f"Observed payload: {control_payload}",
        )
        if isinstance(control_data, dict):
            control_issues = control_data.get("issues")
            check(
                isinstance(control_issues, list),
                "Precondition failed: the supported control search did not return an "
                "issues array for the seeded fixture.\n"
                f"Observed payload: {control_payload}",
            )
            if isinstance(control_issues, list):
                check(
                    [issue.get("key") for issue in control_issues if isinstance(issue, dict)]
                    == list(self.config.expected_issue_keys),
                    "Precondition failed: the seeded repository fixture did not return "
                    "the expected two TRACK issues during the supported control search.\n"
                    f"Observed payload: {control_payload}",
                )

            control_page = control_data.get("page")
            check(
                isinstance(control_page, dict),
                "Precondition failed: the supported control search did not return page "
                "metadata needed to prove the fixture is valid.\n"
                f"Observed payload: {control_payload}",
            )
            if isinstance(control_page, dict):
                check(
                    control_page.get("startAt") == self.config.expected_start_at,
                    "Precondition failed: the supported control search did not honor "
                    "the requested start offset.\n"
                    f"Observed payload: {control_payload}",
                )
                check(
                    control_page.get("maxResults") == self.config.expected_max_results,
                    "Precondition failed: the supported control search did not honor "
                    "the requested maxResults value.\n"
                    f"Observed payload: {control_payload}",
                )
                check(
                    control_page.get("total") == self.config.expected_total,
                    "Precondition failed: the supported control search did not report "
                    "the expected total issue count.\n"
                    f"Observed payload: {control_payload}",
                )

        observation = result.ticket_command
        check(
            observation.requested_command == self.config.requested_command,
            "Precondition failed: TS-319 did not execute the exact ticket command.\n"
            f"Expected command: {' '.join(self.config.requested_command)}\n"
            f"Observed command: {observation.requested_command_text}",
        )
        check(
            observation.compiled_binary_path is not None,
            "Precondition failed: TS-319 must execute a repository-local compiled "
            "binary so the current working directory can remain the seeded TrackState "
            "repository.\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Fallback reason: {observation.fallback_reason}",
        )
        check(
            observation.executed_command[0] == observation.compiled_binary_path,
            "Precondition failed: TS-319 did not run the compiled repository-local "
            "CLI binary.\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Compiled binary path: {observation.compiled_binary_path}",
        )
        check(
            observation.result.exit_code == 0,
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
        check(
            isinstance(observation.result.json_payload, dict),
            "Step 2 failed: the ticket command did not return a machine-readable "
            "JSON envelope.\n"
            f"stdout:\n{observation.result.stdout}\n"
            f"stderr:\n{observation.result.stderr}",
        )
        payload = (
            observation.result.json_payload
            if isinstance(observation.result.json_payload, dict)
            else {}
        )
        check(
            payload.get("ok") is True,
            "Step 2 failed: the ticket command returned a failure envelope instead of "
            "search results.\n"
            f"Observed payload: {payload}\n"
            "\n"
            "Supported control payload:\n"
            f"{control_payload}",
        )
        check(
            payload.get("provider") == self.config.expected_provider,
            "Expected result failed: the successful search envelope did not identify "
            "the Local Git runtime.\n"
            f"Observed payload: {payload}",
        )

        target = payload.get("target") if isinstance(payload, dict) else None
        check(
            isinstance(target, dict),
            "Expected result failed: the successful search envelope did not include "
            "target metadata as an object.\n"
            f"Observed payload: {payload}",
        )
        if isinstance(target, dict):
            check(
                target.get("type") == self.config.expected_target_type,
                "Expected result failed: the successful search envelope did not "
                "identify the target type as local.\n"
                f"Observed payload: {payload}",
            )
            check(
                target.get("value") == observation.repository_path,
                "Expected result failed: the successful search envelope did not keep "
                "the seeded repository as the resolved target.\n"
                f"Observed payload: {payload}",
            )

        data = payload.get("data") if isinstance(payload, dict) else None
        check(
            isinstance(data, dict),
            "Step 2 failed: the JSON envelope did not include a `data` object for the "
            "search response.\n"
            f"Observed payload: {payload}",
        )
        if isinstance(data, dict):
            missing_data_keys = [
                key for key in self.config.required_data_keys if key not in data
            ]
            check(
                not missing_data_keys,
                "Expected result failed: the search response under `data` was missing "
                "the Jira-compatible pagination keys required by the ticket.\n"
                f"Missing keys: {missing_data_keys}\n"
                f"Observed data: {data}\n"
                "\n"
                "Supported control payload for comparison:\n"
                f"{control_payload}",
            )
            check(
                "page" not in data,
                "Expected result failed: the search response still included the legacy "
                "nested `data.page` object after the linked flattening fix.\n"
                f"Observed data: {data}",
            )

            issues = data.get("issues")
            check(
                isinstance(issues, list),
                "Expected result failed: `data.issues` was not encoded as an array.\n"
                f"Observed data: {data}",
            )
            if isinstance(issues, list):
                check(
                    [issue.get("key") for issue in issues if isinstance(issue, dict)]
                    == list(self.config.expected_issue_keys),
                    "Expected result failed: the search response did not include the "
                    "expected two issues from the seeded TRACK project.\n"
                    f"Observed data: {data}",
                )
            if not missing_data_keys:
                check(
                    data.get("startAt") == self.config.expected_start_at,
                    "Expected result failed: `data.startAt` did not report the "
                    "requested offset.\n"
                    f"Observed data: {data}",
                )
                check(
                    data.get("maxResults") == self.config.expected_max_results,
                    "Expected result failed: `data.maxResults` did not report the "
                    "requested page size.\n"
                    f"Observed data: {data}",
                )
                check(
                    data.get("total") == self.config.expected_total,
                    "Expected result failed: `data.total` did not report the total "
                    "number of matching issues.\n"
                    f"Observed data: {data}",
                )
                check(
                    isinstance(data.get("isLastPage"), bool),
                    "Expected result failed: `data.isLastPage` was missing or not "
                    "encoded as a boolean.\n"
                    f"Observed data: {data}",
                )
                check(
                    data.get("isLastPage") is self.config.expected_is_last_page,
                    "Expected result failed: `data.isLastPage` did not report that the "
                    "first page already contains the last search results.\n"
                    f"Observed data: {data}",
                )

        if payload.get("ok") is True:
            for fragment in (
                '"issues": [',
                '"startAt": 0',
                '"maxResults": 2',
                '"total": 2',
                '"isLastPage": true',
                '"key": "TRACK-1"',
                '"summary": "Issue 1"',
            ):
                check(
                    fragment in observation.result.stdout,
                    "Human-style verification failed: the visible JSON output did not "
                    "show the expected Jira-compatible search fields and issue "
                    "content.\n"
                    f"Missing fragment: {fragment}\n"
                    f"Observed stdout:\n{observation.result.stdout}",
                )
            check(
                '"page": {' not in observation.result.stdout,
                "Human-style verification failed: the visible JSON output still "
                "showed the legacy nested `page` object after the linked flattening "
                "fix.\n"
                f"Observed stdout:\n{observation.result.stdout}",
            )
        else:
            check(
                '"message": "Could not find an option named \\"--startAt\\"."' in observation.result.stdout,
                "Human-style verification failed: the visible terminal output did not "
                "show the ticket command's option-parsing error.\n"
                f"Observed stdout:\n{observation.result.stdout}",
            )

        self.assertFalse(failures, "\n\n".join(failures))


if __name__ == "__main__":
    unittest.main()
