from __future__ import annotations

from dataclasses import dataclass

from testing.components.pages.trackstate_live_app_page import TrackStateLiveAppPage
from testing.core.interfaces.web_app_session import WebAppSession, WebAppTimeoutError


@dataclass(frozen=True)
class HostedIndexRecoveryObservation:
    body_text: str
    retry_visible: bool
    connect_github_visible: bool
    regenerate_guidance_visible: bool
    tracker_data_not_found_visible: bool
    app_title_visible: bool
    visible_button_labels: tuple[str, ...]


class LiveHostedIndexRecoveryPage:
    _button_selector = 'flt-semantics[role="button"]'
    _regenerate_guidance = "Regenerate the tracker indexes and retry."

    def __init__(self, session: WebAppSession, app_url: str) -> None:
        self._session = session
        self._live_page = TrackStateLiveAppPage(session, app_url)

    @property
    def regenerate_guidance(self) -> str:
        return self._regenerate_guidance

    def open(self) -> None:
        self._live_page.open()

    def wait_for_failure_surface(
        self,
        *,
        timeout_ms: int = 120_000,
    ) -> HostedIndexRecoveryObservation:
        try:
            self._session.wait_for_function(
                """
                (guidance) => {
                  const bodyText = document.body?.innerText ?? '';
                  return bodyText.includes(guidance)
                    || bodyText.includes('TrackState data was not found')
                    || bodyText.includes('Retry');
                }
                """,
                arg=self._regenerate_guidance,
                timeout_ms=timeout_ms,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                "Step 3 failed: the deployed app never exposed a visible failure "
                "surface for the missing hosted issues index scenario.\n"
                f"Observed body text:\n{self.current_body_text()}",
            ) from error
        return self.observe()

    def observe(self) -> HostedIndexRecoveryObservation:
        payload = self._session.evaluate(
            """
            (guidance) => {
              const bodyText = document.body?.innerText ?? '';
              const visibleButtonLabels = Array.from(
                document.querySelectorAll('flt-semantics[role="button"]'),
              )
                .map((candidate) => (candidate.innerText ?? '').trim())
                .filter((label) => label.length > 0);
              return {
                bodyText,
                retryVisible: bodyText.includes('Retry'),
                connectGitHubVisible: bodyText.includes('Connect GitHub'),
                regenerateGuidanceVisible: bodyText.includes(guidance),
                trackerDataNotFoundVisible: bodyText.includes('TrackState data was not found'),
                appTitleVisible: bodyText.includes('TrackState.AI'),
                visibleButtonLabels,
              };
            }
            """,
            arg=self._regenerate_guidance,
        )
        if not isinstance(payload, dict):
            raise AssertionError(
                "The hosted index recovery page did not expose a readable DOM snapshot.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        return HostedIndexRecoveryObservation(
            body_text=str(payload["bodyText"]),
            retry_visible=bool(payload["retryVisible"]),
            connect_github_visible=bool(payload["connectGitHubVisible"]),
            regenerate_guidance_visible=bool(payload["regenerateGuidanceVisible"]),
            tracker_data_not_found_visible=bool(payload["trackerDataNotFoundVisible"]),
            app_title_visible=bool(payload["appTitleVisible"]),
            visible_button_labels=tuple(
                str(item) for item in payload["visibleButtonLabels"]
            ),
        )

    def tap_retry(self) -> None:
        self._session.click(self._button_selector, has_text="Retry", timeout_ms=30_000)

    def current_body_text(self) -> str:
        return self._session.body_text()

    def screenshot(self, path: str) -> None:
        self._session.screenshot(path)
