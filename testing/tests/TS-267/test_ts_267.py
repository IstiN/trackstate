from __future__ import annotations

import json
import os
from pathlib import Path
import unittest

from testing.core.config.github_actions_dependabot_monitor_config import (
    GitHubActionsDependabotMonitorConfig,
)
from testing.core.interfaces.github_actions_dependabot_monitor_probe import (
    GitHubActionsDependabotMonitorObservation,
    GitHubActionsDependabotMonitorProbe,
)
from testing.tests.support.github_actions_dependabot_monitor_probe_factory import (
    create_github_actions_dependabot_monitor_probe,
)


class DependabotGitHubActionsMonitorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config_path = self.repository_root / "testing/tests/TS-267/config.yaml"
        self.config = GitHubActionsDependabotMonitorConfig.from_file(self.config_path)
        screenshot_path = os.environ.get("TS267_SCREENSHOT_PATH")
        self.probe: GitHubActionsDependabotMonitorProbe = (
            create_github_actions_dependabot_monitor_probe(
                self.repository_root,
                config_path=self.config_path,
                screenshot_path=(
                    Path(screenshot_path) if screenshot_path else None
                ),
            )
        )

    def test_dependabot_monitors_github_action_versions(self) -> None:
        observation = self.probe.validate()
        self._write_result_if_requested(observation.to_dict())

        self.assertEqual(
            observation.repository,
            self.config.repository,
            "Step 1 failed: TS-267 targeted the wrong repository.\n"
            f"Expected repository: {self.config.repository}\n"
            f"Observed repository: {observation.repository}",
        )
        self.assertEqual(
            observation.default_branch,
            self.config.base_branch,
            "Step 1 failed: TS-267 targeted the wrong default branch.\n"
            f"Expected default branch: {self.config.base_branch}\n"
            f"Observed default branch: {observation.default_branch}",
        )
        self.assertTrue(
            observation.dependabot_file_present,
            "Step 2 failed: the live repository does not expose the required "
            "Dependabot configuration file.\n"
            f"Expected file path: {self.config.dependabot_path}\n"
            f"Observed .github entries: {observation.github_directory_entries}\n"
            f"GitHub API endpoint: {observation.raw_file_api_endpoint}\n"
            f"GitHub API error:\n{observation.raw_file_error}",
        )
        self.assertTrue(
            observation.parsed_file_is_mapping,
            "Step 2 failed: the Dependabot configuration file did not decode to a "
            "YAML mapping.\n"
            f"File path: {self.config.dependabot_path}\n"
            f"YAML parse error: {observation.raw_file_parse_error}\n"
            f"Observed file contents:\n{observation.raw_file_text}",
        )
        self.assertTrue(
            observation.github_actions_update_present,
            "Step 3 failed: the Dependabot file does not define a github-actions "
            "updates block.\n"
            f"File path: {self.config.dependabot_path}\n"
            f"Observed updates count: {observation.updates_count}\n"
            f"Observed file contents:\n{observation.raw_file_text}",
        )
        self.assertEqual(
            observation.github_actions_directory,
            self.config.expected_directory,
            "Step 4 failed: the github-actions Dependabot block does not monitor the "
            "repository root.\n"
            f"Expected directory: {self.config.expected_directory}\n"
            f"Observed directory: {observation.github_actions_directory}\n"
            f"Observed file contents:\n{observation.raw_file_text}",
        )
        for schedule_key in self.config.required_schedule_keys:
            self.assertIn(
                schedule_key,
                observation.github_actions_schedule_keys,
                "Step 4 failed: the github-actions Dependabot block does not define "
                "the required schedule fields.\n"
                f"Missing schedule key: {schedule_key}\n"
                f"Observed schedule keys: {observation.github_actions_schedule_keys}\n"
                f"Observed file contents:\n{observation.raw_file_text}",
            )
        self.assertTrue(
            observation.github_actions_schedule_interval,
            "Step 4 failed: the github-actions Dependabot block does not define a "
            "schedule interval.\n"
            f"Observed schedule keys: {observation.github_actions_schedule_keys}\n"
            f"Observed file contents:\n{observation.raw_file_text}",
        )
        self.assertIsNone(
            observation.ui_error,
            "Human-style verification failed: the GitHub file page could not be "
            "opened in the browser.\n"
            f"File URL: {observation.ui_url}\n"
            f"Screenshot: {observation.ui_screenshot_path}\n"
            f"Observed error:\n{observation.ui_error}",
        )
        self.assertIn(
            "dependabot.yml",
            observation.ui_body_text,
            "Human-style verification failed: the GitHub file page did not visibly "
            "show the Dependabot file name.\n"
            f"File URL: {observation.ui_url}\n"
            f"Matched text: {observation.ui_matched_text}\n"
            f"Screenshot: {observation.ui_screenshot_path}\n"
            f"Visible body text:\n{observation.ui_body_text}",
        )
        for visible_text in self.config.expected_visible_texts[1:]:
            self.assertIn(
                visible_text,
                observation.ui_body_text,
                "Human-style verification failed: the GitHub file page did not "
                "visibly show the expected Dependabot content.\n"
                f"Missing visible text: {visible_text}\n"
                f"File URL: {observation.ui_url}\n"
                f"Screenshot: {observation.ui_screenshot_path}\n"
                f"Visible body text:\n{observation.ui_body_text}",
            )

    def _write_result_if_requested(self, payload: dict[str, object]) -> None:
        result_path = os.environ.get("TS267_RESULT_PATH")
        if not result_path:
            return

        destination = Path(result_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    unittest.main()
