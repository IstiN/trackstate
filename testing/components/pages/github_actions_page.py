from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from testing.core.interfaces.web_app_session import WebAppSession, WebAppTimeoutError


@dataclass(frozen=True)
class GitHubActionsPageObservation:
    url: str
    matched_text: str
    body_text: str
    screenshot_path: str | None


class GitHubActionsPage:
    def __init__(self, session: WebAppSession) -> None:
        self._session = session

    def open_page(
        self,
        *,
        url: str,
        expected_texts: Sequence[str],
        screenshot_path: str | None = None,
        timeout_seconds: int = 60,
    ) -> GitHubActionsPageObservation:
        try:
            self._session.goto(
                url,
                wait_until="domcontentloaded",
                timeout_ms=timeout_seconds * 1_000,
            )
            match = self._session.wait_for_any_text(
                tuple(dict.fromkeys(text for text in expected_texts if text)),
                timeout_ms=timeout_seconds * 1_000,
            )
            return GitHubActionsPageObservation(
                url=url,
                matched_text=match.matched_text,
                body_text=match.body_text,
                screenshot_path=self._capture_screenshot(screenshot_path),
            )
        except WebAppTimeoutError as error:
            body_text = self._session.body_text()
            self._capture_screenshot(screenshot_path)
            raise AssertionError(
                "Could not open the GitHub Actions page for human-style verification.\n"
                f"URL: {url}\nVisible body text:\n{body_text}"
            ) from error

    def _capture_screenshot(self, screenshot_path: str | None) -> str | None:
        if screenshot_path is None:
            return None
        destination = Path(screenshot_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        self._session.screenshot(str(destination))
        return str(destination) if destination.exists() else None
