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


@dataclass(frozen=True)
class HeaderSyncStatusObservation:
    body_text: str
    accessible_label: str
    visible_label: str


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
        settings_card_text = self._observe_workspace_sync_card_text() or (
            _extract_workspace_sync_section(body_text) or ""
        )
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

    def observe_header_status(
        self,
        *,
        timeout_ms: int = 60_000,
    ) -> HeaderSyncStatusObservation:
        del timeout_ms
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
                  && rect.y < 140
                  && style.visibility !== 'hidden'
                  && style.display !== 'none';
              };
              const describe = (element) => {
                const rect = element.getBoundingClientRect();
                const accessibleLabel = normalize(element.getAttribute('aria-label'));
                const visibleLabel = normalize(element.innerText || element.textContent);
                const combinedLabel = accessibleLabel || visibleLabel;
                return {
                  element,
                  top: rect.y,
                  left: rect.x,
                  width: rect.width,
                  height: rect.height,
                  area: rect.width * rect.height,
                  accessibleLabel,
                  visibleLabel,
                  combinedLabel,
                };
              };
              const candidates = Array.from(
                document.querySelectorAll(
                  'button, [role="button"], flt-semantics, [aria-label]',
                ),
              )
                .filter(isVisible)
                .map(describe)
                .filter((candidate) =>
                  candidate.height <= 80
                  && candidate.width <= 280
                  && (
                    candidate.accessibleLabel.includes('Sync error')
                    || candidate.visibleLabel.includes('Sync error')
                    || candidate.combinedLabel.includes('Sync error')
                    || knownLabels.includes(candidate.accessibleLabel)
                    || knownLabels.includes(candidate.visibleLabel)
                    || knownLabels.includes(candidate.combinedLabel)
                  ),
                )
                .sort((left, right) => {
                  const topGap = left.top - right.top;
                  if (Math.abs(topGap) > 2) {
                    return topGap;
                  }
                  const leftGap = left.left - right.left;
                  if (Math.abs(leftGap) > 2) {
                    return leftGap;
                  }
                  return left.area - right.area;
                });
              if (candidates.length === 0) {
                return null;
              }
              const candidate = candidates[0];
              return {
                bodyText: document.body?.innerText ?? '',
                accessibleLabel: candidate.accessibleLabel || candidate.combinedLabel,
                visibleLabel: candidate.visibleLabel || candidate.combinedLabel,
              };
            }
            """,
            arg=list(self._known_sync_labels),
        )
        if not isinstance(payload, dict):
            raise AssertionError(
                "The hosted top bar did not expose a readable sync status pill.",
            )
        accessible_label = str(payload.get("accessibleLabel", "")).strip()
        visible_label = str(payload.get("visibleLabel", "")).strip()
        if not accessible_label and not visible_label:
            raise AssertionError(
                "The hosted top bar exposed a sync-status candidate, but it had neither a "
                "readable accessibility label nor visible text.",
            )
        return HeaderSyncStatusObservation(
            body_text=str(payload.get("bodyText", "")),
            accessible_label=accessible_label,
            visible_label=visible_label,
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

    def _observe_workspace_sync_card_text(self) -> str | None:
        payload = self._session.evaluate(
            """
            () => {
              const normalize = (value) => (value ?? '').replace(/\\s+/g, ' ').trim();
              const isVisible = (element) => {
                if (!element) {
                  return false;
                }
                const rect = element.getBoundingClientRect();
                const style = window.getComputedStyle(element);
                return rect.width > 0
                  && rect.height > 0
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
                document.querySelectorAll('flt-semantics[aria-label*="Workspace sync"]'),
              )
                .filter(isVisible)
                .sort((left, right) => area(right) - area(left));
              if (candidates.length === 0) {
                return null;
              }
              return labelOf(candidates[0]);
            }
            """,
        )
        if not isinstance(payload, str) or not payload.strip():
            return None
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
        return ""
    return matches[-1]
