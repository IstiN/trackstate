from __future__ import annotations

from urllib import error as urllib_error
from urllib import request as urllib_request

from testing.core.interfaces.url_text_reader import UrlTextReader, UrlTextReaderError


class UrllibUrlTextReader(UrlTextReader):
    def read_text(
        self,
        *,
        url: str,
        headers: dict[str, str],
        timeout_seconds: int,
    ) -> str:
        request = urllib_request.Request(url, headers=headers)
        try:
            with urllib_request.urlopen(request, timeout=timeout_seconds) as response:
                return response.read().decode("utf-8")
        except urllib_error.HTTPError as error:
            raise UrlTextReaderError(f"GET {url} failed with HTTP {error.code}.") from error
        except urllib_error.URLError as error:
            raise UrlTextReaderError(f"GET {url} failed: {error.reason}") from error
