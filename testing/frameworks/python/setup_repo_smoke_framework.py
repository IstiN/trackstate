from __future__ import annotations

import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Callable
from urllib import error as urllib_error
from urllib import request as urllib_request

try:
    from playwright.sync_api import sync_playwright
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
except ModuleNotFoundError:  # pragma: no cover - exercised in no-Playwright envs
    sync_playwright = None  # type: ignore[assignment]

    class PlaywrightTimeoutError(Exception):  # type: ignore[no-redef]
        pass

from testing.core.config.setup_repo_smoke_config import SetupRepoSmokeConfig
from testing.core.interfaces.setup_repo_smoke_probe import SetupRepoSmokeProbe
from testing.core.models.setup_repo_smoke_result import (
    CliBenchmarkObservation,
    CliCommandObservation,
    CliSmokeObservation,
    PagesHealthObservation,
    PagesInteractiveObservation,
    RuntimeVariableObservation,
    SetupRepoSmokeResult,
)


CliRunner = Callable[[list[str]], CliCommandObservation]


class SetupRepoSmokeFramework(SetupRepoSmokeProbe):
    def __init__(
        self,
        config: SetupRepoSmokeConfig,
        *,
        cli_runner: CliRunner | None = None,
        benchmark_executor_factory: type[Any] | None = None,
    ) -> None:
        self._config = config
        self._cli_runner = cli_runner or self._default_cli_runner
        self._benchmark_executor_factory = (
            benchmark_executor_factory or self._default_benchmark_executor_factory
        )

    @staticmethod
    def _default_benchmark_executor_factory(*, max_workers: int) -> Any:
        from concurrent.futures import ProcessPoolExecutor

        return ProcessPoolExecutor(max_workers=max_workers)

    def run(self) -> SetupRepoSmokeResult:
        errors: list[str] = []

        variables = self._validate_runtime_variables()
        token_available = any(v.present for v in variables)
        if not token_available:
            errors.append(
                "Missing required runtime variable: one of "
                f"{', '.join(self._config.auth_token_variables)} must be set."
            )

        pages_health = self._probe_pages_health()
        if pages_health and pages_health.error:
            errors.append(f"Pages health probe failed: {pages_health.error}")

        pages_interactive = self._measure_pages_time_to_interactive()
        if pages_interactive and pages_interactive.error:
            errors.append(f"Pages interactive probe failed: {pages_interactive.error}")

        cli_smoke: CliSmokeObservation | None = None
        cli_benchmark: CliBenchmarkObservation | None = None

        if not token_available:
            errors.append(
                "Skipping CLI smoke and benchmark because no auth token is available."
            )
        else:
            try:
                cli_smoke = self._run_cli_smoke()
            except Exception as error:  # pragma: no cover - defensive catch
                errors.append(f"CLI smoke failed: {error}")

            try:
                cli_benchmark = self._run_cli_benchmark()
            except Exception as error:  # pragma: no cover - defensive catch
                errors.append(f"CLI benchmark failed: {error}")

        return SetupRepoSmokeResult(
            variables=variables,
            pages_health=pages_health,
            pages_interactive=pages_interactive,
            cli_smoke=cli_smoke,
            cli_benchmark=cli_benchmark,
            errors=errors,
        )

    def _validate_runtime_variables(self) -> tuple[RuntimeVariableObservation, ...]:
        return tuple(
            RuntimeVariableObservation(
                name=name,
                present=os.environ.get(name, "").strip() != "",
            )
            for name in self._config.auth_token_variables
        )

    def _probe_pages_health(self) -> PagesHealthObservation:
        url = self._config.app_url
        try:
            request = urllib_request.Request(url, method="GET")
            with urllib_request.urlopen(request, timeout=30) as response:
                status_code = response.getcode()
                html = response.read().decode("utf-8", errors="replace")
        except urllib_error.HTTPError as error:
            return PagesHealthObservation(
                url=url,
                status_code=error.code,
                title=None,
                base_href=None,
                contains_bootstrap_script=False,
                expected_title=self._config.expected_title,
                expected_base_href=self._config.expected_base_href,
                error=f"GET {url} failed with HTTP {error.code}.",
            )
        except urllib_error.URLError as error:
            return PagesHealthObservation(
                url=url,
                status_code=0,
                title=None,
                base_href=None,
                contains_bootstrap_script=False,
                expected_title=self._config.expected_title,
                expected_base_href=self._config.expected_base_href,
                error=f"GET {url} failed: {error.reason}",
            )
        except Exception as error:  # pragma: no cover - defensive catch
            return PagesHealthObservation(
                url=url,
                status_code=0,
                title=None,
                base_href=None,
                contains_bootstrap_script=False,
                expected_title=self._config.expected_title,
                expected_base_href=self._config.expected_base_href,
                error=str(error),
            )

        title_match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match else None

        base_match = re.search(
            r'<base[^>]+href=["\']([^"\']+)["\']', html, re.IGNORECASE
        )
        base_href = base_match.group(1) if base_match else None

        contains_bootstrap = "flutter_bootstrap.js" in html

        return PagesHealthObservation(
            url=url,
            status_code=status_code,
            title=title,
            base_href=base_href,
            contains_bootstrap_script=contains_bootstrap,
            expected_title=self._config.expected_title,
            expected_base_href=self._config.expected_base_href,
        )

    def _measure_pages_time_to_interactive(self) -> PagesInteractiveObservation:
        url = self._config.app_url
        if sync_playwright is None:
            return PagesInteractiveObservation(
                url=url,
                elapsed_seconds=0.0,
                budget_seconds=self._config.page_interactive_budget_seconds,
                labels_found=(),
                error="Playwright is not installed; cannot measure time-to-interactive.",
            )

        try:
            labels = self._config.shell_navigation_labels
            budget = self._config.page_interactive_budget_seconds

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(
                    args=[
                        "--disable-background-timer-throttling",
                        "--disable-renderer-backgrounding",
                        "--disable-backgrounding-occluded-windows",
                    ]
                )
                try:
                    context = browser.new_context(
                        viewport={"width": 1440, "height": 900}
                    )
                    try:
                        page = context.new_page()
                        try:
                            for _ in range(self._config.page_interactive_warmup_runs):
                                page.goto(url, wait_until="domcontentloaded", timeout=120_000)
                                page.wait_for_timeout(500)

                            started_at = time.monotonic()
                            response = page.goto(
                                url, wait_until="domcontentloaded", timeout=120_000
                            )
                            if response is None:
                                return PagesInteractiveObservation(
                                    url=url,
                                    elapsed_seconds=0.0,
                                    budget_seconds=budget,
                                    labels_found=(),
                                    error="No HTTP response received from the Pages URL.",
                                )

                            page.wait_for_function(
                                """
                                (labels) => {
                                    const bodyText = document.body?.innerText ?? '';
                                    return labels.every((label) => bodyText.includes(label));
                                }
                                """,
                                arg=list(labels),
                                timeout=60_000,
                            )
                            elapsed = time.monotonic() - started_at

                            return PagesInteractiveObservation(
                                url=url,
                                elapsed_seconds=elapsed,
                                budget_seconds=budget,
                                labels_found=labels,
                            )
                        finally:
                            page.close()
                    finally:
                        context.close()
                finally:
                    browser.close()
        except PlaywrightTimeoutError as error:
            return PagesInteractiveObservation(
                url=url,
                elapsed_seconds=0.0,
                budget_seconds=self._config.page_interactive_budget_seconds,
                labels_found=(),
                error=f"Timed out waiting for interactive shell: {error}",
            )
        except Exception as error:  # pragma: no cover - defensive catch
            return PagesInteractiveObservation(
                url=url,
                elapsed_seconds=0.0,
                budget_seconds=self._config.page_interactive_budget_seconds,
                labels_found=(),
                error=str(error),
            )

    def _run_cli_smoke(self) -> CliSmokeObservation:
        session = self._run_cli_command(
            [
                "session",
                "--target",
                "hosted",
                "--provider",
                "github",
                "--repository",
                self._config.repository,
                "--branch",
                self._config.ref,
            ]
        )

        summary = f"TS-24 smoke test {time.strftime('%Y%m%d-%H%M%S')}"
        create = self._run_cli_command(
            [
                "create",
                "--target",
                "hosted",
                "--provider",
                "github",
                "--repository",
                self._config.repository,
                "--branch",
                self._config.ref,
                "--project",
                "DEMO",
                "--summary",
                summary,
                "--issueType",
                "Story",
                "--priority",
                "Medium",
            ]
        )

        created_key = self._extract_issue_key(create)

        transition: CliCommandObservation | None = None
        if created_key:
            transition = self._run_cli_command(
                [
                    "jira_move_to_status",
                    "--target",
                    "hosted",
                    "--provider",
                    "github",
                    "--repository",
                    self._config.repository,
                    "--branch",
                    self._config.ref,
                    "--issueKey",
                    created_key,
                    "--status",
                    "Done",
                ]
            )

        search = self._run_cli_command(
            [
                "search",
                "--target",
                "hosted",
                "--provider",
                "github",
                "--repository",
                self._config.repository,
                "--branch",
                self._config.ref,
                "--jql",
                f'project = DEMO AND text ~ "{summary}"',
            ]
        )

        cleanup: CliCommandObservation | None = None
        delete: CliCommandObservation | None = None
        if created_key:
            cleanup = self._run_cli_command(
                [
                    "jira_move_to_status",
                    "--target",
                    "hosted",
                    "--provider",
                    "github",
                    "--repository",
                    self._config.repository,
                    "--branch",
                    self._config.ref,
                    "--issueKey",
                    created_key,
                    "--status",
                    "Done",
                ]
            )
            delete = self._delete_issue(created_key)

        return CliSmokeObservation(
            session=session,
            create=create,
            transition=transition,
            search=search,
            cleanup=cleanup,
            delete=delete,
        )

    def _delete_issue(self, issue_key: str) -> CliCommandObservation:
        return self._run_cli_command(
            [
                "delete",
                "--target",
                "hosted",
                "--provider",
                "github",
                "--repository",
                self._config.repository,
                "--branch",
                self._config.ref,
                "--issueKey",
                issue_key,
            ]
        )

    def _run_cli_benchmark(self) -> CliBenchmarkObservation:
        from concurrent.futures import as_completed

        config = self._config
        concurrency = config.benchmark_concurrency
        command_timeout = config.cli_command_timeout_seconds

        with self._benchmark_executor_factory(max_workers=concurrency) as executor:
            futures = {
                executor.submit(
                    _benchmark_worker,
                    worker_index,
                    config.repository,
                    config.ref,
                    command_timeout,
                    self._cli_runner,
                ): worker_index
                for worker_index in range(concurrency)
            }

            all_observations: list[CliCommandObservation] = []
            errors: list[str] = []
            for future in as_completed(futures):
                try:
                    observations = future.result()
                    all_observations.extend(observations)
                except Exception as error:  # pragma: no cover - defensive catch
                    errors.append(f"Benchmark worker failed: {error}")

        successful = [o for o in all_observations if o.succeeded]
        failed = [o for o in all_observations if not o.succeeded]
        latencies = [o.elapsed_seconds for o in successful]

        p95 = _percentile(latencies, 0.95) if latencies else 0.0
        max_latency = max(latencies) if latencies else 0.0

        return CliBenchmarkObservation(
            concurrency=concurrency,
            total_commands=len(all_observations),
            successful_commands=len(successful),
            failed_commands=len(failed),
            p95_seconds=p95,
            max_seconds=max_latency,
            budget_seconds=config.benchmark_command_budget_seconds,
            max_budget_seconds=config.benchmark_command_max_seconds,
            min_success_rate=config.benchmark_min_success_rate,
            errors=errors,
        )

    def _run_cli_command(self, arguments: list[str]) -> CliCommandObservation:
        return self._cli_runner(arguments)

    def _default_cli_runner(self, arguments: list[str]) -> CliCommandObservation:
        executable = self._resolve_cli_executable()
        command = [str(executable), *arguments]
        started_at = time.monotonic()
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=self._config.cli_command_timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            return CliCommandObservation(
                command=tuple(command),
                exit_code=1,
                elapsed_seconds=self._config.cli_command_timeout_seconds,
                error="CLI command timed out.",
            )
        elapsed = time.monotonic() - started_at

        return CliCommandObservation(
            command=tuple(command),
            exit_code=completed.returncode,
            elapsed_seconds=elapsed,
            issue_key=self._extract_issue_key_from_stdout(completed.stdout),
            error=completed.stderr.strip() if completed.returncode != 0 else None,
        )

    @staticmethod
    def _resolve_cli_executable() -> Path:
        repo_root = Path(__file__).resolve().parents[3]
        prebuilt = repo_root / "bin" / "trackstate_cli"
        if prebuilt.is_file():
            return prebuilt
        raise FileNotFoundError(
            "TrackState CLI executable not found. Expected bin/trackstate_cli."
        )

    @staticmethod
    def _extract_issue_key(observation: CliCommandObservation) -> str | None:
        return observation.issue_key

    @staticmethod
    def _extract_issue_key_from_stdout(stdout: str) -> str | None:
        payload = SetupRepoSmokeFramework._parse_json(stdout)
        if isinstance(payload, dict):
            data = payload.get("data")
            if isinstance(data, dict):
                issue = data.get("issue")
                if isinstance(issue, dict):
                    return str(issue.get("key"))
                issues = data.get("issues")
                if isinstance(issues, list) and issues:
                    first = issues[0]
                    if isinstance(first, dict):
                        return str(first.get("key"))
        return None

    @staticmethod
    def _parse_json(stdout: str) -> Any:
        text = stdout.strip()
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            first = text.find("{")
            last = text.rfind("}")
            if first == -1 or last == -1:
                return None
            try:
                return json.loads(text[first : last + 1])
            except json.JSONDecodeError:
                return None


def _benchmark_worker(
    worker_index: int,
    repository: str,
    ref: str,
    command_timeout: float,
    cli_runner: CliRunner | None = None,
) -> list[CliCommandObservation]:
    from testing.frameworks.python.setup_repo_smoke_framework import (
        SetupRepoSmokeFramework,
    )

    config = SetupRepoSmokeConfig(
        app_url="",
        repository=repository,
        ref=ref,
        auth_token_variables=(),
        expected_title="",
        expected_base_href="",
        shell_navigation_labels=(),
        page_interactive_budget_seconds=0.0,
        page_interactive_warmup_runs=0,
        cli_command_timeout_seconds=command_timeout,
        benchmark_concurrency=1,
        benchmark_command_budget_seconds=0.0,
        benchmark_command_max_seconds=0.0,
        benchmark_min_success_rate=0.0,
    )
    framework = SetupRepoSmokeFramework(config, cli_runner=cli_runner)
    summary = f"TS-24 benchmark worker {worker_index} {time.strftime('%Y%m%d-%H%M%S')}"

    observations: list[CliCommandObservation] = []

    observations.append(
        framework._run_cli_command(
            [
                "session",
                "--target",
                "hosted",
                "--provider",
                "github",
                "--repository",
                repository,
                "--branch",
                ref,
            ]
        )
    )

    create = framework._run_cli_command(
        [
            "create",
            "--target",
            "hosted",
            "--provider",
            "github",
            "--repository",
            repository,
            "--branch",
            ref,
            "--project",
            "DEMO",
            "--summary",
            summary,
            "--issueType",
            "Story",
            "--priority",
            "Medium",
        ]
    )
    observations.append(create)
    created_key = SetupRepoSmokeFramework._extract_issue_key(create)

    if created_key:
        observations.append(
            framework._run_cli_command(
                [
                    "read",
                    "ticket",
                    "--target",
                    "hosted",
                    "--provider",
                    "github",
                    "--repository",
                    repository,
                    "--branch",
                    ref,
                    "--key",
                    created_key,
                ]
            )
        )

        observations.append(
            framework._run_cli_command(
                [
                    "jira_move_to_status",
                    "--target",
                    "hosted",
                    "--provider",
                    "github",
                    "--repository",
                    repository,
                    "--branch",
                    ref,
                    "--issueKey",
                    created_key,
                    "--status",
                    "Done",
                ]
            )
        )

        observations.append(
            framework._run_cli_command(
                [
                    "delete",
                    "--target",
                    "hosted",
                    "--provider",
                    "github",
                    "--repository",
                    repository,
                    "--branch",
                    ref,
                    "--issueKey",
                    created_key,
                ]
            )
        )

    observations.append(
        framework._run_cli_command(
            [
                "search",
                "--target",
                "hosted",
                "--provider",
                "github",
                "--repository",
                repository,
                "--branch",
                ref,
                "--jql",
                "project = DEMO",
                "--max-results",
                "10",
            ]
        )
    )

    return observations


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    index = (len(sorted_values) - 1) * percentile
    lower = int(index)
    upper = lower + 1
    if upper >= len(sorted_values):
        return sorted_values[-1]
    weight = index - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight
