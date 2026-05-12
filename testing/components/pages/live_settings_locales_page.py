from __future__ import annotations

from dataclasses import dataclass

from testing.components.pages.live_issue_detail_collaboration_page import (
    LiveIssueDetailCollaborationPage,
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
    input_index: int


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
        return bool(
            self._session.evaluate(
                """
                (targetLocale) => {
                  const expectedTexts = [targetLocale, `${targetLocale} (default)`];
                  return Array.from(
                    document.querySelectorAll('flt-semantics[role="radio"], flt-semantics[role="button"]'),
                  ).some((candidate) => {
                    const text = (candidate.innerText ?? '').trim();
                    const label = (candidate.getAttribute('aria-label') ?? '').trim();
                    return expectedTexts.includes(text) || expectedTexts.includes(label);
                  });
                }
                """,
                arg=locale,
            ),
        )

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

    def add_locale(self, locale: str) -> None:
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
            (expectedLocale) => {
              const expectedTexts = [expectedLocale, `${expectedLocale} (default)`];
              const localeChipPresent = Array.from(
                document.querySelectorAll('flt-semantics[role="radio"], flt-semantics[role="button"]'),
              ).some((candidate) => {
                const text = (candidate.innerText ?? '').trim();
                const label = (candidate.getAttribute('aria-label') ?? '').trim();
                return expectedTexts.includes(text) || expectedTexts.includes(label);
              });
              const translationInputs = document.querySelectorAll(
                `input[aria-label="Translation (${expectedLocale})"]`,
              ).length;
              return localeChipPresent && translationInputs > 0;
            }
            """,
            arg=locale,
            timeout_ms=30_000,
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
              const titles = Array.from(
                document.querySelectorAll('flt-semantics[aria-label]'),
              )
                .map((element) => (element.getAttribute('aria-label') ?? '').trim())
                .filter((label) => label.includes(' Locales'))
                .map((label) => label.split('\\n')[0].trim())
                .map((label) => label.slice(0, label.indexOf(' Locales')));
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
                document.querySelectorAll('flt-semantics[aria-label]'),
              ).find(
                (candidate) => (candidate.getAttribute('aria-label') ?? '').trim() === sectionLabel,
              );
              if (!section) {
                return null;
              }
              const sectionRect = section.getBoundingClientRect();
              const allInputs = Array.from(
                document.querySelectorAll(`input[aria-label="${translationLabel}"]`),
              );
              const inputEntries = allInputs
                .map((input, globalIndex) => ({
                  globalIndex,
                  value: input.value ?? '',
                  rect: input.getBoundingClientRect(),
                }))
                .filter(
                  (entry) =>
                    entry.rect.height > 0 &&
                    entry.rect.top >= sectionRect.top - 12 &&
                    entry.rect.bottom <= sectionRect.bottom + 24,
                );

              const visibleTextNodes = Array.from(document.querySelectorAll('body *'))
                .map((element) => ({
                  text: (element.innerText ?? '').trim(),
                  rect: element.getBoundingClientRect(),
                }))
                .filter(
                  (entry) =>
                    entry.text.length > 0 &&
                    entry.rect.width > 0 &&
                    entry.rect.height > 0 &&
                    entry.rect.top >= sectionRect.top - 12 &&
                    entry.rect.bottom <= sectionRect.bottom + 120,
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

              return inputEntries.map((entry) => {
                const rowLabel = dedupedNodes
                  .filter(
                    (candidate) =>
                      candidate.text.includes(' · ') &&
                      candidate.rect.bottom <= entry.rect.top + 18 &&
                      candidate.rect.top >= entry.rect.top - 120,
                  )
                  .sort(
                    (left, right) =>
                      Math.abs(left.rect.top - entry.rect.top) -
                      Math.abs(right.rect.top - entry.rect.top),
                  )[0]?.text ?? '';

                const warningText = dedupedNodes
                  .filter(
                    (candidate) =>
                      candidate.text.startsWith('Missing translation.') &&
                      candidate.rect.top >= entry.rect.bottom - 4 &&
                      candidate.rect.top <= entry.rect.bottom + 96,
                  )
                  .sort((left, right) => left.rect.top - right.rect.top)[0]?.text ?? null;

                return {
                  inputIndex: entry.globalIndex,
                  rowLabel,
                  translation: entry.value,
                  warningText,
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
                    input_index=int(item.get("inputIndex", 0)),
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
