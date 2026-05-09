from __future__ import annotations

import json
from urllib import error as urllib_error
from urllib import request as urllib_request

from testing.core.interfaces.json_array_http_reader import (
    JsonArrayHttpReader,
    JsonArrayHttpReaderError,
    JsonArrayHttpResponse,
)


class UrllibJsonArrayHttpReader(JsonArrayHttpReader):
    def read_json_array(
        self,
        *,
        url: str,
        headers: dict[str, str],
        timeout_seconds: int,
    ) -> JsonArrayHttpResponse:
        request = urllib_request.Request(url, headers=headers)
        try:
            with urllib_request.urlopen(request, timeout=timeout_seconds) as response:
                status_code = response.getcode()
                body = response.read().decode("utf-8")
        except urllib_error.HTTPError as error:
            status_code = error.code
            body = error.read().decode("utf-8", errors="replace")
        except urllib_error.URLError as error:
            raise JsonArrayHttpReaderError(f"GET {url} failed: {error.reason}") from error

        try:
            payload = json.loads(body or "[]")
        except json.JSONDecodeError as error:
            raise JsonArrayHttpReaderError(
                f"GET {url} returned invalid JSON payload."
            ) from error

        if not isinstance(payload, list):
            payload = []

        return JsonArrayHttpResponse(
            status_code=status_code,
            payload=payload,
        )
