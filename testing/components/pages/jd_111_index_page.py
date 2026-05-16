from __future__ import annotations

from dataclasses import dataclass

from testing.core.interfaces.web_app_session import WebAppSession


@dataclass(frozen=True)
class JD111IndexPageObservation:
    url: str
    title: str
    body_text: str
    headings: tuple[str, ...]
    feature_card_count: int
    workflow_step_count: int
    tech_tag_count: int
    html_excerpt: str


class JD111IndexPage:
    def __init__(self, session: WebAppSession, index_url: str) -> None:
        self._session = session
        self._index_url = index_url

    def open(self) -> None:
        self._session.goto(
            self._index_url,
            wait_until="load",
            timeout_ms=120_000,
        )

    def observe(self) -> JD111IndexPageObservation:
        payload = self._session.evaluate(
            """
            () => {
                const text = (value) => (value || '').replace(/\\s+/g, ' ').trim();
                const headingSelectors = 'h1, h2, h3, [role="heading"]';
                const headings = Array.from(document.querySelectorAll(headingSelectors))
                    .map((element) => text(element.textContent))
                    .filter(Boolean);
                return {
                    url: window.location.href,
                    title: document.title,
                    bodyText: text(document.body?.innerText ?? ''),
                    headings,
                    featureCardCount: document.querySelectorAll('.feature-card').length,
                    workflowStepCount: document.querySelectorAll('.workflow-steps li').length,
                    techTagCount: document.querySelectorAll('.tech-tag').length,
                    htmlExcerpt: (document.body?.innerHTML ?? '').slice(0, 4000),
                };
            }
            """,
        )
        return JD111IndexPageObservation(
            url=str(payload["url"]),
            title=str(payload["title"]),
            body_text=str(payload["bodyText"]),
            headings=tuple(str(item) for item in payload["headings"]),
            feature_card_count=int(payload["featureCardCount"]),
            workflow_step_count=int(payload["workflowStepCount"]),
            tech_tag_count=int(payload["techTagCount"]),
            html_excerpt=str(payload["htmlExcerpt"]),
        )

    def screenshot(self, path: str) -> None:
        self._session.screenshot(path)
