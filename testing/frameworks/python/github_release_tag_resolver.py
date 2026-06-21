from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from testing.core.interfaces.github_api_client import GitHubApiClient
from testing.core.interfaces.github_release_tag_resolver import (
    GitHubReleaseTagResolver,
)


class PythonGitHubReleaseTagResolver(GitHubReleaseTagResolver):
    def __init__(self, github_api_client: GitHubApiClient) -> None:
        self._github_api_client = github_api_client

    def resolve_release_tag(
        self,
        *,
        repository: str,
        pattern: str,
        env_key: str,
    ) -> str | None:
        compiled_pattern = re.compile(pattern)

        env_tag = os.getenv(env_key, "").strip()
        if env_tag:
            if compiled_pattern.fullmatch(env_tag) is not None:
                return env_tag
            raise ValueError(
                f"{env_key}={env_tag!r} does not match the configured "
                f"release tag pattern {pattern}."
            )

        ci_tag = _read_ci_release_tag(compiled_pattern)
        if ci_tag:
            return ci_tag

        return _latest_matching_release_tag(
            github_api_client=self._github_api_client,
            repository=repository,
            pattern=compiled_pattern,
        )


def _read_ci_release_tag(pattern: re.Pattern[str]) -> str | None:
    github_ref_name = os.getenv("GITHUB_REF_NAME", "").strip()
    if github_ref_name and pattern.fullmatch(github_ref_name) is not None:
        return github_ref_name

    event_path = os.getenv("GITHUB_EVENT_PATH")
    if not event_path:
        return None
    try:
        payload = json.loads(Path(event_path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None
    if not isinstance(payload, dict):
        return None

    inputs = payload.get("inputs")
    release = payload.get("release")
    candidates: list[str | None] = [
        _payload_string(inputs.get("release_ref")) if isinstance(inputs, dict) else None,
        _payload_string(release.get("tag_name")) if isinstance(release, dict) else None,
        _tag_from_ref(_payload_string(payload.get("ref"))),
    ]
    return _first_matching_ci_tag(pattern, candidates)


def _first_matching_ci_tag(
    pattern: re.Pattern[str],
    values: list[str | None],
) -> str | None:
    for value in values:
        if value is not None and pattern.fullmatch(value) is not None:
            return value
    return None


def _payload_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _tag_from_ref(ref: str | None) -> str | None:
    if ref is None:
        return None
    if ref.startswith("refs/tags/"):
        return ref.removeprefix("refs/tags/").strip() or None
    return None


def _latest_matching_release_tag(
    *,
    github_api_client: GitHubApiClient,
    repository: str,
    pattern: re.Pattern[str],
) -> str | None:
    endpoint = f"/repos/{repository}/releases?per_page=50"
    payload = json.loads(github_api_client.request_text(endpoint=endpoint))
    if not isinstance(payload, list):
        raise RuntimeError(f"GitHub releases API for {repository} did not return a list.")

    for entry in payload:
        if not isinstance(entry, dict):
            continue
        tag_name = str(entry.get("tag_name", "")).strip()
        if tag_name and pattern.fullmatch(tag_name) is not None:
            return tag_name
    return None
