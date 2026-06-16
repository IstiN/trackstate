from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from testing.core.interfaces.web_app_session import WebAppSession, WebAppTimeoutError


@dataclass(frozen=True)
class GitHubRepositoryFileObservation:
    url: str
    matched_text: str
    body_text: str
    screenshot_path: str | None


class GitHubRepositoryFilePage:
    def __init__(self, session: WebAppSession) -> None:
        self._session = session

    def open_file(
        self,
        *,
        repository: str,
        branch: str,
        file_path: str,
        expected_texts: tuple[str, ...],
        screenshot_path: str | None = None,
        timeout_seconds: int = 60,
    ) -> GitHubRepositoryFileObservation:
        url = self._build_file_url(
            repository=repository,
            branch=branch,
            file_path=file_path,
        )
        try:
            self._session.goto(
                url,
                wait_until="domcontentloaded",
                timeout_ms=timeout_seconds * 1_000,
            )
            match = self._session.wait_for_any_text(
                expected_texts,
                timeout_ms=timeout_seconds * 1_000,
            )
            return GitHubRepositoryFileObservation(
                url=url,
                matched_text=match.matched_text,
                body_text=match.body_text,
                screenshot_path=self._capture_screenshot(screenshot_path),
            )
        except WebAppTimeoutError as error:
            body_text = self._session.body_text()
            self._capture_screenshot(screenshot_path)
            raise AssertionError(
                "Could not open the GitHub repository file page for human-style "
                f"verification in the browser.\nURL: {url}\nVisible body text:\n"
                f"{body_text}"
            ) from error

    def _build_file_url(
        self,
        *,
        repository: str,
        branch: str,
        file_path: str,
    ) -> str:
        normalized_path = file_path.strip("/")
        encoded_segments = "/".join(
            quote(segment, safe="") for segment in normalized_path.split("/") if segment
        )
        return f"https://github.com/{repository}/blob/{quote(branch, safe='')}/{encoded_segments}"

    def _capture_screenshot(self, screenshot_path: str | None) -> str | None:
        if screenshot_path is None:
            return None
        destination = Path(screenshot_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        self._session.screenshot(str(destination))
        return str(destination) if destination.exists() else None
