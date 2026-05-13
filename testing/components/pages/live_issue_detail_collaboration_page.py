from __future__ import annotations

from dataclasses import dataclass

from testing.components.pages.live_jql_search_page import LiveJqlSearchPage
from testing.components.pages.trackstate_tracker_page import TrackStateTrackerPage
from testing.core.interfaces.web_app_session import (
    FocusedElementObservation,
    NewPageObservation,
    WebAppTimeoutError,
)


@dataclass(frozen=True)
class ScreenRect:
    left: float
    top: float
    width: float
    height: float


@dataclass(frozen=True)
class TabChipObservation:
    label: str
    is_selected: bool
    left: float
    top: float
    width: float
    height: float


@dataclass(frozen=True)
class CommentCardObservation:
    body_fragment: str
    visible_text: str
    accessible_label: str


@dataclass(frozen=True)
class AttachmentSelectionSummaryObservation:
    summary_text: str
    file_name_visible: bool
    size_label: str
    upload_enabled: bool
    summary_top: float
    first_attachment_top: float | None


@dataclass(frozen=True)
class AttachmentUploadControlsObservation:
    choose_button_count: int
    choose_button_enabled: bool
    upload_button_count: int
    upload_button_enabled: bool


@dataclass(frozen=True)
class CommentComposerObservation:
    field_label: str
    field_enabled: bool
    button_label: str
    button_enabled: bool


class LiveIssueDetailCollaborationPage:
    _button_selector = 'flt-semantics[role="button"]'
    _tab_button_selector = 'flt-semantics[role="button"][aria-current]'
    _active_tab_button_selector = 'flt-semantics[role="button"][aria-current="true"]'
    _connect_button_selector = 'flt-semantics[aria-label="Connect GitHub"]'
    _connected_button_selector = 'flt-semantics[aria-label="Connected"]'
    _token_input_selector = 'input[aria-label="Fine-grained token"]'
    _choose_attachment_button_selector = (
        'flt-semantics[aria-label="Choose attachment"] flt-semantics[flt-tappable]'
    )
    _upload_attachment_button_selector = (
        'flt-semantics[aria-label="Upload attachment"] flt-semantics[flt-tappable]'
    )
    _replace_attachment_button_selector = (
        'flt-semantics[role="button"][flt-tappable]:text-is("Replace attachment")'
    )
    _keep_attachment_button_selector = (
        'flt-semantics[role="button"][flt-tappable]:text-is("Keep current attachment")'
    )
    _selected_button_selector = _active_tab_button_selector

    def __init__(self, tracker_page: TrackStateTrackerPage) -> None:
        self._tracker_page = tracker_page
        self._session = tracker_page.session

    def ensure_connected(
        self,
        *,
        token: str,
        repository: str,
        user_login: str,
    ) -> None:
        connected_banner = TrackStateTrackerPage.CONNECTED_BANNER_TEMPLATE.format(
            user_login=user_login,
            repository=repository,
        )
        if self._is_connected(connected_banner):
            return
        if self._session.count(self._connect_button_selector) == 0:
            raise AssertionError(
                "Step 1 failed: the hosted session did not expose either the connected "
                "state or the Connect GitHub action needed to prove the authentication "
                "precondition for TS-311.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )

        self._session.click(self._connect_button_selector, timeout_ms=30_000)
        self._session.wait_for_selector(self._token_input_selector, timeout_ms=30_000)
        self._session.fill(self._token_input_selector, token, timeout_ms=30_000)
        self._session.press(self._token_input_selector, "Tab", timeout_ms=30_000)
        self._session.click(
            self._button_selector,
            has_text="Connect token",
            timeout_ms=30_000,
        )
        connected_markers = [
            connected_banner,
            "GitHub connection failed:",
            "Manage GitHub access",
            user_login,
        ]
        wait_match = self._session.wait_for_any_text(
            connected_markers,
            timeout_ms=120_000,
        )
        if wait_match.matched_text == "GitHub connection failed:":
            raise AssertionError(
                "Step 1 failed: the hosted GitHub connection flow did not reach the "
                "connected state required for TS-311.\n"
                f"Observed body text:\n{wait_match.body_text}",
            )

    def open_jql_search(self) -> None:
        self._session.click(self._button_selector, has_text="JQL Search", timeout_ms=30_000)
        self._session.wait_for_selector(
            'flt-semantics[role="button"][aria-label*="Open DEMO-"]',
            timeout_ms=60_000,
        )

    def open_issue(self, *, issue_key: str, issue_summary: str) -> None:
        self.open_jql_search()
        self._session.click(
            self._open_issue_selector(issue_key=issue_key, issue_summary=issue_summary),
            timeout_ms=30_000,
        )
        self._session.wait_for_selector(
            self._issue_detail_selector(issue_key),
            timeout_ms=60_000,
        )

    def select_issue_from_visible_list(
        self,
        *,
        issue_key: str,
        issue_summary: str,
    ) -> None:
        self._session.wait_for_selector(
            self._open_issue_selector(issue_key=issue_key, issue_summary=issue_summary),
            timeout_ms=30_000,
        )
        self._session.click(
            self._open_issue_selector(issue_key=issue_key, issue_summary=issue_summary),
            timeout_ms=30_000,
        )
        self._session.wait_for_selector(
            self._issue_detail_selector(issue_key),
            timeout_ms=60_000,
        )

    def dismiss_connection_banner(self) -> None:
        if self._session.count(self._button_selector, has_text="Close") == 0:
            return
        self._session.click(self._button_selector, has_text="Close", timeout_ms=30_000)

    def search_and_select_issue(
        self,
        *,
        issue_key: str,
        issue_summary: str,
        query: str | None = None,
    ) -> None:
        search_query = query or issue_key
        search_page = LiveJqlSearchPage(self._tracker_page)
        search_page.open()
        field_selector, field_index = search_page._wait_for_search_field()
        self._session.fill(
            field_selector,
            search_query,
            index=field_index,
            timeout_ms=30_000,
        )
        self._session.press(
            field_selector,
            "Enter",
            index=field_index,
            timeout_ms=30_000,
        )
        self._session.wait_for_selector(
            self._open_issue_selector(issue_key=issue_key, issue_summary=issue_summary),
            timeout_ms=60_000,
        )
        issue_row = self._session.bounding_box(
            self._open_issue_selector(issue_key=issue_key, issue_summary=issue_summary),
            timeout_ms=30_000,
        )
        self._session.mouse_click(
            issue_row.x + (issue_row.width / 2),
            issue_row.y + (issue_row.height / 2),
        )
        self._session.wait_for_selector(
            self._issue_detail_selector(issue_key),
            timeout_ms=60_000,
        )

    def issue_detail_count(self, issue_key: str) -> int:
        return self._session.count(self._issue_detail_selector(issue_key))

    def issue_result_button_count(self, *, issue_key: str, issue_summary: str) -> int:
        return self._session.count(
            self._open_issue_selector(issue_key=issue_key, issue_summary=issue_summary),
        )

    def visible_issue_result_labels(self) -> tuple[str, ...]:
        payload = self._session.evaluate(
            """
            () => Array.from(
              document.querySelectorAll('flt-semantics[role="button"][aria-label^="Open "]')
            )
              .map((element) => element.getAttribute('aria-label') ?? '')
              .filter((label) => label.length > 0)
            """,
        )
        if not isinstance(payload, list):
            return ()
        return tuple(str(label) for label in payload)

    def tab_button_count(self, label: str) -> int:
        return self._session.count(self._tab_button_selector, has_text=label)

    def active_tab_count(self, label: str) -> int:
        return self._session.count(self._active_tab_button_selector, has_text=label)

    def selected_tab_count(self, label: str) -> int:
        return self._session.count(self._selected_button_selector, has_text=label)

    def open_collaboration_tab(self, label: str) -> None:
        self._session.wait_for_selector(
            self._tab_button_selector,
            has_text=label,
            timeout_ms=30_000,
        )
        self._session.click(
            self._tab_button_selector,
            has_text=label,
            timeout_ms=30_000,
        )
        self._session.wait_for_selector(
            self._active_tab_button_selector,
            has_text=label,
            timeout_ms=30_000,
        )

    def wait_for_selected_tab(self, label: str, *, timeout_ms: int = 30_000) -> None:
        self._session.wait_for_selector(
            self._selected_button_selector,
            has_text=label,
            timeout_ms=timeout_ms,
        )

    def wait_for_text(self, text: str, *, timeout_ms: int = 60_000) -> str:
        return self._session.wait_for_text(text, timeout_ms=timeout_ms)

    def wait_for_text_absent(self, text: str, *, timeout_ms: int = 60_000) -> str:
        return self._session.wait_for_text_absent(text, timeout_ms=timeout_ms)

    def click_button(self, label: str, *, timeout_ms: int = 30_000) -> None:
        self._session.click(
            self._button_selector,
            has_text=label,
            timeout_ms=timeout_ms,
        )

    def click_button_via_semantics_center(
        self,
        label: str,
        *,
        timeout_ms: int = 30_000,
    ) -> None:
        self.wait_for_text(label, timeout_ms=timeout_ms)
        rect = self.find_semantics_rect_containing_text(label)
        self._session.mouse_click(
            rect.left + (rect.width / 2),
            rect.top + (rect.height / 2),
        )
    def wait_for_text_fragment(
        self,
        fragment: str,
        *,
        timeout_ms: int = 30_000,
    ) -> int:
        self.wait_for_text(fragment, timeout_ms=timeout_ms)
        return self.text_fragment_count(fragment)

    def wait_for_text_fragment_to_disappear(
        self,
        fragment: str,
        *,
        timeout_ms: int = 30_000,
    ) -> int:
        self._session.wait_for_text_absence(fragment, timeout_ms=timeout_ms)
        return self.text_fragment_count(fragment)

    def text_fragment_count(self, fragment: str) -> int:
        labeled_fragment_count = self._session.count(
            f'flt-semantics[aria-label*="{self._escape(fragment)}"]',
        )
        if labeled_fragment_count > 0:
            return labeled_fragment_count
        return 1 if fragment in self.current_body_text() else 0

    def button_label_fragment_count(self, fragment: str) -> int:
        labeled_button_count = self._session.count(
            f'flt-semantics[role="button"][aria-label*="{self._escape(fragment)}"]',
        )
        if labeled_button_count > 0:
            return labeled_button_count
        return self._session.count(self._button_selector, has_text=fragment)

    def theme_toggle_label(self) -> str:
        for label in ("Dark theme", "Light theme"):
            if self.button_label_fragment_count(label) > 0:
                return label
        raise AssertionError(
            "Step 3 failed: the live tracker did not expose the theme toggle needed "
            "to validate collaboration metadata contrast across themes.\n"
            f"Observed body text:\n{self.current_body_text()}",
        )

    def toggle_theme(self, *, timeout_ms: int = 30_000) -> str:
        current_label = self.theme_toggle_label()
        next_label = "Light theme" if current_label == "Dark theme" else "Dark theme"
        self._session.click(
            self._button_selector,
            has_text=current_label,
            timeout_ms=timeout_ms,
        )
        self._session.wait_for_selector(
            self._button_selector,
            has_text=next_label,
            timeout_ms=timeout_ms,
        )
        return next_label

    def find_semantics_rect_containing_text(
        self,
        text: str,
        *,
        max_width: float = 1_000,
        max_height: float = 400,
    ) -> ScreenRect:
        payload = self._session.evaluate(
            """
            ({ text, maxWidth, maxHeight }) => {
              const matches = Array.from(document.querySelectorAll("flt-semantics"))
                .map((element) => {
                  const label = element.getAttribute("aria-label") ?? "";
                  const innerText = element.innerText ?? "";
                  const rect = element.getBoundingClientRect();
                  return {
                    label,
                    innerText,
                    width: rect.width,
                    height: rect.height,
                    left: rect.left,
                    top: rect.top,
                    area: rect.width * rect.height,
                  };
                })
                .filter((candidate) =>
                  (candidate.label.includes(text) || candidate.innerText.includes(text)) &&
                  candidate.width > 0 &&
                  candidate.height > 0 &&
                  candidate.width < maxWidth &&
                  candidate.height < maxHeight,
                )
                .sort((left, right) => left.area - right.area);
              if (matches.length === 0) {
                return null;
              }
              const match = matches[0];
              return {
                left: match.left,
                top: match.top,
                width: match.width,
                height: match.height,
              };
            }
            """,
            arg={
                "text": text,
                "maxWidth": max_width,
                "maxHeight": max_height,
            },
        )
        if not isinstance(payload, dict):
            raise AssertionError(
                "Step 2 failed: the live issue detail did not expose a visible "
                f"semantics region containing {text!r}.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        return ScreenRect(
            left=float(payload["left"]),
            top=float(payload["top"]),
            width=float(payload["width"]),
            height=float(payload["height"]),
        )

    def current_body_text(self) -> str:
        return self._tracker_page.body_text()

    def wait_for_collaboration_section_to_settle(
        self,
        section_label: str,
        *,
        timeout_ms: int = 120_000,
    ) -> str:
        payload = self._session.wait_for_function(
            """
            ({ sectionLabel }) => {
              const bodyText = document.body?.innerText ?? '';
              const loadingFragments = [
                `${sectionLabel} loading`,
                `${sectionLabel} Loading...`,
              ];
              return loadingFragments.some((fragment) => bodyText.includes(fragment))
                ? null
                : bodyText;
            }
            """,
            arg={"sectionLabel": section_label},
            timeout_ms=timeout_ms,
        )
        body_text = str(payload).strip()
        if not body_text:
            raise AssertionError(
                "Step 2 failed: the live issue detail did not expose a readable "
                f"body snapshot after {section_label!r} finished loading.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        return body_text

    def visible_timestamped_rows(self) -> tuple[str, ...]:
        payload = self._session.evaluate(
            """
            () => {
              const timestampPattern =
                /\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(?:\\.\\d+)?Z/;
              const seen = new Set();
              return Array.from(document.querySelectorAll('flt-semantics, flt-semantics-img'))
                .map((element) => (element.innerText || element.getAttribute('aria-label') || '').trim())
                .filter((text) =>
                  text.length > 0 &&
                  !text.includes('\\n') &&
                  timestampPattern.test(text),
                )
                .filter((text) => {
                  if (seen.has(text)) {
                    return false;
                  }
                  seen.add(text);
                  return true;
                });
            }
            """,
        )
        if not isinstance(payload, list):
            raise AssertionError(
                "The live issue detail did not expose a readable collaboration row list.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        return tuple(str(item).strip() for item in payload if str(item).strip())

    def screenshot(self, path: str) -> None:
        self._tracker_page.screenshot(path)

    def wait_for_comment_card(
        self,
        body_fragment: str,
        *,
        required_fragments: tuple[str, ...] = (),
        timeout_ms: int = 60_000,
    ) -> CommentCardObservation:
        expected_fragments = tuple(
            fragment.strip()
            for fragment in (body_fragment, *required_fragments)
            if fragment.strip()
        )
        self.wait_for_text(body_fragment, timeout_ms=timeout_ms)
        payload = self._session.wait_for_function(
            """
            ({ bodyFragment, expectedFragments }) => {
              const normalize = (value) => (value || '').replace(/\\s+/g, ' ').trim();
              const descriptionCache = new WeakMap();
              const describe = (element) => {
                const cached = descriptionCache.get(element);
                if (cached) {
                  return cached;
                }

                const rect = element.getBoundingClientRect();
                const label = normalize(element.getAttribute('aria-label') ?? '');
                const text = normalize(element.innerText || element.textContent || '');
                const described = {
                  label,
                  text,
                  combined: [text, label].filter((value) => value.length > 0).join("\\n"),
                  width: rect.width,
                  height: rect.height,
                  area: rect.width * rect.height,
                };
                descriptionCache.set(element, described);
                return described;
              };
              const isVisible = (element) => {
                const rect = element.getBoundingClientRect();
                return rect.width > 0 && rect.height > 0;
              };

              const visibleSemantics = Array.from(document.querySelectorAll('flt-semantics'))
                .filter((element) => isVisible(element));
              const subtreeContainsFragment = (container, fragment) =>
                visibleSemantics.some((element) =>
                  container.contains(element) && describe(element).combined.includes(fragment)
                );

              const matches = [];
              const seen = new Set();
              for (const element of visibleSemantics) {
                if (!describe(element).combined.includes(bodyFragment)) {
                  continue;
                }

                let current = element;
                while (current) {
                  if (current.matches?.('flt-semantics') && isVisible(current) && !seen.has(current)) {
                    if (
                      expectedFragments.every((fragment) =>
                        subtreeContainsFragment(current, fragment)
                      )
                    ) {
                      seen.add(current);
                      matches.push(describe(current));
                    }
                  }
                  current = current.parentElement;
                }
              }

              matches.sort((left, right) => left.area - right.area || left.text.length - right.text.length);
              return matches[0] ?? null;
            }
            """,
            arg={
                "bodyFragment": body_fragment,
                "expectedFragments": list(expected_fragments),
            },
            timeout_ms=timeout_ms,
        )
        if not isinstance(payload, dict):
            raise AssertionError(
                "Step 3 failed: the live Comments tab did not expose a visible comment "
                f"row for {body_fragment!r}.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        visible_text = str(payload.get("text", "")).strip()
        accessible_label = str(payload.get("label", "")).strip()
        if not visible_text:
            raise AssertionError(
                "Step 3 failed: the live Comments tab rendered an empty comment row for "
                f"{body_fragment!r}.\n"
                f"Observed payload: {payload}\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        missing_fragments = [
            fragment for fragment in expected_fragments if fragment not in visible_text
        ]
        if missing_fragments:
            raise AssertionError(
                "Step 3 failed: the live Comments tab did not keep the expected comment "
                f"metadata in the same visible row for {body_fragment!r}.\n"
                f"Missing visible fragments: {missing_fragments}\n"
                f"Observed row text: {visible_text}\n"
                f"Observed accessibility label: {accessible_label}\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        return CommentCardObservation(
            body_fragment=body_fragment,
            visible_text=visible_text,
            accessible_label=accessible_label,
        )

    def issue_detail_accessible_label(
        self,
        issue_key: str,
        *,
        expected_fragment: str | None = None,
        timeout_ms: int = 30_000,
    ) -> str:
        selector = self._issue_detail_selector(issue_key)
        self._session.wait_for_selector(selector, timeout_ms=timeout_ms)
        if expected_fragment is not None:
            self._session.wait_for_function(
                """
                ({ selector, expectedFragment }) => {
                  return Array.from(document.querySelectorAll(selector))
                    .map((element) => element.getAttribute('aria-label') ?? '')
                    .some((label) => label.includes(expectedFragment));
                }
                """,
                arg={
                    "selector": selector,
                    "expectedFragment": expected_fragment,
                },
                timeout_ms=timeout_ms,
            )
        payload = self._session.evaluate(
            """
            ({ selector }) => {
              return Array.from(document.querySelectorAll(selector))
                .map((element) => element.getAttribute('aria-label') ?? '')
                .filter((label) => label.length > 0)
                .sort((left, right) => right.length - left.length)[0] ?? '';
            }
            """,
            arg={"selector": selector},
        )
        label = str(payload).strip()
        if not label:
            raise AssertionError(
                "Step 5 failed: the live issue detail did not expose an accessible "
                f"label for {issue_key!r}.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        return label

    def observe_tab_chip(self, label: str) -> TabChipObservation:
        payload = self._session.evaluate(
            """
            (expectedLabel) => {
              const candidate = Array.from(
                document.querySelectorAll('flt-semantics[role="button"][aria-current]')
              ).find((element) => (element.innerText || '').trim() === expectedLabel);
              if (!candidate) {
                return null;
              }
              const rect = candidate.getBoundingClientRect();
              return {
                label: (candidate.innerText || '').trim(),
                isSelected: candidate.getAttribute('aria-current') === 'true',
                left: rect.left,
                top: rect.top,
                width: rect.width,
                height: rect.height,
              };
            }
            """,
            arg=label,
        )
        if not isinstance(payload, dict):
            raise AssertionError(
                "Step 3 failed: the live issue detail did not expose the expected "
                f"tab chip for {label!r}.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        return TabChipObservation(
            label=str(payload["label"]),
            is_selected=bool(payload["isSelected"]),
            left=float(payload["left"]),
            top=float(payload["top"]),
            width=float(payload["width"]),
            height=float(payload["height"]),
        )

    def wait_for_deferred_error(
        self,
        section_label: str,
        *,
        expected_fragment: str | None = None,
        timeout_ms: int = 30_000,
    ) -> str:
        selector = self._deferred_error_selector(
            section_label,
            expected_fragment=expected_fragment,
        )
        self._session.wait_for_selector(selector, timeout_ms=timeout_ms)
        return self.deferred_error_label(
            section_label,
            expected_fragment=expected_fragment,
            timeout_ms=timeout_ms,
        )

    def wait_for_deferred_loading(
        self,
        section_label: str,
        *,
        timeout_ms: int = 30_000,
    ) -> str:
        selector = self._deferred_loading_selector(section_label)
        selector_probe_timeout = min(timeout_ms, 1_000)
        try:
            self._session.wait_for_selector(
                selector,
                timeout_ms=selector_probe_timeout,
            )
        except WebAppTimeoutError:
            loading_fragment = f"{section_label} loading"
            body_text = self._session.wait_for_function(
                """
                ({ loadingFragment }) => {
                  const bodyText = document.body?.innerText ?? '';
                  return bodyText.toLowerCase().includes(loadingFragment.toLowerCase())
                    ? bodyText
                    : null;
                }
                """,
                arg={"loadingFragment": loading_fragment},
                timeout_ms=timeout_ms,
            )
            if isinstance(body_text, str) and loading_fragment.lower() in body_text.lower():
                return loading_fragment
            return self.current_body_text()
        payload = self._session.evaluate(
            """
            ({ selector }) => {
              const element = document.querySelector(selector);
              return element?.getAttribute('aria-label') ?? '';
            }
            """,
            arg={"selector": selector},
        )
        label = str(payload).strip()
        if not label:
            raise AssertionError(
                "Step 4 failed: the live issue detail did not expose an accessible "
                f"loading label for {section_label!r}.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        return label

    def accessible_label_count_containing(self, fragment: str) -> int:
        selector = f'[aria-label*="{self._escape(fragment)}"]'
        return self._session.count(selector)

    def visible_accessible_label_count_containing(self, fragment: str) -> int:
        payload = self._session.evaluate(
            """
            ({ fragment }) => {
              const isVisible = (element) => {
                if (!element) {
                  return false;
                }
                const rect = element.getBoundingClientRect();
                if (rect.width <= 0 || rect.height <= 0) {
                  return false;
                }
                const style = window.getComputedStyle(element);
                return style.visibility !== 'hidden' && style.display !== 'none';
              };
              const hasVisibleSurface = (element) =>
                isVisible(element)
                || Array.from(element.querySelectorAll('*')).some(isVisible);
              return Array.from(document.querySelectorAll('[aria-label]')).filter(
                (element) =>
                  (element.getAttribute('aria-label') ?? '').includes(fragment)
                  && hasVisibleSurface(element),
              ).length;
            }
            """,
            arg={"fragment": fragment},
        )
        return int(payload) if isinstance(payload, int) else 0

    def wait_for_accessible_label_fragment(
        self,
        fragment: str,
        *,
        timeout_ms: int = 30_000,
    ) -> str:
        selector = f'[aria-label*="{self._escape(fragment)}"]'
        self._session.wait_for_selector(selector, timeout_ms=timeout_ms)
        payload = self._session.evaluate(
            """
            ({ selector }) => {
              return Array.from(document.querySelectorAll(selector))
                .map((element) => element.getAttribute('aria-label') ?? '')
                .filter((label) => label.length > 0)
                .sort((left, right) => right.length - left.length)[0] ?? '';
            }
            """,
            arg={"selector": selector},
        )
        return str(payload).strip()

    def wait_for_visible_accessible_label_fragment(
        self,
        fragment: str,
        *,
        timeout_ms: int = 30_000,
    ) -> str:
        payload = self._session.wait_for_function(
            """
            ({ fragment }) => {
              const isVisible = (element) => {
                if (!element) {
                  return false;
                }
                const rect = element.getBoundingClientRect();
                if (rect.width <= 0 || rect.height <= 0) {
                  return false;
                }
                const style = window.getComputedStyle(element);
                return style.visibility !== 'hidden' && style.display !== 'none';
              };
              const hasVisibleSurface = (element) =>
                isVisible(element)
                || Array.from(element.querySelectorAll('*')).some(isVisible);
              const seen = new Set();
              const matches = Array.from(document.querySelectorAll('[aria-label]'))
                .map((element) => ({
                  label: element.getAttribute('aria-label') ?? '',
                  visible: hasVisibleSurface(element),
                }))
                .filter((candidate) =>
                  candidate.visible
                  && candidate.label.includes(fragment)
                  && !seen.has(candidate.label)
                  && seen.add(candidate.label),
                )
                .map((candidate) => candidate.label)
                .sort((left, right) => right.length - left.length);
              return matches[0] ?? null;
            }
            """,
            arg={"fragment": fragment},
            timeout_ms=timeout_ms,
        )
        return str(payload).strip()

    def wait_for_deferred_error_to_clear(
        self,
        section_label: str,
        *,
        timeout_ms: int = 30_000,
    ) -> int:
        selector = self._deferred_error_selector(section_label)
        self._session.wait_for_function(
            """
            ({ selector }) => document.querySelectorAll(selector).length === 0
            """,
            arg={"selector": selector},
            timeout_ms=timeout_ms,
        )
        return self._session.count(selector)

    def deferred_error_label(
        self,
        section_label: str,
        *,
        expected_fragment: str | None = None,
        timeout_ms: int = 30_000,
    ) -> str:
        selector = self._deferred_error_selector(
            section_label,
            expected_fragment=expected_fragment,
        )
        self._session.wait_for_selector(selector, timeout_ms=timeout_ms)
        payload = self._session.evaluate(
            """
            ({ selector }) => {
              const element = document.querySelector(selector);
              return element?.getAttribute('aria-label') ?? '';
            }
            """,
            arg={"selector": selector},
        )
        label = str(payload).strip()
        if not label:
            raise AssertionError(
                "Step 4 failed: the live issue detail did not expose an accessible "
                f"error label for {section_label!r}.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        return label

    def click_deferred_retry(
        self,
        section_label: str,
        *,
        timeout_ms: int = 30_000,
    ) -> None:
        selector = (
            self._deferred_error_selector(section_label, expected_fragment="Retry")
            + ' flt-semantics[role="button"]'
        )
        self._session.click(selector, timeout_ms=timeout_ms)

    def focus_collaboration_tab(self, label: str) -> None:
        if self._session.count(self._tab_button_selector, has_text=label) > 0:
            self._session.focus(
                self._tab_button_selector,
                has_text=label,
                timeout_ms=30_000,
            )
            return
        self._session.focus(
            self._button_selector,
            has_text=label,
            timeout_ms=30_000,
        )

    def active_element(self) -> FocusedElementObservation:
        return self._session.active_element()

    def press_key(self, key: str) -> None:
        self._session.press_key(key, timeout_ms=30_000)

    def choose_attachment(self, file_path: str) -> None:
        self._session.click_and_choose_file(
            self._choose_attachment_button_selector,
            [file_path],
            timeout_ms=30_000,
        )

    def upload_attachment(self) -> None:
        self._session.click(
            self._upload_attachment_button_selector,
            timeout_ms=30_000,
        )

    def attachment_download_button_count(self, attachment_name: str) -> int:
        payload = self._session.evaluate(
            """
            ({ downloadLabel }) => {
              const isVisible = (element) => {
                if (!element) {
                  return false;
                }
                const rect = element.getBoundingClientRect();
                if (rect.width <= 0 || rect.height <= 0) {
                  return false;
                }
                const style = window.getComputedStyle(element);
                return style.visibility !== 'hidden' && style.display !== 'none';
              };
              const hasVisibleSurface = (element) =>
                isVisible(element)
                || Array.from(
                  element.querySelectorAll('flt-semantics, flt-semantics-img, [aria-label]')
                ).some(isVisible);
              return Array.from(
                document.querySelectorAll('flt-semantics[aria-label]')
              ).filter((element) => {
                const label = element.getAttribute('aria-label') ?? '';
                return label === downloadLabel && hasVisibleSurface(element);
              }).length;
            }
            """,
            arg={"downloadLabel": self._download_button_label(attachment_name)},
        )
        if not isinstance(payload, int):
            raise AssertionError(
                "Step 1 failed: unable to count the visible attachment download controls.\n"
                f"Observed payload: {payload!r}",
            )
        return payload

    def attachment_download_button_label(self, attachment_name: str) -> str:
        download_label = self._download_button_label(attachment_name)
        payload = self._session.evaluate(
            """
            ({ downloadLabel }) => {
              const isVisible = (element) => {
                if (!element) {
                  return false;
                }
                const rect = element.getBoundingClientRect();
                if (rect.width <= 0 || rect.height <= 0) {
                  return false;
                }
                const style = window.getComputedStyle(element);
                return style.visibility !== 'hidden' && style.display !== 'none';
              };
              const hasVisibleSurface = (element) =>
                isVisible(element)
                || Array.from(
                  element.querySelectorAll('flt-semantics, flt-semantics-img, [aria-label]')
                ).some(isVisible);
              return Array.from(
                document.querySelectorAll('flt-semantics[aria-label]')
              ).map((element) => {
                const label = element.getAttribute('aria-label') ?? '';
                if (label !== downloadLabel || !hasVisibleSurface(element)) {
                  return '';
                }
                return label;
              }).find((label) => label.length > 0) ?? '';
            }
            """,
            arg={"downloadLabel": download_label},
        )
        label = str(payload).strip()
        if not label:
            raise AssertionError(
                "Step 1 failed: the Attachments tab did not expose the expected "
                f"download button for {attachment_name!r}.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        return label

    def trigger_focused_download(self) -> str:
        return self._session.wait_for_download_after_keypress(
            "Enter",
            timeout_ms=60_000,
        )

    def activate_focused_control_in_new_page(
        self,
        *,
        timeout_ms: int = 8_000,
    ) -> NewPageObservation:
        return self._session.wait_for_new_page_after_active_element_click(
            timeout_ms=timeout_ms,
        )

    def download_attachment(self, attachment_name: str) -> str:
        return self._session.wait_for_download_after_click(
            self._download_button_selector(attachment_name),
            timeout_ms=60_000,
        )

    def visible_button_count(self, label: str) -> int:
        return self._visible_button_count_by_label(label)

    def observe_attachment_upload_controls(self) -> AttachmentUploadControlsObservation:
        payload = self._session.evaluate(
            """
            () => {
              const isVisible = (element) => {
                if (!element) {
                  return false;
                }
                const rect = element.getBoundingClientRect();
                if (rect.width <= 0 || rect.height <= 0) {
                  return false;
                }
                const style = window.getComputedStyle(element);
                return style.visibility !== 'hidden' && style.display !== 'none';
              };
              const controlRoots = (label) => Array.from(
                document.querySelectorAll(`flt-semantics[aria-label="${label}"]`)
              ).filter((element) =>
                isVisible(element)
                || Array.from(
                  element.querySelectorAll('flt-semantics, flt-semantics-img, [aria-label]')
                ).some(isVisible)
              );
              const controlTrigger = (element) => [
                element?.querySelector('flt-semantics[flt-tappable]'),
                element?.querySelector('[flt-tappable]'),
                element?.querySelector('flt-semantics[role="button"]'),
                element?.querySelector('[role="button"]'),
                (
                  element?.getAttribute('flt-tappable') !== null
                  || element?.getAttribute('aria-disabled') !== null
                )
                  ? element
                  : null,
              ].find((candidate) => !!candidate && isVisible(candidate)) ?? null;
              const isEnabled = (element) => {
                const trigger = controlTrigger(element);
                return (
                  !!trigger
                  && element?.getAttribute('aria-disabled') !== 'true'
                  && trigger.getAttribute('aria-disabled') !== 'true'
                );
              };

              const actionableControls = (label) => controlRoots(label)
                .map((element) => ({ element, trigger: controlTrigger(element) }))
                .filter(({ trigger }) => !!trigger && isVisible(trigger));
              const chooseButtons = actionableControls('Choose attachment');
              const uploadButtons = actionableControls('Upload attachment');

              return {
                chooseButtonCount: chooseButtons.length,
                chooseButtonEnabled: chooseButtons.some(({ element }) => isEnabled(element)),
                uploadButtonCount: uploadButtons.length,
                uploadButtonEnabled: uploadButtons.some(({ element }) => isEnabled(element)),
              };
            }
            """,
        )
        if not isinstance(payload, dict):
            raise AssertionError(
                "Step 1 failed: unable to inspect the hosted attachment upload controls.\n"
                f"Observed payload: {payload!r}",
            )
        return AttachmentUploadControlsObservation(
            choose_button_count=int(payload.get("chooseButtonCount", 0)),
            choose_button_enabled=bool(payload.get("chooseButtonEnabled")),
            upload_button_count=int(payload.get("uploadButtonCount", 0)),
            upload_button_enabled=bool(payload.get("uploadButtonEnabled")),
        )

    def observe_attachment_upload_controls(self) -> AttachmentUploadControlsObservation:
        payload = self._session.evaluate(
            """
            () => {
              const isVisible = (element) => {
                if (!element) {
                  return false;
                }
                const rect = element.getBoundingClientRect();
                return rect.width > 0 && rect.height > 0;
              };
              const isEnabled = (element) =>
                !!element &&
                isVisible(element) &&
                element.getAttribute('aria-disabled') !== 'true';
              const countButtons = (fragment) => Array.from(
                document.querySelectorAll('flt-semantics[role="button"][aria-label]')
              ).filter((element) => {
                const label = element.getAttribute('aria-label') || '';
                return isVisible(element) && label.includes(fragment);
              }).length;

              const chooseButton = document.querySelector(
                'flt-semantics[aria-label="Choose attachment"]'
              );
              const chooseTrigger = document.querySelector(
                'flt-semantics[aria-label="Choose attachment"] flt-semantics'
              );
              const uploadButton = document.querySelector(
                'flt-semantics[aria-label="Upload attachment"]'
              );
              const uploadTrigger = document.querySelector(
                'flt-semantics[aria-label="Upload attachment"] flt-semantics'
              );

              return {
                chooseButtonCount: countButtons('Choose attachment'),
                chooseButtonEnabled:
                  isEnabled(chooseTrigger) || isEnabled(chooseButton),
                uploadButtonCount: countButtons('Upload attachment'),
                uploadButtonEnabled:
                  isEnabled(uploadTrigger) || isEnabled(uploadButton),
              };
            }
            """,
        )
        if not isinstance(payload, dict):
            raise AssertionError(
                "Step 1 failed: unable to inspect the hosted attachment upload controls.\n"
                f"Observed payload: {payload!r}",
            )
        return AttachmentUploadControlsObservation(
            choose_button_count=int(payload.get("chooseButtonCount", 0)),
            choose_button_enabled=bool(payload.get("chooseButtonEnabled")),
            upload_button_count=int(payload.get("uploadButtonCount", 0)),
            upload_button_enabled=bool(payload.get("uploadButtonEnabled")),
        )

    def choose_attachment_file(self, file_path: str) -> None:
        self._session.click_and_set_files(
            self._choose_attachment_button_selector,
            [file_path],
            timeout_ms=30_000,
        )

    def click_upload_attachment(self) -> None:
        self._session.click(
            self._upload_attachment_button_selector,
            timeout_ms=30_000,
        )

    def wait_for_selected_attachment_summary(
        self,
        *,
        attachment_name: str,
        attachment_size_label: str,
        timeout_ms: int = 30_000,
    ) -> str:
        expected_label = (
            f"Selected attachment: {attachment_name} ({attachment_size_label})"
        )
        self._session.wait_for_function(
            """
            ({ expectedLabel }) => {
              const labels = Array.from(document.querySelectorAll('[aria-label]'))
                .map((element) => element.getAttribute('aria-label') ?? '');
              if (labels.some((label) => label.includes(expectedLabel))) {
                return true;
              }
              const bodyText = document.body?.innerText ?? '';
              return bodyText.includes(expectedLabel);
            }
            """,
            arg={"expectedLabel": expected_label},
            timeout_ms=timeout_ms,
        )
        payload = self._session.evaluate(
            """
            ({ expectedLabel }) => {
              const labelMatch = Array.from(document.querySelectorAll('[aria-label]'))
                .map((element) => element.getAttribute('aria-label') ?? '')
                .find((label) => label.includes(expectedLabel));
              if (labelMatch) {
                return labelMatch;
              }
              const bodyText = document.body?.innerText ?? '';
              return bodyText.includes(expectedLabel) ? expectedLabel : '';
            }
            """,
            arg={"expectedLabel": expected_label},
        )
        label = str(payload).strip()
        if not label:
            raise AssertionError(
                "Step 2 failed: the Attachments tab did not expose the selected attachment "
                f"summary for {attachment_name!r}.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        return label

    def wait_for_replace_attachment_dialog(
        self,
        attachment_name: str,
        *,
        timeout_ms: int = 30_000,
    ) -> str:
        expected_fragments = (
            "Replace attachment?",
            f"Uploading this file will replace the existing attachment stored as {attachment_name}.",
            "Keep current attachment",
            "Replace attachment",
        )
        self._session.wait_for_function(
            """
            ({ expectedFragments }) => {
              const bodyText = document.body?.innerText ?? '';
              return expectedFragments.every((fragment) => bodyText.includes(fragment));
            }
            """,
            arg={"expectedFragments": list(expected_fragments)},
            timeout_ms=timeout_ms,
        )
        return self.current_body_text()

    def confirm_replace_attachment(self) -> None:
        self._session.click(self._replace_attachment_button_selector, timeout_ms=30_000)

    def wait_for_replace_attachment_dialog_to_close(
        self,
        *,
        timeout_ms: int = 30_000,
    ) -> None:
        self._session.wait_for_text_absence("Replace attachment?", timeout_ms=timeout_ms)

    def attachment_row_text(self, attachment_name: str, *, timeout_ms: int = 30_000) -> str:
        download_label = self._download_button_label(attachment_name)
        self._session.wait_for_function(
            """
            ({ downloadLabel }) => {
              const isVisible = (element) => {
                if (!element) {
                  return false;
                }
                const rect = element.getBoundingClientRect();
                if (rect.width <= 0 || rect.height <= 0) {
                  return false;
                }
                const style = window.getComputedStyle(element);
                return style.visibility !== 'hidden' && style.display !== 'none';
              };
              const hasVisibleSurface = (element) =>
                isVisible(element)
                || Array.from(
                  element.querySelectorAll('flt-semantics, flt-semantics-img, [aria-label]')
                ).some(isVisible);
              return Array.from(document.querySelectorAll('flt-semantics[aria-label]')).some(
                (element) =>
                  (element.getAttribute('aria-label') ?? '') === downloadLabel
                  && hasVisibleSurface(element)
              );
            }
            """,
            arg={"downloadLabel": download_label},
            timeout_ms=timeout_ms,
        )
        payload = self._session.evaluate(
            """
            ({ attachmentName, downloadLabel }) => {
              const isVisible = (element) => {
                if (!element) {
                  return false;
                }
                const rect = element.getBoundingClientRect();
                if (rect.width <= 0 || rect.height <= 0) {
                  return false;
                }
                const style = window.getComputedStyle(element);
                return style.visibility !== 'hidden' && style.display !== 'none';
              };
              const hasVisibleSurface = (element) =>
                isVisible(element)
                || Array.from(
                  element.querySelectorAll('flt-semantics, flt-semantics-img, [aria-label]')
                ).some(isVisible);
              const button = Array.from(document.querySelectorAll('flt-semantics[aria-label]'))
                .find((element) =>
                  (element.getAttribute('aria-label') ?? '') === downloadLabel
                  && hasVisibleSurface(element)
                );
              if (!button) {
                return '';
              }
              let candidate = button;
              for (let depth = 0; depth < 8 && candidate; depth += 1) {
                const text = (candidate.innerText ?? '').trim();
                if (text.includes(attachmentName) && /\\b\\d+ B\\b/.test(text)) {
                  return text;
                }
                candidate = candidate.parentElement;
              }
              return ((button.parentElement?.innerText) ?? button.innerText ?? '').trim();
            }
            """,
            arg={
                "attachmentName": attachment_name,
                "downloadLabel": download_label,
            },
        )
        row_text = str(payload).strip()
        if not row_text:
            raise AssertionError(
                "Step 5 failed: the Attachments tab did not expose the expected attachment "
                f"row for {attachment_name!r}.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        return row_text

    def wait_for_attachment_picker_ready(self, *, timeout_ms: int = 60_000) -> None:
        self._session.wait_for_function(
            """
            () => {
              const trigger = document.querySelector(
                'flt-semantics[aria-label="Choose attachment"] flt-semantics[flt-tappable]'
              );
              return !!trigger && trigger.getAttribute('aria-disabled') !== 'true';
            }
            """,
            timeout_ms=timeout_ms,
        )

    def choose_attachment(self, file_path: str, *, timeout_ms: int = 30_000) -> None:
        self.wait_for_attachment_picker_ready(timeout_ms=timeout_ms)
        self._session.select_files_after_click(
            'flt-semantics[aria-label="Choose attachment"]',
            [file_path],
            timeout_ms=timeout_ms,
        )

    def wait_for_attachment_selection_summary(
        self,
        *,
        file_name: str,
        timeout_ms: int = 60_000,
    ) -> AttachmentSelectionSummaryObservation:
        payload = self._session.wait_for_function(
            """
            ({ fileName }) => {
              const normalize = (value) => (value || '').replace(/\\s+/g, ' ').trim();
              const collectText = (element) => normalize(
                [
                  element?.getAttribute?.('aria-label') ?? '',
                  element?.innerText ?? '',
                  element?.textContent ?? '',
                ].join(' ')
              );
              const visibleCandidates = Array.from(
                document.querySelectorAll('flt-semantics, flt-semantics-img, [aria-label]')
              )
                .map((element) => {
                  const rect = element.getBoundingClientRect();
                  return {
                    element,
                    text: collectText(element),
                    top: rect.top,
                    width: rect.width,
                    height: rect.height,
                  };
                })
                .filter((candidate) =>
                  candidate.text.includes(fileName) &&
                  candidate.width > 0 &&
                  candidate.height > 0
                );
              if (visibleCandidates.length === 0) {
                return null;
              }

              const scoreCandidate = (candidate) => {
                const lowered = candidate.text.toLowerCase();
                let score = 0;
                if (lowered.includes('selected attachment:')) {
                  score += 100;
                }
                if (lowered.includes('selected file')) {
                  score += 80;
                }
                if (lowered.includes('choose a file to review its size before upload')) {
                  score += 40;
                }
                if (/\\b\\d+(?:\\.\\d+)?\\s*(?:kb|mb|bytes?)\\b/i.test(candidate.text)) {
                  score += 20;
                }
                return score;
              };

              const summaryCandidate = visibleCandidates
                .map((candidate) => ({
                  ...candidate,
                  score: scoreCandidate(candidate),
                  textLength: candidate.text.length,
                  area: candidate.width * candidate.height,
                }))
                .sort((left, right) => {
                  if (right.score !== left.score) {
                    return right.score - left.score;
                  }
                  if (left.textLength !== right.textLength) {
                    return left.textLength - right.textLength;
                  }
                  if (left.area !== right.area) {
                    return left.area - right.area;
                  }
                  return left.top - right.top;
                })[0];

              const sizeMatch = summaryCandidate.text.match(
                /\\b\\d+(?:\\.\\d+)?\\s*(?:KB|MB|bytes?)\\b/i
              );
              const uploadTrigger = document.querySelector(
                'flt-semantics[aria-label="Upload attachment"] flt-semantics[flt-tappable]'
              );
              const firstDownload = Array.from(
                document.querySelectorAll('flt-semantics, [aria-label]')
              )
                .map((element) => ({
                  text: collectText(element),
                  top: element.getBoundingClientRect().top,
                  width: element.getBoundingClientRect().width,
                  height: element.getBoundingClientRect().height,
                }))
                .filter((candidate) =>
                  candidate.text.startsWith('Download ') &&
                  candidate.width > 0 &&
                  candidate.height > 0
                )
                .map((candidate) => candidate.top)
                .filter((top) => Number.isFinite(top))
                .sort((left, right) => left - right)[0];
              return {
                summaryText: summaryCandidate.text,
                fileNameVisible: summaryCandidate.text.includes(fileName),
                sizeLabel: sizeMatch ? sizeMatch[0] : '',
                uploadEnabled: uploadTrigger?.getAttribute('aria-disabled') !== 'true',
                summaryTop: summaryCandidate.top,
                firstAttachmentTop:
                  typeof firstDownload === 'number' ? firstDownload : null,
              };
            }
            """,
            arg={"fileName": file_name},
            timeout_ms=timeout_ms,
        )
        if not isinstance(payload, dict):
            raise AssertionError(
                "Step 3 failed: the Attachments action area never showed a visible selected "
                f"file summary for {file_name!r} before upload.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        return AttachmentSelectionSummaryObservation(
            summary_text=str(payload["summaryText"]),
            file_name_visible=bool(payload["fileNameVisible"]),
            size_label=str(payload["sizeLabel"]),
            upload_enabled=bool(payload["uploadEnabled"]),
            summary_top=float(payload["summaryTop"]),
            first_attachment_top=(
                float(payload["firstAttachmentTop"])
                if payload["firstAttachmentTop"] is not None
                else None
            ),
        )

    def wait_for_comment_composer(
        self,
        *,
        timeout_ms: int = 60_000,
    ) -> CommentComposerObservation:
        payload = self._session.wait_for_function(
            """
            () => {
              const field =
                document.querySelector('textarea[aria-label="Comments"]')
                ?? document.querySelector('input[aria-label="Comments"]')
                ?? document.querySelector('[role="textbox"][aria-label="Comments"]');
              const button = Array.from(
                document.querySelectorAll('flt-semantics[role="button"]'),
              ).find((element) => (element.getAttribute('aria-label') ?? '') === 'Post comment');
              if (!field || !button) {
                return null;
              }
              const fieldDisabled =
                field.getAttribute('disabled') !== null
                || field.getAttribute('aria-disabled') === 'true'
                || field.disabled === true;
              const buttonDisabled =
                button.getAttribute('aria-disabled') === 'true'
                || button.getAttribute('disabled') !== null;
              return {
                fieldLabel: field.getAttribute('aria-label') ?? '',
                fieldEnabled: !fieldDisabled,
                buttonLabel: button.getAttribute('aria-label') ?? '',
                buttonEnabled: !buttonDisabled,
              };
            }
            """,
            timeout_ms=timeout_ms,
        )
        if not isinstance(payload, dict):
            raise AssertionError(
                "Step 2 failed: the Comments tab did not expose the visible comment "
                "composer controls needed to prove commenting stays enabled.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        return CommentComposerObservation(
            field_label=str(payload.get("fieldLabel", "")),
            field_enabled=bool(payload.get("fieldEnabled")),
            button_label=str(payload.get("buttonLabel", "")),
            button_enabled=bool(payload.get("buttonEnabled")),
        )

    def _visible_button_count_by_label(self, label: str) -> int:
        payload = self._session.evaluate(
            """
            ({ label }) => {
              const normalize = (value) => (value || '').replace(/\\s+/g, ' ').trim();
              const seen = new Set();
              let count = 0;
              for (const element of document.querySelectorAll('flt-semantics[role="button"]')) {
                const text = normalize(
                  [
                    element.getAttribute('aria-label') ?? '',
                    element.innerText ?? '',
                    element.textContent ?? '',
                  ].join(' ')
                );
                if (!text.includes(label)) {
                  continue;
                }
                const rect = element.getBoundingClientRect();
                if (rect.width <= 0 || rect.height <= 0) {
                  continue;
                }
                const key = [
                  Math.round(rect.left),
                  Math.round(rect.top),
                  Math.round(rect.width),
                  Math.round(rect.height),
                ].join('|');
                if (seen.has(key)) {
                  continue;
                }
                seen.add(key);
                count += 1;
              }
              return count;
            }
            """,
            arg={"label": label},
        )
        return int(payload)

    def _is_connected(self, connected_banner: str) -> bool:
        return (
            self._session.count(self._connected_button_selector) > 0
            or connected_banner in self.current_body_text()
        )

    @staticmethod
    def _open_issue_selector(*, issue_key: str, issue_summary: str) -> str:
        escaped_key = LiveIssueDetailCollaborationPage._escape(issue_key)
        escaped_summary = LiveIssueDetailCollaborationPage._escape(issue_summary)
        return (
            'flt-semantics[role="button"]'
            f'[aria-label*="Open {escaped_key} {escaped_summary}"]'
        )

    @staticmethod
    def _issue_detail_selector(issue_key: str) -> str:
        return (
            'flt-semantics[aria-label*="Issue detail '
            f'{LiveIssueDetailCollaborationPage._escape(issue_key)}"], '
            'flt-semantics-img[aria-label*="Issue detail '
            f'{LiveIssueDetailCollaborationPage._escape(issue_key)}"]'
        )

    @staticmethod
    def _download_button_label(attachment_name: str) -> str:
        return f"Download {attachment_name}"

    @staticmethod
    def _download_button_selector(attachment_name: str) -> str:
        return (
            'flt-semantics[aria-label="'
            f'{LiveIssueDetailCollaborationPage._escape(LiveIssueDetailCollaborationPage._download_button_label(attachment_name))}'
            '"]'
        )

    @staticmethod
    def _deferred_error_selector(
        section_label: str,
        *,
        expected_fragment: str | None = None,
    ) -> str:
        selector = (
            'flt-semantics[role="button"]'
            f'[aria-label*="{LiveIssueDetailCollaborationPage._escape(section_label)} error"]'
        )
        if expected_fragment:
            selector += (
                f'[aria-label*="{LiveIssueDetailCollaborationPage._escape(expected_fragment)}"]'
            )
        return selector

    @staticmethod
    def _deferred_loading_selector(section_label: str) -> str:
        return (
            '[aria-label*="'
            f'{LiveIssueDetailCollaborationPage._escape(section_label)} loading"]'
        )

    @staticmethod
    def _escape(value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"')
