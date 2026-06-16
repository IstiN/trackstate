from __future__ import annotations

from dataclasses import dataclass

from testing.core.interfaces.web_app_session import WebAppSession, WebAppTimeoutError


@dataclass(frozen=True)
class GitHubRepositoryDirectoryObservation:
    url: str
    body_text: str


class GitHubRepositoryDirectoryPage:
    def __init__(self, session: WebAppSession) -> None:
        self._session = session

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
        body_text = self._open_in_browser(
            url=url,
            expected_filename=expected_filename,
            timeout_seconds=timeout_seconds,
        )
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

    def _open_in_browser(
        self,
        *,
        url: str,
        expected_filename: str,
        timeout_seconds: int,
    ) -> str:
        try:
            self._session.goto(
                url,
                wait_until="domcontentloaded",
                timeout_ms=timeout_seconds * 1_000,
            )
            return self._session.wait_for_text(
                expected_filename,
                timeout_ms=timeout_seconds * 1_000,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                "Could not open the GitHub repository directory page for human-style "
                f"verification in the browser.\nURL: {url}\nVisible body text:\n"
                f"{self._session.body_text()}"
            ) from error
