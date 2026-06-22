from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RuntimeVariableObservation:
    name: str
    present: bool


@dataclass(frozen=True)
class PagesHealthObservation:
    url: str
    status_code: int
    title: str | None
    base_href: str | None
    contains_bootstrap_script: bool
    expected_title: str
    expected_base_href: str
    error: str | None = None

    @property
    def title_matches(self) -> bool:
        return self.title is not None and self.title.strip() == self.expected_title

    @property
    def base_href_matches(self) -> bool:
        return self.base_href is not None and self.base_href == self.expected_base_href

    @property
    def healthy(self) -> bool:
        return (
            self.status_code == 200
            and self.title_matches
            and self.base_href_matches
            and self.contains_bootstrap_script
            and self.error is None
        )


@dataclass(frozen=True)
class PagesInteractiveObservation:
    url: str
    elapsed_seconds: float
    budget_seconds: float
    labels_found: tuple[str, ...]
    error: str | None = None

    @property
    def within_budget(self) -> bool:
        return self.error is None and self.elapsed_seconds <= self.budget_seconds


@dataclass(frozen=True)
class CliCommandObservation:
    command: tuple[str, ...]
    exit_code: int
    elapsed_seconds: float
    issue_key: str | None = None
    error: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.exit_code == 0 and self.error is None


@dataclass(frozen=True)
class CliSmokeObservation:
    session: CliCommandObservation | None = None
    create: CliCommandObservation | None = None
    transition: CliCommandObservation | None = None
    search: CliCommandObservation | None = None
    cleanup: CliCommandObservation | None = None
    delete: CliCommandObservation | None = None

    @property
    def all_succeeded(self) -> bool:
        return all(
            observation is not None and observation.succeeded
            for observation in (self.session, self.create, self.transition, self.search, self.cleanup, self.delete)
        )


@dataclass(frozen=True)
class CliBenchmarkObservation:
    concurrency: int
    total_commands: int
    successful_commands: int
    failed_commands: int
    p95_seconds: float
    max_seconds: float
    budget_seconds: float
    max_budget_seconds: float
    min_success_rate: float = 1.0
    errors: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        success_rate = (
            self.successful_commands / self.total_commands
            if self.total_commands > 0
            else 0.0
        )
        return (
            self.failed_commands == 0
            and self.p95_seconds <= self.budget_seconds
            and self.max_seconds <= self.max_budget_seconds
            and success_rate >= self.min_success_rate
        )


@dataclass(frozen=True)
class SetupRepoSmokeResult:
    variables: tuple[RuntimeVariableObservation, ...]
    pages_health: PagesHealthObservation | None
    pages_interactive: PagesInteractiveObservation | None
    cli_smoke: CliSmokeObservation | None
    cli_benchmark: CliBenchmarkObservation | None
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "variables": [
                {"name": v.name, "present": v.present}
                for v in self.variables
            ],
            "pages_health": _pages_health_dict(self.pages_health),
            "pages_interactive": _pages_interactive_dict(self.pages_interactive),
            "cli_smoke": _cli_smoke_dict(self.cli_smoke),
            "cli_benchmark": _cli_benchmark_dict(self.cli_benchmark),
            "errors": list(self.errors),
        }


def _pages_health_dict(
    observation: PagesHealthObservation | None,
) -> dict[str, Any] | None:
    if observation is None:
        return None
    return {
        "url": observation.url,
        "status_code": observation.status_code,
        "title": observation.title,
        "base_href": observation.base_href,
        "expected_title": observation.expected_title,
        "expected_base_href": observation.expected_base_href,
        "title_matches": observation.title_matches,
        "base_href_matches": observation.base_href_matches,
        "contains_bootstrap_script": observation.contains_bootstrap_script,
        "healthy": observation.healthy,
        "error": observation.error,
    }


def _pages_interactive_dict(
    observation: PagesInteractiveObservation | None,
) -> dict[str, Any] | None:
    if observation is None:
        return None
    return {
        "url": observation.url,
        "elapsed_seconds": observation.elapsed_seconds,
        "budget_seconds": observation.budget_seconds,
        "labels_found": list(observation.labels_found),
        "within_budget": observation.within_budget,
        "error": observation.error,
    }


def _cli_command_dict(observation: CliCommandObservation | None) -> dict[str, Any] | None:
    if observation is None:
        return None
    return {
        "command": list(observation.command),
        "exit_code": observation.exit_code,
        "elapsed_seconds": observation.elapsed_seconds,
        "issue_key": observation.issue_key,
        "succeeded": observation.succeeded,
        "error": observation.error,
    }


def _cli_smoke_dict(observation: CliSmokeObservation | None) -> dict[str, Any] | None:
    if observation is None:
        return None
    return {
        "session": _cli_command_dict(observation.session),
        "create": _cli_command_dict(observation.create),
        "transition": _cli_command_dict(observation.transition),
        "search": _cli_command_dict(observation.search),
        "cleanup": _cli_command_dict(observation.cleanup),
        "delete": _cli_command_dict(observation.delete),
        "all_succeeded": observation.all_succeeded,
    }


def _cli_benchmark_dict(
    observation: CliBenchmarkObservation | None,
) -> dict[str, Any] | None:
    if observation is None:
        return None
    return {
        "concurrency": observation.concurrency,
        "total_commands": observation.total_commands,
        "successful_commands": observation.successful_commands,
        "failed_commands": observation.failed_commands,
        "p95_seconds": observation.p95_seconds,
        "max_seconds": observation.max_seconds,
        "budget_seconds": observation.budget_seconds,
        "max_budget_seconds": observation.max_budget_seconds,
        "passed": observation.passed,
        "errors": list(observation.errors),
    }
