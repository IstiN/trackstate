from __future__ import annotations

import json
import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest import mock
from urllib import error as urllib_error

from testing.core.config.setup_repo_smoke_config import (
    SetupRepoSmokeConfig,
    load_setup_repo_smoke_config,
)
from testing.frameworks.python import setup_repo_smoke_framework as smoke_module
from testing.frameworks.python.setup_repo_smoke_framework import (
    CliCommandObservation,
    SetupRepoSmokeFramework,
    _benchmark_worker,
)


class _FakeUrlopenResponse:
    def __init__(self, code: int, body: bytes) -> None:
        self._code = code
        self._body = body

    def getcode(self) -> int:
        return self._code

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_FakeUrlopenResponse":
        return self

    def __exit__(self, *args: object) -> None:
        pass


class _FakePlaywrightPage:
    def __init__(self, labels_present: bool = True) -> None:
        self._labels_present = labels_present
        self.goto_calls: list[dict[str, object]] = []

    def goto(self, url: str, *, wait_until: str, timeout: int) -> object:
        self.goto_calls.append({"url": url, "wait_until": wait_until})
        return _FakeResponse()

    def wait_for_timeout(self, ms: int) -> None:
        pass

    def wait_for_function(self, expression: str, *, arg: object, timeout: int) -> None:
        if not self._labels_present:
            raise smoke_module.PlaywrightTimeoutError("missing labels")

    def close(self) -> None:
        pass


class _FakeResponse:
    def __init__(self, status: int = 200) -> None:
        self.status = status


class _FakeBrowser:
    def __init__(self, page: _FakePlaywrightPage) -> None:
        self._page = page

    def new_context(self, *, viewport: dict[str, int]) -> "_FakeBrowserContext":
        return _FakeBrowserContext(self._page)

    def close(self) -> None:
        pass


class _FakeBrowserContext:
    def __init__(self, page: _FakePlaywrightPage) -> None:
        self._page = page

    def new_page(self) -> _FakePlaywrightPage:
        return self._page

    def close(self) -> None:
        pass


class _FakePlaywright:
    def __init__(self, page: _FakePlaywrightPage) -> None:
        self.chromium = _FakeChromium(page)


class _FakeChromium:
    def __init__(self, page: _FakePlaywrightPage) -> None:
        self._page = page

    def launch(self, *, args: list[str]) -> _FakeBrowser:
        return _FakeBrowser(self._page)


class _FakePlaywrightManager:
    def __init__(self, page: _FakePlaywrightPage) -> None:
        self._page = page

    def __enter__(self) -> _FakePlaywright:
        return _FakePlaywright(self._page)

    def __exit__(self, *args: object) -> None:
        pass


class SetupRepoSmokeConfigTest(unittest.TestCase):
    def test_default_config_derives_app_url_from_repository(self) -> None:
        config = load_setup_repo_smoke_config()
        self.assertEqual(config.repository, "IstiN/trackstate-setup")
        self.assertEqual(config.app_url, "https://istin.github.io/trackstate-setup/")
        self.assertEqual(config.expected_base_href, "/trackstate-setup/")
        self.assertEqual(config.benchmark_concurrency, 10)

    def test_custom_repository_derives_app_url(self) -> None:
        with mock.patch.dict(
            os.environ,
            {"TRACKSTATE_LIVE_SETUP_REPOSITORY": "owner/custom-setup"},
            clear=False,
        ):
            config = load_setup_repo_smoke_config()
        self.assertEqual(config.app_url, "https://owner.github.io/custom-setup/")


class SetupRepoSmokeFrameworkTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = SetupRepoSmokeConfig(
            app_url="https://example.github.io/trackstate-setup/",
            repository="owner/trackstate-setup",
            ref="main",
            auth_token_variables=("TRACKSTATE_TOKEN", "GH_TOKEN"),
            expected_title="TrackState.AI",
            expected_base_href="/trackstate-setup/",
            shell_navigation_labels=("Dashboard", "Board"),
            page_interactive_budget_seconds=3.0,
            page_interactive_warmup_runs=1,
            cli_command_timeout_seconds=30.0,
            benchmark_concurrency=2,
            benchmark_command_budget_seconds=3.0,
            benchmark_command_max_seconds=5.0,
            benchmark_min_success_rate=1.0,
        )

    def _make_framework(
        self,
        cli_runner: smoke_module.CliRunner | None = None,
    ) -> SetupRepoSmokeFramework:
        return SetupRepoSmokeFramework(
            self.config,
            cli_runner=cli_runner,
            benchmark_executor_factory=ThreadPoolExecutor,
        )

    def _success_create(self, issue_key: str) -> CliCommandObservation:
        return CliCommandObservation(
            command=("trackstate", "create"),
            exit_code=0,
            elapsed_seconds=0.5,
            issue_key=issue_key,
        )

    def _success_command(self, name: str) -> CliCommandObservation:
        return CliCommandObservation(
            command=("trackstate", name),
            exit_code=0,
            elapsed_seconds=0.4,
        )

    @mock.patch("testing.frameworks.python.setup_repo_smoke_framework.urllib_request.urlopen")
    def test_pages_health_probe_passes(self, mock_urlopen: mock.Mock) -> None:
        html = (
            "<html><head><title>TrackState.AI</title>"
            '<base href="/trackstate-setup/"></head>'
            '<body><script src="flutter_bootstrap.js"></script></body></html>'
        )
        mock_urlopen.return_value = _FakeUrlopenResponse(200, html.encode("utf-8"))

        framework = self._make_framework()
        health = framework._probe_pages_health()

        self.assertTrue(health.healthy)
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.title, "TrackState.AI")
        self.assertEqual(health.base_href, "/trackstate-setup/")
        self.assertTrue(health.contains_bootstrap_script)

    @mock.patch("testing.frameworks.python.setup_repo_smoke_framework.urllib_request.urlopen")
    def test_pages_health_probe_reports_http_error(self, mock_urlopen: mock.Mock) -> None:
        mock_urlopen.side_effect = urllib_error.HTTPError(
            "https://example.github.io/trackstate-setup/",
            500,
            "Internal Server Error",
            {},
            None,
        )

        framework = self._make_framework()
        health = framework._probe_pages_health()

        self.assertFalse(health.healthy)
        self.assertEqual(health.status_code, 500)
        self.assertIsNotNone(health.error)

    def test_pages_interactive_within_budget(self) -> None:
        fake_page = _FakePlaywrightPage(labels_present=True)
        fake_manager = _FakePlaywrightManager(fake_page)

        with mock.patch.object(smoke_module, "sync_playwright", lambda: fake_manager):
            framework = self._make_framework()
            observation = framework._measure_pages_time_to_interactive()

        self.assertTrue(observation.within_budget)
        self.assertEqual(observation.labels_found, ("Dashboard", "Board"))
        self.assertIsNone(observation.error)
        self.assertGreaterEqual(observation.elapsed_seconds, 0.0)

    def test_pages_interactive_missing_playwright_returns_error(self) -> None:
        with mock.patch.object(smoke_module, "sync_playwright", None):
            framework = self._make_framework()
            observation = framework._measure_pages_time_to_interactive()

        self.assertIsNotNone(observation.error)
        self.assertIn("Playwright is not installed", observation.error)

    def test_pages_interactive_reports_timeout(self) -> None:
        fake_page = _FakePlaywrightPage(labels_present=False)
        fake_manager = _FakePlaywrightManager(fake_page)

        with mock.patch.object(smoke_module, "sync_playwright", lambda: fake_manager):
            framework = self._make_framework()
            observation = framework._measure_pages_time_to_interactive()

        self.assertIsNotNone(observation.error)
        self.assertIn("Timed out", observation.error)

    def test_cli_smoke_all_succeeds(self) -> None:
        calls: list[list[str]] = []

        def fake_runner(arguments: list[str]) -> CliCommandObservation:
            calls.append(arguments)
            if arguments[0] == "create":
                return self._success_create("DEMO-1000")
            return self._success_command(arguments[0])

        framework = self._make_framework(cli_runner=fake_runner)
        smoke = framework._run_cli_smoke()

        self.assertTrue(smoke.all_succeeded)
        self.assertEqual(smoke.create.issue_key, "DEMO-1000")
        self.assertTrue(smoke.transition.succeeded)
        self.assertTrue(smoke.search.succeeded)
        self.assertTrue(smoke.cleanup.succeeded)
        self.assertIn("session", [c[0] for c in calls])
        self.assertIn("create", [c[0] for c in calls])
        self.assertIn("jira_move_to_status", [c[0] for c in calls])
        self.assertIn("search", [c[0] for c in calls])

    def test_cli_smoke_create_failure_skips_transition(self) -> None:
        def fake_runner(arguments: list[str]) -> CliCommandObservation:
            if arguments[0] == "create":
                return CliCommandObservation(
                    command=("trackstate", "create"),
                    exit_code=1,
                    elapsed_seconds=0.1,
                    error="create failed",
                )
            return self._success_command(arguments[0])

        framework = self._make_framework(cli_runner=fake_runner)
        smoke = framework._run_cli_smoke()

        self.assertFalse(smoke.all_succeeded)
        self.assertIsNone(smoke.transition)
        self.assertIsNone(smoke.cleanup)

    def test_extract_issue_key_from_json(self) -> None:
        stdout = json.dumps(
            {
                "ok": True,
                "data": {
                    "issue": {"key": "DEMO-42", "summary": "test"}
                },
            }
        )
        self.assertEqual(
            SetupRepoSmokeFramework._extract_issue_key_from_stdout(stdout),
            "DEMO-42",
        )

    def test_extract_issue_key_from_search_json(self) -> None:
        stdout = json.dumps(
            {
                "ok": True,
                "data": {
                    "issues": [{"key": "DEMO-1"}, {"key": "DEMO-2"}]
                },
            }
        )
        self.assertEqual(
            SetupRepoSmokeFramework._extract_issue_key_from_stdout(stdout),
            "DEMO-1",
        )

    @mock.patch(
        "testing.frameworks.python.setup_repo_smoke_framework._benchmark_worker"
    )
    def test_cli_benchmark_passes(self, mock_worker: mock.Mock) -> None:
        mock_worker.return_value = [
            CliCommandObservation(
                command=("trackstate", "session"),
                exit_code=0,
                elapsed_seconds=0.5,
            ),
            CliCommandObservation(
                command=("trackstate", "create"),
                exit_code=0,
                elapsed_seconds=0.7,
            ),
            CliCommandObservation(
                command=("trackstate", "read"),
                exit_code=0,
                elapsed_seconds=0.6,
            ),
            CliCommandObservation(
                command=("trackstate", "jira_move_to_status"),
                exit_code=0,
                elapsed_seconds=0.8,
            ),
            CliCommandObservation(
                command=("trackstate", "search"),
                exit_code=0,
                elapsed_seconds=0.5,
            ),
        ]

        framework = self._make_framework()
        benchmark = framework._run_cli_benchmark()

        self.assertTrue(benchmark.passed)
        self.assertEqual(benchmark.concurrency, 2)
        self.assertEqual(benchmark.total_commands, 10)
        self.assertEqual(benchmark.failed_commands, 0)
        self.assertEqual(benchmark.p95_seconds, 0.8)
        self.assertEqual(benchmark.max_seconds, 0.8)
        self.assertEqual(mock_worker.call_count, 2)

    @mock.patch(
        "testing.frameworks.python.setup_repo_smoke_framework._benchmark_worker"
    )
    def test_cli_benchmark_fails_when_command_fails(self, mock_worker: mock.Mock) -> None:
        mock_worker.return_value = [
            CliCommandObservation(
                command=("trackstate", "session"),
                exit_code=0,
                elapsed_seconds=0.5,
            ),
            CliCommandObservation(
                command=("trackstate", "create"),
                exit_code=1,
                elapsed_seconds=0.1,
                error="create failed",
            ),
        ]

        framework = self._make_framework()
        benchmark = framework._run_cli_benchmark()

        self.assertFalse(benchmark.passed)
        self.assertEqual(benchmark.failed_commands, 2)

    @mock.patch("testing.frameworks.python.setup_repo_smoke_framework.urllib_request.urlopen")
    def test_run_reports_missing_auth_token(self, mock_urlopen: mock.Mock) -> None:
        html = (
            "<html><head><title>TrackState.AI</title>"
            '<base href="/trackstate-setup/"></head>'
            '<body><script src="flutter_bootstrap.js"></script></body></html>'
        )
        mock_urlopen.return_value = _FakeUrlopenResponse(200, html.encode("utf-8"))

        with (
            mock.patch.dict(
                os.environ,
                {"TRACKSTATE_TOKEN": "", "GH_TOKEN": ""},
                clear=False,
            ),
            mock.patch.object(smoke_module, "sync_playwright", None),
        ):
            framework = self._make_framework()
            result = framework.run()

        self.assertTrue(any("Missing required runtime variable" in e for e in result.errors))
        self.assertIsNone(result.cli_smoke)
        self.assertIsNone(result.cli_benchmark)


if __name__ == "__main__":
    unittest.main()
