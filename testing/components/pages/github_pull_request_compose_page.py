from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from testing.core.interfaces.web_app_session import WebAppSession, WebAppTimeoutError


@dataclass(frozen=True)
class GitHubPullRequestComposeObservation:
    url: str
    matched_text: str
    body_text: str
    screenshot_path: str | None
    description_value: str | None
    description_selector: str | None


class GitHubPullRequestComposePage:
    def __init__(self, session: WebAppSession) -> None:
        self._session = session

    def open_compose_surface(
        self,
        *,
        repository: str,
        base_branch: str,
        head_branch: str,
        expected_texts: tuple[str, ...],
        screenshot_path: str | None = None,
        timeout_seconds: int = 60,
    ) -> GitHubPullRequestComposeObservation:
        url = self._build_compare_url(
            repository=repository,
            base_branch=base_branch,
            head_branch=head_branch,
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
            description_selector, description_value = (None, None)
            if match.matched_text == "Open a pull request":
                description_selector, description_value = self._read_description_field(
                    timeout_seconds=timeout_seconds
                )
            return GitHubPullRequestComposeObservation(
                url=url,
                matched_text=match.matched_text,
                body_text=match.body_text,
                screenshot_path=self._capture_screenshot(screenshot_path),
                description_value=description_value,
                description_selector=description_selector,
            )
        except WebAppTimeoutError as error:
            body_text = self._session.body_text()
            self._capture_screenshot(screenshot_path)
            raise AssertionError(
                "Could not open the GitHub pull-request compose surface.\n"
                f"URL: {url}\nVisible body text:\n{body_text}"
            ) from error

    def _build_compare_url(
        self,
        *,
        repository: str,
        base_branch: str,
        head_branch: str,
    ) -> str:
        return (
            f"https://github.com/{repository}/compare/"
            f"{quote(base_branch, safe='')}...{quote(head_branch, safe='')}?expand=1"
        )

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

    def _read_description_field(
        self,
        *,
        timeout_seconds: int,
    ) -> tuple[str | None, str | None]:
        evaluated_field = self._evaluate_description_field()
        if evaluated_field is not None:
            return evaluated_field

        selectors = (
            'textarea[name="pull_request[body]"]',
            'textarea[name="issue[body]"]',
            'textarea[id="pull_request_body"]',
            'textarea[id="issue_body"]',
            'textarea[name*="body"]',
            'textarea[id*="body"]',
            'textarea[aria-label*="description"]',
            'textarea[aria-label*="Description"]',
            'textarea[placeholder*="description"]',
            'textarea[placeholder*="Describe"]',
            'input[name*="body"]',
            'input[id*="body"]',
        )
        for selector in selectors:
            try:
                return (
                    selector,
                    self._session.read_value(
                        selector,
                        timeout_ms=timeout_seconds * 1_000,
                    ),
                )
            except (NotImplementedError, WebAppTimeoutError):
                continue
        return None, None

    def _evaluate_description_field(self) -> tuple[str | None, str | None] | None:
        try:
            payload = self._session.evaluate(
                """
                () => {
                  const controls = Array.from(
                    document.querySelectorAll("textarea, input")
                  )
                    .map((element) => {
                      if (!("value" in element) || typeof element.value !== "string") {
                        return null;
                      }
                      const name = element.getAttribute("name") || "";
                      const id = element.getAttribute("id") || "";
                      const ariaLabel = element.getAttribute("aria-label") || "";
                      const placeholder = element.getAttribute("placeholder") || "";
                      const descriptor = `${name} ${id} ${ariaLabel} ${placeholder}`.toLowerCase();
                      let score = 0;
                      if (descriptor.includes("pull_request")) score += 6;
                      if (descriptor.includes("issue")) score += 5;
                      if (descriptor.includes("body")) score += 5;
                      if (descriptor.includes("description")) score += 4;
                      if (descriptor.includes("describe")) score += 3;
                      if (score <= 0) {
                        return null;
                      }
                      if (element.tagName === "TEXTAREA") score += 2;
                      let selector = element.tagName.toLowerCase();
                      if (id) {
                        selector += `#${id}`;
                      } else if (name) {
                        selector += `[name="${name.replace(/"/g, '\\"')}"]`;
                      }
                      return {
                        score,
                        selector,
                        value: element.value,
                      };
                    })
                    .filter(Boolean)
                    .sort((left, right) => right.score - left.score);
                  return controls[0] ?? null;
                }
                """
            )
        except NotImplementedError:
            return None

        if not isinstance(payload, dict):
            return None
        value = payload.get("value")
        if not isinstance(value, str):
            return None
        selector = payload.get("selector")
        return (
            selector if isinstance(selector, str) and selector else None,
            value,
        )
