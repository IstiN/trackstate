from __future__ import annotations

from typing import Any, Mapping, Protocol, Sequence


class GitHubApiClientError(RuntimeError):
    pass


class GitHubApiClient(Protocol):
    def request_text(
        self,
        *,
        endpoint: str,
        method: str = "GET",
        field_args: Sequence[str] | None = None,
        stdin_json: Mapping[str, Any] | None = None,
    ) -> str: ...
