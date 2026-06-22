from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class SetupRepoSmokeConfig:
    app_url: str
    repository: str
    ref: str
    auth_token_variables: tuple[str, ...]
    expected_title: str
    expected_base_href: str
    shell_navigation_labels: tuple[str, ...]
    page_interactive_budget_seconds: float
    page_interactive_warmup_runs: int
    cli_command_timeout_seconds: float
    benchmark_concurrency: int
    benchmark_command_budget_seconds: float
    benchmark_command_max_seconds: float
    benchmark_min_success_rate: float


def load_setup_repo_smoke_config() -> SetupRepoSmokeConfig:
    repository = os.getenv(
        "TRACKSTATE_LIVE_SETUP_REPOSITORY",
        "IstiN/trackstate-setup",
    )
    owner, _, name = repository.partition("/")
    if not name:
        name = owner
        owner = ""
    pages_domain = f"{owner.lower()}.github.io" if owner else "github.io"
    return SetupRepoSmokeConfig(
        app_url=os.getenv(
            "TRACKSTATE_LIVE_APP_URL",
            f"https://{pages_domain}/{name}/",
        ),
        repository=repository,
        ref=os.getenv("TRACKSTATE_LIVE_SETUP_REF", "main"),
        auth_token_variables=(
            "TRACKSTATE_TOKEN",
            "GH_TOKEN",
            "GITHUB_TOKEN",
        ),
        expected_title="TrackState.AI",
        expected_base_href=f"/{name}/",
        shell_navigation_labels=(
            "Dashboard",
            "Board",
            "JQL Search",
            "Hierarchy",
            "Settings",
        ),
        page_interactive_budget_seconds=3.0,
        page_interactive_warmup_runs=1,
        cli_command_timeout_seconds=30.0,
        benchmark_concurrency=10,
        benchmark_command_budget_seconds=3.0,
        benchmark_command_max_seconds=5.0,
        benchmark_min_success_rate=1.0,
    )
