from __future__ import annotations

from dataclasses import dataclass
import re

from testing.components.pages.live_project_settings_page import LiveProjectSettingsPage
from testing.components.pages.trackstate_tracker_page import TrackStateTrackerPage


@dataclass(frozen=True)
class WorkspaceSyncSurfaceObservation:
    body_text: str
    settings_card_text: str
    header_pill_label: str
    settings_pill_label: str


class LiveWorkspaceSyncPage:
    _known_sync_labels = (
        "Synced with Git",
        "Syncing",
        "Attention needed",
        "Sync unavailable",
        "Updates pending",
    )

    def __init__(self, tracker_page: TrackStateTrackerPage) -> None:
        self._tracker_page = tracker_page
        self._session = tracker_page.session
        self._settings_page = LiveProjectSettingsPage(tracker_page)

    def ensure_connected(
        self,
        *,
        token: str,
        repository: str,
        user_login: str,
    ) -> str:
        return self._settings_page.ensure_connected(
            token=token,
            repository=repository,
            user_login=user_login,
        )

    def dismiss_connection_banner(self) -> None:
        self._settings_page.dismiss_connection_banner()

    def open_settings(self, *, timeout_ms: int = 60_000) -> WorkspaceSyncSurfaceObservation:
        self._settings_page.open_settings()
        return self.observe()

    def wait_for_status(
        self,
        expected_label: str,
        *,
        timeout_ms: int = 120_000,
    ) -> WorkspaceSyncSurfaceObservation:
        self._session.wait_for_function(
            """
            (expectedText) => (document.body?.innerText ?? '').includes(expectedText)
            """,
            arg=expected_label,
            timeout_ms=timeout_ms,
        )
        return self.observe()

    def observe(self) -> WorkspaceSyncSurfaceObservation:
        body_text = self._tracker_page.body_text()
        settings_card_text = _extract_workspace_sync_section(body_text) or ""
        header_pill_label = self._observe_header_pill_label()
        settings_pill_label = (
            _extract_settings_pill_label(
                settings_card_text,
                known_labels=self._known_sync_labels,
            )
            if settings_card_text
            else ""
        )
        return WorkspaceSyncSurfaceObservation(
            body_text=body_text,
            settings_card_text=settings_card_text,
            header_pill_label=header_pill_label,
            settings_pill_label=settings_pill_label,
        )

    def screenshot(self, path: str) -> None:
        self._tracker_page.screenshot(path)

    def _observe_header_pill_label(self) -> str:
        payload = self._session.evaluate(
            """
            (knownLabels) => {
              const normalize = (value) => (value ?? '').replace(/\\s+/g, ' ').trim();
              const isVisible = (element) => {
                if (!element) {
                  return false;
                }
                const rect = element.getBoundingClientRect();
                const style = window.getComputedStyle(element);
                return rect.width > 0
                  && rect.height > 0
                  && rect.y < 110
                  && style.visibility !== 'hidden'
                  && style.display !== 'none';
              };
              const area = (element) => {
                const rect = element.getBoundingClientRect();
                return rect.width * rect.height;
              };
              const labelOf = (element) => normalize(
                element.getAttribute('aria-label')
                || element.innerText
                || element.textContent,
              );
              const candidates = Array.from(
                document.querySelectorAll('flt-semantics, [aria-label]'),
              )
                .filter(isVisible)
                .filter((element) => knownLabels.includes(labelOf(element)))
                .sort((left, right) => area(left) - area(right));
              return candidates.length > 0 ? labelOf(candidates[0]) : null;
            }
            """,
            arg=list(self._known_sync_labels),
        )
        if not isinstance(payload, str) or not payload.strip():
            raise AssertionError(
                "The hosted top bar did not expose a readable sync pill label.",
            )
        return payload.strip()


def _extract_workspace_sync_section(body_text: str) -> str | None:
    normalized = body_text.replace("\r\n", "\n")
    match = re.search(
        r"Workspace sync(?P<section>.*?)(?:\nRepository access|\nProject settings administration|\Z)",
        normalized,
        flags=re.S,
    )
    if match is None:
        return None
    return f"Workspace sync{match.group('section')}".strip()


def _extract_settings_pill_label(
    settings_card_text: str,
    *,
    known_labels: tuple[str, ...],
) -> str:
    matches = [
        label for label in known_labels if re.search(re.escape(label), settings_card_text)
    ]
    if not matches:
        raise AssertionError(
            "The hosted `Workspace sync` section did not expose a readable status label.\n"
            f"Observed section text:\n{settings_card_text}",
        )
    return matches[-1]
