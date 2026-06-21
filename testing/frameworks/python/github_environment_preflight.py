from __future__ import annotations

import os
import shutil
import subprocess

from testing.core.interfaces.non_default_branch_release_repository import (
    NonDefaultBranchReleaseEnvironmentError,
)
from testing.frameworks.python.gh_cli_api_client import _resolve_gh_executable


DEFAULT_COMMAND_TIMEOUT_SECONDS = 30.0


def verify_github_environment(
    repository: str,
    *,
    gh_executable: str | None = None,
    command_timeout_seconds: float = DEFAULT_COMMAND_TIMEOUT_SECONDS,
) -> None:
    """Fail fast if the current environment cannot use the live GitHub API.

    Verifies, with a bounded timeout, that:
      1. the GitHub CLI executable is available on PATH;
      2. the GitHub CLI is authenticated;
      3. the GitHub API can read the configured repository.

    Raises:
        NonDefaultBranchReleaseEnvironmentError: when any precondition is not met.
    """
    gh = gh_executable or _resolve_gh_executable()
    if shutil.which(gh) is None:
        raise NonDefaultBranchReleaseEnvironmentError(
            f"TS-252 precondition failed: GitHub CLI ({gh}) is not installed or not on PATH. "
            "Live GitHub API interactions are unavailable in this environment."
        )

    _run_gh_command(
        [gh, "auth", "status"],
        timeout_seconds=command_timeout_seconds,
        error_message="TS-252 precondition failed: GitHub CLI is not authenticated. "
        "Live GitHub API interactions are unavailable in this environment.",
    )

    _run_gh_command(
        [gh, "api", f"/repos/{repository}"],
        timeout_seconds=command_timeout_seconds,
        error_message=f"TS-252 precondition failed: cannot access repository {repository} "
        "via the GitHub API. The current environment may lack network access or "
        "repository permissions, so live GitHub interactions are unavailable.",
    )


def _run_gh_command(
    command: list[str],
    *,
    timeout_seconds: float,
    error_message: str,
) -> None:
    environment = os.environ.copy()
    environment.setdefault("GH_PAGER", "cat")
    environment.setdefault("GIT_TERMINAL_PROMPT", "0")

    try:
        completed = subprocess.run(
            command,
            cwd=None,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as error:
        stderr = error.stderr if isinstance(error.stderr, str) else ""
        raise NonDefaultBranchReleaseEnvironmentError(
            f"{error_message}\nCommand timed out after {timeout_seconds}s: "
            f"{' '.join(command)}\nSTDERR:\n{stderr}"
        ) from error

    if completed.returncode != 0:
        raise NonDefaultBranchReleaseEnvironmentError(
            f"{error_message}\nCommand: {' '.join(command)}\n"
            f"STDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
        )
