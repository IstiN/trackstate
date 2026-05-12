from __future__ import annotations

from dataclasses import dataclass

from testing.components.pages.live_issue_detail_collaboration_page import (
    LiveIssueDetailCollaborationPage,
    ScreenRect,
)
from testing.components.pages.trackstate_tracker_page import TrackStateTrackerPage


@dataclass(frozen=True)
class LocaleCatalogEntryObservation:
    section_title: str
    row_label: str
    entry_name: str
    entry_id: str
    translation: str
    warning_text: str | None
    warning_text_color: str | None
    warning_border_color: str | None
    warning_background_color: str | None
    warning_border_width: str | None
    input_index: int
    input_rect: ScreenRect


class LiveSettingsLocalesPage:
    _button_selector = 'flt-semantics[role="button"]'
    _tab_selector = 'flt-semantics[role="tab"]'
    _settings_admin_heading = "Project settings administration"
    _locales_tab_label = "Locales"
    _translation_label_template = "Translation ({locale})"
    _save_settings_label = "Save settings"
    _locale_code_label = "Locale code"

    def __init__(self, tracker_page: TrackStateTrackerPage) -> None:
        self._tracker_page = tracker_page
        self._session = tracker_page.session
        self._issue_page = LiveIssueDetailCollaborationPage(tracker_page)

    def ensure_connected(
        self,
        *,
        token: str,
        repository: str,
        user_login: str,
    ) -> None:
        self._issue_page.ensure_connected(
            token=token,
            repository=repository,
            user_login=user_login,
        )

    def open_settings_admin(self) -> str:
        if self._settings_admin_heading in self.current_body_text():
            return self.current_body_text()
        self._session.click(
            self._button_selector,
            has_text="Settings",
            timeout_ms=30_000,
        )
        return self._session.wait_for_text(
            self._settings_admin_heading,
            timeout_ms=60_000,
        )

    def open_locales_tab(self) -> str:
        selector = self._tab_selector_for(self._locales_tab_label)
        self._scroll_into_view(selector)
        rect = self._session.bounding_box(selector, timeout_ms=30_000)
        self._session.mouse_click(rect.x + (rect.width / 2), rect.y + (rect.height / 2))
        self._session.focus(selector, timeout_ms=30_000)
        self._session.press(selector, "Enter", timeout_ms=30_000)
        self._session.wait_for_function(
            """
            ({ tabSelector }) => {
              const tab = document.querySelector(tabSelector);
              const labels = Array.from(
                document.querySelectorAll('flt-semantics[aria-label]'),
              ).map((candidate) => (candidate.getAttribute('aria-label') ?? '').trim());
              const hasLocaleContent =
                labels.includes('Add locale')
                || labels.some((label) => label.startsWith('Statuses Locales'));
              return (
                !!tab &&
                tab.getAttribute('aria-selected') === 'true' &&
                hasLocaleContent
              );
            }
            """,
            arg={"tabSelector": selector},
            timeout_ms=30_000,
        )
        return self.current_body_text()

    def locale_exists(self, locale: str) -> bool:
        return locale in self.locale_codes()

    def locale_codes(self) -> list[str]:
        payload = self._session.evaluate(
            """
            () => {
              const localeChipPattern = /^[a-z]{2,3}(?:-[A-Za-z0-9]+)*(?: \\(default\\))?$/i;
              const localeCodes = Array.from(
                document.querySelectorAll('flt-semantics[role="radio"], flt-semantics[role="button"]'),
              )
                .flatMap((candidate) => {
                  const text = (candidate.innerText ?? '').trim();
                  const label = (candidate.getAttribute('aria-label') ?? '').trim();
                  return [text, label];
                })
                .filter((value) => localeChipPattern.test(value))
                .map((value) => value.replace(/ \\(default\\)$/i, ''));
              return Array.from(new Set(localeCodes));
            }
            """,
        )
        if not isinstance(payload, list):
            raise AssertionError(
                "Settings > Locales did not expose readable locale chips.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        return [str(code) for code in payload]

    def select_locale(self, locale: str) -> None:
        clicked = self._session.evaluate(
            """
            (targetLocale) => {
              const expectedTexts = [targetLocale, `${targetLocale} (default)`];
              const candidate = Array.from(
                document.querySelectorAll('flt-semantics[role="radio"], flt-semantics[role="button"]'),
              ).find((element) => {
                const text = (element.innerText ?? '').trim();
                const label = (element.getAttribute('aria-label') ?? '').trim();
                return expectedTexts.includes(text) || expectedTexts.includes(label);
              });
              if (!candidate) {
                return false;
              }
              candidate.scrollIntoView({ block: 'center' });
              candidate.click();
              return true;
            }
            """,
            arg=locale,
        )
        if clicked is not True:
            raise AssertionError(
                f'Could not find the "{locale}" locale chip in Settings > Locales.\n'
                f"Observed body text:\n{self.current_body_text()}",
            )
        self._session.wait_for_count(
            self._translation_input_selector(locale),
            expected_count=self.translation_input_count(locale),
            timeout_ms=30_000,
        )

    def add_locale(self, locale: str) -> str:
        locale_codes_before = self.locale_codes()
        self._session.click(
            'flt-semantics[role="button"][aria-label="Add locale"]',
            timeout_ms=30_000,
        )
        self._session.wait_for_selector(
            f'input[aria-label="{self._locale_code_label}"]',
            timeout_ms=30_000,
        )
        self._session.fill(
            f'input[aria-label="{self._locale_code_label}"]',
            locale,
            timeout_ms=30_000,
        )
        self._session.click(self._button_selector, has_text="Save", timeout_ms=30_000)
        self._session.wait_for_function(
            """
            ({ expectedLocale, localeCodesBefore }) => {
              const localeChipPattern = /^[a-z]{2,3}(?:-[A-Za-z0-9]+)*(?: \\(default\\))?$/i;
              const localeCodes = Array.from(
                document.querySelectorAll('flt-semantics[role="radio"], flt-semantics[role="button"]'),
              )
                .flatMap((candidate) => {
                  const text = (candidate.innerText ?? '').trim();
                  const label = (candidate.getAttribute('aria-label') ?? '').trim();
                  return [text, label];
                })
                .filter((value) => localeChipPattern.test(value))
                .map((value) => value.replace(/ \\(default\\)$/i, ''));
              const distinctLocaleCodes = Array.from(new Set(localeCodes));
              const addedLocale = distinctLocaleCodes.find(
                (code) => !localeCodesBefore.includes(code),
              );
              return (
                distinctLocaleCodes.includes(expectedLocale)
                || (
                  typeof addedLocale === 'string'
                  && document.querySelectorAll(
                    `input[aria-label="Translation (${addedLocale})"]`,
                  ).length > 0
                )
              );
            }
            """,
            arg={"expectedLocale": locale, "localeCodesBefore": locale_codes_before},
            timeout_ms=30_000,
        )
        locale_codes_after = self.locale_codes()
        if locale in locale_codes_after:
            return locale
        added_locales = [
            candidate for candidate in locale_codes_after if candidate not in locale_codes_before
        ]
        if added_locales:
            return added_locales[0]
        raise AssertionError(
            f'Could not determine which locale was added after requesting "{locale}".\n'
            f"Observed locale chips: {locale_codes_after}\n"
            f"Observed body text:\n{self.current_body_text()}",
        )

    def remove_locale(self, locale: str) -> None:
        self.select_locale(locale)
        selector = (
            f'flt-semantics[role="button"][aria-label="{self._escape(self.remove_locale_label(locale))}"]'
        )
        self._scroll_into_view(selector)
        self._session.click(selector, timeout_ms=30_000)
        self._session.wait_for_function(
            """
            (expectedLocale) => {
              const expectedTexts = [expectedLocale, `${expectedLocale} (default)`];
              return !Array.from(
                document.querySelectorAll('flt-semantics[role="radio"], flt-semantics[role="button"]'),
              ).some((candidate) => {
                const text = (candidate.innerText ?? '').trim();
                const label = (candidate.getAttribute('aria-label') ?? '').trim();
                return expectedTexts.includes(text) || expectedTexts.includes(label);
              });
            }
            """,
            arg=locale,
            timeout_ms=30_000,
        )

    def catalog_titles(self) -> list[str]:
        payload = self._session.evaluate(
            """
            () => {
              const suffix = ' Locales';
              const titles = Array.from(
                document.querySelectorAll('[aria-label]'),
              )
                .map((element) => (element.getAttribute('aria-label') ?? '').trim())
                .map((label) => label.split('\\n')[0].trim())
                .filter((label) => label.endsWith(suffix))
                .map((label) => label.slice(0, label.length - suffix.length));
              return Array.from(new Set(titles));
            }
            """,
        )
        if not isinstance(payload, list):
            raise AssertionError(
                "Settings > Locales did not expose readable catalog section headings.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        return [str(title) for title in payload]

    def entry_observation(
        self,
        *,
        section_title: str,
        locale: str,
        entry_id: str,
    ) -> LocaleCatalogEntryObservation:
        for entry in self.entry_observations(section_title=section_title, locale=locale):
            if entry.entry_id == entry_id:
                return entry
        raise AssertionError(
            f'Could not locate the "{entry_id}" row in the "{section_title}" locale catalog.\n'
            f"Observed body text:\n{self.current_body_text()}",
        )

    def entry_observations(
        self,
        *,
        section_title: str,
        locale: str,
    ) -> list[LocaleCatalogEntryObservation]:
        payload = self._session.evaluate(
            """
            ({ sectionTitle, locale }) => {
              const sectionLabel = `${sectionTitle} Locales`;
              const translationLabel = `Translation (${locale})`;
              const section = Array.from(
                document.querySelectorAll('[aria-label]'),
              ).find(
                (candidate) =>
                  ((candidate.getAttribute('aria-label') ?? '').trim().split('\\n')[0] ?? '').trim()
                  === sectionLabel,
              );
              if (!section) {
                return null;
              }
              section.scrollIntoView({ block: 'center' });
              const sectionLines = (section.getAttribute('aria-label') ?? '')
                .split('\\n')
                .map((value) => value.trim())
                .filter((value) => value.length > 0);
              const sectionRows = [];
              for (let index = 2; index < sectionLines.length; index += 1) {
                const line = sectionLines[index];
                if (!line.includes(' · ')) {
                  continue;
                }
                const warnings = [];
                let cursor = index + 1;
                while (cursor < sectionLines.length && !sectionLines[cursor].includes(' · ')) {
                  const warning = sectionLines[cursor];
                  if (
                    warning.startsWith('Missing translation.')
                    && !warnings.includes(warning)
                  ) {
                    warnings.push(warning);
                  }
                  cursor += 1;
                }
                sectionRows.push({
                  rowLabel: line,
                  warningText: warnings[0] ?? null,
                });
              }

              const inputEntries = Array.from(
                section.querySelectorAll(`input[aria-label="${translationLabel}"]`),
              )
                .map((input) => ({
                  element: input,
                  globalIndex: Array.from(
                    document.querySelectorAll(`input[aria-label="${translationLabel}"]`),
                  ).indexOf(input),
                  value: input.value ?? '',
                  rect: input.getBoundingClientRect(),
                }))
                .filter((entry) => entry.rect.width > 0 && entry.rect.height > 0)
                .sort((left, right) => {
                  const topDelta = left.rect.top - right.rect.top;
                  if (Math.abs(topDelta) > 1) {
                    return topDelta;
                  }
                  return left.rect.left - right.rect.left;
                });

              const visibleTextNodes = Array.from(document.querySelectorAll('body *'))
                .map((element) => ({
                  element,
                  text: (element.innerText ?? '').trim(),
                  rect: element.getBoundingClientRect(),
                }))
                .filter(
                  (entry) =>
                    entry.text.length > 0 &&
                    entry.rect.width > 0 &&
                    entry.rect.height > 0 &&
                    entry.rect.top >= window.scrollY &&
                    entry.rect.bottom <= window.scrollY + window.innerHeight,
                );

              const dedupedNodes = [];
              const seen = new Set();
              for (const entry of visibleTextNodes) {
                const key = [
                  entry.text,
                  Math.round(entry.rect.left),
                  Math.round(entry.rect.top),
                ].join('|');
                if (seen.has(key)) {
                  continue;
                }
                seen.add(key);
                dedupedNodes.push(entry);
              }

              return inputEntries.map((entry, index) => {
                entry.element.scrollIntoView({ block: 'center' });
                const inputRect = entry.element.getBoundingClientRect();
                const sectionRow = sectionRows[index] ?? { rowLabel: '', warningText: null };
                const warningNode = dedupedNodes
                  .filter(
                    (candidate) =>
                      candidate.text.startsWith('Missing translation.') &&
                      candidate.rect.top >= inputRect.bottom - 4 &&
                      candidate.rect.top <= inputRect.bottom + 96,
                  )
                  .sort((left, right) => left.rect.top - right.rect.top)[0] ?? null;

                let warningTextColor = null;
                let warningBorderColor = null;
                let warningBackgroundColor = null;
                let warningBorderWidth = null;
                if (warningNode?.element) {
                  warningTextColor = window.getComputedStyle(warningNode.element).color;
                  let warningContainer = warningNode.element;
                  while (warningContainer && warningContainer !== document.body) {
                    const style = window.getComputedStyle(warningContainer);
                    const borderWidth = Number.parseFloat(style.borderTopWidth || '0');
                    const hasVisibleBorder =
                      borderWidth > 0 &&
                      style.borderTopColor !== 'transparent' &&
                      style.borderTopColor !== 'rgba(0, 0, 0, 0)';
                    const hasVisibleBackground =
                      style.backgroundColor !== 'transparent' &&
                      style.backgroundColor !== 'rgba(0, 0, 0, 0)';
                    if (hasVisibleBorder || hasVisibleBackground) {
                      warningBorderColor = style.borderTopColor;
                      warningBackgroundColor = style.backgroundColor;
                      warningBorderWidth = style.borderTopWidth;
                      break;
                    }
                    warningContainer = warningContainer.parentElement;
                  }
                }

                const rowLabel = dedupedNodes
                  .filter(
                    (candidate) =>
                      candidate.text.includes(' · ') &&
                      candidate.rect.bottom <= inputRect.top + 18 &&
                      candidate.rect.top >= inputRect.top - 120,
                  )
                  .sort(
                    (left, right) =>
                      Math.abs(left.rect.top - inputRect.top) -
                      Math.abs(right.rect.top - inputRect.top),
                  )[0]?.text ?? sectionRow.rowLabel;

                return {
                  inputIndex: entry.globalIndex,
                  inputRect: {
                    left: inputRect.left,
                    top: inputRect.top,
                    width: inputRect.width,
                    height: inputRect.height,
                  },
                  rowLabel,
                  warningBackgroundColor,
                  warningBorderColor,
                  warningBorderWidth,
                  warningText: warningNode?.text ?? sectionRow.warningText,
                  warningTextColor,
                  translation: entry.value,
                };
              });
            }
            """,
            arg={"sectionTitle": section_title, "locale": locale},
        )
        if not isinstance(payload, list):
            raise AssertionError(
                f'The "{section_title}" locale catalog did not render a readable section surface.\n'
                f"Observed body text:\n{self.current_body_text()}",
            )

        observations: list[LocaleCatalogEntryObservation] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            row_label = str(item.get("rowLabel", "")).strip()
            name, entry_id = _parse_row_label(row_label)
            observations.append(
                LocaleCatalogEntryObservation(
                    section_title=section_title,
                    row_label=row_label,
                    entry_name=name,
                    entry_id=entry_id,
                    translation=str(item.get("translation", "")),
                    warning_text=(
                        str(item["warningText"])
                        if item.get("warningText") is not None
                        else None
                    ),
                    warning_text_color=(
                        str(item["warningTextColor"])
                        if item.get("warningTextColor") is not None
                        else None
                    ),
                    warning_border_color=(
                        str(item["warningBorderColor"])
                        if item.get("warningBorderColor") is not None
                        else None
                    ),
                    warning_background_color=(
                        str(item["warningBackgroundColor"])
                        if item.get("warningBackgroundColor") is not None
                        else None
                    ),
                    warning_border_width=(
                        str(item["warningBorderWidth"])
                        if item.get("warningBorderWidth") is not None
                        else None
                    ),
                    input_index=int(item.get("inputIndex", 0)),
                    input_rect=ScreenRect(
                        left=float(item.get("inputRect", {}).get("left", 0)),
                        top=float(item.get("inputRect", {}).get("top", 0)),
                        width=float(item.get("inputRect", {}).get("width", 0)),
                        height=float(item.get("inputRect", {}).get("height", 0)),
                    ),
                ),
            )
        return observations

    def fill_translation(
        self,
        *,
        section_title: str,
        locale: str,
        entry_id: str,
        value: str,
    ) -> LocaleCatalogEntryObservation:
        entry = self.entry_observation(
            section_title=section_title,
            locale=locale,
            entry_id=entry_id,
        )
        selector = self._translation_input_selector(locale)
        self._session.focus(selector, index=entry.input_index, timeout_ms=30_000)
        self._session.fill(selector, value, index=entry.input_index, timeout_ms=30_000)
        self._session.wait_for_input_value(
            selector,
            value,
            index=entry.input_index,
            timeout_ms=30_000,
        )
        self._session.press(selector, "Tab", index=entry.input_index, timeout_ms=30_000)
        return self.entry_observation(
            section_title=section_title,
            locale=locale,
            entry_id=entry_id,
        )

    def translation_input_count(self, locale: str) -> int:
        return self._session.count(self._translation_input_selector(locale))

    def save_settings(self) -> None:
        self._session.click(
            f'flt-semantics[role="button"][aria-label="{self._save_settings_label}"]',
            timeout_ms=30_000,
        )

    def remove_locale_label(self, locale: str) -> str:
        return f"Remove locale {locale}"

    def current_body_text(self) -> str:
        return self._tracker_page.body_text()

    def screenshot(self, path: str) -> None:
        self._tracker_page.screenshot(path)

    def _translation_input_selector(self, locale: str) -> str:
        return (
            f'input[aria-label="{self._escape(self._translation_label_template.format(locale=locale))}"]'
        )

    def _tab_selector_for(self, label: str) -> str:
        return f'{self._tab_selector}[aria-label="{self._escape(label)}"]'

    def _scroll_into_view(self, selector: str) -> None:
        self._session.evaluate(
            """
            (value) => {
              document.querySelector(value)?.scrollIntoView({ block: 'center' });
            }
            """,
            arg=selector,
        )

    @staticmethod
    def _escape(value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"')


def _parse_row_label(row_label: str) -> tuple[str, str]:
    if " · " not in row_label:
        return row_label, row_label
    name, entry_id = row_label.split(" · ", 1)
    return name.strip(), entry_id.strip()
