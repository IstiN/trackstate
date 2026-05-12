from __future__ import annotations

from typing import Protocol

from testing.core.models.hosted_repository_file import HostedRepositoryFile


class HostedRepositoryClient(Protocol):
    token: str | None

    def fetch_repo_file(self, path: str) -> HostedRepositoryFile: ...

    def fetch_repo_text(self, path: str) -> str: ...

    def write_repo_text(self, path: str, *, content: str, message: str) -> None: ...

    def delete_repo_file(self, path: str, *, message: str) -> None: ...
