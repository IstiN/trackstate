from __future__ import annotations

from dataclasses import dataclass

from testing.components.pages.live_issue_detail_collaboration_page import (
    LiveIssueDetailCollaborationPage,
)
from testing.components.pages.trackstate_tracker_page import TrackStateTrackerPage
from testing.core.interfaces.web_app_session import WebAppTimeoutError


@dataclass(frozen=True)
class EditControlObservation:
    label: str | None
    text: str
    tabindex: str | None
    expanded: str | None

    def contains(self, fragment: str) -> bool:
        return fragment in self.text or (
            self.label is not None and fragment in self.label
        )


class LiveMultiViewRefreshPage:
    _button_selector = 'flt-semantics[role="button"]'
    _edit_button_selector = 'flt-semantics[role="button"][aria-label="Edit"]'
    _menu_item_selector = 'flt-semantics[role="menuitem"]'
    _dialog_group_selector = 'flt-semantics[role="group"][aria-label="Edit issue"]'

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

    def open_edit_dialog_for_issue(self, *, issue_key: str, issue_summary: str) -> str:
        self.navigate_to_section("JQL Search")
        self._session.wait_for_selector(
            self._issue_selector(issue_key=issue_key, issue_summary=issue_summary),
            timeout_ms=60_000,
        )
        self.open_issue_from_current_section(
            issue_key=issue_key,
            issue_summary=issue_summary,
        )
        self._session.wait_for_selector(self._edit_button_selector, timeout_ms=30_000)
        self._session.click(self._edit_button_selector, timeout_ms=30_000)
        dialog_text = self._session.wait_for_text("Edit issue", timeout_ms=30_000)
        if issue_key not in dialog_text:
            raise AssertionError(
                "Step 3 failed: opening the requested issue from JQL Search did not "
                f"lead to the edit surface for {issue_key}.\n"
                f"Expected issue key in edit dialog: {issue_key}\n"
                f"Observed dialog text:\n{dialog_text}",
            )
        return dialog_text

    def open_issue_from_current_section(
        self,
        *,
        issue_key: str,
        issue_summary: str,
    ) -> str:
        selector = self._issue_selector(issue_key=issue_key, issue_summary=issue_summary)
        self._session.wait_for_selector(selector, timeout_ms=60_000)
        self._session.click(selector, timeout_ms=30_000)
        self._session.wait_for_selector(
            self._issue_detail_selector(issue_key),
            timeout_ms=60_000,
        )
        return self.current_body_text()

    def navigate_to_section(self, label: str) -> None:
        bounds = self._button_bounds_for_sidebar_label(label)
        if bounds is None:
            raise AssertionError(
                f'Step failed: the hosted tracker did not expose a visible "{label}" '
                "navigation entry in the sidebar.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        self._session.mouse_click(
            bounds["x"] + (bounds["width"] / 2),
            bounds["y"] + (bounds["height"] / 2),
        )
        try:
            self._session.wait_for_function(
                """
                (label) => Array.from(document.querySelectorAll('flt-semantics[role="button"]'))
                  .some((element) =>
                    (element.innerText || '').trim() === label
                    && element.getAttribute('aria-current') === 'true')
                """,
                arg=label,
                timeout_ms=30_000,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                f'Step failed: clicking the "{label}" sidebar entry did not activate '
                "that section in the hosted tracker.\n"
                f"Observed body text:\n{self.current_body_text()}",
            ) from error

    def status_control(self) -> EditControlObservation:
        observation = self._control_observation(
            """
            (button) => {
              const label = button.getAttribute('aria-label') ?? '';
              const text = (button.innerText || '').trim();
              return label.includes('Status') || text.startsWith('Status');
            }
            """,
        )
        if observation is None:
            raise AssertionError(
                "Human-style verification failed: the Edit issue surface did not show "
                "a visible Status control.\n"
                f"Observed dialog text:\n{self.current_body_text()}",
            )
        return observation

    def priority_control(self) -> EditControlObservation:
        observation = self._control_observation(
            """
            (button) => {
              const label = button.getAttribute('aria-label') ?? '';
              const text = (button.innerText || '').trim();
              return label.includes('Priority') || text.startsWith('Priority');
            }
            """,
        )
        if observation is None:
            raise AssertionError(
                "Human-style verification failed: the Edit issue surface did not show "
                "a visible Priority control.\n"
                f"Observed dialog text:\n{self.current_body_text()}",
            )
        return observation

    def change_priority(self, target_label: str) -> EditControlObservation:
        control = self.priority_control()
        if control.contains(target_label):
            return control
        options = self._open_focusable_dropdown(
            selector=self._button_selector,
            has_text="Priority",
            control_name="Priority",
        )
        self._select_dropdown_option(
            control_name="Priority",
            target_label=target_label,
            options=options,
        )
        updated = self.priority_control()
        if not updated.contains(target_label):
            raise AssertionError(
                "Step 4 failed: selecting the Priority control did not update the visible "
                f"value to {target_label}.\n"
                f"Observed control label: {updated.label}\n"
                f"Observed control text: {updated.text}\n"
                f"Observed dialog text:\n{self.current_body_text()}",
            )
        return updated

    def change_status_transition(self, target_label: str) -> EditControlObservation:
        control = self.status_control()
        if control.contains("No workflow transitions available."):
            raise AssertionError(
                "Step 5 failed: the Edit issue surface for DEMO-3 did not expose any "
                "workflow transitions, so the scenario could not change the Status to "
                f"{target_label} before saving.\n"
                f"Observed status control label: {control.label}\n"
                f"Observed status helper text: {control.text}\n"
                f"Observed dialog text:\n{self.current_body_text()}",
            )
        if control.tabindex is None:
            raise AssertionError(
                "Step 5 failed: the visible Status control rendered as non-focusable in "
                "the hosted edit dialog, so the test could not perform a production-visible "
                f"workflow transition to {target_label}.\n"
                f"Observed status control label: {control.label}\n"
                f"Observed status helper text: {control.text}\n"
                f"Observed dialog text:\n{self.current_body_text()}",
            )
        if control.contains(target_label):
            return control
        options = self._open_focusable_dropdown(
            selector='flt-semantics[role="button"][aria-label*="Status"]',
            has_text=None,
            control_name="Status",
        )
        self._select_dropdown_option(
            control_name="Status",
            target_label=target_label,
            options=options,
        )
        updated = self.status_control()
        if not updated.contains(target_label):
            raise AssertionError(
                "Step 5 failed: selecting the Status control did not update the visible "
                f"workflow transition to {target_label}.\n"
                f"Observed control label: {updated.label}\n"
                f"Observed control text: {updated.text}\n"
                f"Observed dialog text:\n{self.current_body_text()}",
            )
        return updated

    def save_issue_edits(
        self,
        *,
        issue_key: str,
        expected_status: str,
    ) -> str:
        self._session.click(
            'flt-semantics[role="button"][aria-label="Save"]',
            timeout_ms=30_000,
        )
        try:
            payload = self._session.wait_for_function(
                """
                ({
                  dialogSelector,
                  detailSelector,
                  errorPrefix,
                  successMessages,
                }) => {
                  const bodyText = document.body?.innerText ?? '';
                  if (bodyText.includes(errorPrefix)) {
                    return { kind: 'error', bodyText };
                  }
                  const matchedSuccessMessage =
                    successMessages.find((message) => bodyText.includes(message)) ?? null;
                  const dialogVisible =
                    document.querySelector(dialogSelector) !== null;
                  if (dialogVisible || matchedSuccessMessage === null) {
                    return null;
                  }
                  const detailVisible =
                    document.querySelector(detailSelector) !== null;
                  if (!detailVisible) {
                    return null;
                  }
                  return { kind: 'saved', bodyText, matchedSuccessMessage };
                }
                """,
                arg={
                    "dialogSelector": self._dialog_group_selector,
                    "detailSelector": self._issue_detail_selector(issue_key),
                    "errorPrefix": TrackStateTrackerPage.SAVE_FAILED_PREFIX,
                    "successMessages": [
                        f"{issue_key} moved to {expected_status} and committed to GitHub.",
                        f"{issue_key} moved to {expected_status} and committed to local Git branch ",
                        f"{issue_key} moved locally. Connect GitHub in Settings to persist.",
                    ],
                },
                timeout_ms=180_000,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                "Step 6 failed: clicking Save never surfaced the required user-visible "
                "success banner and returned the app to the refreshed issue detail "
                "surface.\n"
                f"Observed body text:\n{self.current_body_text()}",
            ) from error

        if not isinstance(payload, dict):
            raise AssertionError(
                "Step 6 failed: saving the edited issue did not produce an observable "
                "post-save state in the hosted tracker.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        if str(payload.get("kind")) == "error":
            raise AssertionError(
                "Step 6 failed: clicking Save surfaced a visible save error instead of "
                "committing the edited issue.\n"
                f"Observed body text:\n{payload.get('bodyText', self.current_body_text())}",
            )
        return str(payload["bodyText"])

    def wait_for_issue_detail_state(
        self,
        *,
        issue_key: str,
        issue_summary: str,
        expected_status: str,
        expected_priority: str,
        step_number: int,
    ) -> str:
        try:
            payload = self._session.wait_for_function(
                """
                ({ issueKey, issueSummary, detailSelector, expectedStatus, expectedPriority }) => {
                  if (!document.querySelector(detailSelector)) {
                    return null;
                  }
                  const bodyText = document.body?.innerText ?? '';
                  const matches =
                    bodyText.includes(issueKey) &&
                    bodyText.includes(issueSummary) &&
                    bodyText.includes(expectedStatus) &&
                    bodyText.includes(expectedPriority);
                  return matches ? { bodyText } : null;
                }
                """,
                arg={
                    "issueKey": issue_key,
                    "issueSummary": issue_summary,
                    "detailSelector": self._issue_detail_selector(issue_key),
                    "expectedStatus": expected_status,
                    "expectedPriority": expected_priority,
                },
                timeout_ms=60_000,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                f"Step {step_number} failed: the hosted issue detail for {issue_key} did "
                f"not visibly refresh to Status = {expected_status} and Priority = "
                f"{expected_priority}.\n"
                f"Observed body text:\n{self.current_body_text()}",
            ) from error
        if not isinstance(payload, dict):
            raise AssertionError(
                f"Step {step_number} failed: the hosted issue detail for {issue_key} did "
                "not reach an observable refreshed state.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        return str(payload["bodyText"])

    def wait_for_board_projection(
        self,
        *,
        issue_key: str,
        issue_summary: str,
        expected_column: str,
        expected_priority: str,
    ) -> str:
        self.navigate_to_section("Board")
        try:
            payload = self._session.wait_for_function(
                """
                ({ issueKey, issueSummary, expectedColumn, expectedPriority }) => {
                  const expectedAriaLabel = `${expectedColumn} column`;
                  const column = Array.from(document.querySelectorAll('flt-semantics'))
                    .find((element) => (element.getAttribute('aria-label') ?? '') === expectedAriaLabel);
                  if (!column) {
                    return null;
                  }
                  const text = (column.innerText || '').trim();
                  return text.includes(issueKey)
                    && text.includes(issueSummary)
                    && text.includes(expectedPriority)
                    ? { text }
                    : null;
                }
                """,
                arg={
                    "issueKey": issue_key,
                    "issueSummary": issue_summary,
                    "expectedColumn": expected_column,
                    "expectedPriority": expected_priority,
                },
                timeout_ms=60_000,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                "Step 8 failed: the Board view did not visibly refresh the edited issue "
                f"into the {expected_column} column with Priority = {expected_priority}.\n"
                f"Observed Board text:\n{self.current_body_text()}",
            ) from error
        if not isinstance(payload, dict):
            raise AssertionError(
                "Step 8 failed: the Board view did not expose an observable refreshed "
                f"projection for {issue_key}.\n"
                f"Observed Board text:\n{self.current_body_text()}",
            )
        return str(payload["text"])

    def wait_for_hierarchy_projection(
        self,
        *,
        issue_key: str,
        issue_summary: str,
        expected_status: str,
        expected_priority: str,
    ) -> str:
        self.navigate_to_section("Hierarchy")
        return self._wait_for_issue_projection(
            issue_key=issue_key,
            issue_summary=issue_summary,
            expected_status=expected_status,
            expected_priority=expected_priority,
            section_label="Hierarchy",
            step_number=9,
        )

    def wait_for_jql_search_projection(
        self,
        *,
        issue_key: str,
        issue_summary: str,
        expected_status: str,
        expected_priority: str,
        expected_count_summary: str,
    ) -> str:
        try:
            payload = self._session.wait_for_function(
                """
                ({
                  expectedCountSummary,
                  expectedPriority,
                  expectedStatus,
                  issueKey,
                  issueSelector,
                  issueSummary,
                }) => {
                  const bodyText = document.body?.innerText ?? '';
                  const countMatch = bodyText.match(/\\b(?:No issues|\\d+ issues?)\\b/);
                  const countSummary = countMatch ? countMatch[0] : null;
                  if (countSummary !== expectedCountSummary) {
                    return null;
                  }

                  const issue = document.querySelector(issueSelector);
                  if (!issue) {
                    return null;
                  }

                  let current = issue;
                  while (current) {
                    const projectionText = (current.innerText || current.textContent || '').trim();
                    if (
                      projectionText.includes(issueKey) &&
                      projectionText.includes(issueSummary)
                    ) {
                      return projectionText.includes(expectedStatus) &&
                          projectionText.includes(expectedPriority)
                        ? { countSummary, projectionText }
                        : null;
                    }
                    current = current.parentElement;
                  }

                  return null;
                }
                """,
                arg={
                    "expectedCountSummary": expected_count_summary,
                    "expectedPriority": expected_priority,
                    "expectedStatus": expected_status,
                    "issueKey": issue_key,
                    "issueSelector": self._issue_selector(
                        issue_key=issue_key,
                        issue_summary=issue_summary,
                    ),
                    "issueSummary": issue_summary,
                },
                timeout_ms=60_000,
            )
        except WebAppTimeoutError as error:
            current_projection = self._current_issue_projection_text(
                issue_key=issue_key,
                issue_summary=issue_summary,
            )
            raise AssertionError(
                "Step 10 failed: the JQL Search result row did not visibly refresh "
                f"{issue_key} to Status = {expected_status} and Priority = "
                f"{expected_priority} while showing {expected_count_summary}.\n"
                f"Observed JQL Search projection: {current_projection}\n"
                f"Observed body text:\n{self.current_body_text()}",
            ) from error
        if not isinstance(payload, dict):
            raise AssertionError(
                "Step 10 failed: the JQL Search result row did not expose an observable "
                f"projection for {issue_key} after saving.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        return str(payload["projectionText"])

    def current_body_text(self) -> str:
        return self._tracker_page.body_text()

    def screenshot(self, path: str) -> None:
        self._tracker_page.screenshot(path)

    def _wait_for_issue_projection(
        self,
        *,
        issue_key: str,
        issue_summary: str,
        expected_status: str,
        expected_priority: str,
        section_label: str,
        step_number: int,
    ) -> str:
        try:
            payload = self._session.wait_for_function(
                """
                ({
                  expectedPriority,
                  expectedStatus,
                  issueKey,
                  issueSelector,
                  issueSummary,
                }) => {
                  const issue = document.querySelector(issueSelector);
                  if (!issue) {
                    return null;
                  }

                  let current = issue;
                  while (current) {
                    const projectionText = (current.innerText || current.textContent || '').trim();
                    if (
                      projectionText.includes(issueKey) &&
                      projectionText.includes(issueSummary)
                    ) {
                      return projectionText.includes(expectedStatus) &&
                          projectionText.includes(expectedPriority)
                        ? { projectionText }
                        : null;
                    }
                    current = current.parentElement;
                  }

                  return null;
                }
                """,
                arg={
                    "expectedPriority": expected_priority,
                    "expectedStatus": expected_status,
                    "issueKey": issue_key,
                    "issueSelector": self._issue_selector(
                        issue_key=issue_key,
                        issue_summary=issue_summary,
                    ),
                    "issueSummary": issue_summary,
                },
                timeout_ms=60_000,
            )
        except WebAppTimeoutError as error:
            current_projection = self._current_issue_projection_text(
                issue_key=issue_key,
                issue_summary=issue_summary,
            )
            raise AssertionError(
                f"Step {step_number} failed: the {section_label} projection did not visibly "
                f"refresh {issue_key} to Status = {expected_status} and Priority = "
                f"{expected_priority}.\n"
                f"Observed {section_label} projection: {current_projection}\n"
                f"Observed body text:\n{self.current_body_text()}",
            ) from error
        if not isinstance(payload, dict):
            raise AssertionError(
                f"Step {step_number} failed: the {section_label} view did not expose an "
                f"observable refreshed projection for {issue_key}.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        return str(payload["projectionText"])

    def _current_issue_projection_text(self, *, issue_key: str, issue_summary: str) -> str:
        payload = self._session.evaluate(
            """
            ({ issueKey, issueSelector, issueSummary }) => {
              const issue = document.querySelector(issueSelector);
              if (!issue) {
                return { projectionText: '' };
              }

              let current = issue;
              while (current) {
                const projectionText = (current.innerText || current.textContent || '').trim();
                if (
                  projectionText.includes(issueKey) &&
                  projectionText.includes(issueSummary)
                ) {
                  return { projectionText };
                }
                current = current.parentElement;
              }

              return {
                projectionText: (issue.innerText || issue.textContent || '').trim(),
              };
            }
            """,
            arg={
                "issueKey": issue_key,
                "issueSelector": self._issue_selector(
                    issue_key=issue_key,
                    issue_summary=issue_summary,
                ),
                "issueSummary": issue_summary,
            },
        )
        if not isinstance(payload, dict):
            return ""
        return str(payload.get("projectionText", ""))

    def _control_observation(
        self,
        predicate_expression: str,
    ) -> EditControlObservation | None:
        payload = self._session.evaluate(
            f"""
            (predicateSource) => {{
              const predicate = eval(predicateSource);
              const match = Array.from(document.querySelectorAll('flt-semantics[role="button"]'))
                .map((button) => ({{
                  label: button.getAttribute('aria-label'),
                  text: (button.innerText || '').trim(),
                  tabindex: button.getAttribute('tabindex'),
                  expanded: button.getAttribute('aria-expanded'),
                }}))
                .find((candidate) => predicate({{
                  getAttribute: (name) => {{
                    if (name === 'aria-label') {{
                      return candidate.label;
                    }}
                    if (name === 'tabindex') {{
                      return candidate.tabindex;
                    }}
                    if (name === 'aria-expanded') {{
                      return candidate.expanded;
                    }}
                    return null;
                  }},
                  innerText: candidate.text,
                }}));
              return match ?? null;
            }}
            """,
            arg=predicate_expression,
        )
        if not isinstance(payload, dict):
            return None
        return EditControlObservation(
            label=str(payload["label"]) if payload["label"] is not None else None,
            text=str(payload["text"]),
            tabindex=(
                str(payload["tabindex"]) if payload["tabindex"] is not None else None
            ),
            expanded=(
                str(payload["expanded"]) if payload["expanded"] is not None else None
            ),
        )

    def _open_focusable_dropdown(
        self,
        *,
        selector: str,
        has_text: str | None,
        control_name: str,
    ) -> tuple[str, ...]:
        self._session.focus(
            selector,
            has_text=has_text,
            timeout_ms=30_000,
        )
        for key in ("Enter", " ", "ArrowUp"):
            self._session.press_key(key)
            try:
                self._session.wait_for_function(
                    """
                    () => document.querySelectorAll('flt-semantics[role="menuitem"]').length > 0
                    """,
                    timeout_ms=5_000,
                )
                options = self._visible_menu_options()
                if options:
                    return options
            except WebAppTimeoutError:
                continue
        active = self._session.active_element()
        raise AssertionError(
            f"Step failed: opening the {control_name} control did not expose a "
            "keyboard-selectable menu item in the hosted edit dialog.\n"
            f"Active element after opening: {active}\n"
            f"Observed body text:\n{self.current_body_text()}",
        )

    def _visible_menu_options(self) -> tuple[str, ...]:
        payload = self._session.evaluate(
            """
            (selector) => Array.from(document.querySelectorAll(selector))
              .map((element) => {
                const label = element.getAttribute('aria-label');
                const text = (element.innerText || element.textContent || '').trim();
                return (label || text || '').trim();
              })
              .filter((label) => label.length > 0)
            """,
            arg=self._menu_item_selector,
        )
        if not isinstance(payload, list):
            return ()
        return tuple(str(label) for label in payload)

    def _select_dropdown_option(
        self,
        *,
        control_name: str,
        target_label: str,
        options: tuple[str, ...],
    ) -> None:
        if target_label not in options:
            raise AssertionError(
                f"Step failed: the {control_name} control did not expose the required "
                f'visible option "{target_label}".\n'
                f"Visible options: {list(options)}",
            )
        clicked = self._session.evaluate(
            """
            ({ selector, targetLabel }) => {
              const match = Array.from(document.querySelectorAll(selector)).find((element) => {
                const label = element.getAttribute('aria-label');
                const text = (element.innerText || element.textContent || '').trim();
                return label === targetLabel || text === targetLabel;
              });
              if (!match) {
                return false;
              }
              match.click();
              return true;
            }
            """,
            arg={
                "selector": self._menu_item_selector,
                "targetLabel": target_label,
            },
        )
        if clicked is not True:
            raise AssertionError(
                f"Step failed: the {control_name} menu did not expose a clickable option "
                f'exactly labeled "{target_label}".\n'
                f"Visible options: {list(options)}\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        try:
            self._session.wait_for_function(
                """
                () =>
                  document.querySelectorAll('flt-semantics[role="menuitem"]').length === 0
                  && (document.body?.innerText ?? '').includes('Edit issue')
                """,
                timeout_ms=30_000,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                f"Step failed: selecting {target_label} from the {control_name} menu did "
                "not return the app to the hosted edit dialog.\n"
                f"Observed body text:\n{self.current_body_text()}",
            ) from error

    def _active_menu_item_label(self) -> str:
        active = self._session.active_element()
        if active.role != "menuitem" or active.accessible_name is None:
            raise AssertionError(
                "The hosted dropdown menu lost focus before the test could finish "
                "navigating its visible options.\n"
                f"Observed active element: {active}",
            )
        return active.accessible_name

    def _button_bounds_for_sidebar_label(self, label: str) -> dict[str, float] | None:
        payload = self._session.evaluate(
            """
            (label) => {
              const button = Array.from(document.querySelectorAll('flt-semantics[role="button"]'))
                .find((element) => (element.innerText || '').trim() === label);
              if (!button) {
                return null;
              }
              const rect = button.getBoundingClientRect();
              return {
                x: rect.x,
                y: rect.y,
                width: rect.width,
                height: rect.height,
              };
            }
            """,
            arg=label,
        )
        if not isinstance(payload, dict):
            return None
        return {
            "x": float(payload["x"]),
            "y": float(payload["y"]),
            "width": float(payload["width"]),
            "height": float(payload["height"]),
        }

    @staticmethod
    def _issue_selector(*, issue_key: str, issue_summary: str) -> str:
        escaped_summary = issue_summary.replace("\\", "\\\\").replace('"', '\\"')
        return (
            'flt-semantics[role="button"]'
            f'[aria-label="Open {issue_key} {escaped_summary}"]'
        )

    @staticmethod
    def _issue_detail_selector(issue_key: str) -> str:
        escaped = issue_key.replace("\\", "\\\\").replace('"', '\\"')
        return (
            'flt-semantics[aria-label*="Issue detail '
            f'{escaped}"], '
            'flt-semantics-img[aria-label*="Issue detail '
            f'{escaped}"]'
        )
