from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser

from testing.core.interfaces.url_text_reader import UrlTextReader, UrlTextReaderError


class _VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []

    def handle_data(self, data: str) -> None:
        stripped = data.strip()
        if stripped:
            self._chunks.append(stripped)

    def text(self) -> str:
        return "\n".join(self._chunks)


@dataclass(frozen=True)
class GitHubRepositoryDirectoryObservation:
    url: str
    body_text: str


class GitHubRepositoryDirectoryPage:
    def __init__(self, url_text_reader: UrlTextReader) -> None:
        self._url_text_reader = url_text_reader

    def open_directory(
        self,
        *,
        repository: str,
        branch: str,
        directory_path: str,
        expected_filename: str,
        timeout_seconds: int = 60,
    ) -> GitHubRepositoryDirectoryObservation:
        url = self._build_directory_url(
            repository=repository,
            branch=branch,
            directory_path=directory_path,
        )
        html = self._read_html(url=url, timeout_seconds=timeout_seconds)
        body_text = self._html_to_visible_text(html)
        if expected_filename not in body_text:
            raise AssertionError(
                "Timed out waiting for the workflow filename to appear on the GitHub "
                f"directory page.\nURL: {url}\nVisible body text:\n{body_text}",
            )
        return GitHubRepositoryDirectoryObservation(url=url, body_text=body_text)

    def _build_directory_url(
        self,
        *,
        repository: str,
        branch: str,
        directory_path: str,
    ) -> str:
        normalized_directory = directory_path.strip("/")
        return f"https://github.com/{repository}/tree/{branch}/{normalized_directory}"

    def _read_html(self, *, url: str, timeout_seconds: int) -> str:
        try:
            return self._url_text_reader.read_text(
                url=url,
                headers={"User-Agent": "trackstate-ts82-test"},
                timeout_seconds=timeout_seconds,
            )
        except UrlTextReaderError as error:
            raise AssertionError(
                "Could not open the GitHub repository directory page for human-style "
                f"verification.\nURL: {url}\n{error}"
            ) from error

    def _html_to_visible_text(self, html: str) -> str:
        parser = _VisibleTextParser()
        parser.feed(html)
        return parser.text()
