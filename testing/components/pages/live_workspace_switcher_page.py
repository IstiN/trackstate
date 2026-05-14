from __future__ import annotations

from dataclasses import dataclass

from testing.components.pages.trackstate_tracker_page import TrackStateTrackerPage


@dataclass(frozen=True)
class WorkspaceSwitcherRowObservation:
    display_name: str | None
    target_type_label: str | None
    state_label: str | None
    detail_text: str
    visible_text: str
    selected: bool
    semantics_label: str | None
    icon_accessibility_label: str | None
    action_labels: tuple[str, ...]
    button_labels: tuple[str, ...]


@dataclass(frozen=True)
class WorkspaceSwitcherObservation:
    body_text: str
    switcher_text: str
    row_count: int
    rows: tuple[WorkspaceSwitcherRowObservation, ...]


class LiveWorkspaceSwitcherPage:
    _trigger_label_prefix = "Workspace switcher:"
    _button_selector = 'flt-semantics[role="button"]'
    _switcher_heading = "Workspace switcher"

    def __init__(self, tracker_page: TrackStateTrackerPage) -> None:
        self._tracker_page = tracker_page
        self._session = tracker_page.session

    def open_and_observe(
        self,
        *,
        timeout_ms: int = 60_000,
    ) -> WorkspaceSwitcherObservation:
        self._click_trigger(timeout_ms=timeout_ms)
        payload = self._session.wait_for_function(
            """
            ({ heading }) => {
              const normalize = (value) => (value || '').replace(/\\s+/g, ' ').trim();
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
              const accessibleLabel = (element) =>
                normalize(
                  element?.getAttribute?.('aria-label')
                    || element?.getAttribute?.('alt')
                    || element?.getAttribute?.('title')
                    || element?.innerText
                    || ''
                );
              const dedupeRepeatedLine = (value) => {
                const normalized = normalize(value);
                const match = normalized.match(/^(.+)\\s+\\1$/);
                return match ? match[1] : normalized;
              };
              const visibleElements = (root, selector = '*') =>
                Array.from(root.querySelectorAll(selector)).filter((candidate) => isVisible(candidate));
              const bodyText = document.body?.innerText ?? '';
              if (!bodyText.includes(heading)) {
                return null;
              }

              const headings = visibleElements(document, 'flt-semantics,[aria-label],h1,h2,h3')
                .map((element) => ({
                  element,
                  label: normalize(element.getAttribute?.('aria-label') || ''),
                  text: normalize(element.innerText || ''),
                  area: (() => {
                    const rect = element.getBoundingClientRect();
                    return rect.width * rect.height;
                  })(),
                }))
                .filter((candidate) => candidate.label === heading || candidate.text === heading)
                .sort((left, right) => left.area - right.area);

              let switcher = null;
              for (const headingCandidate of headings) {
                let current = headingCandidate.element;
                while (current && current !== document.body) {
                  const text = normalize(current.innerText || '');
                  if (text.includes(heading) && text.includes('Saved workspaces') && text.includes('Add workspace')) {
                    switcher = current;
                    break;
                  }
                  current = current.parentElement;
                }
                if (switcher) {
                  break;
                }
              }
              if (!switcher) {
                return null;
              }

              const actionLabels = ['Open workspace', 'Active', 'Delete'];
              const stateLabels = [
                'Local Git',
                'Needs sign-in',
                'Connected',
                'Read-only',
                'Saved hosted workspace',
                'Unavailable',
                'Attachments limited',
              ];

              const buttonNodes = visibleElements(
                switcher,
                'flt-semantics[role="button"],[role="button"],button',
              );
              const rowCandidates = buttonNodes
                .filter((element) => accessibleLabel(element) === 'Delete')
                .map((deleteButton) => {
                  let current = deleteButton;
                  while (current && current !== switcher.parentElement) {
                    const text = normalize(current.innerText || '');
                    const buttonLabels = buttonNodes
                      .filter((candidate) => current.contains(candidate))
                      .map((candidate) => accessibleLabel(candidate))
                      .filter((label) => label.length > 0);
                    const hasTypeLabel = text.includes('Hosted') || text.includes('Local');
                    if (
                      hasTypeLabel
                      && text.includes('Branch:')
                      && buttonLabels.includes('Delete')
                      && (buttonLabels.includes('Open workspace') || text.includes('Active'))
                    ) {
                      const rect = current.getBoundingClientRect();
                      return {
                        element: current,
                        text,
                        area: rect.width * rect.height,
                      };
                    }
                    current = current.parentElement;
                  }
                  return null;
                })
                .filter((candidate) => candidate)
                .sort((left, right) => left.area - right.area);

              const rows = [];
              for (const candidate of rowCandidates) {
                if (rows.some((accepted) => accepted.element.contains(candidate.element))) {
                  continue;
                }
                rows.push(candidate);
              }

              return {
                bodyText,
                switcherText: normalize(switcher.innerText || ''),
                rows: rows.map((rowCandidate) => {
                  const rowElement = rowCandidate.element;
                  const rawLines = (rowElement.innerText || '')
                    .split(/\\n+/)
                    .map((line) => dedupeRepeatedLine(line))
                    .filter((line) => line.length > 0 && line !== heading && line !== 'Saved workspaces');
                  const rowActionLabels = rawLines.filter((line) => actionLabels.includes(line));
                  const contentLines = rawLines.filter((line) => !actionLabels.includes(line));
                  const typeLabel =
                    contentLines.find((line) => line === 'Hosted' || line === 'Local') ?? null;
                  const stateLabel =
                    contentLines.find((line) => stateLabels.includes(line)) ?? null;
                  const detailText =
                    contentLines.find((line) => line.includes('Branch:')) ?? '';
                  const displayName =
                    contentLines.find((line) =>
                      line !== typeLabel
                      && line !== stateLabel
                      && line !== detailText
                    ) ?? null;
                  const semanticsLabels = [rowElement, ...visibleElements(rowElement, 'flt-semantics[aria-label],[aria-label]')]
                    .map((element) => dedupeRepeatedLine(element.getAttribute('aria-label') || ''))
                    .filter((label) =>
                      label.length > 0
                      && label !== 'repository'
                      && label !== 'folder'
                      && !actionLabels.includes(label)
                    );
                  const iconLabel =
                    [rowElement, ...visibleElements(rowElement, 'flt-semantics[aria-label],[aria-label]')]
                      .map((element) => dedupeRepeatedLine(element.getAttribute('aria-label') || ''))
                      .find((label) => label === 'repository' || label === 'folder')
                    ?? null;
                  const buttonLabels = visibleElements(
                    rowElement,
                    'flt-semantics[role="button"],[role="button"],button',
                  )
                    .map((element) => accessibleLabel(element))
                    .filter((label) => label.length > 0);
                  const visibleText = normalize(rowElement.innerText || '');
                  return {
                    displayName,
                    targetTypeLabel: typeLabel,
                    stateLabel,
                    detailText,
                    visibleText,
                    selected: visibleText.includes('Active'),
                    semanticsLabel: semanticsLabels[0] ?? null,
                    iconAccessibilityLabel: iconLabel,
                    actionLabels: rowActionLabels,
                    buttonLabels,
                  };
                }),
              };
            }
            """,
            arg={"heading": self._switcher_heading},
            timeout_ms=timeout_ms,
        )
        rows = tuple(
            WorkspaceSwitcherRowObservation(
                display_name=row.get("displayName"),
                target_type_label=row.get("targetTypeLabel"),
                state_label=row.get("stateLabel"),
                detail_text=str(row.get("detailText", "")),
                visible_text=str(row.get("visibleText", "")),
                selected=bool(row.get("selected")),
                semantics_label=row.get("semanticsLabel"),
                icon_accessibility_label=row.get("iconAccessibilityLabel"),
                action_labels=tuple(str(label) for label in row.get("actionLabels", [])),
                button_labels=tuple(str(label) for label in row.get("buttonLabels", [])),
            )
            for row in payload.get("rows", [])
        )
        return WorkspaceSwitcherObservation(
            body_text=str(payload.get("bodyText", "")),
            switcher_text=str(payload.get("switcherText", "")),
            row_count=len(rows),
            rows=rows,
        )

    def close(self, *, timeout_ms: int = 15_000) -> None:
        if self._switcher_heading not in self._session.body_text():
            return
        self._session.press_key("Escape")
        self._session.wait_for_text_absence(self._switcher_heading, timeout_ms=timeout_ms)

    def screenshot(self, path: str) -> None:
        self._tracker_page.screenshot(path)

    def _click_trigger(self, *, timeout_ms: int) -> None:
        self._session.click(
            self._button_selector,
            has_text=self._trigger_label_prefix,
            timeout_ms=timeout_ms,
        )
