from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from testing.core.interfaces.web_app_session import WebAppSession, WebAppTimeoutError


@dataclass(frozen=True)
class GitHubRepositoryBlobObservation:
    url: str
    matched_text: str
    body_text: str
    screenshot_path: str | None


class GitHubRepositoryBlobPage:
    def __init__(self, session: WebAppSession) -> None:
        self._session = session

    def open_blob_page(
        self,
        *,
        repository: str,
        ref: str,
        path: str,
        expected_texts: tuple[str, ...],
        screenshot_path: str | None = None,
        timeout_seconds: int = 60,
    ) -> GitHubRepositoryBlobObservation:
        url = self._build_blob_url(repository=repository, ref=ref, path=path)
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
            return GitHubRepositoryBlobObservation(
                url=url,
                matched_text=match.matched_text,
                body_text=match.body_text,
                screenshot_path=self._capture_screenshot(screenshot_path),
            )
        except WebAppTimeoutError as error:
            body_text = self._session.body_text()
            self._capture_screenshot(screenshot_path)
            raise AssertionError(
                "Could not open the GitHub repository file page.\n"
                f"URL: {url}\nVisible body text:\n{body_text}"
            ) from error

    @staticmethod
    def _build_blob_url(
        *,
        repository: str,
        ref: str,
        path: str,
    ) -> str:
        return f"https://github.com/{repository}/blob/{quote(ref, safe='')}/{quote(path, safe='/')}"

    def _capture_screenshot(self, screenshot_path: str | None) -> str | None:
        if screenshot_path is None:
            return None
        destination = Path(screenshot_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._session.screenshot(str(destination))
        except NotImplementedError:
            return None
        return str(destination) if destination.exists() else None
