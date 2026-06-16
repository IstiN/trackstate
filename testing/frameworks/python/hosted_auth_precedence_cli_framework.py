from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import urllib.error
import urllib.request

from testing.core.config.hosted_auth_precedence_cli_config import (
    HostedAuthPrecedenceCliConfig,
)
from testing.core.models.cli_command_result import CliCommandResult
from testing.core.models.hosted_auth_precedence_cli_result import (
    HostedAuthPrecedenceCliObservation,
    HostedAuthPrecedenceTokenResolution,
)


class PythonHostedAuthPrecedenceCliFramework:
    def __init__(self, repository_root: Path) -> None:
        self._repository_root = Path(repository_root)

    def resolve_environment_token(
        self,
    ) -> tuple[HostedAuthPrecedenceTokenResolution, str | None]:
        explicit_test_token = os.environ.get("TS271_VALID_TRACKSTATE_TOKEN", "").strip()
        if explicit_test_token:
            return (
                HostedAuthPrecedenceTokenResolution(
                    source="TS271_VALID_TRACKSTATE_TOKEN",
                    probe_result=None,
                ),
                explicit_test_token,
            )

        trackstate_env_token = os.environ.get("TRACKSTATE_TOKEN", "").strip()
        if trackstate_env_token:
            return (
                HostedAuthPrecedenceTokenResolution(
                    source="TRACKSTATE_TOKEN",
                    probe_result=None,
                ),
                trackstate_env_token,
            )

        gh_auth_token = self._run(("gh", "auth", "token"))
        if gh_auth_token.succeeded and gh_auth_token.stdout.strip():
            return (
                HostedAuthPrecedenceTokenResolution(
                    source="gh auth token",
                    probe_result=CliCommandResult(
                        command=gh_auth_token.command,
                        exit_code=gh_auth_token.exit_code,
                        stdout="[redacted]",
                        stderr=gh_auth_token.stderr,
                    ),
                ),
                gh_auth_token.stdout.strip(),
            )

        return (
            HostedAuthPrecedenceTokenResolution(
                source="missing",
                probe_result=CliCommandResult(
                    command=gh_auth_token.command,
                    exit_code=gh_auth_token.exit_code,
                    stdout="[redacted]",
                    stderr=gh_auth_token.stderr,
                ),
            ),
            None,
        )

    def verify_hosted_repository_has_project_json(
        self,
        *,
        config: HostedAuthPrecedenceCliConfig,
        environment_token: str,
    ) -> tuple[bool, str | None]:
        branch = os.environ.get("TS271_REPOSITORY_REF", "main")
        url = (
            f"https://api.github.com/repos/{config.repository}"
            f"/git/trees/{branch}?recursive=1"
        )
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "trackstate-ts271-automation",
        }
        if environment_token:
            headers["Authorization"] = f"Bearer {environment_token}"
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            return (
                False,
                f"GitHub API returned HTTP {error.code} while probing "
                f"{config.repository} for project.json: {body}",
            )
        except urllib.error.URLError as error:
            return (
                False,
                f"Could not reach GitHub API to probe {config.repository} "
                f"for project.json: {error.reason}",
            )
        except Exception as error:  # noqa: BLE001
            return (
                False,
                f"Unexpected error probing {config.repository} for project.json: "
                f"{type(error).__name__}: {error}",
            )

        tree = payload.get("tree", [])
        if not isinstance(tree, list):
            return (
                False,
                f"GitHub API tree payload for {config.repository} did not contain "
                "a list of entries.",
            )

        for entry in tree:
            if not isinstance(entry, dict):
                continue
            path = entry.get("path", "")
            if path == "project.json" or path.endswith("/project.json"):
                return True, path
        return (
            False,
            f"No project.json was found in {config.repository}@{branch}. "
            "The configured repository does not appear to be an initialized "
            "TrackState project.",
        )

    def hosted_session_with_environment_token(
        self,
        *,
        config: HostedAuthPrecedenceCliConfig,
        environment_token: str,
    ) -> HostedAuthPrecedenceCliObservation:
        return self._run_hosted_command(
            requested_command=config.requested_environment_command,
            fallback_command=config.fallback_environment_command,
            environment_token=environment_token,
        )

    def hosted_session_with_explicit_invalid_token(
        self,
        *,
        config: HostedAuthPrecedenceCliConfig,
        environment_token: str,
    ) -> HostedAuthPrecedenceCliObservation:
        return self._run_hosted_command(
            requested_command=config.requested_invalid_token_command,
            fallback_command=config.fallback_invalid_token_command,
            environment_token=environment_token,
        )

    def _run_hosted_command(
        self,
        *,
        requested_command: tuple[str, ...],
        fallback_command: tuple[str, ...],
        environment_token: str,
    ) -> HostedAuthPrecedenceCliObservation:
        preferred_binary = shutil.which(requested_command[0])
        if preferred_binary:
            executed_command = (preferred_binary, *requested_command[1:])
            fallback_reason = None
        else:
            executed_command = fallback_command
            fallback_reason = (
                f'"{requested_command[0]}" was not available on PATH, so the test '
                "used the package executable via `dart run trackstate session`."
            )

        return HostedAuthPrecedenceCliObservation(
            requested_command=requested_command,
            executed_command=executed_command,
            fallback_reason=fallback_reason,
            result=self._run(executed_command, environment_token=environment_token),
        )

    def _run(
        self,
        command: tuple[str, ...],
        *,
        environment_token: str | None = None,
    ) -> CliCommandResult:
        env = os.environ.copy()
        env.setdefault("CI", "true")
        env.setdefault("PUB_CACHE", str(Path.home() / ".pub-cache"))
        if environment_token is not None:
            env["TRACKSTATE_TOKEN"] = environment_token

        completed = subprocess.run(
            command,
            cwd=self._repository_root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        return CliCommandResult(
            command=command,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            json_payload=self._parse_json(completed.stdout),
        )

    def _parse_json(self, stdout: str) -> object | None:
        payload = stdout.strip()
        if not payload:
            return None
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            return None
