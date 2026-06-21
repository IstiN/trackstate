from __future__ import annotations

from typing import Any, Mapping, Protocol, Sequence


class GitHubApiClientError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class GitHubApiClient(Protocol):
    def request_text(
        self,
        *,
        endpoint: str,
        method: str = "GET",
        field_args: Sequence[str] | None = None,
        stdin_json: Mapping[str, Any] | None = None,
    ) -> str: ...
