from __future__ import annotations

from typing import Protocol


class GitHubReleaseTagResolver(Protocol):
    def resolve_release_tag(
        self,
        *,
        repository: str,
        pattern: str,
        env_key: str,
    ) -> str | None:
        """Resolve a release tag from environment, CI metadata, or latest matching release."""
        ...
