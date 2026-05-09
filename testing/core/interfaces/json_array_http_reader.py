from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol


class JsonArrayHttpReaderError(RuntimeError):
    pass


@dataclass(frozen=True)
class JsonArrayHttpResponse:
    status_code: int | None
    payload: list[object]


class JsonArrayHttpReader(Protocol):
    def read_json_array(
        self,
        *,
        url: str,
        headers: Mapping[str, str],
        timeout_seconds: int,
    ) -> JsonArrayHttpResponse: ...
