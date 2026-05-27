from __future__ import annotations

import json
import unittest
from contextlib import AbstractContextManager
from pathlib import Path
from unittest.mock import patch

from testing.components.services.github_actions_dependabot_monitor_probe import (
    GitHubActionsDependabotMonitorProbeService,
)
from testing.core.config.github_actions_dependabot_monitor_config import (
    GitHubActionsDependabotMonitorConfig,
)
from testing.core.interfaces.github_api_client import GitHubApiClientError
from testing.tests.support import github_repository_file_page_factory


class _FakeGitHubApiClient:
    def __init__(self, responses: dict[str, object]) -> None:
        self._responses = responses

    def request_text(
        self,
        *,
        endpoint: str,
        method: str = "GET",
        field_args=None,
        stdin_json=None,
    ) -> str:
        del method, field_args, stdin_json
        response = self._responses[endpoint]
        if isinstance(response, Exception):
            raise response
        if isinstance(response, str):
            return response
        return json.dumps(response)


class _FailingFilePageContext(AbstractContextManager[object]):
    def __init__(self, message: str) -> None:
        self._message = message

    def __enter__(self) -> object:
        raise AssertionError(self._message)

    def __exit__(self, exc_type, exc, exc_tb) -> None:
        return None


class GitHubActionsDependabotMonitorProbeRegressionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = GitHubActionsDependabotMonitorConfig(
            repository="IstiN/trackstate-setup",
            base_branch="main",
            dependabot_path=".github/dependabot.yml",
            expected_package_ecosystem="github-actions",
            expected_directory="/",
            required_schedule_keys=("interval",),
            expected_visible_texts=("dependabot.yml", "github-actions", "schedule"),
            ui_missing_page_markers=("Page not found",),
            ui_timeout_seconds=60,
        )

    def test_invalid_yaml_is_reported_as_an_observation_instead_of_erroring(self) -> None:
        invalid_yaml = "updates:\n  - package-ecosystem: github-actions\n    schedule: [\n"
        probe = GitHubActionsDependabotMonitorProbeService(
            self.config,
            github_api_client=_FakeGitHubApiClient(
                {
                    "/repos/IstiN/trackstate-setup": {"default_branch": "main"},
                    "/repos/IstiN/trackstate-setup/contents/.github?ref=main": [],
                    (
                        "/repos/IstiN/trackstate-setup/contents/.github/dependabot.yml"
                        "?ref=main"
                    ): invalid_yaml,
                }
            ),
            file_page_factory=lambda: _FailingFilePageContext("browser unavailable"),
        )

        observation = probe.validate()

        self.assertTrue(observation.dependabot_file_present)
        self.assertFalse(observation.parsed_file_is_mapping)
        self.assertIsNotNone(observation.raw_file_parse_error)
        self.assertIn("while parsing", observation.raw_file_parse_error or "")
        self.assertEqual(observation.raw_file_text, invalid_yaml)
        self.assertEqual(observation.ui_error, "browser unavailable")

    def test_default_file_page_factory_fails_clearly_without_playwright(self) -> None:
        real_import = __import__

        def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "testing.frameworks.python.playwright_web_app_session":
                raise ModuleNotFoundError("No module named 'playwright'")
            return real_import(name, globals, locals, fromlist, level)

        with (
            patch("builtins.__import__", side_effect=fake_import),
            self.assertRaisesRegex(
                AssertionError,
                "Playwright browser verification is required",
            ),
        ):
            github_repository_file_page_factory._default_runtime_factory()


if __name__ == "__main__":
    unittest.main()
