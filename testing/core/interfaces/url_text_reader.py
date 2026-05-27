from __future__ import annotations

from typing import Mapping, Protocol


class UrlTextReaderError(RuntimeError):
    pass


class UrlTextReader(Protocol):
    def read_text(
        self,
        *,
        url: str,
        headers: Mapping[str, str],
        timeout_seconds: int,
    ) -> str: ...
